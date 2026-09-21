#!/usr/bin/env python3
"""本文の「時点」が古い JA ページを機械で見つける（LLM 不使用・読むだけ）。

なぜ（2026-09-22 中島決定・選択肢①）:
  週次の Claude（weekly_run.sh）には Read・Edit・Grep しか渡していない＝外部サイトに出られない。
  だから一次資料（官公庁・OCCTO・IPA）が要る「本文の時点更新」は自動ではやらない。
  代わりに、週次ジョブが「本文の時点が古いページ」をブリーフ 11 節と日曜朝の Telegram の 1 行に出し、
  更新は CC の作業セッションで中島さんの指示で行う（/column-jcstar・/column-lda の PR #95 と同じ型）。

判定（決定論）:
  本文（<body> の見える文字。script・style・コメント・タグを除く）から、ページが自分で名乗っている時点＝
    「YYYY年M月[D日](時点|版|現在|更新)」「令和N年M月[D日](時点|版|現在|更新)」
  を拾い、いちばん新しい日付が今日から STALE_DAYS（180 日＝半年）以上前なら「古い」。
  「公表」「改定」「締切」は外部文書や予定の日付なので時点と見なさない（第1回の約定結果が 2024 年公表でも本文は最新でありうる）。
  時点表現が 1 つも無いページは判定しない（分からないものは出さない）。
  対象はリポジトリ直下の JA の HTML（zh-*.html・en/・404・thanks は除く）。並びは 28 日クリック → 経過日。

    python3 scripts/seo/stale_pages.py            # 表（28 日クリックは GSC の台帳があれば付く）
    python3 scripts/seo/stale_pages.py --json
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REPO, file_to_url, path_of  # noqa: E402

STALE_DAYS = 180
ASOF_SUFFIX = r"(?:時点|版|現在|更新)"
_Z2H = str.maketrans("０１２３４５６７８９", "0123456789")
RE_WESTERN = re.compile(r"(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?" + ASOF_SUFFIX)
RE_REIWA = re.compile(r"令和(\d{1,2})年(\d{1,2})月(?:(\d{1,2})日)?" + ASOF_SUFFIX)
_STRIP = [re.compile(r"<script\b.*?</script>", re.S | re.I), re.compile(r"<style\b.*?</style>", re.S | re.I),
          re.compile(r"<!--.*?-->", re.S), re.compile(r"<[^>]+>")]
SKIP_FILES = {"404.html", "thanks.html"}


def visible_text(html: str) -> str:
    body = html.split("<body", 1)[1] if "<body" in html else html
    for rx in _STRIP:
        body = rx.sub(" ", body)
    return body.translate(_Z2H)


def asof_dates(text: str):
    """(日付, 表現) の列。読めない日付（13月・32日）は捨てる。"""
    out = []
    for rx, base in ((RE_WESTERN, 0), (RE_REIWA, 2018)):
        for m in rx.finditer(text):
            y = int(m.group(1)) + base
            try:
                out.append((datetime.date(y, int(m.group(2)), int(m.group(3) or 1)), m.group(0)))
            except ValueError:
                continue
    return out


def ja_files(repo: pathlib.Path):
    for p in sorted(repo.glob("*.html")):
        if p.name.startswith("zh-") or p.name in SKIP_FILES:
            continue
        yield p


def scan(repo: pathlib.Path = REPO, today: datetime.date | None = None, clicks: dict | None = None,
         stale_days: int = STALE_DAYS) -> list:
    """古いページの行: {page, file, asof, expr, age_days, clicks28, n_marks}。並びは 28 日クリック → 経過日。"""
    today = today or datetime.date.today()
    clicks = clicks or {}
    rows = []
    for p in ja_files(pathlib.Path(repo)):
        try:
            marks = asof_dates(visible_text(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
        if not marks:
            continue
        newest, expr = max(marks, key=lambda t: t[0])
        age = (today - newest).days
        if age < stale_days:
            continue
        url = file_to_url(p.name)
        page = path_of(url) if url else "/" + p.name[:-5]
        rows.append({"page": page, "file": p.name, "asof": str(newest), "expr": expr,
                     "age_days": age, "clicks28": int(clicks.get(page, 0)), "n_marks": len(marks)})
    rows.sort(key=lambda r: (-r["clicks28"], -r["age_days"]))
    return rows


def render(L: list, rows: list, limit: int = 30) -> None:
    """ブリーフ 11 節。週次の Claude が読む（直すためではなく、日付を触らないため）。"""
    L.append(f"## 11. 本文の時点が古いページ（本文が名乗る「◯年◯月時点／版／現在／更新」が {STALE_DAYS} 日以上前）\n")
    L.append("週次では日付・件数・数字を直さない（一次資料に出られないので取り違える）。"
             "更新は CC の作業セッションで中島さんの指示で行う。日曜朝の Telegram に先頭の 1 本と本数を出す。\n")
    if not rows:
        L.append("なし\n")
        return
    L.append("| ページ | 本文の時点 | 経過日 | 28日クリック | 時点表現の数 |\n|---|---|---|---|---|")
    for r in rows[:limit]:
        L.append(f"| {r['page']} | {r['expr']}（{r['asof']}） | {r['age_days']} | {r['clicks28']} | {r['n_marks']} |")
    if len(rows) > limit:
        L.append(f"\n…ほか {len(rows) - limit} 本")
    L.append("")


def tg_line(rows: list) -> str:
    """日曜朝の Telegram の 1 行（先頭 1 本＋本数）。0 本なら空。"""
    if not rows:
        return ""
    r = rows[0]
    more = f" ほか{len(rows) - 1}本" if len(rows) > 1 else ""
    return (f"🕰 本文の時点が古い: {r['page']}（{r['expr']}・{r['age_days']}日前・28日{r['clicks28']}クリック）{more}"
            " → CC の作業セッションで一次資料を当てて更新（週次は触らない）")


def main() -> int:
    clicks = {}
    try:
        import build_brief as bb
        gd = bb.gsc_days()
        if gd:
            latest = bb.d(gd[-1])
            _, pages, _, _ = bb.agg_gsc(bb.load_range("gsc", latest - datetime.timedelta(days=27), latest))
            clicks = {p: v.get("clicks", 0) for p, v in pages.items()}
    except Exception:  # noqa: BLE001 — 台帳が無くても表は出す
        pass
    rows = scan(clicks=clicks)
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    L = []
    render(L, rows, limit=200)
    print("\n".join(L))
    print(tg_line(rows) or "（Telegram の 1 行: なし）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
