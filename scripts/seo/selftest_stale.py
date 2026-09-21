#!/usr/bin/env python3
"""stale_pages.py（本文の時点が古いページ）の合成テスト。一時ディレクトリに HTML を作り、本物のリポジトリには触らない。

    python3 scripts/seo/selftest_stale.py        # 0=全部通った
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stale_pages as sp  # noqa: E402

TODAY = datetime.date(2026, 9, 22)
PAGES = {
    # 名前: (中身, 期待=古い/新しい/判定しない)
    "column-old.html": ("<body><p>制度の現状（2026年1月時点）。</p><script>var x='2026年9月1日時点';</script></body>", "古い"),
    "column-fresh.html": ("<body><h2>適合製品の現状（2026年9月15日版）</h2></body>", "新しい"),
    "column-mixed.html": ("<body><p>2025年10月時点の一覧。</p><p>2026年8月22日時点で更新。</p></body>", "新しい"),
    "column-nomark.html": ("<body><p>2024年4月公表の約定結果。応札締切は2026年1月26日です。</p></body>", "判定しない"),
    "column-reiwa.html": ("<body><p>令和6年12月1日版のガイドライン。</p></body>", "古い"),
    "column-zenkaku.html": ("<body><p>２０２６年２月時点。</p></body>", "古い"),
    "column-comment.html": ("<body><!-- 2026年9月1日時点 --><p>2026年2月現在の一覧。</p></body>", "古い"),
    "column-badday.html": ("<body><p>2026年13月時点。</p></body>", "判定しない"),
    "zh-column-old.html": ("<body><p>2026年1月時点</p></body>", "判定しない"),
    "404.html": ("<body><p>2025年1月時点</p></body>", "判定しない"),
}


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        for name, (html, _) in PAGES.items():
            (repo / name).write_text("<html>" + html + "</html>", encoding="utf-8")
        rows = sp.scan(repo=repo, today=TODAY, clicks={"/column-old": 92, "/column-reiwa": 5})
        got = {r["file"]: r for r in rows}
        for name, (_, want) in PAGES.items():
            is_stale = name in got
            if (want == "古い") != is_stale:
                ok = False
                print(f"NG {name}: 期待={want} 実際={'古い' if is_stale else '古くない/判定しない'}")
        # 並び: クリック多い順（/column-old 92 が先頭）
        if rows and rows[0]["file"] != "column-old.html":
            ok = False; print("NG 並び: 先頭が", rows[0]["file"])
        r = got.get("column-old.html") or {}
        if r.get("asof") != "2026-01-01" or r.get("age_days") != 264 or r.get("expr") != "2026年1月時点":
            ok = False; print("NG column-old の値:", r)
        r = got.get("column-reiwa.html") or {}
        if r.get("asof") != "2024-12-01":
            ok = False; print("NG 令和の換算:", r)
        line = sp.tg_line(rows)
        if "/column-old" not in line or f"ほか{len(rows) - 1}本" not in line:
            ok = False; print("NG Telegram の 1 行:", line)
        if sp.tg_line([]) != "":
            ok = False; print("NG 0 本なのに 1 行が出る")
        L = []; sp.render(L, rows, limit=2)
        if "…ほか" not in "\n".join(L):
            ok = False; print("NG 11 節の省略行が無い")
    print("OK stale_pages" if ok else "NG stale_pages")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
