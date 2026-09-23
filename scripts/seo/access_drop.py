#!/usr/bin/env python3
"""アクセスが減ったページを機械で見つけ、原因の型と「本文の時点」を添える（LLM 不使用・読むだけ）。

なぜ（2026-09-22 中島決定）:
  トリガーは**アクセス減**（「古い」ではない）。/column-jcstar は 28 日クリック 152→92 で見つかり、診断の結果が
  「順位落ち＋本文が 6 月時点のまま」だった。週次の Claude（weekly_run.sh）は Read・Edit・Grep しか持たず外部サイトに
  出られないので、一次資料が要る本文の時点更新は自動でやらない。代わりに週次ジョブが、減ったページと原因の型・本文の時点を
  ブリーフ 11 節と日曜朝の Telegram の 1 行に出し、時点更新は CC の作業セッションで中島さんの指示で行う（PR #95 が型）。

判定（決定論。ブリーフ 4 節の「クリックが3割以上落ちたページ」と同じ基準）:
  直近 28 日のクリックが前 28 日の 7 割未満、かつ前 28 日が 20 クリック以上のページ。
  原因の型: 検索語ごとに失ったクリックを 順位落ち（1.0 以上悪化）／着地移動（表示が半分未満で、同じ語が別ページに表示）／
    表示減（表示が半分未満）／CTR落ち（表示は保ったまま CTR が下がった）に帰属し、いちばん大きい型を採る（内訳の % を添える）。
    語の内訳が無ければページ合計で判定。
  本文の時点: 本文（<body> の見える文字。script・style・コメント・タグを除く）の
    「YYYY年M月[D日](時点|版|現在|更新)」「令和N年…」のいちばん新しい日付（無ければ「時点表現なし」）。
    「公表」「改定」「締切」は外部文書・予定の日付なので見ない。
  次の手: 時点が 90 日以上前 → 本文の時点更新（CC）／CTR落ちだけ → title・description（週次の 3 の仕事）／それ以外 → 本文の受け皿を見直す（CC 判断）。
  並びは失ったクリック数。

    python3 scripts/seo/access_drop.py            # 表（GSC の台帳から直近 28 日と前 28 日）
    python3 scripts/seo/access_drop.py --json
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REPO  # noqa: E402

MIN_PREV_CLICKS = 20     # 4 節と同じ
DROP_RATIO = 0.7         # 4 節と同じ（3 割減）
POS_WORSE = 1.0          # 順位落ちと見なす悪化幅
ASOF_OLD_DAYS = 90       # これ以上前の時点なら「本文の時点更新（CC）」
ASOF_SUFFIX = r"(?:時点|版|現在|更新)"
_Z2H = str.maketrans("０１２３４５６７８９", "0123456789")
RE_WESTERN = re.compile(r"(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?" + ASOF_SUFFIX)
RE_REIWA = re.compile(r"令和(\d{1,2})年(\d{1,2})月(?:(\d{1,2})日)?" + ASOF_SUFFIX)
_STRIP = [re.compile(r"<script\b.*?</script>", re.S | re.I), re.compile(r"<style\b.*?</style>", re.S | re.I),
          re.compile(r"<!--.*?-->", re.S), re.compile(r"<[^>]+>")]


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


def page_file(page: str) -> str:
    """/column-x → column-x.html、/ → index.html、/en/column-x → en/column-x.html（このサイトの置き方）。"""
    rel = page.split("?")[0].split("#")[0].lstrip("/")
    if not rel or rel.endswith("/"):
        rel += "index"
    return rel + ".html"


def asof_of(page: str, repo: pathlib.Path = REPO):
    """ページ（/column-x）の本文が名乗るいちばん新しい時点 → (日付, 表現)。無ければ None。"""
    p = pathlib.Path(repo) / page_file(page)
    if not p.exists():
        return None
    try:
        marks = asof_dates(visible_text(p.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return None
    return max(marks, key=lambda t: t[0]) if marks else None


def judge_by_queries(page: str, qp: dict, pqp: dict):
    """検索語ごとに失ったクリックを 順位落ち／着地移動／表示減／CTR落ち に帰属し、最大の型を返す（無ければ None）。
    ページ合計の順位は表示加重の平均なので、蓄電池事業者の語が 4 位→7 位に落ちても 5.9→6.2 にしか映らない
    （2026-09-22 /column-jcstar の実測）。語ごとに見ないと原因を取り違える。
    順番: 順位が 1.0 以上悪化していれば表示が減っていても「順位落ち」（下がったから表示が減る）。順位が保たれて表示が半分未満なら、
    同じ語が別ページで表示されていれば「着地移動」、そうでなければ「表示減」。表示が保たれて CTR が下がれば「CTR落ち」。"""
    lost = {"順位落ち": 0, "着地移動": 0, "表示減": 0, "CTR落ち": 0}
    for (query, pg), b in pqp.items():
        if pg != page:
            continue
        a = qp.get((query, pg)) or {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": None}
        d = b["clicks"] - a["clicks"]
        if d <= 0:
            continue
        pos_worse = a["position"] is not None and b.get("position") is not None and a["position"] - b["position"] >= POS_WORSE
        imp_half = a["impressions"] < b["impressions"] * 0.5
        if pos_worse:
            lost["順位落ち"] += d
        elif imp_half:
            elsewhere = any(q2 == query and pg2 != page and v.get("impressions", 0) >= b["impressions"] * 0.5
                            for (q2, pg2), v in qp.items())
            lost["着地移動" if elsewhere else "表示減"] += d
        elif a["ctr"] < b["ctr"]:
            lost["CTR落ち"] += d
    total = sum(lost.values())
    if not total:
        return None
    order = sorted(lost.items(), key=lambda kv: -kv[1])
    main = order[0][0]
    parts = "・".join(f"{k} {v * 100 // total}%" for k, v in order if v)
    return main, parts


def judge(a: dict, b: dict) -> str:
    """原因の型（ページ合計。検索語の内訳が無いときの予備）。a=直近 28 日・b=前 28 日。複数なら「・」でつなぐ。"""
    j = []
    if a.get("position") is not None and b.get("position") is not None and a["position"] - b["position"] >= POS_WORSE:
        j.append("順位落ち")
    imp_down = a.get("impressions", 0) < b.get("impressions", 0) * DROP_RATIO
    if imp_down:
        j.append("表示減")
    if not imp_down and a.get("ctr", 0) < b.get("ctr", 0) * DROP_RATIO:
        j.append("CTR落ち")
    return "・".join(j) or "微減"


def next_step(judgement: str, age_days) -> str:
    if age_days is not None and age_days >= ASOF_OLD_DAYS:
        return "本文の時点更新（CC）"
    if "CTR落ち" in judgement and "順位落ち" not in judgement:
        return "title・description（週次）"
    return "本文の受け皿を見直す（CC 判断）"


def drops(pages: dict, ppages: dict, qp: dict | None = None, pqp: dict | None = None,
          repo: pathlib.Path = REPO, today: datetime.date | None = None) -> list:
    """減ったページの行。並びは失ったクリック数（多い順）。qp/pqp（(検索語, ページ) → 集計）があれば原因は語ごとに帰属する。"""
    today = today or datetime.date.today()
    rows = []
    for page, a in pages.items():
        b = ppages.get(page)
        if not b or b["clicks"] < MIN_PREV_CLICKS or a["clicks"] >= b["clicks"] * DROP_RATIO:
            continue
        asof = asof_of(page, repo)
        age = (today - asof[0]).days if asof else None
        jq = judge_by_queries(page, qp, pqp) if (qp and pqp) else None
        jd, detail = (jq[0], jq[1]) if jq else (judge(a, b), "")
        rows.append({"page": page, "clicks_prev": b["clicks"], "clicks_cur": a["clicks"], "judge_detail": detail,
                     "pct": round((a["clicks"] - b["clicks"]) / b["clicks"] * 100),
                     "imp_prev": b.get("impressions", 0), "imp_cur": a.get("impressions", 0),
                     "ctr_prev": b.get("ctr", 0.0), "ctr_cur": a.get("ctr", 0.0),
                     "pos_prev": b.get("position"), "pos_cur": a.get("position"),
                     "judge": jd, "asof": str(asof[0]) if asof else None, "expr": asof[1] if asof else None,
                     "age_days": age, "next": next_step(jd, age)})
    rows.sort(key=lambda r: r["clicks_cur"] - r["clicks_prev"])
    return rows


def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def _asof_txt(r: dict) -> str:
    return f"{r['expr']}＝{r['age_days']}日前" if r.get("expr") else "時点表現なし"


def render(L: list, rows: list, limit: int = 30) -> None:
    """ブリーフ 11 節。週次の Claude が読む（CTR落ちだけなら title・description で受け、時点更新はしない）。"""
    L.append(f"## 11. アクセスが減ったページ（28日クリックが前28日の{int(DROP_RATIO * 100)}%未満・前28日{MIN_PREV_CLICKS}クリック以上）\n")
    L.append("原因の型と本文の時点を添える。**「本文の時点更新（CC）」の行は週次では日付・件数・数字を直さない**"
             "（一次資料に出られないので取り違える）＝CC の作業セッションで中島さんの指示で更新する。"
             "「title・description（週次）」の行は 3 の仕事として受けてよい。日曜朝の Telegram に先頭の 1 本と本数を出す。\n")
    if not rows:
        L.append("なし\n")
        return
    L.append("| ページ | クリック 前→今 | 順位 前→今 | CTR 前→今 | 表示 前→今 | 原因の型 | 本文の時点 | 次の手 |\n|---|---|---|---|---|---|---|---|")
    for r in rows[:limit]:
        L.append(f"| {r['page']} | {r['clicks_prev']}→{r['clicks_cur']}（{r['pct']:+d}%） | {_f(r['pos_prev'])}→{_f(r['pos_cur'])} "
                 f"| {r['ctr_prev'] * 100:.1f}%→{r['ctr_cur'] * 100:.1f}% | {r['imp_prev']}→{r['imp_cur']} | {r['judge']}{('（' + r['judge_detail'] + '）') if r.get('judge_detail') else ''} | {_asof_txt(r)} | {r['next']} |")
    if len(rows) > limit:
        L.append(f"\n…ほか {len(rows) - limit} 本")
    L.append("")


def tg_line(rows: list) -> str:
    """日曜朝の Telegram の 1 行（先頭 1 本＋本数）。0 本なら空。"""
    if not rows:
        return ""
    r = rows[0]
    more = f" ほか{len(rows) - 1}本" if len(rows) > 1 else ""
    return (f"📉 アクセスが減った: {r['page']}（28日 {r['clicks_prev']}→{r['clicks_cur']}・{r['pct']:+d}%・{r['judge']} "
            f"{_f(r['pos_prev'])}→{_f(r['pos_cur'])}位・{_asof_txt(r)}）{more} → {r['next']}。時点更新は CC の作業セッションで（週次は title・description まで）")


def main() -> int:
    import build_brief as bb
    gd = bb.gsc_days()
    if not gd:
        print("GSC の台帳が空"); return 1
    latest = bb.d(gd[-1]); days = 28
    cur_s = latest - datetime.timedelta(days=days - 1)
    _, pages, qp, _ = bb.agg_gsc(bb.load_range("gsc", cur_s, latest))
    _, ppages, pqp, _ = bb.agg_gsc(bb.load_range("gsc", cur_s - datetime.timedelta(days=days), cur_s - datetime.timedelta(days=1)))
    rows = drops(pages, ppages, qp, pqp)
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1)); return 0
    L = []; render(L, rows, limit=200); print("\n".join(L))
    print(tg_line(rows) or "（Telegram の 1 行: なし）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
