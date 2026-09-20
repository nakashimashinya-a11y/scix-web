#!/usr/bin/env python3
"""週次自動更新の安全弁。Claude が作業ツリーに加えた変更を、公開前に機械で検査する。

    python3 scripts/seo/guard_diff.py --manifest <changes.json>     # 検査（0=通す／1=止める）
    python3 scripts/seo/guard_diff.py --manifest <changes.json> --profile structure   # 月1回の構成レビュー（PR で提案）

止める理由は全部表示する。通らなければ weekly_run.sh は何も公開しない（作業ツリーを捨てる）。
検査の中身:
  - 触ってよいファイルだけか（HTML・sitemap・header.js の JA_ONLY_COLUMNS 行。変更日台帳はシェルが記帳するので Claude は書かない）
  - 触ってはいけないもの（フォーム・/fund・vercel.json・projects.json・scripts・.github・robots・img・files・削除）
  - 量の上限（既存ページの変更 12 本まで／新規 HTML 3 本まで／1ファイルの差し替え率）
  - HTML の骨格（title・description・canonical・h1 1つ・header.js・JSON-LD が壊れていない・内部リンク切れ無し）
  - EN は title 70字以内・description 155字以内（Bing の指摘）
  - 新コラムの必須ブロック（監修・Article JSON-LD author=Person・パンくず・CTA・sitemap 登録）
  - 禁止語（自称「中立」・実績の主張・鍵らしき文字列）
  - マニフェスト（何をなぜ変えたか）と実際の差分が一致している
  - トップ（index.html・en/index.html・zh.html）のヒーローより上は変えない（<body> の先頭〜<section class="hero"> の終わり）

--profile structure（月1回の構成レビュー。公開はせず PR で提案する＝weekly_run.sh の MODE=structure）で変わるところ:
  - 量: マニフェストは 3 件まで・新規ファイルは 0・1ファイルの差し替えは「並べ替えを除いた正味」で測る
    （行を多重集合で比べる。節やカードを動かしただけなら正味 0。正味の書き換え 1/4 まで・正味の削除 15% まで・
      見かけの差し替え（+と−の合計）は 120% まで＝動かした行は両方に数えられる）
  - ハブ・トップ（HUBS）はヒーローより下だけ: <body> の先頭〜ヒーローの終わり（ハブは最初の </h1> まで）が同一、
    title・description・canonical も同一（数字だけの違いは無視＝「全N記事」の焼き直し）
  - <!--S:…--> の内側は並び順を問わず同じ中身であること（節ごと動かすのは可・中身を書き換えるのは不可）
  - header.js: JA_ONLY_COLUMNS の行に加えて **ナビ定義**（GROUP_PAGES 〜 var nav = […];）を変えてよい。ただし
    ナビ定義が変わっていたら「ナビの組み替えは90日に1回まで」を、マニフェストの申告（class=nav のエントリの
    nav_rule.last_nav_change）と、変更台帳＋origin/main の header.js の履歴（structure.nav_rule）とで照合する。
    ナビ定義と JA_ONLY_COLUMNS 以外（CSS・計測・更新メール）は変えられない
  - マニフェストの各変更に pages・measure（いつ何で測るか）が要る。rationale には根拠の数字が要る。class は
    hub-order / top-order / cta-route / funnel-block / nav。PR の本文（公開）に載る欄に、問い合わせの件数を書かない
  それ以外（触ってはいけないファイル・title・canonical・JSON-LD・リンク切れ・鍵・自称中立など）は週次と同じ。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import collections
import html.parser
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, file_to_url, path_of  # noqa: E402

REPO = Path(os.environ.get("SCIX_WEB_REPO", Path.cwd()))
ALLOWED_HTML = re.compile(r"^(en/)?[a-z0-9-]+\.html$|^zh-[a-z0-9-]+\.html$")
FORBIDDEN = {"docs/seo-change-log.md", "fund.html", "contact.html", "sell-form.html", "thanks.html", "privacy.html", "404.html",
             "en/contact.html", "en/thanks.html", "zh-contact.html", "zh-thanks.html",
             "projects.json", "vercel.json", "robots.txt", "README.md", "CLAUDE.md"}
FORBIDDEN_PREFIX = ("scripts/", ".github/", "img/", "files/", "notes/", ".claude/", "docs/new-mac-setup.md")
HUBS = {"knowledge.html", "en/knowledge.html", "zh-knowledge.html", "index.html", "en/index.html", "zh.html"}
MAX_EXISTING = 12
MAX_NEW = 3
MAX_REPLACE_RATIO = 0.5
MAX_DELETE_RATIO = 0.25
CLASSES = {"title", "description", "body", "internal-link", "cta", "new-column", "rollback", "hub", "faq", "structured-data"}
# 構成レビュー（--profile structure）
STRUCT_CLASSES = {"hub-order", "top-order", "cta-route", "funnel-block", "nav"}
STRUCT_MAX_ENTRIES = 3
STRUCT_MAX_NEW = 0
STRUCT_MAX_REPLACE_RATIO = 1.2   # 見かけの差し替え（動かした行は + と − の両方に数えられる）
STRUCT_NET_RATIO = 0.25          # 並べ替えを除いた正味の書き換え（足した行＋消した行）
STRUCT_NET_DELETE = 0.15         # 正味の削除
HERO_TOPS = {"index.html", "en/index.html", "zh.html"}
# PR の本文は公開リポジトリに載る。問い合わせ（generate_lead）の件数・用件別は Drive の台帳側だけ
LEAD_NUMBER_RE = re.compile(r"(?:generate_lead|リード数?|問い合わせ(?:件数|数)?|キーイベント|intent)\s*[=:＝：はがを]?\s*[0-9０-９]+")
BAD_WORDS = [(re.compile(r"中立"), "自称「中立」は禁止（メーカー・EPCと資本関係がない、と事実で書く）"),
             (re.compile(r"\bneutral\b|\bindependent (advisor|broker|party)\b", re.I), "neutral/independent の自称は禁止"),
             (re.compile(r"当社の(成約|取引|導入)実績|成約実績|実績多数"), "実績の主張は出さない（中島決定 2026-09-05）"),
             (re.compile(r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,}"), "鍵らしき文字列")]


# 毎朝の案件一覧の同期（scripts/inject_stats.py）が書く場所。週次がここを書き換えても翌朝に黙って戻るか、
# 静的一覧と JS の文言がずれたまま残る。projects.html の一覧を描く JS も同じ理由で週次の対象外。
SYNCED_RE = re.compile(r"<!--S:([a-z]+)-->(.*?)<!--/S:\1-->", re.S)
PAGE_JS_RE = re.compile(r"<script(?![^>]*ld\+json)[^>]*>(.*?)</script>", re.S)


# scripts/inject_stats.py の compute() が返すキーと同じ集合。ナレッジ側の kcount/kdate/knew は
# 週次シェル自身が検査の直前に gen_knowledge_jsonld.py --write で焼き直すので対象にしない。
INJECT_KEYS = {"list", "count", "mw", "prefs", "areas", "shv", "maxmw", "date", "pjnew"}


def synced_regions(text: str) -> list:
    return [(m.group(1), m.group(2)) for m in SYNCED_RE.finditer(text) if m.group(1) in INJECT_KEYS]


def hero_region(text: str):
    """<body> の先頭からヒーローの終わりまで。トップ＝<section class="hero">…</section>、それ以外（ハブ）＝最初の </h1>。
    <!--S:…--> の中身は同期・焼き直しが書くので空にして比べる。取れなければ None。"""
    b = text.find("<body")
    if b < 0:
        return None
    m = re.search(r'<section\b[^>]*class="hero"', text[b:])
    if m:
        end = text.find("</section>", b + m.start())
        end = end + len("</section>") if end >= 0 else -1
    else:
        end = text.find("</h1>", b)
        end = end + len("</h1>") if end >= 0 else -1
    if end < 0:
        return None
    return SYNCED_RE.sub(lambda x: f"<!--S:{x.group(1)}--><!--/S:{x.group(1)}-->", text[b:end])


def net_change(before: str, after: str):
    """並べ替えを除いた正味の変更。(足した行, 消した行, 元の行数)。空行は数えない。"""
    b = collections.Counter(l.strip() for l in before.splitlines() if l.strip())
    a = collections.Counter(l.strip() for l in after.splitlines() if l.strip())
    return sum((a - b).values()), sum((b - a).values()), max(1, sum(b.values()))


def same_but_digits(x, y) -> bool:
    return re.sub(r"[0-9０-９]+", "N", (x or "").strip()) == re.sub(r"[0-9０-９]+", "N", (y or "").strip())


def check_header_js(profile: str, entries: list, problems: list) -> None:
    """header.js。週次＝JA_ONLY_COLUMNS の行だけ。構成レビュー＝加えてナビ定義（90日ルールを台帳と照合）。"""
    if profile != "structure":
        diff = sh("git", "diff", "--", "header.js")
        for line in diff.splitlines():
            if line.startswith(("+++", "---", "@@", "diff", "index")):
                continue
            if line.startswith(("+", "-")) and not re.match(r"^[+-]\s*'/column-[a-z0-9-]+',?\s*$", line):
                problems.append(f"header.js は JA_ONLY_COLUMNS の行しか変えられない: {line[:80]}")
        return
    import structure as st
    before = sh("git", "show", "HEAD:header.js")
    after = (REPO / "header.js").read_text(encoding="utf-8")
    nb, na = st.nav_block(before), st.nav_block(after)
    if nb is None or na is None:
        problems.append("header.js: ナビ定義（var GROUP_PAGES 〜 var nav = […];）を見つけられない＝検査できないので止める")
        return
    if st.header_without_nav(before) != st.header_without_nav(after):
        problems.append("header.js はナビ定義と JA_ONLY_COLUMNS 以外（CSS・計測・更新メール・言語切替）を変えられない")
    m = st.JA_ONLY_RE.search(after)
    for line in (m.group(2).splitlines() if m else []):
        if line.strip() and not re.match(r"^\s*'/column-[a-z0-9-]+',?\s*$", line):
            problems.append(f"header.js: JA_ONLY_COLUMNS の行の形が想定外: {line.strip()[:60]}")
    if nb == na:
        return
    # ナビ定義が変わった → 90日ルール。申告（マニフェスト）と実績（変更台帳＋origin/main の履歴）の両方が要る
    navs = [e for e in entries if e.get("class") == "nav" and "header.js" in (e.get("files") or [])]
    if not navs:
        problems.append("header.js のナビ定義が変わっているのに、マニフェストに class=nav（files に header.js）のエントリが無い")
    rule = st.nav_rule(cwd=REPO)
    if rule["last"]:
        problems.append(f"ナビの組み替えは {st.NAV_FREEZE_DAYS} 日に1回まで: 直近のナビ変更は {rule['last']}"
                        f"（{rule['days_since']} 日前・{rule['changes'][0]['source']} {rule['changes'][0]['ref']}）。"
                        f"次に提案してよいのは {rule['next_ok']} 以降")
    for e in navs:
        decl = e.get("nav_rule")
        if not isinstance(decl, dict) or "last_nav_change" not in decl:
            problems.append("class=nav のエントリに nav_rule.last_nav_change の申告が無い（直近90日にナビ変更が無ければ null）")
        elif decl.get("last_nav_change") != rule["last"]:
            problems.append(f"ナビ変更の申告が台帳と合わない: 申告 {decl.get('last_nav_change')}／台帳・履歴 {rule['last']}")


def sh(*args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""; self._t = False; self.desc = None; self.canonical = None; self.h1 = 0
        self.header_js = False; self.inline_header = False; self.ld = []; self._ld = None
        self.links = []; self.author_box = False; self.breadcrumb = False; self.hreflang = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "title": self._t = True
        elif tag == "meta" and (a.get("name") or "").lower() == "description": self.desc = a.get("content", "")
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical": self.canonical = a.get("href")
            elif rel == "alternate" and a.get("hreflang"): self.hreflang[a["hreflang"]] = a.get("href")
        elif tag == "h1": self.h1 += 1
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json": self._ld = ""
            elif a.get("src") == "/header.js": self.header_js = True
        elif tag == "header" and "scix-header" in cls: self.inline_header = True
        elif tag == "a" and a.get("href"): self.links.append(a["href"])
        elif tag == "nav" and "data-scix-breadcrumb" in a: self.breadcrumb = True
        elif "author-box" in cls.split(): self.author_box = True

    def handle_endtag(self, tag):
        if tag == "title": self._t = False
        elif tag == "script" and self._ld is not None:
            try: self.ld.append(json.loads(self._ld))
            except json.JSONDecodeError: self.ld.append(None)
            self._ld = None

    def handle_data(self, data):
        if self._t: self.title += data
        elif self._ld is not None: self._ld += data


def resolves(href: str, redirects: set, sitemap_paths: set) -> bool:
    if not href.startswith("/") or href.startswith("//"):
        return True
    p = href.split("#")[0].split("?")[0]
    if not p or p == "/":
        return True
    if p in redirects or p in sitemap_paths:
        return True
    if p.startswith(("/img/", "/files/")):
        return (REPO / p.lstrip("/")).exists()
    if p == "/en":
        return (REPO / "en" / "index.html").exists()
    if p.endswith("/"):
        p = p[:-1]
    return (REPO / (p.lstrip("/") + ".html")).exists() or (REPO / p.lstrip("/")).exists() or (REPO / (p.lstrip("/") + ".txt")).exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--profile", choices=("weekly", "structure"), default="weekly",
                    help="structure＝月1回の構成レビュー（並べ替えの分だけ量を緩め、ナビは90日ルールを照合）")
    a = ap.parse_args()
    structure = a.profile == "structure"
    problems = []

    status = [l for l in sh("git", "status", "--porcelain", "--untracked-files=all").splitlines() if l.strip()]
    changed, added, deleted = [], [], []
    for l in status:
        code, path = l[:2], l[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if "D" in code:
            deleted.append(path)
        elif "?" in code or "A" in code:
            added.append(path)
        else:
            changed.append(path)
    if not (changed or added):
        print("変更なし"); return 0
    for p in deleted:
        problems.append(f"削除は禁止: {p}")

    manifest = {}
    try:
        manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        problems.append(f"マニフェストが読めない: {e}")
    entries = manifest.get("changes") or []
    listed = set()
    if structure and len(entries) > STRUCT_MAX_ENTRIES:
        problems.append(f"構成の変更は {STRUCT_MAX_ENTRIES} 件まで（{len(entries)} 件）")
    if structure:
        for l in manifest.get("summary_lines") or []:
            if LEAD_NUMBER_RE.search(str(l)):
                problems.append(f"summary_lines: 問い合わせの件数は公開の PR 本文に書かない: {str(l)[:60]}")
    for i, e in enumerate(entries):
        for k in ("files", "class", "summary", "rationale", "kpi") + (("pages", "measure") if structure else ()):
            if not e.get(k):
                problems.append(f"マニフェスト {i}: {k} が無い")
        if e.get("class") not in (STRUCT_CLASSES if structure else CLASSES):
            problems.append(f"マニフェスト {i}: class が想定外 {e.get('class')}")
        if structure:
            if not re.search(r"[0-9０-９]", str(e.get("rationale", ""))):
                problems.append(f"マニフェスト {i}: rationale に根拠の数字が無い")
            for k in ("summary", "rationale", "kpi", "measure", "hypothesis"):
                if LEAD_NUMBER_RE.search(str(e.get(k, ""))):
                    problems.append(f"マニフェスト {i}: {k} に問い合わせの件数を書かない（PR の本文は公開。件数は private_note へ）")
        if len(str(e.get("summary", ""))) > 300:
            problems.append(f"マニフェスト {i}: summary が長すぎる")
        for f in e.get("files") or []:
            listed.add(f)
    for f in listed:
        if f not in changed and f not in added:
            problems.append(f"マニフェストにあるが実際には変わっていない: {f}")

    redirects = set()
    try:
        redirects = {r["source"] for r in json.load(open(REPO / "vercel.json", encoding="utf-8")).get("redirects", [])}
    except Exception:  # noqa: BLE001
        pass
    sitemap_text = (REPO / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
    sitemap_paths = {path_of(u) for u in sitemap_urls}

    all_titles = {}
    for f in list(REPO.glob("*.html")) + list((REPO / "en").glob("*.html")):
        m = re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8", errors="replace"), re.S)
        if m:
            all_titles.setdefault(m.group(1).strip(), []).append(str(f.relative_to(REPO)))

    n_existing = n_new = 0
    for path in changed + added:
        is_new = path in added
        if path in FORBIDDEN or path.startswith(FORBIDDEN_PREFIX):
            problems.append(f"触ってはいけないファイル: {path}"); continue
        if path == "sitemap.xml":
            continue
        if path == "header.js":
            if is_new:
                problems.append("header.js が新規ファイルになっている"); continue
            check_header_js(a.profile, entries, problems)
            continue
        if not ALLOWED_HTML.match(path):
            problems.append(f"想定外のファイル: {path}"); continue
        if path not in listed and path not in HUBS:
            problems.append(f"マニフェストに載っていない変更: {path}")
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
        before = "" if is_new else sh("git", "show", f"HEAD:{path}")
        if is_new:
            n_new += 1
        elif structure:
            if path not in HUBS:
                n_existing += 1
            num = sh("git", "diff", "--numstat", "--", path).split()
            total = max(1, len(before.splitlines()))
            if len(num) >= 2 and (int(num[0]) + int(num[1])) / total > STRUCT_MAX_REPLACE_RATIO:
                problems.append(f"{path}: 差し替えが大きすぎる（+{num[0]}/-{num[1]} of {total}行）")
            add_, del_, base = net_change(before, text)
            if (add_ + del_) / base > STRUCT_NET_RATIO:
                problems.append(f"{path}: 並べ替えを除いた正味の書き換えが大きすぎる（足した行 {add_}・消した行 {del_} of {base}行・上限 {STRUCT_NET_RATIO:.0%}）")
            if del_ / base > STRUCT_NET_DELETE:
                problems.append(f"{path}: 正味の削除が多すぎる（{del_} of {base}行・上限 {STRUCT_NET_DELETE:.0%}）")
        elif path not in HUBS:
            n_existing += 1
            num = sh("git", "diff", "--numstat", "--", path).split()
            if len(num) >= 2:
                add_, del_ = int(num[0]), int(num[1])
                total = max(1, len(text.splitlines()))
                if (add_ + del_) / total > MAX_REPLACE_RATIO:
                    problems.append(f"{path}: 差し替えが大きすぎる（+{add_}/-{del_} of {total}行）")
                if del_ / total > MAX_DELETE_RATIO:
                    problems.append(f"{path}: 削除が多すぎる（-{del_} of {total}行）")
        if not is_new:
            sb, sa = synced_regions(before), synced_regions(text)
            if (sorted(sb) != sorted(sa)) if structure else (sb != sa):
                problems.append(f"{path}: <!--S:…--> の内側は毎朝の同期が書く場所（件数・一覧・新着）。"
                                + ("節ごと動かすのはよいが、中身は変えない" if structure else "週次では触らない"))
            if path == "projects.html" and PAGE_JS_RE.findall(before) != PAGE_JS_RE.findall(text):
                problems.append("projects.html: 一覧を描く JS は週次では触らない（scripts/inject_stats.py の静的一覧と文言をそろえてある）")
            if path in HERO_TOPS or (structure and path in HUBS):
                hb, ha = hero_region(before), hero_region(text)
                if hb is None or ha is None:
                    problems.append(f"{path}: ヒーローの範囲（<body> 〜 hero の終わり）を取れない＝検査できないので止める")
                elif hb != ha:
                    problems.append(f"{path}: ヒーローより上は変えない（<body> の先頭〜"
                                    + ("<section class=\"hero\"> の終わり" if 'class="hero"' in hb else "最初の </h1>") + "）")
        pg = Page(); pg.feed(text)
        if structure and not is_new and path in HUBS:
            pb = Page(); pb.feed(before)
            if not (same_but_digits(pb.title, pg.title) and same_but_digits(pb.desc, pg.desc) and pb.canonical == pg.canonical):
                problems.append(f"{path}: 構成レビューではハブ・トップの title／description／canonical を変えない")
        url = file_to_url(path)
        if not pg.title.strip():
            problems.append(f"{path}: title が無い")
        else:
            others = [o for o in all_titles.get(pg.title.strip(), []) if o != path]
            if others:
                problems.append(f"{path}: title が他ページと重複 {others}")
        if pg.desc is None or not pg.desc.strip():
            problems.append(f"{path}: description が無い")
        if '"' in (pg.desc or "") and "&quot;" not in text:
            pass
        if not pg.canonical or path_of(pg.canonical) != path_of(url or ""):
            problems.append(f"{path}: canonical が自分を指していない（{pg.canonical}）")
        if pg.h1 != 1:
            problems.append(f"{path}: h1 が {pg.h1} 個")
        if not pg.header_js:
            problems.append(f"{path}: /header.js を読んでいない")
        if pg.inline_header:
            problems.append(f"{path}: ヘッダーの直書き")
        if None in pg.ld:
            problems.append(f"{path}: JSON-LD が壊れている")
        if path.startswith("en/"):
            if len(pg.title.strip()) > 70:
                problems.append(f"{path}: EN title が70字超（{len(pg.title.strip())}）")
            if pg.desc and len(pg.desc) > 155:
                problems.append(f"{path}: EN description が155字超（{len(pg.desc)}）")
        else:
            if pg.desc and len(pg.desc) > 170:
                problems.append(f"{path}: description が長すぎる（{len(pg.desc)}字・目安120）")
        for href in set(pg.links):
            if not resolves(href, redirects, sitemap_paths):
                problems.append(f"{path}: 内部リンク切れ {href}")
        for lang, href in pg.hreflang.items():
            if href and href.startswith(BASE) and not resolves(path_of(href), redirects, sitemap_paths):
                problems.append(f"{path}: hreflang {lang} の先が無い {href}")
        # 新コラムの骨格
        if is_new and re.search(r"(^|/|^zh-)column-", path):
            arts = [x for x in pg.ld if isinstance(x, dict) and x.get("@type") == "Article"]
            if not arts:
                problems.append(f"{path}: Article JSON-LD が無い")
            else:
                au = arts[0].get("author") or {}
                if (au.get("@type") if isinstance(au, dict) else None) != "Person":
                    problems.append(f"{path}: Article.author が Person でない")
            if not any(isinstance(x, dict) and x.get("@type") == "BreadcrumbList" for x in pg.ld):
                problems.append(f"{path}: BreadcrumbList JSON-LD が無い")
            if not pg.author_box:
                problems.append(f"{path}: 監修ブロック（.author-box）が無い")
            if not pg.breadcrumb:
                problems.append(f"{path}: 可視パンくず（data-scix-breadcrumb）が無い")
            if not any(l.split("?")[0].rstrip("/") in ("/projects", "/sourcing", "/transfer", "/investors", "/contact", "/land",
                                                        "/en/contact", "/zh-contact") for l in pg.links):
                problems.append(f"{path}: 収益ページへの CTA リンクが無い")
            if url and path_of(url) not in sitemap_paths:
                problems.append(f"{path}: sitemap.xml に載っていない")
            if not path.startswith(("en/", "zh-")):
                # JA コラム: EN/ZH が無ければ JA_ONLY_COLUMNS に登録されているべき
                slug = "/" + path[:-5]
                has_en = (REPO / "en" / path).exists(); has_zh = (REPO / ("zh-" + path)).exists()
                hj = (REPO / "header.js").read_text(encoding="utf-8")
                if not (has_en and has_zh) and f"'{slug}'" not in hj:
                    problems.append(f"{path}: EN/ZH が無いのに header.js の JA_ONLY_COLUMNS に無い")
        # 禁止語（追加行だけ見る）
        diff = sh("git", "diff", "--", path) if not is_new else "\n".join("+" + l for l in text.splitlines())
        for line in diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for rx, why in BAD_WORDS:
                if rx.search(line):
                    problems.append(f"{path}: {why}: {line[1:90].strip()}")
    if n_existing > MAX_EXISTING:
        problems.append(f"既存ページの変更が多すぎる（{n_existing} > {MAX_EXISTING}）")
    if n_new > (STRUCT_MAX_NEW if structure else MAX_NEW):
        problems.append("構成レビューでは新規ファイルを作らない" if structure else f"新規ファイルが多すぎる（{n_new} > {MAX_NEW}）")
    # sitemap の整合
    if "sitemap.xml" in changed:
        try:
            import xml.dom.minidom
            xml.dom.minidom.parseString(sitemap_text)
        except Exception as e:  # noqa: BLE001
            problems.append(f"sitemap.xml が XML として壊れている: {e}")
        for u in sitemap_urls:
            if not resolves(path_of(u), redirects, set()):
                problems.append(f"sitemap.xml: 実体の無い URL {u}")

    if problems:
        print("止める理由:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK{'（structure）' if structure else ''} 既存 {n_existing}・新規 {n_new}・マニフェスト {len(entries)} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
