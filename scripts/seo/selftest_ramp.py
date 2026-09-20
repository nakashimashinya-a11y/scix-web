#!/usr/bin/env python3
"""新規ページの立ち上がり判定（measure_changes.py の mode=ramp）を合成データで確かめる。
月1回の構成レビューが自動で公開した変更（変更台帳の source=structure）が、週次の変更と同じ流れに乗ることもここで確かめる:
14 日後・28 日後の前後比較 → worse ならブリーフ 8 節に出る（差し戻し候補）→ 8 節の「構成の変更」の表に着地リードの前後。

    python3 scripts/seo/selftest_ramp.py        # 0=全部通った（--keep で合成台帳を残す）

一時ディレクトリに台帳を作り、SCIX_WEB_LEDGER をそこへ向けてから読み込む＝本物の台帳には触らない。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TMP = common = mc = build_brief = None  # main() が一時ディレクトリを作ってから読み込む（import しただけでは何も作らない）
D = datetime.date.fromisoformat
# 日付は今日から相対で作る（ブリーフは「60日以内」「直近28日」を今日から数える＝固定日付だと後日こける）
LATEST = datetime.date.today() - datetime.timedelta(days=3)   # GSC の最新日
START = LATEST - datetime.timedelta(days=80)


def ago(n: int) -> str:
    return str(LATEST - datetime.timedelta(days=n))


# 既存コラム（言語ごとに5本）。1日あたりの表示 → 28日の中央値は JA 280・EN 28・ZH 0
PEERS = {"/column-old-1": 2, "/column-old-2": 5, "/column-old-3": 10, "/column-old-4": 20, "/column-old-5": 40,
         "/en/column-old-1": 0, "/en/column-old-2": 0, "/en/column-old-3": 1, "/en/column-old-4": 2, "/en/column-old-5": 3,
         "/zh-column-old-1": 0, "/zh-column-old-2": 0, "/zh-column-old-3": 0, "/zh-column-old-4": 1, "/zh-column-old-5": 1}
# 新規ページ: (公開日, 公開後の1日あたり表示)
NEW = {"/column-new-a": (ago(38), 15), "/en/column-new-a": (ago(38), 0), "/zh-column-new-a": (ago(38), 1),
       "/column-new-b": (ago(33), 0),
       "/partners-x": (ago(16), 1),
       "/column-new-d": (ago(7), 3),
       "/column-new-f": (ago(36), 2)}
# 公開から20日目に初めて表示が出るページ（14日時点 not-shown → 28日時点は中央値未満）
LATE = {"/column-new-g": (ago(43), 20, 1)}
TITLE_DAY = ago(47)   # 旧方式（前後比較）の対象の変更日
# 構成の変更（source=structure）: STRUCT_DAY にハブの並びを変えたら、クリックも CTR も着地リードも落ちた（＝worse）
STRUCT_DAY = ago(47)
STRUCT_COMMIT = "abcdef1234567890abcdef1234567890abcdef12"


def build() -> None:
    for day in common.daterange(START, LATEST):
        pages = [{"page": p, "clicks": 0, "impressions": n, "ctr": 0.0, "position": 12.0} for p, n in PEERS.items() if n]
        for p, (pub, n) in NEW.items():
            if n and day > D(pub):
                pages.append({"page": p, "clicks": 1 if p == "/column-new-a" else 0, "impressions": n, "ctr": 0.0, "position": 20.0})
        for p, (pub, after, n) in LATE.items():
            if day >= D(pub) + datetime.timedelta(days=after):
                pages.append({"page": p, "clicks": 0, "impressions": n, "ctr": 0.0, "position": 30.0})
        # 旧方式（前後比較）の対象: title を変えて、クリックが倍になった
        pages.append({"page": "/old-title", "clicks": 4 if day > D(TITLE_DAY) else 2, "impressions": 100,
                      "ctr": 0.04 if day > D(TITLE_DAY) else 0.02, "position": 8.0})
        after = day > D(STRUCT_DAY)
        pages.append({"page": "/hub-x", "clicks": 3 if after else 10, "impressions": 100, "ctr": 0.03 if after else 0.10, "position": 6.0})
        common.jdump(TMP / "gsc" / f"{day}.json", {"date": str(day), "totals": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0},
                                                   "pages": pages, "query_page": []})
        # GA4: /hub-x に着地したセッションと問い合わせ。変更前は 2 日に 1 件、変更後は 0 件（合成の数字）
        lead = 0 if after else (day.toordinal() % 2)
        common.jdump(TMP / "ga4" / f"{day}.json", {"date": str(day), "totals": {"sessions": 20, "keyEvents:generate_lead": lead, "engagedSessions": 10},
                                                   "landing": [{"landingPage": "/hub-x", "sessions": 4 if after else 8,
                                                                "keyEvents:generate_lead": lead, "engagedSessions": 3},
                                                               {"landingPage": "/hub-y", "sessions": 5, "keyEvents:generate_lead": 0, "engagedSessions": 2}]})
    urls = list(PEERS) + list(NEW) + list(LATE) + ["/old-title", "/knowledge"]
    common.jdump(TMP / "health" / f"{datetime.date.today()}.json", {
        "date": str(datetime.date.today()), "n": len(urls), "issues": [], "inbound": {},
        "pages": [{"url": u, "status": 200, "internal_links": (list(PEERS) + ["/column-new-a"]) if u == "/knowledge" else []} for u in urls]})

    def entry(eid, date, cls, pages, measured=None, source="manual-auto"):
        return {"id": eid, "date": date, "source": source, "class": cls, "pages": pages,
                "summary": eid, "check_days": [14, 28], "measured": measured or {}}
    old_style = {"verdict": "better", "pre": dict(mc.ZERO), "post": dict(mc.ZERO), "on": ago(20)}
    common.write_jsonl(TMP / "ledger" / "changes.jsonl", [
        entry("new-column-new-a", ago(38), "new-column", ["/column-new-a", "/en/column-new-a", "/zh-column-new-a"]),
        # pages を書き落とした new-column（週次のマニフェストの書き落とし）と、日付が壊れたエントリ。どちらも台帳の途中に置く
        # ＝ここで落ちると後ろのエントリが測られず、前のエントリが measurements.jsonl に毎朝重複する（2026-09-20 の欠陥）
        entry("auto-empty-pages", ago(20), "new-column", [], source="auto"),
        entry("auto-bad-date", "2026-02-30", "new-column", ["/column-new-b"], source="auto"),
        entry("new-column-new-b", ago(33), "new-column", ["/column-new-b"], source="manual"),  # 手で記帳した新設（pr78 と同じ形）
        entry("new-partners-x", ago(16), "new-page", ["/partners-x"]),
        entry("new-column-new-d", ago(7), "new-column", ["/column-new-d"]),
        entry("new-column-new-f", ago(36), "new-column", ["/column-new-f"], {"14": old_style}),
        entry("new-column-new-g", ago(43), "new-column", ["/column-new-g"]),
        {"id": "pr-old-title", "date": TITLE_DAY, "source": "manual", "class": "title", "pages": ["/old-title"],
         "summary": "title", "check_days": [14, 28], "measured": {}},
        # 構成レビューが自動で公開した変更（record_changes.py --source structure と同じ形）。判定済みになる／途中経過／公開直後
        {"id": "structure-test-1", "date": STRUCT_DAY, "source": "structure", "commit": STRUCT_COMMIT, "class": "hub-order",
         "pages": ["/hub-x"], "files": ["knowledge.html"], "summary": "ハブの並び", "measure": "14日後・28日後", "check_days": [14, 28], "measured": {}},
        {"id": "structure-test-2", "date": ago(8), "source": "structure", "commit": STRUCT_COMMIT, "class": "cta-route",
         "pages": ["/hub-y"], "files": ["column-x.html"], "summary": "CTA の行き先", "check_days": [14, 28], "measured": {}},
        {"id": "structure-test-3", "date": ago(-2), "source": "structure", "commit": STRUCT_COMMIT, "class": "funnel-block",
         "pages": ["/hub-y"], "files": ["column-y.html"], "summary": "導線ブロック", "check_days": [14, 28], "measured": {}},
    ])


def main() -> int:
    global TMP, common, mc, build_brief
    TMP = pathlib.Path(tempfile.mkdtemp(prefix="scix-seo-selftest-"))
    os.environ["SCIX_WEB_LEDGER"] = str(TMP)  # common を読み込む前に向き先を変える
    import common, measure_changes as mc, build_brief  # noqa: E401,E402
    import newpages as npg  # noqa: E402
    assert common.LEDGER == TMP and mc.CHANGES.parent.parent == TMP, "台帳の向き先が一時ディレクトリになっていない"
    build()
    new = mc.run()
    got = {(r["id"], r["check"]): r for r in new}
    led = {e["id"]: e for e in common.read_jsonl(TMP / "ledger" / "changes.jsonl")}
    ok = True

    def check(label, actual, expected):
        nonlocal ok
        good = actual == expected
        ok = ok and good
        print(("OK " if good else "NG ") + f"{label}: {actual!r}" + ("" if good else f"（期待 {expected!r}）"))

    a14, a28 = got[("new-column-new-a", 14)], got[("new-column-new-a", 28)]
    check("A 14日 エントリ（JA が主）", a14["verdict"], "shown")
    check("A 14日 EN は表示ゼロ", a14["by_page"]["/en/column-new-a"]["verdict"], "not-shown")
    check("A 28日 JA 420 対 中央値 280", (a28["by_page"]["/column-new-a"]["impressions"], a28["by_page"]["/column-new-a"]["median"],
                                      a28["verdict"]), (420, 280, "above-median"))
    check("A 28日 EN", a28["by_page"]["/en/column-new-a"]["verdict"], "not-shown")
    check("A 28日 ZH 28 対 中央値 0", (a28["by_page"]["/zh-column-new-a"]["median"], a28["by_page"]["/zh-column-new-a"]["verdict"]), (0, "above-median"))
    check("A 初表示日＝公開の翌日", a28["by_page"]["/column-new-a"]["first_shown"], ago(37))
    check("A mode と pre（互換のゼロ）", (a28["mode"], a28["pre"]["clicks"], a28["post"]["clicks"]), ("ramp", 0, 28))
    check("B 14日・28日（表示ゼロ）", (got[("new-column-new-b", 14)]["verdict"], got[("new-column-new-b", 28)]["verdict"]), ("not-shown", "not-shown"))
    check("C new-page 14日", got[("new-partners-x", 14)]["verdict"], "shown")
    check("C 28日はまだ期限前", ("new-partners-x", 28) in got, False)
    check("D 公開7日＝どちらも期限前", [k for k in got if k[0] == "new-column-new-d"], [])
    check("F 判定済みの 14 は触らない", led["new-column-new-f"]["measured"]["14"], {"verdict": "better", "pre": dict(mc.ZERO), "post": dict(mc.ZERO), "on": ago(20)})
    check("F 未判定の 28 は立ち上がりで（56 対 280）", got[("new-column-new-f", 28)]["verdict"], "below-median")
    check("G 14日 not-shown → 28日 below-median", (got[("new-column-new-g", 14)]["verdict"], got[("new-column-new-g", 28)]["verdict"]), ("not-shown", "below-median"))
    check("既存の前後比較はそのまま（title・クリック倍）", (got[("pr-old-title", 14)]["verdict"], "mode" in got[("pr-old-title", 14)]), ("better", False))
    # 構成の変更（source=structure）は週次の変更と同じ前後比較に乗る。クリック 0.3 倍・CTR 0.3 倍 → worse。リードも台帳に残る
    s14, s28 = got.get(("structure-test-1", 14)) or {}, got.get(("structure-test-1", 28)) or {}
    check("構成の変更: 14日後・28日後に前後比較され worse（mode=ramp ではない）",
          (s14.get("verdict"), s28.get("verdict"), "mode" in s14), ("worse", "worse", False))
    check("構成の変更: 着地リードの前後が判定に残る（前 14 日で 7 件 → 後 0 件）",
          ((s14.get("pre") or {}).get("leads"), (s14.get("post") or {}).get("leads"), (s14.get("pre") or {}).get("sessions"), (s14.get("post") or {}).get("sessions")),
          (7, 0, 112, 56))
    check("構成の変更: 期限前のものはまだ測らない", [k for k in got if k[0] in ("structure-test-2", "structure-test-3")], [])
    check("新規は既存コラムの母集団に入らない（JA 5本）", a28["by_page"]["/column-new-a"]["peers"], 5)
    check("2回目は何も足さない", mc.run(), [])
    # 1 件の不正で全体を止めない
    e14 = got.get(("auto-empty-pages", 14)) or {}
    check("pages が空の new-column は落ちずに insufficient で閉じる", (e14.get("verdict"), e14.get("mode"), e14.get("by_page")), ("insufficient", "ramp", {}))
    check("日付が壊れたエントリは飛ばす（後ろのエントリは測られている）", ([k for k in got if k[0] == "auto-bad-date"], ("new-column-new-g", 28) in got), ([], True))
    rows = common.read_jsonl(TMP / "ledger" / "measurements.jsonl")
    keys = [(r["id"], r["check"]) for r in rows]
    check("measurements.jsonl に同じ (id, check) が重複しない（2回走らせたあと）", (len(keys), len(keys) == len(set(keys))), (len(new), True))
    check("変更台帳に判定が残っている（measurements と同じ件数）", sum(len(e.get("measured") or {}) for e in led.values()) - 1, len(new))  # -1＝F の判定済み 14
    check("暦に無い日付は None（days_since・safe_d）", (npg.days_since("2026-09-31", datetime.date.today()), common.safe_d("2026-02-30"), common.safe_d(None)), (None, None, None))

    # ブリーフ 8 節: not-shown で今も表示ゼロ → 要手当て。G は判定後に表示が出た → 外れる。中央値未満は別行
    pages28 = build_brief.agg_gsc(build_brief.load_range("gsc", LATEST - datetime.timedelta(days=27), LATEST))[1]
    ns, below = build_brief.ramp_needs_care(list(led.values()), pages28)
    check("要手当て", sorted(p for p, *_ in ns), ["/column-new-b", "/en/column-new-a"])
    check("中央値未満", sorted(p for p, *_ in below), ["/column-new-f", "/column-new-g"])
    text = build_brief.render()
    check("ブリーフに 8 節の要手当てと 10 節", ("**要手当て" in text, "## 10. 新規ページ" in text, "### 10b." in text), (True, True, True))
    check("8 節: worse の構成の変更が表に出る（＝翌週の週次で差し戻し候補）",
          "| structure-test-1 | hub-order | /hub-x | ハブの並び | worse（140→42, CTR 10.0%→3.0%, lead 7→0） | worse（140→42, CTR 10.0%→3.0%, lead 7→0） |" in text, True)
    check("8 節の「構成の変更」の表: commit・着地セッション・着地リードの前後・判定",
          ("### 構成の変更（月1回の構成レビューが公開したもの" in text,
           f"| structure-test-1 | hub-order | /hub-x | {STRUCT_COMMIT[:10]} | 112→56 | 7→0 | 28日後の判定の窓 | worse／worse |" in text,
           f"| structure-test-2 | cta-route | /hub-y | {STRUCT_COMMIT[:10]} | 70→30 | 0→0 | 途中（GA4 6日ぶん） | 未／未 |" in text,
           "| 0→- | まだ（公開から3日未満） | 未／未 |" in text), (True, True, True, True))
    latest_md = build_brief.render(for_latest=True)
    check("最新.md（毎朝の写し）には構成の変更の表もリードの前後も出さない", "### 構成の変更" in latest_md, False)
    bj = build_brief.brief_json()
    check("brief.json の structure_changes（Drive にだけ置く）", [(r["id"], r["leads"]) for r in bj.get("structure_changes", [])][-1], ("structure-test-1", [7, 0]))
    check("8 節の表: 手で記帳した新設は立ち上がりの書式・自動記帳は件数だけ",
          ("| new-column-new-b | new-column | /column-new-b | new-column-new-b | not-shown（表示 0・クリック 0） | not-shown（表示 0・クリック 0） |" in text,
           "| new-column-new-a |" in text, "新規ページの自動記帳" in text), (True, False, True))
    keep = "--keep" in sys.argv or not ok
    print(("全部通った" if ok else "失敗あり") + (f"（合成台帳を残した: {TMP}）" if keep else ""))
    if not keep:
        shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
