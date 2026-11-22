#!/usr/bin/env python3
"""マーケット側（dealroom.scix.co.jp）の検索を、週のブリーフに足す部品。

会社のサイト（www.scix.co.jp）とは別のホストなので、これまでのブリーフ（ページ別・検索語別）には混ざって見えていた。
ここで見るのは次の3つ（2026-11-22 中島「Seo 対策も徹底してやって」。マーケットの頁は 862 頁が 200 で返るのに、
検索からのクリックが 90 日で 2・URL 検査では試した 10 本すべて「Google に認識されていません」だった＝見つける道が無い）。

  1. マーケット側の検索の動き: www と dealroom に分けた表示・クリック、dealroom の頁の種類（案件・入口・トップと一覧）別、検索語の上位。
  2. 語の定点25語（売買10・解説10・英語5）: 28日の表示・クリック・順位と前28日の表示。語ごとの検索数は取れないので、当社の表示で見る。
  3. URL 検査の定点20本（案件5・入口10・トップと一覧5）: 索引に入ったかを毎週同じ頁で見る（Search Console の URL 検査 API・読み取り）。

案件の住所は公開リポジトリのコードに書かない（O16-19）＝案件の頁は projects.json（公開セーフ）から実行時に選ぶ。
数字は Drive のブリーフにだけ出る（公開リポジトリ・コミット文・PR には写さない）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import json
import os

MARKET = "https://dealroom.scix.co.jp"
AREAS = ["hokkaido", "tohoku", "tokyo", "chubu", "hokuriku", "kansai", "chugoku", "shikoku", "kyushu"]

# 語の定点25語。語を空白で分け、全部を含む検索語（大文字小文字を問わない）を合算する。
FIXED_QUERIES = {
    "売買": ["系統用蓄電池 売買", "蓄電所 売却", "系統用蓄電池 案件", "特別高圧 蓄電所 売却", "九州 系統用蓄電池 案件",
             "系統用蓄電池 権利 売買", "蓄電所 売買", "系統用蓄電池 売却", "高圧 系統用蓄電池 案件", "蓄電所 マーケット"],
    "解説": ["jcスター", "需給調整市場 価格", "トーリング", "容量市場 約定価格", "系統用蓄電池 騒音", "低圧 系統用蓄電池",
             "蓄電所 トラブル", "系統用蓄電池 建設費", "長期脱炭素電源オークション", "需給調整市場 取引実績"],
    "英語": ["revenue stacking", "japan bess for sale", "japan battery storage market", "jc-star", "japan bess development rights"],
}


def host_of(page: str) -> str:
    return "dealroom" if page.startswith(MARKET) else "www"


def kind_of(page: str) -> str:
    """dealroom の頁の種類。案件の頁（/catalog/<番号>）・入口（エリア・県・電圧・取得の形）・トップと一覧・その他。"""
    p = page[len(MARKET):] if page.startswith(MARKET) else page
    p = p.split("?")[0].split("#")[0].rstrip("/") or "/"
    if p.startswith("/en"):
        p = p[3:] or "/"
    parts = [x for x in p.split("/") if x]
    if len(parts) == 2 and parts[0] == "catalog" and parts[1] not in ("area", "pref", "voltage", "type"):
        return "案件"
    if len(parts) >= 3 and parts[0] == "catalog" and parts[1] in ("area", "pref", "voltage", "type"):
        return "入口"
    if p in ("/", "/catalog", "/buy", "/sellers", "/wanted", "/how", "/needs"):
        return "トップと一覧"
    return "その他"


def deal_urls(repo: str, n: int = 5) -> list:
    """公開の案件の頁（projects.json の公開セーフな id から実行時に選ぶ。id はコードに書かない）。"""
    try:
        ps = json.load(open(os.path.join(repo, "projects.json"), encoding="utf-8"))["projects"]
    except (OSError, ValueError, KeyError):
        return []
    ids = sorted(str(x["id"]) for x in ps if x.get("id"))
    step = max(1, len(ids) // n)
    return [f"{MARKET}/catalog/{i}" for i in ids[::step][:n]]


def inspect_targets(repo: str) -> list:
    """URL 検査の定点20本＝案件5・入口10（エリア9＋特別高圧）・トップと一覧5。"""
    urls = deal_urls(repo, 5)
    urls += [f"{MARKET}/catalog/area/{a}" for a in AREAS] + [f"{MARKET}/catalog/voltage/extra-high-voltage"]
    urls += [f"{MARKET}/", f"{MARKET}/en", f"{MARKET}/catalog", f"{MARKET}/wanted", f"{MARKET}/en/catalog"]
    return urls


def collect_inspect(g, repo: str, site: str, out_dir, day: datetime.date, log=print) -> int:
    """定点20本を URL 検査 API で見て、台帳の inspect/<日付>.json に書く。1本ずつ失敗しても止めない。"""
    api = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    rows = []
    for u in inspect_targets(repo):
        try:
            r = g.call(api, {"inspectionUrl": u, "siteUrl": site, "languageCode": "ja"})
            x = (r.get("inspectionResult") or {}).get("indexStatusResult") or {}
            rows.append({"url": u, "verdict": x.get("verdict"), "state": x.get("coverageState"), "crawled": x.get("lastCrawlTime"),
                         "canonical": x.get("googleCanonical"), "robots": x.get("robotsTxtState"), "fetch": x.get("pageFetchState")})
        except Exception as e:  # noqa: BLE001 — 1本の失敗で止めない
            rows.append({"url": u, "error": str(e)[:160]})
            log(f"URL 検査 {u}: {str(e)[:120]}")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{day}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": str(day), "rows": rows}, f, ensure_ascii=False, indent=1)
    return len(rows)


def _split(tokens_q: str) -> list:
    return [t for t in tokens_q.lower().split() if t]


def fixed_rows(q_cur: dict, q_prev: dict) -> list:
    """[(組, 語, 表示, クリック, 順位, 前の表示)]。q_* は build_brief.agg_gsc の検索語別（語 → {impressions, clicks, position}）。"""
    def agg(qd, toks):
        imp = clk = 0
        pos_w = 0.0
        for k, v in qd.items():
            kl = k.lower()
            if all(t in kl for t in toks):
                imp += v["impressions"]; clk += v["clicks"]
                pos_w += (v["position"] or 0) * v["impressions"]
        return imp, clk, (pos_w / imp if imp else None)
    out = []
    for grp, words in FIXED_QUERIES.items():
        for w in words:
            toks = _split(w)
            imp, clk, pos = agg(q_cur, toks)
            pimp = agg(q_prev, toks)[0] if q_prev else None
            out.append((grp, w, imp, clk, pos, pimp))
    return out


def render(L: list, cur: list, w7: list, w7p: list, q_cur: dict, q_prev: dict, ledger, repo: str, fnum, pct) -> None:
    """ブリーフに「マーケット側の検索」の節を足す。cur・w7・w7p は日ごとの GSC の記録、q_* は検索語別の集計。"""
    L.append("## 12. マーケット側の検索（dealroom.scix.co.jp）\n")
    L.append("会社のサイト（www）とマーケット（dealroom）を分けて見る。マーケットの頁は、索引に入っていない間は表示がほとんど出ない＝"
             "まず 12e の「URL 検査の定点」で索引に入ったかを見る。\n")

    def host_sum(recs):
        tot = {"www": [0, 0], "dealroom": [0, 0]}
        kinds = {}
        for r in recs:
            for p in r["pages"]:
                h = host_of(p["page"])
                tot[h][0] += p["clicks"]; tot[h][1] += p["impressions"]
                if h == "dealroom":
                    k = kinds.setdefault(kind_of(p["page"]), [0, 0])
                    k[0] += p["clicks"]; k[1] += p["impressions"]
        return tot, kinds
    t28, k28 = host_sum(cur)
    t7, _ = host_sum(w7)
    t7p, _ = host_sum(w7p)
    L.append("### 12a. ホスト別の表示・クリック\n")
    L.append("| ホスト | 直近7日 表示／クリック | 前7日 表示／クリック | 直近28日 表示／クリック |\n|---|---|---|---|")
    for h in ("www", "dealroom"):
        L.append(f"| {h} | {t7[h][1]}／{t7[h][0]} | {t7p[h][1]}／{t7p[h][0]} | {t28[h][1]}／{t28[h][0]} |")
    L.append("\n### 12b. dealroom の頁の種類別（28日）\n")
    L.append("| 種類 | 表示 | クリック |\n|---|---|---|")
    for k in ("案件", "入口", "トップと一覧", "その他"):
        v = k28.get(k, [0, 0])
        L.append(f"| {k} | {v[1]} | {v[0]} |")
    # dealroom の頁に着地した検索語の上位
    byq = {}
    for r in cur:
        for x in r["query_page"]:
            if host_of(x["page"]) == "dealroom":
                a = byq.setdefault(x["query"], [0, 0])
                a[0] += x["clicks"]; a[1] += x["impressions"]
    L.append("\n### 12c. dealroom の頁に着地した検索語（28日・上位10）\n")
    top = sorted(byq.items(), key=lambda kv: -kv[1][1])[:10]
    L.append("・".join(f"{k}（{v[1]}表示／{v[0]}クリック）" for k, v in top) if top else "なし（表示が出ていない）")
    L.append("\n### 12d. 語の定点25語（28日・当社の表示。語ごとの検索数は取れない）\n")
    L.append("| 組 | 語 | 表示 | クリック | 順位 | 前28日の表示 |\n|---|---|---|---|---|---|")
    for grp, w, imp, clk, pos, pimp in fixed_rows(q_cur, q_prev):
        L.append(f"| {grp} | {w} | {imp} | {clk} | {fnum(pos) if pos else '—'} | {pimp if pimp is not None else '—'} |")
    L.append("\n### 12e. URL 検査の定点20本（索引に入ったか・毎週同じ頁）\n")
    files = sorted((ledger / "inspect_market").glob("????-??-??.json")) if (ledger / "inspect_market").exists() else []
    if not files:
        L.append("まだ検査していない（`collect_daily.py --inspect` か、週に1回の自動の回で台帳 inspect_market/ に溜まる）。")
        return
    j = json.load(open(files[-1], encoding="utf-8"))
    rows = j.get("rows", [])
    ok = [r for r in rows if r.get("verdict") == "PASS"]
    L.append(f"検査日 {j.get('date')}・索引に入っている（PASS）{len(ok)}／{len(rows)}本\n")
    L.append("| 頁 | 状態 | 最後の取得 |\n|---|---|---|")
    for r in rows:
        u = r["url"][len(MARKET):] or "/"
        if r.get("error"):
            L.append(f"| {u} | 検査できない（{r['error'][:40]}） | — |")
        else:
            L.append(f"| {u} | {r.get('state') or r.get('verdict') or '—'} | {(r.get('crawled') or '—')[:10]} |")
