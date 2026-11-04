#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「蓄電所の市場ノート」（旧名 系統用蓄電池の月報・Drive の _作成物/<YYYYMM>_月報/）から、公開のページを焼く。
2026-11-03 改名（中島「月報って RE フォワードのパクリなので変えて」「Web も月報って何？社内用って感じ」）。表に出る語に「月報」「レポート」を使わない。URL の /report はそのまま。

2026-11-01 新設。中島「月報は HP に乗せても良くない」。ただしコラムは中島さんが書く（O16-1）ので、
コラムとは別の「レポート」（毎月の機械発行のデータ月報）として /report と /report/<YYYY-MM> に置く。

読むもの（Drive。リポジトリには置かない）:
  ~/マイドライブ/9_システム/_作成物/<YYYYMM>_月報/蓄電所の市場ノート_<YYYY-MM>.md と .pdf
  図: ~/.openclaw/workspace/build/*月報*/<YYYYMM>/figs/f1.png〜（monthly_report_figs.py の出力）。
      無ければ PDF の各ページを画像にして載せる。
英語版（2026-11-02〜）: 同じフォルダの 蓄電所の市場ノート_<YYYY-MM>_en.md と _en.pdf、図は build/*月報*/<YYYYMM>/figs_en/（bin/monthly_report.py build-en が作る）が
  そろった月だけ en/report/<YYYY-MM>/index.html と en/report/index.html を焼く（図Nのファイルは f<N>.png。図の番号→ファイルは FIG_FILE）。
  日本語のページとは hreflang で相互に結ぶ（sitemap.xml も）。
生成するもの（全文を書き直す。手で直さない）:
  report/index.html                 月報の一覧（新しい月が上）
  report/<YYYY-MM>/index.html       各月のページ（今月の動き3つ・図・PDF・出典と試算の前提・引用の案内）
  report/<YYYY-MM>/f1.png …, scix-bess-monthly-<YYYY-MM>.pdf
  en/report/index.html, en/report/<YYYY-MM>/index.html, f1.png〜, scix-bess-monthly-<YYYY-MM>-en.pdf（英語版）
  sitemap.xml                       /report と各月の行（無ければ足す。英語版があれば hreflang の相互の行も）

置く前の検査（公開リポジトリ＝O16-19）: MD と PDF の文字に、住所・地番・案件ID・価格類（仕入値・売値・土地代）・
売主・成約実績の語が1つでもあれば、何も書かずに終了コード 2 で止まる。図の PNG は文字を持たないので、
図の中身は MD の図の説明文（図N …）で見る。

使い方:
    python3 scripts/build_reports.py            # 書き換えて差分を報告
    python3 scripts/build_reports.py --check    # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
毎朝の同期（scripts/sync_projects_json.sh）の末尾から呼ぶ（月報が出た月に1回だけ差分が出る）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import glob
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_market_data as bmd  # noqa: E402  head / FOOTER / CSS / ld / crumbs / nav_crumbs / ORG を共用する

HOME = os.path.expanduser("~")
SRC = os.environ.get("SCIX_REPORT_SRC", os.path.join(HOME, "マイドライブ", "9_システム", "_作成物"))
FIGS = os.environ.get("SCIX_REPORT_FIGS", os.path.join(HOME, ".openclaw", "workspace", "build"))
BASE = bmd.BASE
DR2_REGISTER = "https://dealroom.scix.co.jp/register"
DR2_REGISTER_EN = "https://dealroom.scix.co.jp/en/register"
# 図N → 図のファイル（bin/monthly_report.py の FIG_FILE と同じ。月報の節の並び）
FIG_FILE = {1: "f9", 2: "f1", 3: "f2", 4: "f12", 5: "f3", 6: "f15", 7: "f18", 8: "f16", 9: "f13", 10: "f14", 11: "f5", 12: "f17", 13: "f10", 14: "f6", 15: "f7"}   # bin/monthly_report.py の FIG_FILE と同じ（2026-11-03 の並び: 3つの稼ぎ口→①卸電気→②需給調整→③容量→当社の記録。2026-11-05 に図7＝管区ごとの約定率 f18 を足した）
NAME, NAME_EN = "蓄電所の市場ノート", "Battery Storage Market Notes"
HOME_FIG = "f16"          # トップの札に出す図（一次調整力の席の取り合い）
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
EN_ORG = {"@type": "Organization", "@id": bmd.BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": bmd.BASE + "/en"}

# 公開してはいけない語（O16-19・O16-7）。「円」「価格」は卸電気の価格や試算で正当に出るので語としては禁じない。
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
"""

SEC_MORE = {"1": "three"}
MOVES_RE = re.compile(r"今月の動き|Three (?:trends|things|moves)", re.I)   # 「今月の動き3つ」の節


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
         .replace(f"{BASE}/img/ogp-x.png", f"{BASE}/img/ogp-x-en.png"))
    return h.replace("</style>", EXTRA_CSS + "</style>", 1)


def en_date(iso):
    y, m, d = iso.split("-")
    return f"{MONTHS_EN[int(m) - 1]} {int(d)}, {y}"


def render_section(sec, figs, month_key, used, lang="ja"):
    src_pre = "出典:" if lang == "ja" else "Source"
    base = "/report" if lang == "ja" else "/en/report"
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
        elif kind == "fig":
            n = int(re.match(r"(?:図|Figure )(\d+)", txt).group(1))
            src = figs.get(n)
            if src:
                used.add(n)
                out.append(f'<figure class="rp-fig"><img src="{base}/{month_key}/f{n}.png" alt="{esc(txt)}" loading="lazy">'
                           f"<figcaption>{esc(txt)}</figcaption></figure>")
            prev_fig = True
        i += 1
    out.append("</div></section>")
    return "\n".join(out)


def render_month(m, doc, figs, page_imgs, has_en=False):
    key = m["key"]
    y, mo = key.split("-")
    path = f"/report/{key}"
    title_h = f"{NAME} {y}年{int(mo)}月号"
    title = f"{title_h}｜卸電気の価格・需給調整市場・容量市場・接続検討｜サイエンスエックス"
    s1 = moves_sec(doc)
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("出典:")]
    desc = (f"{title_h}。" + (moves[0] if moves else doc["intro"]))[:160]
    pdf_name = f"scix-bess-monthly-{key}.pdf"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "Report", "@id": BASE + path + "#report", "url": BASE + path,
                "name": title_h, "description": desc, "inLanguage": "ja", "datePublished": doc["issued"],
                "dateModified": doc["issued"], "author": bmd.ORG, "publisher": bmd.ORG,
                "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{path}/{pdf_name}", "encodingFormat": "application/pdf"}}),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + "/report"), (title_h, BASE + path)])),
    ])
    used = set()
    secs = [render_section(s, figs, key, used) for s in doc["sections"]]
    gallery = ""
    if not figs and page_imgs:
        gallery = ('<section class="md"><div class="container rp-body"><h2 class="md-h">PDF の各ページ</h2>'
                   + "".join(f'<figure class="rp-fig"><img src="/report/{key}/p{n}.png" alt="{NAME} {y}年{int(mo)}月号 {n}ページ" loading="lazy"></figure>'
                             for n in sorted(page_imgs)) + "</div></section>")
    nl = (f'<p>毎月の更新は、LinkedIn のニュースレター「系統用蓄電池の一次データ」でもお届けしています。'
          f'<a href="{esc(doc["newsletter"])}" rel="noopener" target="_blank">ニュースレターを購読する →</a></p>') if doc["newsletter"] else ""
    cite = f"""<section class="md"><div class="container rp-body">
  <div class="cite"><div class="cite-h">引用・転載について</div>
  図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。
  数字は公表データと当社の記録の集計です。値差は1kWh あたりの価格の差で、実際の収益を示すものではありません。集計のしかたは上の「前提と用語」に書きました。</div>
  {nl}
</div></section>"""
    cta = """<section class="cta"><div class="container">
  <h2>このノートの数字の元になった案件を、買い手の方へ</h2>
  <p>当社の棚 DealRoom2 に登録（無料）すると、接続検討の回答書など、案件ごとの資料を申請できます。案件の一覧は、登録なしでご覧いただけます。</p>
  <a class="btn-primary" href="%s" target="_top" rel="nofollow">DealRoom に登録する →</a>
  <a class="btn-secondary" href="/projects">販売中の案件を見る</a>
</div></section>
""" % DR2_REGISTER
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", "/report"), (title_h, path)])}
<section class="hero"><div class="container">
  <span class="badge">毎月発行・出典つき</span>
  <div class="section-label">Market Notes</div>
  <h1>{esc(title_h)}</h1>
  <p>{esc(doc["intro"])}</p>
  <p class="md-note">サイエンスエックス株式会社　発行 {jp_date(doc["issued"])}　A4・全{page_count(m)}ページ</p>
  <div class="rp-btns"><a class="btn-primary" href="{path}/{pdf_name}" download="{NAME}_{key}.pdf">PDF をダウンロード</a>
  <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/report">これまでの号</a></div>
</div></section>
{chr(10).join(secs)}
{gallery}
{cite}
{cta}{bmd.FOOTER}
</body>
</html>
"""
    return page_head(title, desc, path, jsonld, f"/en/report/{key}" if has_en else None) + body, desc


def render_month_en(m, doc, figs):
    """英語の市場ノートのページ（en/report/<YYYY-MM>/index.html）。図は図の番号 → パス。"""
    key = m["key"]
    path = f"/en/report/{key}"
    title_h = doc["title"]
    title = f"{title_h} | ScienceX"
    s1 = moves_sec(doc)
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("Source")]
    desc = f"{title_h}. " + (moves[0] if moves else doc["intro"])
    if len(desc) > 155:  # 検索結果の description は155字まで。語の切れ目で切る
        desc = desc[:154].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
    pdf_name = f"scix-bess-monthly-{key}-en.pdf"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "Report", "@id": BASE + path + "#report", "url": BASE + path,
                "name": title_h, "description": desc, "inLanguage": "en", "datePublished": doc["issued"],
                "dateModified": doc["issued"], "author": EN_ORG, "publisher": EN_ORG,
                "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{path}/{pdf_name}", "encodingFormat": "application/pdf"}}),
        bmd.ld(bmd.crumbs([("Home", BASE + "/en"), ("Reports", BASE + "/en/report"), (title_h, BASE + path)])),
    ])
    used = set()
    secs = [render_section(s, figs, key, used, "en") for s in doc["sections"]]
    nl = (f'<p>Each month\'s update also arrives in our LinkedIn newsletter, &ldquo;Japan grid-scale BESS: primary data&rdquo;. '
          f'<a href="{esc(doc["newsletter"])}" rel="noopener" target="_blank">Subscribe to the newsletter &rarr;</a></p>') if doc["newsletter"] else ""
    cite = f"""<section class="md"><div class="container rp-body">
  <div class="cite"><div class="cite-h">Quoting and reuse</div>
  Charts and figures may be reused as they are, with the source stated (<a href="/en/press">citation guide</a>).
  The figures are tallies of published data and our own records. The price spread is a difference in price per kWh and does not show actual revenue. How we compiled them is in the last section, "Assumptions and terms".</div>
  {nl}
</div></section>"""
    cta = """<section class="cta"><div class="container">
  <h2>Want the projects behind these numbers? Join DealRoom</h2>
  <p>Register on our data room, DealRoom (free), to request project-level documents such as grid connection answers. The list of projects can be viewed without registering.</p>
  <a class="btn-primary" href="%s" target="_top" rel="nofollow">Register on DealRoom &rarr;</a>
  <a class="btn-secondary" href="/en/projects">See projects for sale</a>
</div></section>
""" % DR2_REGISTER_EN
    body = f"""{bmd.nav_crumbs([("Home", "/en"), ("Reports", "/en/report"), (title_h, path)])}
<section class="hero"><div class="container">
  <span class="badge">Monthly &middot; Sources cited</span>
  <div class="section-label">Market Notes</div>
  <h1>{esc(title_h)}</h1>
  <p>{esc(doc["intro"])}</p>
  <p class="md-note">Science X Inc. &middot; Published {en_date(doc["issued"])} &middot; A4, {page_count(m, True)} pages</p>
  <div class="rp-btns"><a class="btn-primary" href="{path}/{pdf_name}" download="{pdf_name}">Download the PDF</a>
  <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/report">All reports</a></div>
</div></section>
{chr(10).join(secs)}
{cite}
{cta}{bmd.EN_FOOTER}
</body>
</html>
"""
    return page_head_en(title, desc, path, jsonld, f"/report/{key}") + body, desc


_PAGES = {}


def page_count(m, en=False):
    ck = (m["key"], en)
    if ck not in _PAGES:
        out = subprocess.run(["pdfinfo", m["en_pdf" if en else "pdf"]], capture_output=True, text=True).stdout
        mt = re.search(r"Pages:\s+(\d+)", out)
        _PAGES[ck] = int(mt.group(1)) if mt else 0
    return _PAGES[ck]


def render_index_en(rows):
    path = "/en/report"
    title = "Battery Storage Market Notes | Wholesale, balancing and capacity markets in Japan | ScienceX"
    desc = "Monthly charts on Japan's three markets for battery storage (JEPX wholesale, EPRX balancing, OCCTO capacity), from published data and ScienceX records. Sources cited, PDF available."
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
                "name": title, "description": desc, "inLanguage": "en", "publisher": EN_ORG,
                "mainEntity": {"@type": "ItemList", "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": f"{BASE}/en/report/{r['key']}", "name": r["title_h"]}
                    for i, r in enumerate(rows)]}}),
        bmd.ld(bmd.crumbs([("Home", BASE + "/en"), ("Market Notes", BASE + path)])),
    ])
    li = "".join(
        f'<li><a class="t" href="/en/report/{r["key"]}">{esc(r["title_h"])}</a>'
        f'<div class="d">Published {en_date(r["issued"])} &middot; PDF available</div><p>{esc(r["lead"])}</p></li>' for r in rows)
    body = f"""{bmd.nav_crumbs([("Home", "/en"), ("Market Notes", path)])}
<section class="hero"><div class="container">
  <span class="badge">Published monthly</span>
  <div class="section-label">Market Notes</div>
  <h1>Battery Storage Market Notes</h1>
  <p>A battery storage site earns from three markets: wholesale power (JEPX), the balancing market (EPRX) and the capacity market (OCCTO). Each month we chart the latest figures for all three, from published data and our own records. Newest first.</p>
</div></section>
<section class="md"><div class="container rp-body">
  <ul class="rp-list">{li}</ul>
  <p class="md-note" style="margin-top:16px">Charts and figures may be reused with the source stated (<a href="/en/press">citation guide</a>). For the projects we list, see <a href="/en/projects">Projects</a> (updated daily).</p>
</div></section>
{bmd.EN_FOOTER}
</body>
</html>
"""
    return page_head_en(title, desc, path, jsonld, "/report") + body


def render_index(rows, has_en=False):
    path = "/report"
    title = "蓄電所の市場ノート｜卸電気・需給調整市場・容量市場の数字を毎月｜サイエンスエックス"
    desc = "蓄電所の3つの稼ぎ口（卸電気 JEPX・需給調整市場 EPRX・容量市場 OCCTO）の数字を、公表データと当社の記録から毎月まとめたノート。卸電気の価格と1kWh あたりの値差、需給調整市場の商品ごとの値段・応札倍率・約定率・蓄電池の使われ方、容量市場の約定価格。毎月発行、出典つき、PDF あり。"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
                "name": title, "description": desc, "inLanguage": "ja", "publisher": bmd.ORG,
                "mainEntity": {"@type": "ItemList", "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": f"{BASE}/report/{r['key']}", "name": r["title_h"]}
                    for i, r in enumerate(rows)]}}),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + path)])),
    ])
    li = "".join(
        f'<li><a class="t" href="/report/{r["key"]}">{esc(r["title_h"])}</a>'
        f'<div class="d">発行 {jp_date(r["issued"])}・PDF あり</div><p>{esc(r["lead"])}</p></li>' for r in rows)
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", path)])}
<section class="hero"><div class="container">
  <span class="badge">毎月発行</span>
  <div class="section-label">Report</div>
  <h1>蓄電所の市場ノート</h1>
  <p>蓄電所（系統用蓄電池）の収入は、①卸電気（JEPX）・②需給調整市場（EPRX）・③容量市場（OCCTO）の3つの市場から入ります。その3つの数字を、公表データと当社の記録から毎月まとめています。新しい号が上です。</p>
</div></section>
<section class="md"><div class="container rp-body">
  <ul class="rp-list">{li}</ul>
  <p class="md-note" style="margin-top:16px">図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。売り案件の集計は <a href="/market-data">市場データ</a>（毎朝更新）に。</p>
</div></section>
{bmd.FOOTER}
</body>
</html>
"""
    return page_head(title, desc, path, jsonld, "/en/report" if has_en else None) + body


# ---------------------------------------------------------------- トップの「今月の月報」の札（2026-11-03 中島「この月報いいのに全然目立たない」）
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
        base, pdf = f"/report/{key}", f"/report/{key}/scix-bess-monthly-{key}.pdf"
        title = f"{NAME} {y}年{int(mo)}月号"
        lead = "蓄電所の3つの稼ぎ口、①卸電気（JEPX）・②需給調整市場（EPRX）・③容量市場（OCCTO）の数字を、公表データと当社の記録から毎月まとめています。図と表は、出典を書けば資料にそのままお使いいただけます。"
        btn, pdf_l, back = f"{int(mo)}月号を読む", "PDF をダウンロード", "バックナンバー"
        back_href, label = "/report", "蓄電所の市場ノート"
    else:
        base, pdf = f"/en/report/{key}", f"/en/report/{key}/scix-bess-monthly-{key}-en.pdf"
        title = doc["title"]
        lead = "A battery storage site earns from three markets: wholesale power (JEPX), the balancing market (EPRX) and the capacity market (OCCTO). Every month we chart the figures for all three from public data and our own records. Charts and tables may be reused with the source stated."
        btn, pdf_l, back = "Read this issue", "Download PDF", "All issues"
        back_href, label = "/en/report", "Market Notes"
    fig = (f'<a class="rp-home-fig" href="{base}#s{sec_f["num"]}"><img src="{base}/f{fn}.png" alt="{esc(cap_f)}" loading="lazy">{esc(cap_f)}</a>'
           if fn in figs and sec_f else "")
    return (f"""{HOME_MARK[0]}
{HOME_CSS}
<section class="rp-home" id="monthly-report"><div class="container"><div class="rp-home-in">
  <div>
    <div class="section-label">{label}</div>
    <h2 class="section-title" style="margin-bottom:10px"><a href="{base}" style="color:inherit;text-decoration:none">{esc(title)}</a></h2>
    <p class="rp-home-lead">{esc(lead)}</p>
    <ul>{"".join(f"<li>{esc(t)}</li>" for t in moves)}</ul>
    <p class="rp-home-btns"><a class="btn-primary" href="{base}">{btn}</a><a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="{pdf}" download>{pdf_l}</a><a href="{back_href}" style="color:var(--navy);border-bottom:1px solid var(--gold);text-decoration:none">{back}</a></p>
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
    """/report と各月の行を足す。英語版（en_rows＝英語のページがある月）があれば hreflang の相互の行も（日本語の行は書き直す）。"""
    en_keys = {r["key"] for r in en_rows}

    def ent(path, lastmod, pr, en_path=None, lang="ja"):
        other = ""
        if en_path:
            ja_p, en_p = (path, en_path) if lang == "ja" else (en_path, path)
            self_en, self_ja = f'<xhtml:link rel="alternate" hreflang="en" href="{BASE}{en_p}"/>', f'<xhtml:link rel="alternate" hreflang="ja" href="{BASE}{ja_p}"/>'
            links = (self_ja + self_en) if lang == "ja" else (self_en + self_ja)
        else:
            links = f'<xhtml:link rel="alternate" hreflang="ja" href="{BASE}{path}"/>'
        return f"  <url><loc>{BASE}{path}</loc>{links}<priority>{pr}</priority><lastmod>{lastmod}</lastmod></url>\n"
    want = [("/report", rows[0]["issued"], "0.7", "/en/report" if en_keys else None, "ja")] + [
        (f"/report/{r['key']}", r["issued"], "0.6", f"/en/report/{r['key']}" if r["key"] in en_keys else None, "ja") for r in rows]
    if en_keys:
        want += [("/en/report", max(r["issued"] for r in en_rows), "0.6", "/report", "en")] + [
            (f"/en/report/{r['key']}", r["issued"], "0.5", f"/report/{r['key']}", "en") for r in en_rows]
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
        if m["en_md"]:
            en_text = open(m["en_md"], encoding="utf-8").read()
            hits += safety_scan(m, en_text, pdf_text(m["en_pdf"]), "en")
            docs[m["key"] + ":en"] = parse_md(en_text, "en")
    if hits:
        print("NG 公開してはいけない語が月報の中にある。何も書かずに止める:")
        print("\n".join(hits))
        return 2

    files = {}   # 相対パス -> bytes
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for m in months:
            doc = docs[m["key"]]
            if not doc["issued"]:
                print(f"NG {m['key']}: 発行日が MD に無い"); return 2
            figs = en_fig_by_number(fig_sources(m))      # 図N → ファイル（図4 は f9.png など。日本語も同じ対応＝2026-11-02 まで図4〜10 が題と別の図だった）
            page_imgs = {} if figs else render_pdf_pages(m["pdf"], tmp)
            html_, _ = render_month(m, doc, figs, page_imgs, bool(m["en_md"]))
            d = f"report/{m['key']}"
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
        files["report/index.html"] = render_index(rows, any(m["en_md"] for m in months)).encode("utf-8")
        latest = months[-1]
        home = put_home("index.html", home_card(latest, docs[latest["key"]], en_fig_by_number(fig_sources(latest))))
        if home is not None:
            files["index.html"] = home.encode("utf-8")
        en_rows = []
        for m in months:
            if not m["en_md"]:
                continue
            doc = docs[m["key"] + ":en"]
            if not doc["issued"]:
                print(f"NG {m['key']}: 英語版の発行日（Published …）が MD に無い"); return 2
            figs = en_fig_by_number(fig_sources(m, "figs_en"))
            html_, _ = render_month_en(m, doc, figs)
            d = f"en/report/{m['key']}"
            files[f"{d}/index.html"] = html_.encode("utf-8")
            files[f"{d}/scix-bess-monthly-{m['key']}-en.pdf"] = open(m["en_pdf"], "rb").read()
            for n, p in figs.items():
                files[f"{d}/f{n}.png"] = open(p, "rb").read()
            s1 = moves_sec(doc)
            moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("Source")]
            en_rows.append({"key": m["key"], "issued": doc["issued"], "title_h": doc["title"], "lead": " ".join(moves[:2]) or doc["intro"]})
        if en_rows:
            files["en/report/index.html"] = render_index_en(en_rows).encode("utf-8")
            le = [m for m in months if m["en_md"]][-1]
            home = put_home("en/index.html", home_card(le, docs[le["key"] + ":en"], en_fig_by_number(fig_sources(le, "figs_en")), "en"))
            if home is not None:
                files["en/index.html"] = home.encode("utf-8")
        sm_path = os.path.join(ROOT, "sitemap.xml")
        sm = open(sm_path, encoding="utf-8").read()
        sm2 = sitemap_add(sm, rows, en_rows)
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
