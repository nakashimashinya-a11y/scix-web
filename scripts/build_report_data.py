#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市場ノートの号（Drive の md）の「市場の数字」の表から、号をまたいだ推移の頁を焼く。build_reports.py の main から呼ぶ。

生成するもの（全文を書き直す。手で直さない）:
  report/data/index.html                 市場データ（卸電気のエリア別の月ごとの推移・容量市場・長期脱炭素電源オークション）
  report/data/*.csv                      上の表の CSV（UTF-8・BOM 付き）
  en/report/data/index.html, *.csv       英語版（英語の号の表の数字が日本語の号と一致するときだけ）
  report/area/<slug>/index.html          エリアの頁（AREA_PAGES に挙げたエリアだけ。日本語だけ）

数字の元は、号の頁と同じ md の表だけ（手で写さない・文の中の数字は読まない）。表の形で無い月・指標は空欄（—）にし、号へのリンクを置く。
説明の文は号の「前提と用語」と各節の冒頭の文をそのまま引く（新しく書くのは見出し・列名・リンクの文だけ）。

需給調整市場（EPRX）の表は、既定では出さない（SCIX_REPORT_DATA_EPRX=1 のときだけ焼く）。号の頁へのリンクだけを置く。
JEPX は出所の明示で利用可、OCCTO は出典の記載で利用可（編集・加工したときはその旨も書く）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import html
import json
import urllib.parse
import os
import re

SHOW_EPRX = os.environ.get("SCIX_REPORT_DATA_EPRX") == "1"
AREA_PAGES = [("東京", "tokyo"), ("九州", "kyushu")]   # エリアの頁を作るエリア（9つに広げるときはここに足す）
AREAS_JA = ["システム（全国）", "北海道", "東北", "東京", "中部", "北陸", "関西", "中国", "四国", "九州"]
AREA_EN = {"北海道": "Hokkaido", "東北": "Tohoku", "東京": "Tokyo", "中部": "Chubu", "北陸": "Hokuriku", "関西": "Kansai",
           "中国": "Chugoku", "四国": "Shikoku", "九州": "Kyushu"}
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MON_EN_S = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

JEPX_URL = "https://www.jepx.jp/electricpower/market-data/spot/"
EPRX_URL = "https://www.eprx.or.jp/information/results.php"
CATALOG = "https://dealroom.scix.co.jp/"

# 号の表の見出し（この並びのときだけ読む。変わったら読まずに知らせる）
JEPX_HEAD = ["エリア", "月平均", "前年同月", "日中（8〜16時）", "夕方（16〜20時）", "4時間の値差", "最高", "30円以上のコマ", "0.01円のコマ"]
JEPX_KEYS = ["avg", "yoy", "day", "eve", "s4", "max", "n30", "n001"]
SPREAD_HEAD = ["エリア", "2時間の値差（円/kWh）", "4時間の値差（円/kWh）", "4時間の値差が10円以上の日"]
SPREAD_KEYS = ["s2", "s4b", "d10"]
EPRX_HEAD = ["商品", "募集量（MW）", "応札量（MW）", "落札量（MW）", "応札倍率（応札÷募集）", "約定率（落札÷応札）", "平均落札価格（円/kW・30分）", "蓄電池の割合"]
EPRX_KEYS = ["req", "bid", "won", "ratio", "rate", "price", "batt"]

# 列名（見出しと列名は自分で付けてよい）
LBL = {
    "ja": {"avg": "月平均", "yoy": "前年同月", "day": "日中（8〜16時）", "eve": "夕方（16〜20時）", "s4": "4時間の値差", "s2": "2時間の値差",
           "max": "最高", "n30": "30円以上のコマ", "n001": "0.01円のコマ", "d10": "4時間の値差が10円以上の日",
           "req": "募集量（MW）", "bid": "応札量（MW）", "won": "落札量（MW）", "ratio": "応札倍率", "rate": "約定率",
           "price": "平均落札価格（円/kW・30分）", "batt": "蓄電池の割合"},
    "en": {"avg": "Monthly average", "yoy": "Same month last year", "day": "Daytime (8:00–16:00)", "eve": "Evening (16:00–20:00)",
           "s4": "4-hour spread", "s2": "2-hour spread", "max": "Highest", "n30": "Slots at 30 yen or more", "n001": "Slots at 0.01 yen",
           "d10": "Days with a 4-hour spread of 10 yen or more", "req": "Procured (MW)", "bid": "Bid (MW)", "won": "Awarded (MW)",
           "ratio": "Bid ratio", "rate": "Award rate", "price": "Average winning price (yen/kW per 30 min)", "batt": "Battery share"},
}
C_PURPLE, C_ORANGE, C_BLUE, C_GREEN, C_GRAY, C_PINK = "#5B32B5", "#C2560A", "#1D4ED8", "#0F7A52", "#8C96A8", "#BE185D"

CSS = """
.rd-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:18px 0 6px;max-width:980px}
.rd-kpi div{background:#fff;border-radius:var(--m-r,18px);box-shadow:var(--m-shadow,0 8px 22px rgba(31,42,72,.08));padding:14px 16px 14px;border-top:6px solid var(--cc,#7C4DDB)}
.rd-kpi div:nth-child(4n+2){--cc:#EA580C}.rd-kpi div:nth-child(4n+3){--cc:#059669}.rd-kpi div:nth-child(4n+4){--cc:#2563EB}
.rd-kpi b{display:block;font-family:var(--m-num,'Inter Tight',sans-serif);font-weight:900;font-size:clamp(1.5rem,3vw,2.1rem);line-height:1.15;color:var(--m-ink,#0B1530);letter-spacing:-.02em}
.rd-kpi b small{font-family:'Noto Sans JP',sans-serif;font-size:.8rem;font-weight:700;color:var(--m-muted,#4A5568);margin-left:3px;letter-spacing:0}
.rd-kpi span{display:block;font-size:.82rem;font-weight:700;color:var(--m-muted,#4A5568);margin-top:6px;line-height:1.5}
.rd-kpi i{display:block;font-style:normal;font-size:.8rem;color:var(--m-muted,#4A5568);margin-top:2px}
.rd-kpi i{color:var(--acc-2,#5B32B5);font-weight:700}
.rd-card{background:#fff;border-radius:var(--m-r,18px);box-shadow:var(--m-shadow,0 8px 22px rgba(31,42,72,.08));padding:14px 16px 10px;margin:16px 0;max-width:980px}
.rd-card h3{font-size:.98rem;font-weight:800;color:var(--m-ink,#0B1530);margin:0 0 6px}
.rd-card svg{display:block;width:100%;height:auto}
.rd-card svg{max-width:640px}.rd-card svg.rd-bar{max-width:520px}
.rd-two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;max-width:1000px;margin:16px 0}.rd-two .rd-card{margin:0}
#jepx .rp-body,#capacity .rp-body,#eprx .rp-body,#projects .rp-body{max-width:1000px}
.rd-t{max-width:1000px!important}.rd-t table th,.rd-t table td{padding:6px 8px}
.rd-sm{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;max-width:980px;margin:14px 0}
.rd-sm figure{background:#fff;border-radius:14px;box-shadow:var(--m-shadow,0 8px 22px rgba(31,42,72,.08));padding:10px 10px 6px;margin:0}
.rd-sm figcaption{font-size:.9rem;font-weight:800;color:var(--m-ink,#0B1530);margin:0 0 2px 4px}
.rd-sm figcaption a{color:inherit}
.rd-sm svg{display:block;width:100%;height:auto}
.rd-lg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.84rem;color:var(--m-body,#24304A);margin:6px 0 2px}
.rd-lg span{display:inline-flex;align-items:center;gap:6px}
.rd-lg span::before{content:"";display:inline-block;width:18px;height:4px;border-radius:2px;background:var(--c)}
.rd-lg span.dash::before{background:repeating-linear-gradient(90deg,var(--c) 0 5px,transparent 5px 8px)}
.rd-def{max-width:860px;margin:10px 0;padding:10px 16px;background:var(--acc-soft,#F2EDFF);border-radius:14px;font-size:.88rem;line-height:1.85;color:var(--m-body,#24304A)}
.rd-def p{margin:4px 0}.rd-def b{color:var(--m-ink,#0B1530)}
.rd-src{font-size:.82rem;color:var(--m-muted,#4A5568);max-width:860px;margin:6px 0 4px;line-height:1.75}
.rd-src a{color:var(--acc-2,#5B32B5)}
.rd-dl{display:inline-block;margin:4px 0 2px;font-size:.86rem;font-weight:700;color:var(--acc-2,#5B32B5)!important;border:2px solid var(--acc,#7C4DDB);border-radius:999px;padding:5px 14px;text-decoration:none}
.rd-t table th:first-child,.rd-t table td:first-child{position:sticky;left:0;z-index:1}
.rd-t caption{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.rd-t table tbody th[scope=row]{background:#fff!important;color:var(--m-ink,#0B1530)!important;font-weight:700!important;text-align:left;vertical-align:baseline;border-bottom:1px solid var(--border)!important;padding:6px 8px;min-width:0;max-width:none;white-space:nowrap}
.rd-t table tbody tr:nth-child(even) th[scope=row]{background:var(--off-white,#F2F6FF)!important}
.rd-t table tr.rd-delta th[scope=row]{border-top:2px solid var(--m-line,#E3E8F2)}
.rd-t table th[scope=row] a{color:var(--acc-2,#5B32B5)}
.rd-latest{max-width:860px;font-size:.95rem;line-height:1.85;color:var(--m-body,#24304A)}
.rd-t table td:first-child{background:#fff;font-weight:700;color:var(--m-ink,#0B1530)}
.rd-t table tbody tr:nth-child(even) td:first-child{background:var(--off-white,#F2F6FF)}
.rd-t table td a{color:var(--acc-2,#5B32B5)}
.rd-t table tr.rd-delta td{font-weight:700;border-top:2px solid var(--m-line,#E3E8F2)}
.rd-quote{max-width:860px;list-style:none;padding:0;margin:10px 0}
.rd-quote li{background:#fff;border-radius:14px;box-shadow:var(--m-shadow,0 8px 22px rgba(31,42,72,.08));padding:10px 16px;margin:10px 0;line-height:1.85;font-size:.92rem}
.rd-quote li a{display:block;font-size:.82rem;font-weight:700;color:var(--acc-2,#5B32B5);margin-top:2px}
.rd-links{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.rd-links a{display:inline-block;background:#fff;border-radius:999px;box-shadow:var(--m-shadow,0 8px 22px rgba(31,42,72,.08));padding:8px 16px;font-weight:700;font-size:.9rem;color:var(--m-ink,#0B1530);text-decoration:none}
.rd-links a:hover{color:var(--acc-2,#5B32B5)}
.rd-toc{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.rd-toc a{background:rgba(255,255,255,.85);border-radius:999px;padding:6px 14px;font-weight:700;font-size:.86rem;color:var(--m-ink,#0B1530)!important;text-decoration:none!important}
@media(max-width:640px){.rd-kpi{grid-template-columns:1fr 1fr;gap:10px}.rd-kpi b{font-size:1.45rem}.rd-card{padding:12px 10px 8px}}
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def num(s):
    """表の文字（1,388.7・123.1%・—）を数に。読めなければ None。"""
    t = str(s).replace(",", "").replace("%", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def csv_val(s):
    """CSV には桁区切りを外した数を書く（% も外す）。"""
    return str(s).replace(",", "").replace("%", "").strip()


# ---------------------------------------------------------------- 号の表を読む
def _tables(doc, src_prefix):
    """(節, 表の前の文, 行, 表の後の出典の行) を順に返す。"""
    for s in doc["sections"]:
        items = s["items"]
        cap, before = "", ""
        for i, (kind, t) in enumerate(items):
            if kind == "table":
                src = ""
                for k2, t2 in items[i + 1:]:
                    if k2 == "table":
                        break
                    if k2 == "li" and t2.startswith(src_prefix):
                        src = t2
                        break
                yield s, cap, t, (src or before)
                before = ""
            elif kind in ("p", "li"):
                cap = t
                if kind == "li" and t.startswith(src_prefix):
                    before = t


def ym_ja(cap):
    mt = re.search(r"(\d{4})年(\d{1,2})月", cap)
    return f"{mt.group(1)}-{int(mt.group(2)):02d}" if mt else None


def ym_en(cap):
    mt = re.search(r"\((" + "|".join(MONTHS_EN) + r") (\d{4})", cap)
    return f"{mt.group(2)}-{MONTHS_EN.index(mt.group(1)) + 1:02d}" if mt else None


def read_issue(doc, lang="ja"):
    """1号の md から {jepx:{ym, rows}, spread:{rows}, eprx:{ym, rows}, cap:[...], lda:[...], src:{...}} を作る。読めない表は入れない。"""
    out = {"src": {}, "warn": []}
    pre = "出典:" if lang == "ja" else "Source"
    for sec, cap, rows, src in _tables(doc, pre):
        head = rows[0]
        if lang == "ja":
            is_jepx, is_spread = head[:2] == JEPX_HEAD[:2], head[:2] == SPREAD_HEAD[:2]
            is_eprx, is_cap, is_lda = head[:2] == EPRX_HEAD[:2], head[0] == "実需給年度", head[0] == "応札年度"
            if is_jepx and head != JEPX_HEAD or is_spread and head != SPREAD_HEAD or is_eprx and head != EPRX_HEAD:
                out["warn"].append(f"表の見出しが変わった: {head}")
                continue
            ym = ym_ja(cap)
        else:
            is_jepx = head[0] == "Area" and head[1] == "Monthly average" and len(head) == len(JEPX_HEAD)
            is_spread = head[0] == "Area" and "2-hour" in head[1] and len(head) == len(SPREAD_HEAD)
            is_eprx = head[0] == "Product" and len(head) == len(EPRX_HEAD)
            is_cap = head[0].strip() == "Delivery fiscal year" and len(head) == 10        # 追加オークションの表（見出しが "Delivery fiscal year of the additional auction"）はメインの表と取り違えない（2026-11-23）
            is_lda = len(head) == 3 and "Long-Term" in cap and "Decarbon" in cap
            ym = ym_en(cap)
        body = rows[1:]
        if is_jepx and ym:
            out["jepx"] = {"ym": ym, "rows": [(r[0], dict(zip(JEPX_KEYS, r[1:]))) for r in body]}
            out["src"]["jepx"] = src
            out.setdefault("market_sec", sec["num"])
        elif is_spread:
            out["spread"] = {"rows": [(r[0], dict(zip(SPREAD_KEYS, r[1:]))) for r in body], "sec": sec["num"]}
            out["src"]["spread"] = src
        elif is_eprx and ym:
            out["eprx"] = {"ym": ym, "rows": [(r[0], dict(zip(EPRX_KEYS, r[1:]))) for r in body]}
            out["src"]["eprx"] = src
            out.setdefault("market_sec", sec["num"])
        elif is_cap:
            out["cap"] = {"head": head, "rows": body}
        elif is_lda:
            out["lda"] = {"head": head, "rows": body}
            out["src"]["occto"] = src
    return out


def terms(doc):
    """「前提と用語」（最後の節）の箇条。"""
    sec = doc["sections"][-1] if doc["sections"] else {"items": []}
    return [t for k, t in sec["items"] if k == "li"]


def find_term(doc, *starts):
    return next((t for t in terms(doc) if any(t.startswith(s) for s in starts)), "")


def sec_by(doc, pat):
    return next((s for s in doc["sections"] if re.search(pat, s["title"])), None)


def first_p(sec):
    return next((t for k, t in (sec["items"] if sec else []) if k == "p"), "")


def sentences(text, n, lang="ja"):
    """文の頭から n 文（言い換えない・切るだけ）。"""
    parts = re.findall(r"[^。]+。", text) if lang == "ja" else re.findall(r"[^.]+(?:\.(?=\s|$))", text)
    return ("" if lang == "ja" else " ").join(p.strip() for p in parts[:n])


def occto_urls(doc, lang="ja"):
    """前提と用語の OCCTO の出典の行から、{年度: URL}（容量市場）と {応札年度: URL}（長期脱炭素）を取る。"""
    capu, ldau = {}, {}
    for t in terms(doc):
        if "OCCTO" not in t:
            continue
        pairs = re.findall(r"(\d{4})\D{0,12}?\s*(https://\S+?\.pdf)", t)
        if not pairs:
            continue
        if ("容量市場の約定結果" in t) or ("capacity market clearing" in t):
            capu = {y: u for y, u in pairs}
        elif ("長期脱炭素" in t) or ("Long-Term" in t):
            ldau = {y: u for y, u in pairs}
    return capu, ldau


# ---------------------------------------------------------------- まとめる
def collect(months, docs, lang="ja"):
    """号（新しい順）→ 月ごとの数字。同じ月が2つの号にあれば新しい号を採る。"""
    jepx, eprx, warn, secmap = {}, {}, [], {}
    latest = None
    for m in months:
        doc = docs.get(m["key"] + (":en" if lang == "en" else ""))
        if not doc:
            continue
        iss = read_issue(doc, lang)
        secmap[m["key"]] = iss.get("market_sec")            # 「市場の数字」の節の番号は号ごとに違う（2026-11-23〜 途中経過・データの時点の節が増えた）
        warn += [f"{m['key']} {lang}: {w}" for w in iss["warn"]]
        if latest is None:
            latest = {"key": m["key"], "doc": doc, "iss": iss}
        if "jepx" in iss and iss["jepx"]["ym"] not in jepx:
            rows = {}
            sp = {a: v for a, v in iss.get("spread", {}).get("rows", [])}
            for a, v in iss["jepx"]["rows"]:
                d = dict(v)
                d.update(sp.get(a, {}))
                rows[a] = d
            jepx[iss["jepx"]["ym"]] = {"issue": m["key"], "issued": doc["issued"], "rows": rows, "sec": iss.get("market_sec"),
                                        "order": [a for a, _ in iss["jepx"]["rows"]], "spread_sec": iss.get("spread", {}).get("sec", "")}
        if "eprx" in iss and iss["eprx"]["ym"] not in eprx:
            eprx[iss["eprx"]["ym"]] = {"issue": m["key"], "issued": doc["issued"], "rows": dict(iss["eprx"]["rows"]), "sec": iss.get("market_sec"),
                                        "order": [a for a, _ in iss["eprx"]["rows"]]}
    return {"jepx": jepx, "eprx": eprx, "latest": latest, "warn": warn, "secmap": secmap}


def month_range(keys):
    if not keys:
        return []
    ks = sorted(keys)
    y, m = map(int, ks[0].split("-"))
    out = []
    while f"{y}-{m:02d}" <= ks[-1]:
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def ym_label(ym, lang="ja", short=False):
    y, m = ym.split("-")
    if lang == "ja":
        return f"{int(m)}月" if short else f"{y}年{int(m)}月"
    return MON_EN_S[int(m) - 1] if short else f"{MON_EN_S[int(m) - 1]} {y}"


def issue_label(key, lang="ja"):
    y, m = key.split("-")
    return f"{y}年{int(m)}月号" if lang == "ja" else f"{MON_EN_S[int(m) - 1]} {y} issue"


# ---------------------------------------------------------------- 図（SVG）
def nice_step(span, n=4):
    if span <= 0:
        return 1.0
    raw = span / n
    k = 10 ** int(f"{raw:e}".split("e")[1])
    for f in (1, 2, 2.5, 5, 10):
        if raw <= f * k:
            return f * k
    return 10 * k


def fmt_tick(v, step):
    if step >= 1:
        return f"{v:,.0f}"
    return f"{v:,.1f}" if step >= 0.1 else f"{v:,.2f}"


def svg_line(xlabels, series, w=640, h=300, ymax=None, aria="", end_labels=True, ref=None, unit_fmt="{:.2f}", fs=13, tick_sfx=""):
    """折れ線。series=[(名前, 色, [値 or None], 破線か)]。ref=(値, 文字) は横の基準線。"""
    vals = [v for _, _, vs, _ in series for v in vs if v is not None] + ([ref[0]] if ref else [])
    hi = max(vals) if vals else 1
    if ymax:
        hi = max(hi, ymax)
    step = nice_step(hi)
    top = step * (int(hi / step) + (0 if hi % step == 0 and hi > 0 else 1))
    L, R, T, B = (fs * (3.6 + 0.5 * len(tick_sfx))), (fs * 4.2 if end_labels or ref else fs * 1.2), fs * 0.9, fs * 2.3
    pw, ph = w - L - R, h - T - B
    n = len(xlabels)

    def X(i):
        return L + (pw * i / (n - 1) if n > 1 else pw / 2)

    def Y(v):
        return T + ph * (1 - v / top) if top else T + ph
    o = [f'<svg viewBox="0 0 {w} {h:.0f}" role="img" aria-label="{esc(aria)}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="Noto Sans JP, sans-serif" font-size="{fs}"><title>{esc(aria)}</title>']
    t = 0.0
    while t <= top + 1e-9:
        y = Y(t)
        o.append(f'<line x1="{L:.1f}" x2="{w - R:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="#E3E8F2" stroke-width="1"/>'
                 f'<text x="{L - 6:.1f}" y="{y + fs * 0.35:.1f}" text-anchor="end" fill="#5B667A">{fmt_tick(t, step)}{tick_sfx}</text>')
        t += step
    if ref:
        y = Y(ref[0])
        o.append(f'<line x1="{L:.1f}" x2="{w - R:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="#B42318" stroke-width="1.5" stroke-dasharray="5 4"/>'
                 f'<text x="{w - R + 4:.1f}" y="{y + fs * 0.35:.1f}" fill="#B42318">{esc(ref[1])}</text>')
    for i, lb in enumerate(xlabels):
        o.append(f'<text x="{X(i):.1f}" y="{h - B + fs * 1.45:.1f}" text-anchor="middle" fill="#5B667A">{esc(lb)}</text>')
    ends = []
    for name, color, vs, dash in series:
        seg, segs = [], []
        for i, v in enumerate(vs):
            if v is None:
                if seg:
                    segs.append(seg)
                seg = []
            else:
                seg.append((X(i), Y(v)))
        if seg:
            segs.append(seg)
        da = ' stroke-dasharray="6 4"' if dash else ""
        for sg in segs:
            if len(sg) > 1:
                o.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.6" stroke-linejoin="round"{da} points="'
                         + " ".join(f"{x:.1f},{y:.1f}" for x, y in sg) + '"/>')
            for x, y in sg:
                o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        last = next(((i, v) for i, v in reversed(list(enumerate(vs))) if v is not None), None)
        if last and end_labels:
            ends.append([Y(last[1]), unit_fmt.format(last[1]), color, X(last[0])])
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):                     # 右端の値の字が重ならないように下へずらす
        if ends[i][0] - ends[i - 1][0] < fs * 1.15:
            ends[i][0] = ends[i - 1][0] + fs * 1.15
    for y, txt, color, x in ends:
        o.append(f'<text x="{x + 7:.1f}" y="{y + fs * 0.35:.1f}" fill="{color}" font-weight="700">{esc(txt)}</text>')
    o.append("</svg>")
    return "".join(o)


def svg_hbar(rows, w=420, color=C_PURPLE, aria="", fs=14, label_w=None, stack=False):
    """横棒。rows=[(ラベル, 値, 字)]。stack=True はラベルを棒の上に置く（長いラベル用）。"""
    vals = [v for _, v, _ in rows if v is not None]
    hi = max(vals) if vals else 1
    lw = 0 if stack else (label_w or fs * 4.6)
    rh = fs * (3.1 if stack else 2.2)
    h = rh * len(rows) + fs * 0.6
    pw = w - lw - fs * 4.4
    o = [f'<svg class="rd-bar" viewBox="0 0 {w} {h:.0f}" role="img" aria-label="{esc(aria)}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="Noto Sans JP, sans-serif" font-size="{fs}"><title>{esc(aria)}</title>']
    for i, (lb, v, txt) in enumerate(rows):
        y = fs * 0.3 + i * rh
        if stack:
            o.append(f'<text x="0" y="{y + fs * 1.0:.1f}" fill="#24304A">{esc(lb)}</text>')
            by, bh = y + fs * 1.45, fs * 1.1
        else:
            o.append(f'<text x="{lw - 8:.1f}" y="{y + rh * 0.62:.1f}" text-anchor="end" fill="#24304A">{esc(lb)}</text>')
            by, bh = y + rh * 0.2, rh * 0.6
        if v is not None:
            bw = max(pw * v / hi if hi else 0, 2)
            o.append(f'<rect x="{lw:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{bh / 2:.1f}" fill="{color}"/>'
                     f'<text x="{lw + bw + 6:.1f}" y="{by + bh * 0.82:.1f}" fill="#0B1530" font-weight="700">{esc(txt)}</text>')
    o.append("</svg>")
    return "".join(o)


def legend(items):
    return '<div class="rd-lg">' + "".join(
        f'<span class="{"dash" if d else ""}" style="--c:{c}">{esc(n)}</span>' for n, c, d in items) + "</div>"


# ---------------------------------------------------------------- 部品
def delta(cur, prev, unit, lang="ja"):
    a, b = num(cur), num(prev)
    if a is None or b is None:
        return ""
    d = a - b
    cls = "up" if d > 0 else ("down" if d < 0 else "")
    txt = f"前月から {d:+.2f}{unit}" if lang == "ja" else f"{d:+.2f} {unit} vs. previous month"
    return f'<i class="{cls}">{esc(txt)}</i>'


def kpi(items):
    """items=[(値, 単位, ラベル, 前月差の html)]"""
    return '<div class="rd-kpi">' + "".join(
        f"<div><b>{esc(v)}<small>{esc(u)}</small></b><span>{esc(lb)}</span>{d}</div>" for v, u, lb, d in items) + "</div>"


def table(head, rows, data_keys=None, delta_row=None, caption=None):
    """表（横に送れる箱）。rows=[[セルの html…]]、data_keys=[[data-k…]]（突き合わせ用）。
    caption＝表の題（画面では隠す・読み上げと検索エンジン向け）。見出しの th は scope=col、1列目の行見出しは th scope=row（2026-11-22 中島「Seo 対策も徹底してやって」）。"""
    num_re = re.compile(r"^[-−—+\d,.%]+$")
    o = ['<div class="rp-table rd-t"><table>' + (f"<caption>{esc(caption)}</caption>" if caption else "")
         + '<thead><tr>' + "".join(f'<th scope="col">{esc(h)}</th>' for h in head) + "</tr></thead><tbody>"]
    for i, r in enumerate(rows):
        cells = []
        for j, c in enumerate(r):
            plain = re.sub(r"<[^>]+>", "", c)
            cls = ' class="rp-n"' if j and num_re.match(plain) else ""
            dk = f' data-k="{esc(data_keys[i][j])}"' if data_keys and data_keys[i][j] else ""
            cells.append(f'<th scope="row"{dk}>{c}</th>' if j == 0 else f"<td{cls}{dk}>{c}</td>")
        o.append("<tr>" + "".join(cells) + "</tr>")
    if delta_row:
        o.append('<tr class="rd-delta">' + "".join(f'<th scope="row">{esc(c)}</th>' if j == 0 else f'<td class=rp-n>{esc(c)}</td>'
                                                   for j, c in enumerate(delta_row)) + "</tr>")
    o.append("</tbody></table></div>")
    return "".join(o)


def month_cell(ym, rec, base, sec="s17", lang="ja"):
    t = f'<time datetime="{ym}">{esc(ym_label(ym, lang))}</time>'
    if not rec:
        return t
    if rec.get("sec"):
        sec = "s" + str(rec["sec"])
    return f'<a href="{base}/{rec["issue"]}#{sec}">{t}</a>'


def src_line(text, links, lang="ja"):
    """出典の行（号の文そのまま）＋公表元へのリンク。"""
    t = re.sub(r"^(出典:|Source:?)\s*", "", text or "")
    lead = "出典: " if lang == "ja" else "Source: "
    lk = "".join(f'　<a href="{esc(u)}" rel="noopener" target="_blank">{esc(n)}</a>' for n, u in links)
    return f'<p class="rd-src">{lead}{esc(t)}{lk}</p>'


# ---------------------------------------------------------------- 頁
def latest_jepx_sentence(lang, ym, area, avg, s4, unit, source):
    """表のいちばん新しい行から機械で作る1文（何の値・いつ・単位・出どころ）。数字は表のセルと同じ文字列（assert_in_table で確かめる）。"""
    if avg is None or s4 is None:
        return ""
    if lang == "ja":
        t = f"{ym_label(ym)}の{area}の卸電気（JEPX）の月平均は{avg}{unit}、4時間の値差は{s4}{unit}でした（出典: {source}）。"
    else:
        t = f"In {ym_label(ym, 'en')}, the JEPX monthly average for {area} was {avg} {unit} and the 4-hour spread was {s4} {unit} (source: {source})."
    return f'<p class="rd-latest" data-latest="jepx">{esc(t)}</p>'


def latest_cap_sentence(lang, year, a_hi, v_hi, a_lo, v_lo, unit, source, area_only=None):
    """容量市場のいちばん新しい実需給年度の行から機械で作る1文。"""
    if lang == "ja":
        t = (f"{year}の容量市場メインオークションのエリアプライスは、{area_only}が{v_hi}{unit}でした（出典: {source}）。" if area_only else
             f"{year}の容量市場メインオークションのエリアプライスは、いちばん高い{a_hi}が{v_hi}{unit}、いちばん低い{a_lo}が{v_lo}{unit}でした（出典: {source}）。")
    else:
        t = (f"The main auction area price for {year} was {v_hi} {unit} in {area_only} (source: {source})." if area_only else
             f"For {year}, the main auction area price was highest in {a_hi} at {v_hi} {unit} and lowest in {a_lo} at {v_lo} {unit} (source: {source}).")
    return f'<p class="rd-latest" data-latest="capacity">{esc(t)}</p>'


def jepx_section(data, lang, base, latest_doc, csv_href, area_order, area_names):
    """②卸電気。全エリアの推移（小さな図を並べる）と、月平均・4時間・2時間の値差の表。"""
    J = data["jepx"]
    yms = month_range(J.keys())
    if not yms:
        return ""
    last, prev = yms[-1], (yms[-2] if len(yms) > 1 else None)
    LB = LBL[lang]
    unit = "円/kWh" if lang == "ja" else "yen/kWh"
    sysn = area_order[0]

    def v(ym, a, k):
        return ((J.get(ym) or {}).get("rows", {}).get(a) or {}).get(k)
    sec10 = sec_by(latest_doc, r"^②.*(平均の値段|Average prices)")
    intro = first_p(sec10)
    t_avg = find_term(latest_doc, "平均価格は", "Average prices are")
    t_spr = find_term(latest_doc, "値差:", "Spread:")
    # 大きな数字（いちばん新しい月）
    big_s4 = max((a for a in area_order[1:] if num(v(last, a, "s4")) is not None), key=lambda a: num(v(last, a, "s4")), default=None)
    ks = [(v(last, sysn, "avg"), unit, f"{area_names[sysn]} {LB['avg']}（{ym_label(last, lang)}）" if lang == "ja" else f"{area_names[sysn]}, {LB['avg']} ({ym_label(last, lang)})",
           delta(v(last, sysn, "avg"), v(prev, sysn, "avg") if prev else None, "円" if lang == "ja" else "yen", lang)),
          (v(last, sysn, "s4"), unit, f"{area_names[sysn]} {LB['s4']}" if lang == "ja" else f"{area_names[sysn]}, {LB['s4']}",
           delta(v(last, sysn, "s4"), v(prev, sysn, "s4") if prev else None, "円" if lang == "ja" else "yen", lang))]
    for a in ("東京", "九州") if lang == "ja" else ("Tokyo", "Kyushu"):
        if a in area_order:
            ks.append((v(last, a, "s4"), unit, f"{area_names[a]} {LB['s4']}" if lang == "ja" else f"{area_names[a]}, {LB['s4']}",
                       delta(v(last, a, "s4"), v(prev, a, "s4") if prev else None, "円" if lang == "ja" else "yen", lang)))
    # 小さな図（エリアごと・月平均・前年同月・4時間の値差）
    xl = [ym_label(y, lang, True) for y in yms]
    ymax = max([num(v(y, a, k)) or 0 for y in yms for a in area_order for k in ("avg", "yoy", "s4")] or [1])
    panels = []
    for a in area_order:
        ser = [(LB["avg"], C_PURPLE, [num(v(y, a, "avg")) for y in yms], False),
               (LB["yoy"], C_GRAY, [num(v(y, a, "yoy")) for y in yms], True),
               (LB["s4"], C_ORANGE, [num(v(y, a, "s4")) for y in yms], False)]
        aria = (f"{area_names[a]}の卸電気の月平均・前年同月・4時間の値差（円/kWh・{ym_label(yms[0])}〜{ym_label(last)}）" if lang == "ja"
                else f"{area_names[a]}: JEPX monthly average, same month last year and 4-hour spread (yen/kWh, {ym_label(yms[0], 'en')}–{ym_label(last, 'en')})")
        slug = dict((x[0], x[1]) for x in AREA_PAGES).get(a) if lang == "ja" else None
        cap = f'<a href="/report/area/{slug}">{esc(area_names[a])}</a>' if slug else esc(area_names[a])
        panels.append(f"<figure><figcaption>{cap}</figcaption>"
                      + svg_line(xl, ser, w=330, h=210, ymax=ymax, aria=aria, end_labels=False, fs=14) + "</figure>")
    lg = legend([(LB["avg"], C_PURPLE, False), (LB["yoy"], C_GRAY, True), (LB["s4"], C_ORANGE, False)])

    def matrix(k):
        head = [("月" if lang == "ja" else "Month")] + [area_names[a] for a in area_order]
        rows, dks = [], []
        cap = (f"エリア別の卸電気の{LB[k]}（{unit}）の月ごとの推移（{ym_label(yms[0])}〜{ym_label(last)}）" if lang == "ja"
               else f"JEPX {LB[k].lower()} by area ({unit}), monthly, {ym_label(yms[0], 'en')} to {ym_label(last, 'en')}")
        for y in yms:
            rec = J.get(y)
            rows.append([month_cell(y, rec, base, "s17", lang)] + [esc(v(y, a, k) or "—") for a in area_order])
            dks.append([""] + [f"jepx|{y}|{a if lang == 'ja' else AREAS_JA[area_order.index(a)]}|{k}" if v(y, a, k) else "" for a in area_order])
        dr = None
        if prev:
            dr = [("前月差" if lang == "ja" else "Change from previous month")]
            for a in area_order:
                x1, x0 = num(v(last, a, k)), num(v(prev, a, k))
                dr.append(f"{x1 - x0:+.2f}" if x1 is not None and x0 is not None else "—")
        return table(head, rows, dks, dr, caption=cap)
    full_head = [("エリア" if lang == "ja" else "Area")] + [LB[k] for k in JEPX_KEYS + ["s2", "d10"]]
    full_rows = [[esc(area_names[a])] + [esc(v(last, a, k) or "—") for k in JEPX_KEYS + ["s2", "d10"]] for a in area_order]
    full_dk = [[""] + [f"jepx|{last}|{a if lang == 'ja' else AREAS_JA[area_order.index(a)]}|{k}" if v(last, a, k) else "" for k in JEPX_KEYS + ["s2", "d10"]] for a in area_order]
    rec_last = J[last]
    src = src_line(data["latest"]["iss"]["src"].get("jepx", ""), [("JEPX スポット市場" if lang == "ja" else "JEPX spot market", JEPX_URL)], lang)
    src2 = src_line(data["latest"]["iss"]["src"].get("spread", ""), [("JEPX スポット市場" if lang == "ja" else "JEPX spot market", JEPX_URL)], lang)
    dl = f'<a class="rd-dl" href="{csv_href}" download>{"CSV をダウンロード（月×エリア・全指標）" if lang == "ja" else "Download CSV (month × area, all measures)"}</a>'
    h = {"ja": ("②卸電気（JEPX）｜エリア別の月平均と値差", "エリアごとの推移", f"月平均（{unit}）", f"4時間の値差（{unit}）", f"2時間の値差（{unit}）",
                f"{ym_label(last)}のエリア別の数字（{unit}）", "定義"),
         "en": ("② Wholesale electricity (JEPX): monthly averages and spreads by area", "Trend by area", f"Monthly average ({unit})",
                f"4-hour spread ({unit})", f"2-hour spread ({unit})", f"Figures by area for {ym_label(last, 'en')} ({unit})", "Definitions")}[lang]
    issue_link = f'<a href="{base}/{rec_last["issue"]}#s{rec_last.get("sec") or "17"}">{esc(issue_label(rec_last["issue"], lang))}</a>'
    latest = latest_jepx_sentence(lang, last, area_names[sysn], v(last, sysn, "avg"), v(last, sysn, "s4"), unit, "JEPX スポット市場" if lang == "ja" else "JEPX spot market")
    return f"""<section class="md" id="jepx"><div class="container rp-body">
  <h2 class="md-h">{esc(h[0])}</h2>
  {latest}
  <p>{esc(intro)}</p>
  {kpi(ks)}
  <div class="rd-def"><p><b>{esc(h[6])}</b></p><p>{esc(t_avg)}</p><p>{esc(t_spr)}</p></div>
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(h[1])}</h3>
  {lg}
  <div class="rd-sm">{"".join(panels)}</div>
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(h[2])}</h3>
  {matrix("avg")}
  {src}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(h[3])}</h3>
  {matrix("s4")}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(h[4])}</h3>
  {matrix("s2")}
  {src2}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(h[5])}</h3>
  {table(full_head, full_rows, full_dk, caption=h[5])}
  <p class="rd-src">{"載った号" if lang == "ja" else "Issue"}: {issue_link}</p>
  {dl}
</div></section>"""


def cap_lda_section(data, lang, base, latest_doc, csv_cap, csv_lda, area_only=None, area_names=None):
    """③容量市場・長期脱炭素電源オークション（いちばん新しい号の表のまま）。area_only を渡すとそのエリアの列だけ。"""
    iss = data["latest"]["iss"]
    key = data["latest"]["key"]
    if "cap" not in iss:
        return ""
    capu, ldau = occto_urls(latest_doc, lang)
    sec14 = sec_by(latest_doc, r"^③")
    intro = sentences(first_p(sec14), 1, lang)
    m = re.search(r"(長期脱炭素電源オークション)（([^）]+)）", first_p(sec14)) if lang == "ja" else \
        re.search(r"(Long-Term Decarbonization Power Source Auction) \(([^)]+)\)", first_p(sec14))
    lda_def = f"<p><b>{esc(m.group(1))}</b>　{esc(m.group(2))}</p>" if m else ""
    t_pub = find_term(latest_doc, "容量市場の約定結果は", "Capacity market clearing results")
    head, rows = iss["cap"]["head"], iss["cap"]["rows"]
    src_t = iss["src"].get("occto", "")
    src_clean = re.sub(r"^(出典:|Source:)\s*", "", src_t)
    # 号の中の「出所は末尾の前提と用語」を指す括弧は、この頁では下の年度のリンクに当たるので外す
    src_clean = re.sub(r"（出所は[^）]*）|\s*\(sources? (?:are )?listed in the last section[^)]*\)\)?", "", src_clean)
    occ = "OCCTO"
    issue_link = f'<a href="{base}/{key}#s{data.get("secmap", {}).get(key) or "17"}">{esc(issue_label(key, lang))}</a>'
    year_links = "".join(f'　<a href="{esc(u)}" rel="noopener" target="_blank">{esc(y + ("年度" if lang == "ja" else ""))}</a>' for y, u in sorted(capu.items()))
    lda_links = "".join(f'　<a href="{esc(u)}" rel="noopener" target="_blank">{esc(y + ("年度応札" if lang == "ja" else ""))}</a>' for y, u in sorted(ldau.items()))
    pre = "出典: " if lang == "ja" else "Source: "
    unit = "円/kW・年" if lang == "ja" else "yen/kW per year"
    if area_only:
        j = head.index(area_only)
        yrs = [r[0] for r in rows]
        ser = [(area_names.get(area_only, area_only), C_PURPLE, [num(r[j]) for r in rows], False)]
        xl = [re.sub(r"年度$", "", y) for y in yrs]
        chart = svg_line(xl, ser, w=420, h=250, aria=f"{area_only}の容量市場メインオークションのエリアプライス（{unit}）",
                         unit_fmt="{:,.0f}", fs=14)
        tbl = table([head[0], f"{area_only}（{unit}）"], [[esc(r[0]), esc(r[j])] for r in rows],
                    [["", f"cap|{r[0]}|{area_only}"] for r in rows], caption=f"{area_only}の容量市場メインオークションのエリアプライス（{unit}）・実需給年度ごと")
        cap_latest = latest_cap_sentence("ja", rows[-1][0], area_only, rows[-1][j], area_only, rows[-1][j], unit, "OCCTO", area_only=area_only)
        note = "（このエリアの列を抜き出して表と図にしました）"
        return f"""<section class="md" id="capacity"><div class="container rp-body">
  <h2 class="md-h">③容量市場（OCCTO）｜{esc(area_only)}のエリアプライス</h2>
  {cap_latest}
  <p>{esc(intro)}</p>
  <div class="rd-two"><div class="rd-card"><h3>実需給年度ごとの約定価格（{esc(unit)}）</h3>{chart}</div><div>{tbl}</div></div>
  <p class="rd-src">{pre}{esc(src_clean)}{esc(note)}{year_links}</p>
  <div class="rd-def"><p>{esc(t_pub)}</p></div>
  <p class="rd-src">載った号: {issue_link}</p>
</div></section>"""
    # 全エリア
    last = rows[-1]
    a_names = head[1:]
    _pairs = [(a, num(val)) for a, val in zip(a_names, last[1:]) if num(val) is not None]
    _hi = max(_pairs, key=lambda x: x[1]) if _pairs else None
    _lo = min(_pairs, key=lambda x: x[1]) if _pairs else None
    cap_latest = (latest_cap_sentence(lang, last[0] + ("" if lang == "ja" else ""), _hi[0], dict(zip(a_names, last[1:]))[_hi[0]], _lo[0],
                                      dict(zip(a_names, last[1:]))[_lo[0]], unit, "OCCTO") if _hi and _lo else "")
    bars = svg_hbar([(a, num(val), val) for a, val in zip(a_names, last[1:])], w=420, color=C_PURPLE,
                    aria=(f"{last[0]}の容量市場メインオークションのエリアプライス（{unit}）" if lang == "ja" else f"Capacity market main auction area prices, {last[0]} ({unit})"),
                    label_w=70 if lang == "ja" else 92, fs=16)
    slug = dict(AREA_PAGES)
    h_cells = [esc(head[0])] + [esc(x) for x in a_names]
    t_rows = [[esc(c) for c in r] for r in rows]
    t_dk = [[""] + [f"cap|{r[0]}|{(a if lang == 'ja' else AREAS_JA[1 + a_names.index(a)])}" for a in a_names] for r in rows]
    cap_cap = (f"容量市場メインオークションのエリアプライス（{unit}）・実需給年度ごと" if lang == "ja"
               else f"Capacity market main auction area prices ({unit}) by delivery year")
    cap_tbl = ('<div class="rp-table rd-t"><table><caption>' + esc(cap_cap) + '</caption><thead><tr>' + "".join(f'<th scope="col">{c}</th>' for c in h_cells) + "</tr></thead><tbody>"
               + "".join("<tr>" + "".join((f'<th scope="row">{c}</th>' if j == 0 else f'<td class=rp-n{(" data-k=" + chr(34) + esc(dk) + chr(34)) if dk else ""}>{c}</td>')
                                          for j, (c, dk) in enumerate(zip(r, d))) + "</tr>" for r, d in zip(t_rows, t_dk))
               + "</tbody></table></div>")
    lh, lrows = iss["lda"]["head"], iss["lda"]["rows"]
    H_LDA = {"ja": "長期脱炭素電源オークションの蓄電池・揚水の約定容量（万kW）",
             "en": "Battery and pumped hydro capacity in the Long-Term Decarbonization Power Source Auction (10,000 kW)"}
    lda_tbl = table([esc(x) for x in lh], [[esc(c) for c in r] for r in lrows], [["", "", f"lda|{r[0]}|{r[1]}"] for r in lrows], caption=H_LDA[lang]) if lang == "ja" else \
        table([esc(x) for x in lh], [[esc(c) for c in r] for r in lrows], [["", "", f"lda|{i}"] for i, r in enumerate(lrows)], caption=H_LDA[lang])
    H = {"ja": ("③容量市場（OCCTO）｜メインオークションと長期脱炭素電源オークション", f"メインオークションのエリアプライス（{unit}）",
                f"{last[0]}のエリアプライス（{unit}）", "長期脱炭素電源オークションの蓄電池・揚水の約定容量（万kW）",
                "CSV をダウンロード（エリアプライス）", "CSV をダウンロード（約定容量）", "載った号"),
         "en": ("③ Capacity market (OCCTO): main auction and the Long-Term Decarbonization Power Source Auction",
                f"Main auction area prices ({unit})", f"Area prices for {last[0]} ({unit})",
                "Battery and pumped hydro capacity in the Long-Term Decarbonization Power Source Auction (10,000 kW)",
                "Download CSV (area prices)", "Download CSV (contracted capacity)", "Issue")}[lang]
    area_links = ""
    if lang == "ja":
        area_links = '<div class="rd-links">' + "".join(f'<a href="/report/area/{s}">{esc(a)}エリアの頁 →</a>' for a, s in AREA_PAGES) + "</div>"
    return f"""<section class="md" id="capacity"><div class="container rp-body">
  <h2 class="md-h">{esc(H[0])}</h2>
  {cap_latest}
  <p>{esc(intro)}</p>
  <div class="rd-card"><h3>{esc(H[2])}</h3>{bars}</div>
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(H[1])}</h3>
  {cap_tbl}
  <p class="rd-src">{pre}{esc(src_clean)}{year_links}</p>
  <div class="rd-def"><p>{esc(t_pub)}</p>{lda_def}</div>
  <a class="rd-dl" href="{csv_cap}" download>{esc(H[4])}</a>
  <h3 class="md-h" style="font-size:1.05rem;margin-top:26px">{esc(H[3])}</h3>
  {lda_tbl}
  <p class="rd-src">{pre}{esc(src_clean)}{lda_links}</p>
  <p class="rd-src">{esc(H[6])}: {issue_link}</p>
  <a class="rd-dl" href="{csv_lda}" download>{esc(H[5])}</a>
  {area_links}
</div></section>"""


def eprx_section(data, lang, base, latest_doc, csv_href, months):
    """①需給調整市場。SHOW_EPRX のときは推移の表と図、出さないときは号へのリンクだけ。"""
    sec3 = sec_by(latest_doc, r"^①")
    intro = sentences(first_p(sec3), 1, lang)
    head_t = "①需給調整市場（EPRX）" if lang == "ja" else "① Balancing market (EPRX)"
    if not SHOW_EPRX:
        links = "".join(f'<a href="{base}/{m["key"]}#s{data.get("secmap", {}).get(m["key"]) or "17"}">{esc(issue_label(m["key"], lang))}</a>'
                        for m in months)
        lead = ("商品ごとの応札倍率・約定率・平均落札価格は、各号の「市場の数字」の節に:" if lang == "ja"
                else "Bid ratios, award rates and average winning prices by product are in the \"Market numbers\" section of each issue:")
        return f"""<section class="md" id="eprx"><div class="container rp-body">
  <h2 class="md-h">{esc(head_t)}</h2>
  <p>{esc(intro)}</p>
  <p>{esc(lead)}</p>
  <div class="rd-links">{links}</div>
</div></section>"""
    E = data["eprx"]
    yms = month_range(E.keys())
    if not yms:
        return ""
    last, prev = yms[-1], (yms[-2] if len(yms) > 1 else None)
    LB = LBL[lang]
    prods = E[last]["order"]

    def v(ym, p, k):
        return ((E.get(ym) or {}).get("rows", {}).get(p) or {}).get(k)
    t_def = find_term(latest_doc, "需給調整市場: ", "Balancing market: ")
    p0 = prods[0]
    unit_p = "円/kW・30分" if lang == "ja" else "yen/kW per 30 min"
    ks = [(v(last, p0, "ratio"), "", f"{p0} {LB['ratio']}（{ym_label(last, lang)}）" if lang == "ja" else f"{p0}, {LB['ratio']} ({ym_label(last, lang)})", ""),
          (v(last, p0, "price"), unit_p, f"{p0} {LB['price'].split('（')[0]}" if lang == "ja" else f"{p0}, average winning price",
           delta(v(last, p0, "price"), v(prev, p0, "price") if prev else None, "円" if lang == "ja" else "yen", lang))]
    if len(prods) > 5:
        p5 = prods[5]
        ks.append((v(last, p5, "price"), unit_p, f"{p5} {LB['price'].split('（')[0]}" if lang == "ja" else f"{p5}, average winning price",
                   delta(v(last, p5, "price"), v(prev, p5, "price") if prev else None, "円" if lang == "ja" else "yen", lang)))
    xl = [ym_label(y, lang, True) for y in yms]
    pr_r = "".join(f"<figure><figcaption>{esc(p)}</figcaption>"
                   + svg_line(xl, [(LB["ratio"], C_PURPLE, [num(v(y, p, "ratio")) for y in yms], False)], w=330, h=210,
                              aria=f"{p} {LB['ratio']}", end_labels=False, ref=(100, "100%"), fs=14, tick_sfx="%") + "</figure>" for p in prods)
    pr_p = "".join(f"<figure><figcaption>{esc(p)}</figcaption>"
                   + svg_line(xl, [(LB["price"], C_ORANGE, [num(v(y, p, "price")) for y in yms], False)], w=330, h=210,
                              aria=f"{p} {LB['price']}", end_labels=False, fs=14) + "</figure>" for p in prods)

    def matrix(k):
        head = [("月" if lang == "ja" else "Month")] + prods
        rows = [[month_cell(y, E.get(y), base, "s17", lang)] + [esc(v(y, p, k) or "—") for p in prods] for y in yms]
        dks = [[""] + [f"eprx|{y}|{p}|{k}" if v(y, p, k) else "" for p in prods] for y in yms]
        return table(head, rows, dks, caption=(f"需給調整市場の商品別の{LB[k]}の月ごとの推移" if lang == "ja" else f"Balancing market {LB[k].lower()} by product, monthly"))
    src = src_line(data["latest"]["iss"]["src"].get("eprx", ""), [("EPRX 取引結果" if lang == "ja" else "EPRX trading results", EPRX_URL)], lang)
    return f"""<section class="md" id="eprx"><div class="container rp-body">
  <h2 class="md-h">{esc(head_t)}｜{"商品ごとの応札倍率と平均落札価格" if lang == "ja" else "bid ratio and average winning price by product"}</h2>
  <p>{esc(intro)}</p>
  {kpi(ks)}
  <div class="rd-def"><p>{esc(t_def)}</p></div>
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(LB['ratio'])}</h3>
  <div class="rd-sm">{pr_r}</div>
  {matrix("ratio")}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(LB['price'])}</h3>
  <div class="rd-sm">{pr_p}</div>
  {matrix("price")}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(LB['rate'])}</h3>
  {matrix("rate")}
  <h3 class="md-h" style="font-size:1.05rem;margin-top:22px">{esc(LB['won'])}</h3>
  {matrix("won")}
  {src}
  <a class="rd-dl" href="{csv_href}" download>{"CSV をダウンロード（月×商品・全指標）" if lang == "ja" else "Download CSV (month × product, all measures)"}</a>
</div></section>"""


# ---------------------------------------------------------------- CSV
def csv_text(rows):
    def q(c):
        c = str(c)
        return '"' + c.replace('"', '""') + '"' if any(x in c for x in ',"\n') else c
    return "﻿" + "".join(",".join(q(c) for c in r) + "\r\n" for r in rows)


def jepx_csv(data, lang, area_order, area_names, base):
    J = data["jepx"]
    ks = JEPX_KEYS + ["s2", "d10"]
    LB = LBL[lang]
    head = (["月", "エリア"] if lang == "ja" else ["month", "area"]) + [LB[k] for k in ks] + (["載った号", "出典"] if lang == "ja" else ["issue", "source"])
    src = re.sub(r"^(出典:|Source:)\s*", "", data["latest"]["iss"]["src"].get("jepx", ""))
    out = [head]
    for ym in sorted(J):
        rec = J[ym]
        for a in area_order:
            r = rec["rows"].get(a)
            if not r:
                continue
            out.append([ym, area_names[a]] + [csv_val(r.get(k, "")) for k in ks] + [f"https://www.scix.co.jp{base}/{rec['issue']}", src])
    return csv_text(out)


def cap_csv(data, lang, area_names):
    iss = data["latest"]["iss"]
    capu, _ = occto_urls(data["latest"]["doc"], lang)
    head = iss["cap"]["head"]
    out = [["実需給年度", "エリア", "エリアプライス（円/kW・年）", "出典"] if lang == "ja" else ["delivery_fiscal_year", "area", "area_price_yen_per_kw_year", "source"]]
    for r in iss["cap"]["rows"]:
        y = re.sub(r"\D", "", r[0])
        for a, val in zip(head[1:], r[1:]):
            out.append([r[0], a, csv_val(val), capu.get(y, "")])
    return csv_text(out)


def lda_csv(data, lang):
    iss = data["latest"]["iss"]
    _, ldau = occto_urls(data["latest"]["doc"], lang)
    out = [["応札年度", "区分", "約定容量（万kW）", "出典"] if lang == "ja" else ["auction_year", "category", "capacity_10000kw", "source"]]
    for r in iss["lda"]["rows"]:
        out.append([r[0], r[1], csv_val(r[2]), ldau.get(re.sub(r"\D", "", r[0]), "")])
    return csv_text(out)


def eprx_csv(data, lang, base):
    E = data["eprx"]
    LB = LBL[lang]
    out = [(["月", "商品"] if lang == "ja" else ["month", "product"]) + [LB[k] for k in EPRX_KEYS] + (["載った号"] if lang == "ja" else ["issue"])]
    for ym in sorted(E):
        rec = E[ym]
        for p in rec["order"]:
            r = rec["rows"][p]
            out.append([ym, p] + [csv_val(r.get(k, "")) for k in EPRX_KEYS] + [f"https://www.scix.co.jp{base}/{rec['issue']}"])
    return csv_text(out)


# ---------------------------------------------------------------- 頁の組み立て
def variables_measured(lang, cap=True, lda=True):
    """Dataset の variableMeasured。表の列と同じ名前と単位（数字は表と同じ公表資料のまま・新しい指標は足さない）。"""
    LB = LBL[lang]
    u = "円/kWh" if lang == "ja" else "yen/kWh"
    out = [{"@type": "PropertyValue", "name": LB[k], "unitText": u} for k in ("avg", "yoy", "day", "eve", "s4", "s2", "max")]
    out += [{"@type": "PropertyValue", "name": LB["n30"], "unitText": "コマ" if lang == "ja" else "slots"},
            {"@type": "PropertyValue", "name": LB["n001"], "unitText": "コマ" if lang == "ja" else "slots"},
            {"@type": "PropertyValue", "name": LB["d10"], "unitText": "日" if lang == "ja" else "days"}]
    if cap:
        out.append({"@type": "PropertyValue", "name": "容量市場メインオークションのエリアプライス" if lang == "ja" else "Capacity market main auction area price",
                    "unitText": "円/kW・年" if lang == "ja" else "yen/kW per year"})
    if lda:
        out.append({"@type": "PropertyValue", "name": "長期脱炭素電源オークションの蓄電池・揚水の約定容量" if lang == "ja"
                    else "Battery and pumped hydro capacity in the Long-Term Decarbonization Power Source Auction",
                    "unitText": "万kW" if lang == "ja" else "10,000 kW"})
    return out


def dataset_ld(br, name, desc, path, csvs, temporal, lang, based_on, spatial, variables=None):
    org = br.bmd.ORG if lang == "ja" else br.EN_ORG
    pub = br.PUBLISHER if lang == "ja" else br.EN_PUBLISHER
    return br.bmd.ld({"@context": "https://schema.org", "@type": "Dataset", "@id": br.BASE + path + "#dataset", "url": br.BASE + path,
                      "name": name, "description": desc, "inLanguage": lang, "creator": org, "publisher": pub, "isAccessibleForFree": True,
                      "temporalCoverage": temporal, "spatialCoverage": {"@type": "Place", "name": spatial},
                      **({"variableMeasured": variables} if variables else {}),
                      "isBasedOn": based_on, "dateModified": temporal_end_date(csvs),
                      "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": br.BASE + u, "name": n} for n, u in csvs]})


_MOD = {}


def temporal_end_date(_):
    return _MOD.get("date", "")


def render_data(br, data, months, lang, has_en):
    latest_doc = data["latest"]["doc"]
    path = "/report/data" if lang == "ja" else "/en/report/data"
    base = "/report" if lang == "ja" else "/en/report"
    J = data["jepx"]
    yms = month_range(J.keys())
    first, last = yms[0], yms[-1]
    order_ja = J[last]["order"]
    if lang == "ja":
        area_order, area_names = order_ja, {a: a for a in order_ja}
    else:
        area_order = J[last]["order"]
        area_names = {a: a for a in area_order}
    sysn = area_order[0]
    rows_last = J[last]["rows"]
    csv_j, csv_c, csv_l, csv_e = (f"{path}/jepx-spot-monthly.csv", f"{path}/capacity-main-auction.csv",
                                  f"{path}/long-term-decarbonization-auction.csv", f"{path}/eprx-monthly.csv")
    sec1 = sec_by(latest_doc, r"^(蓄電所の3つの稼ぎ口|Three income streams)")
    lead = sentences(first_p(sec1), 1, lang)
    if lang == "ja":
        h1 = "蓄電所の市場データ"
        mk = "需給調整市場・卸電気・容量市場" if SHOW_EPRX else "卸電気・容量市場"
        title = f"蓄電所の市場データ｜{mk}の月ごとの推移（エリア別・前月差・CSV）｜サイエンスエックス"
        desc = (f"卸電気（JEPX）のエリア別の月平均・日中・夕方・4時間と2時間の値差を{ym_label(first)}〜{ym_label(last)}の月ごとに表と図で。"
                f"{ym_label(last)}の{sysn}の月平均は{rows_last[sysn]['avg']}円/kWh、4時間の値差は{rows_last[sysn]['s4']}円/kWh。"
                "容量市場のエリアプライスと長期脱炭素電源オークションの約定容量も。出典つき・CSV あり。")
        if SHOW_EPRX:
            desc = "需給調整市場（EPRX）の商品ごとの応札倍率・平均落札価格、" + desc
        label = "毎月更新・出典つき・CSV あり"
        toc = [("#jepx", "②卸電気"), ("#capacity", "③容量市場")] + ([("#eprx", "①需給調整市場")])
        crumbs = [("ホーム", "/"), ("市場ノート", "/report"), ("市場データ", path)]
        cite = br.bmd.cite_html("ja", h1, br.BASE + path, _MOD["date"],
                                '<p>数字は公表データと当社の記録の集計です。値差は1kWh あたりの価格の差で、実際の収益を示すものではありません。'
                                'CSV は各節の下から取れます。転載の決まりは <a href="/press">引用・転載ガイド</a> に。</p>')
        meta = f"{ym_label(first)}〜{ym_label(last)}・{len(months)}号から・最新は{issue_label(data['latest']['key'])}（発行 {br.jp_date(data['latest']['doc']['issued'])}）"
    else:
        h1 = "Battery Storage Market Data"
        mk = "balancing, wholesale and capacity markets" if SHOW_EPRX else "wholesale power and capacity markets"
        title = ("Battery Storage Market Data: EPRX, JEPX and capacity | ScienceX" if SHOW_EPRX
                 else "Battery Storage Market Data: JEPX spot and capacity prices | ScienceX")
        desc = (f"JEPX spot prices by area, monthly from {ym_label(first, 'en')} to {ym_label(last, 'en')}: averages, daytime, evening, "
                f"4-hour and 2-hour spreads. Capacity market prices. Sources cited, CSV.")
        if len(desc) > 155:
            desc = desc[:154].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
        label = "Updated monthly · Sources cited · CSV"
        toc = [("#jepx", "② Wholesale (JEPX)"), ("#capacity", "③ Capacity (OCCTO)"), ("#eprx", "① Balancing (EPRX)")]
        crumbs = [("Home", "/en"), ("Market Notes", "/en/report"), ("Market data", path)]
        cite = br.bmd.cite_html("en", h1, br.BASE + path, _MOD["date"],
                                '<p>The figures are tallies of published data and our own records. The price spread is a difference in price per kWh and does not show actual revenue. '
                                'CSV downloads are below each section; the reuse terms are in the <a href="/en/press">citation guide</a>.</p>')
        meta = f"{ym_label(first, 'en')}–{ym_label(last, 'en')} · from {len(months)} issues · latest: {issue_label(data['latest']['key'], 'en')}"
    jsec = jepx_section(data, lang, base, latest_doc, csv_j, area_order, area_names)
    csec = cap_lda_section(data, lang, base, latest_doc, csv_c, csv_l)
    esec = eprx_section(data, lang, base, latest_doc, csv_e, months)
    secs = [esec, jsec, csec] if SHOW_EPRX else [jsec, csec, esec]
    if SHOW_EPRX:
        toc = [toc[2], toc[0], toc[1]]
    csvs = [("JEPX", csv_j), ("OCCTO capacity", csv_c), ("OCCTO long-term", csv_l)] + ([("EPRX", csv_e)] if SHOW_EPRX else [])
    capu, ldau = occto_urls(latest_doc, lang)
    based = [JEPX_URL] + sorted(capu.values()) + sorted(ldau.values()) + ([EPRX_URL] if SHOW_EPRX else [])
    ds_desc = desc if len(desc) >= 50 else desc + " " + lead
    jsonld = "\n".join([
        dataset_ld(br, title.split("｜")[0].split(" | ")[0] + (f"（{mk}）" if lang == "ja" else f" ({mk})"), ds_desc, path, csvs,
                   f"{first}/{last}", lang, based, "日本" if lang == "ja" else "Japan", variables_measured(lang)),
        br.bmd.ld(br.bmd.crumbs([(n, br.BASE + u) for n, u in crumbs])),
    ])
    toc_html = '<div class="rd-toc">' + "".join(f'<a href="{h}">{esc(n)}</a>' for h, n in toc) + "</div>"
    main = f"""{br.bmd.nav_crumbs(crumbs)}
<section class="hero"><div class="container">
  <div class="section-label">{esc(label)}</div>
  <h1>{esc(h1)}</h1>
  <p>{esc(lead)}</p>
  <p class="md-note">{esc(meta)}</p>
  {toc_html}
</div></section>
{chr(10).join(s for s in secs if s)}
<section class="md"><div class="container rp-body">
  {cite}
</div></section>
"""
    if lang == "ja":
        head = br.page_head(title, desc, path, jsonld, "/en/report/data" if has_en else None)
        foot = br.bmd.CTA + br.bmd.FOOTER
    else:
        head = br.page_head_en(title, desc, path, jsonld, "/report/data")
        foot = EN_CTA + br.bmd.EN_FOOTER
    return head.replace("</style>", CSS + "</style>", 1) + main + foot + "\n</body>\n</html>\n", main


EN_CTA = """<section class="cta"><div class="container">
  <h2>Want to see the projects behind these numbers? Visit Chikudensho Market</h2>
  <p>On Chikudensho Market, our marketplace for battery storage sites, you can browse current listings without registering. Prices and documents are available after free registration, where you agree to a confidentiality undertaking on the registration screen (no signed paper is needed).</p>
  <a class="btn-primary" href="https://dealroom.scix.co.jp/en" target="_top">Browse projects on Chikudensho Market &rarr;</a>
</div></section>
"""


def area_quotes(months, docs, area):
    """号の②③の節の文のうち、そのエリアに触れた文（言い換えない）と、その節へのリンク。①は SHOW_EPRX のときだけ。"""
    out = []
    pat = r"^[②③]" + ("|^①" if SHOW_EPRX else "")
    for i, m in enumerate(months):
        doc = docs.get(m["key"])
        if not doc:
            continue
        for s in doc["sections"]:
            if not re.search(pat, s["title"]):
                continue
            if i and s["title"].startswith("③"):      # 容量市場は年1回の公表で毎号同じ数字＝いちばん新しい号の文だけ
                continue
            for k, t in s["items"]:
                if k != "p":
                    continue
                for sent in re.findall(r"[^。]+。", t):
                    if area in sent and re.search(r"\d", sent):
                        out.append((m["key"], s["num"], s["title"], sent.strip()))
    return out


def market_area_href(area, slug, n):
    """蓄電所マーケットの、そのエリアの静的な入口 /catalog/area/<slug>（絞り込みの検索 ?area= でなく。件数0なら入口は404なのでトップ /）。"""
    return "https://dealroom.scix.co.jp/" + (f"catalog/area/{slug}" if n else "")


def projects_block(br, area, slug):
    """projects.json（公開セーフ項目だけ）からこのエリアの件数。価格・住所・売主は持っていない。"""
    p = os.path.join(br.ROOT, "projects.json")
    try:
        ps_all = json.load(open(p, encoding="utf-8")).get("projects", [])
    except (OSError, ValueError):
        return ""
    ps = [x for x in ps_all if x.get("area") == area]
    n = len(ps)
    s = br.bmd.stats(ps, datetime.date.today()) if ps else None
    if not s:
        return ""
    n_mw = sum(1 for x in ps if isinstance(x.get("mw"), (int, float)))      # 出力・容量が未登録の案件は合計に入らない＝何件分かを添える
    n_mwh = sum(1 for x in ps if isinstance(x.get("mwh"), (int, float)))
    pref = s["pref"].most_common()
    sch = s["scheme"].most_common()
    volt = s["volt"].most_common()
    return f"""<section class="md" id="projects"><div class="container rp-body">
  <h2 class="md-h">このエリアでいま公開している案件 {n}件</h2>
  <p>{esc(area)}エリア（{esc(dict((a, o) for a, _, o in br.bmd.AREAS).get(area, ""))}管内）で当社が扱う、接続検討の回答が出た系統用蓄電池（蓄電所）の案件です。所在県・電圧・規模・連系の見込み・進み具合・取得の形までは登録なしでご覧いただけます。価格と資料は蓄電所マーケットで、無料登録のあとに見られます。</p>
  <div class="rd-kpi">
    <div><b>{n}<small>件</small></b><span>販売中の案件</span></div>
    <div><b>{s['mw']:,}<small>MW</small></b><span>出力が分かる{n_mw}件の合計（容量が分かる{n_mwh}件で{s['mwh']:,}MWh）</span></div>
    <div><b>{s['volt'].get('高圧', 0)}<small>件</small></b><span>高圧</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}<small>件</small></b><span>特別高圧</span></div>
  </div>
  <div class="rd-two"><div class="rd-card"><h3>都道府県</h3>{svg_hbar([(a, c, f"{c}件") for a, c in pref], w=420, label_w=90, fs=17, color=C_GREEN, aria=f"{area}エリアの案件の都道府県別の件数")}</div>
  <div class="rd-card"><h3>取得の形</h3>{svg_hbar([(a or "確認中", c, f"{c}件") for a, c in sch], w=420, label_w=90, fs=17, color=C_GREEN, aria=f"{area}エリアの案件の取得の形別の件数")}</div>
  <div class="rd-card"><h3>電圧</h3>{svg_hbar([(a or "確認中", c, f"{c}件") for a, c in volt], w=420, label_w=90, fs=17, color=C_GREEN, aria=f"{area}エリアの案件の電圧別の件数")}</div></div>
  <div class="rd-links"><a href="{market_area_href(area, slug, n)}" target="_top">蓄電所マーケットで{esc(area)}エリアの案件を見る →</a><a href="/projects-{slug}">{esc(area)}電力管内の案件一覧（{n}件）</a></div>
</div></section>"""


def render_area(br, data, months, docs, area, slug):
    latest_doc = data["latest"]["doc"]
    path = f"/report/area/{slug}"
    base = "/report"
    J = data["jepx"]
    yms = month_range(J.keys())
    first, last = yms[0], yms[-1]
    prev = yms[-2] if len(yms) > 1 else None
    LB = LBL["ja"]

    def v(ym, k):
        return ((J.get(ym) or {}).get("rows", {}).get(area) or {}).get(k)
    ks = JEPX_KEYS + ["s2", "d10"]
    xl = [ym_label(y, "ja", True) for y in yms]
    ch1 = svg_line(xl, [(LB["avg"], C_PURPLE, [num(v(y, "avg")) for y in yms], False),
                        (LB["yoy"], C_GRAY, [num(v(y, "yoy")) for y in yms], True),
                        (LB["day"], C_BLUE, [num(v(y, "day")) for y in yms], False),
                        (LB["eve"], C_PINK, [num(v(y, "eve")) for y in yms], False)],
                   w=420, h=270, fs=14, aria=f"{area}の卸電気の月平均・前年同月・日中・夕方（円/kWh）")
    ch2 = svg_line(xl, [(LB["s4"], C_ORANGE, [num(v(y, "s4")) for y in yms], False),
                        (LB["s2"], C_GREEN, [num(v(y, "s2")) for y in yms], False)],
                   w=420, h=270, fs=14, aria=f"{area}の卸電気の4時間と2時間の値差（円/kWh）")
    head = ["月"] + [LB[k] for k in ks]
    rows = [[month_cell(y, J.get(y), base)] + [esc(v(y, k) or "—") for k in ks] for y in yms]
    dks = [[""] + [f"jepx|{y}|{area}|{k}" if v(y, k) else "" for k in ks] for y in yms]
    dr = None
    if prev:
        dr = ["前月差"] + [(f"{num(v(last, k)) - num(v(prev, k)):+.2f}" if k in ("avg", "yoy", "day", "eve", "s4", "s2", "max")
                           and num(v(last, k)) is not None and num(v(prev, k)) is not None else "—") for k in ks]
    sec10 = sec_by(latest_doc, r"^②.*平均の値段")
    intro = first_p(sec10)
    area_lead = next((x for x in re.findall(r"[^。]+。", intro) if "エリアプライス" in x), intro)
    t_avg = find_term(latest_doc, "平均価格は")
    t_spr = find_term(latest_doc, "値差:")
    src = src_line(data["latest"]["iss"]["src"].get("jepx", ""), [("JEPX スポット市場", JEPX_URL)])
    unit = "円/kWh"
    cap_iss = data["latest"]["iss"].get("cap")
    cap_last = None
    if cap_iss and area in cap_iss["head"]:
        j = cap_iss["head"].index(area)
        cap_last = (cap_iss["rows"][-1][0], cap_iss["rows"][-1][j])
    kp = [(v(last, "avg"), unit, f"{LB['avg']}（{ym_label(last)}）", delta(v(last, "avg"), v(prev, "avg") if prev else None, "円")),
          (v(last, "s4"), unit, LB["s4"], delta(v(last, "s4"), v(prev, "s4") if prev else None, "円")),
          (v(last, "s2"), unit, LB["s2"], delta(v(last, "s2"), v(prev, "s2") if prev else None, "円"))]
    if cap_last:
        kp.append((cap_last[1], "円/kW・年", f"容量市場 {cap_last[0]}", ""))
    quotes = area_quotes(months, docs, area)
    qhtml = ""
    if quotes:
        qhtml = ('<section class="md" id="notes"><div class="container rp-body"><h2 class="md-h">号の中の、' + esc(area) + 'に触れた記述</h2><ul class="rd-quote">'
                 + "".join(f'<li>{esc(t)}<a href="{base}/{k}#s{n}">{esc(issue_label(k))}・{esc(re.sub(r"^[①②③]", "", tt))} →</a></li>'
                           for k, n, tt, t in quotes) + "</ul></div></section>")
    title = f"{area}エリアの市場データ｜卸電気の月平均・値差と容量市場の約定価格（月ごと）｜サイエンスエックス"
    desc = (f"{area}エリアの卸電気（JEPX）の月平均・日中・夕方・4時間と2時間の値差を{ym_label(first)}〜{ym_label(last)}の月ごとに表と図で。"
            f"{ym_label(last)}の月平均は{v(last, 'avg')}円/kWh、4時間の値差は{v(last, 's4')}円/kWh。容量市場のエリアプライスと、このエリアの公開案件の件数も。")
    jsonld = "\n".join([
        dataset_ld(br, f"{area}エリアの卸電気の月ごとの数字", desc, path, [("JEPX", "/report/data/jepx-spot-monthly.csv")],
                   f"{first}/{last}", "ja", [JEPX_URL], f"{area}エリア", variables_measured("ja", lda=False)),
        br.bmd.ld(br.bmd.crumbs([("ホーム", br.BASE + "/"), ("市場ノート", br.BASE + "/report"), ("市場データ", br.BASE + "/report/data"),
                                 (f"{area}エリア", br.BASE + path)])),
    ])
    others = "".join(f'<a href="/report/area/{s}">{esc(a)}エリア →</a>' for a, s in AREA_PAGES if a != area)
    main = f"""{br.bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", "/report"), ("市場データ", "/report/data"), (f"{area}エリア", path)])}
<section class="hero"><div class="container">
  <div class="section-label">毎月更新・出典つき</div>
  <h1>{esc(area)}エリアの市場データ</h1>
  <p>{esc(area_lead)}</p>
  <p class="md-note">{esc(ym_label(first))}〜{esc(ym_label(last))}・最新は{esc(issue_label(data['latest']['key']))}（発行 {esc(br.jp_date(latest_doc['issued']))}）</p>
  <div class="rd-toc"><a href="#jepx">②卸電気</a><a href="#capacity">③容量市場</a>{'<a href="#notes">号の中の記述</a>' if quotes else ''}<a href="#projects">このエリアの案件</a></div>
</div></section>
<section class="md" id="jepx"><div class="container rp-body">
  <h2 class="md-h">②卸電気（JEPX）｜{esc(area)}のエリアプライスと値差</h2>
  {latest_jepx_sentence("ja", last, area, v(last, "avg"), v(last, "s4"), unit, "JEPX スポット市場")}
  <p>{esc(intro)}</p>
  {kpi(kp)}
  <div class="rd-def"><p><b>定義</b></p><p>{esc(t_avg)}</p><p>{esc(t_spr)}</p></div>
  <div class="rd-two"><div class="rd-card"><h3>月平均・前年同月・日中・夕方（{unit}）</h3>{legend([(LB["avg"], C_PURPLE, False), (LB["yoy"], C_GRAY, True), (LB["day"], C_BLUE, False), (LB["eve"], C_PINK, False)])}{ch1}</div>
  <div class="rd-card"><h3>値差（{unit}）</h3>{legend([(LB["s4"], C_ORANGE, False), (LB["s2"], C_GREEN, False)])}{ch2}</div></div>
  {table(head, rows, dks, dr, caption=f"{area}の卸電気の月ごとの数字（{unit}）・月平均・前年同月・日中・夕方・値差")}
  {src}
  <a class="rd-dl" href="/report/data/jepx-spot-monthly.csv" download>CSV をダウンロード（全エリア）</a>
</div></section>
{cap_lda_section(data, "ja", base, latest_doc, "", "", area_only=area, area_names={area: area})}
{qhtml}
{projects_block(br, area, slug)}
<section class="md"><div class="container rp-body">
  <div class="rd-links"><a href="/report/data">全エリアの市場データ →</a>{others}<a href="/report">市場ノートの号の一覧 →</a></div>
  {br.bmd.cite_html("ja", f"{area}エリアの市場データ", br.BASE + path, _MOD["date"],
                    '<p>数字は公表データと当社の記録の集計です。値差は1kWh あたりの価格の差で、実際の収益を示すものではありません。'
                    '転載の決まりは <a href="/press">引用・転載ガイド</a> に。</p>')}
</div></section>
"""
    h = br.page_head(title, desc, path, jsonld, None)
    return h.replace("</style>", CSS + "</style>", 1) + main + br.bmd.CTA + br.bmd.FOOTER + "\n</body>\n</html>\n", main


# ---------------------------------------------------------------- 入口
def en_matches(ja, en):
    """英語の号の表の数字が日本語の号と同じか（行の並びで比べる）。食い違いの一覧を返す。"""
    bad = []
    for ym, rec in ja["jepx"].items():
        e = en["jepx"].get(ym)
        if not e:
            bad.append(f"{ym}: 英語の号に卸電気の表が無い")
            continue
        for (a, ea) in zip(rec["order"], e["order"]):
            for k in JEPX_KEYS + ["s2", "d10"]:
                if rec["rows"][a].get(k) != e["rows"][ea].get(k):
                    bad.append(f"{ym} {a}/{ea} {k}: {rec['rows'][a].get(k)} != {e['rows'][ea].get(k)}")
    li, le = ja["latest"]["iss"], en["latest"]["iss"]
    if li.get("cap", {}).get("rows") and [r[1:] for r in li["cap"]["rows"]] != [r[1:] for r in le.get("cap", {}).get("rows", [])]:
        bad.append("容量市場の表")
    if li.get("lda", {}).get("rows") and [r[2] for r in li["lda"]["rows"]] != [r[2] for r in le.get("lda", {}).get("rows", [])]:
        bad.append("長期脱炭素の表")
    return bad


def build(br, months, docs):
    """{相対パス: bytes}・sitemap に足す行 [(path, lastmod, priority, alt_path, lang)]・知らせ を返す。"""
    files, sm, notes = {}, [], []
    ja = collect(months, docs, "ja")
    notes += ja["warn"]
    if not ja["jepx"] or not ja["latest"] or "cap" not in ja["latest"]["iss"]:
        notes.append("市場データ: 号の表が読めない（卸電気か容量市場の表が無い）。市場データの頁は焼かない")
        return files, sm, notes
    # 頁の dateModified＝sitemap の lastmod＝最新の号の発行日と、今の sitemap の値（頁を変えた日に stamp_sitemap.py が進める）の新しいほう
    _MOD["date"] = br.modified_of("/report/data", ja["latest"]["doc"]["issued"])
    en_months = [m for m in months if m.get("en_md")]
    en = collect(en_months, docs, "en") if en_months else None
    has_en = False
    if en and en["jepx"] and en["latest"] and en["latest"]["key"] == ja["latest"]["key"]:
        bad = en_matches(ja, en)
        if bad:
            notes.append("市場データ（英語）: 英語の号の表の数字が日本語の号と食い違う。英語の頁は焼かない: " + "; ".join(bad[:5]))
        else:
            has_en = True
    elif en_months:
        notes.append("市場データ（英語）: 英語の号がいちばん新しい月にそろっていない。英語の頁は焼かない")
    order = ja["jepx"][max(ja["jepx"])]["order"]
    names = {a: a for a in order}
    page, main = render_data(br, ja, months, "ja", has_en)
    pages = [("report/data/index.html", page, main, "ja")]
    files["report/data/jepx-spot-monthly.csv"] = jepx_csv(ja, "ja", order, names, "/report").encode("utf-8")
    files["report/data/capacity-main-auction.csv"] = cap_csv(ja, "ja", names).encode("utf-8")
    files["report/data/long-term-decarbonization-auction.csv"] = lda_csv(ja, "ja").encode("utf-8")
    if SHOW_EPRX and ja["eprx"]:
        files["report/data/eprx-monthly.csv"] = eprx_csv(ja, "ja", "/report").encode("utf-8")
    d = _MOD["date"]
    sm.append(("/report/data", d, "0.7", "/en/report/data" if has_en else None, "ja"))
    if has_en:
        en_order = en["jepx"][max(en["jepx"])]["order"]
        page_en, main_en = render_data(br, en, en_months, "en", True)
        pages.append(("en/report/data/index.html", page_en, main_en, "en"))
        files["en/report/data/jepx-spot-monthly.csv"] = jepx_csv(en, "en", en_order, {a: a for a in en_order}, "/en/report").encode("utf-8")
        files["en/report/data/capacity-main-auction.csv"] = cap_csv(en, "en", {}).encode("utf-8")
        files["en/report/data/long-term-decarbonization-auction.csv"] = lda_csv(en, "en").encode("utf-8")
        if SHOW_EPRX and en["eprx"]:
            files["en/report/data/eprx-monthly.csv"] = eprx_csv(en, "en", "/en/report").encode("utf-8")
        sm.append(("/en/report/data", d, "0.6", "/report/data", "en"))
    for area, slug in AREA_PAGES:
        if not any(area in rec["rows"] for rec in ja["jepx"].values()):
            notes.append(f"市場データ: {area} の卸電気の数字が号に無い。エリアの頁は焼かない")
            continue
        page, main = render_area(br, ja, months, docs, area, slug)
        pages.append((f"report/area/{slug}/index.html", page, main, "ja"))
        sm.append((f"/report/area/{slug}", d, "0.6", None, "ja"))
    # 公開してはいけない語を、焼いた頁の本文にも掛ける（フッターの住所は除く）
    hits = []
    for rel, page, main, lang in pages:
        for pat, why in (br.FORBIDDEN if lang == "ja" else br.FORBIDDEN_EN):
            for mt in re.finditer(pat, main):
                hits.append(f"{rel}: {why}: 「{mt.group(0)[:40]}」")
        files[rel] = page.encode("utf-8")
    if hits:
        return {}, [], notes + ["NG 市場データの頁に公開してはいけない語がある。市場データの頁は焼かない: " + "; ".join(hits[:5])]
    return files, sm, notes


def sitemap_add(text, entries, base):
    """市場データ・エリアの頁の行を足す（あれば同じ形に書き直す）。"""
    add = ""
    for p, lastmod, pr, alt, lang in entries:
        if alt:
            ja_p, en_p = (p, alt) if lang == "ja" else (alt, p)
            a_ja = f'<xhtml:link rel="alternate" hreflang="ja" href="{base}{ja_p}"/>'
            a_en = f'<xhtml:link rel="alternate" hreflang="en" href="{base}{en_p}"/>'
            links = (a_ja + a_en) if lang == "ja" else (a_en + a_ja)
        else:
            links = f'<xhtml:link rel="alternate" hreflang="ja" href="{base}{p}"/>'
        new = f"  <url><loc>{base}{p}</loc>{links}<priority>{pr}</priority><lastmod>{lastmod}</lastmod></url>\n"
        pat = re.compile(r"  <url><loc>" + re.escape(base + p) + r"</loc>.*?</url>\n")
        if pat.search(text):
            text = pat.sub(lambda _m: new, text, count=1)
        else:
            add += new
    return text.replace("</urlset>", add + "</urlset>", 1) if add else text
