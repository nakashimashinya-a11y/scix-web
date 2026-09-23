#!/usr/bin/env python3
"""access_drop.py（アクセスが減ったページ＋原因の型＋本文の時点）の合成テスト。一時ディレクトリに HTML を作り、本物には触らない。

    python3 scripts/seo/selftest_access_drop.py        # 0=全部通った
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import access_drop as ad  # noqa: E402

TODAY = datetime.date(2026, 9, 22)
HTML = {
    "column-a.html": "<body><h2>現状（2026年6月1日版）</h2><script>var x='2026年9月1日時点';</script></body>",   # 113日前
    "column-b.html": "<body><p>2024年4月公表の結果。締切は2026年1月26日。</p></body>",                        # 時点表現なし
    "column-c.html": "<body><p>令和6年12月1日版。</p><!-- 2026年9月1日時点 --></body>",                        # 2024-12-01＝660日前
    "column-d.html": "<body><p>２０２６年９月１５日版。</p></body>",                                            # 7日前
}
def pg(c, i, pos):
    return {"clicks": c, "impressions": i, "ctr": (c / i if i else 0.0), "position": pos}
PREV = {"/column-a": pg(152, 5311, 5.9), "/column-b": pg(40, 1000, 6.0), "/column-c": pg(30, 900, 7.0),
        "/column-d": pg(50, 2000, 4.0), "/column-e": pg(10, 300, 5.0), "/column-f": pg(100, 3000, 5.0)}
CUR = {"/column-a": pg(92, 4498, 6.2),      # -39%・順位落ち（5.9→6.2 は 1.0 未満）→ 表示減? 4498/5311=0.85 no → CTR 2.0 vs 2.9 = 0.7 → 微妙: CTR落ち
       "/column-b": pg(20, 300, 6.2),       # -50%・表示減
       "/column-c": pg(15, 900, 9.5),       # -50%・順位落ち（+2.5）
       "/column-d": pg(30, 2000, 4.1),      # -40%・CTR落ち（表示同じ・順位ほぼ同じ）
       "/column-e": pg(2, 300, 5.0),        # 前28日が 20 未満＝対象外
       "/column-f": pg(80, 3000, 5.0)}      # -20%＝対象外


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        for name, html in HTML.items():
            (repo / name).write_text("<html>" + html + "</html>", encoding="utf-8")
        rows = ad.drops(CUR, PREV, repo=repo, today=TODAY)
        got = {r["page"]: r for r in rows}
        # 語ごとの帰属: /column-a は「jc-star 蓄電池」が 4.8→6.9 位で -9、「jc star 蓄電池」が表示 36→2 で -4、「jcstar」が CTR 3.3→0.8% で -4
        #   「蓄電池 jc-star」は当ページで表示 58→0、別ページ /column-levels で 60 表示＝着地移動（-2）
        PQP = {("jc-star 蓄電池", "/column-a"): pg(9, 137, 4.8), ("jc star 蓄電池", "/column-a"): pg(4, 36, 4.0),
               ("jcstar", "/column-a"): pg(7, 213, 7.9), ("jc-star 義務化", "/column-a"): pg(3, 74, 6.6),
               ("蓄電池 jc-star", "/column-a"): pg(2, 58, 4.1)}
        QP = {("jc-star 蓄電池", "/column-a"): pg(0, 30, 6.9), ("jc star 蓄電池", "/column-a"): pg(0, 2, 8.0),
              ("jcstar", "/column-a"): pg(3, 370, 8.3), ("jc-star 義務化", "/column-a"): pg(2, 82, 6.3),
              ("蓄電池 jc-star", "/column-levels"): pg(0, 60, 8.0)}
        rq = {r["page"]: r for r in ad.drops(CUR, PREV, QP, PQP, repo=repo, today=TODAY)}
        ja = rq.get("/column-a", {})
        # 失った 20 のうち 順位落ち 13（65%）・CTR落ち 5（25%）・着地移動 2（10%）
        if ja.get("judge") != "順位落ち" or "順位落ち 65%" not in ja.get("judge_detail", "") or "着地移動 10%" not in ja.get("judge_detail", ""):
            ok = False; print("NG 語ごとの帰属:", ja.get("judge"), ja.get("judge_detail"))
        if rq.get("/column-d", {}).get("judge") != "CTR落ち":   # 語の内訳が無いページはページ合計の判定に落ちる
            ok = False; print("NG 予備判定:", rq.get("/column-d", {}).get("judge"))
        want_pages = {"/column-a", "/column-b", "/column-c", "/column-d"}
        if set(got) != want_pages:
            ok = False; print("NG 対象:", sorted(got), "期待:", sorted(want_pages))
        if rows and rows[0]["page"] != "/column-a":
            ok = False; print("NG 並び（失ったクリック順）:", [r["page"] for r in rows])
        checks = {
            "/column-a": ("2026年6月1日版", 113, "本文の時点更新（CC）"),
            "/column-b": (None, None, "本文の受け皿を見直す（CC 判断）"),
            "/column-c": ("令和6年12月1日版", 660, "本文の時点更新（CC）"),
            "/column-d": ("2026年9月15日版", 7, "title・description（週次）"),
        }
        for page, (expr, age, nxt) in checks.items():
            r = got.get(page) or {}
            if (r.get("expr"), r.get("age_days"), r.get("next")) != (expr, age, nxt):
                ok = False; print(f"NG {page}: {(r.get('expr'), r.get('age_days'), r.get('next'))} 期待 {(expr, age, nxt)}")
        if "表示減" not in got.get("/column-b", {}).get("judge", "") or "順位落ち" not in got.get("/column-c", {}).get("judge", "") \
                or got.get("/column-d", {}).get("judge") != "CTR落ち":
            ok = False; print("NG 原因の型:", {p: got[p]["judge"] for p in got})
        if got.get("/column-a", {}).get("pct") != -39:
            ok = False; print("NG 減少率:", got.get("/column-a", {}).get("pct"))
        line = ad.tg_line(rows)
        if "/column-a" not in line or f"ほか{len(rows) - 1}本" not in line or "152→92" not in line:
            ok = False; print("NG Telegram の 1 行:", line)
        if ad.tg_line([]) != "":
            ok = False; print("NG 0 本なのに 1 行が出る")
        L = []; ad.render(L, rows, limit=2)
        if "…ほか" not in "\n".join(L) or "| /column-a |" not in "\n".join(L):
            ok = False; print("NG 11 節:", L[-3:])
        # 4 節と同じ基準（前28日20以上・7割未満）
        if ad.MIN_PREV_CLICKS != 20 or ad.DROP_RATIO != 0.7:
            ok = False; print("NG しきい値が 4 節とずれた")
    print("OK access_drop" if ok else "NG access_drop")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
