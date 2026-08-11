#!/usr/bin/env python3
"""Generate CollectionPage + ItemList + BreadcrumbList JSON-LD for the three
knowledge hubs, reading the article list out of each hub's own cards.

    python3 scripts/gen_knowledge_jsonld.py          # report only
    python3 scripts/gen_knowledge_jsonld.py --write  # apply

Re-run after adding a column so the ItemList stays in sync with the page.
Titles are taken verbatim from the cards; nothing is invented here.
"""
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


def main() -> int:
    write = "--write" in sys.argv
    for name, cfg in HUBS.items():
        path = Path(name)
        block, n = build(path, cfg)
        src = path.read_text(encoding="utf-8")
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
