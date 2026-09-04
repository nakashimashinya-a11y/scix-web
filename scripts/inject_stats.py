#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projects.json の集計値を HTML のマーカーへ静的に焼き込む。

なぜJSで描かないか: サイトへの流入のうち AI Assistant 経由はCVRが最も高く、
その経路はJavaScriptを実行しない。fetch で件数を入れると、その読み手には
H1が「販売中の案件、件。」と読まれてしまう。だから毎朝の同期でHTMLに直接書く。

マーカーの形:  <!--S:count-->127<!--/S:count-->
中身だけを置き換えるので、HTMLの構造には触れない。

使い方:
    python3 scripts/inject_stats.py            # 書き換えて差分を報告
    python3 scripts/inject_stats.py --check    # 書き換えずに、ずれているかだけ見る
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["index.html"]


def compute(projects_json):
    with open(projects_json, encoding="utf-8") as f:
        data = json.load(f)
    ps = data.get("projects", [])
    mw_total = sum(p["mw"] for p in ps if isinstance(p.get("mw"), (int, float)))
    mws = [p["mw"] for p in ps if isinstance(p.get("mw"), (int, float))]
    return {
        "count": f"{len(ps):,}",
        "mw": f"{round(mw_total):,}",
        "prefs": str(len({p.get("pref") for p in ps if p.get("pref")})),
        "areas": str(len({p.get("area") for p in ps if p.get("area")})),
        "shv": str(sum(1 for p in ps if p.get("voltage") == "特別高圧")),
        "maxmw": f"{round(max(mws)) if mws else 0:,}",
        "date": data.get("generatedAt", ""),
    }


def main():
    check = "--check" in sys.argv
    stats = compute(os.path.join(ROOT, "projects.json"))
    changed, stale = 0, []

    for name in TARGETS:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        out = src
        for key, value in stats.items():
            pattern = re.compile(
                r"(<!--S:" + key + r"-->)(.*?)(<!--/S:" + key + r"-->)", re.S)
            def repl(m, v=value, k=key, n=name):
                if m.group(2) != v:
                    stale.append(f"{n} {k}: {m.group(2)} → {v}")
                return m.group(1) + v + m.group(3)
            out = pattern.sub(repl, out)
        if out != src:
            changed += 1
            if not check:
                open(path, "w", encoding="utf-8").write(out)

    for line in stale:
        print("  " + line)
    if check:
        print(f"[check] 要更新 {changed} ファイル")
        return 1 if changed else 0
    print(f"[ok] {changed} ファイルを更新（件数 {stats['count']}・{stats['mw']}MW・"
          f"{stats['prefs']}都道府県・特高{stats['shv']}件・{stats['date']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
