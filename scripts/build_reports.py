#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「蓄電所の市場ノート」（旧名 系統用蓄電池の月報・Drive の _作成物/<YYYYMM>_月報/）から、公開のページを焼く。
2026-11-03 改名（「月報」は他社の名称と紛らわしく、社内用に見えたため）。表に出る語に「月報」「レポート」を使わない。
2026-11-25 住所を /report から /research へ移した（中島「市場レポートは https://www.scix.co.jp/research の URL のほうがいいよね」）。
  /research は入口と月号の一覧を兼ねる1枚（前の手書きの入口の頁 research.html は畳んだ）。古い /report… は vercel.json の 308 で新しい住所へ。

2026-11-01 新設。ただしコラムは代表が書くので、
コラムとは別の「レポート」（毎月の機械発行のデータ月報）として /research と /research/<YYYY-MM> に置く。

読むもの（Drive。リポジトリには置かない）:
  ~/マイドライブ/9_システム/_作成物/<YYYYMM>_月報/蓄電所の市場ノート_<YYYY-MM>.md と .pdf
  図: ~/.openclaw/workspace/build/*月報*/<YYYYMM>/figs/f1.png〜（monthly_report_figs.py の出力）。
      無ければ PDF の各ページを画像にして載せる。
英語版（2026-11-02〜）: 同じフォルダの 蓄電所の市場ノート_<YYYY-MM>_en.md と _en.pdf、図は build/*月報*/<YYYYMM>/figs_en/（bin/monthly_report.py build-en が作る）が
  そろった月だけ en/research/<YYYY-MM>/index.html と en/research/index.html を焼く（図Nのファイルは f<N>.png。図の番号→ファイルは FIG_FILE）。
  日本語のページとは hreflang で相互に結ぶ（sitemap.xml も）。
生成するもの（全文を書き直す。手で直さない）:
  research/index.html                 月報の一覧（新しい月が上）
  research/<YYYY-MM>/index.html       各月のページ（今月の動き3つ・図・PDF・出典と試算の前提・引用の案内）
  research/<YYYY-MM>/f1.png …, scix-bess-monthly-<YYYY-MM>.pdf
  en/research/index.html, en/research/<YYYY-MM>/index.html, f1.png〜, scix-bess-monthly-<YYYY-MM>-en.pdf（英語版）
  sitemap.xml                       /research と各月の行（無ければ足す。英語版があれば hreflang の相互の行も）
  research/latest.json                最新号の要点（号・URL・今月の動きのうち需給調整市場と卸電気の1文ずつ・対象の月）。
                                    header.js が記事（需給調整市場・卸電気・容量市場）に「最新の数字」の札を出すのに読む（2026-11-21）。
                                    中身は号の頁（説明文・今月の動き3つ）に出している文だけで、新しい数字は作らない。
  research/data/, en/research/data/, research/area/<slug>/   号をまたいだ推移の頁と CSV（scripts/build_report_data.py。号と同じ md の表から）
2026-11-21（読まれやすくする第1段）:
  号の頁に「この号の数字の読み方」（関係する記事への段＝READING）を足し、SNS の画像（og:image）を号の図（OG_FIG・大きさと縦横比が合う物だけ）に。
  sitemap の lastmod は、焼き直して頁の中身が変わった日（変わらなければ前の値か発行日の新しいほう）にする。

置く前の検査（公開リポジトリ）: MD と PDF の文字に、住所・地番・案件ID・価格類（仕入値・売値・土地代）・
売主・成約実績の語が1つでもあれば、何も書かずに終了コード 2 で止まる。図の PNG は文字を持たないので、
図の中身は MD の図の説明文（図N …）で見る。

使い方:
    python3 scripts/build_reports.py            # 書き換えて差分を報告
    python3 scripts/build_reports.py --check    # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
毎朝の同期（scripts/sync_projects_json.sh）の末尾から呼ぶ（月報が出た月に1回だけ差分が出る）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import glob
import html
import json
import os
import struct
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def modified_of(path, issued, text=None):
    """頁の dateModified＝sitemap の lastmod。発行日と、sitemap の今の値（頁を変えた日に stamp_sitemap.py が進める）の新しいほう。
    頁の JSON-LD と sitemap の2か所に同じ値を書き、焼き直しで値を戻さない（lastmod は前の値より古くしない＝O16-57）。"""
    if text is None:
        try:
            text = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
        except OSError:
            return issued
    mt = re.search(r"<url><loc>" + re.escape(BASE + path) + r"</loc>.*?<lastmod>([0-9-]{10})</lastmod>", text)
    return max(issued, mt.group(1)) if mt else issued
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_market_data as bmd  # noqa: E402  head / FOOTER / CSS / ld / crumbs / nav_crumbs / ORG を共用する
import build_report_data as brd  # noqa: E402  市場データ（/research/data）とエリアの頁（/research/area/<slug>）

HOME = os.path.expanduser("~")
SRC = os.environ.get("SCIX_REPORT_SRC", os.path.join(HOME, "マイドライブ", "9_システム", "_作成物"))
FIGS = os.environ.get("SCIX_REPORT_FIGS", os.path.join(HOME, ".openclaw", "workspace", "build"))
BASE = bmd.BASE
DR2_REGISTER = "https://dealroom.scix.co.jp/register"
DR2_REGISTER_EN = "https://dealroom.scix.co.jp/en/register"
# 図N → 図のファイル（bin/monthly_report.py の FIG_FILE と同じ。月報の節の並び）
FIG_FILE = {1: "f9", 2: "f15", 3: "f18", 4: "f16", 5: "f13", 6: "f14", 7: "f5", 8: "f17", 9: "f1", 10: "f2", 11: "f12", 12: "f3", 13: "f10", 14: "f6", 15: "f7"}   # bin/monthly_report.py の FIG_FILE と同じ（2026-11-05 の並び: 3つの稼ぎ口→①需給調整→②卸電気→③容量→当社の記録。2026-11-05 に図7＝管区ごとの約定率 f18 を足した）
NAME, NAME_EN = "蓄電所の市場ノート", "Battery Storage Market Notes"
HOME_FIG = "f16"          # トップの札に出す図（一次調整力の席の取り合い）
# 号の頁の SNS 用の画像（og:image）。号ごとに数字の変わる図を、トップの札と同じ図から先に選ぶ。図1（3つの稼ぎ口の模式図）は
# 毎号同じなので使わない。大きさと縦横比（1.91:1 に近い）が合わなければ次の図、どれも合わなければ今の共通の1枚のまま。
OG_MIN_W, OG_RATIO = 1200, (1.6, 2.1)
# 「この号の数字の読み方」＝号の頁から、数字の意味を説明している記事へ（2026-11-21）。記事の題は記事の <title> から読む
# （無い記事・英語版の無い記事は出さない＝JA 専用の記事は英語の頁に出ない）。
READING = [
    (("①需給調整市場（EPRX）", "① Balancing market (EPRX)"),
     ["balancing-market", "eprx", "area-data", "price-cap", "balancing-saturation"]),
    (("②卸電気（JEPX）と、3つの稼ぎ方の組み合わせ", "② Wholesale power (JEPX) and stacking the three"),
     ["revenue", "regional-revenue", "merchant"]),
    (("③容量市場（OCCTO）", "③ Capacity market (OCCTO)"),
     ["capacity-market", "auction"]),
    (("当社の記録（系統につなぐ期間と費用）", "Our records (connecting to the grid)"),
     ["study-reply-4", "grid"]),
]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
EN_ORG = {"@type": "Organization", "@id": bmd.BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": bmd.BASE + "/en"}
# publisher には、会社と同じ @id・名前に、紺のロゴ（画面の img のロゴとは別。構造化データのロゴは白地で読める紺の版＝2026-11-22 中島「Seo 対策も徹底してやって」）
_LOGO = {"@type": "ImageObject", "url": bmd.BASE + "/img/logo-navy.png"}
PUBLISHER = {**bmd.ORG, "logo": _LOGO}
EN_PUBLISHER = {**EN_ORG, "logo": _LOGO}

# 公開してはいけない語。「円」「価格」は卸電気の価格や試算で正当に出るので語としては禁じない。
FORBIDDEN = [
    (r"[都道府県][^\s、。]{0,8}?[市区町村郡][^\s、。]{0,12}?\d+\s*[-－ー番]\s*\d*", "住所らしい並び"),
    (r"地番|番地|丁目|緯度|経度|〒|登記", "住所・地番の語"),
    (r"\b(?:SHV|HV|UR|GT)-\d+", "案件ID"),
    (r"仕入|売主|売値|販売価格|希望価格|土地代|工事費負担金の額|元付", "価格類・関係者の語"),
    (r"成約|取扱高|取引実績|買取実績", "実績の語（O16-7）"),
    (r"[\w.+-]+@(?!scix\.co\.jp)[\w-]+\.[\w.]+", "scix 以外のメールアドレス"),
    (r"(?:https?://)?(?:\S*\.)?(?:drive|docs)\.google\.com\S*", "Drive のリンク"),
]


# 英語の月報の安全の検査（案件 ID・メール・Drive のリンクは日本語と同じ正規表現）。英語の語を足す。
FORBIDDEN_EN = [f for f in FORBIDDEN if f[1] in ("案件ID", "scix 以外のメールアドレス", "Drive のリンク")] + [
    (r"(?i)\b(?:sellers?|purchase price|acquisition price|land price|closed deals|track record)\b", "価格類・関係者・実績の英語の語（O16-19・O16-7）"),
]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- 入力
def find_months():
    out = []
    for d in sorted(glob.glob(os.path.join(SRC, "[0-9][0-9][0-9][0-9][0-9][0-9]_月報"))):
        ym = os.path.basename(d)[:6]
        key = f"{ym[:4]}-{ym[4:]}"
        md = os.path.join(d, f"{NAME}_{key}.md")
        pdf = os.path.join(d, f"{NAME}_{key}.pdf")
        if os.path.isfile(md) and os.path.isfile(pdf):
            m = {"ym": ym, "key": key, "md": md, "pdf": pdf, "en_md": None, "en_pdf": None}
            em, ep = os.path.join(d, f"{NAME}_{key}_en.md"), os.path.join(d, f"{NAME}_{key}_en.pdf")
            if os.path.isfile(em) and os.path.isfile(ep) and fig_sources(m, "figs_en"):
                m["en_md"], m["en_pdf"] = em, ep
            out.append(m)
    return sorted(out, key=lambda m: m["key"], reverse=True)


def pdf_text(pdf):
    try:
        return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"NG PDF の文字を取れない（pdftotext）: {pdf}: {e}")


def safety_scan(m, md_text, pdf_txt, lang="ja"):
    hits = []
    for label, text in (("md", md_text), ("pdf", pdf_txt)):
        for pat, why in (FORBIDDEN if lang == "ja" else FORBIDDEN_EN):
            for mt in re.finditer(pat, text):
                hits.append(f"{m['key']} {lang} {label}: {why}: 「{mt.group(0)[:40]}」")
    return hits


def parse_md(text, lang="ja"):
    """MD を { title, issued, intro, sections:[{title, items:[(kind, text)]}], footer } にする。lang=en は英語版（Published … / (Figure N …)）。"""
    if lang == "ja":
        text = text.replace("最終ページ", "末尾の「前提と用語」")  # PDF では最終ページ・Web では末尾の節
    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    issued = ""
    if lang == "ja":
        mt = re.search(r"発行\s*(\d{4})年(\d{1,2})月(\d{1,2})日", text)
        if mt:
            issued = f"{mt.group(1)}-{int(mt.group(2)):02d}-{int(mt.group(3)):02d}"
    else:
        mt = re.search(r"Published\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})", text)
        if mt and mt.group(1) in MONTHS_EN:
            issued = f"{mt.group(3)}-{MONTHS_EN.index(mt.group(1)) + 1:02d}-{int(mt.group(2)):02d}"
    body = text.split("\n---\n")[0]
    footer = text.split("\n---\n")[1] if "\n---\n" in text else ""
    sections, cur, intro = [], None, []
    for l in body.splitlines():
        s = l.strip()
        if not s or s.startswith("<!--") or s.startswith("# "):
            continue
        if re.match(r"サイエンスエックス株式会社　発行", s) or re.match(r"Science X Inc\.\s+Published", s):
            continue
        if s.startswith("## "):
            cur = {"title": re.sub(r"^\d+\.\s*", "", s[3:].strip()), "num": (re.match(r"^## (\d+)\.", s) or [None, ""])[1], "items": []}
            sections.append(cur)
        elif cur is None:
            intro.append(s)
        else:
            if s.startswith("|"):                       # 表（2026-11-03〜 5節の積み上げ・10節の市場の数字）
                cells = [c.strip() for c in s.strip("|").split("|")]
                if set("".join(cells)) <= set("-: "):
                    continue
                if cur["items"] and cur["items"][-1][0] == "table":
                    cur["items"][-1][1].append(cells)
                else:
                    cur["items"].append(("table", [cells]))
            elif s.startswith("- "):
                cur["items"].append(("li", s[2:].strip()))
            elif re.match(r"^（図\d+", s):
                cur["items"].append(("fig", s[1:-1] if s.endswith("）") else s[1:]))
            elif re.match(r"^\(Figure \d+", s):
                cur["items"].append(("fig", s[1:-1] if s.endswith(")") else s[1:]))
            else:
                cur["items"].append(("p", s))
    nl = re.search(r"https://www\.linkedin\.com/newsletters/\d+/?", footer)
    return {"title": title, "issued": issued, "intro": " ".join(intro), "sections": sections,
            "newsletter": nl.group(0) if nl else ""}


def jp_date(iso):
    y, m, d = iso.split("-")
    return f"{y}年{int(m)}月{int(d)}日"


# ---------------------------------------------------------------- 図
def fig_sources(m, sub="figs"):
    """図 f1..fN の PNG パスの dict。無ければ空。sub=figs_en は英語の図（ファイル番号で返す）。"""
    for d in glob.glob(os.path.join(FIGS, "*月報*", m["ym"], sub)):
        got = {}
        for p in glob.glob(os.path.join(d, "f*.png")):
            mt = re.match(r"f(\d+)\.png$", os.path.basename(p))
            if mt:
                got[int(mt.group(1))] = p
        if got:
            return got
    return {}


def en_fig_by_number(files):
    """英語の図（ファイル番号 → パス）を、図の番号 → パスにする（図4 は f9.png など）。"""
    return {n: files[k] for n, k in ((n, int(f[1:])) for n, f in FIG_FILE.items()) if k in files}


def render_pdf_pages(pdf, tmp):
    base = os.path.join(tmp, "p")
    subprocess.run(["pdftoppm", "-r", "100", "-png", pdf, base], check=True, timeout=180)
    pages = sorted(glob.glob(base + "-*.png"))
    return {i + 1: p for i, p in enumerate(pages)}


def png_size(p):
    """PNG の幅と高さ（IHDR）。読めなければ (0, 0)。"""
    try:
        with open(p, "rb") as f:
            b = f.read(24)
        if b[:8] != b"\x89PNG\r\n\x1a\n":
            return 0, 0
        return struct.unpack(">II", b[16:24])
    except OSError:
        return 0, 0


def pick_og(figs):
    """号の SNS 用の画像にする図の番号（figs＝図の番号 → パス）。合う物が無ければ None（共通の1枚のまま）。"""
    home_n = next((n for n, f in FIG_FILE.items() if f == HOME_FIG), None)
    order = ([home_n] if home_n in figs else []) + [n for n in sorted(figs) if n not in (home_n, 1)]
    for n in order:
        w, h = png_size(figs[n])
        if w >= OG_MIN_W and h and OG_RATIO[0] <= w / h <= OG_RATIO[1]:
            return n, w, h
    return None


def put_og(head_html, url, w, h):
    """head の og:image / twitter:image を号の図に替え、大きさの行を足す（共通の1枚の行が無ければ何もしない）。"""
    out = re.sub(r'(<meta property="og:image" content=")[^"]*(">)', lambda mt: mt.group(1) + url + mt.group(2)
                 + f'\n<meta property="og:image:width" content="{w}">\n<meta property="og:image:height" content="{h}">', head_html, count=1)
    return re.sub(r'(<meta name="twitter:image" content=")[^"]*(">)', lambda mt: mt.group(1) + url + mt.group(2), out, count=1)


def column_title(rel, lang):
    """記事の題（<title> から「｜サイエンスエックス」などを外した物）。ファイルが無ければ ""。"""
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return ""
    mt = re.search(r"<title>([^<]+)</title>", open(p, encoding="utf-8").read())
    if not mt:
        return ""
    t = html.unescape(mt.group(1)).strip()
    t = re.sub(r"\s*[｜|]\s*(?:サイエンスエックス|ScienceX)(?:\s*ナレッジ)?\s*$", "", t)
    return t.strip()


def reading_section(lang="ja"):
    """「この号の数字の読み方」の段（記事への短いリンクの一覧だけ。説明の文は足さない）。"""
    groups = []
    for (h_ja, h_en), slugs in READING:
        links = []
        for s in slugs:
            rel, href = (f"column-{s}.html", f"/column-{s}") if lang == "ja" else (f"en/column-{s}.html", f"/en/column-{s}")
            t = column_title(rel, lang)
            if t:
                links.append(f'<li><a href="{href}">{esc(t)}</a></li>')
        if links:
            groups.append(f'<div class="rp-read-g"><div class="rp-read-h">{esc(h_ja if lang == "ja" else h_en)}</div><ul>{"".join(links)}</ul></div>')
    if not groups:
        return ""
    h2 = "この号の数字の読み方" if lang == "ja" else "How to read the numbers in this issue"
    return (f'<section class="md" id="reading"><div class="container rp-body">\n  <h2 class="md-h">{h2}</h2>\n'
            f'  <div class="rp-read">{"".join(groups)}</div>\n</div></section>')


# 号をまたいだ推移の頁（build_report_data.py が焼く）への入口。焼いた頁だけ出す（DATA_PAGES は main が決める）。
DATA_PAGES = set()
DATA_CSVS = set()   # 焼いた CSV（号の頁の Dataset の distribution に結ぶ・2026-11-22）
CSV_NAMES = {"jepx-spot-monthly.csv": ("卸電気（JEPX）の月ごとの数字（号をまたいだ CSV）", "JEPX spot prices by month (CSV across issues)"),
             "capacity-main-auction.csv": ("容量市場メインオークションのエリアプライス（CSV）", "Capacity market main auction area prices (CSV)"),
             "long-term-decarbonization-auction.csv": ("長期脱炭素電源オークションの約定容量（CSV）", "Long-Term Decarbonization Power Source Auction results (CSV)"),
             "eprx-monthly.csv": ("需給調整市場（EPRX）の月ごとの数字（CSV）", "EPRX balancing market by month (CSV)")}


def issue_dataset(path, title_h, desc, issued, modified, lang, pdf_url):
    """号の頁の Dataset（2026-11-22・Gemini の助言 指令2）。この号の PDF と、号をまたいだ推移の CSV（/research/data・焼いた物だけ）へ結ぶ。
    license は付けない（利用条件を名乗るかは中島さんの決め）。数字は号の本文のまま・新しい数字は作らない。"""
    J = lang == "ja"
    pre = "research/data/" if J else "en/research/data/"
    csvs = sorted(k for k in DATA_CSVS if k.startswith(pre))
    dist = [{"@type": "DataDownload", "encodingFormat": "application/pdf", "contentUrl": pdf_url, "name": "この号の PDF" if J else "This issue (PDF)"}]
    dist += [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}/{k}",
              "name": CSV_NAMES.get(os.path.basename(k), (os.path.basename(k),) * 2)[0 if J else 1]} for k in csvs]
    return {"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset", "url": BASE + path,
            "name": f"{title_h}の数字" if J else f"{title_h}: figures",
            "description": ((f"{title_h}に載せた、蓄電所の3つの稼ぎ口（需給調整市場 EPRX・卸電気 JEPX・容量市場 OCCTO）の数字と当社の記録の集計（図表・PDF）。"
                             "数字は公表データの表示どおりで、出典は号の本文に書いた。号をまたいだ推移の CSV は市場データ（/research/data）。") if J else
                            (f"The figures in {title_h}: the three income streams of a battery storage site (EPRX balancing market, JEPX wholesale power, "
                             "OCCTO capacity market) and our own records, as charts, tables and a PDF. Sources are given in the issue. "
                             "CSV files across issues are on the market data page (/en/research/data).")),
            "inLanguage": lang, "creator": bmd.ORG if J else EN_ORG, "publisher": PUBLISHER if J else EN_PUBLISHER,
            "isAccessibleForFree": True, "datePublished": issued, "dateModified": modified,
            "spatialCoverage": {"@type": "Place", "name": "日本" if J else "Japan"},
            "creditText": (f"出典: サイエンスエックス株式会社『{title_h}』{BASE}{path}" if J else f"Source: Science X Inc., \u201c{title_h}\u201d, {BASE}{path}"),
            "distribution": dist, "mainEntityOfPage": BASE + path}
DATA_LINKS = {
    "ja": [("/research/data", "市場データ（号をまたいだ推移）", "卸電気（JEPX）の月ごとの平均と4時間の値差、容量市場のエリアプライスを、エリア別に号をまたいで並べました。CSV もあります。"),
           ("/research/area/tokyo", "東京エリアの市場データ", "東京エリアの卸電気の月ごとの推移と容量市場の約定価格、エリアの公開案件の件数。"),
           ("/research/area/kyushu", "九州エリアの市場データ", "九州エリアの卸電気の月ごとの推移と容量市場の約定価格、エリアの公開案件の件数。")],
    "en": [("/en/research/data", "Market Data: JEPX spot and capacity prices across issues",
            "Monthly JEPX averages and 4-hour spreads by area, and capacity market area prices, laid out across issues. CSV downloads included.")],
}


def flash_section(lang="ja"):
    """一覧の頁の頭の、毎日更新の速報（/research/flash・scripts/build_flash.py）への入口。速報の頁が焼かれていなければ空（2026-11-23）。"""
    rel = "research/flash/index.html" if lang == "ja" else "en/research/flash/index.html"
    if not os.path.exists(os.path.join(ROOT, rel)):
        return ""
    if lang == "ja":
        h2, body = "毎日の数字は「速報」で", ('卸電気（JEPX）と需給調整市場（EPRX）の今月ここまでの数字・最新の1日の数字・前の月との比べは、公表された最新のデータを毎朝取り直す'
                                            '<a href="/research/flash">蓄電所の市場ノート 速報</a>に載せています（毎日更新）。月の号は、前の月の全日の数字です。')
    else:
        h2, body = "Daily figures: the Daily Flash", ('This month so far, the latest day and the comparison with last month for JEPX wholesale and the EPRX balancing market are on the '
                                                   '<a href="/en/research/flash">Daily Flash</a>, re-fetched from the latest published data every morning. Each monthly issue covers the whole previous month.')
    return (f'<section class="md" id="flash"><div class="container rp-body">\n  <h2 class="md-h">{h2}</h2>\n'
            f'  <p>{body}</p>\n</div></section>')


def data_section(lang="ja"):
    """市場データ（号をまたいだ推移）とエリアの頁への入口の段（一覧の頁と各号の頁）。頁が焼かれていなければ空。"""
    items = [(h, t, d) for h, t, d in DATA_LINKS[lang] if h.lstrip("/") + "/index.html" in DATA_PAGES]
    if not items:
        return ""
    li = "".join(f'<li><a class="t" href="{h}">{esc(t)}</a><p>{esc(d)}</p></li>' for h, t, d in items)
    h2 = "号をまたいだ数字" if lang == "ja" else "Figures across issues"
    return (f'<section class="md" id="data"><div class="container rp-body">\n  <h2 class="md-h">{h2}</h2>\n'
            f'  <ul class="rp-list">{li}</ul>\n</div></section>')


def latest_json(m, doc, md_text, en_doc=None, en_md=""):
    """research/latest.json の中身。号の頁の「今月の動き3つ」の文をそのまま入れる（言い直さない・数字を作らない）。"""
    def pick(d, src, eprx_re, jepx_re, month_re, text):
        s1 = moves_sec(d)
        moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith(src)]
        eprx = next((t for t in moves if re.search(eprx_re, t)), "")
        jepx = next((t for t in moves if re.search(jepx_re, t)), "")
        mt = re.search(month_re, text)
        return {"eprx": eprx, "jepx": jepx, "eprx_month": mt.group(1) if mt else ""}, moves
    y, mo = m["key"].split("-")
    ja, _ = pick(doc, "出典:", r"需給調整市場（EPRX）.*応札倍率", r"卸電気（JEPX）",
                 r"対象の月: 需給調整市場（EPRX）は\s*(\d{4}年\d{1,2}月)", md_text)
    out = {"key": m["key"], "issued": doc["issued"], "title": f"{NAME} {y}年{int(mo)}月号", "url": f"/research/{m['key']}", **ja}
    if en_doc:
        en, _ = pick(en_doc, "Source", r"balancing market \(EPRX\).*bid ratio", r"wholesale (?:electricity|power) \(JEPX\)",
                     r"balancing market \(EPRX\) uses preliminary values for ([A-Z][a-z]+ \d{4})", en_md)
        out["en"] = {"title": en_doc["title"], "url": f"/en/research/{m['key']}", **en}
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


# ---------------------------------------------------------------- ページ
EXTRA_CSS = """
.rp-list{list-style:none;padding:0;margin:0;border-top:1px solid var(--border);max-width:900px}
.rp-list li{padding:18px 0;border-bottom:1px solid var(--border)}
.rp-list a.t{font-size:1.1rem;font-weight:700;color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.rp-list .d{font-size:.84rem;color:var(--text-3);margin:4px 0}
.rp-list p{font-size:.92rem;line-height:1.85;color:var(--text-2);margin:6px 0 0}
.rp-fig{margin:18px 0 6px;max-width:860px}.rp-fig img{display:block;width:100%;height:auto;border:1px solid var(--border);border-radius:6px;background:#fff}
.rp-fig figcaption{font-size:.84rem;color:var(--text-2);margin-top:6px}
.rp-body{max-width:860px}.rp-body p{line-height:1.95;margin:10px 0}.rp-body ul{padding-left:1.3em;line-height:1.9;margin:10px 0}
.rp-body li{margin:4px 0}
.rp-three{border:1px solid var(--border);border-left:4px solid var(--gold);border-radius:8px;padding:6px 20px 10px;background:var(--off-white);max-width:860px}
.rp-three li{margin:10px 0;line-height:1.9}
.rp-btns{margin-top:18px}.rp-btns a{margin:4px 10px 4px 0}
.rp-page{max-width:860px;display:flex;flex-direction:column;gap:14px}
.rp-table{overflow-x:auto;margin:14px 0 6px;max-width:860px}
.rp-table table{border-collapse:collapse;width:max-content;min-width:100%;font-size:.84rem;line-height:1.5}
.rp-table th{background:var(--navy);color:#fff;font-weight:700;text-align:left;padding:7px 9px;vertical-align:bottom;min-width:5.5em;max-width:13em}
.rp-table td{border-bottom:1px solid var(--border);padding:6px 9px;color:var(--text-2);white-space:nowrap}
.rp-table td.rp-n{text-align:right;font-variant-numeric:tabular-nums}
.rp-table tbody tr:nth-child(even){background:var(--off-white)}
.rp-nav{margin-top:14px;font-size:.86rem}.rp-nav a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}.rp-nav-sep{margin:0 10px;color:var(--text-3)}
"""
# 「この号の数字の読み方」の段と、長い URL（前提と用語の出典）の折り返し（号の頁だけ。一覧の頁の head は変えない）。
# 折り返しが無いと、スマホの幅で「前提と用語」の OCCTO の PDF の URL が文書の幅を 835px に広げていた（2026-11-21 実測）。
READ_CSS = """
.rp-body p,.rp-body li,.rp-body .md-note{overflow-wrap:anywhere}
.rp-read{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:14px}
.rp-read-g{background:#fff;border:1px solid var(--border);border-top:4px solid #138A62;border-radius:16px;padding:14px 18px 10px}
.rp-read-h{font-weight:800;color:var(--navy);font-size:.92rem;margin-bottom:6px}
.rp-read-g ul{list-style:none;padding:0;margin:0}.rp-read-g li{margin:0;padding:7px 0;border-top:1px solid var(--border);line-height:1.6;font-size:.88rem}
.rp-read-g li:first-child{border-top:0}.rp-read-g a{color:var(--navy);text-decoration:none;font-weight:600}.rp-read-g a:hover{text-decoration:underline}
"""

SEC_MORE = {"1": "three"}
MOVES_RE = re.compile(r"今月の動き|(?:Three|3) (?:trends|things|moves|movements)", re.I)   # 「今月の動き3つ」の節


def moves_sec(doc):
    return next((s for s in doc["sections"] if MOVES_RE.search(s["title"])), None)


def page_head(title, desc, path, jsonld, en_path=None):
    """日本語ページの head。英語版があれば hreflang="en" の行を足す（ほかは変えない）。"""
    h = bmd.head(title, desc, path, jsonld)
    if en_path:
        ja = f'<link rel="alternate" hreflang="ja" href="{BASE}{path}">'
        assert ja in h
        h = h.replace(ja, ja + f'\n<link rel="alternate" hreflang="en" href="{BASE}{en_path}">', 1)
    return h.replace("</style>", EXTRA_CSS + "</style>", 1)


def page_head_en(title, desc, path, jsonld, ja_path):
    """英語ページの head（render_en_projects と同じ置き換え。日本語のページと hreflang で相互に結ぶ）。"""
    url = BASE + path
    h = (bmd.head(title, desc, path, jsonld)
         .replace('<html lang="ja">', '<html lang="en">')
         .replace(f'<link rel="alternate" hreflang="ja" href="{url}">',
                  f'<link rel="alternate" hreflang="en" href="{url}">\n<link rel="alternate" hreflang="ja" href="{BASE}{ja_path}">')
         .replace('content="ja_JP"', 'content="en_US"')
         .replace(f"{BASE}/img/ogp-m.png", f"{BASE}/img/ogp-m-en.png"))
    return h.replace("</style>", EXTRA_CSS + "</style>", 1)


def en_date(iso):
    y, m, d = iso.split("-")
    return f"{MONTHS_EN[int(m) - 1]} {int(d)}, {y}"


def img_dims(path):
    """PNG の幅と高さ（IHDR）を width・height の属性にする（読み込みの前に場所を確保＝CLS を出さない）。読めなければ空。"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            return f' width="{int.from_bytes(head[16:20], "big")}" height="{int.from_bytes(head[20:24], "big")}"'
    except (OSError, TypeError):
        pass
    return ""


PARTIAL_RE = {"ja": re.compile(r"^(\d{4})年(\d{1,2})月の途中経過"), "en": re.compile(r"^([A-Z][a-z]+ \d{4}) so far")}
PARTIAL_ROW = re.compile(r"（月の途中）|\(partway through the month\)")
PARTIAL_NOTE = re.compile(r"の途中経過の節は|section shows preliminary figures from partway through the month")


def move_partial(doc, lang="ja"):
    """号の中の「（発行する月）の途中経過」の節を、毎日更新の速報（/research/flash）への案内に置き換える（2026-11-23 中島「毎日最新データを落として速報。
    毎月１日に先月のデータを落として月報」＝月の号に当月の途中の数字は入れない）。節の番号は残す（本文の「3節」などの指し先を変えない）。
    あわせて「この号のデータの時点」の表の月の途中の行と、前提と用語の途中経過の注を外す。前の月の数字の節は1字も変えない。返り: 置き換えたか。"""
    hit = False
    for sec in doc["sections"]:
        m = PARTIAL_RE[lang].match(sec["title"])
        if not m:
            continue
        hit = True
        if lang == "ja":
            mon = f"{m.group(1)}年{int(m.group(2))}月"
            sec["title"] = f"{mon}の途中経過は「速報」へ移しました"
            sec["items"] = [("html", f'<p>{esc(mon)}の途中の数字（今月ここまで・最新の1日・前の月との比べ・週ごと）は、公表された最新のデータを毎朝取り直す'
                                     f'<a href="/research/flash">蓄電所の市場ノート 速報</a>に載せています。この号は前の月の全日の数字です。</p>')]
        else:
            mon = m.group(1)
            sec["title"] = f"{mon} so far: moved to the Daily Flash"
            sec["items"] = [("html", f'<p>Figures for {esc(mon)} so far (this month to date, the latest day, comparison with last month and by week) are on the '
                                     f'<a href="/en/research/flash">Daily Flash</a>, re-fetched from the latest published data every morning. This issue covers the whole previous month.</p>')]
    if not hit:
        return False
    for sec in doc["sections"]:
        items = []
        for kind, txt in sec["items"]:
            if kind == "p":                              # 「…の途中の数字は、次の節に載せました。」→ 速報を指す（次の節にはもう数字が無い＝2026-11-23 別の目①）
                txt = re.sub(r"(\d{4}年\d{1,2}月)の途中の数字は、次の節に載せました。", r"\1の途中の数字は、毎日更新の速報に移しました。", txt)
                txt = re.sub(r"Figures for part of ([A-Z][a-z]+ \d{4}) are in the next section\.", r"Figures for part of \1 have moved to the Daily Flash.", txt)
            if kind == "table":
                txt = [r for i, r in enumerate(txt) if i == 0 or not PARTIAL_ROW.search(r[0])]
            elif kind == "li" and PARTIAL_NOTE.search(txt):
                continue
            items.append((kind, txt))
        sec["items"] = items
    return True


def render_section(sec, figs, month_key, used, lang="ja"):
    src_pre = "出典:" if lang == "ja" else "Source"
    base = "/research" if lang == "ja" else "/en/research"
    out = [f'<section class="md" id="s{sec["num"] or ""}"><div class="container rp-body">']
    if sec["num"]:
        out.append(f'<div class="section-label">{sec["num"].zfill(2)}</div>')
    out.append(f'<h2 class="md-h">{esc(sec["title"])}</h2>')
    items, i = sec["items"], 0
    first = bool(MOVES_RE.search(sec["title"]))
    prev_fig = False
    while i < len(items):
        kind, txt = items[i]
        if kind == "p":
            out.append(f"<p>{esc(txt)}</p>")
            prev_fig = False
        elif kind == "li":
            if txt.startswith(src_pre) and prev_fig:
                out.append(f'<p class="md-note">{esc(txt)}</p>')
            else:
                j = i
                lis = []
                while j < len(items) and items[j][0] == "li" and not (items[j][1].startswith(src_pre) and prev_fig):
                    lis.append(items[j][1]); j += 1
                cls = ' class="rp-three"' if first and lis else ""
                out.append(f"<ul{cls}>" + "".join(f"<li>{esc(t)}</li>" for t in lis) + "</ul>")
                i = j - 1
            prev_fig = False
        elif kind == "table":
            head, *body_rows = txt
            num = re.compile(r"^[-−—\d,.%]+$")
            out.append('<div class="rp-table"><table><thead><tr>' + "".join(f"<th>{esc(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f'<td{" class=rp-n" if j and num.match(c) else ""}>{esc(c)}</td>' for j, c in enumerate(r)) + "</tr>" for r in body_rows)
                       + "</tbody></table></div>")
            prev_fig = False
        elif kind == "html":                           # move_partial が置く速報への案内（中身は決まった文だけ）
            out.append(txt)
            prev_fig = False
        elif kind == "fig":
            n = int(re.match(r"(?:図|Figure )(\d+)", txt).group(1))
            src = figs.get(n)
            if src:
                used.add(n)
                out.append(f'<figure class="rp-fig"><img src="{base}/{month_key}/f{n}.png"{img_dims(src)} alt="{esc(txt)}" loading="lazy">'
                           f"<figcaption>{esc(txt)}</figcaption></figure>")
            prev_fig = True
        i += 1
    out.append("</div></section>")
    return "\n".join(out)


def issue_nav(nav, lang="ja"):
    """前の号・次の号のリンク（nav=(古い月, 新しい月)。無い側は出さない）。2026-11-05 バックナンバー（4月〜）を足したとき。"""
    older, newer = nav or (None, None)
    if not older and not newer:
        return ""
    def name(k):
        y, mo = k.split("-")
        return f"{y}年{int(mo)}月号" if lang == "ja" else f"{MONTHS_EN[int(mo) - 1]} {y}"
    base = "/research" if lang == "ja" else "/en/research"
    parts = []
    if older:
        parts.append(f'<a href="{base}/{older}" rel="prev">← {"前の号" if lang == "ja" else "Previous"}: {esc(name(older))}</a>')
    if newer:
        parts.append(f'<a href="{base}/{newer}" rel="next">{"次の号" if lang == "ja" else "Next"}: {esc(name(newer))} →</a>')
    sep = "｜" if lang == "ja" else "|"   # 英語の号は半角の縦線（全角の「｜」は日本語の約物）
    return '<p class="rp-nav">' + f'<span class="rp-nav-sep">{sep}</span>'.join(parts) + "</p>"


def render_month(m, doc, figs, page_imgs, has_en=False, nav=None):
    key = m["key"]
    y, mo = key.split("-")
    path = f"/research/{key}"
    title_h = f"{NAME} {y}年{int(mo)}月号"
    title = f"{title_h}｜需給調整市場・卸電気の価格・容量市場・接続検討｜サイエンスエックス"
    s1 = moves_sec(doc)
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("出典:")]
    desc = (f"{title_h}。" + (moves[0] if moves else doc["intro"]))[:160]
    pdf_name = f"scix-bess-monthly-{key}.pdf"
    mod = modified_of(path, doc["issued"])
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "Report", "@id": BASE + path + "#report", "url": BASE + path,
                "name": title_h, "description": desc, "inLanguage": "ja", "datePublished": doc["issued"],
                "dateModified": mod, "author": bmd.ORG, "publisher": PUBLISHER,
                "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{path}/{pdf_name}", "encodingFormat": "application/pdf"}}),
        bmd.ld(issue_dataset(path, title_h, desc, doc["issued"], mod, "ja", f"{BASE}{path}/{pdf_name}")),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + "/research"), (title_h, BASE + path)])),
    ])
    used = set()
    secs = [render_section(s, figs, key, used) for s in doc["sections"]]
    gallery = ""
    if not figs and page_imgs:
        gallery = ('<section class="md"><div class="container rp-body"><h2 class="md-h">PDF の各ページ</h2>'
                   + "".join(f'<figure class="rp-fig"><img src="/research/{key}/p{n}.png"{img_dims(page_imgs[n])} alt="{NAME} {y}年{int(mo)}月号 {n}ページ" loading="lazy"></figure>'
                             for n in sorted(page_imgs)) + "</div></section>")
    nl = (f'<p>毎月の更新は、LinkedIn のニュースレター「系統用蓄電池の一次データ」でもお届けしています。'
          f'<a href="{esc(doc["newsletter"])}" rel="noopener" target="_blank">ニュースレターを購読する →</a></p>') if doc["newsletter"] else ""
    cite = f"""<section class="md"><div class="container rp-body">
  {bmd.cite_html("ja", title_h, BASE + path, mod,
                 '<p>数字は公表データと当社の記録の集計です。値差は1kWh あたりの価格の差で、実際の収益を示すものではありません。集計のしかたは上の「前提と用語」に書きました。'
                 '号をまたいだ推移は <a href="/research/data">市場データ</a>（CSV あり）に、転載の決まりは <a href="/press">引用・転載ガイド</a> に。</p>')}
  {nl}
</div></section>"""
    cta = """<section class="cta"><div class="container">
  <h2>このノートの数字の元になった案件を、買い手の方へ</h2>
  <p>当社の蓄電所マーケットでは、今ある案件を登録なしでご覧いただけます。価格と資料は、無料登録のあとで見られます（登録画面で秘密保持の誓約に同意いただきます。紙の署名は要りません）。</p>
  <a class="btn-primary" href="%s" target="_top" rel="nofollow">無料登録して価格と資料を見る →</a>
  <a class="btn-secondary" href="https://dealroom.scix.co.jp/" target="_top">蓄電所マーケットで案件を見る</a>
</div></section>
""" % DR2_REGISTER
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", "/research"), (title_h, path)])}
<section class="hero"><div class="container">
  <div class="section-label">毎月発行・出典つき</div>
  <h1>{esc(title_h)}</h1>
  <p>{esc(doc["intro"])}</p>
  <p class="md-note">サイエンスエックス株式会社　発行 {jp_date(doc["issued"])}　A4・全{page_count(m)}ページ</p>
  <div class="rp-btns"><a class="btn-primary" href="{path}/{pdf_name}" download="{NAME}_{key}.pdf">PDF をダウンロード</a>
  <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/research">これまでの号</a></div>
  {issue_nav(nav)}
</div></section>
{chr(10).join(secs)}
{gallery}
{reading_section("ja")}
{data_section("ja")}
{cite}
{cta}{bmd.FOOTER}
</body>
</html>
"""
    head = page_head(title, desc, path, jsonld, f"/en/research/{key}" if has_en else None).replace("</style>", READ_CSS + "</style>", 1)
    og = pick_og(figs)
    if og:
        head = put_og(head, f"{BASE}{path}/f{og[0]}.png", og[1], og[2])
    return head + body, desc


def render_month_en(m, doc, figs, nav=None):
    """英語の市場ノートのページ（en/research/<YYYY-MM>/index.html）。図は図の番号 → パス。"""
    key = m["key"]
    path = f"/en/research/{key}"
    title_h = doc["title"]
    title = f"{title_h} | ScienceX"
    s1 = moves_sec(doc)
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("Source")]
    desc = f"{title_h}. " + (moves[0] if moves else doc["intro"])
    if len(desc) > 155:  # 検索結果の description は155字まで。語の切れ目で切る
        desc = desc[:154].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
    pdf_name = f"scix-bess-monthly-{key}-en.pdf"
    mod = modified_of(path, doc["issued"])
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "Report", "@id": BASE + path + "#report", "url": BASE + path,
                "name": title_h, "description": desc, "inLanguage": "en", "datePublished": doc["issued"],
                "dateModified": mod, "author": EN_ORG, "publisher": EN_PUBLISHER,
                "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{path}/{pdf_name}", "encodingFormat": "application/pdf"}}),
        bmd.ld(issue_dataset(path, title_h, desc, doc["issued"], mod, "en", f"{BASE}{path}/{pdf_name}")),
        bmd.ld(bmd.crumbs([("Home", BASE + "/en"), ("Reports", BASE + "/en/research"), (title_h, BASE + path)])),
    ])
    used = set()
    secs = [render_section(s, figs, key, used, "en") for s in doc["sections"]]
    nl = (f'<p>Each month\'s update also arrives in our LinkedIn newsletter, &ldquo;Japan grid-scale BESS: primary data&rdquo;. '
          f'<a href="{esc(doc["newsletter"])}" rel="noopener" target="_blank">Subscribe to the newsletter &rarr;</a></p>') if doc["newsletter"] else ""
    cite = f"""<section class="md"><div class="container rp-body">
  {bmd.cite_html("en", title_h, BASE + path, mod,
                 '<p>The figures are tallies of published data and our own records. The price spread is a difference in price per kWh and does not show actual revenue. '
                 'How we compiled them is in the last section, &ldquo;Assumptions and terms&rdquo;. Figures across issues are on <a href="/en/research/data">market data</a> (CSV), '
                 'and the reuse terms are in the <a href="/en/press">citation guide</a>.</p>')}
  {nl}
</div></section>"""
    cta = """<section class="cta"><div class="container">
  <h2>Want to see the projects behind these numbers? Visit Chikudensho Market</h2>
  <p>On Chikudensho Market, our marketplace for battery storage sites, you can browse current listings without registering. Prices and documents are available after free registration, where you agree to a confidentiality undertaking on the registration screen (no signed paper is needed).</p>
  <a class="btn-primary" href="%s" target="_top" rel="nofollow">Register free to see prices and documents &rarr;</a>
  <a class="btn-secondary" href="https://dealroom.scix.co.jp/en" target="_top">Browse projects on Chikudensho Market</a>
</div></section>
""" % DR2_REGISTER_EN
    body = f"""{bmd.nav_crumbs([("Home", "/en"), ("Reports", "/en/research"), (title_h, path)])}
<section class="hero"><div class="container">
  <div class="section-label">Monthly &middot; Sources cited</div>
  <h1>{esc(title_h)}</h1>
  <p>{esc(doc["intro"])}</p>
  <p class="md-note">Science X Inc. &middot; Published {en_date(doc["issued"])} &middot; A4, {page_count(m, True)} pages</p>
  <div class="rp-btns"><a class="btn-primary" href="{path}/{pdf_name}" download="{pdf_name}">Download the PDF</a>
  <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/research">All reports</a></div>
  {issue_nav(nav, "en")}
</div></section>
{chr(10).join(secs)}
{reading_section("en")}
{data_section("en")}
{cite}
{cta}{bmd.EN_FOOTER}
</body>
</html>
"""
    head = page_head_en(title, desc, path, jsonld, f"/research/{key}").replace("</style>", READ_CSS + "</style>", 1)
    og = pick_og(figs)
    if og:
        head = put_og(head, f"{BASE}{path}/f{og[0]}.png", og[1], og[2])
    return head + body, desc


_PAGES = {}


def page_count(m, en=False):
    ck = (m["key"], en)
    if ck not in _PAGES:
        out = subprocess.run(["pdfinfo", m["en_pdf" if en else "pdf"]], capture_output=True, text=True).stdout
        mt = re.search(r"Pages:\s+(\d+)", out)
        _PAGES[ck] = int(mt.group(1)) if mt else 0
    return _PAGES[ck]


def data_month(key):
    """号の名前 → 中身の月（2026年11月号から、号の名前は発行する月・中身は前月＝bin/monthly_report.py の NAMING_FROM。2026年10月号までは同じ月）。"""
    if key >= "2026-11":
        y, m = int(key[:4]), int(key[5:])
        return "%04d-%02d" % (y - (m == 1), 12 if m == 1 else m - 1)
    return key


def data_month_ja(key):
    k = data_month(key)
    return f"{k[:4]}年{int(k[5:])}月"


def data_month_en(key):
    k = data_month(key)
    return f"{MONTHS_EN[int(k[5:]) - 1]} {k[:4]}"


def backnumber_note(rows, lang):
    """あとから作った号（発行日が中身の月の翌月より後）の注。「毎月1日発行」とうたう一覧で、発行日が月の1日でない号の訳を書く（2026-11-23 別の目②）。"""
    late = []
    for r in rows:
        dm = data_month(r["key"])
        y, m = int(dm[:4]), int(dm[5:])
        lim = "%04d-%02d-31" % (y + (m == 12), m % 12 + 1)    # 中身の月の翌月の末まで＝その頃に出た号
        if r["issued"] > lim:
            late.append(r)
    if not late:
        return ""
    keys = sorted(r["key"] for r in late)
    when = max(r["issued"] for r in late)
    if lang == "ja":
        span = f"{int(keys[0][:4])}年{int(keys[0][5:])}月号〜{int(keys[-1][:4])}年{int(keys[-1][5:])}月号" if len(keys) > 1 else f"{int(keys[0][:4])}年{int(keys[0][5:])}月号"
        return f'<p class="md-note" style="margin-top:12px">{esc(span)}は、{esc(jp_date(when))}までに公表データから作り直したバックナンバーです。2026年12月号から、毎月1日（休日のときは次の営業日）に前月の数字の号を出します。</p>'
    span = f"{MONTHS_EN[int(keys[0][5:]) - 1]} {keys[0][:4]} to {MONTHS_EN[int(keys[-1][5:]) - 1]} {keys[-1][:4]}" if len(keys) > 1 else f"{MONTHS_EN[int(keys[0][5:]) - 1]} {keys[0][:4]}"
    return (f'<p class="md-note" style="margin-top:12px">The {esc(span)} issues are back issues rebuilt from published data by {esc(en_date(when))}. '
            'From the December 2026 issue, each issue comes out on the 1st of the month (the next business day if the 1st is a holiday) with the previous month\'s figures.</p>')


def render_index_en(rows):
    path = "/en/research"
    title = "Japan Battery Storage Market Notes (Monthly) | ScienceX"
    desc = "Monthly charts of Japan's EPRX balancing, JEPX wholesale and OCCTO capacity markets, from public data and our own records. Sources cited, PDF available."
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
                "name": title, "description": desc, "inLanguage": "en", "publisher": EN_PUBLISHER,
                "mainEntity": {"@type": "ItemList", "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": f"{BASE}/en/research/{r['key']}", "name": r["title_h"]}
                    for i, r in enumerate(rows)]}}),
        bmd.ld(bmd.crumbs([("Home", BASE + "/en"), ("Market Notes", BASE + path)])),
    ])
    li = "".join(
        f'<li><a class="t" href="/en/research/{r["key"]}">{esc(r["title_h"])}</a>'
        f'<div class="d">Published {en_date(r["issued"])} &middot; {esc(data_month_en(r["key"]))} data &middot; PDF available</div><p>{esc(r["lead"])}</p></li>' for r in rows)
    body = f"""{bmd.nav_crumbs([("Home", "/en"), ("Market Notes", path)])}
<section class="hero"><div class="container">
  <div class="section-label">Published on the 1st of each month</div>
  <h1>Battery Storage Market Notes</h1>
  <p>A battery storage site earns from three markets: the balancing market (EPRX), wholesale power (JEPX) and the capacity market (OCCTO). On the 1st of each month we chart the previous month for all three, from published data and our own records. Newest first.</p>
</div></section>
{flash_section("en")}
{data_section("en")}
<section class="md"><div class="container rp-body">
  <ul class="rp-list">{li}</ul>
  {backnumber_note(rows, "en")}
  <p class="md-note" style="margin-top:16px">Charts and figures may be reused with the source stated (<a href="/en/press">citation guide</a>). For the projects we list, see <a href="/en/projects">Projects</a> and the counts on <a href="/en/market-data">Market data</a> (updated daily).</p>
  <p class="md-note">The projects themselves are listed at Chikudensho Market, without registration (prices and documents after free registration). <a href="https://dealroom.scix.co.jp/en" data-cta="body" data-cta-target="market">Browse projects at Chikudensho Market</a></p>
</div></section>
{bmd.EN_FOOTER}
</body>
</html>
"""
    return page_head_en(title, desc, path, jsonld, "/research") + body


def render_index(rows, has_en=False):
    path = "/research"
    title = "蓄電所の市場ノート｜需給調整市場・卸電気・容量市場の数字を毎月｜サイエンスエックス"
    desc = "蓄電所の3つの稼ぎ口（需給調整市場 EPRX・卸電気 JEPX・容量市場 OCCTO）の数字を、公表データと当社の記録から毎月まとめたノート。需給調整市場の商品ごとの値段・応札倍率・約定率・蓄電池の使われ方、卸電気の価格と1kWh あたりの値差、容量市場の約定価格。毎月発行、出典つき、PDF あり。"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
                "name": title, "description": desc, "inLanguage": "ja", "publisher": PUBLISHER,
                "mainEntity": {"@type": "ItemList", "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": f"{BASE}/research/{r['key']}", "name": r["title_h"]}
                    for i, r in enumerate(rows)]}}),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + path)])),
    ])
    li = "".join(
        f'<li><a class="t" href="/research/{r["key"]}">{esc(r["title_h"])}</a>'
        f'<div class="d">発行 {jp_date(r["issued"])}・{esc(data_month_ja(r["key"]))}の数字・PDF あり</div><p>{esc(r["lead"])}</p></li>' for r in rows)
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", path)])}
<section class="hero"><div class="container">
  <div class="section-label">毎月1日発行</div>
  <h1>蓄電所の市場ノート</h1>
  <p>蓄電所（系統用蓄電池）の収入は、①需給調整市場（EPRX）・②卸電気（JEPX）・③容量市場（OCCTO）の3つの市場から入ります。その3つの数字を、公表データと当社の記録から毎月1日に前の月の分をまとめています。新しい号が上です。</p>
</div></section>
{flash_section("ja")}
{data_section("ja")}
<section class="md"><div class="container rp-body">
  <ul class="rp-list">{li}</ul>
  {backnumber_note(rows, "ja")}
  <p class="md-note" style="margin-top:16px">図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。売り案件の集計は <a href="/market-data">市場データ</a>（毎朝更新）に。</p>
  <p class="md-note">売り案件そのものは、蓄電所マーケットで登録なしで一覧できます（価格と資料は無料の登録のあと）。<a href="https://dealroom.scix.co.jp/" data-cta="body" data-cta-target="market">蓄電所マーケットで案件を見る</a></p>
</div></section>
{bmd.FOOTER}
</body>
</html>
"""
    return page_head(title, desc, path, jsonld, "/en/research" if has_en else None) + body


# ---------------------------------------------------------------- トップの「今月の月報」の札（2026-11-03: 目立たなかったため追加）
HOME_MARK = ("<!--R:latest-->", "<!--/R:latest-->")
HOME_CSS = """<style>
.rp-home{padding:56px 0;background:#fff;border-top:4px solid var(--gold);border-bottom:1px solid var(--border,#e5e5e5)}
.rp-home-in{display:grid;grid-template-columns:1.05fr 1fr;gap:36px;align-items:center}
.rp-home ul{margin:14px 0 18px;padding-left:1.2em;line-height:1.85;color:var(--text-secondary,#555)}
.rp-home ul li{margin:6px 0}
.rp-home-lead{color:var(--text-secondary,#555);line-height:1.9;font-size:.92rem}
.rp-home-btns a{margin:4px 12px 4px 0;display:inline-block}
.rp-home-fig{display:block;text-decoration:none;color:var(--text-secondary,#555);font-size:.84rem}
.rp-home-fig img{display:block;width:100%;height:auto;border:1px solid var(--border,#e5e5e5);border-radius:8px;background:#fff;margin-bottom:6px}
@media (max-width:860px){.rp-home-in{grid-template-columns:1fr;gap:22px}.rp-home{padding:40px 0}}
</style>"""


def home_card(m, doc, figs, lang="ja"):
    """トップに置く最新号の札（今月の動き3つ・HOME_FIG の図・読む／PDF）。新しい号が出るたびに書き換わる。"""
    key = m["key"]
    y, mo = key.split("-")
    s1 = moves_sec(doc)
    src = "出典:" if lang == "ja" else "Source"
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith(src)][:3]
    fn = next((n for n, f in FIG_FILE.items() if f == HOME_FIG), None)
    hit = next(((s, t) for s in doc["sections"] for k, t in s["items"] if k == "fig" and fn and re.match(r"(?:図|Figure )%d\b" % fn, t)), (None, ""))
    sec_f, cap_f = hit
    if lang == "ja":
        base, pdf = f"/research/{key}", f"/research/{key}/scix-bess-monthly-{key}.pdf"
        title = f"{NAME} {y}年{int(mo)}月号"
        lead = "蓄電所の3つの稼ぎ口、①需給調整市場（EPRX）・②卸電気（JEPX）・③容量市場（OCCTO）の数字を、公表データと当社の記録から毎月まとめています。図と表は、出典を書けば資料にそのままお使いいただけます。"
        btn, pdf_l, back = f"{int(mo)}月号を読む", "PDF をダウンロード", "バックナンバー"
        back_href, label = "/research", "蓄電所の市場ノート"
        flash_href, flash_l = "/research/flash", "毎日の速報"
    else:
        base, pdf = f"/en/research/{key}", f"/en/research/{key}/scix-bess-monthly-{key}-en.pdf"
        title = doc["title"]
        lead = "A battery storage site earns from three markets: the balancing market (EPRX), wholesale power (JEPX) and the capacity market (OCCTO). Every month we chart the figures for all three from public data and our own records. Charts and tables may be reused with the source stated."
        btn, pdf_l, back = "Read this issue", "Download PDF", "All issues"
        back_href, label = "/en/research", "Market Notes"
        flash_href, flash_l = "/en/research/flash", "Daily Flash"
    flash_link = (f'<a href="{flash_href}" style="color:var(--navy);border-bottom:1px solid var(--gold);text-decoration:none">{flash_l}</a>'
                  if os.path.exists(os.path.join(ROOT, flash_href.lstrip("/"), "index.html")) else "")
    fig = (f'<a class="rp-home-fig" href="{base}#s{sec_f["num"]}"><img src="{base}/f{fn}.png" alt="{esc(cap_f)}"{img_dims(figs[fn])} loading="lazy">{esc(cap_f)}</a>'
           if fn in figs and sec_f else "")
    return (f"""{HOME_MARK[0]}
{HOME_CSS}
<section class="rp-home" id="monthly-report"><div class="container"><div class="rp-home-in">
  <div>
    <div class="section-label">{label}</div>
    <h2 class="section-title" style="margin-bottom:10px"><a href="{base}" style="color:inherit;text-decoration:none">{esc(title)}</a></h2>
    <p class="rp-home-lead">{esc(lead)}</p>
    <ul>{"".join(f"<li>{esc(t)}</li>" for t in moves)}</ul>
    <p class="rp-home-btns"><a class="btn-primary" href="{base}">{btn}</a><a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="{pdf}" download>{pdf_l}</a><a href="{back_href}" style="color:var(--navy);border-bottom:1px solid var(--gold);text-decoration:none">{back}</a>{flash_link}</p>
  </div>
  {fig}
</div></div></section>
{HOME_MARK[1]}""")


def put_home(rel, card):
    """index.html の印の間を札に替えた中身を返す（印が無ければ None）。"""
    p = os.path.join(ROOT, rel)
    t = open(p, encoding="utf-8").read()
    i, j = t.find(HOME_MARK[0]), t.find(HOME_MARK[1])
    if i < 0 or j < i:
        print(f"注意: {rel} に {HOME_MARK[0]} の印が無い（トップの札は書かない）")
        return None
    return t[:i] + card + t[j + len(HOME_MARK[1]):]


# ---------------------------------------------------------------- 書き出し
def sitemap_add(text, rows, en_rows=()):
    """/research と各月の行を足す。英語版（en_rows＝英語のページがある月）があれば hreflang の相互の行も（日本語の行は書き直す）。
    lastmod は 発行日と今の sitemap の値の新しいほう＝頁の JSON-LD の dateModified と同じ値（modified_of。頁を変えた日は stamp_sitemap.py が
    sitemap と頁の両方を進めるので、焼き直しで戻さない。2026-11-22 中島「Seo 対策も徹底して やって」）。"""
    en_keys = {r["key"] for r in en_rows}

    def lastmod_of(path, issued):
        return modified_of(path, issued, text)

    def ent(path, lastmod, pr, en_path=None, lang="ja"):
        lastmod = lastmod_of(path, lastmod)
        other = ""
        if en_path:
            ja_p, en_p = (path, en_path) if lang == "ja" else (en_path, path)
            self_en, self_ja = f'<xhtml:link rel="alternate" hreflang="en" href="{BASE}{en_p}"/>', f'<xhtml:link rel="alternate" hreflang="ja" href="{BASE}{ja_p}"/>'
            links = (self_ja + self_en) if lang == "ja" else (self_en + self_ja)
        else:
            links = f'<xhtml:link rel="alternate" hreflang="ja" href="{BASE}{path}"/>'
        return f"  <url><loc>{BASE}{path}</loc>{links}<priority>{pr}</priority><lastmod>{lastmod}</lastmod></url>\n"
    want = [("/research", max(r["issued"] for r in rows), "0.7", "/en/research" if en_keys else None, "ja")] + [
        (f"/research/{r['key']}", r["issued"], "0.6", f"/en/research/{r['key']}" if r["key"] in en_keys else None, "ja") for r in rows]
    if en_keys:
        want += [("/en/research", max(r["issued"] for r in en_rows), "0.6", "/research", "en")] + [
            (f"/en/research/{r['key']}", r["issued"], "0.5", f"/research/{r['key']}", "en") for r in en_rows]
    add = ""
    for p, d, pr, enp, lang in want:
        new = ent(p, d, pr, enp, lang)
        pat = re.compile(r"  <url><loc>" + re.escape(BASE + p) + r"</loc>.*?</url>\n")
        if pat.search(text):
            text = pat.sub(lambda _m: new, text, count=1)   # 既にある行は同じ形に（日本語の行に hreflang="en" が足されるだけ）
        else:
            add += new
    if not add:
        return text
    return text.replace("</urlset>", add + "</urlset>", 1)


def main():
    check = "--check" in sys.argv
    months = find_months()
    if not months:
        print("月報が見つからない（Drive の _作成物/<YYYYMM>_月報/）。何もしない。")
        return 0
    docs, hits = {}, []
    for m in months:
        md_text = open(m["md"], encoding="utf-8").read()
        hits += safety_scan(m, md_text, pdf_text(m["pdf"]))
        docs[m["key"]] = parse_md(md_text)
        move_partial(docs[m["key"]])                     # 月の途中の数字は速報の頁へ（2026-11-23）
        if m["en_md"]:
            en_text = open(m["en_md"], encoding="utf-8").read()
            hits += safety_scan(m, en_text, pdf_text(m["en_pdf"]), "en")
            docs[m["key"] + ":en"] = parse_md(en_text, "en")
            move_partial(docs[m["key"] + ":en"], "en")
    if hits:
        print("NG 公開してはいけない語が月報の中にある。何も書かずに止める:")
        print("\n".join(hits))
        return 2

    files = {}   # 相対パス -> bytes
    rows = []
    # 市場データ（号をまたいだ推移）とエリアの頁（2026-11-21）。号と同じ md の表から焼く（build_report_data.py）。
    # 号の頁・一覧の頁の入口（data_section）が、焼かれた頁だけを指すように、先に焼く。
    rd_files, rd_sm, rd_notes = brd.build(sys.modules[__name__], months, docs)
    for n in rd_notes:
        print(n)
    if any(n.startswith("NG") for n in rd_notes):        # 容量市場・長期脱炭素の CSV の出典の列が空など。--check でも通さない（2026-11-23）
        return 2
    files.update(rd_files)
    DATA_PAGES.clear()
    DATA_PAGES.update(k for k in rd_files if k.endswith("/index.html"))
    DATA_CSVS.clear()
    DATA_CSVS.update(k for k in rd_files if k.endswith(".csv"))
    with tempfile.TemporaryDirectory() as tmp:
        for i, m in enumerate(months):                   # 新しい月が先
            doc = docs[m["key"]]
            nav = (months[i + 1]["key"] if i + 1 < len(months) else None, months[i - 1]["key"] if i > 0 else None)
            if not doc["issued"]:
                print(f"NG {m['key']}: 発行日が MD に無い"); return 2
            figs = en_fig_by_number(fig_sources(m))      # 図N → ファイル（図4 は f9.png など。日本語も同じ対応＝2026-11-02 まで図4〜10 が題と別の図だった）
            page_imgs = {} if figs else render_pdf_pages(m["pdf"], tmp)
            html_, _ = render_month(m, doc, figs, page_imgs, bool(m["en_md"]), nav)
            d = f"research/{m['key']}"
            files[f"{d}/index.html"] = html_.encode("utf-8")
            files[f"{d}/scix-bess-monthly-{m['key']}.pdf"] = open(m["pdf"], "rb").read()
            for n, p in figs.items():
                files[f"{d}/f{n}.png"] = open(p, "rb").read()
            for n, p in page_imgs.items():
                files[f"{d}/p{n}.png"] = open(p, "rb").read()
            s1 = moves_sec(doc)
            moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("出典:")]
            y, mo = m["key"].split("-")
            rows.append({"key": m["key"], "issued": doc["issued"], "title_h": f"{NAME} {y}年{int(mo)}月号",
                         "lead": " ".join(moves[:2]) or doc["intro"]})
        files["research/index.html"] = render_index(rows, any(m["en_md"] for m in months)).encode("utf-8")
        latest = months[0]                                # find_months は新しい月が先（2026-11-05 バックナンバーを足したら [-1] は一番古い4月号になる。最新月が一番上に来るようにする）
        home = put_home("index.html", home_card(latest, docs[latest["key"]], en_fig_by_number(fig_sources(latest))))
        if home is not None:
            files["index.html"] = home.encode("utf-8")
        en_rows = []
        en_months = [m for m in months if m["en_md"]]
        for i, m in enumerate(en_months):
            nav_en = (en_months[i + 1]["key"] if i + 1 < len(en_months) else None, en_months[i - 1]["key"] if i > 0 else None)
            doc = docs[m["key"] + ":en"]
            if not doc["issued"]:
                print(f"NG {m['key']}: 英語版の発行日（Published …）が MD に無い"); return 2
            figs = en_fig_by_number(fig_sources(m, "figs_en"))
            html_, _ = render_month_en(m, doc, figs, nav_en)
            d = f"en/research/{m['key']}"
            files[f"{d}/index.html"] = html_.encode("utf-8")
            files[f"{d}/scix-bess-monthly-{m['key']}-en.pdf"] = open(m["en_pdf"], "rb").read()
            for n, p in figs.items():
                files[f"{d}/f{n}.png"] = open(p, "rb").read()
            s1 = moves_sec(doc)
            moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("Source")]
            en_rows.append({"key": m["key"], "issued": doc["issued"], "title_h": doc["title"], "lead": " ".join(moves[:2]) or doc["intro"]})
        if en_rows:
            files["en/research/index.html"] = render_index_en(en_rows).encode("utf-8")
            le = [m for m in months if m["en_md"]][0]     # 英語版のある最新の月
            home = put_home("en/index.html", home_card(le, docs[le["key"] + ":en"], en_fig_by_number(fig_sources(le, "figs_en")), "en"))
            if home is not None:
                files["en/index.html"] = home.encode("utf-8")
        lt = months[0]
        files["research/latest.json"] = latest_json(
            lt, docs[lt["key"]], open(lt["md"], encoding="utf-8").read(),
            docs.get(lt["key"] + ":en"), open(lt["en_md"], encoding="utf-8").read() if lt["en_md"] else "").encode("utf-8")
        sm_path = os.path.join(ROOT, "sitemap.xml")
        sm = open(sm_path, encoding="utf-8").read()
        sm2 = sitemap_add(sm, rows, en_rows)
        # 市場データ・エリアの頁の lastmod も号の頁と同じ（最新の号の発行日＝頁の dateModified）
        sm2 = brd.sitemap_add(sm2, list(rd_sm), BASE)
        if sm2 != sm:
            files["sitemap.xml"] = sm2.encode("utf-8")

        changed = []
        for rel, data in sorted(files.items()):
            p = os.path.join(ROOT, rel)
            old = open(p, "rb").read() if os.path.isfile(p) else None
            if old != data:
                changed.append(rel)
                if not check:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "wb") as f:
                        f.write(data)
    print(("ずれ: " if check else "更新: ") + (", ".join(changed) if changed else "なし（最新）"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
