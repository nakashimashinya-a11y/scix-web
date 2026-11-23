#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「蓄電所の市場ノート 速報」（/report/flash・/en/report/flash・毎日更新）を焼く。

2026-11-23 中島（対話画面）「市場レポートの考え方整理。毎日最新データを落として速報。毎月１日に先月のデータを落として月報。
今色々あってわかりにくい。JEPXと需給調整のレポートを分ける必要ないよね。」「メニュー多いのは良くない。シンプルに。速報で毎日の最新データ。
毎月１日の前月最新データがいい。」＝市場の頁は2本だけ: 速報（この頁・毎日）と月の号（/report/<YYYY-MM>・毎月1日・build_reports.py）。

読むもの（リポジトリには置かない）: ~/.openclaw/workspace/state/market_flash/latest.json（bin/market_flash.py が毎朝、公表データを取り直して数える。
  数字と日付だけ。文はここで決まった型にはめる＝LLM を使わない）。SCIX_FLASH_JSON で替えられる。
2026-11-24 中島（対話画面）「グラフにしてくれないと読まない。先週じゃなくて、当月の動きを１日から全部出して。月報と同じく、需給調整が先頭だよね。
月報と全く違うフォーマットにして何が楽しい。」＝頁の型を月号と同じにする: 節の並びは 今月の動き3つ → ①需給調整市場（EPRX）→ ②卸電気（JEPX）→ 表、
図は月号と同じ描き方（作業域の bin/market_flash_figs.py が描く SVG・11枚）、中身は当月1日からの日ごとと今月ここまで。週ごとの表は頁に出さない。

生成するもの（全文を書き直す。手で直さない）:
  report/flash/index.html, en/report/flash/index.html   頁（頭に「何月何日のデータまで」・今月の動き3つ・図11枚・今月ここまで／最新の1日／前月〔全日〕の表・日ごとの表）
  report/flash/<名前>.svg, en/report/flash/<名前>.svg     図（速報の数字と同じ置き場の figs/{ja,en}/ から写す。数字と一緒に作られた物だけ＝入力の figs.ok）
  report/flash/latest.json                              速報の要点（データの日付・今月の動きの文・週の印）。bin/press_release.py の速報の本が読む
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
FIG_SRC = os.path.join(os.path.dirname(SRC), "figs")     # <言葉>/<名前>.svg（数字と同じ回に bin/market_flash.py が描く）
FIG_NAMES = ["e1", "e2", "e3", "e4", "e5", "e6", "j1", "j2", "j3", "j4", "j5"]   # 頁に出す順＝図1〜図11（需給調整市場が先）
FOUR = ["北海道", "東京", "関西", "九州"]               # 図の線に出す4エリア（月号と同じ）
SPREAD_BIG = 10.0                                       # 4時間の値差がこの円/kWh 以上の日を数える（月号と同じ）
PATH, PATH_EN = "/report/flash", "/en/report/flash"
FIRST = "2026-11-23"      # 頁を作った日（JSON-LD の datePublished。dateModified はデータを取り直した日）
NAME, NAME_EN = "蓄電所の市場ノート 速報", "Battery Storage Market Notes: Daily Flash"
AREAS = ["システム", "北海道", "東北", "東京", "中部", "北陸", "関西", "中国", "四国", "九州"]
AREA_JA = {"システム": "システム（全国）"}
AREA_EN = {"システム": "System (Japan)", "北海道": "Hokkaido", "東北": "Tohoku", "東京": "Tokyo", "中部": "Chubu", "北陸": "Hokuriku", "関西": "Kansai",
           "中国": "Chugoku", "四国": "Shikoku", "九州": "Kyushu"}
PROD_EN = {"1-0": "Primary reserve (online)", "1-1": "Primary reserve (offline)", "2-1": "Secondary reserve 1", "2-2": "Secondary reserve 2",
           "3-1": "Tertiary reserve 1", "3-2": "Tertiary reserve 2", "4-0": "Composite product"}
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
.fl-two{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 0}
.fl-two a{display:inline-block}
.rp-body p,.rp-body li{overflow-wrap:anywhere}
.fl-pair{font-size:1.02rem;line-height:1.8;color:var(--navy);margin:6px 0 4px}.fl-pair b{color:#0F7A52}
#eprx .rp-body,#jepx .rp-body,#daily .rp-body,#asof .rp-body{max-width:1120px}#eprx .rp-table,#jepx .rp-table,#daily .rp-table,#asof .rp-table{max-width:1120px}
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
    for rows in (e["mtd"]["rows"], (e.get("day") or {}).get("rows") or []):
        if [r.get("code") for r in rows] != list(PROD_EN):
            return None, "需給調整市場の商品の並びが違う"
    if [a for a in AREAS if a not in ((j.get("day") or {}).get("areas") or {})]:
        return None, "卸電気の最新の1日のエリアが足りない"
    if not e.get("daily") or len(e["daily"]) != e["mtd"]["days"] or not e.get("detail"):
        return None, "需給調整市場の当月1日からの日ごとの数字が無い"
    g = d.get("figs") or {}
    if not (g.get("ok") and g.get("format") == "svg" and all(n in (g.get("names") or []) for n in FIG_NAMES)):
        return None, "図が数字と一緒に作られていない（figs）"
    if g.get("for") != {"jepx_day": j["latest_day"], "eprx_day": e["latest_day"]}:
        return None, "図の日付が数字の日付と違う（figs.for）"
    return d, ""


def load_figs(d, src=None):
    """図の SVG（日本語・英語）。返り: ({(言葉, 名前): 中身}, 訳)。1枚でも無い・SVG でない・数字と別の日に描いた図＝訳つきで空。"""
    src = src or FIG_SRC
    out = {}
    try:
        made = json.load(open(os.path.join(src, "made_for.json"), encoding="utf-8"))
    except (OSError, ValueError) as ex:
        return {}, "図の日付の控えを読めない（%s）: %s" % (src, ex)
    if made != {"jepx_day": d["jepx"]["latest_day"], "eprx_day": d["eprx"]["latest_day"]}:
        return {}, "図（%s）が数字と別の日の物（図 %s・数字 %s／%s）" % (src, made, d["jepx"]["latest_day"], d["eprx"]["latest_day"])
    for lang in ("ja", "en"):
        for n in FIG_NAMES:
            p = os.path.join(src, lang, n + ".svg")
            try:
                b = open(p, "rb").read()
            except OSError as ex:
                return {}, "図を読めない（%s）: %s" % (p, ex)
            if b"<svg" not in b[:600] or b"</svg>" not in b[-200:]:
                return {}, "図が SVG でない（%s）" % p
            out[(lang, n)] = b
    return out, ""


def svg_dims(b):
    """SVG の viewBox → img の width・height（読み込みの前に場所を確保＝CLS を出さない）。読めなければ空。"""
    m = re.search(rb'viewBox="0 0 ([\d.]+) ([\d.]+)"', b[:800])
    return ' width="%d" height="%d"' % (round(float(m.group(1)) * 2), round(float(m.group(2)) * 2)) if m else ""


def lastmod_of(text, path, day):
    mt = re.search(r"<url><loc>" + re.escape(BASE + path) + r"</loc>.*?<lastmod>([0-9-]{10})</lastmod>", text)
    return max(day, mt.group(1)) if mt else day


# ------------------------------------------------------------------ 文（決まった型・数字は入力のまま）
def _span(m):
    return datetime.date.fromisoformat(m["from"]), datetime.date.fromisoformat(m["to"])


def per_ja(m, year=False):
    """期間（受渡日）: 11月1日〜23日。year=True は 2026年11月1日〜23日。"""
    a, b = _span(m)
    s = "%d月%d日" % (a.month, a.day) + ("" if a == b else "〜%s%d日" % ("" if a.month == b.month else "%d月" % b.month, b.day))
    return ("%d年" % a.year if year else "") + s


def per_en(m, year=False):
    """Nov 1–23。year=True は Nov 1–23, 2026。"""
    a, b = _span(m)
    s = md_en(m["from"]) if a == b else "%s–%s" % (md_en(m["from"]), b.day if a.month == b.month else md_en(m["to"]))
    return s + (", %d" % b.year if year else "")


def week_of(d):
    """最新の、7日そろった月曜〜日曜の週（bin/press_release.py が速報の本を出す週を決める印に使う）。頁には出さない。"""
    ws = d.get("weeks") or []
    return ws[0] if ws else None


def month_moves(d, lang):
    """今月の動き3つ（当月1日〜最新の受渡日・前月の全日との比べ）。需給調整市場が先。"""
    j, e = d["jepx"], d["eprx"]
    er = {r["code"]: r for r in e["mtd"]["rows"]}
    pr = {r["code"]: r for r in ((e.get("prev") or {}).get("rows") or [])}
    ja, pa = j["mtd"]["areas"], (j.get("prev") or {}).get("areas") or {}
    epm, jpm = (e.get("prev") or {}).get("month") or "", (j.get("prev") or {}).get("month") or ""
    full = lambda r: bool(r) and r.get("ratio") is not None and r.get("price") is not None  # noqa: E731  前月の値がそろっている時だけ前月の句を出す
    p10, p32 = full(pr.get("1-0")), (pr.get("3-2") or {}).get("price") is not None
    pok = all((pa.get(a) or {}).get(k) is not None for a, k in (("システム", "avg"), ("東京", "s4"), ("九州", "s4")))
    many = j["mtd"]["days"] > 1
    out = []
    if lang == "ja":
        s = "需給調整市場（EPRX）では、%sの一次調整力（オンライン）の応札倍率は%s、平均落札価格は%s円/kW・30分でした（速報値）。" % (
            per_ja(e["mtd"]), f(er["1-0"]["ratio"], 1, "%"), f(er["1-0"]["price"]))
        if p10 and epm:
            s += "前月（%s・全日）は%s、%s円でした。" % (mon_ja(epm), f(pr["1-0"]["ratio"], 1, "%"), f(pr["1-0"]["price"]))
        out.append(s)
        out.append("三次調整力②の平均落札価格は%s円/kW・30分でした" % f(er["3-2"]["price"]) + ("（前月は%s円）。" % f(pr["3-2"]["price"]) if p32 else "。"))
        s = "卸電気（JEPX）では、%sのシステムプライス（全国）の平均は%s円/kWh、4時間の値差%sは東京で%s円、九州で%s円でした" % (
            per_ja(j["mtd"]), f(ja["システム"]["avg"]), "（日ごとの差の平均）" if many else "", f(ja["東京"]["s4"]), f(ja["九州"]["s4"]))
        out.append(s + ("（前月（%s・全日）は%s円、%s円、%s円）。" % (mon_ja(jpm), f(pa["システム"]["avg"]), f(pa["東京"]["s4"]), f(pa["九州"]["s4"])) if pok and jpm else "。"))
    else:
        s = "In the EPRX balancing market, primary reserve (online) had a bid ratio of %s and an average winning price of %s yen/kW per 30 min for %s (preliminary)." % (
            f(er["1-0"]["ratio"], 1, "%"), f(er["1-0"]["price"]), per_en(e["mtd"]))
        if p10 and epm:
            s += " Last month (%s, all days): %s and %s yen." % (mon_en(epm), f(pr["1-0"]["ratio"], 1, "%"), f(pr["1-0"]["price"]))
        out.append(s)
        out.append("Tertiary reserve 2 had an average winning price of %s yen/kW per 30 min" % f(er["3-2"]["price"]) + (" (last month: %s yen)." % f(pr["3-2"]["price"]) if p32 else "."))
        s = "On JEPX, the system price averaged %s yen/kWh for %s; the 4-hour spread%s was %s yen in Tokyo and %s yen in Kyushu" % (
            f(ja["システム"]["avg"]), per_en(j["mtd"]), " (average of daily spreads)" if many else "", f(ja["東京"]["s4"]), f(ja["九州"]["s4"]))
        out.append(s + (" (last month, %s, all days: %s, %s and %s yen)." % (mon_en(jpm), f(pa["システム"]["avg"]), f(pa["東京"]["s4"]), f(pa["九州"]["s4"])) if pok and jpm else "."))
    return out


# ------------------------------------------------------------------ 頁
def kpis(d, lang):
    """頭の数字（需給調整市場が先）。"""
    j, e = d["jepx"], d["eprx"]
    er = {r["code"]: r for r in e["mtd"]["rows"]}
    pr = {r["code"]: r for r in ((e.get("prev") or {}).get("rows") or [])}
    pa = (j.get("prev") or {}).get("areas") or {}
    J = lang == "ja"
    rows = [
        (f(er["1-0"]["ratio"], 1, "%"), "", "一次調整力（オンライン）の応札倍率・速報値" if J else "Primary reserve (online) bid ratio, preliminary",
         f((pr.get("1-0") or {}).get("ratio"), 1, "%")),
        (f(er["1-0"]["price"]), "円" if J else "yen", "一次調整力（オンライン）の平均落札価格（円/kW・30分）" if J else "Primary reserve (online) average winning price (yen/kW per 30 min)",
         f((pr.get("1-0") or {}).get("price"))),
        (f(er["3-2"]["price"]), "円" if J else "yen", "三次調整力②の平均落札価格（円/kW・30分）" if J else "Tertiary reserve 2 average winning price (yen/kW per 30 min)",
         f((pr.get("3-2") or {}).get("price"))),
        (f(j["mtd"]["areas"]["システム"]["avg"]), "円/kWh" if J else "yen/kWh", "卸電気 システムプライスの平均" if J else "JEPX system price, average",
         f((pa.get("システム") or {}).get("avg"))),
        (f(j["mtd"]["areas"]["東京"]["s4"]), "円/kWh" if J else "yen/kWh", "東京の4時間の値差" if J else "Tokyo 4-hour spread", f((pa.get("東京") or {}).get("s4"))),
        (f(j["mtd"]["areas"]["九州"]["s4"]), "円/kWh" if J else "yen/kWh", "九州の4時間の値差" if J else "Kyushu 4-hour spread", f((pa.get("九州") or {}).get("s4"))),
    ]
    # 今月の期間と前月の名前は、市場ごとに別に出す（月の変わり目は卸電気が翌日の受渡分で先に次の月へ進み、需給調整市場とずれる＝2026-11-23 別の目①）
    jm, em = j["mtd"], e["mtd"]
    jpm, epm = (j.get("prev") or {}).get("month") or "", (e.get("prev") or {}).get("month") or ""
    if J:
        jper, eper = "今月 %s" % per_ja(jm), "今月 %s" % per_ja(em)
        jpre, epre = "前月（%s・全日）" % mon_ja(jpm) if jpm else "前月", "前月（%s・全日）" % mon_ja(epm) if epm else "前月"
    else:
        jper, eper = per_en(jm), per_en(em)
        jpre, epre = "Last month (%s, all days)" % mon_en(jpm) if jpm else "Last month", "Last month (%s, all days)" % mon_en(epm) if epm else "Last month"
    per = [eper, eper, eper, jper, jper, jper]
    pre = [epre, epre, epre, jpre, jpre, jpre]
    out = '<div class="fl-kpi" id="kpi">' + "".join(("<div><b>%s<small>%s</small></b><span>%s（%s）</span><i>%s: %s</i></div>" if J else
                                                     "<div><b>%s<small>%s</small></b><span>%s (%s)</span><i>%s: %s</i></div>") % (
        esc(v), esc(u), esc(l), esc(per[i]), esc(pre[i]), esc(p)) for i, (v, u, l, p) in enumerate(rows)) + "</div>"
    note = ("応札倍率＝応札量÷募集量。4時間の値差＝その日の高い4時間と安い4時間の平均の差（円/kWh）。どちらも収益を示すものではありません。" if J else
            "Bid ratio = bids ÷ requirement. 4-hour spread = average of the day's 4 most expensive hours minus its 4 cheapest (yen/kWh). Neither is a revenue figure.")
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


def daily_table(d, lang):
    """当月1日からの日ごとの表（需給調整市場が先）。受渡日は両方の市場の日を合わせ、無い日は「—」。"""
    J = lang == "ja"
    j, e = d["jepx"], d["eprx"]
    em = {x["date"]: x["rows"] for x in e["daily"]}
    jm = {x["date"]: x["areas"] for x in (j.get("daily") or [])}
    days = sorted(set(em) | {x for x in jm if x >= j["mtd"]["from"]})
    head = (["受渡日", "一次調整力（オンライン）の応札倍率", "一次調整力（オンライン）の平均落札価格", "一次調整力（オフライン）の平均落札価格", "三次調整力②の平均落札価格",
             "システムプライスの平均（円/kWh）", "東京の4時間の値差（円/kWh）", "九州の4時間の値差（円/kWh）"] if J else
            ["Delivery day", "Primary (online) bid ratio", "Primary (online) avg. winning price", "Primary (offline) avg. winning price", "Tertiary 2 avg. winning price",
             "System price average (yen/kWh)", "Tokyo 4-hour spread (yen/kWh)", "Kyushu 4-hour spread (yen/kWh)"])
    rows = []
    for x in days:
        E, A = em.get(x) or {}, jm.get(x) or {}
        dd = datetime.date.fromisoformat(x)
        lab = "%d月%d日（%s）" % (dd.month, dd.day, WD_JA[dd.weekday()]) if J else "%s (%s)" % (md_en(x), dd.strftime("%a"))
        rows.append([lab, f((E.get("1-0") or {}).get("ratio"), 1, "%"), f((E.get("1-0") or {}).get("price")), f((E.get("1-1") or {}).get("price")), f((E.get("3-2") or {}).get("price")),
                     f((A.get("システム") or {}).get("avg")), f((A.get("東京") or {}).get("s4")), f((A.get("九州") or {}).get("s4"))])
    return table(head, rows)


def _best(pairs, hi=True):
    """(名前, 値) のうち値のある物の最大（hi=False は最小）。無ければ None。"""
    ps = [(k, v) for k, v in pairs if v is not None]
    return (max if hi else min)(ps, key=lambda t: t[1]) if ps else None


def _hm(k):
    return "%d:%02d" % (k // 2, 30 * (k % 2))


def fig_sections(d, lang, figs, ver):
    """図の節（①需給調整市場 → ②卸電気）。返り: [(id, 題, 中身の HTML)]。文は決まった型で、数字は入力のまま。"""
    J = lang == "ja"
    j, e = d["jepx"], d["eprx"]
    er = {r["code"]: r for r in e["mtd"]["rows"]}
    pr = {r["code"]: r for r in ((e.get("prev") or {}).get("rows") or [])}
    ed, D = e["daily"], e["detail"]
    jd = [x for x in (j.get("daily") or []) if x["date"] >= j["mtd"]["from"]]
    ja, pa = j["mtd"]["areas"], (j.get("prev") or {}).get("areas") or {}
    EP, JP = (per_ja(e["mtd"]), per_ja(j["mtd"])) if J else (per_en(e["mtd"]), per_en(j["mtd"]))
    EPY, JPY = (per_ja(e["mtd"], True), per_ja(j["mtd"], True)) if J else (per_en(e["mtd"], True), per_en(j["mtd"], True))
    pn = (lambda c: er[c]["name"]) if J else (lambda c: PROD_EN[c])
    an = (lambda a: AREA_JA.get(a, a)) if J else (lambda a: AREA_EN[a])
    dn = md_ja if J else md_en
    base = PATH if J else PATH_EN
    E1, E2 = ("①需給調整市場（EPRX）｜", "②卸電気（JEPX）｜") if J else ("① Balancing market (EPRX) | ", "② Wholesale electricity (JEPX) | ")
    src_e = ("出典: 電力需給調整力取引所（EPRX）公表の取引結果（速報値）。当社集計。" if J else "Source: EPRX trading results (preliminary), aggregated by ScienceX.")
    src_j = ("出典: JEPX スポット市場。当社集計。" if J else "Source: JEPX spot market, aggregated by ScienceX.")
    no = [0]

    def fig(name, cap):
        no[0] += 1
        lab = ("図%d　%s" if J else "Figure %d  %s") % (no[0], cap)
        return '<figure class="rp-fig"><img src="%s/%s.svg?v=%s"%s alt="%s" loading="lazy"><figcaption>%s</figcaption></figure>' % (
            base, name, ver, svg_dims(figs[(lang, name)]), esc(lab), esc(lab))

    def body(lead, fact, name, cap, src):
        return "<p>%s</p>\n%s%s\n<p class=\"md-note\">%s</p>" % (esc(lead), ("<p>%s</p>\n" % esc(fact)) if fact else "", fig(name, cap), esc(src))

    out = []
    # ---- 図1 一次調整力の応札倍率と値段（日ごと）
    n_all = len(ed)
    over = lambda c: sum(1 for x in ed if ((x["rows"].get(c) or {}).get("ratio") or 0) >= 100)  # noqa: E731
    p10 = pr.get("1-0") or {}
    if p10.get("ratio") is None or p10.get("price") is None:
        p10 = {}
    off = er["1-1"]["ratio"] is not None and er["1-1"]["price"] is not None
    many_e, many_j = n_all > 1, len(jd) > 1
    if J:
        lead = ("一次調整力は、周波数の変化を受けてすぐに出力を変える、いちばん速い商品で、蓄電池がよく使われます。左がオンライン、右がオフラインの枠です。"
                "棒は日ごとの応札倍率（応札した量÷送配電会社が募集した量）で、金の棒は100%以上の日（募集と同じか、それより多くの札が集まった日）です。線は日ごとの平均落札価格です。")
        fact = "%sの一次調整力（オンライン）の応札倍率は%s%s、平均落札価格は%s円/kW・30分%sでした。" % (
            EP, f(er["1-0"]["ratio"], 1, "%"), "（前月の全日は%s）" % f(p10.get("ratio"), 1, "%") if p10 else "", f(er["1-0"]["price"]),
            "（前月は%s円）" % f(p10.get("price")) if p10 else "")
        if many_e:
            fact += "応札倍率が100%%以上の日は%d日のうち%d日でした。" % (n_all, over("1-0"))
        if off:
            fact += "一次調整力（オフライン）は応札倍率%s、平均落札価格%s円%s。" % (f(er["1-1"]["ratio"], 1, "%"), f(er["1-1"]["price"]),
                                                                   "で、100%%以上の日は%d日でした" % over("1-1") if many_e else "でした")
        cap = "一次調整力の応札倍率（棒）と平均落札価格（線）（%s・日ごと。左がオンライン、右がオフライン。金の棒は応札倍率が100%%以上の日）" % EPY
        ttl = "一次調整力の応札倍率と値段（1日から毎日）"
    else:
        lead = ("Primary reserve is the fastest product, responding to frequency changes within seconds, and batteries are widely used for it. Online is on the left, offline on the right. "
                "Bars show the daily bid ratio (bids ÷ the volume requested by grid operators); gold bars are days at 100% or higher. The line is the daily average winning price.")
        fact = "For %s, primary reserve (online) had a bid ratio of %s%s and an average winning price of %s yen/kW per 30 min%s." % (
            EP, f(er["1-0"]["ratio"], 1, "%"), " (last month, all days: %s)" % f(p10.get("ratio"), 1, "%") if p10 else "", f(er["1-0"]["price"]),
            " (last month: %s yen)" % f(p10.get("price")) if p10 else "")
        if many_e:
            fact += " The bid ratio was 100%% or higher on %d of %d days." % (over("1-0"), n_all)
        if off:
            fact += " Primary reserve (offline): bid ratio %s, average winning price %s yen%s." % (f(er["1-1"]["ratio"], 1, "%"), f(er["1-1"]["price"]),
                                                                                              ", 100%% or higher on %d days" % over("1-1") if many_e else "")
        cap = "Bid ratio (bars) and average winning price (line) for primary reserve (%s, daily; online on the left, offline on the right; gold bars are days with a bid ratio of 100%% or higher)" % EPY
        ttl = "Primary reserve: bid ratio and price, every day from the 1st"
    out.append(("e1", E1 + ttl, body(lead, fact, "e1", cap, src_e)))
    # ---- 図2 商品ごとの値段（日ごと）
    top = {c: _best([(x["date"], (x["rows"].get(c) or {}).get("price")) for x in ed]) for c in ("3-2", "1-0")}
    if J:
        lead = "7つの商品の平均落札価格（落札量で重みを付けた平均・円/kW・30分）を、日ごとに並べました。太い線は一次調整力（オンライン・オフライン）と三次調整力②です。"
        fact = ("%sで日ごとの平均がいちばん高かったのは、三次調整力②が%sの%s円、一次調整力（オンライン）が%sの%s円でした。" % (
            EP, dn(top["3-2"][0]), f(top["3-2"][1]), dn(top["1-0"][0]), f(top["1-0"][1]))) if top["3-2"] and top["1-0"] and many_e else ""
        cap, ttl = "需給調整市場の商品ごとの平均落札価格（円/kW・30分・%s・日ごと）" % EPY, "商品ごとの値段（1日から毎日）"
    else:
        lead = "Average winning prices (weighted by awarded volume, yen/kW per 30 min) for the seven products, by day. Thick lines are primary reserve (online and offline) and tertiary reserve 2."
        fact = ("For %s, the highest daily average was %s yen on %s for tertiary reserve 2 and %s yen on %s for primary reserve (online)." % (
            EP, f(top["3-2"][1]), dn(top["3-2"][0]), f(top["1-0"][1]), dn(top["1-0"][0]))) if top["3-2"] and top["1-0"] and many_e else ""
        cap, ttl = "Average winning price by product in the balancing market (yen/kW per 30 min, %s, daily)" % EPY, "Prices by product, every day from the 1st"
    out.append(("e2", E1 + ttl, body(lead, fact, "e2", cap, src_e)))
    # ---- 図3 商品ごとの応札倍率（日ごと）
    rs = [(pn(r["code"]), r["ratio"]) for r in e["mtd"]["rows"] if r["ratio"] is not None]
    if J:
        lead = ("応札倍率（応札した量÷募集した量）を、商品ごとに日ごとに並べました。破線の100%より上は、募集より多くの札が集まった日です。"
                "100%未満でも、落札されない札はあります。棒や線は、応札が増えても、募集が減っても高くなります。")
        fact = "%sの応札倍率は、%sでした。" % (EP, "、".join("%sが%s" % (n, f(v, 1, "%")) for n, v in rs))
        cap, ttl = "需給調整市場の商品ごとの応札倍率（応札 ÷ 募集・%s・日ごと。破線は100%%）" % EPY, "商品ごとの応札倍率（1日から毎日）"
    else:
        lead = ("Bid ratios (bids ÷ requested volume) by product, by day. Above the dashed 100% line, more was bid than requested. Bids can still lose below 100%. "
                "The ratio rises when bids grow and also when the requested volume shrinks.")
        fact = "Bid ratios for %s: %s." % (EP, ", ".join("%s %s" % (n, f(v, 1, "%")) for n, v in rs))
        cap, ttl = "Bid ratio by product in the balancing market (bids ÷ requirement, %s, daily; dashed line = 100%%)" % EPY, "Bid ratios by product, every day from the 1st"
    out.append(("e3", E1 + ttl, body(lead, fact, "e3", cap, src_e)))
    # ---- 図4 時間帯（今月ここまで）
    hb = {c: _best(list(enumerate((D.get("hourly") or {}).get(c) or []))) for c in ("1-0", "3-2")}
    if J:
        lead = "今月ここまでの平均落札価格を、1日の時刻ごとに並べました（1時間ごと・落札量で重みを付けた平均）。"
        fact = ("%sの平均落札価格がいちばん高い時刻は、一次調整力（オンライン）が%d時台の%s円、三次調整力②が%d時台の%s円でした。" % (
            EP, hb["1-0"][0], f(hb["1-0"][1]), hb["3-2"][0], f(hb["3-2"][1]))) if hb["1-0"] and hb["3-2"] else ""
        cap, ttl = "需給調整市場の時間帯ごとの平均落札価格（%s・円/kW・30分）" % EPY, "1日のどの時間が高いか（今月ここまで）"
    else:
        lead = "Average winning prices for the month so far, by hour of day (hourly, weighted by awarded volume)."
        fact = ("For %s, the highest hourly average was %s yen in the %d:00 hour for primary reserve (online) and %s yen in the %d:00 hour for tertiary reserve 2." % (
            EP, f(hb["1-0"][1]), hb["1-0"][0], f(hb["3-2"][1]), hb["3-2"][0])) if hb["1-0"] and hb["3-2"] else ""
        cap, ttl = "Average winning price by hour of day in the balancing market (%s, yen/kW per 30 min)" % EPY, "Which hours of the day are expensive (month so far)"
    out.append(("e4", E1 + ttl, body(lead, fact, "e4", cap, src_e)))
    # ---- 図5 エリアごとの幅（今月ここまで）
    ba = (D.get("by_area") or {}).get("1-0") or {}
    hi, lo = _best([(a, v.get("avg_price")) for a, v in ba.items()]), _best([(a, v.get("avg_price")) for a, v in ba.items()], False)
    if J:
        lead = ("商品ごとに、電源のあるエリア別の落札価格の幅を並べました。細い線はこの期間でいちばん安い札からいちばん高い札まで、太い帯は10コマのうち8コマが入る幅、"
                "点は落札量で重みを付けた平均です。三次調整力②は値段の桁が違うので、目盛りを別にしています。")
        fact = ("%sの一次調整力（オンライン）の平均落札価格は、いちばん高い%sが%s円、いちばん低い%sが%s円でした（円/kW・30分）。" % (EP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))) if hi and lo else ""
        cap, ttl = "需給調整市場のエリアごとの落札価格の幅と平均（%s・電源のあるエリア別）" % EPY, "エリアごとの値段の幅（今月ここまで）"
    else:
        lead = ("The range of winning prices by product and by area where the power source is. The thin line runs from the lowest to the highest winning bid in the period, "
                "the thick band holds 8 in 10 slots, and the dot is the average weighted by awarded volume. Tertiary reserve 2 uses its own scale.")
        fact = ("For %s, the average winning price for primary reserve (online) was highest in %s (%s yen) and lowest in %s (%s yen), in yen/kW per 30 min." % (
            EP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))) if hi and lo else ""
        cap, ttl = "Range and average of winning prices by area in the balancing market (%s, by area where the power source is)" % EPY, "Price ranges by area (month so far)"
    out.append(("e5", E1 + ttl, body(lead, fact, "e5", cap, src_e)))
    # ---- 図6 管区×時刻の約定率（今月ここまで）
    if J:
        lead = ("約定率（落札した量÷応札した量）を、管区（電源のあるエリア）ごとに時刻で並べました。100%%に近いほど、出した札がそのまま落ちています。"
                "色の帯は9時〜15時で、30分ごとに%d日分を合わせた量で割っています。" % (D.get("slot_days") or n_all))
        cap, ttl = "需給調整市場の約定率（管区（電源のあるエリア）×時刻・%s）" % EPY, "札が落ちやすい管区と時間（今月ここまで）"
    else:
        lead = ("Clearing rates (awarded ÷ bid) by time of day for each grid area (area where the power source is). The closer to 100%%, the more of the bids won. "
                "The shaded band is 9:00 to 15:00; each 30-minute slot adds up %d days." % (D.get("slot_days") or n_all))
        cap, ttl = "Clearing rate in the balancing market (grid area (area where the power source is) × time of day, %s)" % EPY, "Grid areas and times where bids win more easily (month so far)"
    out.append(("e6", E1 + ttl, body(lead, "", "e6", cap, src_e)))
    # ---- 図7 卸電気の日ごとの平均
    sysd = [(x["date"], x["areas"]["システム"]["avg"]) for x in jd]
    hi, lo = _best(sysd), _best(sysd, False)
    psys = (pa.get("システム") or {}).get("avg")
    if J:
        lead = "卸電気（スポット市場）の30分コマの値段を、日ごとに平均しました。破線がシステムプライス（全国）、色の線が北海道・東京・関西・九州です。"
        fact = "%sのシステムプライス（全国）の平均は%s円/kWh%sでした。" % (JP, f(ja["システム"]["avg"]), "（前月の全日は%s円）" % f(psys) if psys is not None else "")
        if hi and lo and len(sysd) > 1:
            fact += "日ごとの平均がいちばん高かったのは%sの%s円、いちばん安かったのは%sの%s円でした。" % (dn(hi[0]), f(hi[1]), dn(lo[0]), f(lo[1]))
        cap, ttl = "卸電気の日ごとの平均価格（円/kWh・%s）" % JPY, "平均の値段（1日から毎日）"
    else:
        lead = "Half-hourly JEPX spot prices averaged by day. The dashed line is the system price (Japan); coloured lines are Hokkaido, Tokyo, Kansai and Kyushu."
        fact = "For %s, the system price averaged %s yen/kWh%s." % (JP, f(ja["システム"]["avg"]), " (last month, all days: %s yen)" % f(psys) if psys is not None else "")
        if hi and lo and len(sysd) > 1:
            fact += " The highest daily average was %s yen on %s and the lowest %s yen on %s." % (f(hi[1]), dn(hi[0]), f(lo[1]), dn(lo[0]))
        cap, ttl = "Daily average JEPX price (yen/kWh, %s)" % JPY, "Average price, every day from the 1st"
    out.append(("j1", E2 + ttl, body(lead, fact, "j1", cap, src_j)))
    # ---- 図8 日ごとの4時間の値差
    big = [(a, sum(1 for x in jd if (x["areas"][a]["s4"] or 0) >= SPREAD_BIG)) for a in FOUR]
    if J:
        lead = "その日の高い4時間の平均から安い4時間の平均を引いた差（4時間の値差）を、日ごとに並べました。差が大きい日ほど、蓄電池が値差で稼げる余地が大きくなります。"
        fact = ("%s（%d日分）のうち、4時間の値差が10円以上の日は、%sでした。" % (JP, len(jd), "、".join("%sが%d日" % (an(a), n) for a, n in big)) if many_j else
                "%sの4時間の値差は、%sでした。" % (JP, "、".join("%sが%s円/kWh" % (an(a), f(ja[a]["s4"])) for a in FOUR)))
        cap, ttl = "卸電気の日ごとの値差（その日の高い4時間の平均 − 安い4時間の平均・円/kWh・%s）" % JPY, "値差は毎日ある"
    else:
        lead = "The daily 4-hour spread: the average of the day's 4 most expensive hours minus the average of its 4 cheapest. The wider the spread, the more room a battery has to earn from it."
        fact = ("Over the %d days of %s, the 4-hour spread was 10 yen or more on %s." % (len(jd), JP, ", ".join("%d days in %s" % (n, an(a)) for a, n in big)) if many_j else
                "On %s, the 4-hour spread was %s." % (JP, ", ".join("%s yen/kWh in %s" % (f(ja[a]["s4"]), an(a)) for a in FOUR)))
        cap, ttl = "Daily JEPX spread (average of the day's top 4 hours minus bottom 4 hours, yen/kWh, %s)" % JPY, "There is a price gap every day"
    out.append(("j2", E2 + ttl, body(lead, fact, "j2", cap, src_j)))
    # ---- 図9 エリアごとの平均（今月ここまでと前月）
    av = [(a, ja[a]["avg"]) for a in AREAS if a != "システム"]
    hi, lo = _best(av), _best(av, False)
    jpm = (j.get("prev") or {}).get("month") or ""
    if J:
        lead = "システムプライス（全国）と9エリアの平均の値段を、今月ここまで（紺）と前月の全日（灰）で並べました。"
        fact = "%sの平均が9エリアでいちばん高いのは%sの%s円/kWh、いちばん安いのは%sの%s円/kWhでした。" % (JP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))
        cap, ttl = "卸電気の平均価格（円/kWh）。紺が%s、灰が%s（全日）" % (JPY, mon_ja(jpm) if jpm else "前月"), "エリアごとの平均の値段（今月ここまでと前月）"
    else:
        lead = "Average prices for the system price (Japan) and the 9 areas: this month so far (navy) and last month, all days (grey)."
        fact = "For %s, among the 9 areas the average was highest in %s (%s yen/kWh) and lowest in %s (%s yen/kWh)." % (JP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))
        cap, ttl = "Average JEPX price (yen/kWh). Navy is %s; grey is %s (all days)" % (JPY, mon_en(jpm) if jpm else "last month"), "Average price by area (month so far and last month)"
    out.append(("j3", E2 + ttl, body(lead, fact, "j3", cap, src_j)))
    # ---- 図10 1日の形（今月ここまで）
    cv = list(enumerate((j["mtd"].get("curve") or {}).get("東京") or []))
    hi, lo = _best(cv), _best(cv, False)
    if J:
        lead = "今月ここまでの値段を、1日の時刻ごとに平均しました。安い時間にためて、高い時間に出すのが、蓄電池の値差の使い方です。"
        fact = ("%sの東京では、いちばん安いのは%sからの30分（%s円/kWh）、いちばん高いのは%sからの30分（%s円/kWh）でした。" % (JP, _hm(lo[0]), f(lo[1]), _hm(hi[0]), f(hi[1]))) if hi and lo else ""
        cap, ttl = "卸電気の1日の価格の山と谷（%s の平均・円/kWh）" % JPY, "値段は1日のなかでこう動く"
    else:
        lead = "Prices for the month so far, averaged by time of day. A battery uses the gap by charging in cheap hours and discharging in expensive ones."
        fact = ("In Tokyo for %s, the cheapest half hour starts at %s (%s yen/kWh) and the most expensive at %s (%s yen/kWh)." % (JP, _hm(lo[0]), f(lo[1]), _hm(hi[0]), f(hi[1]))) if hi and lo else ""
        cap, ttl = "Daily peaks and troughs of the JEPX price (average for %s, yen/kWh)" % JPY, "How the price moves through the day"
    out.append(("j4", E2 + ttl, body(lead, fact, "j4", cap, src_j)))
    # ---- 図11 エリアごとの値差（今月ここまで）
    sp = [(a, ja[a]["s4"]) for a in AREAS if a != "システム"]
    hi, lo = _best(sp), _best(sp, False)
    if J:
        lead = ("4時間の値差（高い4時間の平均 − 安い4時間の平均）の、今月ここまでの平均を、エリアごとに並べました。安い時間と高い時間の順番、充放電で失う電気、"
                "手数料・税・託送の費用は見ていません（収益を示すものではありません）。")
        fact = "%sの4時間の値差が9エリアでいちばん大きいのは%sの%s円/kWh、いちばん小さいのは%sの%s円/kWhでした。" % (JP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))
        cap, ttl = "卸電気の値差: 高い4時間の平均 − 安い4時間の平均（%s・円/kWh・日ごとの差の平均）" % JPY, "値差は1kWh あたりいくらか"
    else:
        lead = ("The 4-hour spread (average of the top 4 hours minus the bottom 4 hours), averaged over the month so far, by area. It ignores the order of cheap and expensive hours, "
                "round-trip losses, fees, taxes and network charges, and is not a revenue figure.")
        fact = "For %s, among the 9 areas the 4-hour spread was largest in %s (%s yen/kWh) and smallest in %s (%s yen/kWh)." % (JP, an(hi[0]), f(hi[1]), an(lo[0]), f(lo[1]))
        cap, ttl = "JEPX spread: average of top 4 hours minus bottom 4 hours (%s, yen/kWh, average of daily spreads)" % JPY, "How large the price gap is per kWh"
    out.append(("j5", E2 + ttl, body(lead, fact, "j5", cap, src_j)))
    assert no[0] == len(FIG_NAMES) and [x[0] for x in out] == FIG_NAMES
    return out


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
    start = min((j.get("prev") or {}).get("month", j["mtd"]["from"][:7]) + "-01", e["mtd"]["from"])
    end = max(j["latest_day"], e["latest_day"])
    org, pub = (bmd.ORG, brp.PUBLISHER) if J else (brp.EN_ORG, brp.EN_PUBLISHER)
    csv = "%s/%s/jepx-daily.csv" % (BASE, path.strip("/"))
    page = {"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path, "name": title, "description": desc,
            "inLanguage": lang, "publisher": pub, "datePublished": FIRST, "dateModified": modified,
            "isPartOf": {"@type": "CollectionPage", "url": BASE + ("/report" if J else "/en/report")}}
    ds = {"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset", "url": BASE + path,
          "name": (NAME + "の数字") if J else (NAME_EN + ": figures"),
          "description": ("卸電気（JEPX スポット市場）の10エリアの平均価格と4時間の値差、需給調整市場（EPRX）の7商品の応札倍率・平均落札価格（速報値）を、"
                          "公表データから毎日取り直して当社が集計した数字。当月1日からの日ごと・今月ここまで・最新の1日・前月（全日）。") if J else
                         ("Average prices and 4-hour spreads for the 10 JEPX spot areas, and bid ratios and average winning prices for the 7 EPRX "
                          "balancing products (preliminary), re-fetched from published data every day and aggregated by ScienceX: every day from the 1st of the month, the month so far, the latest day and last month."),
          "inLanguage": lang, "creator": org, "publisher": pub, "isAccessibleForFree": True, "dateModified": modified,
          "temporalCoverage": "%s/%s" % (start, end), "spatialCoverage": {"@type": "Place", "name": "日本" if J else "Japan"},
          "creditText": ("出典: サイエンスエックス株式会社『%s』%s%s" % (NAME, BASE, path)) if J else ("Source: Science X Inc., “%s”, %s%s" % (NAME_EN, BASE, path)),
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": csv,
                            "name": "卸電気（JEPX）の日ごとの平均と4時間の値差（CSV）" if J else "JEPX daily averages and 4-hour spreads (CSV)"}],
          "mainEntityOfPage": BASE + path}
    cr = bmd.crumbs([("ホーム", BASE + "/"), ("市場ノート", BASE + "/report"), ("速報", BASE + path)] if J else
                    [("Home", BASE + "/en"), ("Market Notes", BASE + "/en/report"), ("Daily Flash", BASE + path)])
    return "\n".join(bmd.ld(x) for x in (page, ds, cr))


def render(d, lang, modified, latest_issue, figs):
    J = lang == "ja"
    j, e = d["jepx"], d["eprx"]
    moves = month_moves(d, lang)
    ver = j["latest_day"].replace("-", "") + e["latest_day"][8:]        # 図の住所に付ける版（データの日付が変わると変わる＝古い図を読ませない）
    if J:
        title = "市場ノート 速報｜需給調整市場・卸電気を毎日更新｜サイエンスエックス"
        desc = ("需給調整市場（EPRX）と卸電気（JEPX）の最新の数字を、公表データを毎朝取り直して出す速報。今月1日からの毎日の動きを月号と同じ図で、"
                "7商品の応札倍率と平均落札価格、システムプライスと9エリアの平均価格と4時間の値差を、今月ここまで・最新の1日・前月（全日）の表で比べます。出典つき、CSV あり。")   # 日付は頁の頭と dateModified に（説明は毎日変えない＝llms.txt を日ごとに古くしない）
        crumbs = bmd.nav_crumbs([("ホーム", "/"), ("市場ノート", "/report"), ("速報", PATH)])
        issue = ('<a class="btn-primary" href="/report/%s">最新の月号を読む（%s号＝%sの数字）</a>' % (latest_issue, mon_ja(latest_issue), mon_ja(issue_data_month(latest_issue)))) if latest_issue else ""
        hero = f"""<section class="hero"><div class="container">
  <div class="section-label">毎日更新（速報）</div>
  <h1>{esc(NAME)}</h1>
  <p class="fl-pair"><b>速報</b>＝今月1日からの毎日の動き（この頁・毎朝更新）。<b>月号</b>＝毎月1日に出す、前月まるごとの図と表。</p>
  <div class="fl-asof"><div class="h">データの時点（{esc(d_ja(d['made_on']))}の朝に公表データを取り直し）</div><b>需給調整市場（EPRX）: {esc(d_ja(e['latest_day'], True))}分まで（速報値）</b><b>卸電気（JEPX）: {esc(d_ja(j['latest_day'], True))}分まで</b><span>日付は電気を受け渡す日（受渡日）です。卸電気は前日に売買が決まるので、翌日分まで入ることがあります。</span></div>
  <p>需給調整市場（EPRX）と卸電気（JEPX）の、今月1日からの毎日の動きを、月号と同じ図と並びで出しています。数字は、公表された最新のデータから毎朝作り直します。</p>
  <p class="fl-two">{issue}<a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/report">月号の一覧</a></p>
</div></section>"""
        same = e["month"] == j["month"]
        m_h = "今月の動き3つ（%s）" % (mon_ja(e["month"]) if same else "需給調整市場は%s・卸電気は%s" % (mon_ja(e["month"]), mon_ja(j["month"])))
        m_lead = ("%sからの動きを、需給調整市場（EPRX）と卸電気（JEPX）の数字から3つにまとめました。" % d_ja(e["mtd"]["from"]) if same else
                  "月の変わり目のため、需給調整市場（EPRX）は%sから、卸電気（JEPX）は%sからの数字です。" % (d_ja(e["mtd"]["from"]), d_ja(j["mtd"]["from"]))) + \
            "図は、月号と同じ順（需給調整市場が先）で下に並べています。"
        s2h, s3h, s4h, s5h = ("①需給調整市場（EPRX）｜商品ごとの数字（今月ここまで・最新の1日・前月）", "②卸電気（JEPX）｜エリアごとの数字（今月ここまで・最新の1日・前月）",
                              "日ごとの数字（1日から・資料にそのまま使える表）", "データの時点と出典")
        d_lead = "図の元の数字を、受渡日ごとに並べました。需給調整市場は速報値です。「—」は、まだ公表されていない日です。"
        e_note = ("応札倍率＝応札量÷募集量、平均落札価格＝落札量で重みを付けた平均（円/kW・30分）。全国の値（公表ファイルの合計の列）。今月の数字は月の途中の速報値で、"
                  "月が終わると変わります。月が終わってから公表される確報値とは少し違うことがあります。出典: 電力需給調整力取引所（EPRX）公表の取引結果（速報値）。当社集計。")
        j_note = ("平均は30分コマの単純平均。4時間の値差は、その日の高い8コマ（4時間）の平均から安い8コマの平均を引いた差の、日ごとの平均です（安い時間と高い時間の順番、"
                  "充放電で失う電気、手数料・税・託送の費用は見ていません。収益を示すものではありません）。出典: 日本卸電力取引所（JEPX）公表のスポット市場の取引結果。当社集計。")
        csvl = '<p class="md-note">卸電気の日ごとの数字（今月と前月・10エリア）: <a href="/report/flash/jepx-daily.csv" download>CSV（日ごとの平均と4時間の値差）</a></p>'
        asof_head = ["出所", "対象の期間", "種類", "取り直した日"]
        notes = ["数字は出典の公表値から当社が機械で集計したもので、図も表も毎朝作り直します。取り直せなかった日は、前の日の版のまま（上の「データの時点」の日付も前のまま）です。",
                 "「速報値」は約定した直後に公表される値、「確報値」は月が終わってから公表される値です（約定のあとの追加調達や訂正を反映）。この頁の需給調整市場の数字は全部速報値です。",
                 "受渡日は電気を受け渡す日です。卸電気のスポット市場は前の日に取引するので、翌日の受渡分まで出ることがあります。",
                 "図の横軸は月の1日から月末までで、日が進むと右へ伸びます。月が替わると、次の月の1日から始め直します（前月まるごとの図と表は月号にあります）。"]
        more = ('<ul class="rp-list" style="margin-top:14px">'
                '<li><a class="t" href="/report">蓄電所の市場ノート（月号・毎月1日）</a><p>前月の全日の数字を、需給調整市場・卸電気・容量市場の順に図と表でまとめた号。PDF あり。</p></li>'
                '<li><a class="t" href="/report/data">市場データ（号をまたいだ推移・CSV）</a><p>卸電気のエリア別の月ごとの推移と容量市場のエリアプライス。</p></li>'
                '<li><a class="t" href="/market-data">系統用蓄電池の売り案件 市場データ</a><p>当社の蓄電所マーケットに載る売り案件の、管内別・電圧別などの集計（毎朝更新）。</p></li>'
                '</ul><p class="md-note" style="margin-top:12px">図表や数値は、出典を明記すればそのままお使いいただけます（<a href="/press">引用・転載ガイド</a>）。</p>')
        footer = bmd.FOOTER
    else:
        title = "Daily Flash: Japan EPRX and JEPX figures | ScienceX"
        desc = ("Japan's latest EPRX balancing and JEPX wholesale figures, re-fetched every morning: daily charts from the 1st of the month in the same format as the "
                "monthly issue, plus tables for the month so far, the latest day and last month.")
        crumbs = bmd.nav_crumbs([("Home", "/en"), ("Market Notes", "/en/report"), ("Daily Flash", PATH_EN)])
        issue = ('<a class="btn-primary" href="/en/report/%s">Read the latest monthly issue (%s issue, %s data)</a>' % (latest_issue, mon_en(latest_issue), mon_en(issue_data_month(latest_issue)))) if latest_issue else ""
        hero = f"""<section class="hero"><div class="container">
  <div class="section-label">Updated daily (flash)</div>
  <h1>{esc(NAME_EN)}</h1>
  <p class="fl-pair"><b>Daily Flash</b> = every day of this month from the 1st (this page, updated each morning). <b>Monthly issue</b> = the whole previous month in charts and tables, out on the 1st.</p>
  <div class="fl-asof"><div class="h">Data as of (re-fetched from published data on the morning of {esc(d_en(d['made_on']))})</div><b>EPRX balancing market: up to delivery on {esc(d_en(e['latest_day']))} (preliminary)</b><b>JEPX wholesale: up to delivery on {esc(d_en(j['latest_day']))}</b><span>Dates are delivery days (the day the power is delivered). JEPX trades the day before, so it can run one day ahead.</span></div>
  <p>Daily movements since the 1st of the month for two markets that pay battery storage sites in Japan, the EPRX balancing market and JEPX wholesale power, in the same charts and order as the monthly issue. Figures are rebuilt from the latest published data every morning.</p>
  <p class="fl-two">{issue}<a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/report">All monthly issues</a></p>
</div></section>"""
        same = e["month"] == j["month"]
        m_h = "Three things this month (%s)" % (mon_en(e["month"]) if same else "balancing market: %s; wholesale: %s" % (mon_en(e["month"]), mon_en(j["month"])))
        m_lead = ("Three points from the EPRX balancing market and JEPX wholesale figures since %s." % d_en(e["mtd"]["from"]) if same else
                  "At the turn of the month, EPRX balancing market figures run from %s and JEPX wholesale figures from %s." % (d_en(e["mtd"]["from"]), d_en(j["mtd"]["from"]))) + \
            " Charts follow below in the same order as the monthly issue (balancing market first)."
        s2h, s3h, s4h, s5h = ("① Balancing market (EPRX) | Figures by product (month so far, latest day, last month)", "② Wholesale electricity (JEPX) | Figures by area (month so far, latest day, last month)",
                              "Daily figures from the 1st (tables you can reuse)", "Data dates and sources")
        d_lead = "The numbers behind the charts, by delivery day. Balancing market figures are preliminary. A dash means the day has not been published yet."
        e_note = ("Bid ratio = bids / procurement; average winning price = weighted by awarded volume (yen/kW per 30 min). National totals. This month's figures are preliminary "
                  "and change after the month ends; final values published later can differ slightly. Source: EPRX trading results (preliminary), aggregated by ScienceX.")
        j_note = ("Averages are simple averages of half-hour slots. The 4-hour spread is the average of the 8 most expensive slots minus the average of the 8 cheapest, averaged over days "
                  "(it ignores slot order, losses, fees, taxes and network charges, and is not a revenue figure). Source: JEPX spot market results, aggregated by ScienceX.")
        csvl = '<p class="md-note">JEPX daily figures (this month and last month, 10 areas): <a href="/en/report/flash/jepx-daily.csv" download>CSV (daily averages and 4-hour spreads)</a></p>'
        asof_head = ["Source", "Period", "Type", "Fetched on"]
        notes = ["Figures are aggregated automatically by ScienceX from published data; charts and tables are rebuilt every morning. If a fetch fails, the previous day's version stays (and so do the dates at the top).",
                 "Preliminary values are published right after the auction; final values are published after the month ends (with later additional procurement and corrections). All balancing market figures here are preliminary.",
                 "Delivery day is the day electricity is delivered. JEPX spot trades the day before, so figures can run to the next day's delivery.",
                 "The horizontal axis of the daily charts runs from the 1st to the end of the month and fills in as days pass. When the month changes, the charts start again from the 1st (the whole previous month is in the monthly issue)."]
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
    fs = fig_sections(d, lang, figs, ver)
    parts = [("moves", m_h, "<p>%s</p>\n<ul class=\"rp-three\">%s</ul>\n%s" % (esc(m_lead), "".join("<li>%s</li>" % esc(m) for m in moves), kpis(d, lang)))]
    parts += [x for x in fs if x[0].startswith("e")]
    parts.append(("eprx", s2h, "%s\n%s\n<p class=\"md-note\">%s</p>" % (scroll, eprx_table(d, lang), esc(e_note))))
    parts += [x for x in fs if x[0].startswith("j")]
    parts.append(("jepx", s3h, "%s\n%s\n<p class=\"md-note\">%s</p>\n%s" % (scroll, jepx_table(d, lang), esc(j_note), csvl)))
    parts.append(("daily", s4h, "<p>%s</p>\n%s\n%s" % (esc(d_lead), scroll, daily_table(d, lang))))
    parts.append(("asof", s5h, "%s\n<ul>%s</ul>\n%s\n%s" % (table(asof_head, asof_rows(d, lang), 9), "".join("<li>%s</li>" % esc(n) for n in notes), more, mk)))
    sections = "\n".join('<section class="md" id="%s"><div class="container rp-body">\n<div class="section-label">%02d</div>\n<h2 class="md-h">%s</h2>\n%s\n</div></section>' % (
        sid, i, esc(h), inner) for i, (sid, h, inner) in enumerate(parts, 1))
    body = f"""{crumbs}
{hero}
{sections}
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
    return h.replace("</style>", CSS + "</style>", 1) + body, moves, week_of(d), core


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
    mo = lambda m: {"from": m["from"], "to": m["to"], "days": m["days"]}  # noqa: E731
    out = {"made_on": d["made_on"], "jepx_day": d["jepx"]["latest_day"], "eprx_day": d["eprx"]["latest_day"], "url": PATH, "title": NAME,
           "week": ({"start": w["start"], "end": w["end"], "key": w["end"], "eprx": bool(w.get("eprx"))} if w else None),   # 速報の本を出す週の印（頁には週の表を出さない）
           "month": {"eprx": mo(d["eprx"]["mtd"]), "jepx": mo(d["jepx"]["mtd"])},                                          # 今月の動きの期間（1日〜最新の受渡日）
           "moves": moves_ja, "figures": len(FIG_NAMES),
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


def safety(texts, rules=None):
    hits = []
    for t in texts:
        for rx, why in (rules or brp.FORBIDDEN):
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
    figs, ferr = load_figs(d)
    if not figs:
        print("NG " + ferr + "（何も書かない）")
        return 2
    dd = dict(d, made_on=modified)
    ja, mv_ja, w, core_ja = render(dd, "ja", modified, latest_issue, figs)
    en, mv_en, _, core_en = render(dd, "en", modified, latest_issue_en, figs)
    hits = safety([core_ja, json.dumps(d, ensure_ascii=False)]) + safety([core_en], brp.FORBIDDEN_EN)
    if hits:
        print("NG 公開してはいけない語がある。何も書かない: " + "／".join(hits))
        return 2
    files = {"report/flash/index.html": ja.encode("utf-8"), "en/report/flash/index.html": en.encode("utf-8"),
             "report/flash/latest.json": flash_json(dd, mv_ja, mv_en, w),
             "report/flash/jepx-daily.csv": csv_daily(d, "ja"), "en/report/flash/jepx-daily.csv": csv_daily(d, "en")}
    for (lang, n), b in figs.items():
        files["%sreport/flash/%s.svg" % ("" if lang == "ja" else "en/", n)] = b
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
