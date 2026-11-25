#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市場データの頁に足した集計の段（scripts/market_data_more.py）の検査（2026-11-25 新設）。

見ること:
  1. 決まり（ネット無し）: 小さい区分を「その他」にまとめるか・控えに案件の番号や名前が入らないか・まとめた区分の名前を注に書かないか。
  2. 控え files/market-data/open-cards-summary.json の数が、蓄電所マーケットの公開のカードの口から今数え直した数と合うか（--live のとき）。
  3. 頁（market-data.html・en/market-data.html）の新しい段に、控えと projects.json から作った段がそのまま入っているか。
  4. projects.json から作った段（管内×規模・取得の形×規模・管内×運転開始）に使う項目（管内・電圧・出力・取得の形）が、
     同じ番号の公開のカードと合うか（--live のとき）。
使い方: python3 scripts/selftest_market_more.py [--live]   （合わなければ 1）
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import market_data_more as M  # noqa: E402

bad = []


def ok(cond, msg):
    if not cond:
        bad.append(msg)


def rules():
    cards = ([{"id": "HV-1", "name": "X蓄電所", "muni": "Y町", "area": "四国", "voltage": "高圧", "saleType": "完成渡し", "viewersTotal": 3,
               "gs": {"now": "完工済み"}, "land": {"zoning": "区域外"}}]
             + [{"id": f"HV-{i}", "name": "Z", "area": "九州", "voltage": "高圧", "saleType": "権利渡し", "viewersTotal": i,
                 "gs": {"now": "負担金 支払済"}, "land": {"zoning": "調整区域"}} for i in range(2, 8)])
    s = M.cards_summary(cards)
    txt = M.cards_text(s)
    ok("HV-" not in txt and "蓄電所" not in txt and "Y町" not in txt, "控えに案件の番号・名前・市区町村が入っている")
    ok("四国" not in s["views"]["area"] and s["views"]["area"].get(M.OTHER, {}).get("n") == 1, "見た人の数の小さい管内が「その他」にまとまらない")
    ok(s["stage"].get("完工済み") is None and s["stage"].get(M.OTHER) == 1, "小さい段が「その他」にまとまらない")
    ok(s["land"]["zoning"].get("区域外") is None, "小さい土地の区分が「その他」にまとまらない")
    ps = [{"area": "九州", "mw": 2.0, "scheme": "権利譲渡", "codYm": "2027-05"} for _ in range(6)] + [{"area": "四国", "mw": 40, "scheme": "完成渡し", "codYm": "2027-05"}]
    pst = M.project_stats(ps, datetime.date(2026, 11, 25))
    ok(pst["area_size"]["rows"] == ["九州", M.OTHER], "管内×規模の小さい行が「その他」にまとまらない")
    html = M.section_size_cross(pst, True)
    ok("四国" not in html, "まとめた区分の名前が頁に出ている")


SCHEME = {"権利渡し": "権利譲渡", "完成渡し": "完成渡し"}


def compare_ids(ps, cards):
    """projects.json の各案件の、管内×規模・取得の形×規模・管内×運転開始の表に使う項目（管内・電圧・出力・取得の形）が、
    同じ番号の公開のカードと合うか。出力は projects.json が小数2桁に丸めているので、カードの値を2桁に丸めて比べる。
    運転開始は、カードの方が広い出どころ（売主の入力を含む）なので比べない（頁の運転開始は projects.json の確かめた予定だけ）。"""
    cid = {c.get("id"): c for c in cards}
    miss = Counter()
    for p in ps:
        c = cid.get(p.get("id"))
        if c is None:
            miss["カードに無い"] += 1
            continue
        if (c.get("area") or None) != (p.get("area") or None):
            miss["管内"] += 1
        if (c.get("voltage") or None) != (p.get("voltage") or None):
            miss["電圧"] += 1
        cm, pm = c.get("mw"), p.get("mw")
        if (cm is None) != (pm is None) or (cm is not None and round(float(cm), 2) != round(float(pm), 2)):
            miss["出力"] += 1
        ps_ = p.get("scheme") if p.get("scheme") in ("権利譲渡", "完成渡し") else None
        if not (c.get("saleType") == "両方" and ps_) and SCHEME.get(c.get("saleType")) != ps_:   # カードの「両方」は一覧ではどちらか一方
            miss["取得の形"] += 1
    return miss


def _t(cx):
    return {k: v for k, v in cx["t"].items() if v}


def main():
    live = "--live" in sys.argv
    rules()
    cs = M.load_cards()
    ok(cs is not None, f"控え {M.CARDS_JSON} が無い")
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        pj = json.load(f)
    ps = pj.get("projects", [])
    today = datetime.date.fromisoformat((pj.get("generatedAt") or datetime.date.today().isoformat())[:10])
    try:
        with open(os.path.join(ROOT, "files/market-data/buyer-requests.json"), encoding="utf-8") as f:
            import build_market_data as B
            nd = B.merge_small_needs(json.load(f))
    except (OSError, ValueError):
        nd = None
    if cs:
        for name, lang in (("market-data.html", "ja"), ("en/market-data.html", "en")):
            with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                page = f.read()
            for part in (M.section_grid_stage(cs, lang == "ja"), M.section_land(cs, lang == "ja"), M.section_views(cs, lang == "ja")):
                ok(part and part in page, f"{name}: カードの段が控えのとおりに入っていない（build_market_data.py を回し直す）")
    # 管内ごとの連系までの月数の表の「計」が、今ある全体の段（回答書の工期）の数と合うか
    import build_market_data as B
    gs = B.stats(ps, today)
    mc = M.project_stats(ps, today)["area_months"]
    ok(sum(mc["rtot"].values()) == len(gs["lead"]), "管内ごとの月数の計が、全体の段の件数と合わない")
    for band, n in gs["bands"].items():
        ok(sum(mc["t"].get((r, band), 0) for r in mc["rows"]) == n, f"管内ごとの月数の「{band}」の計が、全体の段と合わない")
    ok(all(mc["med"][r] is None for r in mc["rows"] if mc["rtot"][r] < M.MIN_GROUP), "5件未満の行に中央値が出ている")
    ok(all(r == M.OTHER or mc["rtot"][r] >= M.MIN_GROUP for r in mc["rows"]), "管内ごとの月数に5件未満の行が残っている")
    if cs:
        for name, lang in (("market-data.html", "ja"), ("en/market-data.html", "en")):
            with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                ok(M.section_months_area(M.project_stats(ps, today), lang == "ja") in f.read(), f"{name}: 管内ごとの月数の段が入っていない（build_market_data.py を回し直す）")
    if live:
        cards = M.read_cards()
        now = M.cards_summary(cards)
        for k in ("n", "stage", "land", "views", "viewsAll"):
            ok(cs and cs.get(k) == now[k], f"控えの {k} が公開のカードから数え直した数と合わない（--fetch-needs で焼き直す）")
        ok(len(cards) == len(ps), f"件数が合わない（projects.json {len(ps)}・カード {len(cards)}）")
        miss = compare_ids(ps, cards)
        ok(not miss, "projects.json の項目が公開のカードと合わない: " + "・".join(f"{k} {v}件" for k, v in miss.items()))
    for m in bad:
        print("NG " + m)
    print(f"[selftest_market_more] {'NG ' + str(len(bad)) if bad else 'ok'}{'（--live: 公開のカードと突き合わせた）' if live else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
