#!/usr/bin/env python3
"""週次自動更新の安全弁。Claude が作業ツリーに加えた変更を、公開前に機械で検査する。

    python3 scripts/seo/guard_diff.py --manifest <changes.json>     # 検査（0=通す／1=止める）

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
"""
import argparse
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
BAD_WORDS = [(re.compile(r"中立"), "自称「中立」は禁止（メーカー・EPCと資本関係がない、と事実で書く）"),
             (re.compile(r"\bneutral\b|\bindependent (advisor|broker|party)\b", re.I), "neutral/independent の自称は禁止"),
             (re.compile(r"当社の(成約|取引|導入)実績|成約実績|実績多数"), "実績の主張は出さない（中島決定 2026-09-05）"),
             (re.compile(r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,}"), "鍵らしき文字列")]


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
    a = ap.parse_args()
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
    for i, e in enumerate(entries):
        for k in ("files", "class", "summary", "rationale", "kpi"):
            if not e.get(k):
                problems.append(f"マニフェスト {i}: {k} が無い")
        if e.get("class") not in CLASSES:
            problems.append(f"マニフェスト {i}: class が想定外 {e.get('class')}")
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
            diff = sh("git", "diff", "--", "header.js")
            for line in diff.splitlines():
                if line.startswith(("+++", "---", "@@", "diff", "index")):
                    continue
                if line.startswith(("+", "-")) and not re.match(r"^[+-]\s*'/column-[a-z0-9-]+',?\s*$", line):
                    problems.append(f"header.js は JA_ONLY_COLUMNS の行しか変えられない: {line[:80]}")
            continue
        if not ALLOWED_HTML.match(path):
            problems.append(f"想定外のファイル: {path}"); continue
        if path not in listed and path not in HUBS:
            problems.append(f"マニフェストに載っていない変更: {path}")
        if is_new:
            n_new += 1
        elif path not in HUBS:
            n_existing += 1
            num = sh("git", "diff", "--numstat", "--", path).split()
            if len(num) >= 2:
                add_, del_ = int(num[0]), int(num[1])
                total = max(1, len((REPO / path).read_text(encoding="utf-8", errors="replace").splitlines()))
                if (add_ + del_) / total > MAX_REPLACE_RATIO:
                    problems.append(f"{path}: 差し替えが大きすぎる（+{add_}/-{del_} of {total}行）")
                if del_ / total > MAX_DELETE_RATIO:
                    problems.append(f"{path}: 削除が多すぎる（-{del_} of {total}行）")
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
        pg = Page(); pg.feed(text)
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
    if n_new > MAX_NEW:
        problems.append(f"新規ファイルが多すぎる（{n_new} > {MAX_NEW}）")
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
    print(f"OK 既存 {n_existing}・新規 {n_new}・マニフェスト {len(entries)} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
