#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市場データの頁（/market-data・/en/market-data）に足す集計の段（2026-11-25 新設）。

なぜ: 中島さん 2026-11-25「PR TIMEはもっと原稿を入れないといけないね。…最大数使いたい」。リリースの元になる一次情報を、
  公開してよい項目だけで増やす。

足す段（どれも件数の集計だけ。価格・単価・負担金の額・案件名・市区町村・番号は持たない＝O16-19・O07-60）:
  grid-stage       蓄電所マーケットの公開のカードに出ている「電力の手続きの段」ごとの件数
  land             公開のカードの土地の区分（市街化の区分・地形・建物までの距離・地目の中心）ごとの件数
  views            公開のカードの「見た人の数」を、取得の形・電圧・管内ごとに（件数・中央値・平均）
  area-size        規模の区分を、管内ごと・取得の形ごとに（projects.json）
  area-cod         運転開始の予定（年度）を、管内ごとに（projects.json）
  needs-supply     買主のリクエストが求めるエリア（延べ）と、そのエリアの販売中の件数（projects.json と買主のリクエストの控え）

カードの元: 蓄電所マーケットの公開の口 /api/open/cards（ログインなしで読める口）。--fetch-needs のとき（毎朝の同期）に読んで、
  区分ごとの数だけの控え files/market-data/open-cards-summary.json を書く（カードの番号・名前・市区町村は持たない）。
  口が読めなければ前の控えのまま。控えが無ければ、カードの段は出さない。
区分の件数が MIN_GROUP 未満なら「その他」にまとめる（個別の案件が割れないように）。
検査: scripts/selftest_market_more.py（控えの数が口から数え直した数と合うか・頁に控えの数が出ているか・projects.json の集計がカードと合うか）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import json
import os
import statistics
import sys
import urllib.request
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_API = "https://dealroom.scix.co.jp/api/open/cards?lang=ja"
CARDS_JSON = "files/market-data/open-cards-summary.json"
MARKET = "https://dealroom.scix.co.jp/"
MIN_GROUP = 5
OTHER = "その他"
NONE_LAND = "判定なし"
NONE_STAGE = "段の表示なし"

STAGE_ORDER = ["需給調整参加済み", "完工済み", "負担金 支払済", "本回答あり", "MS番号あり", "保証金 支払済", "発電調整 申込済",
               "接続検討 回答あり", "受付番号あり"]
LAND_FIELDS = [("zoning", "市街化の区分", "Zoning", ["区域外", "調整区域", "要確認"]),
               ("relief", "地形（高低差）", "Terrain", ["ほぼ平ら", "ゆるい", "高低差あり", "高低差が大きい"]),
               ("bldg", "いちばん近い建物までの距離", "Distance to the nearest building", ["30m未満", "30〜100m", "100〜300m", "300m以上"]),
               ("chimoku", "地目の中心", "Main land category", ["山林が中心", "農地（田・畑）が中心", "宅地が中心", "雑種地が中心", "原野が中心", "雑種地ほか"])]
VIEW_KEYS = [("saleType", "取得の形", "Structure"), ("voltage", "電圧", "Voltage"), ("area", "管内", "Grid area")]
SIZE_BINS = ["2MW未満", "2〜10MW未満", "10〜30MW未満", "30MW以上"]
EN = {"区域外": "Outside urbanization-control areas", "調整区域": "Urbanization-control area", "要確認": "To be checked",
      "ほぼ平ら": "Almost flat", "ゆるい": "Gentle slope", "高低差あり": "Some height difference", "高低差が大きい": "Large height difference",
      "30m未満": "Under 30 m", "30〜100m": "30–100 m", "100〜300m": "100–300 m", "300m以上": "300 m or more",
      "山林が中心": "Mainly forest", "農地（田・畑）が中心": "Mainly farmland", "宅地が中心": "Mainly residential land",
      "雑種地が中心": "Mainly miscellaneous land", "原野が中心": "Mainly wild land", "雑種地ほか": "Miscellaneous and other",
      NONE_LAND: "Not assessed", NONE_STAGE: "No stage shown", OTHER: "Other",
      "需給調整参加済み": "In the balancing market", "完工済み": "Construction completed", "負担金 支払済": "Grid cost paid",
      "本回答あり": "Final grid answer received", "MS番号あり": "MS number issued", "保証金 支払済": "Deposit paid",
      "発電調整 申込済": "Generation-adjustment applied", "接続検討 回答あり": "Connection study answered", "受付番号あり": "Application number issued",
      "完成渡し": "Completed-build handover", "権利渡し": "Transfer of rights", "権利譲渡": "Transfer of rights", "両方": "Either",
      "高圧": "High voltage", "特別高圧": "Extra-high voltage", "低圧": "Low voltage", "確認中": "Under review",
      "東京": "Tokyo", "中部": "Chubu", "九州": "Kyushu", "関西": "Kansai", "中国": "Chugoku", "東北": "Tohoku", "北海道": "Hokkaido",
      "北陸": "Hokuriku", "四国": "Shikoku",
      "2MW未満": "Under 2 MW", "2〜10MW未満": "2 to under 10 MW", "10〜30MW未満": "10 to under 30 MW", "30MW以上": "30 MW or more"}


def en(v):
    if v.endswith("年度") and v[:4].isdigit():
        return "FY" + v[:4]
    if v.endswith("年度以降") and v[:4].isdigit():
        return "FY" + v[:4] + " or later"
    return EN.get(v, v)


# ---------------------------------------------------------------- カードの控え（区分ごとの数だけ）
def _merge_counter(c):
    """MIN_GROUP 未満の区分を「その他」にまとめた dict（控えにも小さい区分を残さない＝個別の案件が割れないように）。"""
    out = Counter()
    for k, v in c.items():
        out[k if (v >= MIN_GROUP or k in (NONE_LAND, NONE_STAGE)) else OTHER] += v
    return dict(out)


def _med(xs):
    return float(statistics.median(xs)) if xs else 0.0


def cards_summary(cards):
    """公開のカードの配列 → 区分ごとの数（番号・名前・市区町村は持たない。MIN_GROUP 未満の区分は「その他」）。"""
    stage = Counter(((c.get("gs") or {}).get("now") or NONE_STAGE) for c in cards)
    land = {k: _merge_counter(Counter(((c.get("land") or {}).get(k) or NONE_LAND) for c in cards)) for k, _, _, _ in LAND_FIELDS}
    views = {}
    for k, _, _ in VIEW_KEYS:
        g = defaultdict(list)
        for c in cards:
            g[c.get(k) or "確認中"].append(int(c.get("viewersTotal") or 0))
        m = defaultdict(list)
        for v, xs in g.items():
            m[v if len(xs) >= MIN_GROUP else OTHER] += xs
        views[k] = {v: {"n": len(xs), "sum": sum(xs), "median": _med(xs)} for v, xs in m.items()}
    allv = [int(c.get("viewersTotal") or 0) for c in cards]
    return {"n": len(cards), "stage": _merge_counter(stage), "land": land, "views": views,
            "viewsAll": {"n": len(cards), "sum": sum(allv), "median": _med(allv)}}


def read_cards(url=CARDS_API):
    req = urllib.request.Request(url, headers={"User-Agent": "scix-web-build/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        cards = json.loads(r.read().decode("utf-8")).get("cards")
    if not isinstance(cards, list):
        raise ValueError("cards が配列でない")
    return cards


def load_cards():
    try:
        with open(os.path.join(ROOT, CARDS_JSON), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def fetch_cards(today):
    old = load_cards()
    try:
        cards = read_cards()
    except (OSError, ValueError) as e:
        print(f"注意: 公開のカードの口が読めない（前の控えのまま）: {e}", file=sys.stderr)
        return old
    c = cards_summary(cards)
    if old and all(old.get(k) == c[k] for k in c):
        return old
    return {"source": MARKET, "asOf": today.isoformat(), **c}


def cards_text(cs):
    return json.dumps(cs, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


# ---------------------------------------------------------------- 集計（まとめ方）
def merged_pairs(counter, order):
    """[(区分, 件数)]。order の順・order に無い区分は件数の多い順・MIN_GROUP 未満は「その他」へ。判定なし類は最後。"""
    tail = [k for k in (NONE_LAND, NONE_STAGE, "確認中") if k in counter]
    keys = [k for k in order if k in counter] + sorted((k for k in counter if k not in order and k not in tail), key=lambda k: -counter[k])
    out, other = [], 0
    for k in keys:
        if counter[k] >= MIN_GROUP:
            out.append((k, counter[k]))
        else:
            other += counter[k]
    if other:
        out.append((OTHER, other))
    return out + [(k, counter[k]) for k in tail if counter[k]]


def _size_bin(mw):
    return "2MW未満" if mw < 2 else "2〜10MW未満" if mw < 10 else "10〜30MW未満" if mw < 30 else "30MW以上"


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _fy(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y if m >= 4 else y - 1}年度"


def cross(ps, rowkey, colkey, col_order):
    """行×列の件数の表。件数が MIN_GROUP 未満の行は「その他」の行にまとめる。"""
    rows = Counter(rowkey(p) for p in ps)
    keep = [r for r, n in rows.most_common() if n >= MIN_GROUP]
    small = [r for r in rows if r not in keep]
    rk = (lambda p: rowkey(p) if rowkey(p) in keep else OTHER)
    t = Counter((rk(p), colkey(p)) for p in ps)
    return {"rows": keep + ([OTHER] if small else []), "cols": col_order, "t": t,
            "rtot": Counter(rk(p) for p in ps), "small": sorted(small)}


def project_stats(ps, today):
    """projects.json からの集計（管内×規模・取得の形×規模・管内×運転開始の年度）。"""
    mw_ps = [p for p in ps if _isnum(p.get("mw"))]
    ym = today.strftime("%Y-%m")
    cod_ps = [p for p in ps if p.get("codYm") and p["codYm"] >= ym and not p.get("live")]
    years = Counter(_fy(p["codYm"]) for p in cod_ps)
    ykeep = sorted(y for y in years)
    # 件数の少ない後ろの年度は「YYYY年度以降」にまとめる（前から順に見て、それより後が全部 MIN_GROUP 未満ならまとめる）
    cut = None
    for i, y in enumerate(ykeep):
        if sum(years[z] for z in ykeep[i:]) < MIN_GROUP * 2 and all(years[z] < MIN_GROUP for z in ykeep[i:]):
            cut = y
            break
    fy_label = (lambda p: (_fy(p["codYm"]) if not cut or _fy(p["codYm"]) < cut else f"{cut[:4]}年度以降"))
    ycols = [y for y in ykeep if not cut or y < cut] + ([f"{cut[:4]}年度以降"] if cut else [])
    return {"n": len(ps), "n_mw": len(mw_ps), "n_cod": len(cod_ps),
            "area_size": cross(mw_ps, lambda p: p.get("area") or "確認中", lambda p: _size_bin(p["mw"]), SIZE_BINS),
            "scheme_size": cross(mw_ps, lambda p: p.get("scheme") if p.get("scheme") in ("権利譲渡", "完成渡し") else "確認中",
                                 lambda p: _size_bin(p["mw"]), SIZE_BINS),
            "area_cod": cross(cod_ps, lambda p: p.get("area") or "確認中", fy_label, ycols)}


# ---------------------------------------------------------------- 段（HTML）
def _B():
    import build_market_data as B  # noqa: WPS433（循環を避けて、呼ぶときに読む）
    return B


def _table(cx, J, caption, rowname, unit_total):
    B = _B()
    head = [rowname] + [(c if J else en(c)) for c in cx["cols"]] + [("計" if J else "Total")]
    u = "件" if J else ""   # 日本語の表は単位つき（引用やリリースで数を書くとき、頁の字と同じになるように）
    body = "".join(
        f'<tr><th scope="row">{B._esc(r if J else en(r))}</th>'
        + "".join(f'<td class="n">{cx["t"].get((r, c), 0)}{u}</td>' for c in cx["cols"])
        + f'<td class="n">{cx["rtot"][r]}{u}</td></tr>' for r in cx["rows"])
    tot = "".join(f'<td class="n">{sum(cx["t"].get((r, c), 0) for r in cx["rows"])}{u}</td>' for c in cx["cols"])
    body += f'<tr><th scope="row">{"計" if J else "Total"}</th>{tot}<td class="n">{unit_total}{u}</td></tr>'
    return (f'<div class="md-scroll"><table class="md-t"><caption>{B._esc(caption)}</caption><thead><tr>{B._ths(head)}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _small_note(*cxs, J=True):
    """件数の少ない行を「その他」にまとめた事の注（どの区分をまとめたかは書かない＝個別の案件が割れないように）。"""
    if not any(cx["small"] for cx in cxs):
        return ""
    if J:
        return f"件数が{MIN_GROUP}件未満の行は「その他」にまとめました。"
    return f" Rows with fewer than {MIN_GROUP} projects are combined as &ldquo;Other&rdquo;."


def section_grid_stage(cs, J):
    if not cs or not cs.get("n"):
        return ""
    B = _B()
    n = cs["n"]
    pairs = merged_pairs(Counter(cs["stage"]), STAGE_ORDER)
    asof = B._esc(cs.get("asOf", ""))
    if J:
        return f"""<section class="md" id="grid-stage"><div class="container">
  <div class="section-label">電力の手続きの段</div>
  <h2 class="md-h">案件のカードに出ている電力の手続きの段（{n}件）</h2>
  <p class="md-lead"><a href="{MARKET}" target="_top">蓄電所マーケット</a>の案件のカード（登録なしで見られる）には、いま分かっている電力の手続きの段を1つ出しています。その段ごとに{n}件を数えました。段は、進んだ順（需給調整市場に参加済み → 完工 → 負担金の支払い → 本回答 → MS番号 → 保証金 → 発電調整の申込 → 接続検討の回答）に並べています。</p>
  <div class="md-grid"><div>{B.bar_rows(pairs, n)}</div></div>
  <p class="md-note">上の「進み具合」（接続検討回答済・負担金確定・連系済の3区分）とは数え方が違い、カードの段をそのまま数えています。件数が{MIN_GROUP}件未満の段は「その他」にまとめ、段を出していないカードは「{NONE_STAGE}」にしました。毎朝、蓄電所マーケットの公開のカードから数え直しています（<time datetime="{asof}">{asof}</time> 時点）。</p>
</div></section>
"""
    pe = [(en(k), v) for k, v in pairs]
    return f"""<section class="md" id="grid-stage"><div class="container">
  <div class="section-label">Grid-process stage</div>
  <h2 class="md-h">Grid-process stage shown on the project cards ({n} projects)</h2>
  <p class="md-lead">Each project card on <a href="{MARKET}en" target="_top">Chikudensho Market</a> (visible without registering) shows the grid-process stage reached so far. The {n} cards are counted by that stage, from the furthest along.</p>
  <div class="md-grid"><div>{B.bar_rows(pe, n, lang="en")}</div></div>
  <p class="md-note">This counts the stage on the cards and differs from the three-way &ldquo;Status&rdquo; above. Stages with fewer than {MIN_GROUP} projects are combined as &ldquo;Other&rdquo;. Recounted every morning from the public cards (as of <time datetime="{asof}">{asof}</time>).</p>
</div></section>
"""


def section_land(cs, J):
    if not cs or not cs.get("n"):
        return ""
    B = _B()
    n = cs["n"]
    asof = B._esc(cs.get("asOf", ""))
    blocks = []
    for k, ja, en_name, order in LAND_FIELDS:
        pairs = merged_pairs(Counter(cs["land"].get(k) or {}), order)
        if not J:
            pairs = [(en(a), v) for a, v in pairs]
        blocks.append(f'<div>{B.H3}{B._esc(ja if J else en_name)}</h3>{B.bar_rows(pairs, n, lang="ja" if J else "en")}</div>')
    if J:
        return f"""<section class="md" id="land"><div class="container">
  <div class="section-label">土地の区分</div>
  <h2 class="md-h">土地の区分ごとの件数（{n}件）</h2>
  <p class="md-lead">蓄電所マーケットの案件の頁と一覧の絞り込みに使っている土地の区分（市街化の区分・地形・いちばん近い建物までの距離・地目の中心）ごとに、{n}件を数えました。区分は決まった言葉だけで、数値と根拠は出していません。</p>
  <div class="md-grid">{"".join(blocks)}</div>
  <p class="md-note">「{NONE_LAND}」は、その区分をまだ出していない案件です。区分は当社が公表の地図などから判定したおおよその物で、現地の確認に代わるものではありません。件数が{MIN_GROUP}件未満の区分は「その他」にまとめました。割合は{n}件に対する割合です。毎朝、公開のカードから数え直しています（<time datetime="{asof}">{asof}</time> 時点）。</p>
</div></section>
"""
    return f"""<section class="md" id="land"><div class="container">
  <div class="section-label">Land</div>
  <h2 class="md-h">Projects by land classification ({n} projects)</h2>
  <p class="md-lead">The {n} projects counted by the land classes used on Chikudensho Market (zoning, terrain, distance to the nearest building, main land category). Only fixed class names are shown, without figures or sources.</p>
  <div class="md-grid">{"".join(blocks)}</div>
  <p class="md-note">&ldquo;Not assessed&rdquo; means the class is not shown yet. Classes are our approximate reading of public maps and do not replace a site check. Classes with fewer than {MIN_GROUP} projects are combined as &ldquo;Other&rdquo;. Shares are of the {n} projects. As of <time datetime="{asof}">{asof}</time>.</p>
</div></section>
"""


def _view_rows(cs, k):
    g = cs["views"].get(k) or {}
    keep = sorted((v for v in g if g[v]["n"] >= MIN_GROUP), key=lambda v: -g[v]["n"])
    small = [v for v in g if v not in keep]
    rows = [(v, g[v]["n"], g[v]["median"], round(g[v]["sum"] / g[v]["n"], 1)) for v in keep]
    return rows, small


def _fmt(v):
    return f"{v:g}"


def section_views(cs, J):
    if not cs or not cs.get("n"):
        return ""
    B = _B()
    asof = B._esc(cs.get("asOf", ""))
    tables, smalls = [], []
    for k, ja, en_name in VIEW_KEYS:
        rows, small = _view_rows(cs, k)
        if small:
            smalls.append(("・".join(small) if J else ", ".join(en(s) for s in small)))
        head = [ja if J else en_name] + (["カードの件数", "見た人の数の中央値", "見た人の数の平均"] if J else ["Cards", "Median viewers", "Mean viewers"])
        uc, up = ("件", "人") if J else ("", "")
        body = "".join(f'<tr><th scope="row">{B._esc(v if J else en(v))}</th><td class="n">{c}{uc}</td><td class="n">{_fmt(m)}{up}</td><td class="n">{a:g}{up}</td></tr>'
                       for v, c, m, a in rows)
        cap = (f"{ja}ごとの、カード1件あたりの見た人の数" if J else f"Viewers per card by {en_name.lower()}")
        tables.append(f'<div class="md-scroll"><table class="md-t"><caption>{B._esc(cap)}</caption><thead><tr>{B._ths(head)}</tr></thead><tbody>{body}</tbody></table></div>')
    va = cs["viewsAll"]
    if J:
        note_small = f"カードが{MIN_GROUP}件未満の区分は「その他」にまとめ、それでも{MIN_GROUP}件未満なら表に出していません。" if smalls else ""
        return f"""<section class="md" id="views"><div class="container">
  <div class="section-label">よく見られている案件</div>
  <h2 class="md-h">見た人の数で見る、関心の集まり方</h2>
  <p class="md-lead">蓄電所マーケットの案件のカードには「見た人の数」を出しています。その数を、取得の形・電圧・管内ごとに、カード1件あたりの中央値と平均で並べました。{va['n']}件のカード全体では、中央値が{_fmt(va['median'])}人です。</p>
  <div class="md-grid">{"".join(tables)}</div>
  <p class="md-note">見た人の数は、カードに出している数をそのまま使っています（案件の頁を見た人の数で、売れ行きを表すものではありません）。載った日が新しいカードほど数が少なくなります。{note_small}毎朝、公開のカードから数え直しています（<time datetime="{asof}">{asof}</time> 時点）。</p>
</div></section>
"""
    note_small = f" Groups with fewer than {MIN_GROUP} cards are combined as &ldquo;Other&rdquo;, and not shown if still fewer than {MIN_GROUP}." if smalls else ""
    return f"""<section class="md" id="views"><div class="container">
  <div class="section-label">Where interest goes</div>
  <h2 class="md-h">Interest by viewers per card</h2>
  <p class="md-lead">Each project card on Chikudensho Market shows how many people have viewed it. Here are the median and mean viewers per card by structure, voltage and grid area. Across all {va['n']} cards the median is {_fmt(va['median'])}.</p>
  <div class="md-grid">{"".join(tables)}</div>
  <p class="md-note">Viewer counts are taken as shown on the cards; they measure page views, not sales. Newer cards have fewer views.{note_small} As of <time datetime="{asof}">{asof}</time>.</p>
</div></section>
"""


def section_size_cross(pst, J):
    B = _B()
    k = pst["n_mw"]
    if not k:
        return ""
    a, s = pst["area_size"], pst["scheme_size"]
    if J:
        return f"""<section class="md" id="area-size"><div class="container">
  <div class="section-label">管内×規模</div>
  <h2 class="md-h">規模の区分を、管内ごと・取得の形ごとに</h2>
  <p class="md-lead">上の「規模の区分」の{k}件（出力の値がある件）を、管内ごとと、取得の形ごとに分けました。</p>
  {_table(a, True, f"管内ごとの規模の区分（出力の値がある{k}件）", "管内", k)}
  {_table(s, True, f"取得の形ごとの規模の区分（出力の値がある{k}件）", "取得の形", k)}
  <p class="md-note">{_small_note(a, s, J=True)}取得の形がまだ決まっていない案件は「確認中」です。</p>
</div></section>
"""
    return f"""<section class="md" id="area-size"><div class="container">
  <div class="section-label">Area × size</div>
  <h2 class="md-h">Size bands by grid area and by structure</h2>
  <p class="md-lead">The {k} projects with a capacity value, split by grid area and by structure.</p>
  {_table(a, False, f"Size bands by grid area ({k} projects with a value)", "Grid area", k)}
  {_table(s, False, f"Size bands by structure ({k} projects with a value)", "Structure", k)}
  <p class="md-note">{_small_note(a, s, J=False)}</p>
</div></section>
"""


def section_area_cod(pst, J):
    k = pst["n_cod"]
    if not k:
        return ""
    a = pst["area_cod"]
    if J:
        return f"""<section class="md" id="area-cod"><div class="container">
  <div class="section-label">管内×運転開始</div>
  <h2 class="md-h">運転開始の予定（年度）を、管内ごとに</h2>
  <p class="md-lead">運転開始の予定が決まっている{k}件を、管内と年度（4月はじまり）で数えました。どの管内で、いつ動き出す案件が売りに出ているかの見当付けにお使いください。</p>
  {_table(a, True, f"管内ごとの運転開始の予定（年度・予定が決まっている{k}件）", "管内", k)}
  <p class="md-note">{_small_note(a, J=True)}件数の少ない後ろの年度は「以降」にまとめました。運転開始の予定が決まっていない案件は数えていません（上の「連系の見込み」の月数を見てください）。</p>
</div></section>
"""
    return f"""<section class="md" id="area-cod"><div class="container">
  <div class="section-label">Area × start of operation</div>
  <h2 class="md-h">Planned start of operation by grid area</h2>
  <p class="md-lead">The {k} projects with a planned operation date, by grid area and Japanese fiscal year (starting in April).</p>
  {_table(a, False, f"Planned start of operation by grid area (fiscal year, {k} projects with a planned date)", "Grid area", k)}
  <p class="md-note">{_small_note(a, J=False)} Later fiscal years with few projects are combined.</p>
</div></section>
"""


def needs_supply_rows(ps, nd):
    """買主のリクエストの「求めるエリア」（延べ）と、そのエリアの販売中の件数・うち権利譲渡・うち高圧。"""
    if not nd or not nd.get("n"):
        return []
    want = (nd.get("fields", {}).get("grid_area") or {}).get("values") or {}
    rows = []
    for a, w in sorted(want.items(), key=lambda t: -t[1]):
        if a in ("その他の選択肢", "指定なし"):
            continue
        aps = [p for p in ps if p.get("area") == a]
        rows.append((a, w, len(aps), sum(1 for p in aps if p.get("scheme") == "権利譲渡"), sum(1 for p in aps if p.get("voltage") == "高圧")))
    return rows


def section_needs_supply(ps, nd, J):
    rows = needs_supply_rows(ps, nd)
    if not rows:
        return ""
    B = _B()
    n = nd["n"]
    st = (nd.get("fields", {}).get("sale_type") or {}).get("values") or {}
    rights = st.get("権利渡し", 0)
    head = (["エリア", "求めるリクエスト（延べ）", "販売中の件数", "うち権利譲渡", "うち高圧"] if J
            else ["Grid area", "Requests naming it", "Projects listed", "of which transfer of rights", "of which high voltage"])
    u = "件" if J else ""
    body = "".join(f'<tr><th scope="row">{B._esc(a if J else en(a))}</th><td class="n">{w}{u}</td><td class="n">{c}{u}</td><td class="n">{r}{u}</td><td class="n">{h}{u}</td></tr>'
                   for a, w, c, r, h in rows)
    asof = B._esc(nd.get("asOf", ""))
    tbl = f'<div class="md-scroll"><table class="md-t"><caption>{"買主のリクエストが求めるエリアと、そのエリアの販売中の件数" if J else "Areas named in buyer requests and projects listed there"}</caption><thead><tr>{B._ths(head)}</tr></thead><tbody>{body}</tbody></table></div>'
    if J:
        return f"""<section class="md" id="needs-supply"><div class="container">
  <div class="section-label">求められている物と、売り物</div>
  <h2 class="md-h">買主のリクエストが求めるエリアと、売り物の並び</h2>
  <p class="md-lead">いま載っている買主のリクエスト{n}件が求めるエリア（1件で複数を選べる・延べ）ごとに、そのエリアで販売中の売り案件の件数を並べました。{n}件のうち{rights}件は、買い方に権利渡しを選んでいます。</p>
  {tbl}
  <p class="md-note">リクエストの件数が{_B().NEEDS_MIN}件未満のエリアは、上の「買主のリクエストの条件」と同じく「その他の選択肢」にまとめ、この表には出していません。販売中の件数は、この頁の集計と同じ一覧（projects.json）から数えています。リクエストの件数が最後に変わった日: <time datetime="{asof}">{asof}</time>。</p>
</div></section>
"""
    return f"""<section class="md" id="needs-supply"><div class="container">
  <div class="section-label">Demand and supply</div>
  <h2 class="md-h">Areas buyers ask for, and what is listed there</h2>
  <p class="md-lead">For each grid area named in the {n} buyer requests now listed (a request may name several), the number of projects listed in that area. {rights} of the {n} requests ask for a transfer of rights.</p>
  {tbl}
  <p class="md-note">Areas named fewer than {_B().NEEDS_MIN} times are combined as &ldquo;Other options&rdquo; above and not shown here. Request counts last changed: <time datetime="{asof}">{asof}</time>.</p>
</div></section>
"""


def sections(ps, today, cs, nd, lang):
    """足す段の全部（日本語は lang='ja'・英語は 'en'）。"""
    J = lang == "ja"
    pst = project_stats(ps, today)
    return (section_grid_stage(cs, J) + section_land(cs, J) + section_size_cross(pst, J) + section_area_cod(pst, J)
            + section_views(cs, J) + section_needs_supply(ps, nd, J))
