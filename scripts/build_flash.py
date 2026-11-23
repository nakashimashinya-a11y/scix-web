#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「蓄電所の市場ノート 速報」（/report/flash・/en/report/flash・毎日更新）を焼く。

2026-11-23 中島（対話画面）「市場レポートの考え方整理。毎日最新データを落として速報。毎月１日に先月のデータを落として月報。
今色々あってわかりにくい。JEPXと需給調整のレポートを分ける必要ないよね。」「メニュー多いのは良くない。シンプルに。速報で毎日の最新データ。
毎月１日の前月最新データがいい。」＝市場の頁は2本だけ: 速報（この頁・毎日）と月の号（/report/<YYYY-MM>・毎月1日・build_reports.py）。

読むもの（リポジトリには置かない）: ~/.openclaw/workspace/state/market_flash/latest.json（bin/market_flash.py が毎朝、公表データを取り直して数える。
  数字と日付だけ。文はここで決まった型にはめる＝LLM を使わない）。SCIX_FLASH_JSON で替えられる。
生成するもの（全文を書き直す。手で直さない）:
  report/flash/index.html, en/report/flash/index.html   頁（頭に「何月何日のデータまで」・今月ここまで・最新の1日・前月〔全日〕との比べ・週ごと）
  report/flash/latest.json                              速報の要点（データの日付・先週の動きの文）。bin/press_release.py の速報の本が読む
  report/flash/jepx-daily.csv, en/report/flash/jepx-daily.csv   卸電気の日ごとの平均と4時間の値差（今月と前月・10エリア）
  sitemap.xml                                           /report/flash と /en/report/flash の行（hreflang・lastmod＝データを取り直した日）
古いデータを新しく見せない: 入力の最新の受渡日が、いま焼いてある頁（report/flash/latest.json）より古ければ何も書かない（前の版のまま＝日付も前のまま）。
需給調整市場の数字は頁の表の集計だけ（日ごとの CSV は出さない＝build_report_data.py と同じ扱い）。

使い方:
    python3 scripts/build_flash.py            # 書き換えて差分を報告（入力が無い・読めない＝rc 2・何も書かない）
    python3 scripts/build_flash.py --check    # 書き換えずに、ずれているかだけ（ずれていれば 1）
毎朝の同期（scripts/sync_projects_json.sh）が月の号の後に呼ぶ。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_reports as brp  # noqa: E402  head・CSS・禁止の語・発行者を共用する
import build_market_data as bmd  # noqa: E402

BASE = bmd.BASE
SRC = os.environ.get("SCIX_FLASH_JSON", os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "state", "market_flash", "latest.json"))
PATH, PATH_EN = "/report/flash", "/en/report/flash"
FIRST = "2026-11-23"      # 頁を作った日（JSON-LD の datePublished。dateModified はデータを取り直した日）
NAME, NAME_EN = "蓄電所の市場ノート 速報", "Battery Storage Market Notes: Daily Flash"
AREAS = ["システム", "北海道", "東北", "東京", "中部", "北陸", "関西", "中国", "四国", "九州"]
AREA_JA = {"システム": "システム（全国）"}
AREA_EN = {"システム": "System (Japan)", "北海道": "Hokkaido", "東北": "Tohoku", "東京": "Tokyo", "中部": "Chubu", "北陸": "Hokuriku", "関西": "Kansai",
           "中国": "Chugoku", "四国": "Shikoku", "九州": "Kyushu"}
PROD_EN = {"1-0": "Primary reserve (online)", "1-1": "Primary reserve (offline)", "2-1": "Secondary reserve 1", "2-2": "Secondary reserve 2",
           "3-1": "Tertiary reserve 1", "3-2": "Tertiary reserve 2", "4-0": "Combined products"}
WD_JA = "月火水木金土日"
MONTHS_EN = brp.MONTHS_EN
JEPX_URL = "https://www.jepx.jp/electricpower/market-data/spot/"
EPRX_URL = "https://www.eprx.or.jp/information/results.php"

CSS = """
.fl-asof{display:inline-flex;flex-direction:column;gap:4px;margin:14px 0 6px;padding:14px 18px;border:2px solid #138A62;border-radius:14px;background:#fff;max-width:860px}
.fl-asof .h{font-size:.8rem;font-weight:800;color:#0F7A52;letter-spacing:.04em}
.fl-asof b{font-size:clamp(1.05rem,2.6vw,1.35rem);color:var(--navy);line-height:1.5}
.fl-asof span{font-size:.84rem;color:var(--text-2)}
.fl-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0 6px;max-width:960px}
.fl-kpi div{background:#fff;border:1px solid var(--border);border-top:5px solid #138A62;border-radius:14px;padding:12px 14px}
.fl-kpi b{display:block;font-size:clamp(1.4rem,3vw,1.9rem);font-weight:900;color:var(--navy);line-height:1.2;font-variant-numeric:tabular-nums}
.fl-kpi b small{font-size:.78rem;font-weight:700;color:var(--text-2);margin-left:3px}
.fl-kpi span{display:block;font-size:.8rem;font-weight:700;color:var(--text-2);margin-top:6px;line-height:1.5}
.fl-kpi i{display:block;font-style:normal;font-size:.78rem;color:var(--text-3);margin-top:2px}
.fl-chart{max-width:720px;margin:14px 0 4px;background:#fff;border:1px solid var(--border);border-radius:12px;padding:10px 12px 6px}
.fl-chart svg{display:block;width:100%;height:auto}
.fl-two{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 0}
.fl-two a{display:inline-block}
.rp-body p,.rp-body li{overflow-wrap:anywhere}
.fl-pair{font-size:1.02rem;line-height:1.8;color:var(--navy);margin:6px 0 4px}.fl-pair b{color:#0F7A52}
#week .rp-body,#eprx .rp-body,#jepx .rp-body,#asof .rp-body{max-width:1120px}#week .rp-table,#eprx .rp-table,#jepx .rp-table,#asof .rp-table{max-width:1120px}
.fl-scroll{display:none;font-size:.8rem;color:var(--text-3);margin:6px 0 -6px}
@media(max-width:900px){.fl-scroll{display:block}}
.fl-mk{max-width:1100px;margin:28px 0 0;padding:20px 24px;background:#F3F6FD;border:1.5px solid #D2DCF2;border-radius:18px;display:flex;flex-wrap:wrap;align-items:center;gap:12px 24px}
.fl-mk p{flex:1 1 320px;margin:0}
"""


# ------------------------------------------------------------------ 小道具
def esc(s):
    return brp.esc(str(s))


def f(x, nd=2, unit=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return "%.*f%s" % (nd, x, unit)


def d_ja(iso, wd=False):
    d = datetime.date.fromisoformat(iso)
    s = "%d年%d月%d日" % (d.year, d.month, d.day)
    return s + ("（%s）" % WD_JA[d.weekday()]) if wd else s


def md_ja(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d月%d日" % (d.month, d.day)


def d_en(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d, %d" % (MONTHS_EN[d.month - 1], d.day, d.year)


def md_en(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d" % (MONTHS_EN[d.month - 1][:3], d.day)


def mon_ja(ym):
    return "%d年%d月" % (int(ym[:4]), int(ym[5:]))


def mon_en(ym):
    return "%s %d" % (MONTHS_EN[int(ym[5:]) - 1], int(ym[:4]))


def issue_data_month(key):
    """月号の号の名前 → 中身の月（2026年11月号から、号の名前は発行する月・中身は前月＝bin/monthly_report.py の NAMING_FROM）。"""
    if key >= "2026-11":
        y, m = int(key[:4]), int(key[5:])
        return "%04d-%02d" % (y - (m == 1), 12 if m == 1 else m - 1)
    return key


def week_ja(w):
    a, b = datetime.date.fromisoformat(w["start"]), datetime.date.fromisoformat(w["end"])
    return "%d月%d日（月）〜%s%d日（日）" % (a.month, a.day, "" if a.month == b.month else "%d月" % b.month, b.day)


def week_en(w):
    return "%s–%s" % (md_en(w["start"]), md_en(w["end"]))


def table(head, rows, num_from=1):
    numre = re.compile(r"^[-−—\d,.%]+$")
    return ('<div class="rp-table"><table><thead><tr>' + "".join('<th scope="col">%s</th>' % esc(c) for c in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join('<%s%s>%s</%s>' % ("th scope=\"row\"" if j == 0 else "td", ' class="rp-n"' if j >= num_from and numre.match(c) else "", esc(c), "th" if j == 0 else "td")
                              for j, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>")


# ------------------------------------------------------------------ 入力の検査
def load(path=SRC):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, "速報の数字（%s）を読めない: %s" % (path, e)
    if d.get("schema") != 1:
        return None, "速報の数字の形（schema）が違う: %r" % d.get("schema")
    j, e = d.get("jepx") or {}, d.get("eprx") or {}
    if not (j.get("ok") and e.get("ok")):
        return None, "卸電気か需給調整市場の数字が欠けている"
    for k in (j.get("latest_day"), e.get("latest_day"), d.get("made_on")):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", k or ""):
            return None, "日付の形が違う: %r" % k
    if [a for a in AREAS if a not in j["mtd"]["areas"]] or len(e["mtd"]["rows"]) != 7:
        return None, "エリアか商品の数が違う"
    return d, ""


def lastmod_of(text, path, day):
    mt = re.search(r"<url><loc>" + re.escape(BASE + path) + r"</loc>.*?<lastmod>([0-9-]{10})</lastmod>", text)
    return max(day, mt.group(1)) if mt else day


# ------------------------------------------------------------------ 文（決まった型・数字は入力のまま）
def week_moves(d, lang):
    """先週（最新の、7日そろった月曜〜日曜）の動き3つ。需給調整市場の7日がそろっていない週は需給調整市場の文を出さない。"""
    ws = d.get("weeks") or []
    if not ws:
        return None, []
    w, p = ws[0], (ws[1] if len(ws) > 1 else None)
    out = []
    E, PE = w.get("eprx") or {}, ((p or {}).get("eprx") or {})
    J, PJ = w["jepx"], (p or {}).get("jepx") or {}
    if lang == "ja":
        lab = "%s" % week_ja(w)
        if "1-0" in E:
            s = "%sの一次調整力（オンライン）の応札倍率は%s、平均落札価格は%s円/kW・30分でした（速報値）。" % (lab, f(E["1-0"]["ratio"], 1, "%"), f(E["1-0"]["price"]))
            if "1-0" in PE:
                s += "前の週は%s、%s円でした。" % (f(PE["1-0"]["ratio"], 1, "%"), f(PE["1-0"]["price"]))
            out.append(s)
        if "3-2" in E:
            out.append("三次調整力②の平均落札価格は%s円/kW・30分でした（前の週は%s円）。" % (f(E["3-2"]["price"]), f((PE.get("3-2") or {}).get("price"))))
        s = "卸電気のシステムプライス（全国）の平均は%s円/kWh、4時間の値差（日ごとの差の平均）は東京で%s円、九州で%s円でした" % (f(J["system"]), f(J["tokyo_s4"]), f(J["kyushu_s4"]))
        out.append(s + ("（前の週は%s円、%s円、%s円）。" % (f(PJ.get("system")), f(PJ.get("tokyo_s4")), f(PJ.get("kyushu_s4"))) if PJ else "。"))
    else:
        lab = "In the week of %s" % week_en(w)
        if "1-0" in E:
            s = "%s, primary reserve (online) had a bid ratio of %s and an average winning price of %s yen/kW per 30 min (preliminary)." % (lab, f(E["1-0"]["ratio"], 1, "%"), f(E["1-0"]["price"]))
            if "1-0" in PE:
                s += " The week before: %s and %s yen." % (f(PE["1-0"]["ratio"], 1, "%"), f(PE["1-0"]["price"]))
            out.append(s)
        if "3-2" in E:
            out.append("Tertiary reserve 2 had an average winning price of %s yen/kW per 30 min (the week before: %s yen)." % (f(E["3-2"]["price"]), f((PE.get("3-2") or {}).get("price"))))
        s = "The JEPX system price averaged %s yen/kWh; the 4-hour spread (average of daily spreads) was %s yen in Tokyo and %s yen in Kyushu" % (f(J["system"]), f(J["tokyo_s4"]), f(J["kyushu_s4"]))
        out.append(s + (" (the week before: %s, %s and %s yen)." % (f(PJ.get("system")), f(PJ.get("tokyo_s4")), f(PJ.get("kyushu_s4"))) if PJ else "."))
    return w, out


# ------------------------------------------------------------------ 図（日ごとの4時間の値差・軽い SVG）
def chart(d, lang):
    days = (d["jepx"].get("daily") or [])
    if len(days) < 2:
        return ""
    W, H, L, R, T, B = 640, 250, 40, 12, 26, 34
    ser = [("東京", "#1D4ED8", "Tokyo"), ("九州", "#C2560A", "Kyushu")]
    vals = [x["areas"][a]["s4"] for x in days for a, _, _ in ser if x["areas"][a]["s4"] is not None]
    if not vals:
        return ""
    top = max(10, math.ceil(max(vals) / 10.0) * 10)
    n = len(days)
    X = lambda i: L + (W - L - R) * (i / (n - 1))  # noqa: E731
    Y = lambda v: T + (H - T - B) * (1 - v / top)  # noqa: E731
    g = []
    for v in range(0, top + 1, 10):
        g.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#E2E8F0"/><text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="#4A5568">%d</text>' % (L, W - R, Y(v), Y(v), L - 6, Y(v) + 4, v))
    for i, x in enumerate(days):                         # 月の初めの日に区切りと月の名前
        if x["date"].endswith("-01") or i == 0:
            g.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#CBD5E1" stroke-dasharray="3 3"/><text x="%.1f" y="%d" font-size="11" fill="#4A5568">%s</text>' % (
                X(i), X(i), T, H - B, X(i) + 3, H - B + 16, esc(mon_ja(x["date"][:7]) if lang == "ja" else mon_en(x["date"][:7]))))
    for a, col, en in ser:
        pts = " ".join("%.1f,%.1f" % (X(i), Y(x["areas"][a]["s4"])) for i, x in enumerate(days) if x["areas"][a]["s4"] is not None)
        g.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (col, pts))
    lg = []
    for k, (a, col, en) in enumerate(ser):
        lg.append('<rect x="%d" y="6" width="14" height="4" fill="%s"/><text x="%d" y="12" font-size="12" fill="#0B1530">%s</text>' % (L + k * 90, col, L + k * 90 + 18, esc(a if lang == "ja" else en)))
    unit = "円/kWh" if lang == "ja" else "yen/kWh"
    title = ("日ごとの4時間の値差（東京・九州・%s）" % unit) if lang == "ja" else ("Daily 4-hour spread (Tokyo and Kyushu, %s)" % unit)
    svg = ('<svg viewBox="0 0 %d %d" role="img" aria-label="%s"><title>%s</title>%s%s<text x="%d" y="%d" font-size="11" text-anchor="end" fill="#4A5568">%s</text></svg>' % (
        W, H, esc(title), esc(title), "".join(g), "".join(lg), W - R, 12, unit))
    cap = ("図: %s。前月と今月の受渡日ごと。値差は、その日の高い8コマ（4時間）の平均から安い8コマの平均を引いた差。出典: JEPX のスポット市場の取引結果から当社集計。" % title) if lang == "ja" else (
        "Figure: %s, by delivery day for last month and this month. The spread is the average of the 8 most expensive half-hour slots (4 hours) minus the average of the 8 cheapest. Source: JEPX spot results, aggregated by ScienceX." % title)
    return '<figure class="fl-chart">%s<figcaption class="md-note">%s</figcaption></figure>' % (svg, esc(cap))


# ------------------------------------------------------------------ 頁
def kpis(d, lang):
    j, e = d["jepx"], d["eprx"]
    er = {r["code"]: r for r in e["mtd"]["rows"]}
    pr = {r["code"]: r for r in ((e.get("prev") or {}).get("rows") or [])}
    pa = (j.get("prev") or {}).get("areas") or {}
    J = lang == "ja"
    rows = [
        (f(j["mtd"]["areas"]["システム"]["avg"]), "円/kWh" if J else "yen/kWh", "卸電気 システムプライスの平均" if J else "JEPX system price, average",
         f((pa.get("システム") or {}).get("avg"))),
        (f(j["mtd"]["areas"]["東京"]["s4"]), "円/kWh" if J else "yen/kWh", "東京の4時間の値差" if J else "Tokyo 4-hour spread", f((pa.get("東京") or {}).get("s4"))),
        (f(j["mtd"]["areas"]["九州"]["s4"]), "円/kWh" if J else "yen/kWh", "九州の4時間の値差" if J else "Kyushu 4-hour spread", f((pa.get("九州") or {}).get("s4"))),
        (f(er["1-0"]["ratio"], 1, "%"), "", "一次調整力（オンライン）の応札倍率・速報値" if J else "Primary reserve (online) bid ratio, preliminary",
         f((pr.get("1-0") or {}).get("ratio"), 1, "%")),
        (f(er["3-2"]["price"]), "円" if J else "yen", "三次調整力②の平均落札価格（円/kW・30分）" if J else "Tertiary reserve 2 average winning price (yen/kW per 30 min)",
         f((pr.get("3-2") or {}).get("price"))),
    ]
    # 今月の期間と前月の名前は、市場ごとに別に出す（月の変わり目は卸電気が翌日の受渡分で先に次の月へ進み、需給調整市場とずれる＝2026-11-23 別の目①）
    jm, em = j["mtd"], e["mtd"]
    jpm, epm = (j.get("prev") or {}).get("month") or "", (e.get("prev") or {}).get("month") or ""
    if J:
        jper, eper = "今月 %s〜%s" % (md_ja(jm["from"]), md_ja(jm["to"])), "今月 %s〜%s" % (md_ja(em["from"]), md_ja(em["to"]))
        jpre, epre = "前月（%s・全日）" % mon_ja(jpm) if jpm else "前月", "前月（%s・全日）" % mon_ja(epm) if epm else "前月"
    else:
        jper, eper = "%s–%s" % (md_en(jm["from"]), md_en(jm["to"])), "%s–%s" % (md_en(em["from"]), md_en(em["to"]))
        jpre, epre = "Last month (%s, all days)" % mon_en(jpm) if jpm else "Last month", "Last month (%s, all days)" % mon_en(epm) if epm else "Last month"
    per = [jper, jper, jper, eper, eper]
    pre = [jpre, jpre, jpre, epre, epre]
    out = '<div class="fl-kpi">' + "".join("<div><b>%s<small>%s</small></b><span>%s（%s）</span><i>%s: %s</i></div>" % (
        esc(v), esc(u), esc(l), esc(per[i]), esc(pre[i]), esc(p)) if J else "<div><b>%s<small>%s</small></b><span>%s (%s)</span><i>%s: %s</i></div>" % (
        esc(v), esc(u), esc(l), esc(per[i]), esc(pre[i]), esc(p)) for i, (v, u, l, p) in enumerate(rows)) + "</div>"
    note = ("4時間の値差＝その日の高い4時間と安い4時間の平均の差（円/kWh）。応札倍率＝応札量÷募集量。どちらも収益を示すものではありません。詳しい表は下にあります。" if J else
            "4-hour spread = average of the day's 4 most expensive hours minus its 4 cheapest (yen/kWh). Bid ratio = bids ÷ requirement. Neither is a revenue figure. Full tables below.")
    return out + '<p class="md-note">%s</p>' % esc(note)


def eprx_table(d, lang):
    e = d["eprx"]
    J = lang == "ja"
    pr = {r["code"]: r for r in ((e.get("prev") or {}).get("rows") or [])}
    dr = {r["code"]: r for r in e["day"]["rows"]}
    m0, m1, ld = e["mtd"]["from"], e["mtd"]["to"], e["day"]["date"]
    pm = (e.get("prev") or {}).get("month") or ""
    if J:
        cm = "今月（%s〜%s）" % (md_ja(m0), md_ja(m1))
        head = ["商品", "応札倍率 " + cm, "応札倍率 最新の1日（%s）" % md_ja(ld), "応札倍率 前月（%s・全日）" % mon_ja(pm) if pm else "前月",
                "平均落札価格 " + cm, "平均落札価格 最新の1日", "平均落札価格 前月（全日）"]
    else:
        cm = "this month (%s–%s)" % (md_en(m0), md_en(m1))
        head = ["Product", "Bid ratio, " + cm, "Bid ratio, latest day (%s)" % md_en(ld), "Bid ratio, last month (%s)" % mon_en(pm) if pm else "Last month",
                "Avg. winning price, " + cm, "Avg. winning price, latest day", "Avg. winning price, last month"]
    rows = []
    for r in e["mtd"]["rows"]:
        c = r["code"]
        rows.append([r["name"] if J else PROD_EN[c], f(r["ratio"], 1, "%"), f(dr[c]["ratio"], 1, "%"), f((pr.get(c) or {}).get("ratio"), 1, "%"),
                     f(r["price"]), f(dr[c]["price"]), f((pr.get(c) or {}).get("price"))])
    return table(head, rows)


def jepx_table(d, lang):
    j = d["jepx"]
    J = lang == "ja"
    pa = (j.get("prev") or {}).get("areas") or {}
    da = j["day"]["areas"]
    m0, m1, ld = j["mtd"]["from"], j["mtd"]["to"], j["day"]["date"]
    pm = (j.get("prev") or {}).get("month") or ""
    if J:
        cm = "今月（%s〜%s）" % (md_ja(m0), md_ja(m1))
        head = ["エリア", "平均 " + cm, "平均 最新の1日（%s）" % md_ja(ld), "平均 前月（%s・全日）" % mon_ja(pm) if pm else "前月",
                "4時間の値差 " + cm, "4時間の値差 最新の1日", "4時間の値差 前月（全日）"]
    else:
        cm = "this month (%s–%s)" % (md_en(m0), md_en(m1))
        head = ["Area", "Average, " + cm, "Average, latest day (%s)" % md_en(ld), "Average, last month (%s)" % mon_en(pm) if pm else "Last month",
                "4-hour spread, " + cm, "4-hour spread, latest day", "4-hour spread, last month"]
    rows = []
    for a in AREAS:
        m = j["mtd"]["areas"][a]
        rows.append([AREA_JA.get(a, a) if J else AREA_EN[a], f(m["avg"]), f(da[a]["avg"]), f((pa.get(a) or {}).get("avg")),
                     f(m["s4"]), f(da[a]["s4"]), f((pa.get(a) or {}).get("s4"))])
    return table(head, rows)


def weeks_table(d, lang):
    J = lang == "ja"
    head = (["週（受渡日）", "システムプライスの平均（円/kWh）", "東京の4時間の値差（円/kWh）", "九州の4時間の値差（円/kWh）", "一次調整力（オンライン）の応札倍率",
             "一次調整力（オンライン）の平均落札価格", "一次調整力（オフライン）の平均落札価格", "三次調整力②の平均落札価格"] if J else
            ["Week (delivery days)", "System price average (yen/kWh)", "Tokyo 4-hour spread (yen/kWh)", "Kyushu 4-hour spread (yen/kWh)", "Primary (online) bid ratio",
             "Primary (online) avg. winning price", "Primary (offline) avg. winning price", "Tertiary 2 avg. winning price"])
    rows = []
    for w in d.get("weeks") or []:
        E = w.get("eprx") or {}
        rows.append([week_ja(w) if J else week_en(w), f(w["jepx"]["system"]), f(w["jepx"]["tokyo_s4"]), f(w["jepx"]["kyushu_s4"]),
                     f((E.get("1-0") or {}).get("ratio"), 1, "%"), f((E.get("1-0") or {}).get("price")), f((E.get("1-1") or {}).get("price")), f((E.get("3-2") or {}).get("price"))])
    return table(head, rows) if rows else ""


def asof_rows(d, lang):
    j, e = d["jepx"], d["eprx"]
    J = lang == "ja"
    jf = max((v.get("fetched") or "") for v in (j.get("files") or {"x": {"fetched": d["made_on"]}}).values()) or d["made_on"]
    ef = e.get("fetched") or d["made_on"]
    if J:
        return [["卸電気（JEPX）スポット市場・今月", "%s〜%s（%d日分・受渡日）" % (d_ja(j["mtd"]["from"]), md_ja(j["mtd"]["to"]), j["mtd"]["days"]), "取引結果（確定した約定値）", d_ja(jf)],
                ["卸電気（JEPX）・前月", "%s（%d日分）" % (mon_ja(j["prev"]["month"]), j["prev"]["days"]) if j.get("prev") else "—", "取引結果（確定した約定値）", d_ja(jf)],
                ["需給調整市場（EPRX）・今月", "%s〜%s（%d日分・受渡日）" % (d_ja(e["mtd"]["from"]), md_ja(e["mtd"]["to"]), e["mtd"]["days"]), "速報値", d_ja(ef)],
                ["需給調整市場（EPRX）・前月", "%s（%d日分）" % (mon_ja(e["prev"]["month"]), e["prev"]["days"]) if e.get("prev") else "—", "速報値", d_ja(ef)]]
    return [["JEPX spot, this month", "%s to %s (%d days, delivery)" % (d_en(j["mtd"]["from"]), md_en(j["mtd"]["to"]), j["mtd"]["days"]), "Trading results (settled)", d_en(jf)],
            ["JEPX spot, last month", "%s (%d days)" % (mon_en(j["prev"]["month"]), j["prev"]["days"]) if j.get("prev") else "—", "Trading results (settled)", d_en(jf)],
            ["EPRX balancing market, this month", "%s to %s (%d days, delivery)" % (d_en(e["mtd"]["from"]), md_en(e["mtd"]["to"]), e["mtd"]["days"]), "Preliminary", d_en(ef)],
            ["EPRX balancing market, last month", "%s (%d days)" % (mon_en(e["prev"]["month"]), e["prev"]["days"]) if e.get("prev") else "—", "Preliminary", d_en(ef)]]


def jsonld(d, lang, title, desc, modified):
    J = lang == "ja"
    path = PATH if J else PATH_EN
    j, e = d["jepx"], d["eprx"]
    start = min([(j.get("prev") or {}).get("month", j["mtd"]["from"][:7]) + "-01", e["mtd"]["from"]] + [w["start"] for w in d.get("weeks") or []])
    end = max(j["latest_day"], e["latest_day"])
    org, pub = (bmd.ORG, brp.PUBLISHER) if J else (brp.EN_ORG, brp.EN_PUBLISHER)
    csv = "%s/%s/jepx-daily.csv" % (BASE, path.strip("/"))
    page = {"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path, "name": title, "description": desc,
            "inLanguage": lang, "publisher": pub, "datePublished": FIRST, "dateModified": modified,
            "isPartOf": {"@type": "CollectionPage", "url": BASE + ("/report" if J else "/en/report")}}
    ds = {"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset", "url": BASE + path,
          "name": (NAME + "の数字") if J else (NAME_EN + ": figures"),
          "description": ("卸電気（JEPX スポット市場）の10エリアの平均価格と4時間の値差、需給調整市場（EPRX）の7商品の応札倍率・平均落札価格（速報値）を、"
                          "公表データから毎日取り直して当社が集計した数字。今月ここまで・最新の1日・前月（全日）・週ごと。") if J else
                         ("Average prices and 4-hour spreads for the 10 JEPX spot areas, and bid ratios and average winning prices for the 7 EPRX "
                          "balancing products (preliminary), re-fetched from published data every day and aggregated by ScienceX: this month so far, the latest day, last month and by week."),
          "inLanguage": lang, "creator": org, "publisher": pub, "isAccessibleForFree": True, "dateModified": modified,
          "temporalCoverage": "%s/%s" % (start, end), "spatialCoverage": {"@type": "Place", "name": "日本" if J else "Japan"},
          "creditText": ("出典: サイエンスエックス株式会社『%s』%s%s" % (NAME, BASE, path)) if J else ("Source: Science X Inc., “%s”, %s%s" % (NAME_EN, BASE, path)),
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": csv,
                            "name": "卸電気（JEPX）の日ごとの平均と4時間の値差（CSV）" if J else "JEPX daily averages and 4-hour spreads (CSV)"}],
          "mainEntityOfPage": BASE + path}
    cr = bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + "/report"), ("速報", BASE + path)] if J else
                    [("Home", BASE + "/en"), ("Market Notes", BASE + "/en/report"), ("Daily Flash", BASE + path)])
    return "\n".join(bmd.ld(x) for x in (page, ds, cr))


def render(d, lang, modified, latest_issue):
    J = lang == "ja"
    j, e = d["jepx"], d["eprx"]
    w, moves = week_moves(d, lang)
    if J:
        title = "市場ノート 速報｜卸電気・需給調整市場を毎日更新｜サイエンスエックス"
        desc = ("卸電気（JEPX）と需給調整市場（EPRX）の最新の数字を、公表データを毎朝取り直して出す速報。10エリアの平均価格と4時間の値差、7商品の応札倍率と平均落札価格を、"
                "今月ここまで・最新の1日・前月（全日）・週ごとで比べます。出典つき、CSV あり。")   # 日付は頁の頭と dateModified に（説明は毎日変えない＝llms.txt を日ごとに古くしない）
        crumbs = bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", "/report"), ("速報", PATH)])
        issue = ('<a class="btn-primary" href="/report/%s">最新の月号を読む（%s号＝%sの数字）</a>' % (latest_issue, mon_ja(latest_issue), mon_ja(issue_data_month(latest_issue)))) if latest_issue else ""
        hero = f"""<section class="hero"><div class="container">
  <div class="section-label">毎日更新（速報）</div>
  <h1>{esc(NAME)}</h1>
  <p class="fl-pair"><b>速報</b>＝毎朝更新の最新の数字（この頁）。<b>月号</b>＝毎月1日に出す、前月まるごとの図と表。</p>
  <div class="fl-asof"><div class="h">データの時点（{esc(d_ja(d['made_on']))}の朝に公表データを取り直し）</div><b>卸電気（JEPX）: {esc(d_ja(j['latest_day'], True))}分まで</b><b>需給調整市場（EPRX）: {esc(d_ja(e['latest_day'], True))}分まで（速報値）</b><span>日付は電気を受け渡す日（受渡日）です。卸電気は前日に売買が決まるので、翌日分まで入ることがあります。</span></div>
  <p>卸電気（JEPX）と需給調整市場（EPRX）の数字を、公表された最新のデータから毎朝作り直しています。今月ここまで・最新の1日・前月（全日）・週ごとで比べられます。</p>
  <p class="fl-two">{issue}<a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/report">月号の一覧</a></p>
</div></section>"""
        s_week = ("<h2 class=\"md-h\">先週の動き（%s）</h2>" % esc(week_ja(w))) if w else "<h2 class=\"md-h\">週ごとの数字</h2>"
        wk_lead = "月曜から日曜までの7日がそろった週の数字です。需給調整市場は速報値です。"
        s2h, s3h, s4h = "需給調整市場（EPRX）｜今月ここまで", "卸電気（JEPX）｜今月ここまで", "データの時点と出典"
        e_note = ("応札倍率＝応札量÷募集量、平均落札価格＝落札量で重みを付けた平均（円/kW・30分）。全国の値（公表ファイルの合計の列）。今月の数字は月の途中の速報値で、"
                  "月が終わると変わります。月が終わってから公表される確報値とは少し違うことがあります。出典: 電力需給調整力取引所（EPRX）公表の取引結果（速報値）。当社集計。")
        j_note = ("平均は30分コマの単純平均。4時間の値差は、その日の高い8コマ（4時間）の平均から安い8コマの平均を引いた差の、日ごとの平均です（安い時間と高い時間の順番、"
                  "充放電で失う電気、手数料・税・託送の費用は見ていません。収益を示すものではありません）。出典: 日本卸電力取引所（JEPX）公表のスポット市場の取引結果。当社集計。")
        csvl = '<p class="md-note">卸電気の日ごとの数字（今月と前月・10エリア）: <a href="/report/flash/jepx-daily.csv" download>CSV（日ごとの平均と4時間の値差）</a></p>'
        asof_head = ["出所", "対象の期間", "種類", "取り直した日"]
        notes = ["数字は出典の公表値から当社が機械で集計したもので、毎朝作り直します。取り直せなかった日は、前の日の版のまま（上の「データの時点」の日付も前のまま）です。",
                 "「速報値」は約定した直後に公表される値、「確報値」は月が終わってから公表される値です（約定のあとの追加調達や訂正を反映）。この頁の需給調整市場の数字は全部速報値です。",
                 "受渡日は電気を受け渡す日です。卸電気のスポット市場は前の日に取引するので、翌日の受渡分まで出ることがあります。"]
        more = ('<ul class="rp-list" style="margin-top:14px">'
                '<li><a class="t" href="/report">蓄電所の市場ノート（月号・毎月1日）</a><p>前月の全日の数字を、需給調整市場・卸電気・容量市場の順に図と表でまとめた号。PDF あり。</p></li>'
                '<li><a class="t" href="/report/data">市場データ（号をまたいだ推移・CSV）</a><p>卸電気のエリア別の月ごとの推移と容量市場のエリアプライス。</p></li>'
                '<li><a class="t" href="/market-data">系統用蓄電池の売り案件 市場データ</a><p>当社の蓄電所マーケットに載る売り案件の、管内別・電圧別などの集計（毎朝更新）。</p></li>'
                '</ul><p class="md-note" style="margin-top:12px">図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。</p>')
        footer = bmd.FOOTER
    else:
        title = "Daily Flash: Japan JEPX and EPRX figures | ScienceX"
        desc = ("Japan's latest JEPX wholesale and EPRX balancing figures, re-fetched every morning: area prices, 4-hour spreads, bid ratios "
                "and winning prices for this month so far, the latest day, last month and by week.")
        crumbs = bmd.nav_crumbs([("Home", "/en"), ("Market Notes", "/en/report"), ("Daily Flash", PATH_EN)])
        issue = ('<a class="btn-primary" href="/en/report/%s">Read the latest monthly issue (%s issue, %s data)</a>' % (latest_issue, mon_en(latest_issue), mon_en(issue_data_month(latest_issue)))) if latest_issue else ""
        hero = f"""<section class="hero"><div class="container">
  <div class="section-label">Updated daily (flash)</div>
  <h1>{esc(NAME_EN)}</h1>
  <p class="fl-pair"><b>Daily Flash</b> = the latest figures, updated every morning (this page). <b>Monthly issue</b> = the whole previous month in charts and tables, out on the 1st.</p>
  <div class="fl-asof"><div class="h">Data as of (re-fetched from published data on the morning of {esc(d_en(d['made_on']))})</div><b>JEPX wholesale: up to delivery on {esc(d_en(j['latest_day']))}</b><b>EPRX balancing market: up to delivery on {esc(d_en(e['latest_day']))} (preliminary)</b><span>Dates are delivery days (the day the power is delivered). JEPX trades the day before, so it can run one day ahead.</span></div>
  <p>Figures for two markets that pay battery storage sites in Japan, JEPX wholesale power and the EPRX balancing market, re-fetched from the latest published data every morning: this month so far, the latest day, last month (all days) and by week. The monthly issue, with charts and tables for the whole previous month, comes out on the 1st of each month.</p>
  <p class="fl-two">{issue}<a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/report">All monthly issues</a></p>
</div></section>"""
        s_week = ("<h2 class=\"md-h\">Last week (%s)</h2>" % esc(week_en(w))) if w else "<h2 class=\"md-h\">By week</h2>"
        wk_lead = "Weeks run Monday to Sunday; only weeks with all 7 days are shown. Balancing market figures are preliminary."
        s2h, s3h, s4h = "EPRX balancing market: this month so far", "JEPX wholesale power: this month so far", "Data dates and sources"
        e_note = ("Bid ratio = bids / procurement; average winning price = weighted by awarded volume (yen/kW per 30 min). National totals. This month's figures are preliminary "
                  "and change after the month ends; final values published later can differ slightly. Source: EPRX trading results (preliminary), aggregated by ScienceX.")
        j_note = ("Averages are simple averages of half-hour slots. The 4-hour spread is the average of the 8 most expensive slots minus the average of the 8 cheapest, averaged over days "
                  "(it ignores slot order, losses, fees, taxes and network charges, and is not a revenue figure). Source: JEPX spot market results, aggregated by ScienceX.")
        csvl = '<p class="md-note">JEPX daily figures (this month and last month, 10 areas): <a href="/en/report/flash/jepx-daily.csv" download>CSV (daily averages and 4-hour spreads)</a></p>'
        asof_head = ["Source", "Period", "Type", "Fetched on"]
        notes = ["Figures are aggregated automatically by ScienceX from published data and rebuilt every morning. If a fetch fails, the previous day's version stays (and so do the dates at the top).",
                 "Preliminary values are published right after the auction; final values are published after the month ends (with later additional procurement and corrections). All balancing market figures here are preliminary.",
                 "Delivery day is the day electricity is delivered. JEPX spot trades the day before, so figures can run to the next day's delivery."]
        more = ('<ul class="rp-list" style="margin-top:14px">'
                '<li><a class="t" href="/en/report">Battery Storage Market Notes (monthly issue, 1st of each month)</a><p>The whole previous month in charts and tables: balancing, wholesale and capacity markets. PDF available.</p></li>'
                '<li><a class="t" href="/en/report/data">Market Data (across issues, CSV)</a><p>Monthly JEPX figures by area and capacity market area prices.</p></li>'
                '<li><a class="t" href="/en/market-data">Japan BESS Projects for Sale: Market Data</a><p>Counts of projects listed on our marketplace by area and voltage (updated daily).</p></li>'
                '</ul><p class="md-note" style="margin-top:12px">Charts and figures may be reused with the source stated (<a href="/en/press">citation guide</a>).</p>')
        footer = bmd.EN_FOOTER
    scroll = '<p class="fl-scroll">%s</p>' % ("表は横にずらして見られます →" if J else "Swipe the table sideways to see all columns →")
    mk = ('<div class="fl-mk"><p>%s</p><a class="btn-primary" href="%s" data-cta="body" data-cta-target="market">%s</a></div>' % (
        ("いま売りに出ている蓄電所の案件は、蓄電所マーケットで登録なしで一覧できます（価格と資料は無料の登録のあと）。", "https://dealroom.scix.co.jp/", "蓄電所マーケットで案件を見る") if J else
        ("Battery storage projects for sale in Japan are listed on our marketplace; browse without signing up (prices and documents after free registration).", "https://dealroom.scix.co.jp/en", "See projects for sale")))
    body = f"""{crumbs}
{hero}
<section class="md" id="kpi"><div class="container rp-body">
{kpis(d, lang)}
</div></section>
<section class="md" id="week"><div class="container rp-body">
  {s_week}
  {('<ul class="rp-three">' + "".join("<li>%s</li>" % esc(m) for m in moves) + "</ul>") if moves else ""}
  <p>{esc(wk_lead)}</p>
  {scroll}
  {weeks_table(d, lang)}
</div></section>
<section class="md" id="eprx"><div class="container rp-body">
  <h2 class="md-h">{esc(s2h)}</h2>
  {scroll}
  {eprx_table(d, lang)}
  <p class="md-note">{esc(e_note)}</p>
</div></section>
<section class="md" id="jepx"><div class="container rp-body">
  <h2 class="md-h">{esc(s3h)}</h2>
  {scroll}
  {jepx_table(d, lang)}
  <p class="md-note">{esc(j_note)}</p>
  {chart(d, lang)}
  {csvl}
</div></section>
<section class="md" id="asof"><div class="container rp-body">
  <h2 class="md-h">{esc(s4h)}</h2>
  {table(asof_head, asof_rows(d, lang), 9)}
  <ul>{"".join("<li>%s</li>" % esc(n) for n in notes)}</ul>
  {more}
  {mk}
</div></section>
{footer}
</body>
</html>
"""
    js = jsonld(d, lang, title, desc, modified)
    if J:
        h = brp.page_head(title, desc, PATH, js, PATH_EN)
    else:
        h = brp.page_head_en(title, desc, PATH_EN, js, PATH)
    core = body.split(footer)[0]                    # 下の帯（会社の住所）を除いた中身＝禁止の語を見る相手
    return h.replace("</style>", CSS + "</style>", 1) + body, moves, w, core


def csv_daily(d, lang):
    J = lang == "ja"
    head = ["受渡日", "エリア", "平均（円/kWh）", "4時間の値差（円/kWh）"] if J else ["delivery_date", "area", "average_yen_per_kwh", "spread_4h_yen_per_kwh"]
    out = [",".join(head)]
    for x in d["jepx"].get("daily") or []:
        for a in AREAS:
            v = x["areas"][a]
            out.append(",".join([x["date"], AREA_JA.get(a, a) if J else AREA_EN[a], f(v["avg"]), f(v["s4"])]).replace("—", ""))
    src = ("出典: 日本卸電力取引所（JEPX）スポット市場の取引結果から サイエンスエックス株式会社が集計（%s%s）" % (BASE, PATH)) if J else \
          ("Source: JEPX spot market results, aggregated by Science X Inc. (%s%s)" % (BASE, PATH_EN))
    out.append('"%s"' % src)
    return ("﻿" + "\r\n".join(out) + "\r\n").encode("utf-8")


def flash_json(d, moves_ja, moves_en, w):
    out = {"made_on": d["made_on"], "jepx_day": d["jepx"]["latest_day"], "eprx_day": d["eprx"]["latest_day"], "url": PATH, "title": NAME,
           "week": ({"start": w["start"], "end": w["end"], "key": w["end"], "eprx": bool(w.get("eprx"))} if w else None), "moves": moves_ja,
           "en": {"url": PATH_EN, "title": NAME_EN, "moves": moves_en}}
    return (json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def sitemap_rows(text, modified):
    def ent(path, other, lang, pr):
        lm = lastmod_of(text, path, modified)
        me = '<xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (lang, BASE, path)
        ot = '<xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % ("en" if lang == "ja" else "ja", BASE, other)
        return "  <url><loc>%s%s</loc>%s%s<priority>%s</priority><lastmod>%s</lastmod></url>\n" % (BASE, path, me if lang == "ja" else me, ot, pr, lm)
    add = ""
    for path, other, lang, pr in ((PATH, PATH_EN, "ja", "0.7"), (PATH_EN, PATH, "en", "0.6")):
        new = ent(path, other, lang, pr)
        pat = re.compile(r"  <url><loc>" + re.escape(BASE + path) + r"</loc>.*?</url>\n")
        if pat.search(text):
            text = pat.sub(lambda _m: new, text, count=1)
        else:
            add += new
    return text.replace("</urlset>", add + "</urlset>", 1) if add else text


def safety(texts):
    hits = []
    for t in texts:
        for rx, why in brp.FORBIDDEN:
            m = re.search(rx, t)
            if m:
                hits.append("%s「%s」" % (why, m.group(0)[:30]))
    return hits


def main():
    check = "--check" in sys.argv
    d, err = load()
    if not d:
        print("NG " + err + "（何も書かない）")
        return 2
    cur = {}
    try:
        cur = json.load(open(os.path.join(ROOT, "report/flash/latest.json"), encoding="utf-8"))
    except (OSError, ValueError):
        pass
    for k_in, k_cur in (("jepx", "jepx_day"), ("eprx", "eprx_day")):
        if (cur.get(k_cur) or "") > d[k_in]["latest_day"]:
            print("NG 入力の%sの最新の受渡日 %s が、焼いてある頁（%s）より古い＝書かない" % (k_in, d[k_in]["latest_day"], cur[k_cur]))
            return 2
    sm_path = os.path.join(ROOT, "sitemap.xml")
    sm = open(sm_path, encoding="utf-8").read()
    same_data = cur.get("jepx_day") == d["jepx"]["latest_day"] and cur.get("eprx_day") == d["eprx"]["latest_day"] and cur.get("made_on")
    modified = cur.get("made_on") if same_data else d["made_on"]     # 数字が同じなら dateModified も前のまま（毎日焼き直しても日付だけ進めない）
    latest_issue = ""
    try:
        latest_issue = json.load(open(os.path.join(ROOT, "report/latest.json"), encoding="utf-8")).get("key") or ""
    except (OSError, ValueError):
        pass
    if not os.path.exists(os.path.join(ROOT, "en/report", latest_issue, "index.html")):
        latest_issue_en = ""
    else:
        latest_issue_en = latest_issue
    dd = dict(d, made_on=modified)
    ja, mv_ja, w, core_ja = render(dd, "ja", modified, latest_issue)
    en, mv_en, _, core_en = render(dd, "en", modified, latest_issue_en)
    hits = safety([core_ja, core_en, json.dumps(d, ensure_ascii=False)])
    if hits:
        print("NG 公開してはいけない語がある。何も書かない: " + "／".join(hits))
        return 2
    files = {"report/flash/index.html": ja.encode("utf-8"), "en/report/flash/index.html": en.encode("utf-8"),
             "report/flash/latest.json": flash_json(dd, mv_ja, mv_en, w),
             "report/flash/jepx-daily.csv": csv_daily(d, "ja"), "en/report/flash/jepx-daily.csv": csv_daily(d, "en")}
    sm2 = sitemap_rows(sm, modified)
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
                with open(p, "wb") as fh:
                    fh.write(data)
    print(("ずれ: " if check else "更新: ") + (", ".join(changed) if changed else "なし（最新）"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
