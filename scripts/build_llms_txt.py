#!/usr/bin/env python3
"""/llms.txt（機械向けの案内）を、sitemap の頁の題と説明から作る。

載せるのは今ある頁（sitemap.xml にある頁）の題・説明・住所だけ。題と説明は各頁の <title>・meta description そのまま
（言い換えない・足さない）。新しい主張・実績・利回り・手数料は書かない（O16-8）。手で直さない。

並び（2026-11-23・AI の答えに先に拾われたい順）:
  会社は何か（トップの説明・英語の会社案内の説明）
  → 売り案件の市場データ（/market-data・/en/market-data・/zh-market-data と、その頁の CSV）
  → 市場ノート（/research＝入口と月号の一覧 → 速報 /research/flash → 各号〔新しい号から〕→ /research/data と、その頁の CSV → エリア別）
  → 蓄電所マーケット（登録なしで価格を除く一覧＝マーケットのトップ・管内別の入口。会社サイトの /projects は 2026-11-25 にやめた）
  → 柱の頁（トップ・全体像・ガイド・買う／売るの入口・ナレッジの入口・会社案内）
  → コラム → その他（問い合わせ・個人情報の方針）
各区画の中は 日本語 → English → 中文 の順、言葉の中は sitemap の順（市場ノートの区画だけは issue_key() の順）。
CSV の行の字は、その頁のダウンロードのリンクの字をそのまま使う。
マーケットの2行は dealroom.scix.co.jp の頁の title と description をそのまま写す（MARKET。マーケットの頁の字が変わったら写し直す）。

    python3 scripts/build_llms_txt.py           # llms.txt を書く
    python3 scripts/build_llms_txt.py --check   # 書かずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「Seo 対策も徹底してやって」。
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.scix.co.jp"
OUT = os.path.join(ROOT, "llms.txt")

# 蓄電所マーケット（別のリポジトリ・別の住所）の頁の title と description。2026-11-23 に本番の頁で字を確かめて写した。
MARKET = {
    "ja": ("https://dealroom.scix.co.jp/",
           "蓄電所マーケット｜系統用蓄電池（蓄電所）を、買う。売る。",
           "蓄電所マーケットは、系統用蓄電所（できあがった蓄電所、土地と系統の権利）を買いたい会社と売りたい会社をつなぐ場です。"
           "低圧・高圧・特別高圧、完成渡し・権利渡し。登録は無料、社名は面談の日時が決まるまで出ません。運営 サイエンスエックス株式会社。"),
    "en": ("https://dealroom.scix.co.jp/en",
           "BESS projects for sale in Japan | Chikudensho Market",
           "Grid-scale battery storage (BESS) projects for sale in Japan: completed plants and land-and-grid-rights deals. "
           "Buy and sell; prices after free registration."),
}

# 区画: (鍵, 見出し)。頁の振り分けは section_of()。
SECTIONS = [
    ("data", "売り案件の市場データ（Market data: BESS projects for sale in Japan）"),
    ("notes", "月の市場ノートと市場データ（Monthly market notes）"),
    ("market", "蓄電所マーケット・登録なしで見られる案件の一覧（Chikudensho Market: project list without registration, prices after registration）"),
    ("pillar", "柱の頁（Guides and main pages）"),
    ("column", "コラム（Columns）"),
    ("other", "その他（Optional）"),
]
LANG_NAMES = {"ja": "日本語", "en": "English", "zh": "中文"}


def file_of(url):
    p = url[len(BASE):].strip("/")
    for c in ([p + ".html", p + "/index.html"] if p else ["index.html"]):
        if os.path.isfile(os.path.join(ROOT, c)):
            return os.path.join(ROOT, c)
    return None


def head_of(path):
    s = open(path, encoding="utf-8").read()
    s = s[: s.find("</head>")]
    t = re.search(r"<title>(.*?)</title>", s, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', s)
    return (html.unescape(t.group(1)).strip() if t else ""), (html.unescape(d.group(1)).strip() if d else "")


def csv_links(path):
    """頁の中の CSV のダウンロードのリンク（住所・字）を、出てくる順に。字はリンクの字そのまま。"""
    s = open(path, encoding="utf-8").read()
    out = []
    for href, text in re.findall(r'<a [^>]*href="([^"]+\.csv)"[^>]*>(.*?)</a>', s, re.S):
        label = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
        url = href if href.startswith("http") else BASE + href
        if label and url not in [u for u, _ in out]:
            out.append((url, label))
    return out


def lang_of(url):
    p = url[len(BASE):]
    if p == "/en" or p.startswith("/en/"):
        return "en"
    if p == "/zh" or p.startswith("/zh-"):
        return "zh"
    return "ja"


def section_of(url):
    p = url[len(BASE):] or "/"
    if p in ("/en", "/zh"):
        return "pillar"
    bare = re.sub(r"^/(en/|zh-)", "/", p)  # /en/x と /zh-x を /x にそろえる
    if bare in ("/market-data", "/press"):
        return "data"
    if bare == "/research" or bare.startswith("/research/"):
        return "notes"
    if bare == "/projects" or bare.startswith("/projects-"):
        return "market"
    if bare.startswith("/column-"):
        return "column"
    if bare in ("/contact", "/privacy", "/thanks"):
        return "other"
    return "pillar"


def issue_key(url):
    """市場ノートの区画の並び: 入口（/research＝月号の一覧を兼ねる）→ 各号（新しい号を先に）→ 市場データ（/research/data・エリア）。
    同じ段の中は sitemap の順のまま（安定な並べ替え）。"""
    p = re.sub(r"^/(en/|zh-)", "/", url[len(BASE):])
    if p == "/research":
        return (0, 0)
    if p == "/research/flash":                       # 毎日更新の速報は入口の次（2026-11-23・市場の頁は速報と月号の2本）
        return (0, 1)
    m = re.search(r"^/research/(\d{4})-(\d{2})$", p)
    if m:
        return (1, -(int(m.group(1)) * 100 + int(m.group(2))))
    return (2, 0)


def build():
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    urls = []
    for u in re.findall(r"<loc>([^<]+)</loc>", sm):
        if u not in urls:
            urls.append(u)
    groups = {(k, lg): [] for k, _ in SECTIONS for lg in LANG_NAMES}
    for lg, (mu, t, d) in MARKET.items():
        groups[("market", lg)].append((mu, [f"- [{t}]({mu}): {d}"]))
    seen_csv = set()
    for u in urls:
        f = file_of(u)
        if not f:
            continue
        t, d = head_of(f)
        rows = [f"- [{t}]({u})" + (f": {d}" if d else "")]
        sec = section_of(u)
        if sec in ("data", "notes"):
            for cu, label in csv_links(f):
                if cu not in seen_csv:
                    seen_csv.add(cu)
                    rows.append(f"- [{label}]({cu})")
        groups[(sec, lang_of(u))].append((u, rows))
    _, top_d = head_of(os.path.join(ROOT, "index.html"))
    _, en_co_d = head_of(os.path.join(ROOT, "en", "company.html"))
    out = ["# ScienceX（サイエンスエックス株式会社）", "", "> " + top_d, ">", "> " + en_co_d, "",
           "このファイルは、サイトにある頁の題と説明の一覧です（各頁の title と description をそのまま載せています）。"
           "蓄電所マーケットの2行は dealroom.scix.co.jp の頁の title と description、CSV の行は各頁のダウンロードのリンクの字をそのまま載せています。",
           ""]
    for key, name in SECTIONS:
        out.append("## " + name)
        out.append("")
        for lg, lname in LANG_NAMES.items():
            items = groups[(key, lg)]
            if not items:
                continue
            if key == "notes":
                items = sorted(items, key=lambda it: issue_key(it[0]))
            out.append(f"### {lname}")
            out.append("")
            for _, rows in items:
                out.extend(rows)
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else None
        if cur != text:
            print("ずれ: llms.txt")
            return 1
        return 0
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"llms.txt を書いた: {text.count(chr(10) + '- [')} 行（頁・CSV・マーケット）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
