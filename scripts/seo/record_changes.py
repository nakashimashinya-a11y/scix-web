#!/usr/bin/env python3
"""週次自動更新の記帳。マニフェスト（changes.json）から
  --changelog PATH  docs/seo-change-log.md の表の先頭に行を足す（公開リポジトリ＝GSC の数字だけ・GA4 のリード数は書かない）
  --commit SHA      Drive の台帳 ledger/changes.jsonl に効果測定の対象として追記する（変更前の28日値を焼き込む）
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, append_jsonl, today  # noqa: E402


def before_text(pages, brief):
    parts = []
    for p in pages:
        a = (brief.get("pages") or {}).get(p)
        if a:
            pos = f"{a['position']:.1f}位" if a.get("position") else "-"
            parts.append(f"{p} クリック{a['clicks']}・表示{a['impressions']}・CTR{a['ctr']*100:.1f}%・{pos}")
        else:
            parts.append(f"{p} 表示なし")
    return "／".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--changelog")
    ap.add_argument("--commit")
    ap.add_argument("--dry-ledger", action="store_true", help="台帳には書かない（changelog だけ）")
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    brief = json.loads(Path(a.brief).read_text(encoding="utf-8")) if Path(a.brief).exists() else {}
    changes = man.get("changes") or []
    day = today()
    c14, c28 = day + datetime.timedelta(days=14), day + datetime.timedelta(days=28)

    if a.changelog:
        p = Path(a.changelog)
        text = p.read_text(encoding="utf-8")
        anchor = "## 変更（新しいものを上に）"
        i = text.find(anchor)
        if i < 0:
            print("changelog に見出しが無い", file=sys.stderr); return 1
        j = text.find("|---|", i)
        j = text.find("\n", j) + 1
        rows = []
        for n, c in enumerate(changes, 1):
            pages = " ".join(c.get("pages") or [])
            summ = str(c.get("summary", "")).replace("|", "｜").replace("\n", " ")
            rat = str(c.get("rationale", "")).replace("|", "｜").replace("\n", " ")
            kpi = str(c.get("kpi", "")).replace("|", "｜").replace("\n", " ")
            rows.append(f"| {day} | {pages} | {summ}（自動・{c.get('class')}。根拠: {rat}） | auto {day} #{n} | "
                        f"{before_text(c.get('pages') or [], brief)} | {c14} / {c28} | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: {kpi} |")
        text = text[:j] + "\n".join(rows) + "\n" + text[j:]
        p.write_text(text, encoding="utf-8")
        print(f"changelog に {len(rows)} 行")

    if a.commit and not a.dry_ledger:
        for n, c in enumerate(changes, 1):
            append_jsonl(LEDGER / "ledger" / "changes.jsonl", {
                "id": f"auto-{day.strftime('%Y%m%d')}-{n}", "date": str(day), "source": "auto",
                "commit": a.commit, "files": c.get("files"), "pages": c.get("pages") or [],
                "class": c.get("class"), "summary": c.get("summary"), "rationale": c.get("rationale"),
                "hypothesis": c.get("hypothesis"), "kpi": c.get("kpi"),
                "before": {p: (brief.get("pages") or {}).get(p) for p in (c.get("pages") or [])},
                "check_days": [14, 28], "measured": {},
            })
        print(f"台帳に {len(changes)} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
