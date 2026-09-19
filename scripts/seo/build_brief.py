#!/usr/bin/env python3
"""週次ブリーフ: 台帳（GSC・GA4・健診・変更台帳）から「今週どこを直すか」の材料を1枚にする。

    python3 scripts/seo/build_brief.py                 # weekly/<今日>/brief.md と brief.json を書く
    python3 scripts/seo/build_brief.py --stdout        # 画面に出すだけ

ここは決定論。判断（何を変えるか）は weekly_run.sh が呼ぶ Claude が brief を読んで行う。
"""
import datetime
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (COMMERCIAL, LEDGER, REPO, d, daterange, file_to_url, jload, path_of,  # noqa: E402
                    read_jsonl, today)

LEAD = "keyEvents:generate_lead"
COMMERCIAL_RE = re.compile(r"買(い|う|取|収)|売(り|る|買|却)|案件|物件|投資|ファンド|譲渡|価格|利回り|相場|完成渡し|権利|仲介|for sale|invest|acqui")
COOLDOWN_DAYS = 14


# ---------------------------------------------------------------- 読み込み

def gsc_days():
    return sorted(p.stem for p in (LEDGER / "gsc").glob("????-??-??.json"))


def load_range(kind, start, end):
    out = []
    for day in daterange(start, end):
        r = jload(LEDGER / kind / f"{day}.json")
        if r:
            out.append(r)
    return out


def agg_gsc(recs):
    tot = {"clicks": 0, "impressions": 0, "pos_w": 0.0, "days": len(recs)}
    pages, qp, q = {}, {}, {}
    for r in recs:
        t = r["totals"]
        tot["clicks"] += t["clicks"]; tot["impressions"] += t["impressions"]; tot["pos_w"] += t["position"] * t["impressions"]
        for p in r["pages"]:
            a = pages.setdefault(p["page"], {"clicks": 0, "impressions": 0, "pos_w": 0.0})
            a["clicks"] += p["clicks"]; a["impressions"] += p["impressions"]; a["pos_w"] += p["position"] * p["impressions"]
        for x in r["query_page"]:
            a = qp.setdefault((x["query"], x["page"]), {"clicks": 0, "impressions": 0, "pos_w": 0.0})
            a["clicks"] += x["clicks"]; a["impressions"] += x["impressions"]; a["pos_w"] += x["position"] * x["impressions"]
            b = q.setdefault(x["query"], {"clicks": 0, "impressions": 0, "pos_w": 0.0, "pages": {}})
            b["clicks"] += x["clicks"]; b["impressions"] += x["impressions"]; b["pos_w"] += x["position"] * x["impressions"]
            b["pages"][x["page"]] = b["pages"].get(x["page"], 0) + x["impressions"]
    def fin(a):
        a["ctr"] = a["clicks"] / a["impressions"] if a["impressions"] else 0.0
        a["position"] = a["pos_w"] / a["impressions"] if a["impressions"] else None
        a.pop("pos_w", None)
        return a
    fin(tot)
    for v in pages.values(): fin(v)
    for v in qp.values(): fin(v)
    for v in q.values(): fin(v)
    return tot, pages, qp, q


def agg_ga4(recs):
    tot = {"sessions": 0, "leads": 0, "engaged": 0, "days": len(recs)}
    landing, trans, events, intents, nav, news, search = {}, {}, {}, {}, {}, {}, {}
    for r in recs:
        t = r["totals"]
        tot["sessions"] += int(t.get("sessions") or 0); tot["leads"] += int(t.get(LEAD) or 0)
        tot["engaged"] += int(t.get("engagedSessions") or 0)
        for x in r.get("landing", []):
            a = landing.setdefault(x.get("landingPage"), {"sessions": 0, "leads": 0, "engaged": 0})
            a["sessions"] += int(x.get("sessions") or 0); a["leads"] += int(x.get(LEAD) or 0)
            a["engaged"] += int(x.get("engagedSessions") or 0)
        for x in r.get("transitions", []):
            k = (x["from"], x["to"])
            trans[k] = trans.get(k, 0) + int(x.get("views") or 0)
        for x in r.get("events", []):
            events[x["eventName"]] = events.get(x["eventName"], 0) + int(x.get("eventCount") or 0)
        for x in r.get("lead_intent") or []:
            k = (x.get("customEvent:intent"), x.get("landingPage"))
            intents[k] = intents.get(k, 0) + int(x.get(LEAD) or 0)
        for x in r.get("nav_click") or []:
            k = x.get("customEvent:nav_group"); nav[k] = nav.get(k, 0) + int(x.get("eventCount") or 0)
        for x in r.get("newsletter") or []:
            k = x.get("customEvent:placement"); news[k] = news.get(k, 0) + int(x.get("eventCount") or 0)
        for x in r.get("knowledge_search") or []:
            k = x.get("customEvent:search_term"); search[k] = search.get(k, 0) + int(x.get("eventCount") or 0)
    return tot, landing, trans, events, intents, nav, news, search


def cooldown_pages():
    """直近14日に人か自動が触ったページ（案件一覧の自動同期は除く）。今週は触らない。"""
    out = {}
    try:
        log_ = subprocess.run(["git", "log", f"--since={COOLDOWN_DAYS}.days", "--format=%H%x09%cs%x09%s"],
                              cwd=REPO, capture_output=True, text=True).stdout.splitlines()
        for line in log_:
            sha, date, subj = line.split("\t", 2)
            if subj.startswith("chore(projects)"):
                continue
            files = subprocess.run(["git", "show", "--name-only", "--format=", sha], cwd=REPO,
                                   capture_output=True, text=True).stdout.split()
            for f in files:
                u = file_to_url(f)
                if u:
                    out.setdefault(path_of(u), (date, subj[:60]))
    except Exception:  # noqa: BLE001
        pass
    for e in read_jsonl(LEDGER / "ledger" / "changes.jsonl"):
        if (today() - d(e["date"])).days <= COOLDOWN_DAYS:
            for p in e["pages"]:
                out.setdefault(p, (e["date"], e.get("summary", "")[:60]))
    return out


# ---------------------------------------------------------------- 描画

def pct(x):
    return f"{x*100:.1f}%"


def fnum(x):
    return "-" if x is None else (f"{x:.1f}" if isinstance(x, float) else str(x))


def delta(a, b):
    if not b:
        return "（前期0）"
    r = (a - b) / b * 100
    return f"{r:+.0f}%"


def render(days=28, for_latest=False):
    gd = gsc_days()
    if not gd:
        return "# ブリーフ\n\nGSC の台帳がまだ空です。`python3 scripts/seo/collect_daily.py --days 90` を先に。\n"
    latest = d(gd[-1])
    cur_s, cur_e = latest - datetime.timedelta(days=days - 1), latest
    prev_s, prev_e = cur_s - datetime.timedelta(days=days), cur_s - datetime.timedelta(days=1)
    w7_s = latest - datetime.timedelta(days=6); w7p_s, w7p_e = w7_s - datetime.timedelta(days=7), w7_s - datetime.timedelta(days=1)

    cur = load_range("gsc", cur_s, cur_e); prev = load_range("gsc", prev_s, prev_e)
    w7 = load_range("gsc", w7_s, latest); w7p = load_range("gsc", w7p_s, w7p_e)
    tot, pages, qp, q = agg_gsc(cur); ptot, ppages, _, pq = agg_gsc(prev)
    t7, _, _, _ = agg_gsc(w7); t7p, _, _, _ = agg_gsc(w7p)

    ga_cur = load_range("ga4", cur_s, cur_e); ga_prev = load_range("ga4", prev_s, prev_e)
    ga7 = load_range("ga4", w7_s, latest); ga7p = load_range("ga4", w7p_s, w7p_e)
    gtot, landing, trans, events, intents, nav, news, search = agg_ga4(ga_cur)
    gptot, planding, *_ = agg_ga4(ga_prev)
    g7, *_ = agg_ga4(ga7); g7p, *_ = agg_ga4(ga7p)

    health_files = sorted((LEDGER / "health").glob("????-??-??.json"))
    health = jload(health_files[-1]) if health_files else None
    inbound = (health or {}).get("inbound", {})

    L = []
    L.append(f"# scix.co.jp ブリーフ（生成 {today()}・GSC最新日 {latest}・{days}日窓 {cur_s}〜{cur_e}）\n")
    L.append("## 1. 全体\n")
    L.append("| 指標 | 直近7日 | 前7日 | 増減 | 直近28日 | 前28日 | 増減 |\n|---|---|---|---|---|---|---|")
    L.append(f"| GSC クリック | {t7['clicks']} | {t7p['clicks']} | {delta(t7['clicks'], t7p['clicks'])} | {tot['clicks']} | {ptot['clicks']} | {delta(tot['clicks'], ptot['clicks'])} |")
    L.append(f"| GSC 表示 | {t7['impressions']} | {t7p['impressions']} | {delta(t7['impressions'], t7p['impressions'])} | {tot['impressions']} | {ptot['impressions']} | {delta(tot['impressions'], ptot['impressions'])} |")
    L.append(f"| GSC CTR | {pct(t7['ctr'])} | {pct(t7p['ctr'])} | | {pct(tot['ctr'])} | {pct(ptot['ctr'])} | |")
    L.append(f"| GSC 平均順位 | {fnum(t7['position'])} | {fnum(t7p['position'])} | | {fnum(tot['position'])} | {fnum(ptot['position'])} | |")
    if gtot["days"]:
        L.append(f"| GA4 セッション | {g7['sessions']} | {g7p['sessions']} | {delta(g7['sessions'], g7p['sessions'])} | {gtot['sessions']} | {gptot['sessions']} | {delta(gtot['sessions'], gptot['sessions'])} |")
        L.append(f"| GA4 問い合わせ（generate_lead） | {g7['leads']} | {g7p['leads']} | | {gtot['leads']} | {gptot['leads']} | |")
    else:
        L.append("| GA4 | （トークン未取得＝未収集） | | | | | |")
    L.append(f"\nデータ日数: GSC {tot['days']}/{days}・GA4 {gtot['days']}/{days}\n")

    # 2. リード
    L.append("## 2. 問い合わせ（GA4 generate_lead・28日）\n")
    if gtot["days"]:
        top_l = sorted(((k, v) for k, v in landing.items() if v["leads"]), key=lambda kv: -kv[1]["leads"])
        L.append("| 着地ページ | リード | セッション | 前28日のリード |\n|---|---|---|---|")
        for k, v in top_l[:20]:
            L.append(f"| {k} | {v['leads']} | {v['sessions']} | {planding.get(k, {}).get('leads', 0)} |")
        if intents:
            by_intent = {}
            for (i, _), n in intents.items():
                by_intent[i or "(not set)"] = by_intent.get(i or "(not set)", 0) + n
            L.append("\n用件（intent）別: " + "・".join(f"{i}={n}" for i, n in sorted(by_intent.items(), key=lambda kv: -kv[1])))
        if news:
            L.append("更新メール登録（placement 別）: " + "・".join(f"{k}={v}" for k, v in sorted(news.items(), key=lambda kv: -kv[1])))
        if nav:
            L.append("ナビのクリック（nav_group 別）: " + "・".join(f"{k}={v}" for k, v in sorted(nav.items(), key=lambda kv: -kv[1])))
        if search:
            L.append("ナレッジ検索の語: " + "・".join(f"{k}({v})" for k, v in sorted(search.items(), key=lambda kv: -kv[1])[:20]))
        L.append("")
    else:
        L.append("GA4 未収集。\n")

    # 3. 収益ページ
    L.append("## 3. 収益ページ（買い手 ≧ 投資家 ＞ 土地）\n")
    L.append("| ページ | クリック | 前28日 | 表示 | CTR | 順位 | GA4 着地 | リード | 被リンク |\n|---|---|---|---|---|---|---|---|---|")
    for p in COMMERCIAL:
        a = pages.get(p, {"clicks": 0, "impressions": 0, "ctr": 0, "position": None}); b = ppages.get(p, {"clicks": 0})
        la = landing.get(p, {"sessions": 0, "leads": 0})
        L.append(f"| {p} | {a['clicks']} | {b['clicks']} | {a['impressions']} | {pct(a['ctr'])} | {fnum(a['position'])} | {la['sessions']} | {la['leads']} | {inbound.get(p, '-')} |")
    L.append("")

    # 4. ページ別
    lim = 15 if for_latest else 40
    L.append(f"## 4. ページ別（28日・クリック上位{lim}）\n")
    L.append("| ページ | クリック | 前28日 | 増減 | 表示 | CTR | 順位 | GA4 着地 | リード |\n|---|---|---|---|---|---|---|---|---|")
    for p, a in sorted(pages.items(), key=lambda kv: -kv[1]["clicks"])[:lim]:
        b = ppages.get(p, {"clicks": 0}); la = landing.get(p, {"sessions": 0, "leads": 0})
        L.append(f"| {p} | {a['clicks']} | {b['clicks']} | {delta(a['clicks'], b['clicks'])} | {a['impressions']} | {pct(a['ctr'])} | {fnum(a['position'])} | {la['sessions']} | {la['leads']} |")
    # 落ちたページ
    drops = [(p, a, ppages[p]) for p, a in pages.items() if p in ppages and ppages[p]["clicks"] >= 20 and a["clicks"] < ppages[p]["clicks"] * 0.7]
    if drops:
        L.append("\n**クリックが3割以上落ちたページ**: " + "・".join(f"{p} {b['clicks']}→{a['clicks']}" for p, a, b in sorted(drops, key=lambda x: x[2]['clicks'] - x[1]['clicks'])[:15]))
    L.append("")

    # 5. 検索語
    L.append("## 5. 検索語（28日）\n")
    bands = {}
    for p, a in pages.items():
        if a["impressions"] >= 50 and a["position"]:
            band = "1-3" if a["position"] <= 3 else "4-10" if a["position"] <= 10 else "11-20" if a["position"] <= 20 else "21+"
            bands.setdefault(band, []).append(a["ctr"])
    med = {b: statistics.median(v) for b, v in bands.items()}
    L.append("順位帯ごとの CTR 中央値（ページ・表示50以上）: " + "・".join(f"{b} {pct(m)}" for b, m in sorted(med.items())) + "\n")
    lim = 15 if for_latest else 40
    L.append(f"### 5a. 4〜20位で表示が多い語（title/本文で押し上げる候補・上位{lim}）\n")
    L.append("| 検索語 | 表示 | クリック | CTR | 順位 | 主な着地 |\n|---|---|---|---|---|---|")
    sd = [(k, v) for k, v in q.items() if v["impressions"] >= 50 and v["position"] and 4 <= v["position"] <= 20]
    for k, v in sorted(sd, key=lambda kv: -kv[1]["impressions"])[:lim]:
        top = max(v["pages"].items(), key=lambda kv: kv[1])[0]
        L.append(f"| {k} | {v['impressions']} | {v['clicks']} | {pct(v['ctr'])} | {fnum(v['position'])} | {top} |")
    L.append(f"\n### 5b. 表示は多いのに CTR が帯の中央値の半分未満のページ（description/title の候補）\n")
    L.append("| ページ | 表示 | クリック | CTR | 順位 | 帯の中央値 |\n|---|---|---|---|---|---|")
    low = []
    for p, a in pages.items():
        if a["impressions"] >= 100 and a["position"]:
            band = "1-3" if a["position"] <= 3 else "4-10" if a["position"] <= 10 else "11-20" if a["position"] <= 20 else "21+"
            m = med.get(band)
            if m and a["ctr"] < m * 0.5:
                low.append((p, a, m))
    for p, a, m in sorted(low, key=lambda x: -x[1]["impressions"])[:lim]:
        L.append(f"| {p} | {a['impressions']} | {a['clicks']} | {pct(a['ctr'])} | {fnum(a['position'])} | {pct(m)} |")
    L.append(f"\n### 5c. 商用の意図がある語（買う・売る・案件・投資・ファンド…）と着地\n")
    L.append("| 検索語 | 表示 | クリック | 順位 | 着地 |\n|---|---|---|---|---|")
    com = [(k, v) for k, v in q.items() if COMMERCIAL_RE.search(k) and v["impressions"] >= 10]
    for k, v in sorted(com, key=lambda kv: -kv[1]["impressions"])[:lim]:
        top = max(v["pages"].items(), key=lambda kv: kv[1])[0]
        flag = "" if top in COMMERCIAL else " ←コラム着地"
        L.append(f"| {k} | {v['impressions']} | {v['clicks']} | {fnum(v['position'])} | {top}{flag} |")
    L.append(f"\n### 5d. 表示30以上でクリック0の語\n")
    zero = [(k, v) for k, v in q.items() if v["impressions"] >= 30 and v["clicks"] == 0]
    L.append("・".join(f"{k}({v['impressions']}/{fnum(v['position'])}位)" for k, v in sorted(zero, key=lambda kv: -kv[1]["impressions"])[:lim]) or "なし")
    L.append("")

    # 6. 行動
    L.append("## 6. サイト内の動き（GA4・28日）\n")
    if gtot["days"]:
        into = {}
        for (f, t), n in trans.items():
            if t in COMMERCIAL and f != t:
                into.setdefault(t, {})[f] = into.get(t, {}).get(f, 0) + n
        for t in COMMERCIAL:
            src = into.get(t)
            if src:
                L.append(f"- **{t} へ**: " + "・".join(f"{f} {n}" for f, n in sorted(src.items(), key=lambda kv: -kv[1])[:8]))
        # コラム別: セッションと商用ページへの遷移
        out_by = {}
        for (f, t), n in trans.items():
            if t in COMMERCIAL and f.startswith(("/column-", "/en/column-", "/zh-column-")):
                out_by[f] = out_by.get(f, 0) + n
        L.append("\n| コラム（着地セッション上位） | セッション | エンゲージ | リード | 収益ページへの遷移 |\n|---|---|---|---|---|")
        cols = [(k, v) for k, v in landing.items() if k and k.startswith(("/column-", "/en/column-", "/zh-column-"))]
        for k, v in sorted(cols, key=lambda kv: -kv[1]["sessions"])[:lim]:
            L.append(f"| {k} | {v['sessions']} | {v['engaged']} | {v['leads']} | {out_by.get(k, 0)} |")
        L.append("\n主なイベント: " + "・".join(f"{k}={v}" for k, v in sorted(events.items(), key=lambda kv: -kv[1])[:12]))
    else:
        L.append("GA4 未収集。")
    L.append("")

    # 7. 健診
    L.append("## 7. 本番HTMLの健診\n")
    if health:
        L.append(f"{health['date']}・{health['n']}ページ・問題 {len(health['issues'])}件")
        for i in health["issues"][:40]:
            L.append(f"- {i}")
    else:
        L.append("未実施。")
    L.append("")

    # 8. 変更台帳と計測
    if not for_latest:
        L.append("## 8. 変更台帳（60日）と効果測定\n")
        L.append("| 変更日 | id | 種別 | ページ | 要約 | 2週後 | 4週後 |\n|---|---|---|---|---|---|---|")
        for e in sorted(read_jsonl(LEDGER / "ledger" / "changes.jsonl"), key=lambda x: x["date"], reverse=True):
            if (today() - d(e["date"])).days > 60:
                continue
            m = e.get("measured") or {}
            def vs(k):
                x = m.get(k)
                if not x:
                    return "未"
                return f"{x['verdict']}（{x['pre']['clicks']}→{x['post']['clicks']}, CTR {pct(x['pre']['ctr'])}→{pct(x['post']['ctr'])}, lead {x['pre']['leads']}→{x['post']['leads']}）"
            L.append(f"| {e['date']} | {e['id']} | {e.get('class','')} | {' '.join(e['pages'][:6])}{'…' if len(e['pages'])>6 else ''} | {e.get('summary','')[:80]} | {vs('14')} | {vs('28')} |")
        L.append("\n**worse の変更は差し戻し候補**（同じ変更を繰り返さない）。\n")
        cd = cooldown_pages()
        L.append("## 9. 今週触らないページ（14日以内に変更済み・効果測定中）\n")
        L.append("・".join(f"{p}（{dt}）" for p, (dt, _) in sorted(cd.items())) or "なし")
        L.append("")
    return "\n".join(L) + "\n"


def brief_json(days=28):
    gd = gsc_days()
    if not gd:
        return {}
    latest = d(gd[-1])
    cur = load_range("gsc", latest - datetime.timedelta(days=days - 1), latest)
    tot, pages, _, _ = agg_gsc(cur)
    ga = load_range("ga4", latest - datetime.timedelta(days=days - 1), latest)
    _, landing, *_ = agg_ga4(ga)
    return {"generated": str(today()), "latest_gsc": str(latest), "days": days, "totals": tot,
            "pages": pages, "landing": landing, "cooldown": {k: v[0] for k, v in cooldown_pages().items()}}


def main() -> int:
    text = render()
    if "--stdout" in sys.argv:
        print(text); return 0
    out = LEDGER / "weekly" / str(today())
    out.mkdir(parents=True, exist_ok=True)
    (out / "brief.md").write_text(text, encoding="utf-8")
    (out / "brief.json").write_text(json.dumps(brief_json(), ensure_ascii=False), encoding="utf-8")
    print(out / "brief.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
