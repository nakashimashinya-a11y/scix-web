#!/usr/bin/env python3
"""言葉と受ける頁の表（docs/keyword-page-map.md・機械版 keyword_page_map.json）と、週報 12f（market_side.py）の自己検査。
本物の台帳・Search Console・本番には触らない（リポジトリの手元のファイルと合成の行だけ）。

    python3 scripts/seo/selftest_keyword_map.py        # 0=全部通った
"""
from __future__ import annotations  # launchd の python3 は 3.9
import os
import pathlib
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = pathlib.Path(HERE).parent.parent
sys.path.insert(0, HERE)
import market_side as ms  # noqa: E402

FAILS = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILS.append(msg)
        print("NG ", msg)


def www_exists(path: str) -> bool:
    """www の頁が手元にあるか（cleanUrls・日本語の頁は <path>.html、/en は en/index.html、/zh は zh.html）。"""
    if path.endswith("*"):
        pre = path[:-1].lstrip("/")
        return any(REPO.glob(pre + "*.html")) or any(REPO.glob(pre + "*/index.html"))
    p = path.strip("/")
    if p == "":
        return (REPO / "index.html").exists()
    return any((REPO / x).exists() for x in (p + ".html", p + "/index.html"))


def test_map_file() -> None:
    k = ms.load_keyword_map()
    ids = [b["id"] for b in k["bundles"]]
    check(len(ids) == len(set(ids)), "束の id が重なっている")
    for b in k["bundles"]:
        for key in ("id", "group", "label", "script", "any", "need", "exclude", "main", "sub", "pending"):
            check(key in b, f"{b.get('id')}: 欄 {key} が無い")
        check(b["script"] in ("cjk", "ascii", "any"), f"{b['id']}: script が不正")
        check(len(b["main"]) >= 1, f"{b['id']}: 正の頁が無い")
        check(bool(b["any"]) and all(isinstance(g, list) and g for g in b["any"]), f"{b['id']}: 語の組が空")
        for g in b["any"]:
            check(all(t == t.lower() for t in g), f"{b['id']}: 語は小文字で書く（{g}）")
        for a in b["main"] + b["sub"] + b["pending"]:
            check(bool(re.match(r"^(www|dealroom):/", a)), f"{b['id']}: 住所の書き方が不正 {a}")
            if a.startswith("www:"):
                # 決め待ちの dealroom 以外（www の正・副）は実在する頁だけ
                if a in b["main"] or a in b["sub"]:
                    check(www_exists(a[4:]), f"{b['id']}: www の頁が手元に無い {a}")
        check(len(b["main"]) == 1, f"{b['id']}: 正は1束に1つ（{b['main']}）")
    # 表（人が読む版）と束がそろっているか
    doc = (REPO / "docs" / "keyword-page-map.md").read_text(encoding="utf-8")
    for b in k["bundles"]:
        # 管区の束は「（`area-tokyo` ほか9）」と1行にまとめて書く
        if b["id"].startswith("area-") and b["id"] != "area-tokyo":
            continue
        check(f"`{b['id']}`" in doc, f"docs/keyword-page-map.md に束 {b['id']} が書かれていない")
    # 公開リポジトリに置いてはいけないもの（案件の ID・金額）が表に混ざっていない
    check(not re.search(r"\b(HV|SHV|UR|GT)-\d+", doc), "表に案件の ID らしい文字列がある（O16-19）")


def test_classify() -> None:
    k = ms.load_keyword_map()
    cases = [
        ("系統用蓄電池 案件", "buy-list"),
        ("系統用蓄電池 売買 仲介", "sell-project"),
        ("系統用蓄電所 物件 売りたい", "sell-project"),
        ("蓄電池用地 買取", "land"),
        ("系統用蓄電池 買取", "sell-project"),
        ("系統用蓄電池 土地 売りたい", "sell-project"),
        ("蓄電池 ファンド", "fund"),
        ("蓄電池 投資", "invest"),
        ("蓄電池 投資 利回り", None),
        ("九州 系統用蓄電池 案件", "area-kyushu"),
        ("特別高圧 蓄電所 売却", "volt-ehv"),
        ("高圧 系統用蓄電池 案件", "volt-hv"),
        ("系統用蓄電池 権利 売買", "buy-types"),
        ("蓄電所 価格 相場", "price-howto"),
        ("蓄電所マーケット", "market-name"),
        ("サイエンスエックス株式会社", "brand"),
        ("japan bess for sale", "en-list"),
        ("how to sell a bess project", "en-howto"),
        ("japan battery storage market", "en-market"),
        ("jcスター 取得製品", None),
        ("需給調整市場 価格", None),
    ]
    for q, want in cases:
        b = ms.bundle_of(q, k["bundles"])
        got = b["id"] if b else None
        check(got == want, f"束の振り分け: 「{q}」→ {got}（期待 {want}）")


def test_stats() -> None:
    k = ms.load_keyword_map()
    old = {"www:/land": "/sourcing"}
    rows = [
        {"query": "系統用蓄電池 案件", "page": "/projects", "clicks": 1, "impressions": 10, "position": 2.0},
        {"query": "系統用蓄電池 案件", "page": "/", "clicks": 0, "impressions": 30, "position": 50.0},
        {"query": "系統用蓄電池 案件", "page": "https://dealroom.scix.co.jp/", "clicks": 0, "impressions": 5, "position": 9.0},
        {"query": "系統用蓄電池 物件", "page": "/projects-kyushu", "clicks": 0, "impressions": 4, "position": 6.0},
        {"query": "系統用蓄電池 売却", "page": "/land", "clicks": 0, "impressions": 8, "position": 12.0},
        {"query": "系統用蓄電池 売却", "page": "/sourcing", "clicks": 0, "impressions": 2, "position": 10.0},
        {"query": "謎の売却の語", "page": "/knowledge", "clicks": 0, "impressions": 7, "position": 40.0},
    ]
    res = ms.keyword_stats(rows, k, old)
    bl = res["bundles"]["buy-list"]
    check(bl["imp"] == 49, f"buy-list の表示 {bl['imp']}（期待 49）")
    check(bl["main"] == 10, f"buy-list の正の表示 {bl['main']}（期待 10）")
    check(bl["sub"] == 4, f"buy-list の副の表示 {bl['sub']}（期待 4）")
    check(bl["pending"] == 5, f"buy-list の決め待ちの表示 {bl['pending']}（期待 5）")
    check(bl["other"] == {"www:/": 30}, f"buy-list の割れ {bl['other']}")
    check(bl["split_q"] == 1 and bl["queries_n"] == 2, f"buy-list の割れた語 {bl['split_q']}／{bl['queries_n']}")
    check(abs(bl["position"] - (2 * 10 + 50 * 30 + 9 * 5 + 6 * 4) / 49) < 1e-9, "buy-list の順位は表示で重みを付けた平均")
    sp = res["bundles"]["sell-project"]
    check(sp["old"] == 8 and sp["main"] == 2, f"sell-project の旧住所 {sp['old']}・正 {sp['main']}")
    check(sp["split_q"] == 0, f"旧住所は割れの語に数えない {sp['split_q']}")
    check(res["unassigned"].get("謎の売却の語") == [7, 0], f"束に入らない買う・売るの語を数える {res['unassigned']}")


def test_address() -> None:
    cases = {
        "/": "www:/", "/projects": "www:/projects", "/projects/": "www:/projects",
        "https://www.scix.co.jp/en/projects?x=1": "www:/en/projects",
        "https://dealroom.scix.co.jp/catalog/area/kyushu": "dealroom:/catalog/area/kyushu",
        "https://dealroom.scix.co.jp": "dealroom:/",
        "https://scix.co.jp/bss": "www:/bss",
    }
    for src, want in cases.items():
        got = ms.address_of(src)
        check(got == want, f"住所の正規化 {src} → {got}（期待 {want}）")


def test_redirects_and_render() -> None:
    old = ms.redirect_sources(str(REPO))
    check(old.get("www:/land") == "/sourcing", "vercel.json の /land → /sourcing を旧住所として読む")
    check(all(not k.startswith("www:/%") for k in old), "百分率符号の入った住所は旧住所に入れない")
    L: list = []
    cur = [{"query_page": [
        {"query": "系統用蓄電池 案件", "page": "/projects", "clicks": 1, "impressions": 10, "position": 2.0, "ctr": 0.1},
        {"query": "系統用蓄電池 案件", "page": "/investors", "clicks": 0, "impressions": 3, "position": 60.0, "ctr": 0.0},
        {"query": "系統用蓄電池 売却", "page": "/land", "clicks": 0, "impressions": 4, "position": 12.0, "ctr": 0.0},
        {"query": "蓄電所 売却 マッチング", "page": "/knowledge", "clicks": 0, "impressions": 2, "position": 30.0, "ctr": 0.0},
    ]}]
    q_prev = {"系統用蓄電池 案件": {"impressions": 7, "clicks": 0, "position": 5.0, "pages": {"/projects": 7}}}
    ms.render_keyword_map(L, cur, q_prev, str(REPO), lambda x: f"{x:.1f}", lambda x: f"{x * 100:.0f}%")
    out = "\n".join(L)
    check("12f" in out and "売り案件の一覧・物件" in out, "12f の見出しと束の行が出る")
    check("/investors（3）" in out, "割れの頁が出る")
    check("表示0の束" in out, "表示0の束の1行が出る")
    check("表に入らない買う・売るの語" in out, "束に入らない語の行が出る")
    # 前の28日・今の28日がともに無いときも落ちない
    L2: list = []
    ms.render_keyword_map(L2, [{"query_page": []}], {}, str(REPO), lambda x: f"{x:.1f}", lambda x: f"{x * 100:.0f}%")
    check(any("表示0の束" in x for x in L2), "行が1つも無い週も落ちない")


def main() -> int:
    for t in (test_map_file, test_classify, test_stats, test_address, test_redirects_and_render):
        t()
    print("OK 全部通った" if not FAILS else f"NG {len(FAILS)} 件")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
