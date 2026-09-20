#!/usr/bin/env python3
"""変更の効果測定。ledger/changes.jsonl の各変更について、2週後と4週後に GSC/GA4 の前後比較を書く。

窓の取り方（変更日を d とする）:
  前:   d-15 〜 d-2 の14日
  2週後: d+3 〜 d+16 の14日（反映までの2日を飛ばす）
  4週後: d+17 〜 d+30 の14日
判定は CTR とクリックの比。順位は日次でぶれるので主役にしない（台帳の方針どおり）。
  worse  = クリック 0.8倍未満 かつ CTR 0.85倍未満
  better = クリック 1.2倍以上 または リードが増えた
  flat   = それ以外
  insufficient = 表示が前後合計60未満、または前の窓のデータ日数が10日未満
月1回の構成レビューが公開した変更（source=structure）も同じ判定式。**問い合わせ・送客が減っても worse にはならない**
（リードは better の側にしか使わない。件数が少なく、機械の判定に入れると誤って戻す回数が増える）。その分は週次のブリーフ 8 節の
「構成の変更」の表が「注意」（リード減・送客減）として出し、週次の Claude が差し戻すかを決める（build_brief.structure_change_rows）。
測るのは pages（＝編集したページ）だけ: GA4 のリードは着地ページに付くので、送客先の収益ページ（kpi_pages）は前後比較に入れない。

新規ページ（class が new-column / new-page）は前の窓が無い＝前後比較だと 1 クリックで必ず better になる。
だから **立ち上がり** で判定する（mode="ramp"。変更日＝公開日を d とする）:
  14日時点（GSC が d+14 まで届いたら）: d〜d+14 に表示が 1 以上あれば shown、無ければ not-shown
  28日時点（GSC が d+28 まで届いたら）: d+1〜d+28 の表示を、同じ言語の既存コラム（公開60日以内の新規は除く）の
      同じ 28 日の表示の中央値と比べて above-median / below-median。表示ゼロは not-shown
  3言語のエントリはページごとに判定を持ち（by_page）、エントリの判定は主たるページ（JA→EN→ZH の順で最初）のもの。
  not-shown は worse と同じ扱い＝翌週のブリーフ 8 節に「要手当て」として出る（差し戻しではなく内部リンクで育てる）。
  既に判定済みのレコードは触らない。

1 件の不正で全体を止めない: エントリごとに例外を受け、そのエントリだけ飛ばして次へ進む（ログに id を出す）。
pages が空の新規ページ（マニフェストの書き落とし）は insufficient で閉じる。measurements.jsonl への追記は
changes.jsonl を書き戻したあと＝途中で落ちても同じ行が毎朝増えない（(id, check) が既にある行も足さない）。

    python3 scripts/seo/measure_changes.py          # 期限が来たものを計測して台帳に書く
    python3 scripts/seo/measure_changes.py --list   # 台帳を表示
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, d, daterange, jload, log, read_jsonl, safe_d, today, write_jsonl, append_jsonl  # noqa: E402
import newpages as npg  # noqa: E402

CHANGES = LEDGER / "ledger" / "changes.jsonl"
MEASURES = LEDGER / "ledger" / "measurements.jsonl"
WINDOWS = {14: (3, 16), 28: (17, 30)}
PRE = (-15, -2)
LEAD = "keyEvents:generate_lead"


def latest_gsc_date():
    days = sorted(p.stem for p in (LEDGER / "gsc").glob("????-??-??.json"))
    return d(days[-1]) if days else None


def window_metrics(pages, start, end):
    pages = set(pages)
    m = {"days": 0, "clicks": 0, "impressions": 0, "pos_w": 0.0, "sessions": 0, "leads": 0, "ga4_days": 0}
    for day in daterange(start, end):
        g = jload(LEDGER / "gsc" / f"{day}.json")
        if g:
            m["days"] += 1
            for p in g["pages"]:
                if p["page"] in pages:
                    m["clicks"] += p["clicks"]; m["impressions"] += p["impressions"]
                    m["pos_w"] += p["position"] * p["impressions"]
        a = jload(LEDGER / "ga4" / f"{day}.json")
        if a:
            m["ga4_days"] += 1
            for r in a.get("landing", []):
                if r.get("landingPage") in pages:
                    m["sessions"] += int(r.get("sessions") or 0)
                    m["leads"] += int(r.get(LEAD) or 0)
    m["ctr"] = m["clicks"] / m["impressions"] if m["impressions"] else 0.0
    m["position"] = m["pos_w"] / m["impressions"] if m["impressions"] else None
    del m["pos_w"]
    return m


def verdict(pre, post):
    if pre["days"] < 10 or (pre["impressions"] + post["impressions"]) < 60:
        return "insufficient"
    c_ratio = post["clicks"] / pre["clicks"] if pre["clicks"] else (2.0 if post["clicks"] else 1.0)
    ctr_ratio = post["ctr"] / pre["ctr"] if pre["ctr"] else (2.0 if post["ctr"] else 1.0)
    if c_ratio < 0.8 and ctr_ratio < 0.85:
        return "worse"
    if c_ratio >= 1.2 or post["leads"] > pre["leads"]:
        return "better"
    return "flat"


NEW_EXCLUDE_DAYS = 60   # 公開からこの日数以内のページは「既存コラム」の母集団に入れない
MIN_PEERS = 5           # 母集団がこれ未満なら中央値と比べない（shown / not-shown だけ返す）
ZERO = {"days": 0, "clicks": 0, "impressions": 0, "sessions": 0, "leads": 0, "ga4_days": 0, "ctr": 0.0, "position": None}


def ramp_verdict(impressions, median):
    if not impressions:
        return "not-shown"
    if median is None:
        return "shown"
    return "above-median" if impressions >= median else "below-median"


def measure_ramp(e, check, entries, health):
    """新規ページの立ち上がり。返り値は measured[<check>] に入れる dict（pre は互換のためのゼロ）。"""
    day = d(e["date"])
    end = day + datetime.timedelta(days=check)
    start = day if check == 14 else day + datetime.timedelta(days=1)
    pages = [p for p in (e.get("pages") or []) if isinstance(p, str) and p]
    if not pages:
        # 測る対象が無い（マニフェストで pages を書き落とした new-column など）。落とさずに insufficient で閉じる
        # ＝翌朝また同じところで止まらない。旧方式（前後比較）でも pages が空なら insufficient だった
        return {"verdict": "insufficient", "mode": "ramp", "window": [str(start), str(end)], "note": "pages が空",
                "pre": dict(ZERO), "post": dict(ZERO), "by_page": {}, "on": str(today())}
    sums, first, days = npg.gsc_page_sums(start, end)
    if days < (end - start).days // 2:
        verdicts = {p: "insufficient" for p in pages}
    else:
        verdicts = {}
    # 既存コラムの母集団から外す「新規」: 窓の終わりの60日前より後に公開されたページ（台帳＋git の公開日。
    # 窓より後に出たページも外す＝その窓では表示ゼロで当たり前なので、中央値を不当に下げる）
    recent = set(pages)
    for x in entries:
        xd = safe_d(x.get("date"))   # 他のエントリの日付が壊れていても、このエントリの判定は落とさない
        if x.get("class") in npg.NEW_CLASSES and xd and (end - xd).days <= NEW_EXCLUDE_DAYS:
            recent.update(x.get("pages") or [])
    for r in npg.site_pages():
        rd = safe_d(r["published"])
        if rd and (end - rd).days <= NEW_EXCLUDE_DAYS:
            recent.add(r["page"])
    by_page, medians = {}, {}
    for p in pages:
        imp = sums.get(p, {}).get("impressions", 0)
        rec = {"impressions": imp, "clicks": sums.get(p, {}).get("clicks", 0), "first_shown": first.get(p)}
        if check == 28 and p not in verdicts:
            lang = npg.lang_of(p)
            if lang not in medians:
                peers = npg.peer_columns(lang, recent, health)
                medians[lang] = (statistics.median([sums.get(u, {}).get("impressions", 0) for u in peers])
                                 if len(peers) >= MIN_PEERS else None, len(peers))
            rec["median"], rec["peers"] = medians[lang]
            rec["verdict"] = ramp_verdict(imp, rec["median"])
        else:
            rec["verdict"] = verdicts.get(p) or ("shown" if imp else "not-shown")
        by_page[p] = rec
    primary = sorted(pages, key=lambda p: npg.LANG_ORDER[npg.lang_of(p)])[0]
    return {"verdict": by_page[primary]["verdict"], "mode": "ramp", "window": [str(start), str(end)],
            "pre": dict(ZERO), "post": window_metrics(pages, start, end), "by_page": by_page,
            "on": str(today())}


def measure_entry(e, latest, entries, health_box):
    """1 エントリの、期限が来た未判定の check を測る。返り値 [(key, measured に入れる dict, measurements の行)]。
    台帳（e）は書き換えない＝途中で例外が出ても、そのエントリには半端な measured が残らない。"""
    day = d(e["date"])
    pages = e.get("pages") or []
    out = []
    for check, (ps, pe) in WINDOWS.items():
        key = str(check)
        if key in (e.get("measured") or {}):
            continue
        if e.get("class") in npg.NEW_CLASSES:
            if latest < day + datetime.timedelta(days=check):
                continue
            if health_box[0] is None:
                health_box[0] = npg.latest_health() or {}
            m = measure_ramp(e, check, entries, health_box[0])
            rec = {"id": e["id"], "check": check, "measured_on": str(today()), "pages": pages, **m}
            rec.pop("on", None)
            out.append((key, m, rec))
            continue
        if latest < day + datetime.timedelta(days=pe):
            continue
        pre = window_metrics(pages, day + datetime.timedelta(days=PRE[0]), day + datetime.timedelta(days=PRE[1]))
        post = window_metrics(pages, day + datetime.timedelta(days=ps), day + datetime.timedelta(days=pe))
        v = verdict(pre, post)
        rec = {"id": e["id"], "check": check, "measured_on": str(today()), "pages": pages,
               "pre": pre, "post": post, "verdict": v}
        out.append((key, {"verdict": v, "pre": pre, "post": post, "on": str(today())}, rec))
    return out


def run():
    entries = read_jsonl(CHANGES)
    latest = latest_gsc_date()
    if not entries or not latest:
        return []
    new = []
    health_box = [None]
    for e in entries:
        try:
            got = measure_entry(e, latest, entries, health_box)
        except Exception as ex:  # noqa: BLE001 — 1 件の不正（壊れた日付・想定外の形）で、後ろのエントリの計測まで止めない
            log(f"効果測定: {e.get('id')} を飛ばす（{type(ex).__name__}: {ex}）")
            continue
        for key, m, rec in got:
            if not isinstance(e.get("measured"), dict):
                e["measured"] = {}
            e["measured"][key] = m
            new.append(rec)
    if not new:
        return []
    # 先に変更台帳（正本）を書き戻す。ここで落ちたら measurements には何も足さない＝翌朝の測り直しで行が重複しない
    write_jsonl(CHANGES, entries)
    try:
        seen = {(r.get("id"), r.get("check")) for r in read_jsonl(MEASURES)}
    except (json.JSONDecodeError, OSError):
        seen = set()
    for rec in new:
        if (rec["id"], rec["check"]) not in seen:
            append_jsonl(MEASURES, rec)
            seen.add((rec["id"], rec["check"]))
    return new


def main() -> int:
    if "--list" in sys.argv:
        for e in read_jsonl(CHANGES):
            m = e.get("measured") or {}
            print(e.get("date"), e.get("id"), e.get("class"), ",".join(e.get("pages") or [])[:60],
                  {k: (v or {}).get("verdict") for k, v in m.items()})
        return 0
    for r in run():
        pre, post = r["pre"], r["post"]
        if r.get("mode") == "ramp":
            print(f"{r['id']} {r['check']}日後: {r['verdict']}  " + "・".join(
                f"{p} 表示{x['impressions']}" + (f"/中央値{x['median']:g}" if x.get("median") is not None else "") + f"={x['verdict']}"
                for p, x in r["by_page"].items()))
            continue
        print(f"{r['id']} {r['check']}日後: {r['verdict']}  clicks {pre['clicks']}→{post['clicks']} "
              f"CTR {pre['ctr']:.3f}→{post['ctr']:.3f} leads {pre['leads']}→{post['leads']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
