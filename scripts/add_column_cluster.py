#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""コラムから、そのまとまり（トピッククラスター）の柱の頁へ結ぶ。

各コラム（日英中）に2つを足す。どちらも本文（中島さんの文）と h1 の外で、何度回しても同じ結果になる。
  1. 「このテーマの全体像: <柱の頁の題>」の1行（<!-- scix-cluster:begin --> … <!-- scix-cluster:end --> で囲む）。
     置き場は末尾の区画の並び（よくある質問 → 役割分け → この1行）の最後＝著者の箱の直前
     （著者の箱が無ければ本文の箱の終わりの手前）。並びの順は column_blocks.py の ORDER。
  2. パンくずの段: 画面のパンくず（nav[data-scix-breadcrumb]）の最後の段の前に柱の頁を1段（a[data-scix-cluster]）、
     構造化データの BreadcrumbList の最後の段の前にも同じ頁を1段。
柱の頁がその言葉に無いまとまり（例: 接続検討の柱は日本語だけ）は、その言葉のコラムには足さない。柱の頁そのものにも足さない。
土地の持ち主向けのコラム（land-buyback・land-lease・land-value）には足さない（O16-5）。

まとまり9個は、2026-11-22 のコラムの棚卸し（U4_clusters.csv）のとおり。柱の頁は新しい5本（scripts/build_guides.py）と、
今ある4本（/column-jcstar・/grid-storage〔英語は /en/primer・中国語は /zh-primer〕・/column-study-reply・/column-investment-tax）。

    python3 scripts/add_column_cluster.py            # 書き換える
    python3 scripts/add_column_cluster.py --check    # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
    python3 scripts/add_column_cluster.py --root DIR # 別の木で試す

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指令1）。
コラムを変える PR が入ったら、ほかの区画の生成器の後にこれを回す（--check が 0 になるまで）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import column_blocks as cb  # noqa: E402  区画の置き場と並びの共通部品

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "--root" in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index("--root") + 1])
BASE = "https://www.scix.co.jp"
B, E = "<!-- scix-cluster:begin -->", "<!-- scix-cluster:end -->"
LAND = {"land-buyback", "land-lease", "land-value", "land-zoning"}   # 土地の持ち主向け（O16-5・コラムの持ち場の column_blocks.py と同じ4本）

# まとまり: (柱の頁 {言葉: 住所}, 属するコラムの slug)
CLUSTERS = {
    "C1": ({"ja": "/guide-balancing-market", "en": "/en/guide-balancing-market", "zh": "/zh-guide-balancing-market"},
           "eprx balancing-market area-data day-ahead price-cap balancing-saturation balancing-saturation-volume balancing-saturation-supply "
           "balancing-saturation-floor bidding-ceiling bidding-ceiling-law bidding-ceiling-calc bidding-ceiling-market bidding-ceiling-monitoring aggregator-fee"),
    "C2": ({"ja": "/guide-capacity-lda", "en": "/en/guide-capacity-lda", "zh": "/zh-guide-capacity-lda"},
           "capacity-market lda auction long-term-contract merchant"),
    "C3": ({"ja": "/guide-revenue-cost", "en": "/en/guide-revenue-cost", "zh": "/zh-guide-revenue-cost"},
           "revenue regional-revenue cashflow construction-cost biz"),
    "C4": ({"ja": "/guide-buy-sell", "en": "/en/guide-buy-sell", "zh": "/zh-guide-buy-sell"},
           "buyer-structures trading project-price pricing transfer options buyer-check financing foreign-investor"),
    "C5": ({"ja": "/column-study-reply"},
           "study-reply study-reply-2 study-reply-3 study-reply-4 grid grid-rules equipment nonfirm contract-flow contracts low-voltage development"),
    "C6": ({"ja": "/column-investment-tax", "en": "/en/column-investment-tax", "zh": "/zh-column-investment-tax"},
           "tax investment-tax investment-tax-law investment-tax-practice investment-tax-schedule subsidies"),
    "C7": ({"ja": "/column-jcstar", "en": "/en/column-jcstar", "zh": "/zh-column-jcstar"},
           "jcstar jcstar-2027 jcstar-2027-list jcstar-2027-existing jcstar-2027-nationality"),
    "C8": ({"ja": "/guide-siting-risk", "en": "/en/guide-siting-risk", "zh": "/zh-guide-siting-risk"},
           "noise hazard-eal land-zoning four-labels om bess-insurance"),
    "C9": ({"ja": "/grid-storage", "en": "/en/primer", "zh": "/zh-primer"},
           " ".join(["somosomo"] + [f"somosomo-{i}" for i in range(2, 21)])),
}
LABEL = {"ja": "このテーマの全体像: ", "en": "The big picture on this topic: ", "zh": "本主题的全貌："}
FONT = {"ja": "'Noto Sans JP',sans-serif", "en": "'Noto Sans JP',sans-serif", "zh": "'Noto Sans SC','Noto Sans JP',sans-serif"}
SUFFIX_RX = re.compile(r"\s*(｜|\|)\s*(サイエンスエックス|ScienceX|Science X)\s*$")
SEP = '<span style="color:#C49A3C;margin:0 7px">›</span>'
# 画面のパンくずの区切りは頁によって3つの形がある（同じ見た目の › の実体参照・class="breadcrumb" の素の › ）
SEPS = (SEP, '<span style="color:#C49A3C;margin:0 7px">&rsaquo;</span>', " › ")


def file_of(p: str):
    p = p.strip("/")
    for c in (p + ".html", p + "/index.html"):
        if os.path.isfile(os.path.join(ROOT, c)):
            return c
    return None


def pillar_name(p: str) -> str:
    """柱の頁の題: <title> から会社名を落とし、最初の区切り（｜・—・──）の前（短すぎれば題のまま）。"""
    s = open(os.path.join(ROOT, file_of(p)), encoding="utf-8").read()
    t = SUFFIX_RX.sub("", html.unescape(re.search(r"<title>(.*?)</title>", s, re.S).group(1)).strip())
    head = re.split(r"\s*(?:｜|\||──|—)\s*", t, maxsplit=1)[0]
    return head if len(head) >= 6 else t


def targets():
    """(コラムのファイル, 言葉, 柱の住所)。"""
    out = []
    for _cid, (pillars, slugs) in CLUSTERS.items():
        for slug in slugs.split():
            if slug in LAND:
                continue
            for lg, pre in (("ja", "column-"), ("en", "en/column-"), ("zh", "zh-column-")):
                rel = pre + slug + ".html"
                pil = pillars.get(lg)
                if not pil or not file_of(pil) or not os.path.isfile(os.path.join(ROOT, rel)):
                    continue
                if "/" + rel[:-5] == pil:   # 柱の頁そのもの
                    continue
                out.append((rel, lg, pil))
    return out


def strip_mine(s: str, pillars: set) -> str:
    s = re.sub(re.escape(B) + r".*?" + re.escape(E) + r"\n?", "", s, flags=re.S)
    s = re.sub(r'<a data-scix-cluster [^>]*>.*?</a>(?:' + "|".join(re.escape(x) for x in SEPS) + ")", "", s)
    return s


def put_line(s: str, block: str) -> str:
    # 末尾の区画の並び（よくある質問 → 役割分け → この1行）の最後＝著者の箱の直前。
    # column_blocks.py の ORDER に cluster を載せてあるので、ほかの生成器を回しても並びは崩れない。
    pos = cb.end_anchor(s)
    if pos is not None:
        return cb.place(s, "cluster", block, pos)
    m = re.search(r"\n</div>\s*\n\s*(?:<!-- scix-column-cta|<!-- scix-entrances|<!-- ScienceX Footer)", s)
    if m:
        return s[:m.start() + 1] + block + s[m.start() + 1:]
    raise ValueError("置き場が見つからない")


def put_crumb(s: str, lg: str, pil: str, name: str) -> str:
    m = re.search(r"<nav\b[^>]*data-scix-breadcrumb[^>]*>.*?</nav>", s, re.S)
    if not m:
        return s
    nav = m.group(0)
    i, sep = max((nav.rfind(x), x) for x in SEPS)
    if i < 0:
        return s
    lim = 56 if lg == "en" else 36   # 今の柱の題は全部この字数に収まる（切らずに出す）
    short = name if len(name) <= lim else name[:lim - 1] + "…"
    style = "" if sep == " › " else ' style="color:#555555;text-decoration:none"'
    a = f'<a data-scix-cluster href="{pil}"{style}>{html.escape(short, quote=False)}</a>'
    nav2 = nav[:i + len(sep)] + a + sep + nav[i + len(sep):]
    return s[:m.start()] + nav2 + s[m.end():]


def fix_ld(s: str, pil: str, name: str, pillars: set) -> str:
    def one(m):
        try:
            o = json.loads(m.group(1))
        except ValueError:
            return m.group(0)
        if not isinstance(o, dict) or o.get("@type") != "BreadcrumbList":
            return m.group(0)
        before = json.dumps(o, sort_keys=True)
        items = [it for it in o.get("itemListElement", []) if str(it.get("item", "")).replace(BASE, "") not in pillars]
        if len(items) < 2:
            return m.group(0)
        items.insert(len(items) - 1, {"@type": "ListItem", "position": 0, "name": name, "item": BASE + pil})
        for n, it in enumerate(items, 1):
            it["position"] = n
        o["itemListElement"] = items
        if json.dumps(o, sort_keys=True) == before:
            return m.group(0)
        # 元の書式（1行か、字下げの幅）に合わせて書き、区画の外の書式の差分を出さない
        orig = m.group(1)
        lines = orig.strip().split("\n")
        if len(lines) == 1:
            dumped = json.dumps(o, ensure_ascii=False)
        else:
            ind = len(lines[1]) - len(lines[1].lstrip(" ")) or 2
            dumped = json.dumps(o, ensure_ascii=False, indent=ind)
            if re.search(r'^\s*\{ "@type": "ListItem"', orig, re.M):   # 段を1行ずつ書く元の形
                sp = " " * ind
                rows = ",\n".join(sp * 2 + "{ " + ", ".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in it.items()) + " }"
                                  for it in items)
                head = {k: v for k, v in o.items() if k != "itemListElement"}
                dumped = "{\n" + "".join(f"{sp}{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in head.items()) \
                    + f'{sp}"itemListElement": [\n{rows}\n{sp}]\n}}'
        return m.group(0).replace(orig, dumped, 1)
    return re.sub(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', one, s, flags=re.S)


def apply(s: str, lg: str, pil: str, name: str, pillars: set) -> str:
    s = strip_mine(s, pillars)
    line = (f'{B}\n<p class="scix-cluster" data-scix-cluster style="margin:20px 0;padding:10px 16px;background:#F7F7F7;border:1px solid #E6E6E6;'
            f'border-radius:6px;font-family:{FONT[lg]};font-size:14px;line-height:1.8;color:#1F2A48">{html.escape(LABEL[lg], quote=False)}'
            f'<a target="_top" href="{pil}" style="color:#1F2A48;font-weight:700">{html.escape(name, quote=False)} →</a></p>\n{E}\n')
    s = put_line(s, line)
    s = put_crumb(s, lg, pil, name)
    return fix_ld(s, pil, name, pillars)


def main() -> int:
    check = "--check" in sys.argv
    pillars = {p for ps, _ in CLUSTERS.values() for p in ps.values()}
    names = {}
    bad, n = 0, 0
    for rel, lg, pil in targets():
        if pil not in names:
            names[pil] = pillar_name(pil)
        p = os.path.join(ROOT, rel)
        s = open(p, encoding="utf-8").read()
        try:
            out = apply(s, lg, pil, names[pil], pillars)
        except ValueError as e:
            print(f"止めた: {rel}（{e}）")
            bad = 1
            continue
        n += 1
        if out != s:
            if check:
                print("ずれ:", rel)
                bad = 1
            else:
                open(p, "w", encoding="utf-8").write(out)
    print(f"まとまりの行: 対象 {n} 頁・柱 {len(names)} 本" + ("（--check）" if check else "（書いた）"))
    return bad


if __name__ == "__main__":
    sys.exit(main())
