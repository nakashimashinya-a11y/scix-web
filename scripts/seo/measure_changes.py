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

    python3 scripts/seo/measure_changes.py          # 期限が来たものを計測して台帳に書く
    python3 scripts/seo/measure_changes.py --list   # 台帳を表示
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LEDGER, d, daterange, jload, log, read_jsonl, today, write_jsonl, append_jsonl  # noqa: E402

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


def run():
    entries = read_jsonl(CHANGES)
    latest = latest_gsc_date()
    if not entries or not latest:
        return []
    new = []
    changed = False
    for e in entries:
        day = d(e["date"])
        for check, (ps, pe) in WINDOWS.items():
            key = str(check)
            if key in (e.get("measured") or {}):
                continue
            if latest < day + datetime.timedelta(days=pe):
                continue
            pre = window_metrics(e["pages"], day + datetime.timedelta(days=PRE[0]), day + datetime.timedelta(days=PRE[1]))
            post = window_metrics(e["pages"], day + datetime.timedelta(days=ps), day + datetime.timedelta(days=pe))
            v = verdict(pre, post)
            rec = {"id": e["id"], "check": check, "measured_on": str(today()), "pages": e["pages"],
                   "pre": pre, "post": post, "verdict": v}
            e.setdefault("measured", {})[key] = {"verdict": v, "pre": pre, "post": post, "on": str(today())}
            append_jsonl(MEASURES, rec)
            new.append(rec)
            changed = True
    if changed:
        write_jsonl(CHANGES, entries)
    return new


def main() -> int:
    if "--list" in sys.argv:
        for e in read_jsonl(CHANGES):
            m = e.get("measured") or {}
            print(e["date"], e["id"], e.get("class"), ",".join(e["pages"])[:60],
                  {k: v["verdict"] for k, v in m.items()})
        return 0
    for r in run():
        pre, post = r["pre"], r["post"]
        print(f"{r['id']} {r['check']}日後: {r['verdict']}  clicks {pre['clicks']}→{post['clicks']} "
              f"CTR {pre['ctr']:.3f}→{post['ctr']:.3f} leads {pre['leads']}→{post['leads']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
