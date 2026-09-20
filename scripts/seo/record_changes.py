#!/usr/bin/env python3
"""週次自動更新と月1回の構成レビューの記帳。マニフェスト（changes.json）から
  --changelog PATH  docs/seo-change-log.md の表の先頭に行を足す（公開リポジトリ＝GSC の数字だけ・GA4 のリード数は書かない）
  --commit SHA      Drive の台帳 ledger/changes.jsonl に効果測定の対象として追記する（変更前の28日値を焼き込む）
  --source structure
                    月1回の構成レビューが **自動で公開した** 変更（2026-09-20〜）。上の 2 つと組み合わせる。変更台帳には
                    source=structure・id structure-YYYYMM-N・check_days [14, 28] で入る＝週次の変更と同じく measure_changes.py が
                    14 日後・28 日後に前後比較し、worse なら翌週のブリーフ 8 節で差し戻し候補になる。measure と private_note
                    （問い合わせの件数はここにだけ書ける）も台帳に残す。既定は auto（週次）
  --proposal --commit SHA --branch B [--pr N --pr-url U]
                    構成レビューのうちナビ（header.js）を含む回（未公開・PR で提案）。ledger/proposals.jsonl に status=proposed で残す。
                    変更台帳には書かない＝公開されるまで効果測定も「今週触らないページ」も動かさない。マージされたら
                    register_structure_merges.py が変更台帳へ移す
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, append_jsonl, read_jsonl, today  # noqa: E402


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
    ap.add_argument("--source", choices=("auto", "structure"), default="auto",
                    help="structure＝構成レビューが自動で公開した変更（変更台帳に source=structure で入る）")
    ap.add_argument("--proposal", action="store_true", help="構成レビューの提案として proposals.jsonl に残す（未公開）")
    ap.add_argument("--branch")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--pr-url")
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    brief = json.loads(Path(a.brief).read_text(encoding="utf-8")) if Path(a.brief).exists() else {}
    changes = man.get("changes") or []
    structure = a.source == "structure"
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
            rows.append(f"| {day} | {pages} | {summ}（{'自動・構成レビュー' if structure else '自動'}・{c.get('class')}。根拠: {rat}） | "
                        f"{'auto(structure)' if structure else 'auto'} {day} #{n} | "
                        f"{before_text(c.get('pages') or [], brief)} | {c14} / {c28} | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: {kpi} |")
        text = text[:j] + "\n".join(rows) + "\n" + text[j:]
        p.write_text(text, encoding="utf-8")
        print(f"changelog に {len(rows)} 行")

    if a.proposal:
        if a.dry_ledger or not a.commit:
            print("提案の記帳は --commit が要る（--dry-ledger なら書かない）"); return 0
        path = LEDGER / "ledger" / "proposals.jsonl"
        have = {e.get("id") for e in read_jsonl(path)}
        n_written = 0
        for n, c in enumerate(changes, 1):
            pid = f"structure-{day.strftime('%Y%m')}-{n}"
            while pid in have:   # 同じ月に出し直したとき
                pid += "b"
            have.add(pid)
            rec = {"id": pid, "date": str(day), "status": "proposed", "source": "structure", "branch": a.branch,
                   "pr": a.pr, "pr_url": a.pr_url, "commit": a.commit, "files": c.get("files"),
                   "pages": c.get("pages") or [], "class": c.get("class"), "summary": c.get("summary"),
                   "rationale": c.get("rationale"), "hypothesis": c.get("hypothesis"), "kpi": c.get("kpi"),
                   "measure": c.get("measure"), "private_note": c.get("private_note"),
                   "before": {p: (brief.get("pages") or {}).get(p) for p in (c.get("pages") or [])}}
            if c.get("nav_rule") is not None:
                rec["nav_rule"] = c.get("nav_rule")
            append_jsonl(path, rec); n_written += 1
        print(f"提案を {n_written} 件（{path.name}・未公開）")
        return 0

    if a.commit and not a.dry_ledger:
        path = LEDGER / "ledger" / "changes.jsonl"
        # 構成レビューの id は提案（PR の経路）と同じ形＝同じ月に手で回し直しても、PR のマージの記帳とも重ならないようにする
        have = ({e.get("id") for e in read_jsonl(path)} | {e.get("id") for e in read_jsonl(LEDGER / "ledger" / "proposals.jsonl")}
                if structure else set())
        for n, c in enumerate(changes, 1):
            cid = f"structure-{day.strftime('%Y%m')}-{n}" if structure else f"auto-{day.strftime('%Y%m%d')}-{n}"
            while cid in have:
                cid += "b"
            have.add(cid)
            rec = {"id": cid, "date": str(day), "source": a.source,
                   "commit": a.commit, "files": c.get("files"), "pages": c.get("pages") or [],
                   "class": c.get("class"), "summary": c.get("summary"), "rationale": c.get("rationale"),
                   "hypothesis": c.get("hypothesis"), "kpi": c.get("kpi"),
                   "before": {p: (brief.get("pages") or {}).get(p) for p in (c.get("pages") or [])},
                   "check_days": [14, 28], "measured": {}}
            if structure:
                rec["measure"] = c.get("measure")
                if c.get("private_note"):
                    rec["private_note"] = c.get("private_note")
                if c.get("class") == "nav":   # ナビは PR の経路にしか出さないが、万一ここへ来ても90日ルールの起点にする
                    rec["nav_change"] = True
            append_jsonl(path, rec)
        print(f"台帳に {len(changes)} 件（source={a.source}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
