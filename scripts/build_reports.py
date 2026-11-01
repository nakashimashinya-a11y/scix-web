#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月報（Drive の _作成物/<YYYYMM>_月報/）から、公開の「レポート」ページを焼く。

2026-11-01 新設。中島「月報は HP に乗せても良くない」。ただしコラムは中島さんが書く（O16-1）ので、
コラムとは別の「レポート」（毎月の機械発行のデータ月報）として /report と /report/<YYYY-MM> に置く。

読むもの（Drive。リポジトリには置かない）:
  ~/マイドライブ/9_システム/_作成物/<YYYYMM>_月報/系統用蓄電池の月報_<YYYY-MM>.md と .pdf
  図: ~/.openclaw/workspace/build/*月報*/<YYYYMM>/figs/f1.png〜（monthly_report_figs.py の出力）。
      無ければ PDF の各ページを画像にして載せる。
生成するもの（全文を書き直す。手で直さない）:
  report/index.html                 月報の一覧（新しい月が上）
  report/<YYYY-MM>/index.html       各月のページ（今月の動き3つ・図・PDF・出典と試算の前提・引用の案内）
  report/<YYYY-MM>/f1.png …, scix-bess-monthly-<YYYY-MM>.pdf
  sitemap.xml                       /report と各月の行（無ければ足す）

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
DR2_REGISTER = "https://scix-dealroom2.pages.dev/register"

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


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- 入力
def find_months():
    out = []
    for d in sorted(glob.glob(os.path.join(SRC, "[0-9][0-9][0-9][0-9][0-9][0-9]_月報"))):
        ym = os.path.basename(d)[:6]
        key = f"{ym[:4]}-{ym[4:]}"
        md = os.path.join(d, f"系統用蓄電池の月報_{key}.md")
        pdf = os.path.join(d, f"系統用蓄電池の月報_{key}.pdf")
        if os.path.isfile(md) and os.path.isfile(pdf):
            out.append({"ym": ym, "key": key, "md": md, "pdf": pdf})
    return sorted(out, key=lambda m: m["key"], reverse=True)


def pdf_text(pdf):
    try:
        return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"NG PDF の文字を取れない（pdftotext）: {pdf}: {e}")


def safety_scan(m, md_text, pdf_txt):
    hits = []
    for label, text in (("md", md_text), ("pdf", pdf_txt)):
        for pat, why in FORBIDDEN:
            for mt in re.finditer(pat, text):
                hits.append(f"{m['key']} {label}: {why}: 「{mt.group(0)[:40]}」")
    return hits


def parse_md(text):
    """MD を { title, issued, intro, sections:[{title, items:[(kind, text)]}], footer } にする。"""
    text = text.replace("最終ページ", "末尾の「試算の前提と用語」")  # PDF では最終ページ・Web では末尾の節
    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    issued = ""
    mt = re.search(r"発行\s*(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if mt:
        issued = f"{mt.group(1)}-{int(mt.group(2)):02d}-{int(mt.group(3)):02d}"
    body = text.split("\n---\n")[0]
    footer = text.split("\n---\n")[1] if "\n---\n" in text else ""
    sections, cur, intro = [], None, []
    for l in body.splitlines():
        s = l.strip()
        if not s or s.startswith("<!--") or s.startswith("# "):
            continue
        if re.match(r"サイエンスエックス株式会社　発行", s):
            continue
        if s.startswith("## "):
            cur = {"title": re.sub(r"^\d+\.\s*", "", s[3:].strip()), "num": (re.match(r"^## (\d+)\.", s) or [None, ""])[1], "items": []}
            sections.append(cur)
        elif cur is None:
            intro.append(s)
        else:
            if s.startswith("- "):
                cur["items"].append(("li", s[2:].strip()))
            elif re.match(r"^（図\d+", s):
                cur["items"].append(("fig", s[1:-1] if s.endswith("）") else s[1:]))
            else:
                cur["items"].append(("p", s))
    nl = re.search(r"https://www\.linkedin\.com/newsletters/\d+/?", footer)
    return {"title": title, "issued": issued, "intro": " ".join(intro), "sections": sections,
            "newsletter": nl.group(0) if nl else ""}


def jp_date(iso):
    y, m, d = iso.split("-")
    return f"{y}年{int(m)}月{int(d)}日"


# ---------------------------------------------------------------- 図
def fig_sources(m):
    """図 f1..fN の PNG パスの dict。無ければ空。"""
    for d in glob.glob(os.path.join(FIGS, "*月報*", m["ym"], "figs")):
        got = {}
        for p in glob.glob(os.path.join(d, "f*.png")):
            mt = re.match(r"f(\d+)\.png$", os.path.basename(p))
            if mt:
                got[int(mt.group(1))] = p
        if got:
            return got
    return {}


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
"""

SEC_MORE = {"1": "three"}


def page_head(title, desc, path, jsonld):
    h = bmd.head(title, desc, path, jsonld)
    return h.replace("</style>", EXTRA_CSS + "</style>", 1)


def render_section(sec, figs, month_key, used):
    out = [f'<section class="md" id="s{sec["num"] or ""}"><div class="container rp-body">']
    if sec["num"]:
        out.append(f'<div class="section-label">{sec["num"].zfill(2)}</div>')
    out.append(f'<h2 class="md-h">{esc(sec["title"])}</h2>')
    items, i = sec["items"], 0
    first = sec["num"] == "1"
    prev_fig = False
    while i < len(items):
        kind, txt = items[i]
        if kind == "p":
            out.append(f"<p>{esc(txt)}</p>")
            prev_fig = False
        elif kind == "li":
            if txt.startswith("出典:") and prev_fig:
                out.append(f'<p class="md-note">{esc(txt)}</p>')
            else:
                j = i
                lis = []
                while j < len(items) and items[j][0] == "li" and not (items[j][1].startswith("出典:") and prev_fig):
                    lis.append(items[j][1]); j += 1
                cls = ' class="rp-three"' if first and lis else ""
                out.append(f"<ul{cls}>" + "".join(f"<li>{esc(t)}</li>" for t in lis) + "</ul>")
                i = j - 1
            prev_fig = False
        elif kind == "fig":
            n = int(re.match(r"図(\d+)", txt).group(1))
            src = figs.get(n)
            if src:
                used.add(n)
                out.append(f'<figure class="rp-fig"><img src="/report/{month_key}/f{n}.png" alt="{esc(txt)}" loading="lazy">'
                           f"<figcaption>{esc(txt)}</figcaption></figure>")
            prev_fig = True
        i += 1
    out.append("</div></section>")
    return "\n".join(out)


def render_month(m, doc, figs, page_imgs):
    key = m["key"]
    y, mo = key.split("-")
    path = f"/report/{key}"
    title_h = f"系統用蓄電池の月報 {y}年{int(mo)}月"
    title = f"{title_h}｜卸電気の価格・調整力市場・接続検討・土地の相談｜サイエンスエックス"
    s1 = next((s for s in doc["sections"] if s["num"] == "1"), None)
    moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("出典:")]
    desc = (f"{title_h}。" + (moves[0] if moves else doc["intro"]))[:160]
    pdf_name = f"scix-bess-monthly-{key}.pdf"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "Report", "@id": BASE + path + "#report", "url": BASE + path,
                "name": title_h, "description": desc, "inLanguage": "ja", "datePublished": doc["issued"],
                "dateModified": doc["issued"], "author": bmd.ORG, "publisher": bmd.ORG,
                "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{path}/{pdf_name}", "encodingFormat": "application/pdf"}}),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("レポート", BASE + "/report"), (title_h, BASE + path)])),
    ])
    used = set()
    secs = [render_section(s, figs, key, used) for s in doc["sections"]]
    gallery = ""
    if not figs and page_imgs:
        gallery = ('<section class="md"><div class="container rp-body"><h2 class="md-h">PDF の各ページ</h2>'
                   + "".join(f'<figure class="rp-fig"><img src="/report/{key}/p{n}.png" alt="月報 {y}年{int(mo)}月 {n}ページ" loading="lazy"></figure>'
                             for n in sorted(page_imgs)) + "</div></section>")
    nl = (f'<p>毎月の更新は、LinkedIn のニュースレター「系統用蓄電池の一次データ」でもお届けしています。'
          f'<a href="{esc(doc["newsletter"])}" rel="noopener" target="_blank">ニュースレターを購読する →</a></p>') if doc["newsletter"] else ""
    cite = f"""<section class="md"><div class="container rp-body">
  <div class="cite"><div class="cite-h">引用・転載について</div>
  図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。
  数字は公表データと当社の記録の集計で、試算は目安です。実際の収益を示すものでも、保証するものでもありません。前提は上の「試算の前提と用語」に書きました。</div>
  {nl}
</div></section>"""
    cta = """<section class="cta"><div class="container">
  <h2>この月報の数字の元になった案件を、買い手の方へ</h2>
  <p>当社の棚 DealRoom2 に登録（無料）すると、接続検討の回答書など、案件ごとの資料を申請できます。案件の一覧は、登録なしでご覧いただけます。</p>
  <a class="btn-primary" href="%s" target="_top" rel="nofollow">DealRoom に登録する →</a>
  <a class="btn-secondary" href="/projects">販売中の案件を見る</a>
</div></section>
""" % DR2_REGISTER
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("レポート", "/report"), (title_h, path)])}
<section class="hero"><div class="container">
  <span class="badge">毎月発行・出典つき</span>
  <div class="section-label">Monthly Report</div>
  <h1>{esc(title_h)}</h1>
  <p>{esc(doc["intro"])}</p>
  <p class="md-note">サイエンスエックス株式会社　発行 {jp_date(doc["issued"])}　A4・全{page_count(m)}ページ</p>
  <div class="rp-btns"><a class="btn-primary" href="{path}/{pdf_name}" download="系統用蓄電池の月報_{key}.pdf">PDF をダウンロード</a>
  <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/report">月報の一覧</a></div>
</div></section>
{chr(10).join(secs)}
{gallery}
{cite}
{cta}{bmd.FOOTER}
</body>
</html>
"""
    return page_head(title, desc, path, jsonld) + body, desc


_PAGES = {}


def page_count(m):
    if m["key"] not in _PAGES:
        out = subprocess.run(["pdfinfo", m["pdf"]], capture_output=True, text=True).stdout
        mt = re.search(r"Pages:\s+(\d+)", out)
        _PAGES[m["key"]] = int(mt.group(1)) if mt else 0
    return _PAGES[m["key"]]


def render_index(rows):
    path = "/report"
    title = "レポート｜系統用蓄電池の月報（卸電気の価格・調整力市場・接続検討・土地の相談）｜サイエンスエックス"
    desc = "公表データ（JEPX・EPRX）と当社の記録の集計から、系統用蓄電池の今月の動きを図でまとめた月報。毎月発行、出典つき、PDF あり。"
    jsonld = "\n".join([
        bmd.ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
                "name": title, "description": desc, "inLanguage": "ja", "publisher": bmd.ORG,
                "mainEntity": {"@type": "ItemList", "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": f"{BASE}/report/{r['key']}", "name": r["title_h"]}
                    for i, r in enumerate(rows)]}}),
        bmd.ld(bmd.crumbs([("ホーム", BASE + "/"), ("レポート", BASE + path)])),
    ])
    li = "".join(
        f'<li><a class="t" href="/report/{r["key"]}">{esc(r["title_h"])}</a>'
        f'<div class="d">発行 {jp_date(r["issued"])}・PDF あり</div><p>{esc(r["lead"])}</p></li>' for r in rows)
    body = f"""{bmd.nav_crumbs([("ホーム", "/"), ("レポート", path)])}
<section class="hero"><div class="container">
  <span class="badge">毎月発行</span>
  <div class="section-label">Report</div>
  <h1>系統用蓄電池の月報</h1>
  <p>電気の値段は使う時間で変わります。その差で働くのが系統用蓄電池です。公表されている数字（JEPX・EPRX）と、当社の記録の集計から、今月の動きを図でお伝えします。新しい月が上です。コラムとは別に、機械が毎月まとめる数字の報告です。</p>
</div></section>
<section class="md"><div class="container rp-body">
  <ul class="rp-list">{li}</ul>
  <p class="md-note" style="margin-top:16px">図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。売り案件の集計は <a href="/market-data">市場データ</a>（毎朝更新）に。</p>
</div></section>
{bmd.FOOTER}
</body>
</html>
"""
    return page_head(title, desc, path, jsonld) + body


# ---------------------------------------------------------------- 書き出し
def sitemap_add(text, rows):
    def ent(path, lastmod, pr):
        return (f'  <url><loc>{BASE}{path}</loc><xhtml:link rel="alternate" hreflang="ja" href="{BASE}{path}"/>'
                f"<priority>{pr}</priority><lastmod>{lastmod}</lastmod></url>\n")
    want = [("/report", rows[0]["issued"], "0.7")] + [(f"/report/{r['key']}", r["issued"], "0.6") for r in rows]
    add = "".join(ent(p, d, pr) for p, d, pr in want if f"<loc>{BASE}{p}</loc>" not in text)
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
            figs = fig_sources(m)
            page_imgs = {} if figs else render_pdf_pages(m["pdf"], tmp)
            html_, _ = render_month(m, doc, figs, page_imgs)
            d = f"report/{m['key']}"
            files[f"{d}/index.html"] = html_.encode("utf-8")
            files[f"{d}/scix-bess-monthly-{m['key']}.pdf"] = open(m["pdf"], "rb").read()
            for n, p in figs.items():
                files[f"{d}/f{n}.png"] = open(p, "rb").read()
            for n, p in page_imgs.items():
                files[f"{d}/p{n}.png"] = open(p, "rb").read()
            s1 = next((s for s in doc["sections"] if s["num"] == "1"), None)
            moves = [t for k, t in (s1["items"] if s1 else []) if k == "li" and not t.startswith("出典:")]
            y, mo = m["key"].split("-")
            rows.append({"key": m["key"], "issued": doc["issued"], "title_h": f"系統用蓄電池の月報 {y}年{int(mo)}月",
                         "lead": " ".join(moves[:2]) or doc["intro"]})
        files["report/index.html"] = render_index(rows).encode("utf-8")
        sm_path = os.path.join(ROOT, "sitemap.xml")
        sm = open(sm_path, encoding="utf-8").read()
        sm2 = sitemap_add(sm, rows)
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
