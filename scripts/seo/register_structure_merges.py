#!/usr/bin/env python3
"""月1回の構成レビューの提案（PR）がマージされたら、変更台帳（ledger/changes.jsonl）へ記帳する。

    python3 scripts/seo/register_structure_merges.py         # 記帳する（collect_daily.py が毎朝、効果測定の前に呼ぶ）
    python3 scripts/seo/register_structure_merges.py --dry   # 書かずに一覧

提案は weekly_run.sh（MODE=structure）が ledger/proposals.jsonl に status=proposed で残す（PR 番号つき・未公開）。
ここでは origin/main の履歴だけを見て、マージされたものを見つける（gh は使わない＝launchd でも認証に依らない）:
  1. PR 番号があれば、件名が「…(#NN)」（squash マージ＝このリポジトリの慣例）か「Merge pull request #NN …」のコミット
  2. PR 番号が無い（gh が失敗して枝だけ push した）ときは、提案のコミットと同じ中身のファイルを持つコミット
     （提案のコミットが手元に残っているときだけ。見つからなければ proposed のまま）
見つけたら、変更日＝マージコミットの日付で変更台帳に足し（id は提案と同じ＝何度走っても重複しない。効果測定は
measure_changes.py が 14 日後・28 日後に前後比較）、提案を status=merged にする。class=nav は nav_change=true を
付ける＝「ナビの組み替えは90日に1回まで」の起点になる。60 日マージされなかった提案は expired（不採用とみなす）。
PR を閉じたかどうかは見ない（gh が要る）＝閉じた提案は 60 日後に expired になる。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import append_jsonl, d, log, read_jsonl, today, write_jsonl  # noqa: E402
import newpages as npg  # noqa: E402
import structure as st  # noqa: E402

EXPIRE_DAYS = 60


def commits_since(date_str: str) -> list:
    out = npg.git("log", npg.ref(), f"--since={date_str} 00:00", "--format=%H%x09%cs%x09%s")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append(parts)
    return rows[::-1]  # 古い順＝最初に載ったコミットを採る


def blob(sha: str, rel: str) -> str:
    return npg.git("rev-parse", "--verify", "--quiet", f"{sha}:{rel}").strip()


def find_merge(p: dict, claimed=()):
    rows = commits_since(p["date"])
    pr = p.get("pr")
    if pr:
        rx = re.compile(r"\(#%d\)\s*$|^Merge pull request #%d\b" % (int(pr), int(pr)))
        for sha, date, subj in rows:
            if rx.search(subj):
                return sha, date, subj
        return None
    files = [f for f in (p.get("files") or []) if f]
    want = {f: blob(p.get("commit") or "", f) for f in files}
    if not files or not all(want.values()):
        return None  # 提案のコミットが手元に無い
    for sha, date, subj in rows:
        if sha in claimed:   # 別の提案のマージとして記帳済み（同じ中身の出し直しを二重に数えない）
            return None
        if sha != p.get("commit") and all(blob(sha, f) == want[f] for f in files):
            return sha, date, subj
    return None


def publishable_ref() -> bool:
    return npg.ref() != "HEAD" or bool(os.environ.get("SCIX_WEB_REF"))


def run(dry: bool = False) -> list:
    """記帳した（dry なら記帳するはずの）変更台帳のエントリを返す。"""
    props = st.proposals()
    if not props or not any(p.get("status") == "proposed" for p in props):
        return []
    if not publishable_ref():
        log("構成の提案の記帳: origin/main が見つからないので見送る")
        return []
    ids = {e.get("id") for e in read_jsonl(st.CHANGES)}
    new, changed = [], False
    claimed = {p.get("merge_commit") for p in props if p.get("merge_commit")}
    for p in sorted(props, key=lambda x: 0 if x.get("pr") else 1):   # PR 番号のある提案を先に（確実なほうから）
        if p.get("status") != "proposed":
            continue
        hit = find_merge(p, claimed)
        if hit:
            sha, date, subj = hit
            e = {"id": p["id"], "date": date, "source": "structure", "commit": sha, "files": p.get("files"),
                 "pages": p.get("pages") or [], "class": p.get("class"), "summary": p.get("summary"),
                 "rationale": p.get("rationale"), "hypothesis": p.get("hypothesis"), "kpi": p.get("kpi"),
                 "measure": p.get("measure"), "before": p.get("before") or {}, "proposed_on": p.get("date"),
                 "check_days": [14, 28], "measured": {}}
            if p.get("pr"):
                e["pr"] = p["pr"]
            if p.get("class") == "nav":
                e["nav_change"] = True
            if e["id"] not in ids:
                new.append(e); ids.add(e["id"])
                if not dry:
                    append_jsonl(st.CHANGES, e)
            p.update({"status": "merged", "merged_on": date, "merge_commit": sha}); changed = True
            claimed.add(sha)
        elif (today() - d(p["date"])).days > EXPIRE_DAYS:
            p.update({"status": "expired", "expired_on": str(today())}); changed = True
    if changed and not dry:
        write_jsonl(st.PROPOSALS, props)
    return new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="台帳に書かずに一覧")
    a = ap.parse_args()
    for e in run(dry=a.dry):
        print(f"{'（dry）' if a.dry else '記帳'} {e['date']} {e['id']} [{e['class']}] {' '.join(e['pages'])} — {e['commit'][:10]}")
    for p in st.proposals():
        print(f"{p.get('date')} {p.get('id')} {p.get('status')} " + (f"#{p['pr']}" if p.get("pr") else str(p.get("branch"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
