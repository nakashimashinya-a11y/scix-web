#!/usr/bin/env python3
"""build_flash.py（市場ノートの速報の頁）の自己試験。合成の数字と空の図だけで焼く（本物の数字・リポジトリの頁・ネットは読まない）。
    python3 scripts/selftest_flash.py
見る事（2026-11-24 中島「グラフにしてくれないと読まない。先週じゃなくて、当月の動きを１日から全部出して。月報と同じく、需給調整が先頭だよね。」）:
  節の並びが 今月の動き → ①需給調整市場（図6枚・表）→ ②卸電気（図5枚・表）→ 日ごとの表 → データの時点／図が11枚で図1〜図11の順／
  先週の節が無い／日ごとの表が1日から全部ある／月の初め・前月なし・一次オフラインなしでも落ちない／図や日ごとの数字の無い入力は焼かない。"""
from __future__ import annotations  # launchd の python3 は 3.9

import copy
import datetime
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_flash as b  # noqa: E402

CODES = [("1-0", "一次調整力（オンライン）"), ("1-1", "一次調整力（オフライン）"), ("2-1", "二次調整力①"), ("2-2", "二次調整力②"),
         ("3-1", "三次調整力①"), ("3-2", "三次調整力②"), ("4-0", "複合商品")]
ORDER = ["moves", "e1", "e2", "e3", "e4", "e5", "e6", "eprx", "j1", "j2", "j3", "j4", "j5", "jepx", "daily", "asof"]
SVG = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="50pt" viewBox="0 0 100 50"></svg>\n'


def days(ym, n):
    return ["%s-%02d" % (ym, i) for i in range(1, n + 1)]


def make(e_month="2026-11", e_days=23, j_month="2026-11", j_days=24, prev=True, offline=True):
    """合成の入力（bin/market_flash.py の latest.json と同じ形）。値は日と商品で変える（最大・最小が決まるように）。"""
    areas = lambda k: {a: {"avg": 20.0 + i + k, "s4": 10.0 + i - k, "s2": 12.0, "max": 60.0} for i, a in enumerate(b.AREAS)}  # noqa: E731
    pm = lambda ym: "%04d-%02d" % (int(ym[:4]) - (ym[5:] == "01"), 12 if ym[5:] == "01" else int(ym[5:]) - 1)  # noqa: E731

    def rows(k):
        return [{"code": c, "name": n, "ratio": None if (c == "1-1" and not offline) else 90.0 + 10 * i + k, "award": 70.0,
                 "price": None if (c == "1-1" and not offline) else 2.0 + i + k / 10.0, "komas": 48} for i, (c, n) in enumerate(CODES)]

    jd = [{"date": x, "areas": {a: {"avg": v["avg"], "s4": v["s4"]} for a, v in areas(n % 5).items()}}
          for n, x in enumerate((days(pm(j_month), 28) if prev else []) + days(j_month, j_days))]
    ed = [{"date": x, "rows": {r["code"]: {"ratio": r["ratio"], "award": r["award"], "price": r["price"]} for r in rows(n % 7)}} for n, x in enumerate(days(e_month, e_days))]
    j = {"ok": True, "latest_day": days(j_month, j_days)[-1], "month": j_month, "files": {},
         "mtd": {"from": j_month + "-01", "to": days(j_month, j_days)[-1], "days": j_days, "areas": areas(0), "curve": {a: [10.0 + (k % 24) for k in range(48)] for a in b.AREAS}},
         "day": {"date": days(j_month, j_days)[-1], "areas": areas(1)},
         "prev": {"month": pm(j_month), "days": 28, "days_in_month": 28, "areas": areas(2)} if prev else None, "daily": jd}
    e = {"ok": True, "basis": "速報値", "latest_day": days(e_month, e_days)[-1], "month": e_month, "fetched": "2026-11-24",
         "mtd": {"from": e_month + "-01", "to": days(e_month, e_days)[-1], "days": e_days, "rows": rows(0)},
         "day": {"date": days(e_month, e_days)[-1], "rows": rows(1)},
         "prev": {"month": pm(e_month), "days": 28, "days_in_month": 28, "rows": rows(2)} if prev else None, "daily": ed,
         "detail": {"hourly": {c: [1.0 + (h % 12) for h in range(24)] for c, _ in CODES},
                    "by_area": {c: {a: {"avg_price": 1.0 + i} for i, a in enumerate(b.AREAS[1:])} for c, _ in CODES},
                    "rate_slot_area": {c: {a: [50.0] * 48 for a in b.AREAS[1:]} for c, _ in CODES}, "slot_days": e_days}}
    return {"schema": 1, "made_on": "2026-11-24", "jepx": j, "eprx": e, "weeks": [],
            "figs": {"ok": True, "format": "svg", "names": list(b.FIG_NAMES), "langs": ["ja", "en"],
                     "for": {"jepx_day": j["latest_day"], "eprx_day": e["latest_day"]}}}


def figs():
    return {(lang, n): SVG for lang in ("ja", "en") for n in b.FIG_NAMES}


def check_page(html, lang, d):
    ids = re.findall(r'<section class="md" id="([^"]+)">', html)
    assert ids == ORDER, ids
    labels = re.findall(r'<div class="section-label">(\d\d)</div>', html)
    assert labels == ["%02d" % i for i in range(1, len(ORDER) + 1)], labels
    caps = re.findall(r"<figcaption>(.*?)</figcaption>", html)
    assert len(caps) == 11 and html.count('<figure class="rp-fig">') == 11, len(caps)
    for i, c in enumerate(caps, 1):
        assert c.startswith(("図%d　" if lang == "ja" else "Figure %d  ") % i), c[:20]
    srcs = re.findall(r'<img src="([^"?]+)\?v=\d+" width="200" height="100"', html)
    assert srcs == ["%s/%s.svg" % (b.PATH if lang == "ja" else b.PATH_EN, n) for n in b.FIG_NAMES], srcs
    for bad in ("先週の動き", "Last week (", "週ごとの数字", "By week"):
        assert bad not in html, bad
    hero = html.split('class="fl-asof"')[1].split("</div></section>")[0]
    assert hero.index("EPRX") < hero.index("JEPX"), "データの時点は需給調整市場が先"
    daily = html.split('id="daily"')[1].split("</section>")[0]
    n_rows = daily.count("<tr>") - 1
    want = len(set(x["date"] for x in d["eprx"]["daily"]) | set(x["date"] for x in d["jepx"]["daily"] if x["date"] >= d["jepx"]["mtd"]["from"]))
    assert n_rows == want, (n_rows, want)
    first = re.search(r'<tbody><tr><th scope="row">(.*?)</th>', daily).group(1)
    a = datetime.date.fromisoformat(min(d["eprx"]["mtd"]["from"], d["jepx"]["mtd"]["from"]))
    assert first.startswith("%d月1日" % a.month if lang == "ja" else "%s 1 " % b.MONTHS_EN[a.month - 1][:3]), first


def main():
    # 1) ふつうの月の途中
    d = make()
    for lang in ("ja", "en"):
        html, moves, w, core = b.render(d, lang, "2026-11-24", "2026-11", figs())
        check_page(html, lang, d)
        assert len(moves) == 3 and ("需給調整市場" in moves[0] if lang == "ja" else "EPRX" in moves[0]), moves
        assert w is None and not b.safety([core]), b.safety([core])
    ja = b.render(d, "ja", "2026-11-24", "2026-11", figs())[0]
    assert "<h2 class=\"md-h\">今月の動き3つ（2026年11月）</h2>" in ja
    assert "応札倍率が100%以上の日は23日のうち" in ja and "11月1日〜24日（24日分）のうち" in ja
    # 月の初め: 見出しと導入が2つの市場の月を分けて言う／1日分では「◯日のうち」と言わない／前月の値が欠けたら前月の句を出さない
    dd = make(e_month="2026-11", e_days=30, j_month="2026-12", j_days=1)
    t = b.render(dd, "ja", "2026-12-01", "", figs())[0]
    assert "今月の動き3つ（需給調整市場は2026年11月・卸電気は2026年12月）" in t and "月の変わり目のため" in t and "（1日分）のうち" not in t, "月の初め"
    dd = make()
    dd["eprx"]["prev"]["rows"][0]["price"] = None
    dd["jepx"]["prev"]["areas"]["九州"]["s4"] = None
    t = b.render(dd, "ja", "2026-11-24", "", figs())[0].split('id="eprx"')[0]
    assert "—" not in t.split('id="moves"')[1].split('id="kpi"')[0] and "前月の全日は" not in t.split('id="e1"')[1].split("<figure")[0], "前月の値が欠けた時"
    # 2) 月の初め（卸電気は新しい月の1日だけ・需給調整市場の「今月」は前の月）／前月なし／一次オフラインなし／今月が1日だけ
    for kw in ({"e_month": "2026-11", "e_days": 30, "j_month": "2026-12", "j_days": 1}, {"prev": False}, {"offline": False},
               {"e_days": 1, "j_days": 1}, {"e_month": "2027-01", "e_days": 5, "j_month": "2027-01", "j_days": 6}):
        dd = make(**kw)
        for lang in ("ja", "en"):
            html = b.render(dd, lang, "2026-11-24", "", figs())[0]
            check_page(html, lang, dd)
            assert "None" not in html.split("<body")[1] and "nan" not in html.split("<body")[1].lower().replace("finance", ""), kw
    # 3) 入力の検査: 図・日ごとの数字が無ければ焼かない
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "latest.json")

        def load(x):
            json.dump(x, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            return b.load(p)
        assert load(d)[0] is not None
        for cut in ("figs", ("eprx", "daily"), ("eprx", "detail"), ("eprx", "day"), ("jepx", "day")):
            x = copy.deepcopy(d)
            if isinstance(cut, tuple):
                x[cut[0]][cut[1]] = None
            else:
                x.pop(cut)
            got, why = load(x)
            assert got is None and why, cut
        x = copy.deepcopy(d)
        x["eprx"]["daily"] = x["eprx"]["daily"][:-1]
        assert load(x)[0] is None
        x = copy.deepcopy(d)
        x["figs"]["for"]["eprx_day"] = "2026-11-22"                     # 図が数字と別の日の物
        assert load(x)[0] is None
        # 図のファイル: 1枚でも無ければ空
        for lang in ("ja", "en"):
            os.makedirs(os.path.join(t, "figs", lang))
            for n in b.FIG_NAMES:
                open(os.path.join(t, "figs", lang, n + ".svg"), "wb").write(SVG)
        got, why = b.load_figs(d, os.path.join(t, "figs"))
        assert got == {} and "控え" in why, why                           # 日付の控えが無い
        json.dump(d["figs"]["for"], open(os.path.join(t, "figs", "made_for.json"), "w"))
        got, why = b.load_figs(d, os.path.join(t, "figs"))
        assert len(got) == 22 and not why
        x = copy.deepcopy(d)
        x["eprx"]["latest_day"] = "2026-11-24"
        assert b.load_figs(x, os.path.join(t, "figs"))[0] == {}         # 数字だけ新しい
        os.remove(os.path.join(t, "figs", "en", "j5.svg"))
        got, why = b.load_figs(d, os.path.join(t, "figs"))
        assert got == {} and "j5" in why, why
    print("ok")


if __name__ == "__main__":
    main()
