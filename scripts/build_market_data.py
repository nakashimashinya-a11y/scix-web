#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projects.json（公開セーフ項目だけ）から、市場データのページと管内別の案件一覧ページを焼き直す。

2026-10-29 新設。DR2 は限定公開情報なので、公開セーフ項目（管内・県・電圧・MW/MWh・
状態・取得の形・連系の見込み・掲載日）の集計だけで、他社に無い「売り案件の市場データ」を作る。価格・住所・売主は無い
（projects.json に入っていない）。

生成するもの（全文を書き直す。手で直さない。週次の検査は FORBIDDEN で触らない）:
  market-data.html            系統用蓄電池の売り案件 市場データ（当社観測）
  projects-<slug>.html ×9      管内別の案件一覧（東京・中部・九州・関西・中国・東北・北海道・北陸・四国）
                              件数が MIN_INDEX 未満の管内は noindex（薄いページを索引に出さない）
  en/projects.html           英語の案件一覧（海外の買い手向け・1枚・価格なし・2026-10-31 新設）
  en/market-data.html         英語の市場データ（日本語の /market-data と同じ集計・hreflang で相互に結ぶ・2026-11-22 新設）
  zh-market-data.html         中国語（簡体字）の市場データ（同じ集計・hreflang で3言語を相互に結ぶ・用語は docs/glossary-en-zh.md・CSV は英語版を指す・2026-11-23 新設）
  files/market-data/*.csv     集計の CSV（日英・UTF-8 BOM 付き・CRLF）: 集計・週ごとの推移・買主のリクエストの条件
  files/market-data/buyer-requests.json  買主のリクエスト（蓄電所マーケットの公開の口 /api/open/needs）の選択肢ごとの数の控え。
                              --fetch-needs のときだけ口を読み、数が変わったときだけ書き直す（件数と選択肢ごとの数だけ。
                              番号・載った日・買主の属性は持たない）。口が読めなければ前の控えのまま。

2026-11-22（中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」・Gemini の助言 指令2＝一次情報）:
  集計の節を3つ（電圧×取得の形・規模の区分・連系までの月数の取得の形別）、買主のリクエストの条件の集計、CSV、
  Dataset の variableMeasured・distribution、表の caption・th scope・time、「引用のしかた」、英語の /en/market-data、
  /en/projects の Dataset（件数の集計だけ）を足した。値のある件だけの集計は母数と欠けを併記し、件数の少ない区分は
  MIN_GROUP（買主のリクエストは NEEDS_MIN）未満を「その他」にまとめる。価格・単価・負担金の額・案件の番号・市区町村は出さない
  （CSV にも JSON-LD にも。O16-19・O16-20）。掲載の増え方は当社が一覧に載せた作業の波で、市場の伸びではないと注を付ける。

使い方:
    python3 scripts/build_market_data.py                  # 書き換えて差分を報告
    python3 scripts/build_market_data.py --check          # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
    python3 scripts/build_market_data.py --fetch-needs    # 買主のリクエストを公開の口から数え直してから焼く（毎朝の同期）
    python3 scripts/build_market_data.py --check --fetch-needs   # 口の今の数で、ずれているかだけ見る（控えは書かない）
毎朝の同期（scripts/sync_projects_json.sh）が inject_stats.py の直後に呼ぶ。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from inject_stats import BAND_EVERY, NEW_DAYS, _esc, cod_bucket, cod_sort_key, cod_text, is_new  # noqa: E402
from build_ga_tag import TAGS as GA_BLOCK  # noqa: E402  全頁と同じ GA の区画（本番以外・自動操作は送らない・社内の印）と LinkedIn のタグ（入力のフォームの無い頁）

BASE = "https://www.scix.co.jp"
MIN_INDEX = 5   # 管内の件数がこれ未満なら noindex
AREAS = [
    ("東京", "tokyo", "東京電力パワーグリッド"),
    ("中部", "chubu", "中部電力パワーグリッド"),
    ("九州", "kyushu", "九州電力送配電"),
    ("関西", "kansai", "関西電力送配電"),
    ("中国", "chugoku", "中国電力ネットワーク"),
    ("東北", "tohoku", "東北電力ネットワーク"),
    ("北海道", "hokkaido", "北海道電力ネットワーク"),
    ("北陸", "hokuriku", "北陸電力送配電"),
    ("四国", "shikoku", "四国電力送配電"),
]
OUTPUTS = ["market-data.html", "en/projects.html", "en/market-data.html", "zh-market-data.html"] + [f"projects-{slug}.html" for _, slug, _ in AREAS]

# 2026-11-22 足した集計・CSV・買主のリクエスト
MIN_GROUP = 5    # 新しい集計の区分（電圧・取得の形の行・月数の行・CSV の管内と都道府県）は、件数がこれ未満なら「その他」にまとめる
NEEDS_MIN = 3    # 買主のリクエストの選択肢は、数がこれ未満なら「その他の選択肢」にまとめる
CSV_DIR = "files/market-data"
CSV = {"summary": f"/{CSV_DIR}/market-data-summary.csv", "weekly": f"/{CSV_DIR}/market-data-weekly.csv",
       "needs": f"/{CSV_DIR}/buyer-requests-summary.csv"}
CSV_EN = {k: v.replace(".csv", "-en.csv") for k, v in CSV.items()}
NEEDS_JSON = f"{CSV_DIR}/buyer-requests.json"
NEEDS_API = "https://dealroom.scix.co.jp/api/open/needs"
NEEDS_PAGE = "https://dealroom.scix.co.jp/needs"
NEEDS_PAGE_EN = "https://dealroom.scix.co.jp/en/needs"
GROWTH_NOTE = "掲載の件数の増え方は、当社が一覧に載せた作業の波（まとめて載せた日がある）で、市場の伸びを表すものではありません。"
GROWTH_NOTE_EN = ("Growth in the number of listings reflects when we added projects to the list (some were added in batches), "
                  "not growth of the market.")


# ---------------------------------------------------------------- 集計
def fiscal_half(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    fy = y if m >= 4 else y - 1
    return f"{fy}年度{'上期' if 4 <= m <= 9 else '下期'}"


def stats(ps, today):
    today_ym = today.strftime("%Y-%m")
    mws = [p["mw"] for p in ps if isinstance(p.get("mw"), (int, float))]
    mwhs = [p["mwh"] for p in ps if isinstance(p.get("mwh"), (int, float))]
    lead = sorted(p["leadMonths"] for p in ps if isinstance(p.get("leadMonths"), (int, float)))
    ym = [p["codYm"] for p in ps if p.get("codYm") and p["codYm"] >= today_ym and not p.get("live")]
    half = Counter(fiscal_half(x) for x in ym)
    bands = Counter()
    for n in lead:
        bands["6か月以内" if n <= 6 else "7〜12か月" if n <= 12 else "13〜24か月" if n <= 24 else "25か月以上"] += 1
    fs = Counter((p.get("firstSeen") or "")[:7] for p in ps if p.get("firstSeen"))
    return {
        "n": len(ps),
        "mw": round(sum(mws)),
        "mwh": round(sum(mwhs)),
        "mw_median": (sorted(mws)[len(mws) // 2] if mws else None),
        "volt": Counter(p.get("voltage") for p in ps if p.get("voltage")),
        "area": Counter(p.get("area") for p in ps if p.get("area")),
        "area_mw": {a: round(sum(p["mw"] for p in ps if p.get("area") == a and isinstance(p.get("mw"), (int, float))))
                    for a in {p.get("area") for p in ps if p.get("area")}},
        "pref": Counter(p.get("pref") for p in ps if p.get("pref")),
        "scheme": Counter(p.get("scheme") or "確認中" for p in ps),
        "status": Counter(p.get("status") or "確認中" for p in ps),
        "live": sum(1 for p in ps if p.get("live")),
        "ym_known": len(ym), "half": half,
        "lead": lead, "lead_median": (lead[len(lead) // 2] if lead else None), "bands": bands,
        "basis": Counter(p.get("leadBasis") or "unspecified" for p in ps if isinstance(p.get("leadMonths"), (int, float))),
        "undecided": sum(1 for p in ps if not p.get("live") and not (p.get("codYm") and p["codYm"] >= today_ym)),
        "lead_only": sum(1 for p in ps if not p.get("live") and not (p.get("codYm") and p["codYm"] >= today_ym)
                         and isinstance(p.get("leadMonths"), (int, float))),
        "new14": sum(1 for p in ps if is_new(p, today)),
        "first_seen": sorted(fs.items())[-6:],
    }


# ---------------------------------------------------------------- 週ごとの推移（量）
# 公開一覧（projects.json）の git 履歴から、週の終わり時点で見えていた案件の数と MW を数える（公開と同じ物・価格や ID は持たない）。
# 2026-09-05 より前は一覧が止まっていた時期で実際の在庫と違うため、WEEKLY_FROM の週から。売却済み・外れた数は出さない（成約件数は書かない決まり O16-8・O16-7）。
WEEKLY_FROM = "2026-09-07"
WEEKLY_SHOW = 12   # 表と図に出す週の数（新しい方から）


MW_MISSING_MAX = 0.03   # 出力(MW)が空の案件の割合の上限


def _monday(d):
    return d - datetime.timedelta(days=d.weekday())


def _git_snapshots():
    """projects.json を変えた commit の [(JSTの日付, hash)] を古い順に。取れなければ None。"""
    try:
        out = subprocess.run(["git", "-C", ROOT, "log", "HEAD", "--format=%H %cI", "--", "projects.json"],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return None
        jst = datetime.timezone(datetime.timedelta(hours=9))
        rows = []
        for ln in out.stdout.splitlines():
            h, iso = ln.split(" ", 1)
            rows.append((datetime.datetime.fromisoformat(iso).astimezone(jst).date(), h))
        return sorted(rows, key=lambda x: x[0])
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _git_projects(h):
    out = subprocess.run(["git", "-C", ROOT, "show", f"{h}:projects.json"], capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout).get("projects", [])


def _week_row(week, ps):
    mw = sum(p["mw"] for p in ps if isinstance(p.get("mw"), (int, float)))
    sc = Counter(p.get("scheme") for p in ps)
    vo = Counter(p.get("voltage") for p in ps)
    n = len(ps)
    mw_missing = sum(1 for p in ps if not isinstance(p.get("mw"), (int, float)))
    hv, ehv = vo.get("高圧", 0), vo.get("特別高圧", 0)
    # 出力(MW)が空の案件が週の件数の MW_MISSING_MAX を超える週は、合計 MW が実在庫の増減でなく欠けの影響になるので出さない
    return {"week": week.isoformat(), "n": n, "mw": round(mw), "hv": hv, "ehv": ehv,
            "rights": sc.get("権利譲渡", 0), "built": sc.get("完成渡し", 0),
            "mw_missing": mw_missing, "mw_ok": bool(n) and mw_missing / n <= MW_MISSING_MAX,
            "other_v": n - hv - ehv}


def weekly_series(ps_now, today, hist=None, load=None):
    """[{week(月曜), n, mw, hv, ehv, rights, built, new}] を古い順に（WEEKLY_FROM から今週まで・最後の WEEKLY_SHOW 週）。
    今週は渡された ps_now（いまの projects.json）の数。過去の週は、その週の日曜までの最後の commit の一覧。
    履歴が取れない・足りないときは空（節を出さない）。hist/load は試験用の差し替え。"""
    hist = _git_snapshots() if hist is None else hist
    load = load or _git_projects
    if not hist:
        return []
    start = max(_monday(hist[0][0]), datetime.date.fromisoformat(WEEKLY_FROM))
    this = _monday(today)
    snaps, rows, first, mw_of = {}, [], {}, {}
    w = start
    while w <= this:
        end = w + datetime.timedelta(days=6)
        if w == this:
            ps = ps_now
        else:
            cand = [x for x in hist if x[0] <= end]
            if not cand:
                w += datetime.timedelta(days=7)
                continue
            h = cand[-1][1]
            if h not in snaps:
                snaps[h] = load(h)
            ps = snaps[h]
        rows.append(_week_row(w, ps))
        for p in ps:
            if p.get("id"):
                fs = p.get("firstSeen")
                if fs and (p["id"] not in first or fs < first[p["id"]]):
                    first[p["id"]] = fs
        w += datetime.timedelta(days=7)
    for r in rows:
        s0 = datetime.date.fromisoformat(r["week"])
        e0 = (s0 + datetime.timedelta(days=6)).isoformat()
        r["new"] = sum(1 for fs in first.values() if r["week"] <= fs <= e0)
    return rows[-WEEKLY_SHOW:]


def _short(week):
    d = datetime.date.fromisoformat(week)
    return f"{d.month}/{d.day}"


def weekly_svg(rows, key_a, key_b, label_a, label_b, title, unit):
    """週ごとの積み上げ棒（下が key_a・上が key_b）。JS なし・色は CSS 変数（札の色）。"""
    if not rows:
        return ""
    W, H, L, B, T = 720, 230, 44, 34, 18
    mx = max(r[key_a] + r[key_b] for r in rows) or 1
    step = (W - L - 8) / len(rows)
    bw = step * 0.62
    ph = H - B - T
    out = [f'<svg class="md-svg" viewBox="0 0 {W} {H}" role="img" aria-label="{_esc(title)}" xmlns="http://www.w3.org/2000/svg">',
           f'<title>{_esc(title)}</title>']
    for frac in (0, 0.5, 1):
        y = T + ph * (1 - frac)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - 8}" y2="{y:.1f}" stroke="var(--border)" stroke-width="1"/>'
                   f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="var(--text-3)">{round(mx * frac):,}</text>')
    for i, r in enumerate(rows):
        x = L + step * i + (step - bw) / 2
        ha = r[key_a] / mx * ph
        hb = r[key_b] / mx * ph
        out.append(f'<rect x="{x:.1f}" y="{T + ph - ha:.1f}" width="{bw:.1f}" height="{ha:.1f}" fill="var(--gold)"/>'
                   f'<rect x="{x:.1f}" y="{T + ph - ha - hb:.1f}" width="{bw:.1f}" height="{hb:.1f}" fill="var(--navy)"/>')
        tot = r[key_a] + r[key_b]
        if tot and (i == len(rows) - 1 or i == 0 or tot == mx):
            out.append(f'<text x="{x + bw / 2:.1f}" y="{T + ph - ha - hb - 4:.1f}" text-anchor="middle" font-size="11" fill="var(--text-2)">{tot:,}</text>')
        if i % 2 == (len(rows) - 1) % 2:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 14}" text-anchor="middle" font-size="11" fill="var(--text-3)">{_short(r["week"])}</text>')
    out.append(f'<text x="{L}" y="12" font-size="11" fill="var(--text-3)">{_esc(unit)}</text>')
    out.append("</svg>")
    legend = (f'<p class="md-legend"><span><i style="background:var(--gold)"></i>{_esc(label_a)}</span>'
              + (f'<span><i style="background:var(--navy)"></i>{_esc(label_b)}</span>' if label_b else "") + "</p>")
    return "\n".join(out) + legend


def _mwcell(r):
    return f'{r["mw"]:,}' if r["mw_ok"] else "—"


def _mw_rows(rows):
    """MW の図用: 出力の欠けが多い週は図から外す（空の枠も残さない。表は「—」）。"""
    return [dict(r, a=r["mw"], b=0) for r in rows if r["mw_ok"]]


def _mw_chart_ja(rows):
    ok = _mw_rows(rows)
    if len(ok) < 2:
        return '<p class="md-note">合計出力の図は、値の欠けの少ない週が2週以上そろうまで出しません（表を見てください）。</p>'
    svg = weekly_svg(ok, "a", "b", "合計MW", "", "販売中の合計出力（MW）の週ごとの推移", "MW")
    gone = len(rows) - len(ok)
    if gone:
        svg += f'<p class="md-note">値の欠けた{gone}週は図に出していません（表は「—」）。</p>'
    return svg


def _ths(cols):
    """表の見出しの行（th scope=col）。"""
    return "".join(f'<th scope="col">{_esc(c)}</th>' for c in cols)


def weekly_section_ja(rows, generated):
    if len(rows) < 2:
        return ""
    last = rows[-1]
    body = "".join(
        f'<tr><th scope="row"><time datetime="{r["week"]}">{_esc(_short(r["week"]))}</time>{"（途中）" if i == len(rows) - 1 else ""}</th><td class="n">{r["n"]}</td><td class="n">{_mwcell(r)}</td>'
        f'<td class="n">{r["hv"]}</td><td class="n">{r["ehv"]}</td><td class="n">{r["rights"]}</td><td class="n">{r["built"]}</td>'
        f'<td class="n">{r["new"]}</td></tr>' for i, r in enumerate(rows))
    nmw = sum(1 for r in rows if not r["mw_ok"])
    mw_note = (f"合計MWは、出力の値が空の案件が多い週（{nmw}週）を表で「—」にし、図からも外しています。"
               "値の欠けで増減して見える週を、規模の推移として出さないためです。") if nmw else ""
    last_mw = f"・{last['mw']:,}MW" if last["mw_ok"] else ""
    return f"""<section class="md"><div class="container">
  <div class="section-label">週ごとの推移</div>
  <h2 class="md-h">販売中の件数と規模の、週ごとの推移</h2>
  <p class="md-lead">毎週の終わり（日曜）に、買い手に見えていた案件の件数と合計出力です。直近{len(rows)}週を、月曜はじまりの週で並べています。今週は{_esc(generated)}時点の途中の数です。案件が載ると増え、一覧から外れると減ります。</p>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">件数（高圧・特別高圧の積み上げ）</h3>{weekly_svg(rows, "hv", "ehv", "高圧", "特別高圧", "販売中の件数の週ごとの推移（高圧・特別高圧）", "件")}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">合計出力（MW）</h3>{_mw_chart_ja(rows)}</div>
  </div>
  <div class="md-scroll"><table class="md-t"><caption>販売中の件数と合計出力の週ごとの推移（直近{len(rows)}週・高圧と特別高圧・権利譲渡と完成渡しの内訳）</caption><thead><tr>{_ths(["週（月曜）", "件数", "合計MW", "高圧", "特別高圧", "権利譲渡", "完成渡し", "新しく載った件"])}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">図の件数は高圧と特別高圧の積み上げです。電圧が未設定の案件（直近は{last["other_v"]}件）は図に入らず、表の件数には入ります。{mw_note}「新しく載った件」は、その週に一覧へ載った案件の数です。{GROWTH_NOTE}取得の形が確認中の案件は、権利譲渡・完成渡しの列に入りません。当社の観測で、日本の市場全体の数ではありません。価格・案件名・所在地は載せていません。毎朝この表を作り直しています（直近は{last["n"]}件{last_mw}）。</p>
</div></section>
"""


def weekly_section_en(rows, generated):
    if len(rows) < 2:
        return ""
    last = rows[-1]
    body = "".join(
        f'<tr><th scope="row"><time datetime="{r["week"]}">{_esc(_short(r["week"]))}</time>{" (partial)" if i == len(rows) - 1 else ""}</th><td class="n">{r["n"]}</td><td class="n">{_mwcell(r)}</td>'
        f'<td class="n">{r["hv"]}</td><td class="n">{r["ehv"]}</td><td class="n">{r["rights"]}</td><td class="n">{r["built"]}</td>'
        f'<td class="n">{r["new"]}</td></tr>' for i, r in enumerate(rows))
    return f"""<section class="md" id="weekly"><div class="container">
  <div class="section-label">Weekly volume</div>
  <h2 class="md-h">Listed projects by week</h2>
  <p class="md-lead">Number and total capacity of the projects visible to buyers at the end of each week (Monday-start weeks, last {len(rows)}). The latest week is partial, as of {_esc(generated)}.</p>
  {weekly_svg(rows, "hv", "ehv", "High voltage", "Extra-high voltage", "Listed projects per week (high voltage and extra-high voltage)", "projects")}
  <div class="md-scroll"><table class="md-t"><caption>Listed projects and total capacity by week (last {len(rows)} weeks, by voltage class and structure)</caption><thead><tr>{_ths(["Week of", "Projects", "Total MW", "High voltage", "Extra-high", "Transfer of rights", "Completed-build", "New listings"])}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">The chart stacks high voltage and extra-high voltage; projects without a voltage ({last["other_v"]} in the latest week) are not in the chart but are in the table counts. {"Total MW is shown as &ldquo;&mdash;&rdquo; for weeks when many projects had no capacity value, so that gaps in the data are not read as a change in market size. " if any(not r["mw_ok"] for r in rows) else ""}{GROWTH_NOTE_EN} ScienceX&rsquo;s own listings, not statistics for the whole Japanese market. Projects whose structure is under review are not in the last two structure columns. No prices, sites or names are published here.</p>
</div></section>
"""


# ---------------------------------------------------------------- 部品
def bar_rows(pairs, total, unit="件", lang="ja"):
    """横棒の行。pairs=[(ラベル, 値)]。CSS だけで描く（JS 無し）。"""
    if not pairs or not total:
        return {"ja": "<p class=\"md-note\">該当なし</p>", "zh": "<p class=\"md-note\">无</p>"}.get(lang, "<p class=\"md-note\">None</p>")
    if lang == "zh" and unit == "件":
        unit = "个"
    mx = max(v for _, v in pairs) or 1
    out = ['<div class="md-bars">']
    for label, v in pairs:
        pct = v / total * 100
        out.append(f'<div class="md-bar"><span class="md-bar-l">{_esc(label)}</span>'
                   f'<span class="md-bar-t"><span class="md-bar-f" style="width:{v / mx * 100:.1f}%"></span></span>'
                   + (f'<span class="md-bar-v">{v}{unit}<small>（{pct:.0f}%）</small></span></div>' if lang in ("ja", "zh")
                      else f'<span class="md-bar-v">{v}<small> ({pct:.0f}%)</small></span></div>'))
    out.append("</div>")
    return "\n".join(out)


def rows_html(ps, today):
    """管内ページの静的一覧。/projects の静的一覧（inject_stats.render_list）と同じ文言・同じ並び。"""
    today_ym = today.strftime("%Y-%m")

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)
    lines = ['<ul class="pj-static">']
    for p in sorted(ps, key=key):
        mw = p.get("mw"); mwh = p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        cod = cod_text(p, today_ym)
        parts = [f"{_esc(p.get('pref') or '所在県 確認中')}", _esc(p.get("voltage") or "—"), size,
                 _esc(cod if p.get("live") else "連系の見込み " + cod)]
        if not p.get("live"):
            parts.append(_esc(p.get("status") or "—"))
        parts.append(_esc(p.get("scheme") or "取得の形 確認中"))
        if is_new(p, today):
            parts.append(f"新着（{_esc(p['firstSeen'])} 掲載）")
        pid = _esc(p.get("id") or "")
        lines.append(f'<li id="p-{pid}"><a href="https://dealroom.scix.co.jp/catalog/{pid}" target="_top"><b>{pid}</b></a>　' + "｜".join(parts) + "</li>")
    lines.append("</ul>")
    return "\n".join(lines)


CSS = """
:root{--navy:#1F2A48;--navy-light:#2D3A5C;--gold:#C49A3C;--green:#1A7A4C;--white:#fff;--off-white:#F5F5F3;--text:#1F2A48;--text-2:#555555;--text-3:#8C8C8C;--border:#E6E6E6;--sans:'Noto Sans JP',sans-serif;--serif:'Noto Sans JP',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}html{font-size:16px;scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--text);background:var(--white);line-height:1.9;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.container{max-width:1100px;margin:0 auto;padding:0 24px}
.section-label{font-size:.7rem;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-bottom:12px}
.hero{padding:64px 0 40px;background:linear-gradient(160deg,var(--white) 0%,var(--off-white) 60%,#EEEEEC 100%)}
.hero h1{font-family:var(--serif);font-size:clamp(1.5rem,3.4vw,2.2rem);font-weight:700;color:var(--navy);line-height:1.5;margin-bottom:16px}
.hero p{font-size:.95rem;color:var(--text-2);max-width:760px}
.badge{display:inline-block;margin-bottom:16px;padding:5px 14px;background:rgba(26,122,76,.1);color:var(--green);font-size:.72rem;font-weight:600;letter-spacing:1px;border-radius:4px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:28px 0 0}
.kpi div{background:var(--white);border:1px solid var(--border);border-radius:8px;padding:16px 18px}
.kpi b{display:block;font-family:var(--serif);font-size:1.6rem;color:var(--navy);line-height:1.3}
.kpi span{font-size:.78rem;color:var(--text-2)}
section.md{padding:40px 0;border-top:1px solid var(--border)}
h2.md-h{font-family:var(--serif);font-size:1.25rem;font-weight:600;color:var(--navy);margin-bottom:10px}
.md-lead{font-size:.92rem;color:var(--text-2);margin-bottom:18px;max-width:760px}
.md-bars{max-width:760px}.md-bar{display:grid;grid-template-columns:9.5em 1fr 8.5em;align-items:center;gap:10px;font-size:.88rem;padding:4px 0}
.md-bar-l{color:var(--text)}.md-bar-t{height:12px;background:#EFECE6;border-radius:3px;overflow:hidden}.md-bar-f{display:block;height:100%;background:var(--gold)}
.md-bar-v{color:var(--text-2);text-align:right}.md-bar-v small{color:var(--text-3);font-size:.8em;margin-left:2px}
.md-note{font-size:.84rem;color:var(--text-3);margin-top:8px}
.md-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px 40px}
table.md-t{border-collapse:collapse;font-size:.88rem;max-width:760px;width:100%}.md-t th,.md-t td{border-bottom:1px solid var(--border);padding:7px 10px;text-align:left}.md-t th{color:var(--text-2);font-weight:500;background:var(--off-white)}.md-t td.n{text-align:right;font-variant-numeric:tabular-nums}.md-scroll .md-t th,.md-scroll .md-t td.n{white-space:nowrap}
.areas{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;max-width:900px}
.areas a{display:block;border:1px solid var(--border);border-radius:8px;padding:14px 16px;text-decoration:none;color:var(--text);background:var(--white)}
.areas a:hover{border-color:var(--gold)}.areas b{display:block;color:var(--navy);font-size:1rem}.areas span{font-size:.82rem;color:var(--text-2)}
.pj-static{list-style:none;padding:0;margin:0;border-top:1px solid var(--border);max-width:900px}
.pj-static li{padding:9px 0;border-bottom:1px solid var(--border);font-size:.88rem;line-height:1.7}.pj-static li a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.cite{margin-top:28px;background:var(--off-white);border:1px solid var(--border);border-radius:8px;padding:16px 20px;font-size:.86rem;line-height:1.9;max-width:760px}
.cite .cite-h{font-size:.8em;font-weight:700;color:var(--gold);letter-spacing:.08em;margin-bottom:6px}
.cta{padding:56px 0;background:linear-gradient(160deg,var(--navy) 0%,var(--navy-light) 100%);text-align:center;color:#fff}
.cta h2{font-family:var(--serif);font-size:1.4rem;font-weight:600;margin-bottom:10px}.cta p{color:rgba(255,255,255,.8);font-size:.92rem;margin-bottom:22px}
.btn-primary{display:inline-flex;align-items:center;gap:8px;padding:14px 32px;background:var(--gold);color:var(--navy);font-size:.9rem;font-weight:600;text-decoration:none;border-radius:4px;margin:4px}
.btn-secondary{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:transparent;color:#fff;font-size:.88rem;font-weight:600;text-decoration:none;border-radius:4px;border:1px solid rgba(255,255,255,.45);margin:4px}
.scix-footer{background-color:#1F2A48;color:rgba(255,255,255,0.85);font-family:'Noto Sans JP',sans-serif;font-weight:300;font-size:12.5px;line-height:1.9;padding:44px 28px 32px;width:100%}
.scix-footer-inner{display:flex;flex-direction:column;align-items:center;gap:28px}.scix-footer-logo img{height:48px;width:auto;display:block;opacity:.95}
.scix-footer-info{text-align:center}.scix-footer-copyright{font-size:11px;letter-spacing:.04em;color:rgba(255,255,255,.55);margin-top:20px}
.scix-footer-company{font-size:12.5px;line-height:2;color:rgba(255,255,255,.8)}.scix-footer-company .company-name{font-weight:500;font-size:13.5px;color:rgba(255,255,255,.92);margin-bottom:2px}
.scix-footer-company .representative{margin-top:4px;color:rgba(255,255,255,.6);font-size:12px}.scix-footer-company a{color:rgba(255,255,255,.8);text-decoration:none}.scix-footer-company a:hover{color:#C49A3C}
.scix-footer-divider{width:60px;border:none;border-top:1px solid rgba(196,154,60,.5)}
.md-svg{width:100%;height:auto;display:block;max-width:760px}.md-legend{display:flex;gap:16px;font-size:.8rem;color:var(--text-2);margin:4px 0 0}.md-legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.md-scroll{overflow-x:auto;margin-top:18px}
.md-t tbody th{background:none;color:var(--text);font-weight:500}.md-t caption{caption-side:top;text-align:left;font-size:.8rem;color:var(--text-3);padding:0 0 6px}
.cite p{margin:4px 0}.cite .cite-line{margin:8px 0;padding:8px 12px;background:#fff;border:1px solid var(--border);border-radius:6px;overflow-wrap:anywhere}.cite .cite-meta{font-size:.8rem;color:var(--text-3);overflow-wrap:anywhere}
.md-dl{list-style:none;padding:0;margin:0 0 6px;max-width:760px}.md-dl li{padding:8px 0;border-bottom:1px solid var(--border);font-size:.9rem}.md-dl a{color:var(--navy);font-weight:600;text-decoration:none;border-bottom:1px solid var(--gold)}.md-dl small{display:block;color:var(--text-3);font-size:.8rem}
@media(max-width:640px){.md-bar{grid-template-columns:7em 1fr 7em;font-size:.82rem}.hero{padding:48px 0 32px}}
"""

FOOTER = """<footer class="scix-footer">
  <div class="scix-footer-inner">
    <a href="https://www.scix.co.jp/" class="scix-footer-logo" aria-label="ScienceX ホーム">
      <img width="300" height="118" src="/img/logo-white.png" alt="ScienceX サイエンスエックス株式会社" loading="lazy" />
    </a>
    <hr class="scix-footer-divider" />
    <div class="scix-footer-info">
      <div class="scix-footer-company">
        <div class="company-name">サイエンスエックス株式会社</div>
        〒103-0016 東京都中央区日本橋小網町8-2<br>
        BIZMARKS日本橋茅場町<br>
        TEL: <a href="tel:0366913484">03-6691-3484</a><br>
        MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>
        <div class="representative">代表取締役 中島 晋也（工学博士）</div>
      </div>
      <div class="scix-footer-nav" style="margin-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:10px 22px;justify-content:center;">
        <a href="/grid-storage" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">蓄電池事業のしくみ</a>
        <a href="/transfer" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件を買う</a>
        <a href="https://dealroom.scix.co.jp/" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">蓄電所マーケット</a>
        <a href="/market-data" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">売り案件の市場データ</a>
        <a href="/sourcing" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件・権利を売る</a>
        <a href="/sell-form" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件・権利の売却査定</a>
        <a href="/knowledge" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">ナレッジ</a>
        <a href="/qa" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">入門Q&amp;A</a>
        <a href="/company" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">会社案内</a>
        <a href="/contact" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">お問い合わせ</a>
        <a href="/investors" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">系統用蓄電池への投資</a>
        <a href="/fund" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">系統用蓄電池ファンド</a>
        <a href="/privacy" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">プライバシーポリシー</a>
      </div>
      <div class="scix-footer-copyright">&copy; 2025–2026 Science X Inc. All Rights Reserved.</div>
    </div>
  </div>
</footer>"""

FONTS = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&display=swap"


def head(title, desc, path, jsonld, robots="index,follow,max-image-preview:large"):
    url = BASE + path
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<link rel="icon" type="image/svg+xml" href="/img/favicon.svg">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
{GA_BLOCK}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ja" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{_esc(title)}">
<meta property="og:description" content="{_esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="ScienceX">
<meta property="og:image" content="{BASE}/img/ogp-m.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(title)}">
<meta name="twitter:description" content="{_esc(desc)}">
<meta name="twitter:image" content="{BASE}/img/ogp-m.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONTS}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONTS}"></noscript>
<style>{CSS}</style>
{jsonld}
<link rel="stylesheet" href="/theme.css">
</head>
<body>
<script src="/header.js"></script>
"""


def ld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=1) + '\n</script>'


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def nav_crumbs(items):
    sep = '<span style="color:#C49A3C;margin:0 7px">›</span>'
    parts = [f'<a href="{u}" style="color:#555555;text-decoration:none">{_esc(n)}</a>' for n, u in items[:-1]]
    parts.append(f'<span style="color:#8C8C8C">{_esc(items[-1][0])}</span>')
    return ('<nav data-scix-breadcrumb aria-label="breadcrumb" style="max-width:1100px;margin:0 auto;padding:14px 24px 0;'
            "font-family:'Noto Sans JP',sans-serif;font-size:12.5px;line-height:1.6;color:#8C8C8C\">" + sep.join(parts) + '</nav>')


ORG = {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "サイエンスエックス株式会社",
       "url": BASE + "/"}
EN_ORG = {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": BASE + "/en"}

CTA = """<section class="cta"><div class="container">
  <h2>案件そのものは、蓄電所マーケットでご覧いただけます</h2>
  <p>今ある案件は、登録なしで蓄電所マーケットで見られます。価格と資料は、無料登録のあとで見られます（登録画面で秘密保持の誓約に同意いただきます）。売りたい方は、査定は無料で、最初の連絡は5行で足ります。</p>
  <a class="btn-primary" href="https://dealroom.scix.co.jp/" target="_top">蓄電所マーケットで案件を見る →</a>
  <a class="btn-secondary" href="/sell-form">案件・権利の売却査定（無料）</a>
</div></section>
"""

NOTE_SCOPE = ("ここで数えているのは、当社に持ち込まれ、一覧への掲載を了承いただいた系統用蓄電池（蓄電所）の売り案件です。"
              "日本の市場全体の統計ではなく、当社の観測です。地番・売主は載せていません（価格と資料は、蓄電所マーケットで無料登録のあとに見られます）。"
              "数字は毎朝、案件一覧と同じデータから自動で集計し直しています。")


# ---------------------------------------------------------------- 2026-11-22 足した集計（値のある件だけ・母数と欠けを併記）
SIZE_BINS = [(None, 2, "2MW未満", "Under 2 MW"), (2, 10, "2〜10MW未満", "2 to under 10 MW"),
             (10, 30, "10〜30MW未満", "10 to under 30 MW"), (30, None, "30MW以上", "30 MW or more")]
LEAD_BANDS = [("6か月以内", "Within 6 months"), ("7〜12か月", "7–12 months"), ("13〜24か月", "13–24 months"), ("25か月以上", "25 months or more")]
VOLT_ORDER = ["高圧", "特別高圧", "低圧", "確認中"]
SCHEME_COLS = ["権利譲渡", "完成渡し", "確認中"]
OTHER = "その他"


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def lead_band(n):
    return "6か月以内" if n <= 6 else "7〜12か月" if n <= 12 else "13〜24か月" if n <= 24 else "25か月以上"


def size_bin(mw):
    for lo, hi, ja, _ in SIZE_BINS:
        if (lo is None or mw >= lo) and (hi is None or mw < hi):
            return ja
    return SIZE_BINS[-1][2]


def _med(xs):
    """中央値（偶数個なら真ん中2つの平均）。表示は小数1桁まで。"""
    m = statistics.median(xs)
    return round(m, 1) if isinstance(m, float) else m


def _g(v):
    return f"{v:g}" if _num(v) else "—"


def extra_stats(ps):
    """電圧×取得の形・規模の区分・連系までの月数（取得の形別・電圧別）。件数が MIN_GROUP 未満の電圧は「その他」にまとめる。"""
    n = len(ps)

    def vg(p):
        return p.get("voltage") or "確認中"

    def sg(p):
        s = p.get("scheme")
        return s if s in ("権利譲渡", "完成渡し") else "確認中"
    vt = Counter(vg(p) for p in ps)
    keep = [v for v in VOLT_ORDER if vt.get(v, 0) >= MIN_GROUP] + sorted(v for v in vt if v not in VOLT_ORDER and vt[v] >= MIN_GROUP)
    merged = sorted((v for v in vt if v not in keep), key=lambda v: (VOLT_ORDER.index(v) if v in VOLT_ORDER else 99, v))

    def vgm(p):
        v = vg(p)
        return v if v in keep else OTHER
    vrows = keep + ([OTHER] if merged else [])
    cross = Counter((vgm(p), sg(p)) for p in ps)
    scols = [s for s in SCHEME_COLS if any(sg(p) == s for p in ps)]
    mw_ps = [p for p in ps if _num(p.get("mw"))]
    size = Counter(size_bin(p["mw"]) for p in mw_ps)
    size_med = []
    for v in vrows:
        xs = [p["mw"] for p in mw_ps if vgm(p) == v]
        if len(xs) >= MIN_GROUP:
            size_med.append((v, _med(xs), len(xs)))
    lead_ps = [p for p in ps if _num(p.get("leadMonths"))]

    def lead_rows(key, order):
        rows, other = [], 0
        for k in order:
            xs = sorted(p["leadMonths"] for p in lead_ps if key(p) == k)
            if len(xs) >= MIN_GROUP:
                rows.append({"k": k, "n": len(xs), "med": _med(xs), "bands": Counter(lead_band(x) for x in xs)})
            else:
                other += len(xs)
        return rows, other
    lead_s, lead_s_other = lead_rows(sg, SCHEME_COLS)
    lead_v, lead_v_other = lead_rows(vgm, vrows)
    return {"n": n, "vrows": vrows, "vmerged": merged, "scols": scols, "cross": cross,
            "vtotal": Counter(vgm(p) for p in ps), "stotal": Counter(sg(p) for p in ps),
            "n_mw": len(mw_ps), "size": size, "size_med": size_med,
            "n_lead": len(lead_ps), "lead_s": lead_s, "lead_s_other": lead_s_other, "lead_v": lead_v, "lead_v_other": lead_v_other}


def merge_small(counter, keep_min, other_label=OTHER):
    """[(区分, 件数)]。件数が keep_min 未満の区分を other_label にまとめ、まとめた区分の名前も返す。"""
    keep = [(k, v) for k, v in counter.most_common() if v >= keep_min]
    small = sorted(k for k, v in counter.items() if v < keep_min)
    if small:
        keep.append((other_label, sum(counter[k] for k in small)))
    return keep, small


# ---------------------------------------------------------------- 買主のリクエスト（公開の口の選択肢ごとの数だけ）
NEEDS_FIELDS = [("sale_type", "買い方", "Purchase structure"), ("voltage", "電圧", "Voltage"),
                ("grid_area", "求めるエリア（複数選べる・延べ）", "Grid areas wanted (several allowed)"),
                ("cod", "運転開始の希望", "Wanted commercial operation"), ("grid_stage", "電力の手続き", "Grid-process stage wanted")]
NEEDS_ORDER = {"sale_type": ["権利渡し", "完成渡し"], "voltage": ["高圧", "特別高圧", "高圧・特別高圧", "低圧"],
               "grid_area": ["北海道", "東北", "東京", "中部", "北陸", "関西", "中国", "四国", "九州", "沖縄"],
               "grid_stage": ["本回答あり（またはその先）", "保証金支払済（またはその先）", "工事負担金支払済（またはその先）"]}
NEEDS_EN = {"権利渡し": "Transfer of rights", "完成渡し": "Completed-build handover", "高圧": "High voltage", "特別高圧": "Extra-high voltage",
            "高圧・特別高圧": "High or extra-high voltage", "低圧": "Low voltage",
            "本回答あり（またはその先）": "Answer to the connection application received (or later)",
            "保証金支払済（またはその先）": "Grid deposit paid (or later)",
            "工事負担金支払済（またはその先）": "Grid construction cost paid (or later)"}


def needs_counts(items):
    """公開の口の needs[] → {"n", "fields": {k: {"set": 書いた件数, "values": {選択肢: 数}}}}。エリアは「・」で分けて延べで数える。"""
    out = {"n": len(items), "fields": {}}
    for k, _, _ in NEEDS_FIELDS:
        vals, n_set = Counter(), 0
        for it in items:
            v = next((r.get("value") for r in it.get("rows", []) if r.get("k") == k and r.get("value")), None)
            if not v:
                continue
            n_set += 1
            for part in (v.split("・") if k == "grid_area" else [v]):
                vals[part.strip()] += 1
        out["fields"][k] = {"set": n_set, "values": dict(sorted(vals.items()))}
    return merge_small_needs(out)


def merge_small_needs(nd):
    """NEEDS_MIN 未満の選択肢を「その他の選択肢」に足し込む。公開の控え（buyer-requests.json）も頁と同じ、まとめた後の数だけを持つ。"""
    if not nd:
        return nd
    for f in nd.get("fields", {}).values():
        vals = f.get("values", {})
        small = sum(v for x, v in vals.items() if x == "その他の選択肢" or v < NEEDS_MIN)
        kept = {x: v for x, v in vals.items() if x != "その他の選択肢" and v >= NEEDS_MIN}
        if small:
            kept["その他の選択肢"] = small
        f["values"] = dict(sorted(kept.items()))
    return nd


def load_needs():
    try:
        with open(os.path.join(ROOT, NEEDS_JSON), encoding="utf-8") as f:
            return merge_small_needs(json.load(f))
    except (OSError, ValueError):
        return None


def fetch_needs(today):
    """公開の口を読み、選択肢ごとの数の控え（dict）を返す。数が前の控えと同じなら前の控えをそのまま返す（日付を動かさない）。
    読めない・形が違うときは前の控え（無ければ None）。"""
    old = load_needs()
    try:
        req = urllib.request.Request(NEEDS_API, headers={"User-Agent": "scix-web-build/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            items = json.loads(r.read().decode("utf-8")).get("needs")
        if not isinstance(items, list):
            raise ValueError("needs が配列でない")
    except (OSError, ValueError) as e:
        print(f"注意: 買主のリクエストの口が読めない（前の控えのまま）: {e}", file=sys.stderr)
        return old
    c = needs_counts(items)
    if old and old.get("n") == c["n"] and old.get("fields") == c["fields"]:
        return old
    return {"source": NEEDS_PAGE, "asOf": today.isoformat(), **c}


def needs_text(nd):
    return json.dumps(nd, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def _cod_key(v):
    m = re.match(r"(\d{4})年(\d{1,2})月", v)
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 99)


def needs_pairs(nd, k):
    """1つの項目の [(選択肢, 数)]（並びは決まった順・NEEDS_MIN 未満は「その他の選択肢」）と「指定なし」の数。"""
    f = nd["fields"].get(k) or {"set": 0, "values": {}}
    vals = f["values"]
    order = NEEDS_ORDER.get(k)
    if k == "cod":
        keys = sorted(vals, key=_cod_key)
    elif order:
        keys = [x for x in order if x in vals] + sorted(x for x in vals if x not in order)
    else:
        keys = sorted(vals)
    pairs = [(x, vals[x]) for x in keys if vals[x] >= NEEDS_MIN and x != "その他の選択肢"]
    small = sum(vals[x] for x in keys if vals[x] < NEEDS_MIN or x == "その他の選択肢")
    if small:
        pairs.append(("その他の選択肢", small))
    return pairs, nd["n"] - f["set"], f["set"]


def needs_en(v):
    if v in NEEDS_EN:
        return NEEDS_EN[v]
    if v in EN_AREA:
        return EN_AREA[v]
    if v == "その他の選択肢":
        return "Other options"
    m = re.match(r"(\d{4})年(\d{1,2})月まで$", v)
    if m:
        return f"By {EN_MON[int(m.group(2)) - 1]} {m.group(1)}"
    return None


# ---------------------------------------------------------------- 引用のしかた（データの頁に共通）
def cite_html(lang, name, url, updated, extra=""):
    """「引用のしかた」の箱: 出典として書く1行・頁の住所・更新日。license の住所は付けない（利用条件を名乗るかは中島さんの決め）。"""
    t = f'<time datetime="{_esc(updated)}">{_esc(updated)}</time>'
    if lang == "ja":
        return (f'<div class="cite" id="cite"><div class="cite-h">引用のしかた</div>'
                f'<p>この頁の数字・図表の引用を歓迎します。記事・資料・社内の検討にお使いいただくときは、出典として次の1行をお書きください。</p>'
                f'<p class="cite-line">出典: サイエンスエックス株式会社『{_esc(name)}』（{_esc(updated)} 更新） {_esc(url)}</p>'
                f'<p class="cite-meta">頁の住所: <a href="{_esc(url)}">{_esc(url)}</a>　更新日: {t}</p>{extra}</div>')
    if lang == "zh":
        return (f'<div class="cite" id="cite"><div class="cite-h">引用方法</div>'
                f'<p>欢迎引用本页的数字与图表。在文章、资料或内部研讨中使用时，请按下面的格式注明出处。</p>'
                f'<p class="cite-line">出处：Science X Inc.《{_esc(name)}》（{_esc(updated)}更新） {_esc(url)}</p>'
                f'<p class="cite-meta">页面地址：<a href="{_esc(url)}">{_esc(url)}</a>　更新日期：{t}</p>{extra}</div>')
    return (f'<div class="cite" id="cite"><div class="cite-h">How to cite</div>'
            f'<p>You are welcome to quote the figures and charts on this page. Please give the source as follows.</p>'
            f'<p class="cite-line">Source: Science X Inc., &ldquo;{_esc(name)}&rdquo; (updated {_esc(updated)}), {_esc(url)}</p>'
            f'<p class="cite-meta">Page: <a href="{_esc(url)}">{_esc(url)}</a> &middot; Updated: {t}</p>{extra}</div>')


# ---------------------------------------------------------------- CSV（UTF-8 BOM 付き・CRLF。/report/data と同じ型）
def csv_text(rows):
    def q(c):
        c = "" if c is None else str(c)
        return '"' + c.replace('"', '""') + '"' if any(x in c for x in ',"\n') else c
    return "﻿" + "".join(",".join(q(c) for c in r) + "\r\n" for r in rows)


def _en_label(kind, v):
    """CSV・英語の頁の区分の英語。"""
    if v == OTHER:
        return "Other"
    if kind == "area":
        return EN_AREA.get(v, v)
    if kind == "pref":
        return EN_PREF.get(v, v)
    if kind == "volt":
        return EN_VOLT.get(v, "Under review" if v == "確認中" else v)
    if kind == "scheme":
        return EN_SCHEME.get(v, "Under review" if v == "確認中" else v)
    if kind == "status":
        return EN_STATUS.get(v, "Under review" if v == "確認中" else v)
    if kind == "size":
        return next((en for _, _, ja, en in SIZE_BINS if ja == v), v)
    if kind == "band":
        return dict(LEAD_BANDS).get(v, v)
    if kind == "half":
        m = re.match(r"(\d{4})年度(上期|下期)", v)
        return f"FY{m.group(1)} {'H1 (Apr–Sep)' if m.group(2) == '上期' else 'H2 (Oct–Mar)'}" if m else v
    return v


def summary_rows(ps, s, x, generated, today):
    """集計の CSV の行（日英の組）。1行＝(集計, 区分, 内訳, 値, 単位, 母数, 注記) の (ja, en)。"""
    rows = []

    def add(kind, cat, sub, val, unit, base, note=("", "")):
        rows.append((kind, cat, sub, val, unit, base, note))
    n = s["n"]
    U = ("件", "projects")
    n_mw = sum(1 for p in ps if _num(p.get("mw")))
    n_mwh = sum(1 for p in ps if _num(p.get("mwh")))
    add(("全体", "Overall"), ("販売中の案件", "Projects listed for sale"), ("", ""), n, U, n)
    add(("全体", "Overall"), ("合計出力", "Total capacity"), ("", ""), s["mw"], ("MW", "MW"), n_mw,
        (f"出力の値が無い{n - n_mw}件は除く", f"Excludes {n - n_mw} projects without a MW value"))
    add(("全体", "Overall"), ("合計容量", "Total energy"), ("", ""), s["mwh"], ("MWh", "MWh"), n_mwh,
        (f"容量の値が無い{n - n_mwh}件は除く", f"Excludes {n - n_mwh} projects without a MWh value"))
    pairs, small = merge_small(s["area"], MIN_GROUP)
    for a, c in pairs:
        note = (f"{MIN_GROUP}件未満の管内（{'・'.join(small)}）をまとめた", f"Grid areas with fewer than {MIN_GROUP} projects combined") if a == OTHER else ("", "")
        add(("管内別", "By grid area"), (a, _en_label("area", a)), ("", ""), c, U, n, note)
    top = s["pref"].most_common(10)
    rest = n - sum(c for _, c in top)
    for p_, c in top:
        add(("都道府県別（上位10）", "By prefecture (top 10)"), (p_, _en_label("pref", p_)), ("", ""), c, U, n)
    if rest:
        k = len(s["pref"]) - len(top)
        add(("都道府県別（上位10）", "By prefecture (top 10)"), (OTHER, "Other"), ("", ""), rest, U, n,
            (f"上位10の外の{k}都道府県（と所在県が確認中の案件）", f"The other {k} prefectures (and projects whose prefecture is under review)"))
    for kind, key, lab in (("電圧区分", "voltage", "By voltage class"), ("取得の形", "scheme", "By structure"), ("進み具合", "status", "By status")):
        lk = {"voltage": "volt", "scheme": "scheme", "status": "status"}[key]
        for k, c in Counter(p.get(key) or "確認中" for p in ps).most_common():
            add((kind, lab), (k, _en_label(lk, k)), ("", ""), c, U, n)
    for v in x["vrows"]:
        for sc in x["scols"]:
            note = (f"{MIN_GROUP}件未満の電圧（{'・'.join(x['vmerged'])}）をまとめた", f"Voltage classes with fewer than {MIN_GROUP} projects combined") if v == OTHER else ("", "")
            add(("電圧×取得の形", "Voltage class × structure"), (v, _en_label("volt", v)), (sc, _en_label("scheme", sc)),
                x["cross"].get((v, sc), 0), U, x["vtotal"][v], note)
    for _, _, ja, en in SIZE_BINS:
        add(("規模の区分", "By size"), (ja, en), ("", ""), x["size"].get(ja, 0), U, x["n_mw"],
            (f"出力の値が無い{n - x['n_mw']}件は除く", f"Excludes {n - x['n_mw']} projects without a MW value"))
    for v, med, k in x["size_med"]:
        add(("規模の中央値（電圧別）", "Median size by voltage class"), (v, _en_label("volt", v)), ("", ""), _g(med), ("MW（中央値）", "MW (median)"), k)
    for ja, en in LEAD_BANDS:
        add(("連系までの月数の区分", "Months to grid connection (bands)"), (ja, en), ("", ""), s["bands"].get(ja, 0), U, len(s["lead"]),
            (f"月数の無い{n - len(s['lead'])}件は除く・起点は回答書の記載のまま", f"Excludes {n - len(s['lead'])} projects without a figure; start point as written in the utility's answer"))
    for kind, rws, other, lk in ((("連系までの月数（取得の形別）", "Months to grid connection by structure"), x["lead_s"], x["lead_s_other"], "scheme"),
                                 (("連系までの月数（電圧別）", "Months to grid connection by voltage class"), x["lead_v"], x["lead_v_other"], "volt")):
        for r in rws:
            add(kind, (r["k"], _en_label(lk, r["k"])), ("中央値", "median"), _g(r["med"]), ("か月", "months"), r["n"],
                ((f"月数のある{MIN_GROUP}件未満の区分（{other}件）は除く" if other else ""), (f"Groups with fewer than {MIN_GROUP} figures ({other} projects) excluded" if other else "")))
            for ja, en in LEAD_BANDS:
                add(kind, (r["k"], _en_label(lk, r["k"])), (ja, en), r["bands"].get(ja, 0), U, r["n"])
    for h, c in sorted(s["half"].items()):
        add(("運転開始の予定（年度・半期）", "Planned COD (Japanese fiscal half-year)"), (h, _en_label("half", h)), ("", ""), c, U, s["ym_known"],
            ("今日より後の予定がある件だけ（連系済みは除く）", "Only projects with a future planned date (grid-connected excluded)"))
    fs = Counter((p.get("firstSeen") or "")[:7] for p in ps if p.get("firstSeen"))
    for m, c in sorted(fs.items()):
        add(("掲載月", "Month first listed"), (m, m), ("", ""), c, U, n,
            ("当社が一覧に載せた作業の波で、市場の伸びではない", "Reflects when we added projects to the list, not market growth"))
    return rows


def summary_csv(rows, lang, generated):
    i = 0 if lang == "ja" else 1
    src = BASE + ("/market-data" if lang == "ja" else "/en/market-data")
    head = (["集計日", "集計", "区分", "内訳", "値", "単位", "母数", "注記", "出典"] if lang == "ja"
            else ["as_of", "table", "category", "breakdown", "value", "unit", "base", "note", "source"])
    out = [head]
    for kind, cat, sub, val, unit, base, note in rows:
        out.append([generated, kind[i], cat[i], sub[i], val, unit[i], base, note[i], src])
    return csv_text(out)


def weekly_csv(weekly, lang, generated):
    src = BASE + ("/market-data" if lang == "ja" else "/en/market-data")
    head = (["週（月曜はじまり）", "途中の週", "件数", "合計出力（MW）", "高圧", "特別高圧", "権利譲渡", "完成渡し", "新しく載った件", "注記", "出典"] if lang == "ja"
            else ["week_start_monday", "partial_week", "projects", "total_mw", "high_voltage", "extra_high_voltage", "transfer_of_rights", "completed_build", "new_listings", "note", "source"])
    out = [head]
    rows = list(weekly)
    for j, r in enumerate(rows):
        last = j == len(rows) - 1
        note = []
        if not r["mw_ok"]:
            note.append("出力の値が空の案件が多い週のため合計出力は空欄" if lang == "ja" else "Total MW left blank: many projects had no MW value that week")
        if j == 0:
            note.append(GROWTH_NOTE if lang == "ja" else GROWTH_NOTE_EN)
        if last:
            note.append(f"{generated}時点の途中の数" if lang == "ja" else f"Partial week, as of {generated}")
        out.append([r["week"], ("はい" if lang == "ja" else "yes") if last else "", r["n"], r["mw"] if r["mw_ok"] else "", r["hv"], r["ehv"],
                    r["rights"], r["built"], r["new"], " / ".join(note), src])
    return csv_text(out)


def needs_csv(nd, lang):
    src = NEEDS_PAGE if lang == "ja" else NEEDS_PAGE_EN
    head = (["件数が変わった日", "集計", "選択肢", "数", "母数", "注記", "出典"] if lang == "ja"
            else ["last_changed", "field", "option", "count", "base", "note", "source"])
    out = [head, [nd["asOf"], "いま載っているリクエスト" if lang == "ja" else "Requests now listed", "", nd["n"], nd["n"], "", src]]
    for k, ja, en in NEEDS_FIELDS:
        pairs, unset, n_set = needs_pairs(nd, k)
        for v, c in pairs:
            lab = v if lang == "ja" else (needs_en(v) or "Other options")
            note = (f"{NEEDS_MIN}件未満の選択肢をまとめた" if lang == "ja" else f"Options with fewer than {NEEDS_MIN} combined") if v == "その他の選択肢" else ""
            if k == "grid_area" and not note:
                note = "延べ（1件で複数を選べる）" if lang == "ja" else "Several areas per request allowed"
            out.append([nd["asOf"], ja if lang == "ja" else en, lab, c, nd["n"], note, src])
        if unset:
            out.append([nd["asOf"], ja if lang == "ja" else en, "指定なし" if lang == "ja" else "Not specified", unset, nd["n"], "", src])
    return csv_text(out)


# ---------------------------------------------------------------- 2026-11-22 足した節（日英）
H3 = '<h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">'
H3B = '<h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">'


def _vl(v, lang):
    if lang == "zh":
        return _zh_label("volt", v, table=True)
    return (v if v != "確認中" else "電圧 確認中") if lang == "ja" else _en_label("volt", v)


def _sl(v, lang):
    if lang == "zh":
        return _zh_label("scheme", v)
    return v if lang == "ja" else _en_label("scheme", v)


def _list_ja(items):
    return "・".join(items)


def section_voltage_scheme(x, lang):
    cols = x["scols"]
    J = lang == "ja"
    lab_v, lab_t = {"ja": ("電圧", "計"), "en": ("Voltage class", "Total"), "zh": ("电压", "合计")}[lang]
    head = [lab_v] + [_sl(c, lang) for c in cols] + [lab_t]
    body = "".join(
        f'<tr><th scope="row">{_esc(_vl(v, lang))}</th>' + "".join(f'<td class="n">{x["cross"].get((v, c), 0)}</td>' for c in cols)
        + f'<td class="n">{x["vtotal"][v]}</td></tr>' for v in x["vrows"])
    body += (f'<tr><th scope="row">{lab_t}</th>' + "".join(f'<td class="n">{x["stotal"].get(c, 0)}</td>' for c in cols)
             + f'<td class="n">{x["n"]}</td></tr>')
    hv, ehv = x["vtotal"].get("高圧", 0), x["vtotal"].get("特別高圧", 0)
    if lang == "zh":
        say = ""
        if hv and ehv:
            say = (f"高压{hv}个项目中有{x['cross'].get(('高圧', '完成渡し'), 0)}个为完工交付，"
                   f"特别高压{ehv}个项目中有{x['cross'].get(('特別高圧', '権利譲渡'), 0)}个为权利转让。")
        merged = (f"项目数不足{MIN_GROUP}个的电压（{'、'.join(_zh_label('volt', v) for v in x['vmerged'])}）合并为“其他”。"
                  if x["vmerged"] else "")
        return f"""<section class="md" id="voltage-structure"><div class="container">
  <div class="section-label">电压×取得方式</div>
  <h2 class="md-h">电压与取得方式的组合</h2>
  <p class="md-lead">按电压统计，通过权利取得、由买方自行建设的项目（权利转让）与以建成状态交付的项目（完工交付）各有多少。{say}</p>
  <div class="md-scroll"><table class="md-t"><caption>按电压类别与取得方式组合统计的项目数（全部{x['n']}个）</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">统计全部{x['n']}个项目。{merged}取得方式尚未确定的项目标为“待确认”。</p>
</div></section>
"""
    if J:
        say = ""
        if hv and ehv:
            say = (f"高圧は{hv}件のうち{x['cross'].get(('高圧', '完成渡し'), 0)}件が完成渡し、"
                   f"特別高圧は{ehv}件のうち{x['cross'].get(('特別高圧', '権利譲渡'), 0)}件が権利譲渡です。")
        merged = f"件数が{MIN_GROUP}件未満の電圧（{_list_ja(x['vmerged'])}）は「その他」にまとめました。" if x["vmerged"] else ""
        return f"""<section class="md" id="voltage-structure"><div class="container">
  <div class="section-label">電圧×取得の形</div>
  <h2 class="md-h">電圧と取得の形の組み合わせ</h2>
  <p class="md-lead">電圧ごとに、権利で買って自分で建てる案件（権利譲渡）と、建った状態で受け取る案件（完成渡し）がどれだけあるかです。{say}</p>
  <div class="md-scroll"><table class="md-t"><caption>電圧区分と取得の形の組み合わせごとの件数（全{x['n']}件）</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">全{x['n']}件を数えています。{merged}取得の形がまだ決まっていない案件は「確認中」です。</p>
</div></section>
"""
    say = ""
    if hv and ehv:
        say = (f" Of {hv} high-voltage projects, {x['cross'].get(('高圧', '完成渡し'), 0)} are completed-build handovers; "
               f"of {ehv} extra-high-voltage projects, {x['cross'].get(('特別高圧', '権利譲渡'), 0)} are transfers of rights.")
    merged = (f" Voltage classes with fewer than {MIN_GROUP} projects ({', '.join(_en_label('volt', v) for v in x['vmerged'])}) are combined as &ldquo;Other&rdquo;."
              if x["vmerged"] else "")
    return f"""<section class="md" id="voltage-structure"><div class="container">
  <div class="section-label">Voltage × structure</div>
  <h2 class="md-h">Voltage class and structure combined</h2>
  <p class="md-lead">For each voltage class, how many projects are sold as development rights (the buyer builds) and how many as completed-build handovers.{say}</p>
  <div class="md-scroll"><table class="md-t"><caption>Projects by voltage class and structure (all {x['n']} projects)</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">All {x['n']} projects are counted.{merged} &ldquo;Under review&rdquo; means the structure is not yet fixed.</p>
</div></section>
"""


def section_size(x, lang):
    J = lang == "ja"
    n, k = x["n"], x["n_mw"]
    pairs = [((ja if J else (_zh_label("size", ja) if lang == "zh" else en)), x["size"].get(ja, 0)) for _, _, ja, en in SIZE_BINS]
    if lang == "zh":
        med = "；".join(f"{_vl(v, lang)}为{_g(m)}MW（{c}个）" for v, m, c in x["size_med"])
        return f"""<section class="md" id="size"><div class="container">
  <div class="section-label">规模</div>
  <h2 class="md-h">按规模分类（输出功率 MW）</h2>
  <p class="md-lead">将有输出功率（MW）数值的{k}个项目按规模分类（全部{n}个项目中有{n - k}个没有该数值，未计入）。{f"中位数：{med}。" if med else ""}</p>
  <div class="md-grid"><div>{bar_rows(pairs, k, lang="zh")}</div></div>
  <p class="md-note">占比为占有数值的{k}个项目的比例。中位数仅列出项目数不少于{MIN_GROUP}个的电压。</p>
</div></section>
"""
    if J:
        med = "、".join(f"{_vl(v, lang)}が{_g(m)}MW（{c}件）" for v, m, c in x["size_med"])
        return f"""<section class="md" id="size"><div class="container">
  <div class="section-label">規模</div>
  <h2 class="md-h">規模の区分（出力 MW）</h2>
  <p class="md-lead">出力（MW）の値がある{k}件を、規模で分けました（全{n}件のうち{n - k}件は値が無く、数えていません）。{f"中央値は、{med}です。" if med else ""}</p>
  <div class="md-grid"><div>{bar_rows(pairs, k)}</div></div>
  <p class="md-note">割合は値のある{k}件に対する割合です。中央値は、件数が{MIN_GROUP}件以上の電圧だけを出しています。</p>
</div></section>
"""
    med = "; ".join(f"{_vl(v, lang).lower()} {_g(m)} MW ({c} projects)" for v, m, c in x["size_med"])
    return f"""<section class="md" id="size"><div class="container">
  <div class="section-label">Size</div>
  <h2 class="md-h">Projects by size (MW)</h2>
  <p class="md-lead">The {k} projects with a capacity value, grouped by size ({n - k} of the {n} projects have no value and are not counted).{f" Median size: {med}." if med else ""}</p>
  <div class="md-grid"><div>{bar_rows(pairs, k, lang="en")}</div></div>
  <p class="md-note">Shares are of the {k} projects with a value. Medians are shown only for voltage classes with at least {MIN_GROUP} projects.</p>
</div></section>
"""


def section_lead_by_scheme(x, s, lang):
    J = lang == "ja"
    n, k = x["n"], x["n_lead"]
    if not x["lead_s"]:
        return ""
    h1_, h2_, h3_ = {"ja": ("取得の形", "月数のある件", "中央値"), "en": ("Structure", "Projects with a figure", "Median"),
                     "zh": ("取得方式", "有月数的项目", "中位数")}[lang]
    head = [h1_, h2_, h3_] + [(ja if J else (_zh_label("band", ja) if lang == "zh" else en)) for ja, en in LEAD_BANDS]
    unit_m = {"ja": "か月", "en": " months", "zh": "个月"}[lang]
    body = "".join(
        f'<tr><th scope="row">{_esc(_sl(r["k"], lang))}</th><td class="n">{r["n"]}</td><td class="n">{_g(r["med"])}{unit_m}</td>'
        + "".join(f'<td class="n">{r["bands"].get(ja, 0)}</td>' for ja, _ in LEAD_BANDS) + "</tr>" for r in x["lead_s"])
    if J:
        vmed = "、".join(f"{_vl(r['k'], lang)}が{_g(r['med'])}か月（{r['n']}件）" for r in x["lead_v"])
        other = f"月数のある件が{MIN_GROUP}件未満の取得の形（{x['lead_s_other']}件）は表に出していません。" if x["lead_s_other"] else ""
        return f"""<section class="md" id="lead-structure"><div class="container">
  <div class="section-label">連系までの月数×取得の形</div>
  <h2 class="md-h">連系までの月数を、取得の形ごとに</h2>
  <p class="md-lead">接続検討回答書に書かれた「連系までにかかる月数」がある{k}件を、取得の形ごとに数えました（全{n}件のうち{n - k}件は月数が無く、数えていません）。{f"電圧で分けると、中央値は{vmed}です。" if vmed else ""}</p>
  <div class="md-scroll"><table class="md-t"><caption>取得の形ごとの、回答書の連系までの月数（中央値と区分ごとの件数・月数のある{k}件）</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">月数は回答書の記載のままで、起点（工事費負担金の入金からなど）が書かれているのは{k - s['basis'].get('unspecified', 0)}件です（内訳は上の「月数の起点」）。運転開始の予定日から数えた月数ではありません。{other}</p>
</div></section>
"""
    if lang == "zh":
        vmed = "；".join(f"{_vl(r['k'], lang)}为{_g(r['med'])}个月（{r['n']}个）" for r in x["lead_v"])
        other = f"有月数的项目不足{MIN_GROUP}个的取得方式（{x['lead_s_other']}个）未列入表中。" if x["lead_s_other"] else ""
        return f"""<section class="md" id="lead-structure"><div class="container">
  <div class="section-label">并网所需月数×取得方式</div>
  <h2 class="md-h">按取得方式看并网所需月数</h2>
  <p class="md-lead">将接入系统研究答复书中写明“并网所需月数”的{k}个项目，按取得方式统计（全部{n}个项目中有{n - k}个没有月数，未计入）。{f"按电压区分，中位数为：{vmed}。" if vmed else ""}</p>
  <div class="md-scroll"><table class="md-t"><caption>答复书所载并网所需月数，按取得方式统计（中位数与各区间项目数，有月数的{k}个项目）</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">月数以答复书的记载为准，其中写明起点（如自并网工程费分摊款支付起算）的有{k - s['basis'].get('unspecified', 0)}个（明细见上方“月数的起点”）。这不是自预计投运日起算的月数。{other}</p>
</div></section>
"""
    vmed = "; ".join(f"{_vl(r['k'], lang).lower()} {_g(r['med'])} months ({r['n']} projects)" for r in x["lead_v"])
    other = (f" Structures with fewer than {MIN_GROUP} figures ({x['lead_s_other']} project{'' if x['lead_s_other'] == 1 else 's'}) are not shown."
             if x["lead_s_other"] else "")
    return f"""<section class="md" id="lead-structure"><div class="container">
  <div class="section-label">Months to connection × structure</div>
  <h2 class="md-h">Months to grid connection, by structure</h2>
  <p class="md-lead">The {k} projects whose grid connection study answer states the months needed to connect, counted by structure ({n - k} of the {n} projects have no figure and are not counted).{f" By voltage class, the median is {vmed}." if vmed else ""}</p>
  <div class="md-scroll"><table class="md-t"><caption>Months to grid connection stated in the utility&rsquo;s answer, by structure (median and counts per band, {k} projects with a figure)</caption><thead><tr>{_ths(head)}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">The months are as written in the utility&rsquo;s answer; {k - s['basis'].get('unspecified', 0)} of them state a start point (such as payment of the grid construction cost). These are not months from the planned commercial operation date.{other}</p>
</div></section>
"""


def section_needs(nd, lang):
    """買主のリクエストの条件（いま載っている件数と選択肢ごとの数だけ。買主の属性・載った日・推移は出さない）。"""
    if not nd or not nd.get("n"):
        return ""
    J = lang == "ja"
    n = nd["n"]
    blocks = []
    for k, ja, en in NEEDS_FIELDS:
        pairs, unset, n_set = needs_pairs(nd, k)
        if not J:
            tr, fb = (needs_zh, "其他选项") if lang == "zh" else (needs_en, "Other options")
            agg = Counter()
            for v, c in pairs:
                agg[tr(v) or fb] += c
            order = []
            for v, _ in pairs:
                lab = tr(v) or fb
                if lab not in order:
                    order.append(lab)
            pairs = [(lab, agg[lab]) for lab in order]
        if unset:
            pairs = pairs + [({"ja": "指定なし", "en": "Not specified", "zh": "未指定"}[lang], unset)]
        blocks.append(f'<div>{H3}{_esc(ja if J else (NEEDS_ZH_FIELD[k] if lang == "zh" else en))}</h3>{bar_rows(pairs, n, lang=lang)}</div>')
    asof = nd.get("asOf", "")
    if lang == "zh":
        return f"""<section class="md" id="buyer-requests"><div class="container">
  <div class="section-label">买方的需求</div>
  <h2 class="md-h">买方目前的需求条件（{n}条）</h2>
  <p class="md-lead">蓄电所市场上，买方发布的<a href="{NEEDS_PAGE_EN}" target="_top">买方需求</a>（买方自行发布的想买项目的条件，英文页面）目前有{n}条，下面按选项统计各条件的数量。可用来大致判断您想出售的项目是否符合买方的条件。</p>
  <div class="md-grid">{"".join(blocks)}</div>
  <p class="md-note">由于仅有{n}条，不列出随时间的变化（走势）；也不公布买方公司的属性与发布日期。希望的区域可多选，因此按累计数统计，占比为占{n}条需求的比例。选择次数不足{NEEDS_MIN}次的选项合并为“其他选项”，未填写条件的需求计入“未指定”。每天早上根据蓄电所市场的公开一览重新统计（条数最后变动的日期：<time datetime="{_esc(asof)}">{_esc(asof)}</time>）。</p>
</div></section>
"""
    if J:
        return f"""<section class="md" id="buyer-requests"><div class="container">
  <div class="section-label">買主のリクエスト</div>
  <h2 class="md-h">いま載っている買主のリクエストの条件（{n}件）</h2>
  <p class="md-lead">蓄電所マーケットの<a href="{NEEDS_PAGE}" target="_top">買主のリクエスト</a>（買いたい案件の条件を、買主が載せたもの）に、いま載っている{n}件の条件を、選択肢ごとに数えました。売りたい案件が条件に合うかの見当付けにお使いください。</p>
  <div class="md-grid">{"".join(blocks)}</div>
  <p class="md-note">{n}件と少ないため、増え方（推移）は出していません。買主の会社の属性と、載った日も出していません。求めるエリアは1件で複数を選べるので延べの数で、割合は{n}件に対する割合です。{NEEDS_MIN}件未満の選択肢は「その他の選択肢」にまとめ、条件を書いていないリクエストは「指定なし」にしました。毎朝、蓄電所マーケットの公開の一覧から数え直しています（件数が最後に変わった日: <time datetime="{_esc(asof)}">{_esc(asof)}</time>）。</p>
</div></section>
"""
    return f"""<section class="md" id="buyer-requests"><div class="container">
  <div class="section-label">Buyer requests</div>
  <h2 class="md-h">What buyers are asking for now ({n} requests)</h2>
  <p class="md-lead">The conditions in the {n} <a href="{NEEDS_PAGE_EN}" target="_top">buyer requests</a> now listed on Chikudensho Market (conditions that buyers post for projects they want to buy), counted by option.</p>
  <div class="md-grid">{"".join(blocks)}</div>
  <p class="md-note">With only {n} requests, no trend over time is shown, and neither the buyers&rsquo; company profiles nor the dates posted are published. A request may name several grid areas, so area counts can add up to more than {n}; shares are of the {n} requests. Options chosen fewer than {NEEDS_MIN} times are combined as &ldquo;Other options&rdquo;; requests that leave a field blank are &ldquo;Not specified&rdquo;. Recounted every morning from the public list on Chikudensho Market (counts last changed: <time datetime="{_esc(asof)}">{_esc(asof)}</time>).</p>
</div></section>
"""


def section_download(lang, generated, has_weekly, has_needs, name, url, extra=""):
    J = lang == "ja"
    c = CSV if J else CSV_EN
    if J:
        items = [(c["summary"], "集計（CSV）", "管内・都道府県（上位10）・電圧・取得の形・進み具合・電圧×取得の形・規模・連系までの月数・運転開始の予定・掲載月")]
        if has_weekly:
            items.append((c["weekly"], "週ごとの推移（CSV）", "週ごとの件数・合計出力・電圧と取得の形の内訳・新しく載った件"))
        if has_needs:
            items.append((c["needs"], "買主のリクエストの条件（CSV）", "いま載っている件数と、選択肢ごとの数"))
        items.append(("/projects.json", "公開の一覧（JSON）", "案件ごとの公開項目（管内・県・電圧・規模・進み具合・取得の形・連系の見込み）"))
        lis = "".join(f'<li><a href="{h}"{" download" if h.endswith(".csv") else ""}>{_esc(t)}</a><small>{_esc(d)}</small></li>' for h, t, d in items)
        return f"""<section class="md" id="download"><div class="container">
  <div class="section-label">ダウンロード・引用</div>
  <h2 class="md-h">データのダウンロードと、引用のしかた</h2>
  <p class="md-lead">この頁の集計は CSV でも取れます（UTF-8・BOM 付き）。毎朝、頁と同じデータから作り直しています。価格・案件名・所在地は入っていません。</p>
  <ul class="md-dl">{lis}</ul>
  {cite_html("ja", name, url, generated, extra)}
</div></section>
"""
    if lang == "zh":
        items = [(c["summary"], "汇总表（CSV）", "分区·都道府县（前10）·电压·取得方式·进展·电压×取得方式·规模·并网所需月数·预计投运·上线月份（列名与分类为英文）")]
        if has_weekly:
            items.append((c["weekly"], "每周变化（CSV）", "每周的项目数·合计输出功率·电压与取得方式明细·新增项目（列名为英文）"))
        if has_needs:
            items.append((c["needs"], "买方需求条件（CSV）", "目前的需求条数与各选项的数量（列名与选项为英文）"))
        items.append(("/projects.json", "公开一览（JSON）", "各项目的公开字段（分区·县·电压·规模·进展·取得方式·并网预期；标签为日文）"))
        lis = "".join(f'<li><a href="{h}"{" download" if h.endswith(".csv") else ""}>{_esc(t)}</a><small>{_esc(d)}</small></li>' for h, t, d in items)
        return f"""<section class="md" id="download"><div class="container">
  <div class="section-label">下载与引用</div>
  <h2 class="md-h">数据下载与引用方法</h2>
  <p class="md-lead">本页的汇总也可下载为 CSV（UTF-8，带 BOM）。每天早上依据与本页相同的数据重新生成。CSV 的列名与分类名为英文版（数字与本页一致）。不含价格、项目名称与所在地。</p>
  <ul class="md-dl">{lis}</ul>
  {cite_html("zh", name, url, generated, extra)}
</div></section>
"""
    items = [(c["summary"], "Summary tables (CSV)", "Grid area, prefecture (top 10), voltage, structure, status, voltage × structure, size, months to connection, planned COD, month first listed")]
    if has_weekly:
        items.append((c["weekly"], "Weekly figures (CSV)", "Projects and total MW per week, by voltage class and structure, new listings"))
    if has_needs:
        items.append((c["needs"], "Buyer request conditions (CSV)", "Requests now listed and counts per option"))
    items.append(("/projects.json", "Public list (JSON)", "Public fields per project (grid area, prefecture, voltage, size, status, structure, expected COD; labels in Japanese)"))
    lis = "".join(f'<li><a href="{h}"{" download" if h.endswith(".csv") else ""}>{_esc(t)}</a><small>{_esc(d)}</small></li>' for h, t, d in items)
    return f"""<section class="md" id="download"><div class="container">
  <div class="section-label">Download and citation</div>
  <h2 class="md-h">Download the data, and how to cite it</h2>
  <p class="md-lead">The tables on this page are also available as CSV (UTF-8 with BOM), rebuilt every morning from the same data. No prices, project names or sites are included.</p>
  <ul class="md-dl">{lis}</ul>
  {cite_html("en", name, url, generated, extra)}
</div></section>
"""


def variables_ja():
    P = lambda n, u=None: {"@type": "PropertyValue", "name": n, **({"unitText": u} if u else {})}  # noqa: E731
    return [P("販売中の案件の件数", "件"), P("合計出力", "MW"), P("合計容量", "MWh"), P("管内（一般送配電事業者の供給区域）"), P("都道府県"),
            P("電圧区分（高圧・特別高圧・低圧）"), P("取得の形（権利譲渡・完成渡し）"), P("進み具合（接続検討回答済・負担金確定・連系済）"),
            P("規模の区分", "MW"), P("連系までの月数（接続検討回答書の記載・中央値と区分）", "か月"), P("運転開始の予定（年度・半期）"),
            P("掲載月"), P("週ごとの件数と合計出力", "件・MW")]


def variables_en():
    P = lambda n, u=None: {"@type": "PropertyValue", "name": n, **({"unitText": u} if u else {})}  # noqa: E731
    return [P("Number of projects listed for sale", "projects"), P("Total capacity", "MW"), P("Total energy", "MWh"),
            P("Grid area (transmission and distribution operator)"), P("Prefecture"), P("Voltage class"),
            P("Structure (transfer of rights or completed-build handover)"), P("Status"), P("Size band", "MW"),
            P("Months to grid connection stated in the utility answer (median and bands)", "months"),
            P("Planned commercial operation (fiscal half-year)"), P("Month first listed"), P("Projects and total MW per week", "projects, MW")]


def variables_zh():
    P = lambda n, u=None: {"@type": "PropertyValue", "name": n, **({"unitText": u} if u else {})}  # noqa: E731
    return [P("在售项目数", "个"), P("合计输出功率", "MW"), P("合计容量", "MWh"), P("分区（一般输配电企业的供电区域）"), P("都道府县"),
            P("电压类别（高压·特别高压·低压）"), P("取得方式（权利转让·完工交付）"), P("进展（已取得接入系统研究答复·并网工程费分摊已确定·已并网）"),
            P("规模区间", "MW"), P("并网所需月数（接入系统研究答复书所载，中位数与区间）", "个月"), P("预计投运（财年上下半期）"),
            P("上线月份"), P("每周项目数与合计输出功率", "个·MW")]


def needs_dataset(nd, lang, page_url):
    if not nd or not nd.get("n"):
        return None
    J = lang == "ja"
    c = CSV if J else CSV_EN
    P = lambda n: {"@type": "PropertyValue", "name": n, "unitText": "件" if J else ("条" if lang == "zh" else "requests")}  # noqa: E731
    if lang == "zh":
        return {"@context": "https://schema.org", "@type": "Dataset", "@id": page_url + "#buyer-requests-dataset",
                "name": "蓄电所市场的买方需求条件（各选项的数量）",
                "description": (f"买方在蓄电所市场上发布的、想购买的电网侧储能（蓄电所）项目的条件，对目前的{nd['n']}条需求按选项统计的结果："
                                "购买方式、电压、希望的区域、希望的投运时间、电力手续阶段。不含买方属性、发布日期与走势。"),
                "url": page_url + "#buyer-requests", "inLanguage": "zh-CN", "creator": ZH_ORG, "publisher": ZH_ORG, "isAccessibleForFree": True,
                "isBasedOn": NEEDS_PAGE_EN, "spatialCoverage": {"@type": "Place", "name": "日本"},
                "variableMeasured": [P(NEEDS_ZH_FIELD[k]) for k, _, _ in NEEDS_FIELDS],
                "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + c["needs"],
                                  "name": "买方需求条件（CSV）"}]}
    return {"@context": "https://schema.org", "@type": "Dataset", "@id": page_url + "#buyer-requests-dataset",
            "name": "蓄電所マーケットの買主のリクエストの条件（選択肢ごとの数）" if J else "Buyer request conditions on Chikudensho Market (counts per option)",
            "description": (f"蓄電所マーケットに買主が載せた、買いたい系統用蓄電池（蓄電所）の案件の条件を、いま載っている{nd['n']}件について選択肢ごとに数えたもの。"
                            "買い方・電圧・求めるエリア・運転開始の希望・電力の手続き。買主の属性・載った日・推移は含まない。" if J else
                            f"Conditions that buyers have posted on Chikudensho Market for grid-scale battery storage projects they want to buy, counted by option for the {nd['n']} requests now listed: "
                            "purchase structure, voltage, grid areas, wanted operation date and grid-process stage. No buyer profiles, posting dates or trends."),
            "url": page_url + "#buyer-requests", "inLanguage": lang, "creator": ORG if J else EN_ORG, "publisher": ORG if J else EN_ORG, "isAccessibleForFree": True,
            "isBasedOn": NEEDS_PAGE if J else NEEDS_PAGE_EN, "spatialCoverage": {"@type": "Place", "name": "日本" if J else "Japan"},
            "variableMeasured": [P(ja if J else en) for _, ja, en in NEEDS_FIELDS],
            "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + c["needs"],
                              "name": "買主のリクエストの条件（CSV）" if J else "Buyer request conditions (CSV)"}]}


# ---------------------------------------------------------------- ページ
def render_market(ps, today, generated, weekly=(), nd=None):
    s = stats(ps, today)
    x = extra_stats(ps)
    weekly = list(weekly)
    path = "/market-data"
    title = f"系統用蓄電池の売り案件 市場データ｜管内別の件数・規模・連系の見込み（{s['n']}件・毎朝更新）｜サイエンスエックス"
    desc = (f"当社が扱う系統用蓄電池（蓄電所）の売り案件{s['n']}件・合計{s['mw']:,}MWを、管内別・都道府県別・電圧別・取得の形・"
            f"連系の見込み・回答書の工期で集計。接続検討の回答が出た案件だけ。毎朝更新。価格と資料は蓄電所マーケットで（無料登録）。")
    area_pairs = [(f"{a}（{nm}）", s["area"].get(a, 0)) for a, _, nm in AREAS if s["area"].get(a)]
    other_areas = [(a, n) for a, n in s["area"].items() if a not in {x[0] for x in AREAS}]
    area_pairs += [(a, n) for a, n in other_areas]
    half_pairs = sorted(s["half"].items())
    band_order = ["6か月以内", "7〜12か月", "13〜24か月", "25か月以上"]
    band_pairs = [(b, s["bands"][b]) for b in band_order if s["bands"].get(b)]
    basis_label = {"payment": "工事費負担金の入金から", "apply": "接続契約の申込みから", "contract": "ご契約から", "unspecified": "起点の記載なし（回答書の記載のまま）"}
    basis_pairs = [(basis_label.get(k, k), v) for k, v in s["basis"].most_common()]
    month_rows = "".join(f'<tr><th scope="row"><time datetime="{_esc(m)}">{_esc(m)}</time></th><td class="n">{n}</td></tr>' for m, n in s["first_seen"])
    pref_rows = "".join(f'<tr><th scope="row">{_esc(p)}</th><td class="n">{n}</td></tr>' for p, n in s["pref"].most_common(10))
    area_table = "".join(
        f'<tr><th scope="row"><a href="/projects-{slug}">{_esc(a)}（{_esc(nm)}）</a></th><td class="n">{s["area"].get(a, 0)}</td>'
        f'<td class="n">{s["area_mw"].get(a, 0):,}</td></tr>' for a, slug, nm in AREAS if s["area"].get(a))
    n_mw = sum(1 for p in ps if _num(p.get("mw")))
    needs_ld = needs_dataset(nd, "ja", BASE + path)
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "ja", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/", "name": "ScienceX"}, "publisher": ORG}),
        ld({"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset",
            "name": "系統用蓄電池の売り案件 市場データ（サイエンスエックス観測）",
            "description": ("系統用蓄電池（蓄電所）の売り案件の件数・規模・電圧区分・取得の形・連系の見込み・回答書の工期を、管内別・都道府県別に集計したデータ。"
                            "電圧×取得の形・規模の区分・連系までの月数の取得の形別と、週ごとの推移を含む。接続検討の回答が出た案件のみ。"
                            "価格・単価・負担金の額・案件名・地番・売主は含まない。値のある件だけの集計は母数を併記。" + GROWTH_NOTE + "毎朝更新。"),
            "url": BASE + path, "inLanguage": "ja", "creator": ORG, "publisher": ORG, "isAccessibleForFree": True,
            "dateModified": generated, "temporalCoverage": f"2026-06/{generated[:7]}",
            "spatialCoverage": {"@type": "Place", "name": "日本（9電力管内）"},
            "keywords": ["系統用蓄電池", "蓄電所", "売り案件", "市場データ", "連系の見込み", "工事費負担金", "権利譲渡", "完成渡し"],
            "measurementTechnique": "当社が蓄電所マーケットに載せた売り案件の公開項目（projects.json）を、毎朝数え直した集計",
            "variableMeasured": variables_ja(),
            "creditText": f"出典: サイエンスエックス株式会社『系統用蓄電池の売り案件 市場データ』{BASE}{path}",
            "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV["summary"], "name": "集計（CSV）"}]
            + ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV["weekly"], "name": "週ごとの推移（CSV）"}] if len(weekly) >= 2 else [])
            + [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/projects.json", "name": "公開の一覧（JSON）"}],
            "mainEntityOfPage": BASE + path}),
        ld(crumbs([("ホーム", BASE + "/"), ("案件一覧", BASE + "/projects"), ("売り案件の市場データ", BASE + path)])),
    ] + ([ld(needs_ld)] if needs_ld else []))
    body = f"""{nav_crumbs([("ホーム", "/"), ("案件一覧", "/projects"), ("売り案件の市場データ", path)])}
<section class="hero"><div class="container">
  <div class="section-label">毎朝更新・当社観測</div>
  <h1>系統用蓄電池の売り案件 市場データ</h1>
  <p>当社が扱う売り案件{s['n']}件を、管内・都道府県・電圧・取得の形・連系の見込み・回答書の工期で数えました。どの管内に何件あり、いつ連系する見込みで、権利で買える案件と完成渡しの案件がどれだけあるか。案件を探す前の見当付けと、売る前の相場観（件数の分布）にお使いください。<time datetime="{_esc(generated)}">{_esc(generated)}</time> 時点です。集計は <a href="#download">CSV</a> でも取れます（<a href="/en/market-data" hreflang="en">English</a>）。</p>
  <div class="kpi">
    <div><b>{s['n']}件</b><span>販売中の案件</span></div>
    <div><b>{s['mw']:,}MW</b><span>合計出力（{s['mwh']:,}MWh）</span></div>
    <div><b>{len(s['pref'])}都道府県</b><span>{len(s['area'])}管内</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}件</b><span>特別高圧（おおむね10MW以上）</span></div>
    <div><b>{s['new14']}件</b><span>この{NEW_DAYS}日の新着</span></div>
  </div>
  <p class="md-note" style="margin-top:14px">{NOTE_SCOPE}</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">エリア別</div>
  <h2 class="md-h">管内別の件数と規模</h2>
  <p class="md-lead">一般送配電事業者の管内ごとの件数です。管内名を押すと、その管内の案件一覧に移ります。</p>
  <div class="md-grid">
    <div>{bar_rows(area_pairs, s['n'])}</div>
    <div><table class="md-t"><caption>管内別の件数と合計出力（合計MWは出力の値がある{n_mw}件の合計）</caption><thead><tr>{_ths(["管内", "件数", "合計MW"])}</tr></thead><tbody>{area_table}</tbody></table></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">都道府県別</div>
  <h2 class="md-h">都道府県別（上位10）</h2>
  <p class="md-lead">案件の多い都道府県です。{len(s['pref'])}都道府県に案件があります。</p>
  <table class="md-t"><caption>都道府県別の件数（上位10）</caption><thead><tr>{_ths(["都道府県", "件数"])}</tr></thead><tbody>{pref_rows}</tbody></table>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">電圧・買い方・手続き</div>
  <h2 class="md-h">電圧区分・取得の形・進み具合</h2>
  <p class="md-lead">高圧は2MW級が中心で、特別高圧はおおむね10MW以上です。取得の形は、権利で買って自分で建てる「権利譲渡」と、建った状態で受け取る「完成渡し」に分かれます。進み具合は、接続検討の回答までか、契約申込みの本回答まで進んで工事費負担金が確定しているか、連系済みかです。</p>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">電圧区分</h3>{bar_rows(s['volt'].most_common(), s['n'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">取得の形</h3>{bar_rows(s['scheme'].most_common(), s['n'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">進み具合</h3>{bar_rows(s['status'].most_common(), s['n'])}</div>
  </div>
</div></section>
{section_voltage_scheme(x, "ja")}{section_size(x, "ja")}
<section class="md"><div class="container">
  <div class="section-label">連系の時期</div>
  <h2 class="md-h">連系の見込み</h2>
  <p class="md-lead">運転開始の予定が決まっている案件は年度の上期・下期で、決まっていない案件は接続検討回答書に書かれた「連系までにかかる月数」で数えました。予定が決まっているのは{s['ym_known']}件、予定は決まっていないが月数が分かるのは{s['lead_only']}件、時期を確認中が{s['undecided'] - len([1 for p in ps if not p.get('live') and not (p.get('codYm') and p['codYm'] >= today.strftime('%Y-%m')) and isinstance(p.get('leadMonths'), (int, float))])}件です。回答書に月数が書かれているのは、予定の決まっている件も合わせて{len(s['lead'])}件で、「回答書の工期」の図はこの{len(s['lead'])}件を数えています。月数は回答書の記載のままで、起点（工事費負担金の入金からなど）が書かれているのは{len(s['lead']) - s['basis'].get('unspecified', 0)}件です。</p>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">運転開始の予定（年度・半期）</h3>{bar_rows(half_pairs, s['ym_known'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">回答書の工期（連系までの月数）{f'　中央値 {s["lead_median"]}か月' if s['lead_median'] else ''}</h3>{bar_rows(band_pairs, len(s['lead']))}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">月数の起点</h3>{bar_rows(basis_pairs, len(s['lead']))}</div>
  </div>
</div></section>
{section_lead_by_scheme(x, s, "ja")}
{weekly_section_ja(weekly, generated)}
<section class="md"><div class="container">
  <div class="section-label">新着</div>
  <h2 class="md-h">掲載の推移</h2>
  <p class="md-lead">月ごとに一覧へ載せた件数です。売却済み・売り止めで外した案件は含みません。{GROWTH_NOTE}</p>
  <table class="md-t"><caption>掲載月ごとの件数（件数のある月の新しい6つまで・いま販売中の案件）</caption><thead><tr>{_ths(["掲載月", "件数"])}</tr></thead><tbody>{month_rows}</tbody></table>
</div></section>
{section_needs(nd, "ja")}
{section_download("ja", generated, len(weekly) >= 2, bool(nd and nd.get("n")), "系統用蓄電池の売り案件 市場データ", BASE + path,
                  '<p>数字の読み方は <a href="/column-project-price">蓄電所は、いくらで買えるのか</a>（取得価格の中央値）と <a href="/column-study-reply">接続検討回答書を毎日読む当社が、最初に見る6か所</a> に。</p>')}
{CTA}{FOOTER}
</body>
</html>
"""
    h = head(title, desc, path, jsonld)
    ja_alt = f'<link rel="alternate" hreflang="ja" href="{BASE}{path}">'
    h = h.replace(ja_alt, ja_alt + f'\n<link rel="alternate" hreflang="en" href="{BASE}/en/market-data">'
                  f'\n<link rel="alternate" hreflang="zh-CN" href="{BASE}/zh-market-data">', 1)
    return h + body


def render_area(ps_all, area, slug, operator, today, generated):
    ps = [p for p in ps_all if p.get("area") == area]
    s = stats(ps, today)
    path = f"/projects-{slug}"
    n = s["n"]
    title = f"{area}電力管内（{operator}）の系統用蓄電池 売り案件 {n}件｜高圧・特別高圧・連系の見込み｜サイエンスエックス"
    if area in ("東京", "中部", "九州", "関西", "中国", "東北", "北海道", "北陸", "四国"):
        title = f"{operator}管内の系統用蓄電池 売り案件 {n}件｜連系の見込み・取得の形｜サイエンスエックス"
    desc = (f"{operator}管内（{area}エリア）で当社が扱う系統用蓄電池（蓄電所）の売り案件{n}件・合計{s['mw']:,}MW。"
            f"都道府県・電圧・規模・連系の見込み・進み具合・取得の形まで登録なしで公開。価格と資料は蓄電所マーケットで（無料登録）。接続検討の回答が出た案件だけ。毎朝更新。")
    robots = "index,follow,max-image-preview:large" if n >= MIN_INDEX else "noindex,follow"
    pref_pairs = s["pref"].most_common()
    half_pairs = sorted(s["half"].items())
    band_order = ["6か月以内", "7〜12か月", "13〜24か月", "25か月以上"]
    band_pairs = [(b, s["bands"][b]) for b in band_order if s["bands"].get(b)]
    items = [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/projects#p-{p.get('id')}",
              "name": f"{p.get('id')} {p.get('pref') or ''} {p.get('voltage') or ''} {p.get('mw') or ''}MW"}
             for i, p in enumerate(sorted(ps, key=lambda p: cod_sort_key(p, today.strftime('%Y-%m'))))]
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "ja", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/", "name": "ScienceX"}, "publisher": ORG,
            "mainEntity": {"@type": "ItemList", "numberOfItems": n, "itemListElement": items}}),
        ld(crumbs([("ホーム", BASE + "/"), ("案件一覧", BASE + "/projects"), (f"{area}電力管内", BASE + path)])),
    ])
    others = "　".join(f'<a href="/projects-{sl}">{_esc(a)}（{s_all}件）</a>'
                      for a, sl, _ in AREAS if a != area for s_all in [sum(1 for p in ps_all if p.get("area") == a)] if s_all)
    list_html = rows_html(ps, today) if ps else '<p class="md-note">いまこの管内に販売中の案件はありません。新しく載ったら、ここと <a href="/projects">案件一覧</a> に出ます。</p>'
    body = f"""{nav_crumbs([("ホーム", "/"), ("案件一覧", "/projects"), (f"{area}電力管内", path)])}
<section class="hero"><div class="container">
  <div class="section-label">登録不要・毎朝更新</div>
  <h1>{_esc(operator)}管内の系統用蓄電池 売り案件 {n}件</h1>
  <p>{_esc(area)}エリア（{_esc(operator)}管内）で当社が扱う、接続検討の回答が出た系統用蓄電池（蓄電所）の案件です。所在県・電圧・規模・連系の見込み・進み具合・取得の形までは登録なしでご覧いただけます。蓄電所マーケットの一覧では、案件名・市区町村・写真まで登録なしで見られます。価格と資料は無料登録のあとです。地番・売主は本ページでは載せていません。{_esc(generated)} 時点です。</p>
  <div class="kpi">
    <div><b>{n}件</b><span>販売中の案件</span></div>
    <div><b>{s['mw']:,}MW</b><span>合計出力（{s['mwh']:,}MWh）</span></div>
    <div><b>{s['volt'].get('高圧', 0)}件</b><span>高圧（2MW級が中心）</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}件</b><span>特別高圧（おおむね10MW以上）</span></div>
    <div><b>{s['scheme'].get('権利譲渡', 0)}件</b><span>権利譲渡（自分で建てる）</span></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">あらまし</div>
  <h2 class="md-h">{_esc(area)}エリアの案件の内訳</h2>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">都道府県</h3>{bar_rows(pref_pairs, n)}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">運転開始の予定（年度・半期）</h3>{bar_rows(half_pairs, s['ym_known'])}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">回答書の工期（連系までの月数）{f'　中央値 {s["lead_median"]}か月' if s['lead_median'] else ''}</h3>{bar_rows(band_pairs, len(s['lead']))}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">進み具合</h3>{bar_rows(s['status'].most_common(), n)}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">取得の形</h3>{bar_rows(s['scheme'].most_common(), n)}</div>
  </div>
  <p class="md-note" style="margin-top:14px">{NOTE_SCOPE} 全国の集計は <a href="/market-data">売り案件の市場データ</a> に。</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">案件</div>
  <h2 class="md-h">{_esc(operator)}管内の案件一覧（{n}件・{_esc(generated)} 更新）</h2>
  <p class="md-lead">連系が早い順です。案件番号を押すと、蓄電所マーケットのその案件の頁（登録なしで見られる公開の項目）が開きます。価格と資料は、<a href="https://dealroom.scix.co.jp/" target="_top">蓄電所マーケット</a>で無料登録のあとに見られます。</p>
  {list_html}
  <p class="md-note" style="margin-top:16px">ほかの管内: {others}</p>
</div></section>
{CTA}{FOOTER}
</body>
</html>
"""
    return head(title, desc, path, jsonld, robots) + body


# ---------------------------------------------------------------- 英語の案件一覧（en/projects.html）
# 公開してよい項目（projects.json の PUBLIC_KEYS）だけを使う。価格・住所・売主は持っていないので出せない。
EN_AREA = {"北海道": "Hokkaido", "東北": "Tohoku", "東京": "Tokyo", "中部": "Chubu", "北陸": "Hokuriku", "関西": "Kansai",
           "中国": "Chugoku", "四国": "Shikoku", "九州": "Kyushu", "沖縄": "Okinawa"}
EN_PREF = {
    "北海道": "Hokkaido", "青森県": "Aomori", "岩手県": "Iwate", "宮城県": "Miyagi", "秋田県": "Akita", "山形県": "Yamagata",
    "福島県": "Fukushima", "茨城県": "Ibaraki", "栃木県": "Tochigi", "群馬県": "Gunma", "埼玉県": "Saitama", "千葉県": "Chiba",
    "東京都": "Tokyo", "神奈川県": "Kanagawa", "新潟県": "Niigata", "富山県": "Toyama", "石川県": "Ishikawa", "福井県": "Fukui",
    "山梨県": "Yamanashi", "長野県": "Nagano", "岐阜県": "Gifu", "静岡県": "Shizuoka", "愛知県": "Aichi", "三重県": "Mie",
    "滋賀県": "Shiga", "京都府": "Kyoto", "大阪府": "Osaka", "兵庫県": "Hyogo", "奈良県": "Nara", "和歌山県": "Wakayama",
    "鳥取県": "Tottori", "島根県": "Shimane", "岡山県": "Okayama", "広島県": "Hiroshima", "山口県": "Yamaguchi",
    "徳島県": "Tokushima", "香川県": "Kagawa", "愛媛県": "Ehime", "高知県": "Kochi", "福岡県": "Fukuoka", "佐賀県": "Saga",
    "長崎県": "Nagasaki", "熊本県": "Kumamoto", "大分県": "Oita", "宮崎県": "Miyazaki", "鹿児島県": "Kagoshima",
    "沖縄県": "Okinawa",
}
EN_VOLT = {"高圧": "High voltage", "特別高圧": "Extra-high voltage", "低圧": "Low voltage"}
EN_STATUS = {"接続検討回答済": "Grid connection study answered", "負担金確定": "Grid cost confirmed", "連系済": "Grid-connected"}
EN_SCHEME = {"完成渡し": "Completed-build handover", "権利譲渡": "Transfer of rights"}
EN_LEAD = {"payment": "about {n} months after grid cost payment", "apply": "about {n} months after connection application",
           "contract": "about {n} months after contract", "unspecified": "about {n} months of grid work"}
EN_COD_LABELS = [("live", "Grid-connected"), ("thisfy", "This fiscal year"), ("nextfy", "Next fiscal year"),
                 ("later", "Later"), ("lead", "Given in months"), ("tbd", "Under review")]
EN_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

EN_CSS = """
.pj-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:26px 0 0}
.pj-sum div{background:var(--white);border:1px solid var(--border);border-radius:8px;padding:14px 18px}
.pj-sum b{display:block;font-size:1.5rem;color:var(--navy);line-height:1.3}.pj-sum span{font-size:.78rem;color:var(--text-2)}
.pj-filter{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:flex-end;margin:0 0 14px}
.pj-filter label{display:flex;flex-direction:column;font-size:.76rem;color:var(--text-2);gap:4px;min-width:0}
.pj-filter select{font:inherit;font-size:.9rem;padding:8px 10px;border:1px solid #C9C9C9;border-radius:6px;background:#fff;color:var(--navy);max-width:100%}
.pj-count{font-size:.86rem;color:var(--text-2);margin-left:auto}
.pj-t{border-collapse:collapse;width:100%;font-size:.86rem}
.pj-t th,.pj-t td{border-bottom:1px solid var(--border);padding:8px 10px;text-align:left;vertical-align:top}
.pj-t th{background:var(--off-white);color:var(--text-2);font-weight:500;white-space:nowrap}
.pj-t td.n,.pj-t th.n{text-align:right;font-variant-numeric:tabular-nums}
.pj-t tr[hidden]{display:none!important}
.pj-new{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:3px;background:rgba(26,122,76,.12);color:var(--green);font-size:.7rem;font-weight:600}
.pj-none{display:none;padding:18px 0;color:var(--text-2)}
.hero.pj-hero{padding:26px 0 20px}
.pj-hero h1{font-size:clamp(1.3rem,3.2vw,1.9rem);margin-bottom:8px}
.pj-hero p.sub{font-size:.9rem;line-height:1.8;margin-bottom:14px}
.hero-btns{display:flex;flex-wrap:wrap;gap:10px}
.hb{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;font-size:.84rem;font-weight:600;text-decoration:none;border-radius:4px}
.hb-list{background:var(--navy);color:#fff}.hb-dr{background:var(--gold);color:var(--navy)}
section.pj-list{padding:20px 0 40px;border-top:none;scroll-margin-top:72px}
.pj-lock{display:inline-block;padding:4px 12px;border:1.5px solid var(--navy);border-radius:100px;color:var(--navy);font-size:.76rem;font-weight:600;text-decoration:none;white-space:nowrap}
.pj-lock:hover{background:var(--navy);color:#fff}
.pj-idlk{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.pj-reg{display:block;margin-top:5px;color:var(--text-2);font-size:.72rem;text-decoration:underline;white-space:nowrap}
.pj-t th.c-lock,.pj-t td.c-lock{background:rgba(196,154,60,.07)}
.pj-t tr.pj-band td{background:var(--navy);color:#fff;padding:9px 14px;border:none}
.pj-t tr.pj-band td span{margin-right:14px;font-size:.82rem}
.pj-band-btn{display:inline-block;padding:4px 14px;background:var(--gold);color:var(--navy);border-radius:4px;font-size:.78rem;font-weight:600;text-decoration:none;white-space:nowrap}
.pj-dr{background:var(--off-white);border:1px solid var(--border);border-radius:8px;padding:22px 24px;max-width:860px}
.pj-dr ol{margin:10px 0 18px 1.3em;font-size:.92rem;color:var(--text-2)}
@media(max-width:900px){
  .pj-t,.pj-t tbody,.pj-t tr,.pj-t td{display:block;width:100%}
  .pj-t thead{display:none}
  .pj-t tr{border:1px solid var(--border);border-radius:8px;margin-bottom:10px;padding:6px 12px}
  .pj-t td{border:none;padding:3px 0;text-align:left!important;display:flex;justify-content:space-between;gap:12px}
  .pj-t td::before{content:attr(data-l);color:var(--text-3);font-size:.78rem;flex:0 0 38%}
  .pj-count{margin-left:0;width:100%}
  .pj-filter label{flex:1 1 44%}
  .pj-filter select{width:100%}
  .pj-t td.c-lock{background:none;margin-top:6px;justify-content:flex-start;align-items:center;flex-wrap:wrap;gap:6px 14px}
  .pj-t td.c-lock::before{content:none}
  .pj-t td.c-lock .pj-reg{display:inline-block;margin-top:0}
  .pj-t tr.pj-band{border:none;padding:0;margin:0 0 10px}
  .pj-t tr.pj-band td{display:block}.pj-t tr.pj-band td::before{content:none}
  .pj-t tr.pj-band td span{display:block;margin:0 0 6px}
}
"""

EN_FOOTER = """<footer class="scix-footer">
  <div class="scix-footer-inner">
    <a href="https://www.scix.co.jp/en" class="scix-footer-logo" aria-label="ScienceX Home">
      <img width="300" height="118" src="/img/logo-white.png" alt="ScienceX — Science X Inc." loading="lazy" />
    </a>
    <hr class="scix-footer-divider" />
    <div class="scix-footer-info">
      <div class="scix-footer-company">
        <div class="company-name">Science X Inc.</div>
        8-2 Nihonbashi Koamicho, Chuo-ku, Tokyo 103-0016<br>
        BIZMARKS Nihonbashi Kayabacho<br>
        TEL: <a href="tel:+81366913484">+81 3 6691 3484</a><br>
        MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>
        <div class="representative">Shinya Nakashima, Ph.D. (Eng.), Representative Director</div>
      </div>
      <div class="scix-footer-nav" style="margin-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:10px 22px;justify-content:center;">
        <a href="/en" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Home</a>
        <a href="https://dealroom.scix.co.jp/en" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Chikudensho Market</a>
        <a href="/en/market-data" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Market Data</a>
        <a href="/en/knowledge" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Knowledge</a>
        <a href="/en/qa" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Q&amp;A</a>
        <a href="/en/glossary" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Glossary</a>
        <a href="/en/market-entry-guide" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Market Entry Guide</a>
        <a href="/en/company" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Company</a>
        <a href="/en/contact" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Contact</a>
        <a href="/en/privacy" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Privacy Policy</a>
      </div>
      <div class="scix-footer-copyright">&copy; 2025–2026 Science X Inc. All Rights Reserved.</div>
    </div>
  </div>
</footer>"""


def en_cod(p, today_ym):
    """Expected COD（連系の見込み）の英語表示。inject_stats.cod_text と同じ規則（年月が過去なら出さない）。"""
    if p.get("live"):
        return "Grid-connected"
    ym = p.get("codYm")
    ym = ym if (ym and ym >= today_ym) else None
    n = p.get("leadMonths")
    lead = EN_LEAD.get(p.get("leadBasis") or "unspecified", EN_LEAD["unspecified"]).format(n=n) if n else ""
    if ym:
        return f"{EN_MON[int(ym[5:7]) - 1]} {ym[:4]}" + (f" ({lead})" if lead else "")
    return lead or "Under review"


def render_en_projects(ps, today, generated, weekly=()):
    today_ym = today.strftime("%Y-%m")
    path = "/en/projects"
    url = BASE + path
    n = len(ps)
    mw = round(sum(p.get("mw") or 0 for p in ps))
    volt = Counter(p.get("voltage") for p in ps)
    prefs = len({p.get("pref") for p in ps if p.get("pref")})

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)

    ps = sorted(ps, key=key)
    title = "Japan Grid-Scale BESS Projects Listed | ScienceX"
    desc = (f"{n} grid-scale battery storage (BESS) projects in Japan, about {mw:,} MW. "
            "Area, voltage, size, status, expected COD. No prices. Updated daily.")
    areas = [a for a in EN_AREA if any(p.get("area") == a for p in ps)]
    area_opts = "".join(f'<option value="{_esc(a)}">{EN_AREA[a]}</option>' for a in areas)
    volt_opts = "".join(f'<option value="{_esc(v)}">{EN_VOLT[v]}</option>' for v in EN_VOLT if volt.get(v))
    scheme_opts = "".join(f'<option value="{_esc(k)}">{v}</option>' for k, v in EN_SCHEME.items() if any(p.get("scheme") == k for p in ps))
    buckets = {cod_bucket(p, today_ym) for p in ps}
    cod_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in EN_COD_LABELS if k in buckets)
    reg = "https://dealroom.scix.co.jp/en/register"

    def band():
        return ('<tr class="pj-band"><td colspan="10"><span>Project pages open without registration; the Chikudensho Market list also shows each project&rsquo;s name, city and photos. Prices, exact sites and documents follow free registration.</span>'
                f'<a class="pj-band-btn" href="{reg}" rel="nofollow" onclick="window.gtag&&gtag(\'event\',\'dr2_promo_click\',{{target:\'band_en\'}})">Register on Chikudensho Market &rarr;</a></td></tr>')

    rows = []
    for i, p in enumerate(ps, 1):
        pid = _esc(p.get("id") or "")
        m, mh = p.get("mw"), p.get("mwh")
        new = '<span class="pj-new">New</span>' if is_new(p, today) else ""
        rows.append(
            f'<tr class="pj-row" id="p-{pid}" data-area="{_esc(p.get("area") or "")}" data-volt="{_esc(p.get("voltage") or "")}" '
            f'data-scheme="{_esc(p.get("scheme") or "")}" data-cod="{cod_bucket(p, today_ym)}">'
            f'<td data-l="ID"><a class="pj-idlk" href="https://dealroom.scix.co.jp/en/catalog/{pid}">{pid}</a>{new}</td>'
            f'<td data-l="Area">{EN_AREA.get(p.get("area"), "TBC")}</td>'
            f'<td data-l="Prefecture">{EN_PREF.get(p.get("pref"), "Under review")}</td>'
            f'<td data-l="Voltage">{EN_VOLT.get(p.get("voltage"), "—")}</td>'
            f'<td class="n" data-l="MW">{f"{m:g}" if isinstance(m, (int, float)) else "—"}</td>'
            f'<td class="n" data-l="MWh">{f"{mh:g}" if isinstance(mh, (int, float)) else "—"}</td>'
            f'<td data-l="Status">{EN_STATUS.get(p.get("status"), "—")}</td>'
            f'<td data-l="Structure">{EN_SCHEME.get(p.get("scheme"), "Under review")}</td>'
            f'<td data-l="Expected COD">{_esc(en_cod(p, today_ym))}</td>'
            f'<td class="c-lock" data-l="Details"><a class="pj-lock" href="https://dealroom.scix.co.jp/en/catalog/{pid}" '
            f'onclick="window.gtag&&gtag(\'event\',\'dr2_promo_click\',{{target:\'row_en\'}})">View the project page</a>'
            f'<a class="pj-reg" href="{reg}" rel="nofollow" '
            f'onclick="window.gtag&&gtag(\'event\',\'dr2_promo_click\',{{target:\'row_register_en\'}})">Price &amp; documents (free registration)</a></td></tr>')
        if i % BAND_EVERY == 0 and i != len(ps):
            rows.append(band())
    rows.append(band())
    items = [{"@type": "ListItem", "position": i + 1, "name": f"{p.get('id')} {EN_PREF.get(p.get('pref'), '')} {EN_VOLT.get(p.get('voltage'), '')} {p.get('mw') or ''} MW".replace("  ", " ")}
             for i, p in enumerate(ps)]
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": title,
            "description": desc, "inLanguage": "en", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": "ScienceX"},
            "publisher": {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": BASE + "/en"},
            "mainEntity": {"@type": "ItemList", "numberOfItems": n, "itemListElement": items}}),
        ld(en_dataset(path, "Grid-scale battery storage projects listed for sale in Japan: counts",
                      ("Counts of the grid-scale battery storage projects ScienceX lists for sale in Japan: number of projects and total capacity "
                       "by grid area, prefecture, voltage class, structure, status and expected grid connection, and weekly figures. "
                       "Aggregate counts only; no prices, sites or sellers. " + GROWTH_NOTE_EN + " Updated every morning."),
                      generated,
                      [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["summary"], "name": "Summary tables (CSV)"}]
                      + ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["weekly"], "name": "Weekly figures (CSV)"}] if len(list(weekly)) >= 2 else []),
                      variables_en())),
        ld(crumbs([("Home", BASE + "/en"), ("Projects", url)])),
    ])
    head_html = (head(title, desc, path, jsonld)
                 .replace('<html lang="ja">', '<html lang="en">')
                 .replace(f'<link rel="alternate" hreflang="ja" href="{url}">',
                          f'<link rel="alternate" hreflang="en" href="{url}">\n<link rel="alternate" hreflang="ja" href="{BASE}/projects">')
                 .replace('content="ja_JP"', 'content="en_US"')
                 .replace(f'{BASE}/img/ogp-m.png', f'{BASE}/img/ogp-m-en.png')
                 .replace(f"<style>{CSS}</style>", f"<style>{CSS}{EN_CSS}</style>"))
    body = f"""<section class="hero pj-hero"><div class="container">
  <h1>{n} grid-scale BESS projects for sale in Japan <span style="font-size:.7em;font-weight:500;color:var(--text-2)">(high voltage {volt.get('高圧', 0)} · extra-high voltage {volt.get('特別高圧', 0)})</span></h1>
  <p class="sub">Click a project ID to open its page on Chikudensho Market (no registration). The market list also shows project names, cities and photos; prices and documents follow free registration.</p>
  <div class="hero-btns">
    <a class="hb hb-list" href="#list">View the list</a>
    <a class="hb hb-dr" href="https://dealroom.scix.co.jp/en/register" rel="nofollow" onclick="window.gtag&&gtag('event','dr2_promo_click',{{target:'hero_en'}})">Register on Chikudensho Market</a>
  </div>
</div></section>

<section class="md pj-list" id="list"><div class="container">
  <div class="pj-filter">
    <label>Area<select id="f-area"><option value="">All areas</option>{area_opts}</select></label>
    <label>Voltage<select id="f-volt"><option value="">All voltage classes</option>{volt_opts}</select></label>
    <label>Structure<select id="f-scheme"><option value="">All structures</option>{scheme_opts}</select></label>
    <label>Expected COD<select id="f-cod"><option value="">Any time</option>{cod_opts}</select></label>
    <span class="pj-count" id="pj-count" aria-live="polite">{n} of {n} projects · updated {_esc(generated)}</span>
  </div>
  <table class="pj-t" id="pj-table">
    <thead><tr><th>ID</th><th>Area</th><th>Prefecture</th><th>Voltage</th><th class="n">MW</th><th class="n">MWh</th><th>Status</th><th>Structure</th><th>Expected COD</th><th class="c-lock">Details</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>
  <p class="pj-none" id="pj-none">No listed project matches these filters.</p>
</div></section>

<section class="md" id="dealroom"><div class="container">
  <div class="section-label">Chikudensho Market</div>
  <h2 class="md-h">Detailed materials are on Chikudensho Market, after free registration</h2>
  <div class="pj-dr">
    <p class="md-lead" style="margin-bottom:6px">This list shows the prefecture only. Chikudensho Market shows the project name, prefecture and city, voltage, sale type, scale, expected start of operation, grid procedure stage, photos and how many people have viewed it, without registration. Prices, site details, technical documents and the Q&amp;A for each project follow free registration (English screens available).</p>
    <ol>
      <li>Register on Chikudensho Market (free of charge) and agree to the confidentiality undertaking on the registration page &mdash; no signed or sealed paper is needed.</li>
      <li>After registering, you can open the prices and documents for each project.</li>
    </ol>
    <a class="btn-primary" href="https://dealroom.scix.co.jp/en/register" rel="nofollow" onclick="window.gtag&&gtag('event','dr2_promo_click',{{target:'register_en'}})">Register on Chikudensho Market &rarr;</a>
    <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/contact?intent=dealroom" onclick="window.gtag&&gtag('event','dr2_promo_click',{{target:'apply_en'}})">Or apply through our contact form</a>
    <p class="md-note" style="margin-top:12px">If you prefer paper, the undertaking is also available as a PDF: <a href="/files/scix-nda-pledge-en.pdf">English</a> / <a href="/files/scix-nda-pledge.pdf">Japanese</a>.</p>
  </div>
</div></section>

{weekly_section_en(list(weekly), generated)}
<section class="md" id="about"><div class="container">
  <h2 class="md-h">About this list</h2>
  <p class="md-lead">High-voltage (~2 MW) and extra-high-voltage battery storage projects, from development rights with grid connection answers to grid-connected assets. Sorted by earliest expected COD (commercial operation date). Total: about {mw:,} MW across {prefs} prefectures. Prices, exact sites and counterparties are not published here.</p>
  <p class="md-note" style="margin-top:14px">Area = the grid area of the transmission and distribution operator (Tokyo, Chubu, Kyushu and so on). Status: &ldquo;Grid connection study answered&rdquo; means the utility has issued its answer on the connection study; &ldquo;Grid cost confirmed&rdquo; means the grid construction cost has been fixed; &ldquo;Grid-connected&rdquo; means the project is already connected. Structure: &ldquo;Completed-build handover&rdquo; or &ldquo;Transfer of rights&rdquo; (the buyer builds). Expected COD is an estimate taken from the utility&rsquo;s answer and may change. These are ScienceX&rsquo;s own listings, not statistics for the whole Japanese market.</p>
  <p class="md-lead" style="margin-top:14px">Counts by grid area, voltage class, structure, size and months to grid connection, with CSV downloads, are on <a href="/en/market-data">Market data</a>.</p>
  {cite_html("en", "Grid-scale battery storage projects listed for sale in Japan: counts", url, generated,
             f'<p>CSV: <a href="{CSV_EN["summary"]}" download>summary tables</a> &middot; <a href="{CSV_EN["weekly"]}" download>weekly figures</a> &middot; counts only, no prices or sites.</p>')}
</div></section>

<section class="cta"><div class="container">
  <h2>Looking for something specific?</h2>
  <p>Tell us the area, voltage class, size and timing you are looking for, and we will tell you which listed projects fit. Questions about the confidentiality undertaking, structure or process are welcome.</p>
  <a class="btn-primary" href="/en/contact">Contact ScienceX &rarr;</a>
  <a class="btn-secondary" target="_top" href="https://dealroom.scix.co.jp/en" data-cta="hub-end" style="display:inline-block;padding:12px 22px;margin:8px 10px 0 8px;font-size:.95rem;text-decoration:none">See projects on Chikudensho Market &rarr;</a>
</div></section>
<script>
(function(){{
  var tbody=document.querySelector('#pj-table tbody');
  var rows=[].slice.call(tbody.querySelectorAll('tr.pj-row'));
  var bandTpl=tbody.querySelector('tr.pj-band');
  var BAND_EVERY={BAND_EVERY};
  var sel={{area:document.getElementById('f-area'),volt:document.getElementById('f-volt'),scheme:document.getElementById('f-scheme'),cod:document.getElementById('f-cod')}};
  var cnt=document.getElementById('pj-count'),none=document.getElementById('pj-none');
  var tail=cnt.textContent.replace(/^\\d+ of \\d+ projects/,'');
  function apply(){{
    var shown=[];
    rows.forEach(function(r){{
      var ok=(!sel.area.value||r.dataset.area===sel.area.value)&&(!sel.volt.value||r.dataset.volt===sel.volt.value)&&(!sel.scheme.value||r.dataset.scheme===sel.scheme.value)&&(!sel.cod.value||r.dataset.cod===sel.cod.value);
      r.hidden=!ok; if(ok)shown.push(r);
    }});
    [].forEach.call(tbody.querySelectorAll('tr.pj-band'),function(b){{b.parentNode.removeChild(b);}});
    shown.forEach(function(r,i){{
      tbody.appendChild(r);
      if((i+1)%BAND_EVERY===0&&i+1!==shown.length)tbody.appendChild(bandTpl.cloneNode(true));
    }});
    if(shown.length)tbody.appendChild(bandTpl.cloneNode(true));
    cnt.textContent=shown.length+' of '+rows.length+' projects'+tail;
    none.style.display=shown.length?'none':'block';
  }}
  Object.keys(sel).forEach(function(k){{sel[k].addEventListener('change',apply);}});
}})();
</script>
{EN_FOOTER}
</body>
</html>
"""
    return head_html + body


EN_BASIS = {"payment": "From payment of the grid construction cost", "apply": "From the connection application",
            "contract": "From the contract", "unspecified": "Start point not stated (as written in the answer)"}
EN_CTA_MD = """<section class="cta"><div class="container">
  <h2>See the projects themselves on Chikudensho Market</h2>
  <p>Current listings can be browsed on Chikudensho Market without registering. Prices and documents are shown after free registration, where you agree to a confidentiality undertaking on the registration screen (no signed paper is needed).</p>
  <a class="btn-primary" href="https://dealroom.scix.co.jp/en" target="_top">Browse projects on Chikudensho Market &rarr;</a>
  <a class="btn-secondary" href="/en/contact">Contact ScienceX</a>
</div></section>
"""


def en_dataset(path, name, desc, generated, distribution, variables):
    return {"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset", "name": name, "description": desc,
            "url": BASE + path, "inLanguage": "en", "creator": EN_ORG, "publisher": EN_ORG, "isAccessibleForFree": True,
            "dateModified": generated, "temporalCoverage": f"2026-06/{generated[:7]}",
            "spatialCoverage": {"@type": "Place", "name": "Japan (9 grid areas)"},
            "keywords": ["Japan", "grid-scale battery storage", "BESS", "projects for sale", "market data", "grid connection", "COD"],
            "measurementTechnique": "Counts of the public fields of the projects ScienceX lists on Chikudensho Market (projects.json), recounted every morning",
            "variableMeasured": variables,
            "creditText": f"Source: Science X Inc., \u201c{name}\u201d, {BASE}{path}",
            "distribution": distribution, "mainEntityOfPage": BASE + path}


def en_head(title, desc, path, jsonld, ja_path):
    url = BASE + path
    return (head(title, desc, path, jsonld)
            .replace('<html lang="ja">', '<html lang="en">')
            .replace(f'<link rel="alternate" hreflang="ja" href="{url}">',
                     f'<link rel="alternate" hreflang="en" href="{url}">\n<link rel="alternate" hreflang="ja" href="{BASE}{ja_path}">'
                     f'\n<link rel="alternate" hreflang="zh-CN" href="{BASE}/zh-market-data">')
            .replace('content="ja_JP"', 'content="en_US"')
            .replace(f'{BASE}/img/ogp-m.png', f'{BASE}/img/ogp-m-en.png'))


def render_en_market(ps, today, generated, weekly=(), nd=None):
    """英語の市場データ（/en/market-data）。日本語の /market-data と同じ集計（件数・規模・月数だけ・価格なし）。"""
    s = stats(ps, today)
    x = extra_stats(ps)
    weekly = list(weekly)
    path = "/en/market-data"
    n = s["n"]
    n_mw = sum(1 for p in ps if _num(p.get("mw")))
    title = "Japan BESS Projects for Sale: Market Data | ScienceX"
    desc = (f"{n} grid-scale battery storage projects for sale in Japan, about {s['mw']:,} MW, counted by grid area, prefecture, voltage, "
            "structure, size and months to grid connection. CSV. No prices. Updated daily.")
    name = "Grid-scale battery storage projects for sale in Japan: market data"
    dist = ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["summary"], "name": "Summary tables (CSV)"}]
            + ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["weekly"], "name": "Weekly figures (CSV)"}] if len(weekly) >= 2 else [])
            + [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/projects.json", "name": "Public list (JSON)"}])
    ds_desc = ("Counts of the grid-scale battery storage projects for sale that ScienceX lists in Japan: number, capacity, voltage class, structure "
               "(transfer of rights or completed-build handover), status, expected grid connection and the months to connection stated in the utility's answer, "
               "by grid area and prefecture, with voltage × structure, size bands, months to connection by structure and weekly figures. "
               "Only projects with a grid connection study answer. No prices, unit prices, grid cost amounts, project names, sites or sellers. "
               "Tallies of values that exist state their base. " + GROWTH_NOTE_EN + " Updated every morning.")
    needs_ld = needs_dataset(nd, "en", BASE + path)
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "en", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/en", "name": "ScienceX"}, "publisher": EN_ORG}),
        ld(en_dataset(path, name, ds_desc, generated, dist, variables_en())),
        ld(crumbs([("Home", BASE + "/en"), ("Projects", BASE + "/en/projects"), ("Market data", BASE + path)])),
    ] + ([ld(needs_ld)] if needs_ld else []))
    area_pairs = [(EN_AREA.get(a, a), s["area"].get(a, 0)) for a, _, _ in AREAS if s["area"].get(a)]
    area_table = "".join(f'<tr><th scope="row">{_esc(EN_AREA.get(a, a))}</th><td class="n">{s["area"].get(a, 0)}</td>'
                         f'<td class="n">{s["area_mw"].get(a, 0):,}</td></tr>' for a, _, _ in AREAS if s["area"].get(a))
    pref_rows = "".join(f'<tr><th scope="row">{_esc(EN_PREF.get(p_, p_))}</th><td class="n">{c}</td></tr>' for p_, c in s["pref"].most_common(10))
    half_pairs = [(_en_label("half", h), c) for h, c in sorted(s["half"].items())]
    band_pairs = [(en, s["bands"][ja]) for ja, en in LEAD_BANDS if s["bands"].get(ja)]
    basis_pairs = [(EN_BASIS.get(k, k), v) for k, v in s["basis"].most_common()]
    month_rows = "".join(f'<tr><th scope="row"><time datetime="{_esc(m)}">{_esc(m)}</time></th><td class="n">{c}</td></tr>' for m, c in s["first_seen"])
    volt_pairs = [(_en_label("volt", k), v) for k, v in s["volt"].most_common()]
    scheme_pairs = [(_en_label("scheme", k), v) for k, v in s["scheme"].most_common()]
    status_pairs = [(_en_label("status", k), v) for k, v in s["status"].most_common()]
    undated = s["undecided"] - sum(1 for p in ps if not p.get("live") and not (p.get("codYm") and p["codYm"] >= today.strftime("%Y-%m")) and _num(p.get("leadMonths")))
    body = f"""{nav_crumbs([("Home", "/en"), ("Projects", "/en/projects"), ("Market data", path)])}
<section class="hero"><div class="container">
  <div class="section-label">Updated daily &middot; ScienceX listings</div>
  <h1>Japan grid-scale battery storage projects for sale: market data</h1>
  <p>The {n} projects we list, counted by grid area, prefecture, voltage class, structure, status, size and expected grid connection: where the projects are, when they are expected to connect, and how many can be bought as development rights or as completed-build handovers. As of <time datetime="{_esc(generated)}">{_esc(generated)}</time>. The tables are also available as <a href="#download">CSV</a> (<a href="/market-data" hreflang="ja">Japanese</a>).</p>
  <div class="kpi">
    <div><b>{n}</b><span>projects listed for sale</span></div>
    <div><b>{s['mw']:,} MW</b><span>total capacity ({s['mwh']:,} MWh)</span></div>
    <div><b>{len(s['pref'])}</b><span>prefectures, {len(s['area'])} grid areas</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}</b><span>extra-high voltage (roughly 10 MW and above)</span></div>
    <div><b>{s['new14']}</b><span>new in the last {NEW_DAYS} days</span></div>
  </div>
  <p class="md-note" style="margin-top:14px">These are the battery storage projects for sale that have been brought to ScienceX and cleared for listing, all with a grid connection study answer from the utility. They are ScienceX&rsquo;s own listings, not statistics for the whole Japanese market. Sites and sellers are not published (prices and documents are on Chikudensho Market after free registration). The figures are recounted every morning from the same data as the project list.</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">By grid area</div>
  <h2 class="md-h">Projects and capacity by grid area</h2>
  <p class="md-lead">Grid area = the service area of the general transmission and distribution operator.</p>
  <div class="md-grid">
    <div>{bar_rows(area_pairs, n, lang="en")}</div>
    <div><table class="md-t"><caption>Projects and total capacity by grid area (total MW is the sum for the {n_mw} projects with a MW value)</caption><thead><tr>{_ths(["Grid area", "Projects", "Total MW"])}</tr></thead><tbody>{area_table}</tbody></table></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">By prefecture</div>
  <h2 class="md-h">Projects by prefecture (top 10)</h2>
  <p class="md-lead">There are projects in {len(s['pref'])} prefectures.</p>
  <table class="md-t"><caption>Projects by prefecture (top 10)</caption><thead><tr>{_ths(["Prefecture", "Projects"])}</tr></thead><tbody>{pref_rows}</tbody></table>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Voltage, structure, status</div>
  <h2 class="md-h">Voltage class, structure and status</h2>
  <p class="md-lead">High-voltage projects are mostly around 2 MW; extra-high-voltage projects are roughly 10 MW and above. A project is sold either as development rights that the buyer builds out (transfer of rights) or as a completed-build handover. Status shows whether the utility has answered the grid connection study, whether the grid construction cost has been fixed, or whether the project is already connected.</p>
  <div class="md-grid">
    <div>{H3}Voltage class</h3>{bar_rows(volt_pairs, n, lang="en")}</div>
    <div>{H3}Structure</h3>{bar_rows(scheme_pairs, n, lang="en")}</div>
    <div>{H3}Status</h3>{bar_rows(status_pairs, n, lang="en")}</div>
  </div>
</div></section>
{section_voltage_scheme(x, "en")}{section_size(x, "en")}
<section class="md"><div class="container">
  <div class="section-label">Grid connection timing</div>
  <h2 class="md-h">Expected grid connection</h2>
  <p class="md-lead">Projects with a planned operation date are counted by Japanese fiscal half-year (the fiscal year starts in April); the others by the months to connection stated in the grid connection study answer. {s['ym_known']} projects have a planned date, {s['lead_only']} have no planned date but a stated number of months, and {undated} are under review. In all, {len(s['lead'])} projects (including some with a planned date) have a stated number of months; the &ldquo;Months to connection&rdquo; chart counts these {len(s['lead'])}.</p>
  <div class="md-grid">
    <div>{H3}Planned operation (fiscal half-year)</h3>{bar_rows(half_pairs, s['ym_known'], lang="en")}</div>
    <div>{H3}Months to connection in the answer{f" &middot; median {s['lead_median']} months" if s['lead_median'] else ""}</h3>{bar_rows(band_pairs, len(s['lead']), lang="en")}
      {H3B}Start point of the months</h3>{bar_rows(basis_pairs, len(s['lead']), lang="en")}</div>
  </div>
</div></section>
{section_lead_by_scheme(x, s, "en")}
{weekly_section_en(weekly, generated)}
<section class="md"><div class="container">
  <div class="section-label">New listings</div>
  <h2 class="md-h">Listings by month first listed</h2>
  <p class="md-lead">Projects now listed, by the month they were first listed. Projects taken off the list are not included. {GROWTH_NOTE_EN}</p>
  <table class="md-t"><caption>Projects by month first listed (up to the latest six months with listings, projects now listed)</caption><thead><tr>{_ths(["Month first listed", "Projects"])}</tr></thead><tbody>{month_rows}</tbody></table>
</div></section>
{section_needs(nd, "en")}
{section_download("en", generated, len(weekly) >= 2, bool(nd and nd.get("n")), name, BASE + path,
                  '<p>The full project list in English is on <a href="/en/projects">Projects</a>; market prices (JEPX, capacity market) are on <a href="/en/report/data">Battery Storage Market Data</a>.</p>')}
{EN_CTA_MD}{EN_FOOTER}
</body>
</html>
"""
    return en_head(title, desc, path, jsonld, "/market-data") + body


# ---------------------------------------------------------------- 中国語（簡体字）の市場データ（zh-market-data.html）
# 日本語の /market-data と同じ集計（同じ projects.json の公開項目・同じ関数）を、用語は docs/glossary-en-zh.md と zh-faq.html にそろえて出す。
# 価格・案件名・所在地・売主は持っていないので出せない（O16-19）。CSV は英語版（列名と区分が英語）を指す（中国語の CSV は作らない）。
ZH_ORG = {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": BASE + "/zh"}
ZH_AREA = {"北海道": "北海道", "東北": "东北", "東京": "东京", "中部": "中部", "北陸": "北陆", "関西": "关西",
           "中国": "中国地区（日本本州西部）", "四国": "四国", "九州": "九州", "沖縄": "冲绳"}
ZH_PREF = {
    "北海道": "北海道", "青森県": "青森县", "岩手県": "岩手县", "宮城県": "宫城县", "秋田県": "秋田县", "山形県": "山形县",
    "福島県": "福岛县", "茨城県": "茨城县", "栃木県": "栃木县", "群馬県": "群马县", "埼玉県": "埼玉县", "千葉県": "千叶县",
    "東京都": "东京都", "神奈川県": "神奈川县", "新潟県": "新潟县", "富山県": "富山县", "石川県": "石川县", "福井県": "福井县",
    "山梨県": "山梨县", "長野県": "长野县", "岐阜県": "岐阜县", "静岡県": "静冈县", "愛知県": "爱知县", "三重県": "三重县",
    "滋賀県": "滋贺县", "京都府": "京都府", "大阪府": "大阪府", "兵庫県": "兵库县", "奈良県": "奈良县", "和歌山県": "和歌山县",
    "鳥取県": "鸟取县", "島根県": "岛根县", "岡山県": "冈山县", "広島県": "广岛县", "山口県": "山口县",
    "徳島県": "德岛县", "香川県": "香川县", "愛媛県": "爱媛县", "高知県": "高知县", "福岡県": "福冈县", "佐賀県": "佐贺县",
    "長崎県": "长崎县", "熊本県": "熊本县", "大分県": "大分县", "宮崎県": "宫崎县", "鹿児島県": "鹿儿岛县",
    "沖縄県": "冲绳县",
}
ZH_VOLT = {"高圧": "高压", "特別高圧": "特别高压", "低圧": "低压"}
ZH_SCHEME = {"権利譲渡": "权利转让", "完成渡し": "完工交付"}
ZH_STATUS = {"接続検討回答済": "已取得接入系统研究答复", "負担金確定": "并网工程费分摊已确定", "連系済": "已并网"}
ZH_SIZE = {"2MW未満": "不足2MW", "2〜10MW未満": "2MW以上、不足10MW", "10〜30MW未満": "10MW以上、不足30MW", "30MW以上": "30MW以上"}
ZH_BAND = {"6か月以内": "6个月以内", "7〜12か月": "7–12个月", "13〜24か月": "13–24个月", "25か月以上": "25个月以上"}
ZH_BASIS = {"payment": "自并网工程费分摊款支付起", "apply": "自提出并网申请起", "contract": "自签约起", "unspecified": "未注明起点（以答复书记载为准）"}
NEEDS_ZH = {"権利渡し": "权利转让", "完成渡し": "完工交付", "高圧": "高压", "特別高圧": "特别高压", "高圧・特別高圧": "高压或特别高压", "低圧": "低压",
            "本回答あり（またはその先）": "已收到并网申请的答复（或更后阶段）",
            "保証金支払済（またはその先）": "已支付并网保证金（或更后阶段）",
            "工事負担金支払済（またはその先）": "已支付并网工程费分摊（或更后阶段）"}
NEEDS_ZH_FIELD = {"sale_type": "购买方式", "voltage": "电压", "grid_area": "希望的区域（可多选，累计）",
                  "cod": "希望的投运时间", "grid_stage": "电力手续阶段"}
GROWTH_NOTE_ZH = "上线项目数量的增加，反映的是我们将项目录入一览的工作节奏（有些日子是集中录入），并不代表市场的增长。"
FONTS_ZH = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&family=Noto+Sans+SC:wght@400;500;700;900&display=swap"


def _zh_label(kind, v, table=False):
    """中国語の頁の区分の言い方（_en_label と同じ対応）。table=True は表の行見出し（電圧の確認中を「电压待确认」にする）。"""
    if v == OTHER:
        return "其他"
    if kind == "area":
        return ZH_AREA.get(v, v)
    if kind == "pref":
        return ZH_PREF.get(v, v)
    if kind == "volt":
        return ZH_VOLT.get(v, ("电压待确认" if table else "待确认") if v == "確認中" else v)
    if kind == "scheme":
        return ZH_SCHEME.get(v, "待确认" if v == "確認中" else v)
    if kind == "status":
        return ZH_STATUS.get(v, "待确认" if v == "確認中" else v)
    if kind == "size":
        return ZH_SIZE.get(v, v)
    if kind == "band":
        return ZH_BAND.get(v, v)
    if kind == "half":
        m = re.match(r"(\d{4})年度(上期|下期)", v)
        return f"{m.group(1)}财年{'上半期（4–9月）' if m.group(2) == '上期' else '下半期（10月–次年3月）'}" if m else v
    return v


def needs_zh(v):
    if v in NEEDS_ZH:
        return NEEDS_ZH[v]
    if v in ZH_AREA:
        return ZH_AREA[v]
    if v == "その他の選択肢":
        return "其他选项"
    m = re.match(r"(\d{4})年(\d{1,2})月まで$", v)
    if m:
        return f"至{m.group(1)}年{int(m.group(2))}月"
    return None


def weekly_section_zh(rows, generated):
    if len(rows) < 2:
        return ""
    last = rows[-1]
    body = "".join(
        f'<tr><th scope="row"><time datetime="{r["week"]}">{_esc(_short(r["week"]))}</time>{"（统计中）" if i == len(rows) - 1 else ""}</th><td class="n">{r["n"]}</td><td class="n">{_mwcell(r)}</td>'
        f'<td class="n">{r["hv"]}</td><td class="n">{r["ehv"]}</td><td class="n">{r["rights"]}</td><td class="n">{r["built"]}</td>'
        f'<td class="n">{r["new"]}</td></tr>' for i, r in enumerate(rows))
    mw_note = ("合计MW在输出功率数值缺失较多的周显示为“—”，以免把数据缺失误读为市场规模的变化。"
               if any(not r["mw_ok"] for r in rows) else "")
    return f"""<section class="md" id="weekly"><div class="container">
  <div class="section-label">每周变化</div>
  <h2 class="md-h">每周在售项目数</h2>
  <p class="md-lead">每周末买方可见的项目数与合计输出功率（以周一为起点的周，最近{len(rows)}周）。最新一周为截至{_esc(generated)}的统计中数字。</p>
  {weekly_svg(rows, "hv", "ehv", "高压", "特别高压", "每周在售项目数（高压与特别高压）", "个")}
  <div class="md-scroll"><table class="md-t"><caption>每周在售项目数与合计输出功率（最近{len(rows)}周，按电压类别与取得方式）</caption><thead><tr>{_ths(["周（周一）", "项目数", "合计MW", "高压", "特别高压", "权利转让", "完工交付", "新增项目"])}</tr></thead><tbody>{body}</tbody></table></div>
  <p class="md-note">图中为高压与特别高压的叠加；未设定电压的项目（最新一周为{last["other_v"]}个）不在图中，但计入表中的项目数。{mw_note}{GROWTH_NOTE_ZH}这是 ScienceX 自身挂牌的项目，并非日本全市场的统计。取得方式待确认的项目不计入最后两列。此处不公布价格、所在地与名称。</p>
</div></section>
"""


ZH_CTA_MD = """<section class="cta"><div class="container">
  <h2>项目本身，请在蓄电所市场查看</h2>
  <p>现有项目无需注册即可在蓄电所市场（Chikudensho Market）浏览。价格与资料在免费注册后查看，在注册界面同意保密承诺即可（无需签署纸质文件）。蓄电所市场的页面为英文。</p>
  <a class="btn-primary" href="https://dealroom.scix.co.jp/en" target="_top">在蓄电所市场查看项目 &rarr;</a>
  <a class="btn-secondary" href="/zh-contact">联系 ScienceX</a>
</div></section>
"""

ZH_FOOTER = """<footer class="scix-footer">
  <div class="scix-footer-inner">
    <a href="https://www.scix.co.jp/zh" class="scix-footer-logo" aria-label="ScienceX 首页">
      <img width="300" height="118" src="/img/logo-white.png" alt="ScienceX — Science X Inc." loading="lazy" />
    </a>
    <hr class="scix-footer-divider" />
    <div class="scix-footer-info">
      <div class="scix-footer-company">
        <div class="company-name">Science X Inc.（赛恩斯艾克斯）</div>
        日本〒103-0016 东京都中央区日本桥小网町8-2<br>
        BIZMARKS日本桥茅场町<br>
        TEL: <a href="tel:+81366913484">+81 3 6691 3484</a><br>
        MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>
        <div class="representative">代表董事 中岛晋也（工学博士）</div>
      </div>
      <div class="scix-footer-nav" style="margin-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:10px 22px;justify-content:center;">
        <a href="/zh" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">首页</a>
        <a href="https://dealroom.scix.co.jp/en" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">蓄电所市场</a>
        <a href="/zh-market-data" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">市场数据</a>
        <a href="/zh-knowledge" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">洞见</a>
        <a href="/zh-qa" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">问答</a>
        <a href="/zh-faq" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">常见问题</a>
        <a href="/zh-glossary" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">术语表</a>
        <a href="/zh-company" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">公司介绍</a>
        <a href="/zh-contact" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">联系我们</a>
        <a href="/zh-privacy" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">隐私政策</a>
      </div>
      <div class="scix-footer-copyright">&copy; 2025–2026 Science X Inc. All Rights Reserved.</div>
    </div>
  </div>
</footer>"""


def zh_head(title, desc, path, jsonld):
    """日本語の head を、中国語（簡体字）の頁の形に替える（lang・hreflang・og:locale・字体）。"""
    url = BASE + path
    h = (head(title, desc, path, jsonld)
         .replace('<html lang="ja">', '<html lang="zh-CN">')
         .replace(f'<link rel="alternate" hreflang="ja" href="{url}">',
                  f'<link rel="alternate" hreflang="zh-CN" href="{url}">\n<link rel="alternate" hreflang="ja" href="{BASE}/market-data">\n'
                  f'<link rel="alternate" hreflang="en" href="{BASE}/en/market-data">')
         .replace('content="ja_JP"', 'content="zh_CN"')
         .replace(FONTS, FONTS_ZH))
    return h.replace("'Noto Sans JP',sans-serif", "'Noto Sans SC','Noto Sans JP',sans-serif")


def render_zh_market(ps, today, generated, weekly=(), nd=None):
    """中国語の市場データ（/zh-market-data）。日本語の /market-data と同じ集計（件数・規模・月数だけ・価格なし）。"""
    s = stats(ps, today)
    x = extra_stats(ps)
    weekly = list(weekly)
    path = "/zh-market-data"
    n = s["n"]
    n_mw = sum(1 for p in ps if _num(p.get("mw")))
    title = "日本电网侧储能在售项目 市场数据｜ScienceX"
    desc = (f"ScienceX 挂牌的日本电网侧储能（蓄电池）在售项目{n}个、合计约{s['mw']:,}MW，按分区、都道府县、电压、取得方式、规模与并网所需月数统计。"
            "可下载CSV。不含价格。每天更新。")
    name = "日本电网侧储能在售项目：市场数据"
    dist = ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["summary"], "name": "汇总表（CSV，英文版）"}]
            + ([{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + CSV_EN["weekly"], "name": "每周变化（CSV，英文版）"}] if len(weekly) >= 2 else [])
            + [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/projects.json", "name": "公开一览（JSON）"}])
    ds_desc = ("ScienceX 在日本挂牌的电网侧储能在售项目的统计：项目数、容量、电压类别、取得方式（权利转让或完工交付）、进展、预计并网，"
               "以及电力公司答复书所载的并网所需月数，按分区与都道府县统计，并含电压×取得方式、规模区间、按取得方式的并网所需月数与每周变化。"
               "仅限已取得接入系统研究答复的项目。不含价格、单价、并网工程费分摊的金额、项目名称、所在地与卖方。"
               "对有数值的项目的统计均注明母数。" + GROWTH_NOTE_ZH + "每天早上更新。")
    needs_ld = needs_dataset(nd, "zh", BASE + path)
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "zh-CN", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/zh", "name": "ScienceX"}, "publisher": ZH_ORG}),
        ld({"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset", "name": name, "description": ds_desc,
            "url": BASE + path, "inLanguage": "zh-CN", "creator": ZH_ORG, "publisher": ZH_ORG, "isAccessibleForFree": True,
            "dateModified": generated, "temporalCoverage": f"2026-06/{generated[:7]}",
            "spatialCoverage": {"@type": "Place", "name": "日本（9个电力分区）"},
            "keywords": ["日本", "电网侧储能", "蓄电池", "在售项目", "市场数据", "并网", "投运"],
            "measurementTechnique": "对 ScienceX 在蓄电所市场挂牌的项目的公开字段（projects.json）每天早上重新统计",
            "variableMeasured": variables_zh(),
            "creditText": f"出处：Science X Inc.《{name}》，{BASE}{path}",
            "distribution": dist, "mainEntityOfPage": BASE + path}),
        ld(crumbs([("首页", BASE + "/zh"), ("市场数据", BASE + path)])),
    ] + ([ld(needs_ld)] if needs_ld else []))
    area_pairs = [(_zh_label("area", a), s["area"].get(a, 0)) for a, _, _ in AREAS if s["area"].get(a)]
    area_table = "".join(f'<tr><th scope="row">{_esc(_zh_label("area", a))}</th><td class="n">{s["area"].get(a, 0)}</td>'
                         f'<td class="n">{s["area_mw"].get(a, 0):,}</td></tr>' for a, _, _ in AREAS if s["area"].get(a))
    pref_rows = "".join(f'<tr><th scope="row">{_esc(_zh_label("pref", p_))}</th><td class="n">{c}</td></tr>' for p_, c in s["pref"].most_common(10))
    half_pairs = [(_zh_label("half", h), c) for h, c in sorted(s["half"].items())]
    band_pairs = [(_zh_label("band", b), s["bands"][b]) for b, _ in LEAD_BANDS if s["bands"].get(b)]
    basis_pairs = [(ZH_BASIS.get(k, k), v) for k, v in s["basis"].most_common()]
    month_rows = "".join(f'<tr><th scope="row"><time datetime="{_esc(m)}">{_esc(m)}</time></th><td class="n">{c}</td></tr>' for m, c in s["first_seen"])
    volt_pairs = [(_zh_label("volt", k), v) for k, v in s["volt"].most_common()]
    scheme_pairs = [(_zh_label("scheme", k), v) for k, v in s["scheme"].most_common()]
    status_pairs = [(_zh_label("status", k), v) for k, v in s["status"].most_common()]
    undated = s["undecided"] - sum(1 for p in ps if not p.get("live") and not (p.get("codYm") and p["codYm"] >= today.strftime("%Y-%m")) and _num(p.get("leadMonths")))
    median = f"　中位数 {s['lead_median']}个月" if s["lead_median"] else ""
    body = f"""{nav_crumbs([("首页", "/zh"), ("市场数据", path)])}
<section class="hero"><div class="container">
  <div class="section-label">每天更新 · ScienceX 挂牌项目</div>
  <h1>日本电网侧储能在售项目 市场数据</h1>
  <p>我们挂牌的{n}个在售项目，按分区、都道府县、电压类别、取得方式、进展、规模与预计并网统计：项目分布在哪些分区，预计何时并网，以及有多少可通过权利取得（权利转让）、有多少为建成后交付（完工交付）。统计截至<time datetime="{_esc(generated)}">{_esc(generated)}</time>。表格也可下载为 <a href="#download">CSV</a>（日文页面：<a href="/market-data" hreflang="ja">市場データ</a>；英文页面：<a href="/en/market-data" hreflang="en">Market data</a>）。</p>
  <div class="kpi">
    <div><b>{n}个</b><span>在售项目</span></div>
    <div><b>{s['mw']:,} MW</b><span>合计输出功率（{s['mwh']:,} MWh）</span></div>
    <div><b>{len(s['pref'])}个</b><span>都道府县，{len(s['area'])}个分区</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}个</b><span>特别高压（大致10MW以上）</span></div>
    <div><b>{s['new14']}个</b><span>最近{NEW_DAYS}日新增</span></div>
  </div>
  <p class="md-note" style="margin-top:14px">这里统计的是已提交给 ScienceX、并同意挂牌的电网侧储能（蓄电所）在售项目，均已取得电力公司的接入系统研究答复（接続検討の回答）。这是 ScienceX 自身挂牌的项目，并非日本全市场的统计。不公布项目所在地与卖方（价格与资料请在免费注册后于蓄电所市场查看）。数字每天早上依据与项目一览相同的数据重新统计。</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">按分区</div>
  <h2 class="md-h">按分区统计的项目数与规模</h2>
  <p class="md-lead">分区＝一般输配电企业（一般送配電事業者）的供电区域。</p>
  <div class="md-grid">
    <div>{bar_rows(area_pairs, n, lang="zh")}</div>
    <div><table class="md-t"><caption>按分区统计的项目数与合计输出功率（合计MW为有输出功率数值的{n_mw}个项目之和）</caption><thead><tr>{_ths(["分区", "项目数", "合计MW"])}</tr></thead><tbody>{area_table}</tbody></table></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">按都道府县</div>
  <h2 class="md-h">按都道府县统计（前10）</h2>
  <p class="md-lead">项目分布在{len(s['pref'])}个都道府县。</p>
  <table class="md-t"><caption>按都道府县统计的项目数（前10）</caption><thead><tr>{_ths(["都道府县", "项目数"])}</tr></thead><tbody>{pref_rows}</tbody></table>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">电压、取得方式、进展</div>
  <h2 class="md-h">电压类别、取得方式与进展</h2>
  <p class="md-lead">高压（日本的电压分类）项目以2MW左右为主；特别高压（日本的电压分类，并非中国800kV级的特高压）大致为10MW以上。取得方式分为两种：通过权利取得并由买方自行建设（权利转让），或以建成状态交付（完工交付）。进展表示：是否已取得接入系统研究（接続検討）的答复、并网工程费分摊（工事費負担金）是否已确定，或是否已并网。</p>
  <div class="md-grid">
    <div>{H3}电压类别</h3>{bar_rows(volt_pairs, n, lang="zh")}</div>
    <div>{H3}取得方式</h3>{bar_rows(scheme_pairs, n, lang="zh")}</div>
    <div>{H3}进展</h3>{bar_rows(status_pairs, n, lang="zh")}</div>
  </div>
</div></section>
{section_voltage_scheme(x, "zh")}{section_size(x, "zh")}
<section class="md"><div class="container">
  <div class="section-label">并网时间</div>
  <h2 class="md-h">预计并网</h2>
  <p class="md-lead">已定预计投运日的项目按财年（日本的财年自4月起）上、下半期统计；其余项目按接入系统研究答复书中写明的“并网所需月数”统计。已定预计日期的有{s['ym_known']}个，没有预计日期但写明月数的有{s['lead_only']}个，时间待确认的有{undated}个。答复书中写明月数的项目（含已定预计日期的）共{len(s['lead'])}个，“答复书所载并网所需月数”的图统计的就是这{len(s['lead'])}个。月数以答复书的记载为准，其中写明起点（如自并网工程费分摊款支付起算）的有{len(s['lead']) - s['basis'].get('unspecified', 0)}个。</p>
  <div class="md-grid">
    <div>{H3}预计投运（财年上、下半期）</h3>{bar_rows(half_pairs, s['ym_known'], lang="zh")}</div>
    <div>{H3}答复书所载并网所需月数{median}</h3>{bar_rows(band_pairs, len(s['lead']), lang="zh")}
      {H3B}月数的起点</h3>{bar_rows(basis_pairs, len(s['lead']), lang="zh")}</div>
  </div>
</div></section>
{section_lead_by_scheme(x, s, "zh")}
{weekly_section_zh(weekly, generated)}
<section class="md"><div class="container">
  <div class="section-label">新增项目</div>
  <h2 class="md-h">按上线月份统计</h2>
  <p class="md-lead">按首次录入一览的月份统计目前在售的项目。已售出或已撤下的项目不计入。{GROWTH_NOTE_ZH}</p>
  <table class="md-t"><caption>按上线月份统计的项目数（有项目的最近6个月，目前在售的项目）</caption><thead><tr>{_ths(["上线月份", "项目数"])}</tr></thead><tbody>{month_rows}</tbody></table>
</div></section>
{section_needs(nd, "zh")}
{section_download("zh", generated, len(weekly) >= 2, bool(nd and nd.get("n")), name, BASE + path,
                  '<p>项目一览请见<a href="/en/projects">Projects（英文页面）</a>；市场价格（JEPX、容量市场）请见<a href="/en/report/data">Battery Storage Market Data（英文页面）</a>。</p>')}
{ZH_CTA_MD}{ZH_FOOTER}
</body>
</html>
"""
    body = body.replace("'Noto Sans JP',sans-serif", "'Noto Sans SC','Noto Sans JP',sans-serif")
    return zh_head(title, desc, path, jsonld) + body


def sync_area_sitemap(ps, today):
    """noindex の管内ページ（件数が MIN_INDEX 未満）は sitemap から外し、索引に出す管内は載せる。"""
    path = os.path.join(ROOT, "sitemap.xml")
    lines = open(path, encoding="utf-8").read().split("\n")
    for area, slug, _ in AREAS:
        n = sum(1 for p in ps if p.get("area") == area)
        loc = f"<loc>{BASE}/projects-{slug}</loc>"
        idx = [i for i, l in enumerate(lines) if loc in l]
        if n < MIN_INDEX:
            for i in reversed(idx):
                del lines[i]
        elif not idx:
            last = max(i for i, l in enumerate(lines) if f"<loc>{BASE}/projects-" in l)
            u = f"{BASE}/projects-{slug}"
            lines.insert(last + 1, f'  <url>{loc}<xhtml:link rel="alternate" hreflang="ja" href="{u}"/>'
                                   f'<priority>0.7</priority><lastmod>{today.isoformat()}</lastmod></url>')
    return "\n".join(lines)


def sync_md_sitemap(text, generated):
    """/market-data・/en/market-data・/zh-market-data の行を、互いの hreflang つきで置く（無い行は /market-data の次に足す）。lastmod は今の値を残す。"""
    urls = {"ja": f"{BASE}/market-data", "en": f"{BASE}/en/market-data", "zh-CN": f"{BASE}/zh-market-data"}
    prio = {"ja": "0.8", "en": "0.7", "zh-CN": "0.6"}
    alt = {k: f'<xhtml:link rel="alternate" hreflang="{k}" href="{u}"/>' for k, u in urls.items()}

    def lastmod(u):
        m = re.search(r"<url><loc>" + re.escape(u) + r"</loc>.*?<lastmod>([0-9-]{10})</lastmod>", text)
        return m.group(1) if m else generated
    pat = {k: re.compile(r"  <url><loc>" + re.escape(u) + r"</loc>.*?</url>\n") for k, u in urls.items()}
    if not pat["ja"].search(text):
        return text
    # 自分の行は自分を先頭に、残りは ja・en・zh-CN の順（既存の ja・en の行の並びを変えない）
    line = {}
    for k, u in urls.items():
        rest = [alt[o] for o in ("ja", "en", "zh-CN") if o != k]
        line[k] = f"  <url><loc>{u}</loc>{alt[k]}{''.join(rest)}<priority>{prio[k]}</priority><lastmod>{lastmod(u)}</lastmod></url>\n"
    text = pat["ja"].sub(lambda _m: line["ja"], text, count=1)
    if pat["en"].search(text):
        text = pat["en"].sub(lambda _m: line["en"], text, count=1)
    else:
        text = text.replace(line["ja"], line["ja"] + line["en"], 1)
    if pat["zh-CN"].search(text):
        return pat["zh-CN"].sub(lambda _m: line["zh-CN"], text, count=1)
    return text.replace(line["en"], line["en"] + line["zh-CN"], 1)


def main():
    check = "--check" in sys.argv
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        data = json.load(f)
    ps = data.get("projects", [])
    generated = data.get("generatedAt") or datetime.date.today().isoformat()
    today = datetime.date.today()
    weekly = weekly_series(ps, today)
    nd = fetch_needs(today) if "--fetch-needs" in sys.argv else load_needs()
    pages = {"market-data.html": render_market(ps, today, generated, weekly, nd)}
    for area, slug, operator in AREAS:
        pages[f"projects-{slug}.html"] = render_area(ps, area, slug, operator, today, generated)
    pages["en/projects.html"] = render_en_projects(ps, today, generated, weekly)
    pages["en/market-data.html"] = render_en_market(ps, today, generated, weekly, nd)
    pages["zh-market-data.html"] = render_zh_market(ps, today, generated, weekly, nd)
    rows = summary_rows(ps, stats(ps, today), extra_stats(ps), generated, today)
    for lang, c in (("ja", CSV), ("en", CSV_EN)):
        pages[c["summary"].lstrip("/")] = summary_csv(rows, lang, generated)
        pages[c["weekly"].lstrip("/")] = weekly_csv(weekly, lang, generated)
        if nd and nd.get("n"):
            pages[c["needs"].lstrip("/")] = needs_csv(nd, lang)
    if nd:
        pages[NEEDS_JSON] = needs_text(nd)
    pages["sitemap.xml"] = sync_md_sitemap(sync_area_sitemap(ps, today), generated)
    changed = []
    for name, html in pages.items():
        path = os.path.join(ROOT, name)
        data_b = html.encode("utf-8")
        cur = open(path, "rb").read() if os.path.exists(path) else None
        if cur != data_b:
            changed.append(name)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as fh:
                    fh.write(data_b)
    if check:
        print(f"[check] 要更新 {len(changed)} ファイル" + (": " + " ".join(changed) if changed else ""))
        return 1 if changed else 0
    print(f"[ok] {len(changed)} ファイルを更新（{len(ps)}件・{generated}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
