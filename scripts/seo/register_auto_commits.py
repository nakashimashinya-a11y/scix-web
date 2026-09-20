#!/usr/bin/env python3
"""自動で公開したのに変更台帳（ledger/changes.jsonl）に載っていないコミットを拾い直す。

    python3 scripts/seo/register_auto_commits.py         # 記帳する（collect_daily.py が毎朝、効果測定の前に呼ぶ）
    python3 scripts/seo/register_auto_commits.py --dry   # 書かずに一覧

weekly_run.sh は main へ push した **あとで** 変更台帳（Drive）に記帳する。そこで失敗すると（台帳に書けない・毎朝の効果測定の
書き戻しと重なって追記が消える）、公開は済んでいるのに効果測定の対象にならず、ブリーフ 8 節にも出ず、翌月に同じ案がまた出る。
構成の変更は承認なしで公開している＝「14 日後・28 日後に測って、悪ければ週次が戻す」が人の目の代わりなので、黙って外さない。

  対象      origin/main の直近 LOOKBACK_DAYS 日のコミットで、件名が「auto(seo): 」「auto(structure): 」で始まるもの。
            PR のマージ（件名の末尾が (#NN)）は register_structure_merges.py の仕事なので除く
  記帳済み  変更台帳のどれかのエントリの commit がそのコミット（PR の経路は proposals.jsonl の merge_commit も）
  中身      コミット本文の「…scix-web解析/weekly/<日付>[/structure]」（無ければコミットの日付）から、その回のマニフェスト
            weekly/<日付>[/structure]/changes.json と brief.json。マニフェストの files がそのコミットの変更ファイルに
            含まれているときだけ採る（別の回・DRY_RUN のマニフェストを拾わない）
  変更日    コミットの日付（今日ではない）。レコードの形は record_changes.ledger_records と同じ＝source は auto／structure
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, append_jsonl, d, jload, log, read_jsonl  # noqa: E402
import newpages as npg  # noqa: E402
from record_changes import ledger_records  # noqa: E402

LOOKBACK_DAYS = 35      # 28 日後の判定に間に合う範囲
SUBJECT_RE = re.compile(r"^auto\((seo|structure)\): ")
MERGE_RE = re.compile(r"\(#\d+\)\s*$")
RUN_DIR_RE = re.compile(r"scix-web解析/weekly/(\d{4}-\d{2}-\d{2})(/structure)?")


def auto_commits() -> list:
    """[(sha, 日付, source, 件名, 本文)]。古い順。"""
    out = npg.git("log", npg.ref(), f"--since={LOOKBACK_DAYS}.days", "--format=%H%x09%cs%x09%s%x09%b%x1e")
    rows = []
    for rec in out.split("\x1e"):
        parts = rec.strip("\n").split("\t", 3)
        if len(parts) < 3:
            continue
        sha, date, subj = parts[0].strip(), parts[1], parts[2]
        m = SUBJECT_RE.match(subj)
        if m and not MERGE_RE.search(subj):
            rows.append((sha, date, "structure" if m.group(1) == "structure" else "auto", subj, parts[3] if len(parts) > 3 else ""))
    return rows[::-1]


def run(dry: bool = False) -> list:
    """記帳した（dry なら記帳するはずの）変更台帳のエントリを返す。"""
    if npg.ref() == "HEAD" and not os.environ.get("SCIX_WEB_REF"):
        log("自動公開の拾い直し: origin/main が見つからないので見送る")
        return []
    path = LEDGER / "ledger" / "changes.jsonl"
    ledger = read_jsonl(path)
    props = read_jsonl(LEDGER / "ledger" / "proposals.jsonl")
    done = [str(e.get("commit") or "") for e in ledger] + [str(p.get("merge_commit") or "") for p in props]
    have = {e.get("id") for e in ledger} | {p.get("id") for p in props}
    new = []
    for sha, date, source, subj, body in auto_commits():
        if any(c and (sha.startswith(c) or c.startswith(sha)) for c in done):
            continue
        m = RUN_DIR_RE.search(body)
        run_dir = LEDGER / "weekly" / (m.group(1) if m else date)
        if source == "structure":
            run_dir = run_dir / "structure"
        man = jload(run_dir / "changes.json")
        changes = [c for c in ((man or {}).get("changes") or []) if isinstance(c, dict)]
        if not changes:
            log(f"自動公開の拾い直し: {sha[:10]}（{subj[:40]}）のマニフェストが無い（{run_dir}）＝手で記帳する")
            continue
        touched = set(npg.git("show", "--name-only", "--format=", sha).split())
        listed = {f for c in changes for f in (c.get("files") or [])}
        if not listed or not listed <= touched:
            log(f"自動公開の拾い直し: {sha[:10]} とマニフェスト（{run_dir}）の files が合わない＝別の回のもの。飛ばす")
            continue
        recs = ledger_records(changes, jload(run_dir / "brief.json") or {}, source, sha, d(date), have)
        for rec in recs:
            rec["recovered"] = True   # push のあとの記帳が失敗し、あとから拾い直したもの
            if not dry:
                append_jsonl(path, rec)
        new.extend(recs)
    return new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="台帳に書かずに一覧")
    a = ap.parse_args()
    for e in run(dry=a.dry):
        print(f"{'（dry）' if a.dry else '記帳'} {e['date']} {e['id']} [{e['class']}] {' '.join(e['pages'])} — {e['commit'][:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
