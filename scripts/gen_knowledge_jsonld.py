#!/usr/bin/env python3
"""Generate CollectionPage + ItemList + BreadcrumbList JSON-LD for the three
knowledge hubs, reading the article list out of each hub's own cards.

    python3 scripts/gen_knowledge_jsonld.py          # report only
    python3 scripts/gen_knowledge_jsonld.py --write  # apply

Re-run after adding a column so the ItemList stays in sync with the page.
Titles are taken verbatim from the cards; nothing is invented here.

2026-09-17 (PR#86): the JA hub and the top page also get their freshness
stamped from the same cards, so a new column needs one edit (its card):
  * <!--S:kcount-->67<!--/S:kcount-->  … 記事数 = ハブのカード数 + そもそも連載の子ページ数
    （深掘りの子ページ 47-2 や 45-2 はカードに無いので数えない＝従来の「全67記事」の数え方）
  * 「全N記事」 in the hub's <title> / meta description / og / twitter
  * <!--S:kdate-->2026.09.13<!--/S:kdate-->  … 最新の datePublished
  * <!--S:knew-->…<!--/S:knew-->  … 新着リスト（ハブ4本・トップ3枚）を datePublished 順に描画
  * カードの NEW バッジ（.is-new + <span class="new">）= 公開から NEW_DAYS 日以内だけ
"""
import datetime
import html
import json
import re
import sys
from pathlib import Path

BASE = "https://www.scix.co.jp"
MARKER = "<!-- scix-knowledge-jsonld -->"

HUBS = {
    "knowledge.html": {
        "url": f"{BASE}/knowledge",
        "card": r'<a[^>]*href="(/column-[^"]+)"[^>]*class="ac[^"]*"[^>]*>(.*?)</a>',
        "title": r"<h3[^>]*>(.*?)</h3>",
        "name": "ナレッジ",
        "crumbs": [("ホーム", f"{BASE}/"), ("ナレッジ", f"{BASE}/knowledge")],
        "lang": None,
    },
    "en/knowledge.html": {
        "url": f"{BASE}/en/knowledge",
        "card": r'<a[^>]*href="(/en/[^"]+)"[^>]*class="ac[^"]*"[^>]*>(.*?)</a>',
        "title": r"<h3[^>]*>(.*?)</h3>",
        "name": "Knowledge",
        "crumbs": [("Home", f"{BASE}/en"), ("Knowledge", f"{BASE}/en/knowledge")],
        "lang": None,
    },
    "zh-knowledge.html": {
        "url": f"{BASE}/zh-knowledge",
        "card": r'<a[^>]*class="kn-card"[^>]*href="(/zh-[^"]+)"[^>]*>(.*?)</a>',
        "title": r'<div class="kn-title"[^>]*>(.*?)</div>',
        "name": "洞见",
        "crumbs": [("首页", f"{BASE}/zh"), ("洞见", f"{BASE}/zh-knowledge")],
        "lang": "zh-CN",
    },
}


def clean(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html.unescape(text).split())


def meta(source: str, name: str) -> str:
    m = re.search(r'<meta name="%s" content="([^"]*)"' % name, source)
    return html.unescape(m.group(1)) if m else ""


def build(path: Path, cfg: dict) -> tuple[str, int]:
    src = path.read_text(encoding="utf-8")
    cards = re.findall(cfg["card"], src, re.S)
    if not cards:
        raise SystemExit(f"{path}: カードを抽出できませんでした")

    items = []
    for i, (href, body) in enumerate(cards, 1):
        m = re.search(cfg["title"], body, re.S)
        if not m:
            raise SystemExit(f"{path}: {href} のタイトルが取れません")
        items.append({
            "@type": "ListItem",
            "position": i,
            "url": BASE + href,
            "name": clean(m.group(1)),
        })

    title = re.search(r"<title>(.*?)</title>", src, re.S).group(1)
    collection = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": html.unescape(title).split("｜")[0].split("|")[0].strip(),
        "description": meta(src, "description"),
        "url": cfg["url"],
        "isPartOf": {"@type": "WebSite", "name": "ScienceX", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "Science X Inc."},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        },
    }
    if cfg["lang"]:
        collection["inLanguage"] = cfg["lang"]

    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": u}
            for i, (n, u) in enumerate(cfg["crumbs"], 1)
        ],
    }

    block = "%s\n<script type=\"application/ld+json\">\n%s\n</script>\n<script type=\"application/ld+json\">\n%s\n</script>" % (
        MARKER,
        json.dumps(collection, ensure_ascii=False, indent=2),
        json.dumps(crumbs, ensure_ascii=False, indent=2),
    )
    return block, len(items)


NEW_DAYS = 45
S_MARK = re.compile(r"(<!--S:(kcount|kdate|knew)-->)(.*?)(<!--/S:\2-->)", re.S)


def date_published(slug: str) -> str:
    """column-xxx → datePublished from its Article JSON-LD ('' if absent)."""
    p = Path(slug.lstrip("/") + ".html")
    if not p.exists():
        return ""
    m = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', p.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def ja_cards(src: str) -> list:
    """Cards of the JA hub with category, number, title, description and date."""
    out = []
    for cat_id, block in re.findall(r'<div class="cat-block" id="(cat-[a-z]+)">(.*?)(?=<div class="cat-block"|<div class="wrapper" style="padding-bottom)', src, re.S):
        cat_title = clean(re.search(r'class="cat-title">(.*?)<span', block, re.S).group(1))
        for m in re.finditer(r'<a[^>]*href="(/column-[^"]+)"[^>]*class="ac[^"]*"[^>]*>(.*?)</a>', block, re.S):
            href, body = m.groups()
            num = re.search(r'class="an">COLUMN ([\d-]+)</span>', body)
            out.append({
                "href": href,
                "cat": cat_id,
                "cat_title": cat_title,
                "num": num.group(1) if num else "",
                "title": clean(re.search(r"<h3[^>]*>(.*?)</h3>", body, re.S).group(1)),
                "desc": clean(re.search(r'class="ad">(.*?)</p>', body, re.S).group(1)),
                "date": date_published(href),
            })
    return out


def stamp(src: str, values: dict) -> str:
    return S_MARK.sub(lambda m: m.group(1) + values[m.group(2)] + m.group(4), src)


def esc(t: str) -> str:
    return html.escape(t, quote=False)


def freshness(hub_src: str, index_path: Path, write: bool) -> str:
    """Stamp count / latest date / 新着 / NEW badges into the JA hub and the top page.
    Returns the (possibly rewritten) hub source."""
    cards = ja_cards(hub_src)
    series_children = len(list(Path(".").glob("column-somosomo-*.html")))
    count = len(cards) + series_children
    dated = sorted((c for c in cards if c["date"]), key=lambda c: (c["date"], c["num"]), reverse=True)
    latest = dated[0]["date"] if dated else ""
    today = datetime.date.today()
    cutoff = (today - datetime.timedelta(days=NEW_DAYS)).isoformat()

    # NEW badges on the hub cards
    def badge(m):
        href, cls, body = m.group(1), m.group(2), m.group(3)
        d = date_published(href)
        is_new = bool(d) and d >= cutoff
        cls2 = re.sub(r"\s*is-new", "", cls) + (" is-new" if is_new else "")
        body2 = re.sub(r'<span class="new">NEW</span>', "", body)
        if is_new:
            body2 = re.sub(r'(class="an">COLUMN [\d-]+</span>)', r'\1<span class="new">NEW</span>', body2, count=1)
        return '<a target="_top" href="%s" class="%s">%s</a>' % (href, cls2.strip(), body2)
    hub = re.sub(r'<a target="_top" href="(/column-[^"]+)" class="(ac[^"]*)">(.*?)</a>', badge, hub_src, flags=re.S)

    # 全N記事 in title / meta / og / twitter
    head_end = hub.find("</head>")
    hub = re.sub(r"全\d+記事", f"全{count}記事", hub[:head_end]) + hub[head_end:]

    ymd = latest.replace("-", ".")
    hub_new = "\n".join(
        '          <li><a target="_top" href="%s"><span class="n">%s</span>%s<span class="d">%s</span></a></li>'
        % (c["href"], esc(c["num"]), esc(c["title"]), c["date"].replace("-", "."))
        for c in dated[:4]
    )
    hub = stamp(hub, {"kcount": str(count), "kdate": ymd, "knew": "\n" + hub_new + "\n        "})

    idx_new = "\n".join(
        '          <a target="_top" href="%s" class="k-card">\n'
        '            <div class="k-num">COLUMN %s <span class="k-tag">%s</span></div>\n'
        '            <h4>%s</h4>\n'
        '            <p class="k-desc">%s</p>\n'
        '          </a>' % (c["href"], esc(c["num"]), esc(c["cat_title"]), esc(c["title"]), esc(c["desc"]))
        for c in dated[:3]
    )
    idx = index_path.read_text(encoding="utf-8")
    idx2 = stamp(idx, {"kcount": str(count), "kdate": ymd, "knew": "\n" + idx_new + "\n        "})
    new_n = sum(1 for c in cards if c["date"] and c["date"] >= cutoff)
    print(f"freshness: 記事数 {count}（カード {len(cards)} + 連載 {series_children}）・最終更新 {latest}・NEW {new_n} 枚・新着 {[c['num'] for c in dated[:4]]}")
    if write and idx2 != idx:
        index_path.write_text(idx2, encoding="utf-8")
    return hub


def main() -> int:
    write = "--write" in sys.argv
    for name, cfg in HUBS.items():
        path = Path(name)
        src = path.read_text(encoding="utf-8")
        if name == "knowledge.html":
            src = freshness(src, Path("index.html"), write)
            if write:
                path.write_text(src, encoding="utf-8")
        block, n = build(path, cfg)
        if MARKER in src:
            src = re.sub(
                re.escape(MARKER) + r".*?</script>\s*<script type=\"application/ld\+json\">.*?</script>",
                lambda _: block, src, count=1, flags=re.S,
            )
        else:
            assert "</head>" in src, name
            src = src.replace("</head>", block + "\n</head>", 1)
        print(f"{name}: 記事 {n} 件を ItemList 化")
        if write:
            path.write_text(src, encoding="utf-8")
    print("書き込みました。" if write else "（--write を付けると反映します）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
