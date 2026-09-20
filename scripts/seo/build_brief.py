#!/usr/bin/env python3
"""週次ブリーフ: 台帳（GSC・GA4・健診・変更台帳）から「今週どこを直すか」の材料を1枚にする。

    python3 scripts/seo/build_brief.py                 # weekly/<今日>/brief.md と brief.json を書く
    python3 scripts/seo/build_brief.py --stdout        # 画面に出すだけ
    python3 scripts/seo/build_brief.py --structure     # 月1回の構成レビュー用（S1〜S8 節を足す）。weekly/<今日>/structure/ に書く

ここは決定論。判断（何を変えるか）は weekly_run.sh が呼ぶ Claude が brief を読んで行う。
10 節（新規ページの立ち上がり・90日表示ゼロ）は台帳と git（origin/main）だけで作る＝追加 API なし。
8 節の末尾「構成の変更」の表は、月1回の構成レビューが公開した変更（変更台帳の source=structure）の、測る対象のページ（＝編集した
ページ）に着地したセッションと問い合わせ（generate_lead）の前後、そのページから送客先（マニフェストの kpi_pages。無ければ収益ページ
全部）への遷移の前後。構成の変更の KPI は問い合わせと送客＝GSC の判定（better／flat／worse）には出ないので、ここで見る:
14 日の窓がそろった行に「注意」（リード減・送客減）を付け、週次は worse と注意つきの行を差し戻し候補として読む。
数字は Drive のブリーフにだけ出る（公開リポジトリ・コミット文・PR には写さない＝検査 guard_diff.py が公開欄の件数を止める）。
--structure の S1〜S8 節（ナビのクリック・遷移の太さ・コラムの送客・セッション0・孤立・カテゴリ別・トップの節・過去の提案）も同じ
（中身は structure.py）。通常の週次のブリーフ（weekly/<今日>/brief.md）は上書きしない。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (COMMERCIAL, LEDGER, REPO, d, daterange, file_to_url, jload, path_of,  # noqa: E402
                    read_jsonl, safe_d, today)
import newpages as npg  # noqa: E402

LEAD = "keyEvents:generate_lead"
COMMERCIAL_RE = re.compile(r"買(い|う|取|収)|売(り|る|買|却)|案件|物件|投資|ファンド|譲渡|価格|利回り|相場|完成渡し|権利|仲介|for sale|invest|acqui")
COOLDOWN_DAYS = 14
NEW_DAYS = 60            # 「新規ページ」= 公開からこの日数以内
NEW_GRACE_DAYS = 14      # 公開からこの日数を超えて表示ゼロなら旗
ZERO_WINDOW = 90         # sitemap にあるのに表示ゼロ、を見る窓
FLAG_ZERO = "公開14日超で表示ゼロ"
FLAG_INBOUND = "被リンク1以下"
FLAG_SITEMAP = "sitemap 未登録"
FLAG_JA_ONLY = "JA専用の登録漏れ"


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


def cooldown_pages(structure=False):
    """直近14日に人か自動が触ったページ（案件一覧の自動同期は除く）。今週は触らない。

    structure=True（月1回の構成レビュー用）: ハブ・トップ（structure.HUB_TOP_FILES）の凍結は、**変更台帳の構成系の
    エントリだけ** で決める（structure.is_structure_entry: class が hub／hub-order／top-order／nav／rollback、または
    source=structure で、そのページが pages に載っているもの。rollback＝週次による差し戻し）。git の履歴と、それ以外の class のエントリでは凍結しない
    （毎週コラムを足すたびにハブ・トップはカード・件数・新着が変わる＝全コミットで数えると / と /knowledge が常に
    凍結され、hub-order・top-order を一度も提案できない）。ハブ・トップ以外のページは週次と同じ数え方。"""
    out = {}
    st = None
    if structure:
        import structure as st  # noqa: PLC0415
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
                if not u:
                    continue
                if st is not None and f in st.HUB_TOP_FILES:
                    continue  # 構成レビューでは、ハブ・トップを git の履歴で凍結しない（下の変更台帳だけで決める）
                out.setdefault(path_of(u), (date, subj[:60]))
    except Exception:  # noqa: BLE001
        pass
    for e in read_jsonl(LEDGER / "ledger" / "changes.jsonl"):
        day = safe_d(e.get("date"))
        if day and (today() - day).days <= COOLDOWN_DAYS:
            for p in e.get("pages") or []:
                if st is not None and p in st.HUB_TOP_PAGES and not st.is_structure_entry(e):
                    continue  # title・description などの変更では、構成レビューのハブ・トップは凍結しない
                out.setdefault(p, (e["date"], (e.get("summary") or "")[:60]))
    return out


def hub_top_freeze_lines(cd) -> list:
    """9 節の末尾に足す行（構成レビュー用のブリーフだけ）。cd＝cooldown_pages(structure=True)。"""
    import structure as st  # noqa: PLC0415
    hubs = sorted(st.HUB_TOP_PAGES)
    frozen = [f"{p}（{cd[p][0]}・{cd[p][1]}）" for p in hubs if p in cd]
    out = ["\nハブ・トップ（" + "・".join(hubs) + "）の凍結は、この構成レビュー用のブリーフでは **変更台帳の構成系のエントリだけ** で"
           "決めている: class が hub／hub-order／top-order／nav／rollback（週次による差し戻し）、または構成レビューが公開したもの（自動公開・PR のマージ＝source=structure）で、"
           "そのページが測る対象（pages）に載っている変更。コラムを足したときのカード・件数・新着・JSON-LD の焼き直しや、"
           "title・description の変更では凍結しない（毎週コラムを足すたびに触られるため）。"
           "いま凍結中のハブ・トップ: " + ("・".join(frozen) if frozen else "なし") + "。"]
    try:
        loose = st.unrecorded_layout_commits(COOLDOWN_DAYS, frozen=set(cd), cwd=REPO)
    except Exception:  # noqa: BLE001
        loose = []
    if loose:
        out.append("\n参考（凍結ではない）: 直近 14 日に、変更台帳に構成系の記帳が無いままハブ・トップの並び・見出し・本文を変えたコミットがある: "
                   + "・".join(f"{p}（{dt}・{subj}）" for p, dt, subj in loose)
                   + "。そのページの 28 日の数字には変更前の期間が混ざる＝根拠にするなら、そのことを rationale に書く。")
    return out


# ---------------------------------------------------------------- 新規ページ（10 節）

def new_pages_data(latest, pages28, landing):
    """(new_rows, zero_rows)。どちらも旗・緊急度の順に並べた全件（描画側で行数を切る）。

    new_rows:  公開 NEW_DAYS 日以内のページ。公開日は Article JSON-LD の datePublished、無ければ git の初回コミット日
    zero_rows: 本番の sitemap（＝健診のページ一覧）にあり、公開 NEW_GRACE_DAYS 日以上で、GSC ZERO_WINDOW 日の表示がゼロ
    """
    health = npg.latest_health() or {}
    hpages = {p["url"]: p for p in health.get("pages", [])}
    inbound = npg.inbound_counts(health)
    hdate = health.get("date")
    site = npg.site_pages()
    files = {r["file"] for r in site}
    ja_only = npg.ja_only_columns()
    sums90, first90, _ = npg.gsc_page_sums(latest - datetime.timedelta(days=ZERO_WINDOW - 1), latest)

    new_rows = []
    for r in site:
        age = npg.days_since(r["published"], today())
        if age is None or age < 0 or age > NEW_DAYS:
            continue
        p = r["page"]
        a = pages28.get(p) or {"impressions": 0, "clicks": 0}
        in_health = p in hpages
        flags = []
        if age > NEW_GRACE_DAYS and not a["impressions"]:
            flags.append(FLAG_ZERO)
        if in_health and inbound.get(p, 0) <= 1:
            flags.append(FLAG_INBOUND)
        if hpages and not in_health and hdate and r["published"] < hdate:
            flags.append(FLAG_SITEMAP)  # 健診は本番の sitemap を辿る＝そこに居ない
        if r["lang"] == "ja" and npg.is_column(p) and p not in ja_only and not (
                "en/" + r["file"] in files and "zh-" + r["file"] in files):
            flags.append(FLAG_JA_ONLY)
        new_rows.append({"page": p, "lang": r["lang"], "published": r["published"], "published_by": r["published_by"],
                         "age_days": age, "first_shown": first90.get(p), "impressions": a["impressions"],
                         "clicks": a["clicks"], "ga4_sessions": (landing.get(p) or {}).get("sessions", 0),
                         "inbound": inbound.get(p, 0) if in_health else None, "flags": flags})
    # 旗つき（旗の多い順・古い順）→ 旗なしは「まだ表示が出ていない」ものを先に（次に旗が立つ候補）
    new_rows.sort(key=lambda x: (0, -len(x["flags"]), -x["age_days"], x["page"]) if x["flags"]
                  else (1, 1 if x["impressions"] else 0, -x["age_days"], x["page"]))

    pub = {r["page"]: r for r in site}
    zero_rows = []
    for p, h in hpages.items():
        if h.get("status") != 200 or sums90.get(p, {}).get("impressions", 0):
            continue
        r = pub.get(p) or {}
        age = npg.days_since(r.get("published"), today())
        if age is not None and age < NEW_GRACE_DAYS:
            continue
        zero_rows.append({"page": p, "lang": npg.lang_of(p), "published": r.get("published"), "age_days": age,
                          "inbound": inbound.get(p, 0), "ga4_sessions": (landing.get(p) or {}).get("sessions", 0)})
    zero_rows.sort(key=lambda x: (x["inbound"], -(x["age_days"] or 10 ** 6), x["page"]))
    return new_rows, zero_rows


def render_new_pages(L, new_rows, zero_rows, latest, lim_new=40, lim_zero=20):
    L.append(f"## 10. 新規ページ（公開{NEW_DAYS}日以内）の立ち上がり\n")
    if not new_rows:
        L.append(f"公開{NEW_DAYS}日以内のページは無い。\n")
    else:
        flagged = [x for x in new_rows if x["flags"]]
        by_flag = {}
        for x in flagged:
            for f in x["flags"]:
                by_flag[f] = by_flag.get(f, 0) + 1
        L.append(f"{len(new_rows)}ページ・旗つき {len(flagged)}"
                 + ("（" + "・".join(f"{k} {v}" for k, v in sorted(by_flag.items(), key=lambda kv: -kv[1])) + "）" if by_flag else "")
                 + f"。表示・クリックは GSC の28日窓（最新日 {latest}）、初表示日は台帳で最初に表示が出た日、"
                   "被リンクは健診（サイト内でそのページを指すページ数・自分自身は除く）。旗つきを先に並べる。\n")
        L.append("| ページ | 公開日 | 経過日数 | 初表示日 | 表示 | クリック | GA4 着地 | 被リンク | 旗 |\n|---|---|---|---|---|---|---|---|---|")
        for x in new_rows[:lim_new]:
            L.append(f"| {x['page']} | {x['published']}{'（git）' if x['published_by'] == 'git' else ''} | {x['age_days']} | "
                     f"{x['first_shown'] or '未'} | {x['impressions']} | {x['clicks']} | {x['ga4_sessions']} | "
                     f"{'-' if x['inbound'] is None else x['inbound']} | {'・'.join(x['flags'])} |")
        if len(new_rows) > lim_new:
            L.append(f"\n（ほか {len(new_rows) - lim_new} ページ。全件は brief.json の new_pages）")
        L.append("")
    L.append(f"### 10b. sitemap にあるのに{ZERO_WINDOW}日表示ゼロ（公開{NEW_GRACE_DAYS}日以上）\n")
    if not zero_rows:
        L.append("なし。\n")
        return
    L.append(f"{len(zero_rows)}ページ。被リンクの少ない順。\n")
    L.append("| ページ | 公開日 | 経過日数 | 被リンク | GA4 着地（28日） |\n|---|---|---|---|---|")
    for x in zero_rows[:lim_zero]:
        L.append(f"| {x['page']} | {x['published'] or '-'} | {'-' if x['age_days'] is None else x['age_days']} | {x['inbound']} | {x['ga4_sessions']} |")
    if len(zero_rows) > lim_zero:
        L.append(f"\n（ほか {len(zero_rows) - lim_zero} ページ。全件は brief.json の zero_impression）")
    L.append("")


def ramp_needs_care(entries, pages28):
    """新規ページの立ち上がり判定（measure_changes.py の mode=ramp）で手当てが要るもの。
    ページごとに最新の判定を見る。判定のあとで表示が出たページ（直近28日に表示あり）は not-shown から外す。
    返り値 (not_shown, below_median)＝[(page, check, 表示, 中央値)]"""
    not_shown, below = [], []
    for e in entries:
        m = e.get("measured") or {}
        ramp = sorted((int(k), v) for k, v in m.items() if isinstance(v, dict) and v.get("mode") == "ramp")
        if not ramp:
            continue
        check, last = ramp[-1]
        for p, x in (last.get("by_page") or {}).items():
            if x.get("verdict") == "not-shown":
                if (pages28.get(p) or {}).get("impressions"):
                    continue
                not_shown.append((p, check, x.get("impressions", 0), x.get("median")))
            elif x.get("verdict") == "below-median":
                below.append((p, check, x.get("impressions", 0), x.get("median")))
    return not_shown, below


LEAD_DROP_MIN = 2        # 注意「リード減」: 前の窓の着地リードがこの件数以上で、後が半分以下
FEED_DROP_MIN = 10       # 注意「送客減」: 前の窓の送客先への遷移がこの回数以上で、後が 7 割未満
FEED_DROP_RATIO = 0.7


def transition_views(sources, targets, start, end) -> int:
    """sources のどれか → targets のどれか の遷移（GA4 のページ遷移の表示回数）の合計。"""
    import structure as st  # noqa: PLC0415
    sources, targets = set(sources), set(targets)
    n = 0
    for day in daterange(start, end):
        for x in (jload(LEDGER / "ga4" / f"{day}.json") or {}).get("transitions") or []:
            f, t = st.norm(x.get("from")), st.norm(x.get("to"))
            if f != t and f in sources and t in targets:
                n += int(x.get("views") or 0)
    return n


def structure_change_rows(ledger) -> list:
    """構成の変更（変更台帳の source=structure）ごとに、測る対象のページ（pages＝編集したページ）に着地したセッションと
    問い合わせの前後、そのページから送客先（kpi_pages。無ければ収益ページ全部）への遷移の前後。
    判定済みなら効果測定（measure_changes.py）の窓の値をそのまま使う（28 日後が出ていればそちら）。まだなら、
    前＝変更日の 15〜2 日前、後＝変更日の 3 日後〜（最長 16 日後・GA4 が届いている日まで）を途中経過として数える。
    flags（注意）は 14 日の窓がそろった行にだけ付ける（途中経過は後の窓が短い＝減って見えて当たり前）: 判定は GSC の
    クリックと CTR で決まり、問い合わせ・送客が減っても worse にならないので、週次が差し戻しを検討する材料を別に出す。"""
    import measure_changes as mc  # noqa: PLC0415
    ga_days = sorted(p.stem for p in (LEDGER / "ga4").glob("????-??-??.json"))
    latest_ga = d(ga_days[-1]) if ga_days else None
    rows = []
    for e in ledger:
        day = safe_d(e.get("date"))
        if e.get("source") != "structure" or not day:
            continue
        pages = [p for p in (e.get("pages") or []) if isinstance(p, str)]
        m = e.get("measured") or {}
        verdicts = {k: (m.get(k) or {}).get("verdict") for k in ("14", "28")}
        done = next((k for k in ("28", "14") if isinstance(m.get(k), dict) and isinstance(m[k].get("pre"), dict)
                     and isinstance(m[k].get("post"), dict)), None)
        pre_w = (day + datetime.timedelta(days=mc.PRE[0]), day + datetime.timedelta(days=mc.PRE[1]))
        if done:
            pre, post, window = m[done]["pre"], m[done]["post"], f"{done}日後の判定の窓"
            post_w = tuple(day + datetime.timedelta(days=n) for n in mc.WINDOWS[int(done)])
        else:
            pre = mc.window_metrics(pages, *pre_w)
            start = day + datetime.timedelta(days=mc.WINDOWS[14][0])
            if latest_ga and latest_ga >= start:
                post_w = (start, min(day + datetime.timedelta(days=mc.WINDOWS[14][1]), latest_ga))
                post = mc.window_metrics(pages, *post_w)
                window = f"途中（GA4 {post['ga4_days']}日ぶん）"
            else:
                post, post_w, window = None, None, "まだ（公開から3日未満）"
        kpi_pages = [p for p in (e.get("kpi_pages") or []) if isinstance(p, str)]
        targets = kpi_pages or COMMERCIAL
        feed = [transition_views(pages, targets, *pre_w), None if post_w is None else transition_views(pages, targets, *post_w)]
        leads = [pre.get("leads", 0), None if post is None else post.get("leads", 0)]
        flags = []
        if done:
            if leads[0] >= LEAD_DROP_MIN and leads[1] * 2 <= leads[0]:
                flags.append("リード減")
            if feed[0] >= FEED_DROP_MIN and feed[1] < feed[0] * FEED_DROP_RATIO:
                flags.append("送客減")
        rows.append({"date": e["date"], "id": e.get("id"), "class": e.get("class"), "pages": pages, "kpi_pages": kpi_pages,
                     "commit": (e.get("commit") or "")[:10], "summary": (e.get("summary") or "")[:80], "window": window,
                     "sessions": [pre.get("sessions", 0), None if post is None else post.get("sessions", 0)],
                     "leads": leads, "feed": feed, "flags": flags,
                     "verdict_14": verdicts["14"], "verdict_28": verdicts["28"]})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def render_structure_changes(L, rows) -> None:
    if not rows:
        return
    L.append("### 構成の変更（月1回の構成レビューが公開したもの・source=structure）— 着地・問い合わせ・送客の前後\n")
    L.append("測る対象のページ（＝編集したページ）に着地したセッションと問い合わせ（generate_lead）、そのページから送客先"
             "（マニフェストの kpi_pages。無ければ収益ページ全部）への遷移。前＝変更日の 15〜2 日前の 14 日。"
             "**worse と、注意（リード減・送客減）の付いた行は差し戻し候補**（`git show <commit>` で差分を見て戻す）。"
             "判定（better／flat／worse）は GSC のクリックと CTR で決まる＝構成の変更の本来の KPI（問い合わせ・送客）が減っても worse には"
             f"ならないので、注意の列で見る（14 日の窓がそろった行にだけ付く。リード減＝前 {LEAD_DROP_MIN} 件以上が半分以下／"
             f"送客減＝前 {FEED_DROP_MIN} 以上が {FEED_DROP_RATIO:.0%} 未満）。問い合わせは件数が少ないので 1〜2 件の差は揺れとして読む。"
             "逆に worse でも、着地・リード・送客が落ちていなければ GSC の揺れのことがある。"
             "**この表の件数は、マニフェストの公開される欄（summary_lines・summary・rationale・kpi…）に写さない**（private_note へ）。\n")
    L.append("| 変更日 | id | 種別 | ページ | commit | 着地セッション 前→後 | 着地リード 前→後 | 送客先への遷移 前→後 | 後の窓 | 判定 14日／28日 | 注意 |\n|---|---|---|---|---|---|---|---|---|---|---|")
    def arrow(v):
        return f"{v[0]}→{'-' if v[1] is None else v[1]}"
    for r in rows:
        L.append(f"| {r['date']} | {r['id']} | {r['class']} | {' '.join(r['pages'][:6])}{'…' if len(r['pages']) > 6 else ''} | {r['commit']} | "
                 f"{arrow(r['sessions'])} | {arrow(r['leads'])} | {arrow(r['feed'])}{'（' + ' '.join(r['kpi_pages'][:4]) + '）' if r['kpi_pages'] else ''} | "
                 f"{r['window']} | {r['verdict_14'] or '未'}／{r['verdict_28'] or '未'} | {'**' + '・'.join(r['flags']) + '**' if r['flags'] else ''} |")
    L.append("")


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


def render(days=28, for_latest=False, structure=False):
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
        ledger = [e for e in read_jsonl(LEDGER / "ledger" / "changes.jsonl")
                  if safe_d(e.get("date")) and (today() - safe_d(e["date"])).days <= 60]
        auto_new = [e for e in ledger if e.get("source") == "manual-auto"]
        for e in sorted(ledger, key=lambda x: x["date"], reverse=True):
            if e.get("source") == "manual-auto":
                continue  # 新規ページの自動記帳は下に件数だけ（個別は 10 節）
            m = e.get("measured") or {}
            def vs(k):
                x = m.get(k)
                if not x:
                    return "未"
                if x.get("mode") == "ramp":  # 新規ページ＝前後比較ではなく立ち上がり
                    return f"{x['verdict']}（表示 {x['post']['impressions']}・クリック {x['post']['clicks']}）"
                return f"{x['verdict']}（{x['pre']['clicks']}→{x['post']['clicks']}, CTR {pct(x['pre']['ctr'])}→{pct(x['post']['ctr'])}, lead {x['pre']['leads']}→{x['post']['leads']}）"
            ep = e.get("pages") or []
            L.append(f"| {e['date']} | {e.get('id')} | {e.get('class','')} | {' '.join(ep[:6])}{'…' if len(ep)>6 else ''} | {(e.get('summary') or '')[:80]} | {vs('14')} | {vs('28')} |")
        L.append("\n**worse の変更は差し戻し候補**（同じ変更を繰り返さない）。構成の変更（source=structure）は、下の表の「注意」も見る。\n")
        try:
            render_structure_changes(L, structure_change_rows(ledger))
        except Exception as e:  # noqa: BLE001 — ここが落ちても 8 節の残りと 9 節以降は出す
            L.append(f"構成の変更の表の生成に失敗: {e}\n")
        if auto_new:
            tally = {}
            for e in auto_new:
                for k in ("14", "28"):
                    v = ((e.get("measured") or {}).get(k) or {}).get("verdict", "未")
                    tally.setdefault(k, {})[v] = tally.setdefault(k, {}).get(v, 0) + 1
            L.append(f"新規ページの自動記帳（手動 PR で足したページ・register_new_pages.py）: {len(auto_new)} 件。"
                     + "／".join(f"{k}日後 " + "・".join(f"{v} {n}" for v, n in sorted(t.items())) for k, t in sorted(tally.items()))
                     + "。個別は 10 節。\n")
        not_shown, below = ramp_needs_care(ledger, pages)
        if not_shown:
            L.append("**要手当て（新規ページ・判定は not-shown で、直近28日も表示ゼロ）**: "
                     + "・".join(f"{p}（{c}日後）" for p, c, _, _ in sorted(not_shown))
                     + "\n差し戻しではなく育成＝関連コラム・ハブからの内部リンク、sitemap・ハブカードの登録漏れの点検（10 節の旗）。\n")
        if below:
            L.append("中央値未満（新規ページ・28日後。同じ言語の既存コラムの中央値と比較）: "
                     + "・".join(f"{p}（表示 {i}／中央値 {m:g}）" for p, _, i, m in sorted(below)) + "\n")
        cd = cooldown_pages(structure=structure)
        L.append("## 9. 今週触らないページ（14日以内に変更済み・効果測定中）\n")
        L.append("・".join(f"{p}（{dt}）" for p, (dt, _) in sorted(cd.items())) or "なし")
        if structure:
            L.extend(hub_top_freeze_lines(cd))
        L.append("")

    # 10. 新規ページの立ち上がり（最新.md には短く）
    try:
        new_rows, zero_rows = new_pages_data(latest, pages, landing)
        render_new_pages(L, new_rows, zero_rows, latest, *((15, 10) if for_latest else (40, 20)))
    except Exception as e:  # noqa: BLE001 — ここが落ちてもブリーフの他の節は出す
        L.append(f"## 10. 新規ページ（公開{NEW_DAYS}日以内）の立ち上がり\n\n生成に失敗: {e}\n")

    # S1〜S8. 構成レビュー（月1回・--structure のときだけ）
    if structure:
        try:
            import structure as st
            st.render_sections(L, st.data(ga_cur, ga_prev, pages, landing, health))
        except Exception as e:  # noqa: BLE001 — ここが落ちても上の節は出す
            L.append(f"\n# 構成レビュー用の節\n\n生成に失敗: {e}\n")
    return "\n".join(L) + "\n"


def brief_json(days=28, structure=False):
    gd = gsc_days()
    if not gd:
        return {}
    latest = d(gd[-1])
    cur = load_range("gsc", latest - datetime.timedelta(days=days - 1), latest)
    tot, pages, _, _ = agg_gsc(cur)
    ga = load_range("ga4", latest - datetime.timedelta(days=days - 1), latest)
    _, landing, *_ = agg_ga4(ga)
    try:
        new_rows, zero_rows = new_pages_data(latest, pages, landing)
    except Exception:  # noqa: BLE001
        new_rows, zero_rows = [], []
    out = {"generated": str(today()), "latest_gsc": str(latest), "days": days, "totals": tot,
           "pages": pages, "landing": landing,
           "cooldown": {k: v[0] for k, v in cooldown_pages(structure=structure).items()},
           "new_pages": new_rows, "zero_impression": zero_rows}
    try:
        out["structure_changes"] = structure_change_rows(
            [e for e in read_jsonl(LEDGER / "ledger" / "changes.jsonl")
             if safe_d(e.get("date")) and (today() - safe_d(e["date"])).days <= 60])
    except Exception:  # noqa: BLE001
        out["structure_changes"] = []
    if structure:
        try:
            import structure as st
            ga_prev = load_range("ga4", latest - datetime.timedelta(days=2 * days - 1), latest - datetime.timedelta(days=days))
            health = npg.latest_health()
            s = st.data(ga, ga_prev, pages, landing, health)
            s["matrix"] = {a: dict(b) for a, b in s["matrix"].items()}
            out["structure"] = s
        except Exception as e:  # noqa: BLE001
            out["structure"] = {"error": str(e)}
    return out


def main() -> int:
    structure = "--structure" in sys.argv
    text = render(structure=structure)
    if "--stdout" in sys.argv:
        print(text); return 0
    out = LEDGER / "weekly" / str(today())
    if structure:
        out = out / "structure"   # 同じ日の週次のブリーフを上書きしない
    out.mkdir(parents=True, exist_ok=True)
    (out / "brief.md").write_text(text, encoding="utf-8")
    (out / "brief.json").write_text(json.dumps(brief_json(structure=structure), ensure_ascii=False, default=list), encoding="utf-8")
    print(out / "brief.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
