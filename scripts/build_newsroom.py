#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""報道資料室（/newsroom・/en/newsroom）を、プレスリリースの一覧のデータ scripts/data/newsroom/releases.json から作る。

頁の中身: プレスリリースの一覧（新しい順・日付・題・自社の頁へのリンク・要点・配信後の ValuePress! の掲載頁）、
会社概要と代表の略歴（/company の字のまま）、使える素材（ロゴ・写真・図表の使い方＝/press・公開の CSV）、
取材・問い合わせの窓口（/press と同じ）、蓄電所マーケットの案内。
構造化データ: CollectionPage（一覧）＋BreadcrumbList。リリースのうち、本文が scix.co.jp の頁に在る物だけを NewsArticle にする
（蓄電所マーケットなど外の頁の物は ListItem の住所と題だけ）。
題と要点は行き先の頁の字のまま書き、生成器が頁の本文と一字ずつ突き合わせる（作った数字・言い換えを入れない＝O16-8）。
書かない物: 価格・手数料・利回り・実績（成約件数・取扱高・取引先名）・先行買取（O16-7・O16-8）。

    python3 scripts/build_newsroom.py            # 頁2本と sitemap の2行（lastmod）を書く
    python3 scripts/build_newsroom.py --check    # 書かずに、頁・sitemap がデータとずれていないか・決まりに触れていないかを見る（あれば 1）

    # 次のリリースを足す（自社の頁＝題と要点は頁から取る。英語の頁は頁の hreflang から）
    python3 scripts/build_newsroom.py add --date 2026-11-25 --page /column-xxx
    # 自社の頁の無い物（蓄電所マーケットの話など）は、題と要点を公開の頁の字のまま渡す
    python3 scripts/build_newsroom.py add --date 2026-11-27 --kind market --url https://dealroom.scix.co.jp/ \\
        --ja-title "…" --ja-point "…" --en-url https://dealroom.scix.co.jp/en --en-title "…" --en-point "…"
    # 配信の後に ValuePress! の掲載頁の住所を足す
    python3 scripts/build_newsroom.py set-vp --id 2026-11-24-report-2026-11 --url https://www.value-press.com/pressrelease/NNNNNN

add と set-vp は、データの modified を今日（日本時間）にして、頁と sitemap の lastmod を書き直す。
2026-11-23 中島「無意味なページよりも、受注・売上になるページをどんどん出して」（ValuePress! の配信が続くので、記者が来る頁を1か所に）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import argparse
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_ga_tag as ga_tag  # noqa: E402  GA の区画（全頁で同じ形）

DATA = os.path.join(ROOT, "scripts", "data", "newsroom", "releases.json")
PARTS = os.path.join(ROOT, "scripts", "data", "guides", "_parts")   # 下の帯は柱の頁と同じ部品
SITEMAP = os.path.join(ROOT, "sitemap.xml")
BASE = "https://www.scix.co.jp"
MARKET_HOSTS = ("https://dealroom.scix.co.jp",)
VP_PREFIX = "https://www.value-press.com/"
ORG_ID = BASE + "/#organization"
YT_CHANNEL = "https://www.youtube.com/channel/UCH9WUVm8V2zsMc8s9WS2OYg"   # 会社の YouTube チャンネル（解説動画。Organization の sameAs と窓口の一行）
SITE_ID = BASE + "/#website"
PATHS = {"ja": "/newsroom", "en": "/en/newsroom"}
FILES = {"ja": "newsroom.html", "en": "en/newsroom.html"}
KINDS = {"report": ("市場ノート", "Market Notes"), "column": ("コラム", "Column"),
         "market": ("蓄電所マーケット", "Chikudensho Market"), "news": ("お知らせ", "News")}
# 素材に書かない語（価格・手数料・利回り・実績・先行買取・比べの語・投資をすすめる語）。市場の公表価格（落札価格など）は書いてよい
NG = re.compile(r"手数料|利回り|IRR|成約|取扱高|取扱件数|先行買取|仕入|販売価格|売値|日本最大|業界初|No\.?\s?1|唯一|もうか|儲か|お得|確実|"
                r"commission|brokerage fee|yield|track record|largest in Japan|first in the industry|guaranteed", re.I)

FONT = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&display=swap"

L = {
    "ja": dict(
        html_lang="ja", hreflang="ja", og_locale="ja_JP", og_img="/img/ogp-m.png", home=("ホーム", "/"),
        title="報道資料室｜プレスリリース・会社概要・取材窓口｜サイエンスエックス",
        desc=("サイエンスエックスの報道資料室。プレスリリースの一覧（蓄電所の市場ノートなど）、会社概要と代表の略歴、"
              "ロゴ・写真と図表・データ（CSV）の使い方、取材・問い合わせの窓口を1か所にまとめています。"),
        h1="報道資料室", label="記者・編集者の方へ",
        lead="サイエンスエックスのプレスリリース、会社概要、図表とデータの使い方、取材の窓口を、この頁にまとめました。",
        toc=[("releases", "プレスリリース"), ("company", "会社概要"), ("profile", "代表の略歴"), ("assets", "使える素材"),
             ("contact", "取材・問い合わせの窓口"), ("market", "蓄電所マーケット")],
        rel_h="プレスリリース", rel_lead="新しいものから並べています。本文と図表は、それぞれの頁にあります。",
        read="頁を読む →", vp="ValuePress! の配信を見る ↗", ja_only="", list_name="サイエンスエックスのプレスリリース",
        co_h="会社概要", co_more=("会社案内を見る →", "/company"),
        co_rows=[
            ("商号", "サイエンスエックス株式会社（Science X Inc.）"),
            ("所在地", "〒103-0016 東京都中央区日本橋小網町8-2 BIZMARKS日本橋茅場町"),
            ("代表者", "代表取締役 中島 晋也（工学博士）"),
            ("設立", "2021年"),
            ("資本金", "900万円"),
            ("事業内容", "系統用蓄電池の見極め・組成・運用設計<br>確定案件の権利譲渡／実物資産投資の組成支援"),
            ("役員", "代表取締役 中島 晋也（工学博士）<br>取締役 CTO 大井 俊夫（元 昭和電工 取締役）<br>取締役 CFO 唐澤 佳長（元 帝人 代表取締役副社長）"),
            ("法人番号", '6010001215846（<a href="https://info.gbiz.go.jp/hojin/ichiran?hojinBango=6010001215846" rel="noopener">国のgBizINFOで確認する</a>）'),
            ("連絡先", 'TEL <a href="tel:0366913484">03-6691-3484</a>　MAIL <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>'),
        ],
        co_lead="系統用蓄電池に特化し、案件の売買を行う会社です。特定のメーカー・EPCと資本関係はありません。",
        pf_h="代表の略歴", pf_name="中島 晋也（工学博士）　代表取締役", pf_more=("略歴の全文と研究業績を見る →", "/company#profile"),
        pf_rows=[
            ("1990年", "進化製薬株式会社 入社（研究員／医薬品の品質管理・薬事申請・製剤研究）"),
            ("1993年", "西川計測株式会社 入社（横河電機／ヒューレット・パッカードの代理店として計測器・分析装置・プラント制御システムを扱う専門商社。化学分析システム・LIMSの開発、GC/MS分析ソリューションの設計に27年間従事）"),
            ("2015年", "熊本県立大学大学院 修了、博士（工学）取得（環境・エネルギー工学）"),
            ("2021年", "東京家政大学 講師（化学）就任（5年間）"),
            ("2021年", "サイエンスエックス株式会社 設立、代表取締役 就任（現任）。博士研究を応用したバイオガスシステムを国内3箇所に導入"),
        ],
        as_h="使える素材", as_lead="記事の数値・図表は、出典を明記すれば許諾の連絡なしにお使いいただけます。出典の書き方・使える範囲・図の埋め込みコードは、引用・転載ガイドにまとめています。",
        as_press=("引用・転載ガイド（出典の書き方・図表・埋め込みコード）を見る →", "/press"),
        as_yt=("解説動画（YouTube チャンネル）を見る ↗", YT_CHANNEL),
        as_logo_h="ロゴと写真",
        as_logo=[("/img/logo-white.png", "ロゴ（白・透過 PNG。紺や濃い背景でお使いください）"),
                 ("/img/apple-touch-icon.png", "正方形のマーク（PNG）"),
                 ("/img/nakashima.png", "代表 中島 晋也の写真（PNG）")],
        as_data_h="データ（CSV）",
        as_data=[("蓄電所の市場データ", "/report/data", [
                    ("/report/data/jepx-spot-monthly.csv", "卸電気（JEPX）のエリア別の月平均と値差（月×エリア・全指標）"),
                    ("/report/data/capacity-main-auction.csv", "容量市場（OCCTO）メインオークションのエリアプライス"),
                    ("/report/data/long-term-decarbonization-auction.csv", "長期脱炭素電源オークションの約定容量")]),
                 ("系統用蓄電池の売り案件 市場データ", "/market-data", [
                    ("/files/market-data/market-data-summary.csv", "集計（管内別・電圧区分・連系の見込みなど）"),
                    ("/files/market-data/market-data-weekly.csv", "販売中の件数と規模の、週ごとの推移")])],
        ct_h="取材・問い合わせの窓口", ct_lead="次のことに応じます。",
        ct_items=["記事の元データの説明、図表の元の数表、必要な形（表のみ・エリア別の抜粋など）への整形",
                  "系統用蓄電池の制度・市場・売買についての取材と、媒体向けの寄稿",
                  'データ記事の更新のお知らせ（<a href="/feed.xml">RSS</a>）'],
        ct_who="サイエンスエックス株式会社　代表取締役 中島 晋也（工学博士）",
        ct_line='MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a> ／ TEL: <a href="tel:0366913484">03-6691-3484</a>',
        ct_form=("お問い合わせフォームから送る →", "/contact?intent=proposal"),
        mk_h="蓄電所マーケット",
        mk_text="売り案件そのものは、蓄電所マーケットで登録なしで一覧できます（価格と資料は無料の登録のあと）。",
        mk_btn=("蓄電所マーケットで案件を見る", "https://dealroom.scix.co.jp/"),
        updated="最終更新",
    ),
    "en": dict(
        html_lang="en", hreflang="en", og_locale="en_US", og_img="/img/ogp-m-en.png", home=("Home", "/en"),
        title="Newsroom | Press Releases, Company Facts, Media Contact | ScienceX",
        desc=("ScienceX newsroom: press releases (including the monthly Battery Storage Market Notes), company facts and the founder's "
              "profile, logos, photos, charts and data (CSV), and the contact for interviews and media inquiries."),
        h1="Newsroom", label="For journalists and editors",
        lead="Press releases from ScienceX, company facts, how to use our charts and data, and the contact for interviews, all on one page.",
        toc=[("releases", "Press releases"), ("company", "Company facts"), ("profile", "Founder profile"), ("assets", "Media assets"),
             ("contact", "Media contact"), ("market", "Chikudensho Market")],
        rel_h="Press releases", rel_lead="Newest first. The full text and charts are on each page.",
        read="Read the page →", vp="See the release on ValuePress! (Japanese) ↗", ja_only="Japanese only",
        list_name="Press releases from ScienceX",
        co_h="Company facts", co_more=("See the company page →", "/en/company"),
        co_rows=[
            ("Company name", "Science X Inc. (サイエンスエックス株式会社)"),
            ("Address", "BIZMARKS Nihonbashi Kayabacho 801, 8-2 Nihonbashi Koamicho, Chuo-ku, Tokyo 103-0016, Japan"),
            ("Representative", "Shinya Nakashima, Ph.D. (Eng.), Representative Director"),
            ("Founded", "2021"),
            ("Capital", "¥9 million"),
            ("Business", "Grid-scale battery storage: project screening, structuring and operation planning<br>Transfer of rights in confirmed projects; support in structuring real-asset investment"),
            ("Officers", "Representative Director: Shinya Nakashima, Ph.D. (Eng.)<br>Director, CTO: Toshio Oi (Former Director, Showa Denko K.K., now Resonac)<br>Director, CFO: Yoshinaga Karasawa (Former Representative Director and Executive Vice President, Teijin Limited)"),
            ("Corporate Number", '6010001215846 (<a href="https://info.gbiz.go.jp/hojin/ichiran?hojinBango=6010001215846" rel="noopener">check it on gBizINFO</a>)'),
            ("Contact", 'Phone <a href="tel:+81366913484">+81 3 6691 3484</a>　Email <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>'),
        ],
        co_lead="We focus on grid-scale battery storage, buying and selling projects. We have no capital ties to any manufacturer or EPC.",
        pf_h="Founder profile", pf_name="Shinya Nakashima, Ph.D. (Eng.), Representative Director",
        pf_more=("Full profile and research output →", "/en/company#profile"),
        pf_rows=[
            ("1990", "Joined Shinka Pharmaceutical Co., Ltd. as a researcher (pharmaceutical quality control, regulatory submissions and formulation research)"),
            ("1993", "Joined Nishikawa Keisoku Co., Ltd., a specialist trading firm and distributor for Yokogawa Electric and Hewlett-Packard covering measuring instruments, analytical equipment and plant control systems; worked there for 27 years on developing chemical analysis systems and LIMS and designing GC/MS analysis solutions"),
            ("2015", "Completed the doctoral program at the Graduate School of the Prefectural University of Kumamoto; Ph.D. in Engineering (environmental and energy engineering)"),
            ("2021", "Appointed Lecturer in Chemistry, Tokyo Kasei University (five years)"),
            ("2021", "Founded Science X Inc. and became its Representative Director (current). Biogas systems applying his doctoral research installed at three sites in Japan"),
        ],
        as_h="Media assets", as_lead="Figures and charts in our articles may be used without asking permission, as long as you credit the source. How to cite, what you may use and the embed code for charts are in our Citation & Press Guide.",
        as_press=("See the Citation & Press Guide (how to cite, charts, embed code) →", "/en/press"),
        as_yt=("Explainer videos on the ScienceX YouTube channel (Japanese) ↗", YT_CHANNEL),
        as_logo_h="Logo and photo",
        as_logo=[("/img/logo-white.png", "Logo (white, transparent PNG; for use on navy or dark backgrounds)"),
                 ("/img/apple-touch-icon.png", "Square mark (PNG)"),
                 ("/img/nakashima.png", "Photo of Shinya Nakashima, Representative Director (PNG)")],
        as_data_h="Data (CSV)",
        as_data=[("Battery Storage Market Data", "/en/report/data", [
                    ("/en/report/data/jepx-spot-monthly.csv", "Wholesale electricity (JEPX): monthly averages and spreads by area (month × area, all measures)"),
                    ("/en/report/data/capacity-main-auction.csv", "Capacity market (OCCTO): main auction area prices"),
                    ("/en/report/data/long-term-decarbonization-auction.csv", "Long-Term Decarbonization Power Source Auction: contracted capacity")]),
                 ("Japan BESS Projects for Sale: Market Data", "/en/market-data", [
                    ("/files/market-data/market-data-summary-en.csv", "Summary tables (by grid area, voltage class, expected grid connection and more)"),
                    ("/files/market-data/market-data-weekly-en.csv", "Weekly figures for listed projects")])],
        ct_h="Media contact", ct_lead="We respond to the following.",
        ct_items=["Explaining the source data of an article, and shaping the underlying tables of the charts into the form you need (tables only, an excerpt by area, and so on)",
                  "Interviews on the rules, markets and transactions of grid-scale battery storage, and contributions for media",
                  'Notice of updates to the data articles (<a href="/feed.xml">RSS</a>)'],
        ct_who="Science X Inc.　Shinya Nakashima, Ph.D. (Eng.), Representative Director",
        ct_line='MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a> / TEL: <a href="tel:+81366913484">+81 3 6691 3484</a>',
        ct_form=("Send us a message →", "/en/contact"),
        mk_h="Chikudensho Market",
        mk_text="The projects themselves are listed at Chikudensho Market, without registration (prices and documents after free registration).",
        mk_btn=("Browse projects at Chikudensho Market", "https://dealroom.scix.co.jp/en"),
        updated="Last updated",
    ),
}

CSS = """:root{--navy:#1F2A48;--navy-light:#2D3A5C;--gold:#C49A3C;--green:#1A7A4C;--white:#fff;--off-white:#F5F5F3;--text:#1F2A48;--text-2:#555555;--text-3:#8C8C8C;--border:#E6E6E6;--sans:'Noto Sans JP',sans-serif;--serif:'Noto Sans JP',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}html{font-size:16px;scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--text);background:var(--white);line-height:1.9;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.container{max-width:1100px;margin:0 auto;padding:0 24px}
.section-label{font-size:.78rem;font-weight:700;letter-spacing:.08em;color:var(--gold);margin-bottom:12px}
.hero{padding:64px 0 40px;background:linear-gradient(160deg,var(--white) 0%,var(--off-white) 60%,#EEEEEC 100%)}
.hero h1{font-family:var(--serif);font-size:clamp(1.5rem,3.4vw,2.2rem);font-weight:700;color:var(--navy);line-height:1.5;margin-bottom:16px}
.hero p{font-size:.95rem;color:var(--text-2);max-width:760px}
.nr-toc{list-style:none;display:flex;flex-wrap:wrap;gap:8px 10px;margin:22px 0 0;padding:0;max-width:760px}
.nr-toc a{display:inline-block;padding:6px 14px;border:1px solid var(--border);border-radius:999px;background:#fff;font-size:.84rem;color:var(--navy);text-decoration:none}
.nr-toc a:hover{border-color:var(--gold)}
section.md{padding:40px 0;border-top:1px solid var(--border);scroll-margin-top:72px}
h2.md-h{font-family:var(--serif);font-size:1.25rem;font-weight:700;color:var(--navy);margin-bottom:10px}
h3.md-s{font-size:1rem;font-weight:700;color:var(--navy);margin:22px 0 8px}
.md-lead{font-size:.92rem;color:var(--text-2);margin-bottom:18px;max-width:760px}
.md-more{margin-top:14px;font-size:.9rem}.md-more a,.md-body a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.md-body{max-width:860px}
.nr-list{list-style:none;padding:0;margin:0;border-top:1px solid var(--border);max-width:860px}
.nr-list>li{padding:20px 0;border-bottom:1px solid var(--border)}
.nr-meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;font-size:.84rem;color:var(--text-3)}
.nr-kind{display:inline-block;padding:2px 10px;border-radius:999px;background:#EEF2FA;color:#1E3A8A;font-size:.76rem;font-weight:700}
.nr-lang{font-size:.76rem;color:var(--text-3)}
a.nr-t{display:inline-block;margin-top:6px;font-size:1.1rem;font-weight:700;color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold);line-height:1.6}
.nr-pts{margin:10px 0 0;padding-left:1.3em;font-size:.92rem;line-height:1.85;color:var(--text-2)}.nr-pts li{margin:4px 0}
.nr-links{margin-top:10px;font-size:.88rem;display:flex;flex-wrap:wrap;gap:6px 22px}.nr-links a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
table.nr-t{border-collapse:collapse;font-size:.9rem;max-width:860px;width:100%}
.nr-t th,.nr-t td{border-bottom:1px solid var(--border);padding:9px 12px;text-align:left;vertical-align:top;line-height:1.8}
.nr-t th{color:var(--text-2);font-weight:500;background:var(--off-white);width:9em;white-space:nowrap}
.nr-t td a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.nr-pf-name{font-weight:700;color:var(--navy);margin-bottom:8px}
.nr-dl{list-style:none;padding:0;margin:0 0 6px;max-width:860px}.nr-dl li{padding:8px 0;border-bottom:1px solid var(--border);font-size:.9rem}
.nr-dl a{color:var(--navy);font-weight:600;text-decoration:none;border-bottom:1px solid var(--gold)}
.nr-sub{list-style:none;padding:0 0 0 1.1em;margin:6px 0 0}.nr-sub li{padding:3px 0;border:0;font-size:.86rem}.nr-sub a{font-weight:500}
.nr-ct{max-width:860px;background:var(--off-white);border:1px solid var(--border);border-radius:8px;padding:16px 20px;font-size:.92rem}
.nr-ct ul{padding-left:1.3em;margin:6px 0 12px}.nr-ct li{margin:4px 0}.nr-ct a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.rs-mk{max-width:1100px;margin:0;padding:20px 24px;background:#F3F6FD;border:1.5px solid #D2DCF2;border-radius:18px;display:flex;flex-wrap:wrap;align-items:center;gap:12px 24px}
.rs-mk p{flex:1 1 320px;font-size:.92rem;line-height:1.85;color:#24304A;margin:0}
.rs-mk a.rs-btn{display:inline-flex;align-items:center;justify-content:center;padding:13px 26px;background:#D4610A;color:#fff;font-weight:900;font-size:.95rem;border:0;border-radius:999px;text-decoration:none;box-shadow:0 6px 16px rgba(212,97,10,.30);white-space:nowrap}
.rs-mk a.rs-btn:hover{background:#EF7A1A;color:#fff}
.nr-upd{font-size:.82rem;color:var(--text-3);margin-top:22px}
@media(max-width:640px){.hero{padding:48px 0 32px}.nr-t th{width:auto;white-space:normal}.nr-t th,.nr-t td{display:block;border-bottom:0;padding:6px 10px}.nr-t tr{display:block;border-bottom:1px solid var(--border)}.rs-mk{padding:18px}.rs-mk a.rs-btn{width:100%;white-space:normal;text-align:center;line-height:1.5;padding:13px 16px}}
"""


# ---------------------------------------------------------------- 読み書き

def load() -> dict:
    return json.load(open(DATA, encoding="utf-8"))


def save(d: dict) -> None:
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def today_jst() -> str:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()


def page_file(path: str) -> str | None:
    """自社の頁の住所（/report/2026-11・/column-x）を、リポジトリのファイルにする。無ければ None。"""
    p = path.split("#")[0].strip("/")
    for c in ([p + ".html", p + "/index.html"] if p else ["index.html"]):
        if os.path.isfile(os.path.join(ROOT, c)):
            return os.path.join(ROOT, c)
    return None


def is_local(path: str) -> bool:
    return path.startswith("/") and not path.startswith("//")


def body_text(src: str) -> str:
    """頁の本文の字（タグ・空白を除き、文字参照を戻す）。突き合わせに使う。"""
    s = re.sub(r"<head\b.*?</head>|<script\b.*?</script>|<style\b.*?</style>", " ", src, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", "", s)


def squash(s: str) -> str:
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", " ", s)))


def head_meta(src: str, prop: str) -> str:
    m = re.search(r'<meta (?:name|property)="%s" content="([^"]*)"' % re.escape(prop), src)
    return html.unescape(m.group(1)).strip() if m else ""


# ---------------------------------------------------------------- 点検

def problems(d: dict) -> list:
    out = []
    ids = set()
    for r in d.get("releases", []):
        rid = r.get("id", "")
        if not re.fullmatch(r"\d{4}-\d\d-\d\d-[a-z0-9-]+", rid):
            out.append(f"id の形が違う: {rid!r}")
        if rid in ids:
            out.append(f"id が重なる: {rid}")
        ids.add(rid)
        if not re.fullmatch(r"\d{4}-\d\d-\d\d", r.get("date", "")):
            out.append(f"{rid}: date の形が違う")
        if r.get("kind") not in KINDS:
            out.append(f"{rid}: kind は {sorted(KINDS)} のどれか")
        vp = r.get("valuepress", "")
        if vp and not vp.startswith(VP_PREFIX):
            out.append(f"{rid}: valuepress は {VP_PREFIX} の住所だけ")
        if "ja" not in r:
            out.append(f"{rid}: ja が無い")
        for lg in ("ja", "en"):
            x = r.get(lg)
            if not x:
                continue
            page, title, pts = x.get("page", ""), x.get("title", ""), x.get("points", [])
            if not title or not page:
                out.append(f"{rid}/{lg}: title と page が要る")
                continue
            for s in [title] + pts:
                m = NG.search(s)
                if m:
                    out.append(f"{rid}/{lg}: 書かない語「{m.group(0)}」: {s[:40]}")
            if is_local(page):
                f = page_file(page)
                if not f:
                    out.append(f"{rid}/{lg}: 頁のファイルが無い: {page}")
                    continue
                if lg == "en" and not page.startswith("/en/"):
                    out.append(f"{rid}/{lg}: 英語の頁は /en/ の下: {page}")
                src = open(f, encoding="utf-8").read()
                bt = body_text(src)
                for s in [title] + pts:
                    if squash(s) not in bt:
                        out.append(f"{rid}/{lg}: 頁の本文に無い字: {s[:50]}")
            elif not page.startswith(MARKET_HOSTS):
                out.append(f"{rid}/{lg}: 行き先は自社の頁（/…）か蓄電所マーケットだけ: {page}")
    return out


# ---------------------------------------------------------------- 頁を作る

def jsonld(o) -> str:
    return '<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=1) + "\n</script>"


def disp_date(ymd: str, lg: str) -> str:
    y, m, dd = (int(x) for x in ymd.split("-"))
    if lg == "ja":
        return f"{y}年{m}月{dd}日"
    return datetime.date(y, m, dd).strftime("%B ") + f"{dd}, {y}"


def abs_url(page: str) -> str:
    return BASE + page if is_local(page) else page


def entries(d: dict, lg: str) -> list:
    """頁に出す並び（新しい日付から。同じ日はデータの後ろの物から）。英語の頁で英語の無い物は日本語のまま出す。"""
    rows = []
    for i, r in enumerate(d.get("releases", [])):
        x = r.get(lg) or r.get("ja")
        rows.append((r["date"], i, r, x, lg == "en" and not r.get("en")))
    rows.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return rows


def render(d: dict, lg: str) -> str:
    c = L[lg]
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    url = BASE + PATHS[lg]
    rows = entries(d, lg)
    org = {"@type": "Organization", "@id": ORG_ID, "name": "ScienceX",
           "alternateName": ["サイエンスエックス", "サイエンスエックス株式会社", "Science X Inc.", "Science X"],
           "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + "/img/logo-navy.png"},
           "sameAs": [YT_CHANNEL]}
    items = []
    for n, (_dt, _i, r, x, _jo) in enumerate(rows, 1):
        page = x["page"]
        li = {"@type": "ListItem", "position": n}
        f = page_file(page) if is_local(page) else None
        if f:   # 本文が自社の頁に在る物だけ NewsArticle
            src = open(f, encoding="utf-8").read()
            art = {"@type": "NewsArticle", "@id": url + "#" + r["id"], "headline": x["title"],
                   "datePublished": r["date"], "inLanguage": "en" if page.startswith("/en/") else "ja",
                   "url": abs_url(page), "mainEntityOfPage": abs_url(page),
                   "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}
            img = head_meta(src, "og:image")
            if img.startswith(BASE):
                art["image"] = img
            if r.get("valuepress"):
                art["sameAs"] = r["valuepress"]
            li["item"] = art
        else:
            li["url"] = abs_url(page)
            li["name"] = x["title"]
        items.append(li)
    ld_page = {
        "@context": "https://schema.org", "@type": "CollectionPage", "@id": url + "#webpage", "url": url,
        "name": c["title"], "description": c["desc"], "inLanguage": c["hreflang"],
        "datePublished": d["published"], "dateModified": d["modified"],
        "isPartOf": {"@type": "WebSite", "@id": SITE_ID, "url": BASE + "/", "name": "ScienceX"},
        "about": {"@id": ORG_ID}, "publisher": org,
        "breadcrumb": {"@id": url + "#breadcrumb"},
        "mainEntity": {"@type": "ItemList", "@id": url + "#releases", "name": c["list_name"],
                       "numberOfItems": len(items), "itemListElement": items},
    }
    ld_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": c["home"][0], "item": BASE + ("/" if c["home"][1] == "/" else c["home"][1])},
        {"@type": "ListItem", "position": 2, "name": c["h1"], "item": url}]}

    # プレスリリースの一覧
    lis = []
    for _dt, _i, r, x, ja_only in rows:
        kind = KINDS[r["kind"]][0 if lg == "ja" else 1]
        page = x["page"]
        ext = "" if is_local(page) else ' rel="noopener"'
        pts = "".join(f"<li>{e(p)}</li>" for p in x.get("points", []))
        links = [f'<a href="{e(page)}"{ext}>{e(c["read"])}</a>']
        if r.get("valuepress"):
            links.append(f'<a href="{e(r["valuepress"])}" rel="noopener">{e(c["vp"])}</a>')
        mark = "" if r.get("valuepress") else f"\n    <!-- valuepress: 配信の後に scripts/build_newsroom.py set-vp --id {r['id']} --url … で足す -->"
        lang_tag = f'<span class="nr-lang">{e(c["ja_only"])}</span>' if ja_only else ""
        lis.append(
            f'  <li id="{e(r["id"])}">\n'
            f'    <div class="nr-meta"><time datetime="{r["date"]}">{e(disp_date(r["date"], lg))}</time><span class="nr-kind">{e(kind)}</span>{lang_tag}</div>\n'
            f'    <a class="nr-t" href="{e(page)}"{ext}>{e(x["title"])}</a>\n'
            + (f'    <ul class="nr-pts">{pts}</ul>\n' if pts else "")
            + f'    <p class="nr-links">{"".join(links)}</p>{mark}\n'
            f"  </li>")
    rel_html = "\n".join(lis)

    co = "\n".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{v}</td></tr>" for k, v in c["co_rows"])
    pf = "\n".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{e(v)}</td></tr>" for k, v in c["pf_rows"])
    logos = "\n".join(f'<li><a href="{p}" download>{e(t)}</a></li>' for p, t in c["as_logo"])
    data_html = ""
    for name, page, csvs in c["as_data"]:
        data_html += f'<li><a href="{page}">{e(name)}</a><ul class="nr-sub">' + "".join(
            f'<li><a href="{p}" download>{e(t)}（CSV）</a></li>' if lg == "ja" else f'<li><a href="{p}" download>{e(t)} (CSV)</a></li>'
            for p, t in csvs) + "</ul></li>\n"
    toc = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in c["toc"])
    cts = "".join(f"<li>{t}</li>" for t in c["ct_items"])
    footer = open(os.path.join(PARTS, f"footer.{lg}.part"), encoding="utf-8").read().rstrip("\n")
    alts = (f'<link rel="alternate" hreflang="ja" href="{BASE}{PATHS["ja"]}">\n'
            f'<link rel="alternate" hreflang="en" href="{BASE}{PATHS["en"]}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{BASE}{PATHS["en"]}">')
    crumb = (f'<nav data-scix-breadcrumb aria-label="breadcrumb" style="max-width:1100px;margin:0 auto;padding:14px 24px 0;'
             f"font-family:'Noto Sans JP',sans-serif;font-size:12.5px;line-height:1.6;color:#8C8C8C\">"
             f'<a href="{c["home"][1]}" style="color:#555555;text-decoration:none">{e(c["home"][0])}</a>'
             f'<span style="color:#C49A3C;margin:0 7px">›</span><span style="color:#8C8C8C">{e(c["h1"])}</span></nav>')
    return f"""<!DOCTYPE html>
<html lang="{c['html_lang']}">
<head>
<link rel="icon" type="image/svg+xml" href="/img/favicon.svg">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
{ga_tag.BLOCK}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- scripts/build_newsroom.py が scripts/data/newsroom/releases.json から作る頁（手で直さない） -->
<title>{e(c['title'])}</title>
<meta name="description" content="{e(c['desc'])}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">
{alts}
<meta property="og:type" content="website">
<meta property="og:title" content="{e(c['title'])}">
<meta property="og:description" content="{e(c['desc'])}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{c['og_locale']}">
<meta property="og:site_name" content="ScienceX">
<meta property="og:image" content="{BASE}{c['og_img']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(c['title'])}">
<meta name="twitter:description" content="{e(c['desc'])}">
<meta name="twitter:image" content="{BASE}{c['og_img']}">
<link rel="alternate" type="application/rss+xml" title="ScienceX" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONT}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONT}"></noscript>
<style>
{CSS}</style>
{jsonld(ld_page)}
{jsonld(ld_bc)}
<link rel="stylesheet" href="/theme.css">
</head>
<body>
<script src="/header.js"></script>
{crumb}
<section class="hero"><div class="container">
  <div class="section-label">{e(c['label'])}</div>
  <h1>{e(c['h1'])}</h1>
  <p>{e(c['lead'])}</p>
  <ul class="nr-toc">{toc}</ul>
</div></section>
<section class="md" id="releases"><div class="container md-body">
<h2 class="md-h">{e(c['rel_h'])}</h2>
<p class="md-lead">{e(c['rel_lead'])}</p>
<ul class="nr-list">
{rel_html}
</ul>
</div></section>
<section class="md" id="company"><div class="container md-body">
<h2 class="md-h">{e(c['co_h'])}</h2>
<p class="md-lead">{e(c['co_lead'])}</p>
<table class="nr-t"><tbody>
{co}
</tbody></table>
<p class="md-more"><a href="{c['co_more'][1]}">{e(c['co_more'][0])}</a></p>
</div></section>
<section class="md" id="profile"><div class="container md-body">
<h2 class="md-h">{e(c['pf_h'])}</h2>
<p class="nr-pf-name">{e(c['pf_name'])}</p>
<table class="nr-t"><tbody>
{pf}
</tbody></table>
<p class="md-more"><a href="{c['pf_more'][1]}">{e(c['pf_more'][0])}</a></p>
</div></section>
<section class="md" id="assets"><div class="container md-body">
<h2 class="md-h">{e(c['as_h'])}</h2>
<p class="md-lead">{e(c['as_lead'])}</p>
<p class="md-more"><a href="{c['as_press'][1]}">{e(c['as_press'][0])}</a></p>
<p class="md-more"><a href="{c['as_yt'][1]}" rel="noopener">{e(c['as_yt'][0])}</a></p>
<h3 class="md-s">{e(c['as_logo_h'])}</h3>
<ul class="nr-dl">
{logos}
</ul>
<h3 class="md-s">{e(c['as_data_h'])}</h3>
<ul class="nr-dl">
{data_html}</ul>
</div></section>
<section class="md" id="contact"><div class="container md-body">
<h2 class="md-h">{e(c['ct_h'])}</h2>
<div class="nr-ct">
<p>{e(c['ct_lead'])}</p>
<ul>{cts}</ul>
<p>{e(c['ct_who'])}<br>{c['ct_line']}</p>
<p class="md-more"><a href="{c['ct_form'][1]}">{e(c['ct_form'][0])}</a></p>
</div>
</div></section>
<section class="md" id="market"><div class="container md-body">
<h2 class="md-h">{e(c['mk_h'])}</h2>
<div class="rs-mk"><p>{e(c['mk_text'])}</p><a class="rs-btn" href="{c['mk_btn'][1]}" data-cta="body" data-cta-target="market">{e(c['mk_btn'][0])}</a></div>
<p class="nr-upd">{e(c['updated'])}: <time datetime="{d['modified']}">{e(disp_date(d['modified'], lg))}</time></p>
</div></section>
{footer}
</body>
</html>
"""


# ---------------------------------------------------------------- sitemap（この頁の2行だけ）

def sitemap_text(sm: str, modified: str) -> str:
    def line(lg: str) -> str:
        me, other = (("ja", "en") if lg == "ja" else ("en", "ja"))
        return (f'  <url><loc>{BASE}{PATHS[lg]}</loc>'
                f'<xhtml:link rel="alternate" hreflang="{me}" href="{BASE}{PATHS[me]}"/>'
                f'<xhtml:link rel="alternate" hreflang="{other}" href="{BASE}{PATHS[other]}"/>'
                f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}{PATHS["en"]}"/>'
                f'<priority>{"0.6" if lg == "ja" else "0.5"}</priority><lastmod>{modified}</lastmod></url>')
    for lg in ("ja", "en"):
        rx = re.compile(r"  <url><loc>%s</loc>.*?</url>" % re.escape(BASE + PATHS[lg]))
        if rx.search(sm):
            sm = rx.sub(lambda _m, lg=lg: line(lg), sm, count=1)
        else:
            sm = sm.replace("</urlset>", line(lg) + "\n</urlset>", 1)
    return sm


# ---------------------------------------------------------------- 書く・見る

def targets(d: dict) -> dict:
    out = {os.path.join(ROOT, FILES[lg]): render(d, lg) for lg in ("ja", "en")}
    out[SITEMAP] = sitemap_text(open(SITEMAP, encoding="utf-8").read(), d["modified"])
    return out


def build(check: bool) -> int:
    d = load()
    bad = problems(d)
    for b in bad:
        print("決まりに触れる:", b)
    if bad:
        return 1
    drift = 0
    for path, text in targets(d).items():
        cur = open(path, encoding="utf-8").read() if os.path.isfile(path) else None
        if cur == text:
            continue
        if check:
            print("ずれ:", os.path.relpath(path, ROOT))
            drift += 1
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print("書いた:", os.path.relpath(path, ROOT))
    if check:
        return 1 if drift else 0
    return 0


# ---------------------------------------------------------------- add・set-vp

def from_page(page: str) -> tuple[str, list]:
    """自社の頁から題（h1）と要点（「3行で言うと」の枠、無ければ meta description の文）を取る。"""
    f = page_file(page)
    if not f:
        raise SystemExit(f"頁のファイルが無い: {page}（先に頁を公開してから足す）")
    src = open(f, encoding="utf-8").read()
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", src, re.S)
    title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " ", re.sub(r"<(?!br)[^>]+>", "", m.group(1))))).strip() if m else ""
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"(?<=[^\x00-\x7F])\s+(?=[^\x00-\x7F])", "", title)   # 日本語の改行（<br>）は詰める
    pts = []
    s3 = re.search(r'class="sum3"[^>]*>.*?<ol>(.*?)</ol>', src, re.S)
    if s3:
        pts = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip() for x in re.findall(r"<li>(.*?)</li>", s3.group(1), re.S)]
    if not pts:
        desc = head_meta(src, "description")
        if desc.endswith("…"):   # 切れた説明は、最後の文の終わりまでにする
            cut = max(desc.rfind("。"), desc.rfind(". "))
            desc = desc[: cut + 1].strip() if cut > 0 else ""
        for head in (title + "。", title + ". "):   # 説明の頭に題が付いている頁（市場ノート）は、題を外す
            if desc.startswith(head):
                desc = desc[len(head):].strip()
        if desc:
            pts = [desc]
    return title, pts


def en_of(page: str) -> str:
    f = page_file(page)
    if not f:
        return ""
    m = re.search(r'<link rel="alternate" hreflang="en" href="([^"]+)"', open(f, encoding="utf-8").read())
    if not m or not m.group(1).startswith(BASE):
        return ""
    p = m.group(1)[len(BASE):]
    return p if page_file(p) else ""


def kind_of(page: str) -> str:
    if page.startswith(MARKET_HOSTS):
        return "market"
    p = re.sub(r"^/en", "", page)
    if p.startswith("/report"):
        return "report"
    if p.startswith(("/column-", "/guide-")):
        return "column"
    return "news"


def cmd_add(a) -> int:
    d = load()
    ja_page = a.page or a.url
    if not ja_page:
        raise SystemExit("--page（自社の頁）か --url（蓄電所マーケットの頁）が要る")
    rec = {"date": a.date, "kind": a.kind or kind_of(ja_page), "valuepress": a.vp or ""}
    if is_local(ja_page):
        t, p = from_page(ja_page)
        rec["ja"] = {"title": a.ja_title or t, "page": ja_page, "points": a.ja_point or p}
        en_page = a.en_page or en_of(ja_page)
        if en_page:
            t2, p2 = from_page(en_page)
            rec["en"] = {"title": a.en_title or t2, "page": en_page, "points": a.en_point or p2}
    else:
        if not a.ja_title:
            raise SystemExit("外の頁は --ja-title（と --ja-point）を、公開の頁の字のまま渡す")
        rec["ja"] = {"title": a.ja_title, "page": ja_page, "points": a.ja_point or []}
        if a.en_title:
            rec["en"] = {"title": a.en_title, "page": a.en_url or a.en_page or ja_page, "points": a.en_point or []}
    slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://[^/]+", "", ja_page).lower()).strip("-") or "top"
    if rec["kind"] == "market" and not is_local(ja_page):
        slug = "market-" + slug if slug != "top" else "market"
    rec["id"] = f"{a.date}-{slug}"[:80].rstrip("-")
    if any(r["id"] == rec["id"] for r in d["releases"]):
        raise SystemExit(f"同じ id が既にある: {rec['id']}")
    rec = {k: rec[k] for k in ("id", "date", "kind", "valuepress", "ja", "en") if k in rec}
    d["releases"].append(rec)
    d["modified"] = today_jst()
    bad = problems(d)
    if bad:
        for b in bad:
            print("決まりに触れる:", b)
        return 1
    save(d)
    print("足した:", rec["id"], "／", rec["ja"]["title"])
    return build(check=False)


def cmd_set_vp(a) -> int:
    d = load()
    if not a.url.startswith(VP_PREFIX):
        raise SystemExit(f"ValuePress! の住所（{VP_PREFIX}…）だけ")
    hit = [r for r in d["releases"] if r["id"] == a.id]
    if not hit:
        raise SystemExit("id が無い: " + a.id + "（ある id: " + ", ".join(r["id"] for r in d["releases"]) + "）")
    hit[0]["valuepress"] = a.url
    d["modified"] = today_jst()
    save(d)
    print("ValuePress! の住所を足した:", a.id)
    return build(check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("add", help="リリースを1本足す")
    p.add_argument("--date", required=True, help="配信の日 YYYY-MM-DD")
    p.add_argument("--page", help="自社の頁（/column-x・/report/2026-12）")
    p.add_argument("--url", help="自社の頁の無い物の行き先（蓄電所マーケットの頁）")
    p.add_argument("--kind", choices=sorted(KINDS))
    p.add_argument("--en-page", help="英語の頁（省くと頁の hreflang から）")
    p.add_argument("--en-url", help="外の頁の英語の行き先")
    p.add_argument("--ja-title")
    p.add_argument("--en-title")
    p.add_argument("--ja-point", action="append", help="要点（何度でも）。省くと頁の「3行で言うと」か説明から")
    p.add_argument("--en-point", action="append")
    p.add_argument("--vp", help="ValuePress! の掲載頁（配信の後なら）")
    q = sub.add_parser("set-vp", help="配信の後に ValuePress! の掲載頁を足す")
    q.add_argument("--id", required=True)
    q.add_argument("--url", required=True)
    a = ap.parse_args()
    if a.cmd == "add":
        return cmd_add(a)
    if a.cmd == "set-vp":
        return cmd_set_vp(a)
    return build(check=a.check)


if __name__ == "__main__":
    sys.exit(main())
