#!/usr/bin/env python3
"""月1回の構成レビュー（第1日曜・weekly_run.sh の MODE=structure）の共通部品。

  build_brief.py --structure   … ブリーフに S1〜S8 節を足す（ナビ・遷移の太さ・コラムの送客・セッション0・孤立・カテゴリ・トップの節・過去の提案）
  guard_diff.py --profile structure … ナビ配列の変更を見つけ、「ナビの組み替えは90日に1回まで」を台帳と git で照合する
  register_structure_merges.py … 提案 PR（ledger/proposals.jsonl）がマージされたら変更台帳へ記帳する

どれも台帳（GSC・GA4・健診・変更台帳）と git（origin/main）だけで決定論に作る。追加 API なし。
サイトの現物（ハブのカテゴリ・トップの節・ナビ）は作業ツリーではなく git の ref（既定 origin/main）から読む。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import html
import re
import subprocess

from common import COMMERCIAL, LEDGER, REPO, d, read_jsonl, safe_d, today
import newpages as npg

NAV_FREEZE_DAYS = 90     # ナビの組み替えは四半期に1回まで
PROPOSALS = LEDGER / "ledger" / "proposals.jsonl"
CHANGES = LEDGER / "ledger" / "changes.jsonl"
# 構成レビューで「収益ページ」と呼ぶ7本（表の列）。COMMERCIAL のそれ以外（/sell-form・EN/ZH の contact）は「ほか」に足す
REVENUE = ["/projects", "/transfer", "/investors", "/fund", "/sourcing", "/land", "/contact"]
TOPS = {"/", "/en", "/zh"}
HUB_PAGES = {"/knowledge", "/en/knowledge", "/zh-knowledge"}
HUB_FILES = {"ja": "knowledge.html", "en": "en/knowledge.html", "zh": "zh-knowledge.html"}
HUB_FILES_PAGE = {"ja": "/knowledge", "en": "/en/knowledge", "zh": "/zh-knowledge"}
NOT_CONTENT = {"/privacy", "/thanks", "/en/thanks", "/zh-thanks", "/404"}
KIND_LABEL = {"top": "トップ", "hub": "ハブ", "column": "コラム", "revenue": "収益ページ", "other": "その他"}
KINDS = ["top", "hub", "column", "revenue", "other"]
MIN_VIEWS_ZERO_FEED = 20   # 「送客ゼロのコラム」に数える最低の表示回数（28日）


# ---------------------------------------------------------------- パス

def norm(p) -> str:
    """GA4 の pagePath・referrer を sitemap のパスにそろえる（/x.html → /x・/index → /・末尾の / を落とす）。"""
    p = (p or "").split("?")[0].split("#")[0]
    if not p.startswith("/"):
        return p
    if p.endswith(".html"):
        p = p[:-5]
    if p.endswith("/index"):
        p = p[:-6]
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p or "/"


def kind(p: str) -> str:
    if p in TOPS:
        return "top"
    if p in HUB_PAGES:
        return "hub"
    if p in COMMERCIAL:
        return "revenue"
    if npg.is_column(p):
        return "column"
    return "other"


# ---------------------------------------------------------------- GA4 の集計

def agg(ga_recs):
    """(views, sessions, trans, nav, nav_days)。views/sessions はページ別、trans は (from, to)→表示回数。"""
    views, sessions, trans, nav, nav_days = {}, {}, {}, {}, 0
    for r in ga_recs:
        for x in r.get("pages") or []:
            p = norm(x.get("pagePath"))
            views[p] = views.get(p, 0) + int(x.get("screenPageViews") or 0)
            sessions[p] = sessions.get(p, 0) + int(x.get("sessions") or 0)
        for x in r.get("transitions") or []:
            f, t = norm(x.get("from")), norm(x.get("to"))
            if f and t and f != t:
                trans[(f, t)] = trans.get((f, t), 0) + int(x.get("views") or 0)
        if r.get("nav_click"):
            nav_days += 1
        for x in r.get("nav_click") or []:
            k = x.get("customEvent:nav_group") or "(not set)"
            nav[k] = nav.get(k, 0) + int(x.get("eventCount") or 0)
    return views, sessions, trans, nav, nav_days


def flow_matrix(trans) -> dict:
    m = {a: {b: 0 for b in KINDS} for a in KINDS}
    for (f, t), n in trans.items():
        m[kind(f)][kind(t)] += n
    return m


# ---------------------------------------------------------------- git の現物（ハブ・トップ・ナビ）

def _git(*args, cwd=None) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(cwd or REPO), capture_output=True, text=True, timeout=120).stdout
    except Exception:  # noqa: BLE001
        return ""


def _show(rel: str, cwd=None) -> str:
    return _git("show", f"{npg.ref()}:{rel}", cwd=cwd)


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


BLOCK_RE = re.compile(r'<div class="(?:cat-block|kn-group)[^"]*" id="((?:kn-)?cat-[a-z0-9-]+)"')
CARD_RE = re.compile(r'<a\b[^>]*class="(?:ac|kn-card)(?:\s[^"]*)?"[^>]*>')
TITLE_RE = re.compile(r'<(?:h2|div) class="(?:cat-title|kn-group-title)"[^>]*>(.*?)</(?:h2|div)>', re.S)


def hub_categories(lang: str = "ja", cwd=None) -> list:
    """ハブのカテゴリブロックを並び順どおりに。[{id, title, order, cards:[パス]}]"""
    src = _show(HUB_FILES[lang], cwd=cwd)
    starts = [(m.start(), m.group(1)) for m in BLOCK_RE.finditer(src)]
    out = []
    for i, (pos, cid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        block = src[pos:end]
        t = TITLE_RE.search(block)
        title = _text(re.sub(r"<span[^>]*>.*?</span>", "", t.group(1), flags=re.S)) if t else cid
        cards = []
        for a in CARD_RE.finditer(block):
            h = re.search(r'href="(/[^"#?]+)"', a.group(0))
            if h and norm(h.group(1)) not in cards:
                cards.append(norm(h.group(1)))
        out.append({"id": cid, "title": title, "order": i + 1, "cards": cards})
    return out


SECTION_RE = re.compile(r'<section\b([^>]*)>(.*?)</section>', re.S)


def top_sections(cwd=None) -> list:
    """トップ（index.html）の節を並び順どおりに。[{id, cls, h2, links:[内部リンク先]}]。先頭の hero も含める。"""
    src = _show("index.html", cwd=cwd)
    out = []
    for m in SECTION_RE.finditer(src):
        attrs, body = m.group(1), m.group(2)
        sid = re.search(r'id="([^"]+)"', attrs)
        cls = re.search(r'class="([^"]+)"', attrs)
        h = re.search(r"<h[12][^>]*>(.*?)</h[12]>", body, re.S)
        links = []
        for href in re.findall(r'<a\b[^>]*href="(/[^"#?]*)', body):
            p = norm(href)
            if p not in links and p != "/":
                links.append(p)
        out.append({"id": sid.group(1) if sid else "", "cls": cls.group(1) if cls else "",
                    "h2": _text(re.sub(r"<!--.*?-->", "", h.group(1), flags=re.S))[:60] if h else "", "links": links})
    return out


NAV_RE = re.compile(r"var GROUP_PAGES\s*=.*?\n\s*var nav\s*=.*?\n  \];", re.S)
JA_ONLY_RE = re.compile(r"(var JA_ONLY_COLUMNS\s*=\s*\[)(.*?)(\];)", re.S)


def cta_block_files(cwd=None) -> set:
    """標準の CTA ブロック（<!-- scix-column-cta -->）を持つページ。持たないコラムは旧世代の CTA か、CTA が無い。"""
    out = _git("grep", "-l", "scix-column-cta", npg.ref(), "--", "*.html", cwd=cwd)
    return {npg.page_path(l.split(":", 1)[1]) for l in out.splitlines() if ":" in l and npg.is_page_file(l.split(":", 1)[1])}


def nav_block(header_js: str):
    """header.js のナビ定義（GROUP_PAGES 〜 var nav = […];）。空白の違いは無視。見つからなければ None。"""
    m = NAV_RE.search(header_js or "")
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def header_without_nav(header_js: str) -> str:
    """ナビ定義と JA_ONLY_COLUMNS の中身を抜いた header.js（それ以外が変わっていないかの比較用）。"""
    s = NAV_RE.sub("<<NAV>>", header_js or "", count=1)
    return JA_ONLY_RE.sub(lambda m: m.group(1) + "<<JA_ONLY>>" + m.group(3), s, count=1)


def nav_changes(days: int = NAV_FREEZE_DAYS, cwd=None, asof=None) -> list:
    """直近 days 日のナビ変更。変更台帳（class=nav か nav_change）と、origin/main の header.js の履歴
    （ナビ定義が親コミットと違うもの）の両方から拾う。[{date, source, ref, summary}]・新しい順。"""
    asof = asof or today()
    since = asof - datetime.timedelta(days=days)
    out = []
    for e in read_jsonl(CHANGES):
        day = safe_d(e.get("date"))   # 台帳の 1 行の日付が壊れていても、ナビの90日ルールの照合とブリーフは止めない
        if (e.get("class") == "nav" or e.get("nav_change")) and day and day >= since:
            out.append({"date": e["date"], "source": "ledger", "ref": e.get("id"), "summary": (e.get("summary") or "")[:80]})
    log_ = _git("log", npg.ref(), f"--since={since - datetime.timedelta(days=1)}", "--format=%H%x09%cs%x09%s",
                "--", "header.js", cwd=cwd)
    for line in log_.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3 or d(parts[1]) < since:
            continue
        sha, date, subj = parts
        after = nav_block(_git("show", f"{sha}:header.js", cwd=cwd))
        before = nav_block(_git("show", f"{sha}^:header.js", cwd=cwd))
        if after != before:
            out.append({"date": date, "source": "git", "ref": sha[:10], "summary": subj[:80]})
    out.sort(key=lambda x: (x["date"], x["source"]), reverse=True)
    return out


def nav_rule(cwd=None, asof=None) -> dict:
    """{'last': 直近のナビ変更日 or None, 'days_since', 'allowed': bool, 'next_ok': 次に提案してよい日, 'changes': […]}"""
    asof = asof or today()
    ch = nav_changes(cwd=cwd, asof=asof)
    last = ch[0]["date"] if ch else None
    since = (asof - d(last)).days if last else None
    return {"last": last, "days_since": since, "allowed": last is None,
            "next_ok": str(d(last) + datetime.timedelta(days=NAV_FREEZE_DAYS + 1)) if last else None, "changes": ch}


def proposals() -> list:
    return read_jsonl(PROPOSALS)


# ---------------------------------------------------------------- ハブ・トップの凍結（ブリーフ 9 節・構成レビュー用）
# 週次のブリーフの 9 節は「直近14日に触った全コミット」で凍結する。ハブ・トップはコラムを 1 本足すたびに
# カードが足され、件数・新着（<!--S:kcount--> <!--S:knew-->）・ItemList が焼き直される＝毎週触られる。それを凍結に
# 数えると、構成レビューの主目的（hub-order・top-order）が一度も提案できない。だから構成レビュー用のブリーフでは、
# ハブ・トップの凍結を **変更台帳の構成系のエントリだけ** で決める（is_structure_entry。git の履歴では凍結しない）。
# 人が手で構成を変えたときも、台帳に class=hub で記帳してあれば凍結される（効果測定もそこから走る）。
HUB_TOP_FILES = {"knowledge.html": "/knowledge", "en/knowledge.html": "/en/knowledge", "zh-knowledge.html": "/zh-knowledge",
                 "index.html": "/", "en/index.html": "/en", "zh.html": "/zh"}
HUB_TOP_PAGES = frozenset(HUB_TOP_FILES.values())
FREEZE_CLASSES = ("hub", "hub-order", "top-order", "nav")   # 週次の hub と、構成レビューの hub-order／top-order／nav


def is_structure_entry(e: dict) -> bool:
    """変更台帳のエントリが構成系か（ハブ・トップを凍結する変更か）。構成レビューの PR がマージされたもの
    （source=structure。cta-route・funnel-block も含む）と、class が hub／hub-order／top-order／nav のもの。"""
    return e.get("class") in FREEZE_CLASSES or e.get("source") == "structure"


# 参考の表示用（凍結には使わない）: 台帳に記帳の無い、ハブ・トップの構成を変えたコミットを見つける。
# ブリーフの 28 日の数字はその変更より前のものが混ざる＝根拠として弱い、と Claude に知らせるため。
_S_BLOCK_RE = re.compile(r"<!--S:([a-z]+)-->.*?<!--/S:\1-->", re.S)
_LD_BLOCK_RE = re.compile(r"<script\b[^>]*application/ld\+json[^>]*>.*?</script>", re.S | re.I)
_CARD_BLOCK_RE = re.compile(r'<a\b[^>]*class="(?:ac|kn-card)(?:\s[^"]*)?"[^>]*>.*?</a>', re.S)


def layout_signature(text: str):
    """(骨格, カードの並び)。骨格＝<!--S:…--> の中身・JSON-LD・カード（a.ac／a.kn-card）を抜き、数字を N にした行の列
    （「全 N 記事」・カテゴリの件数の焼き直しを無視する）。カードの並び＝カードの href を出てくる順に。"""
    s = _S_BLOCK_RE.sub(lambda m: f"<!--S:{m.group(1)}--><!--/S:{m.group(1)}-->", text or "")
    s = _LD_BLOCK_RE.sub("", s)
    cards = []

    def take(m):
        h = re.search(r'href="([^"#?]+)', m.group(0))
        cards.append(norm(h.group(1)) if h else m.group(0)[:60])
        return ""
    s = _CARD_BLOCK_RE.sub(take, s)
    skeleton = tuple(re.sub(r"[0-9０-９]+", "N", l.strip()) for l in s.splitlines() if l.strip())
    return skeleton, cards


def layout_changed(before: str, after: str) -> bool:
    """ハブ・トップの構成（並び・見出し・導線・本文）が変わったか。カードの追加と、件数・新着・JSON-LD の
    焼き直しだけなら False。カードを消した・入れ替えた、カード以外の行が 1 行でも変わった、なら True。"""
    sb, cb = layout_signature(before)
    sa, ca = layout_signature(after)
    if sb != sa:
        return True
    it = iter(ca)
    return not all(c in it for c in cb)   # 前のカードの並びが、後の並びの部分列（＝足しただけ）でなければ構成の変更


def layout_changed_in(sha: str, rel: str, cwd=None) -> bool:
    """コミット sha がファイル rel の構成を変えたか（親コミットと比べる。読めなければ安全側＝変えた）。"""
    after = _git("show", f"{sha}:{rel}", cwd=cwd)
    before = _git("show", f"{sha}^:{rel}", cwd=cwd)
    if not after or not before:
        return True
    return layout_changed(before, after)


def unrecorded_layout_commits(days: int, frozen=(), cwd=None) -> list:
    """[(ページ, 日付, 件名)]。直近 days 日の履歴（HEAD）で、ハブ・トップの構成（並び・見出し・導線・本文）を変えた
    コミットのうち、そのページが frozen（台帳の構成系エントリで凍結中）に入っていないもの。ページごとに新しい 1 件。
    案件一覧の自動同期と、カードの追加・件数／新着／JSON-LD の焼き直しだけのコミットは出さない。"""
    out = {}
    for line in _git("log", f"--since={days}.days", "--format=%H%x09%cs%x09%s", "--", *sorted(HUB_TOP_FILES), cwd=cwd).splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3 or parts[2].startswith("chore(projects)"):
            continue
        sha, date, subj = parts
        for rel in _git("show", "--name-only", "--format=", sha, cwd=cwd).split():
            page = HUB_TOP_FILES.get(rel)
            if page and page not in frozen and page not in out and layout_changed_in(sha, rel, cwd=cwd):
                out[page] = (page, date, subj[:60])
    return sorted(out.values())


# ---------------------------------------------------------------- ブリーフの節

def data(ga_cur, ga_prev, pages28, landing, health, cwd=None) -> dict:
    views, sessions, trans, nav, nav_days = agg(ga_cur)
    _, _, _, pnav, pnav_days = agg(ga_prev)
    hpages = [p for p in (health or {}).get("pages", []) if p.get("status") == 200]
    inbound = npg.inbound_counts(health)
    has_cta = cta_block_files(cwd=cwd)

    # S3: コラム → 収益ページ
    feed = {}
    for (f, t), n in trans.items():
        if kind(f) == "column" and t in COMMERCIAL:
            a = feed.setdefault(f, {"total": 0, "to": {}})
            a["total"] += n; a["to"][t] = a["to"].get(t, 0) + n
    columns = sorted({p["url"] for p in hpages if npg.is_column(p["url"])} | {p for p in views if npg.is_column(p)})
    col_rows = []
    for c in columns:
        f = feed.get(c, {"total": 0, "to": {}})
        col_rows.append({"page": c, "views": views.get(c, 0), "landing": (landing.get(c) or {}).get("sessions", 0),
                         "to_revenue": f["total"], "to": f["to"],
                         "rate": (f["total"] / views[c]) if views.get(c) else 0.0,
                         "cta_block": c in has_cta})
    top_feed = sorted([r for r in col_rows if r["to_revenue"]], key=lambda r: (-r["to_revenue"], r["page"]))
    zero_feed = sorted([r for r in col_rows if not r["to_revenue"] and r["views"] >= MIN_VIEWS_ZERO_FEED],
                       key=lambda r: (-r["views"], r["page"]))

    # S4: 28日セッション0（sitemap にあるページ）
    zero_sessions = []
    for p in hpages:
        u = p["url"]
        if u in NOT_CONTENT or sessions.get(u) or views.get(u) or (landing.get(u) or {}).get("sessions"):
            continue
        zero_sessions.append({"page": u, "lang": npg.lang_of(u), "kind": kind(u), "inbound": inbound.get(u, 0),
                              "impressions": (pages28.get(u) or {}).get("impressions", 0)})
    zero_sessions.sort(key=lambda r: (npg.LANG_ORDER[r["lang"]], r["inbound"], r["page"]))

    # S5: 孤立（サイト内被リンク1以下。ナビは header.js が実行時に描くので数に入らない＝本文・フッターからのリンクだけ）
    orphans = []
    for p in hpages:
        u = p["url"]
        if u in NOT_CONTENT or u in TOPS or inbound.get(u, 0) > 1:
            continue
        orphans.append({"page": u, "lang": npg.lang_of(u), "kind": kind(u), "inbound": inbound.get(u, 0),
                        "views": views.get(u, 0), "impressions": (pages28.get(u) or {}).get("impressions", 0)})
    orphans.sort(key=lambda r: (r["inbound"], -r["impressions"], r["page"]))

    # S6: カテゴリ別
    cats = {}
    for lang in ("ja", "en", "zh"):
        rows = []
        for c in hub_categories(lang, cwd=cwd):
            g = [pages28.get(u) or {} for u in c["cards"]]
            rows.append({**c, "n": len(c["cards"]), "clicks": sum(x.get("clicks", 0) for x in g),
                         "impressions": sum(x.get("impressions", 0) for x in g),
                         "views": sum(views.get(u, 0) for u in c["cards"]),
                         "landing": sum((landing.get(u) or {}).get("sessions", 0) for u in c["cards"]),
                         "from_hub": sum(trans.get((HUB_FILES_PAGE[lang], u), 0) for u in c["cards"]),
                         "to_revenue": sum(feed.get(u, {}).get("total", 0) for u in c["cards"])})
        cats[lang] = rows

    # S7: トップの節（その節が持つリンク先へ、トップから何回遷移したか。節ごとのクリックは測っていない＝近似）
    secs = []
    for i, s in enumerate(top_sections(cwd=cwd)):
        per = {l: trans.get(("/", l), 0) for l in s["links"]}
        secs.append({**s, "order": i + 1, "out": sum(per.values()),
                     "out_top": sorted(((l, n) for l, n in per.items() if n), key=lambda kv: -kv[1])[:5]})

    return {"views": views, "sessions": sessions, "nav": nav, "nav_days": nav_days, "nav_prev": pnav,
            "nav_prev_days": pnav_days, "matrix": flow_matrix(trans),
            "from_top": sorted(((t, n) for (f, t), n in trans.items() if f == "/"), key=lambda kv: -kv[1])[:12],
            "from_hub": sorted(((t, n) for (f, t), n in trans.items() if f == "/knowledge"), key=lambda kv: -kv[1])[:12],
            "into_revenue": {r: sorted(((f, n) for (f, t), n in trans.items() if t == r), key=lambda kv: -kv[1])[:6]
                             for r in REVENUE},
            "revenue_to_form": sorted(((f + " → " + t, n) for (f, t), n in trans.items()
                                       if t in ("/contact", "/sell-form") and f in COMMERCIAL), key=lambda kv: -kv[1]),
            "top_feed": top_feed, "zero_feed": zero_feed, "n_columns": len(columns),
            "zero_sessions": zero_sessions, "orphans": orphans, "categories": cats, "top_sections": secs,
            "nav_rule": nav_rule(cwd=cwd), "proposals": proposals()}



def render_sections(L: list, s: dict, lim: int = 20) -> None:
    L.append("\n---\n\n# 構成レビュー用の節（月1回・第1日曜）\n")
    L.append("ここから下は `build_brief.py --structure` のときだけ出る。遷移・表示回数は GA4 の28日窓（上の節と同じ）。"
             "遷移は「同じサイト内の前のページ → そのページ」の表示回数で、人数ではない。\n")

    # S1
    L.append("## S1. ナビのクリック（GA4 nav_click・グループ別）\n")
    nav, prev = s["nav"], s["nav_prev"]
    tot = sum(nav.values())
    if tot:
        L.append(f"データのある日数: 直近28日のうち {s['nav_days']} 日・前28日のうち {s['nav_prev_days']} 日"
                 "（nav_click の計測は 2026-09-17 のナビ再編から。日数が少ないうちは順位だけを見る）。\n")
        L.append("| nav_group | クリック | 構成比 | 前28日 |\n|---|---|---|---|")
        for k, v in sorted(nav.items(), key=lambda kv: (-kv[1], kv[0])):
            L.append(f"| {k} | {v} | {v / tot * 100:.0f}% | {prev.get(k, 0)} |")
        L.append("\nnav_group の意味: knowledge／buy／sell＝引き出しの中の行き先、top＝引き出しの外の直リンク（会社案内・お問い合わせ）、"
                 "cta＝金ボタン（販売中の案件を見る）、logo＝ロゴ、lang＝言語切替。\n")
    else:
        L.append("nav_click のデータが無い（GA4 未収集か、カスタムディメンション nav_group が未登録）。\n")
    nr = s["nav_rule"]
    if nr["last"]:
        L.append(f"**ナビの組み替えは今回提案しない**: 直近90日にナビ変更あり（最後は {nr['last']}・{nr['days_since']} 日前）。"
                 f"次に提案してよいのは {nr['next_ok']} 以降。")
        for c in nr["changes"][:5]:
            L.append(f"- {c['date']} {c['source']} {c['ref']} {c['summary']}")
    else:
        L.append("**ナビの組み替えを提案してよい**: 変更台帳と origin/main の header.js の履歴に、直近90日のナビ変更は無い。"
                 "提案するときはマニフェストに `\"nav_rule\": {\"last_nav_change\": null}` を書く（検査が台帳と照合する）。")
    L.append("")

    # S2
    L.append("## S2. 遷移の太さ（トップ → ハブ → コラム → 収益ページ）\n")
    m = s["matrix"]
    if any(m[a][b] for a in KINDS for b in KINDS):
        L.append("| から ＼ へ | " + " | ".join(KIND_LABEL[k] for k in KINDS) + " |\n|---|" + "---|" * len(KINDS))
        for a in KINDS:
            L.append(f"| {KIND_LABEL[a]} | " + " | ".join(str(m[a][b]) for b in KINDS) + " |")
        L.append("\n- **トップ（/）から**: " + ("・".join(f"{t} {n}" for t, n in s["from_top"]) or "なし"))
        L.append("- **ハブ（/knowledge）から**: " + ("・".join(f"{t} {n}" for t, n in s["from_hub"]) or "なし"))
        for r in REVENUE:
            src = s["into_revenue"].get(r)
            if src:
                L.append(f"- **{r} へ**: " + "・".join(f"{f} {n}" for f, n in src))
        if s["revenue_to_form"]:
            L.append("- **収益ページ → フォーム**: " + "・".join(f"{f} {n}" for f, n in s["revenue_to_form"][:8]))
    else:
        L.append("GA4 の遷移データが無い。")
    L.append("")

    # S3
    L.append("## S3. コラムから収益ページへの送客\n")
    L.append(f"コラム {s['n_columns']} 本のうち、28日で収益ページへの遷移があったのは {len(s['top_feed'])} 本。"
             "「CTA」は標準の CTA ブロック（`<!-- scix-column-cta -->`）の有無。無いコラムは旧世代の CTA か CTA なし＝行き先は現物を読む。\n")
    L.append(f"### S3a. 送客が多いコラム（上位{lim}）\n")
    L.append("| コラム | 表示回数 | 着地 | 収益ページへ | 率 | 行き先 | CTA |\n|---|---|---|---|---|---|---|")
    for r in s["top_feed"][:lim]:
        L.append(f"| {r['page']} | {r['views']} | {r['landing']} | {r['to_revenue']} | {r['rate'] * 100:.1f}% | "
                 + "・".join(f"{t} {n}" for t, n in sorted(r["to"].items(), key=lambda kv: -kv[1])) + " | "
                 + ("あり" if r["cta_block"] else "標準なし") + " |")
    L.append(f"\n### S3b. 読まれているのに送客ゼロのコラム（表示回数 {MIN_VIEWS_ZERO_FEED} 以上・上位{lim}）\n")
    if s["zero_feed"]:
        L.append("| コラム | 表示回数 | 着地 | CTA |\n|---|---|---|---|")
        for r in s["zero_feed"][:lim]:
            L.append(f"| {r['page']} | {r['views']} | {r['landing']} | {'あり' if r['cta_block'] else '標準なし'} |")
        if len(s["zero_feed"]) > lim:
            L.append(f"\n（ほか {len(s['zero_feed']) - lim} 本。全件は brief.json の structure.zero_feed）")
    else:
        L.append("なし。")
    L.append("")

    # S4
    L.append("## S4. 28日セッション0のページ（sitemap にあるのに GA4 で一度も開かれていない）\n")
    z = s["zero_sessions"]
    if z:
        by = {}
        for r in z:
            by[r["lang"]] = by.get(r["lang"], 0) + 1
        L.append(f"{len(z)} ページ（" + "・".join(f"{k} {v}" for k, v in sorted(by.items())) + "）。被リンクの少ない順。\n")
        L.append("| ページ | 言語 | 種別 | 被リンク | GSC 表示（28日） |\n|---|---|---|---|---|")
        for r in z[:lim * 2]:
            L.append(f"| {r['page']} | {r['lang']} | {KIND_LABEL[r['kind']]} | {r['inbound']} | {r['impressions']} |")
        if len(z) > lim * 2:
            L.append(f"\n（ほか {len(z) - lim * 2} ページ。全件は brief.json の structure.zero_sessions）")
    else:
        L.append("なし（健診のページ一覧が無いときもここは空）。")
    L.append("")

    # S5
    L.append("## S5. 孤立ページ（サイト内被リンク1以下）\n")
    o = s["orphans"]
    if o:
        L.append(f"{len(o)} ページ。被リンクは健診（本番 HTML の本文・フッターのリンク。ナビは header.js が描くので数に入らない）。\n")
        L.append("| ページ | 言語 | 種別 | 被リンク | 表示回数（GA4） | GSC 表示 |\n|---|---|---|---|---|---|")
        for r in o[:lim * 2]:
            L.append(f"| {r['page']} | {r['lang']} | {KIND_LABEL[r['kind']]} | {r['inbound']} | {r['views']} | {r['impressions']} |")
        if len(o) > lim * 2:
            L.append(f"\n（ほか {len(o) - lim * 2} ページ。全件は brief.json の structure.orphans）")
    else:
        L.append("なし。")
    L.append("")

    # S6
    L.append("## S6. カテゴリ別の本数と流入（ハブの並び順どおり）\n")
    for lang, label in (("ja", "JA /knowledge"), ("en", "EN /en/knowledge"), ("zh", "ZH /zh-knowledge")):
        rows = s["categories"].get(lang) or []
        if not rows:
            continue
        L.append(f"### {label}\n")
        L.append("| 並び | カテゴリ | 本数 | GSC クリック | GSC 表示 | 表示回数（GA4） | 着地 | ハブから | 収益ページへ |\n|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            L.append(f"| {r['order']} | {r['title']}（#{r['id']}） | {r['n']} | {r['clicks']} | {r['impressions']} | "
                     f"{r['views']} | {r['landing']} | {r['from_hub']} | {r['to_revenue']} |")
        L.append("")
    L.append("本数はそのカテゴリブロックのカード数（そもそも連載の子ページ・深掘りの子ページはカードに無いので数えない）。"
             "「ハブから」はハブ → そのカテゴリのコラムへの遷移。\n")

    # S7
    L.append("## S7. トップ（/）の節の並び\n")
    L.append("「リンク先への遷移」は、その節が持つ内部リンクの行き先へ、トップから遷移した回数の合計"
             "（節ごとのクリックは測っていない＝同じ行き先を複数の節が持つと両方に数える近似）。先頭の hero は動かさない。\n")
    L.append("| 並び | 節（id） | 見出し | リンク先の数 | リンク先への遷移 | 主な行き先 |\n|---|---|---|---|---|---|")
    for r in s["top_sections"]:
        L.append(f"| {r['order']} | {r['cls']}{('#' + r['id']) if r['id'] else ''} | {r['h2']} | {len(r['links'])} | {r['out']} | "
                 + "・".join(f"{l} {n}" for l, n in r["out_top"]) + " |")
    L.append("")

    # S8
    L.append("## S8. これまでの構成の提案\n")
    pr = s["proposals"]
    if pr:
        L.append("| 提案日 | id | 状態 | PR | 種別 | ページ | 要約 |\n|---|---|---|---|---|---|---|")
        for e in sorted(pr, key=lambda x: x.get("date", ""), reverse=True)[:20]:
            L.append(f"| {e.get('date')} | {e.get('id')} | {e.get('status')} | {('#' + str(e['pr'])) if e.get('pr') else e.get('branch', '')} | "
                     f"{e.get('class', '')} | {' '.join((e.get('pages') or [])[:5])} | {(e.get('summary') or '')[:80]} |")
        L.append("\nproposed＝PR が開いたまま（同じ提案を重ねない）。merged＝公開済み（効果は 8 節の変更台帳）。"
                 "expired＝60日マージされなかった（不採用とみなす。同じ案を出すなら根拠の数字が変わっていること）。")
    else:
        L.append("まだ無い。")
    L.append("")
