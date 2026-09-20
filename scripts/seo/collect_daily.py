#!/usr/bin/env python3
"""毎日の収集: Search Console・GA4・本番HTMLの健診を Drive の台帳へ蓄積する。変更はしない。

    python3 scripts/seo/collect_daily.py               # 直近10日を取り直す（欠けと未確定を埋める）
    python3 scripts/seo/collect_daily.py --days 90     # 初回の積み上げ
    python3 scripts/seo/collect_daily.py --no-health   # 健診（本番へのアクセス）を飛ばす

データの遅れ: GSC は2〜3日、GA4 は1〜2日。若い日付は毎回取り直して上書きする。
収集のあと、origin/main に足された新規ページを変更台帳へ自動で記帳し（register_new_pages.py）、月1回の構成レビューの
提案がマージされていればそれも記帳し（register_structure_merges.py）、期限が来た変更を計測する。
GA4 のトークンが無ければ GA4 だけ飛ばす（他は止めない）。
"""
import argparse
import datetime
import html.parser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BASE, GA4_TOKEN, LEDGER, SC_TOKEN, UA, Google, d, daterange,  # noqa: E402
                    ga4_report, gsc_query, jdump, jload, log, path_of, today)

GSC_LAG = 2          # 今日-2 までを取る
GSC_REFRESH = 5      # この日数より若い日は毎回取り直す
GA4_LAG = 1
GA4_REFRESH = 3


# ---------------------------------------------------------------- GSC

def collect_gsc(days: int) -> int:
    g = Google(SC_TOKEN)
    end = today() - datetime.timedelta(days=GSC_LAG)
    start = end - datetime.timedelta(days=days - 1)
    n = 0
    for day in daterange(start, end):
        out = LEDGER / "gsc" / f"{day}.json"
        age = (today() - day).days
        if out.exists() and age > GSC_REFRESH:
            continue
        tot = gsc_query(g, day, day, ["date"])
        if not tot:
            log(f"GSC {day}: データ無し（まだ届いていない）")
            continue
        t = tot[0]
        rec = {
            "date": str(day), "fetched": str(today()),
            "totals": {"clicks": t["clicks"], "impressions": t["impressions"], "ctr": t["ctr"], "position": t["position"]},
            "pages": [{"page": path_of(r["keys"][0]), "clicks": r["clicks"], "impressions": r["impressions"],
                       "ctr": r["ctr"], "position": r["position"]} for r in gsc_query(g, day, day, ["page"])],
            "query_page": [{"query": r["keys"][0], "page": path_of(r["keys"][1]), "clicks": r["clicks"],
                            "impressions": r["impressions"], "ctr": r["ctr"], "position": r["position"]}
                           for r in gsc_query(g, day, day, ["query", "page"])],
            "device": [{"device": r["keys"][0], "clicks": r["clicks"], "impressions": r["impressions"]}
                       for r in gsc_query(g, day, day, ["device"])],
            "country": [{"country": r["keys"][0], "clicks": r["clicks"], "impressions": r["impressions"]}
                        for r in gsc_query(g, day, day, ["country"], row_limit=25)],
        }
        jdump(out, rec)
        n += 1
        log(f"GSC {day}: clicks {t['clicks']} impr {t['impressions']} 検索語×ページ {len(rec['query_page'])}行")
    return n


# ---------------------------------------------------------------- GA4

def _try(fn, label):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — 登録されていないカスタムディメンションは飛ばす
        log(f"GA4 {label}: 取れない（{str(e)[:120]}）")
        return None


def collect_ga4(days: int) -> int:
    if not GA4_TOKEN.exists():
        log(f"GA4: トークンが無いので飛ばす（python3 scripts/seo/ga4_auth.py で取得）: {GA4_TOKEN}")
        return 0
    g = Google(GA4_TOKEN)
    end = today() - datetime.timedelta(days=GA4_LAG)
    start = end - datetime.timedelta(days=days - 1)
    lead = "keyEvents:generate_lead"
    n = 0
    for day in daterange(start, end):
        out = LEDGER / "ga4" / f"{day}.json"
        age = (today() - day).days
        if out.exists() and age > GA4_REFRESH:
            continue
        s = e = day
        totals = ga4_report(g, s, e, ["date"], ["sessions", "totalUsers", "newUsers", "engagedSessions",
                                              "averageSessionDuration", lead])
        if not totals:
            log(f"GA4 {day}: データ無し")
            continue
        internal = {"filter": {"fieldName": "pageReferrer", "stringFilter": {"matchType": "CONTAINS", "value": "scix.co.jp"}}}
        rec = {
            "date": str(day), "fetched": str(today()),
            "totals": {k: v for k, v in totals[0].items() if k != "date"},
            "landing": ga4_report(g, s, e, ["landingPage"], ["sessions", "engagedSessions", "newUsers",
                                                                "averageSessionDuration", lead]),
            "pages": ga4_report(g, s, e, ["pagePath"], ["screenPageViews", "sessions", "userEngagementDuration"]),
            "transitions": [{"from": path_of(r["pageReferrer"]), "to": r["pagePath"], "views": r["screenPageViews"]}
                            for r in (ga4_report(g, s, e, ["pageReferrer", "pagePath"], ["screenPageViews"],
                                                 dim_filter=internal) or [])],
            "channels": ga4_report(g, s, e, ["sessionDefaultChannelGroup"], ["sessions", lead]),
            "events": ga4_report(g, s, e, ["eventName"], ["eventCount"]),
            "lead_intent": _try(lambda: ga4_report(g, s, e, ["customEvent:intent", "landingPage"], [lead]), "intent"),
            # GA4 に登録済みのカスタムディメンションは intent / nav_group / form_type だけ（2026-09-19 実測）。
            # placement（更新メール登録の置き場）と search_term（ナレッジ検索の語）は未登録＝GA4 管理画面で
            # イベントパラメータをカスタムディメンションに登録すれば下の2行を戻せる。
            "lead_type": _try(lambda: ga4_report(g, s, e, ["customEvent:form_type"], [lead]), "form_type"),
            "nav_click": _try(lambda: ga4_report(g, s, e, ["customEvent:nav_group"], ["eventCount"],
                                                 dim_filter={"filter": {"fieldName": "eventName", "stringFilter": {"value": "nav_click"}}}), "nav_group"),
            "newsletter": None,
            "knowledge_search": None,
        }
        # 空の lead_intent 行は落とす（着地ごとに0が並ぶ）
        if rec["lead_intent"]:
            rec["lead_intent"] = [r for r in rec["lead_intent"] if r.get(lead)]
        jdump(out, rec)
        n += 1
        log(f"GA4 {day}: sessions {rec['totals'].get('sessions')} leads {rec['totals'].get(lead)}")
    return n


# ---------------------------------------------------------------- 健診（本番HTML）

class Meta(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""; self._in_title = False
        self.desc = None; self.canonical = None; self.h1 = 0; self.og_image = False
        self.hreflang = 0; self.jsonld = []; self._in_ld = False; self._ld = ""
        self.links = []; self.robots = None; self.text_len = 0; self._skip = 0
        self.header_js = False; self.inline_header = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name == "description":
                self.desc = a.get("content", "")
            elif name == "og:image":
                self.og_image = True
            elif name == "robots":
                self.robots = a.get("content")
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical":
                self.canonical = a.get("href")
            elif rel == "alternate" and a.get("hreflang"):
                self.hreflang += 1
        elif tag == "h1":
            self.h1 += 1
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json":
                self._in_ld = True; self._ld = ""
            elif a.get("src") == "/header.js":
                self.header_js = True
            self._skip += 1
        elif tag == "style":
            self._skip += 1
        elif tag == "header" and "scix-header" in (a.get("class") or ""):
            self.inline_header = True
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if self._in_ld:
                try:
                    json.loads(self._ld); self.jsonld.append(True)
                except json.JSONDecodeError:
                    self.jsonld.append(False)
                self._in_ld = False
            self._skip = max(0, self._skip - 1)
        elif tag == "style":
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_ld:
            self._ld += data
        elif not self._skip:
            self.text_len += len(data.strip())


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, res.geturl(), res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:  # noqa: BLE001
        return 0, url, str(e)


def collect_health(sleep: float = 0.5) -> dict:
    st, _, xml = fetch(BASE + "/sitemap.xml")
    if st != 200:
        log(f"健診: sitemap.xml が {st}")
        return {}
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    pages, titles = [], {}
    for url in locs:
        st, final, body = fetch(url)
        rec = {"url": path_of(url), "status": st}
        if st == 200 and body:
            m = Meta(); m.feed(body)
            rec.update({
                "title": m.title.strip(), "title_len": len(m.title.strip()),
                "desc_len": len(m.desc or "") if m.desc is not None else None,
                "canonical": path_of(m.canonical) if m.canonical else None,
                "canonical_ok": bool(m.canonical) and path_of(m.canonical) == path_of(url),
                "h1": m.h1, "og_image": m.og_image, "hreflang": m.hreflang,
                "jsonld": len(m.jsonld), "jsonld_bad": m.jsonld.count(False),
                "header_js": m.header_js, "inline_header": m.inline_header,
                "robots": m.robots, "text_len": m.text_len,
                "internal_links": sorted({path_of(h) for h in m.links if h.startswith("/") and not h.startswith("//")}),
            })
            titles.setdefault(rec["title"], []).append(rec["url"])
        elif final != url:
            rec["redirect_to"] = final
        pages.append(rec)
        time.sleep(sleep)
    issues = []
    for p in pages:
        u = p["url"]
        if p["status"] != 200:
            issues.append(f"{u}: HTTP {p['status']}")
            continue
        if not p["title"]:
            issues.append(f"{u}: title が無い")
        if p["desc_len"] is None:
            issues.append(f"{u}: description が無い")
        elif p["desc_len"] < 50:
            issues.append(f"{u}: description が短い（{p['desc_len']}字）")
        if u.startswith("/en") and p["title_len"] > 70:
            issues.append(f"{u}: EN title が70字超（{p['title_len']}）")
        if u.startswith("/en") and (p["desc_len"] or 0) > 155:
            issues.append(f"{u}: EN description が155字超（{p['desc_len']}）")
        if not p["canonical_ok"]:
            issues.append(f"{u}: canonical が自分を指していない（{p['canonical']}）")
        if p["h1"] != 1:
            issues.append(f"{u}: h1 が {p['h1']} 個")
        if p["jsonld_bad"]:
            issues.append(f"{u}: JSON-LD が壊れている（{p['jsonld_bad']}）")
        if p["inline_header"]:
            issues.append(f"{u}: ヘッダーが直書き（header.js に統一）")
        if p["robots"] and "noindex" in p["robots"]:
            issues.append(f"{u}: noindex（sitemap に載せているのに）")
    for t, us in titles.items():
        if len(us) > 1:
            issues.append(f"title 重複「{t[:40]}」: {' '.join(us)}")
    # 内部リンク切れ（sitemap に無く、GETしても200でないもの）
    known = {p["url"] for p in pages}
    targets = {}
    for p in pages:
        for l in p.get("internal_links", []):
            if l not in known:
                targets.setdefault(l, []).append(p["url"])
    broken = []
    for l, srcs in sorted(targets.items()):
        if l.startswith(("/img/", "/files/")):
            continue
        st, final, _ = fetch(BASE + l)
        time.sleep(sleep)
        if st != 200:
            broken.append({"link": l, "status": st, "from": srcs[:5]})
            issues.append(f"内部リンク {l} が HTTP {st}（{len(srcs)}ページから）")
    # 被リンク数（サイト内でそのページを指すページ数）
    inbound = {}
    for p in pages:
        for l in set(p.get("internal_links", [])):
            inbound[l] = inbound.get(l, 0) + 1
    rec = {"date": str(today()), "checked_at": time.strftime("%F %T"), "n": len(pages),
           "issues": issues, "broken_links": broken, "inbound": inbound, "pages": pages}
    jdump(LEDGER / "health" / f"{today()}.json", rec)
    log(f"健診: {len(pages)}ページ・問題 {len(issues)}件")
    return rec


# ---------------------------------------------------------------- 最新.md（Web版Claude・スマホ用の写し）

def write_latest() -> None:
    import build_brief  # 遅延: 台帳が無い初回でも collect は動くように
    try:
        text = build_brief.render(days=28, for_latest=True)
    except Exception as e:  # noqa: BLE001
        text = f"# scix.co.jp 最新（生成失敗: {e}）\n"
    p = LEDGER / "最新.md"
    p.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--no-gsc", action="store_true")
    ap.add_argument("--no-ga4", action="store_true")
    ap.add_argument("--no-health", action="store_true")
    ap.add_argument("--no-register", action="store_true", help="新規ページの自動記帳を飛ばす")
    ap.add_argument("--no-measure", action="store_true")
    a = ap.parse_args()
    rc = 0
    if not a.no_gsc:
        try:
            collect_gsc(a.days)
        except Exception as e:  # noqa: BLE001
            log(f"GSC 収集で失敗: {e}"); rc = 1
    if not a.no_ga4:
        try:
            collect_ga4(a.days)
        except Exception as e:  # noqa: BLE001
            log(f"GA4 収集で失敗: {e}"); rc = 1
    if not a.no_health:
        try:
            collect_health()
        except Exception as e:  # noqa: BLE001
            log(f"健診で失敗: {e}"); rc = 1
    if not a.no_register:
        # 手動 PR で足したページを変更台帳へ（効果測定の前に。measure が同じ朝に拾えるように）
        try:
            import register_new_pages
            for e in register_new_pages.run():
                log(f"新規ページを記帳: {e['id']} {' '.join(e['pages'])}")
        except Exception as e:  # noqa: BLE001
            log(f"新規ページの記帳で失敗: {e}"); rc = 1
    if not a.no_register:
        # 月1回の構成レビューの提案（PR）がマージされていたら変更台帳へ（提案が無ければ何もしない）
        try:
            import register_structure_merges
            for e in register_structure_merges.run():
                log(f"構成の提案がマージされた → 変更台帳へ: {e['id']} {' '.join(e['pages'])}")
        except Exception as e:  # noqa: BLE001
            log(f"構成の提案の記帳で失敗: {e}"); rc = 1
    if not a.no_measure:
        try:
            import measure_changes
            new = measure_changes.run()
            for m in new:
                ns = [p for p, x in (m.get("by_page") or {}).items() if x.get("verdict") == "not-shown"]
                log(f"計測: {m['id']} {m['check']}日後 → {m['verdict']}" + (f"（表示ゼロ: {' '.join(ns)}）" if ns else ""))
        except Exception as e:  # noqa: BLE001
            log(f"効果測定で失敗: {e}"); rc = 1
    try:
        write_latest()
    except Exception as e:  # noqa: BLE001
        log(f"最新.md の生成で失敗: {e}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
