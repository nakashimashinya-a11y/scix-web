#!/usr/bin/env python3
"""手動 PR で足したページを、変更台帳（ledger/changes.jsonl）へ自動で記帳する。

    python3 scripts/seo/register_new_pages.py            # 記帳する（collect_daily.py が毎朝、効果測定の前に呼ぶ）
    python3 scripts/seo/register_new_pages.py --dry      # 書かずに一覧
    python3 scripts/seo/register_new_pages.py --days 60  # さかのぼる日数（既定 28）

origin/main の git 履歴から、直近 N 日に **足された** *.html を拾う。3言語版（column-x.html・
en/column-x.html・zh-column-x.html）は 1 エントリにまとめる。id は new-<slug> 固定＝何度走っても重複しない。
台帳のどれかのエントリの pages に既に入っているページは足さない（手で記帳した PR・週次の自動 new-column と二重にしない）。
JA を先に出して EN/ZH を後から足したとき（new-<slug> が既にある）は new-<slug>-en-zh として残りだけを記帳する。
効果測定は measure_changes.py が「立ち上がり」で判定する（前後比較はしない＝前の窓が無い）。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import datetime
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, append_jsonl, log, read_jsonl, today  # noqa: E402
import newpages as npg  # noqa: E402

CHANGES = LEDGER / "ledger" / "changes.jsonl"
KPI = "立ち上がり: 14日で表示が出るか・28日の表示が同じ言語の既存コラムの中央値を超えるか"


def page_title(rel: str) -> str:
    m = re.search(r"<title>(.*?)</title>", npg.git("show", f"{npg.ref()}:{rel}"), re.S)
    return html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""


def candidates(days: int) -> list:
    """直近 days 日に足され、いまも ref に在るページを slug ごとにまとめる。"""
    since = str(today() - datetime.timedelta(days=days))
    added = npg.added_commits()
    groups = {}
    for r in npg.site_pages():
        a = added.get(r["file"])
        if not a or a[0] < since:
            continue
        groups.setdefault(r["slug"], []).append({**r, "added": a[0], "sha": a[1], "subject": a[2]})
    out = []
    for slug, rows in groups.items():
        rows.sort(key=lambda r: npg.LANG_ORDER[r["lang"]])
        out.append({"slug": slug, "rows": rows})
    def natural(slug):  # column-somosomo-2 を -10 より前に
        return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", slug)]
    return sorted(out, key=lambda g: (min(r["added"] for r in g["rows"]), natural(g["slug"])))


def plan(days: int):
    """(足すエントリ, 見送り [(slug, 理由)])。台帳は読むだけ。"""
    entries = read_jsonl(CHANGES)
    ids = {e.get("id") for e in entries}
    covered = {}
    for e in entries:
        for p in e.get("pages") or []:
            covered.setdefault(p, e.get("id"))
    new, skipped = [], []
    for g in candidates(days):
        rows = [r for r in g["rows"] if r["page"] not in covered]
        if not rows:
            skipped.append((g["slug"], "記帳済み（" + "・".join(sorted({covered[r["page"]] for r in g["rows"]})) + "）"))
            continue
        eid = f"new-{g['slug']}"
        if eid in ids:  # JA 先行 → EN/ZH を後から足した
            eid = f"new-{g['slug']}-" + "-".join(r["lang"] for r in rows)
        if eid in ids:
            skipped.append((g["slug"], f"id が既にある（{eid}）"))
            continue
        ids.add(eid)
        first = min(rows, key=lambda r: (r["added"], npg.LANG_ORDER[r["lang"]]))
        pr = re.search(r"\(#(\d+)\)\s*$", first["subject"])
        e = {"id": eid, "date": first["added"], "source": "manual-auto", "commit": first["sha"],
             "files": [r["file"] for r in rows], "pages": [r["page"] for r in rows],
             "class": "new-column" if g["slug"].startswith("column-") else "new-page",
             "summary": ("新規ページ: " + page_title(rows[0]["file"]))[:120],
             "rationale": first["subject"][:120], "kpi": KPI,
             "check_days": [14, 28], "measured": {}}
        if pr:
            e["pr"] = int(pr.group(1))
        new.append(e)
    return new, skipped


def publishable_ref() -> bool:
    """本番（origin/main）か、明示された ref のときだけ書く。HEAD への黙った代替では書かない
    （作業ブランチの未公開ページを台帳に入れない）。"""
    return npg.ref() != "HEAD" or bool(os.environ.get("SCIX_WEB_REF"))


def run(days: int = 28, dry: bool = False) -> list:
    if not dry and not publishable_ref():
        log("新規ページの記帳: origin/main が見つからないので書かない")
        return []
    new, _ = plan(days)
    if not dry:
        for e in new:
            append_jsonl(CHANGES, e)
    return new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="台帳に書かずに一覧")
    ap.add_argument("--days", type=int, default=28)
    a = ap.parse_args()
    if not a.dry and not publishable_ref():
        print("origin/main が見つからない（SCIX_WEB_REF も無い）。書かずに終了。--dry なら HEAD で一覧できる", file=sys.stderr)
        return 1
    new, skipped = plan(a.days)
    for e in new:
        print(f"{'（dry）' if a.dry else '記帳'} {e['date']} {e['id']} [{e['class']}] {' '.join(e['pages'])} — {e['summary'][:70]}")
        if not a.dry:
            append_jsonl(CHANGES, e)
    for slug, why in skipped:
        print(f"見送り {slug}: {why}")
    n_pages = sum(len(e["pages"]) for e in new)
    print(f"{'書かずに終了' if a.dry else '台帳に追記'}: {len(new)} エントリ・{n_pages} ページ（直近 {a.days} 日・{npg.ref()}）／見送り {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
