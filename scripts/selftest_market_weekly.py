#!/usr/bin/env python3
"""build_market_data.weekly_series の自己試験（合成の一覧と履歴だけ・git も本物の一覧も読まない）。
    python3 scripts/selftest_market_weekly.py"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_market_data as b  # noqa: E402

D = datetime.date


def P(i, mw, volt, scheme, fs):
    return {"id": i, "mw": mw, "voltage": volt, "scheme": scheme, "firstSeen": fs}


def main():
    a = [P("T1", 2.0, "高圧", "完成渡し", "2026-09-08")]
    c = a + [P("T2", 20.0, "特別高圧", "権利譲渡", "2026-09-16")]
    snaps = {"a": a, "b": c}
    hist = [(D(2026, 9, 8), "a"), (D(2026, 9, 16), "b")]
    r = b.weekly_series(c, D(2026, 9, 20), hist, snaps.get)
    assert [x["n"] for x in r] == [1, 2], r
    assert [x["new"] for x in r] == [1, 1], r
    assert r[1]["mw"] == 22 and r[1]["ehv"] == 1 and r[1]["rights"] == 1, r
    assert b.weekly_series(c, D(2026, 9, 20), [], snaps.get) == []
    assert b.weekly_section_ja(r[:1], "2026-09-20") == ""      # 1週だけなら節を出さない
    html = b.weekly_section_ja(r, "2026-09-20") + b.weekly_section_en(r, "2026-09-20")
    for bad in ("T1", "T2", "売却", "sold"):
        assert bad not in html, bad
    # MW が空の案件が5%を超える週は MW を出さない（表は「—」）・電圧未設定は注記で差を示す
    d = [P("T%d" % i, None if i < 3 else 2.0, "高圧", "完成渡し", "2026-09-08") for i in range(10)] + [P("X", 1.0, None, None, "2026-09-09")]
    rr = b.weekly_series(d, D(2026, 9, 20), [(D(2026, 9, 8), "a")], {"a": d}.get)
    assert rr[-1]["mw_ok"] is False and rr[-1]["other_v"] == 1 and rr[0]["mw_missing"] == 3, rr
    rr2 = [dict(rr[-1], week="2026-09-07", mw_ok=True, mw=100), rr[-1]]
    h2 = b.weekly_section_ja(rr2, "2026-09-20")
    assert "<td class=\"n\">—</td>" in h2 and "電圧が未設定の案件（直近は1件）" in h2, h2[:200]
    # 欠けの週は MW の図から外す（空の枠を残さない）・MW の図に出せる週が2未満なら図を出さず表を案内する
    assert len(b._mw_rows(rr2)) == 1 and "表を見てください" in b._mw_chart_ja(rr2)
    rr3 = [dict(rr2[0], week="2026-08-31"), rr2[0], rr[-1]]
    c3 = b._mw_chart_ja(rr3)
    assert c3.count("<rect") == 2 * 2 and "値の欠けた1週は図に出していません" in c3, c3
    print("ok")


if __name__ == "__main__":
    main()
