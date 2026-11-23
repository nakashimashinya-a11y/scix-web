#!/usr/bin/env python3
"""ハブ・用語集・Q&A・収益の頁に、本文の外の決まった区画を足す（日英中）。

    python3 scripts/add_hub_blocks.py           # 書き込む
    python3 scripts/add_hub_blocks.py --check   # 書き込みが要る頁があれば終了コード 1

何度回しても同じ結果になる作り:
  * 区画は <!-- scix-g:<名前>:begin --> … <!-- scix-g:<名前>:end --> で囲む。
    回すたびに、まず全部の区画を外して元の頁に戻し、下のデータから置き直す。
  * 用語集の語数（title・description・バッジ・JSON-LD）は、置いた後の g-term の数で書き直す。
  * JSON-LD の Organization・WebSite の @id と、代表の Person の knowsAbout・alumniOf は、
    無いときだけ足す（あれば触らない）。

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」
（Gemini の SEO の助言の 指令1・指令5・指令6・指示5）。

書く事実は、当社のコラム・用語集・Q&A の本文にある事か、公表資料（OCCTO・総務省）を
原本で確かめた事だけ。出どころは各区画の data-src に書く。
制度・税・土地の語と問いは日本語の頁だけに置く（O16-53）。コラムの頁とトップ3頁には触らない。
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://www.scix.co.jp"
ORG_ID = f"{BASE}/#organization"
SITE_ID = f"{BASE}/#website"
MARKET_EN = "https://dealroom.scix.co.jp/en"

BLOCK_RE = re.compile(r"<!-- scix-g:([a-z0-9-]+):begin -->.*?<!-- scix-g:\1:end -->", re.S)


def wrap(name: str, body: str) -> str:
    return f"<!-- scix-g:{name}:begin -->{body}<!-- scix-g:{name}:end -->"


def strip_blocks(src: str) -> str:
    return BLOCK_RE.sub("", src)


def insert_before(src: str, anchor: str, block: str, *, after_from: str | None = None, path: str = "") -> str:
    start = src.find(after_from) if after_from else 0
    if start < 0:
        raise SystemExit(f"{path}: 起点が見つからない: {after_from[:60]}")
    i = src.find(anchor, start)
    if i < 0:
        raise SystemExit(f"{path}: 目印が見つからない: {anchor[:60]}")
    return src[:i] + block + src[i:]


def insert_after(src: str, anchor: str, block: str, *, after_from: str | None = None, path: str = "") -> str:
    start = src.find(after_from) if after_from else 0
    if start < 0:
        raise SystemExit(f"{path}: 起点が見つからない: {after_from[:60]}")
    i = src.find(anchor, start)
    if i < 0:
        raise SystemExit(f"{path}: 目印が見つからない: {anchor[:60]}")
    j = i + len(anchor)
    return src[:j] + block + src[j:]


# ---------------------------------------------------------------- 用語集の語

GLOSS = {
    "glossary.html": {
        "set": f"{BASE}/glossary#set",
        "page": f"{BASE}/glossary",
        "count": [r"(\d+)語を", r"用語集・(\d+)語"],
        "terms": {
            "c-0": [
                ("term-english-name", "系統用蓄電池の英語名（BESS・grid-scale battery storage）", "けいとうようちくでんちのえいごめい",
                 "英語では grid-scale battery storage、または BESS（battery energy storage system の略）と呼びます。海外の資料や英語の案件概要はこの言い方で書かれ、当社の英語の頁と英語の用語集も同じ言い方です。",
                 "/en/glossary#term-grid-scale-battery", "英語の用語集", "/en/glossary#term-grid-scale-battery"),
            ],
            "c-1": [
                ("term-clearing-method", "約定価格の決め方（需給調整市場・容量市場）", "やくじょうかかくのきめかた",
                 "需給調整市場の ΔkW は、落札した札ごとにその札の価格で精算するマルチプライス（pay-as-bid）で、市場の平均約定単価と個社の精算単価は一致しません。札には上限価格と、ガイドラインの一定額による上限がかかります。容量市場のメインオークションは最後の落札者の価格が全員に適用されるシングルプライス、LDA は応札価格がそのまま約定価格になるマルチプライスです。",
                 "/column-regional-revenue", "管区別の収益と pay-as-bid", "/column-regional-revenue /column-capacity-market /column-lda /glossary#term-一定額ガイドラインの"),
                ("term-adjustment-factor-requirement", "調整係数・リクワイアメント（容量市場）", "ちょうせいけいすう・リクワイアメント",
                 "容量市場で契約になる容量は、設備容量そのものではなく「設備容量×調整係数」で、4時間の蓄電池は係数で割り引かれます。リクワイアメントは、約定した電源が実需給の年に守る義務で、未達には経済的ペナルティがあり、上限は年間で契約金額の110%です。蓄電池は2027年度向けのメインオークションから、安定電源か発動指令電源として参加します。",
                 "/column-capacity-market", "容量市場メインオークションと蓄電池", "/qa#q3 /column-regional-revenue /column-contracts"),
                ("term-spread-arbitrage", "スプレッド（価格差）・アービトラージ", "スプレッド・アービトラージ",
                 "卸電力市場（JEPX）で、安い時間帯に充電し、高い時間帯に放電して得る価格差の取引。JEPX は1日を30分ごとの48コマで取引し、1日の最高値と最安値の差は2024年に平均約20円/kWh（2020年頃は約4円/kWh）でした。",
                 "/column-revenue", "3つの収益源とスタッキング", "/column-revenue /qa#q2"),
            ],
            "c-2": [
                ("term-necessity-check-form", "接続検討要否確認依頼書", "せつぞくけんとうようひかくにんいらいしょ",
                 "「接続検討の要否確認」を申し込むときの依頼書。広域機関（OCCTO）が高圧用・特別高圧用の様式を公開していて、連系先の一般送配電事業者に出します。回答は原則1か月で、検討料はかかりません。",
                 "/column-equipment", "接続検討の要否確認とは", "/column-equipment"),
                ("term-grid-connection-cost", "系統連系費用（工事費負担金の言い方）", "けいとうれんけいひよう",
                 "系統につなぐための工事費のうち、申込者が負担する分をこう呼ぶことがあります。回答書・請求書の上の名前は「工事費負担金」です。額は契約申込みへの本回答（連系承諾）で示されますが、最終額ではなく、工事の完了後の精算でもう一度動きます。",
                 "#term-工事費負担金", "工事費負担金", "/glossary#term-工事費負担金 /column-grid"),
                ("term-wheeling-approval", "託送供給の承諾（連系承諾とあわせて届く紙）", "たくそうきょうきゅうのしょうだく",
                 "契約申込みへの承諾（連系承諾）と同封か、続けて届く書類の一つ。東京電力パワーグリッドでは「託送供給の承諾のお知らせ」が届きます。同じころに、工事費負担金の請求書と負担金契約書、ノンファーム型接続の同意書の控えもそろいます。",
                 "/column-study-reply-3", "連系承諾で確定するもの、まだ動くもの", "/column-study-reply-3"),
                ("term-nonfirm-consent", "ノンファーム型接続の同意書", "ノンファームがたせつぞくのどういしょ",
                 "ノンファーム型接続で連系するときに出す同意書。OCCTO の様式には「容量市場および需給調整市場に参加できない場合は、これを容認すること」という文言がありますが、将来の制限の可能性への留保で、いまの一律の禁止ではありません。九州電力送配電は、発電量調整供給契約の申込みにこの同意書を求めています。",
                 "/column-nonfirm", "ノンファーム型接続と出力制御リスク", "/column-nonfirm /column-low-voltage"),
            ],
            "c-3": [
                ("term-jcstar-spelling", "JCスター・JCSTAR（JC-STAR の表記）", "ジェイシースター",
                 "JC-STAR はジェイシースターと読み、カタカナで「JCスター」、ハイフンを省いて「JCSTAR」とも書かれます。どれも、IPA が運営する IoT 機器のセキュリティのラベリング制度のことです。",
                 "/column-jcstar", "JC-STAR（JCスター）とは", "/column-jcstar /glossary#term-JCSTAR"),
                ("term-development-permit", "開発許可（都市計画法）", "かいはつきょか",
                 "都市計画法で、開発行為や、市街化調整区域での第一種特定工作物の新設に要る許可。国土交通省は2025年4月8日の技術的助言（国都計第7号）で、電気事業の用に供する電気工作物に当たらず危険物を含む系統用蓄電池は、第一種特定工作物に当たり得ると整理しました。高圧2MW級は発電事業者に当たらないので、正面から開発許可を求めることになる場合が多くなります。",
                 "/column-land-zoning", "市街化調整区域と国都計第7号", "/column-land-zoning /qa#q6"),
            ],
            "c-4": [
                ("term-rights-sale", "権利渡し（権利売り・権利売買）", "けんりわたし",
                 "権利譲渡の別の言い方。接続検討の回答と用地の権利を、建つ前の段階で渡す取引を指します。当社の案件一覧では「権利譲渡（開発中）」の区分で載せています。",
                 "#term-権利譲渡", "権利譲渡", "/glossary#term-権利譲渡 /glossary#term-取得の形"),
                ("term-secondary", "セカンダリー（稼働済みの蓄電所の取得）", "セカンダリー",
                 "商業運転を始め、市場取引の実績を持つ蓄電所を取得すること。買っているのは設備よりも、月ごとに積み上がった確かめられるキャッシュフローで、器は資産のことも SPC の持分のこともあります。",
                 "/column-buyer-structures", "蓄電所の買い方は、4つある", "/column-buyer-structures /glossary#term-稼働中案件"),
                ("term-rtb", "RTB（Ready To Build）", "アールティービー",
                 "海外の蓄電池の M&A で、開発が進み建設に着手できる段に達した案件を指す言葉。当社のコラムでは、欧州の観測で、初期段階・先行開発・RTB と段が上がるごとに開発の対価の上乗せが切り上がる例を紹介しています。当社の国内の案件一覧ではこの言葉を使わず、権利譲渡・完成渡し・稼働中の3つで表します。",
                 "/column-buyer-structures", "段が上がると価格が上がる理由", "/column-buyer-structures /glossary#term-取得の形"),
            ],
        },
    },
    "en/glossary.html": {
        "set": f"{BASE}/en/glossary#set",
        "page": f"{BASE}/en/glossary",
        "count": [r"Glossary: (\d+) Terms", r"\"(\d+) terms for ", r"Glossary · (\d+) terms"],
        "terms": {
            "c-0": [
                ("term-bess", "BESS (battery energy storage system)", None,
                 "Another name for grid-scale battery storage: BESS, short for battery energy storage system. Japanese documents call it 系統用蓄電池, and under the Electricity Business Act a grid-connected installation is a storage station (蓄電所).",
                 "#term-grid-scale-battery", "Grid-scale battery storage", "/en/glossary#term-grid-scale-battery /en/glossary#term-storage-station"),
            ],
            "c-1": [
                ("term-spread-arbitrage", "Spread and arbitrage (JEPX)", None,
                 "Trading the price difference on the wholesale market (JEPX): charging in cheap half-hour slots and discharging in expensive ones. JEPX trades the day in 48 half-hour slots; the gap between the daily high and low averaged about ¥20/kWh in 2024, against about ¥4/kWh around 2020.",
                 "/en/column-revenue", "The three revenue sources", "/column-revenue /en/column-revenue"),
            ],
            "c-3": [
                ("term-jcstar-spelling", "JCSTAR, JC STAR (spellings of JC-STAR)", None,
                 "JC-STAR is also written JCSTAR or JC STAR, and in Japanese as JCスター. All of them refer to the security labelling scheme for IoT products run by IPA.",
                 "/en/column-jcstar", "What JC-STAR requires", "/en/glossary#term-jc-star /column-jcstar"),
            ],
            "c-4": [
                ("term-rights-sale", "Rights sale (権利渡し, 権利売り)", None,
                 "Another name used in Japan for a rights transfer: the connection study reply and the land rights change hands before anything is built. Our listings show these projects as rights transfer (in development).",
                 "#term-rights-transfer", "Rights transfer", "/en/glossary#term-rights-transfer /en/glossary#term-form-of-acquisition"),
                ("term-secondary", "Secondary (acquiring an operating storage station)", None,
                 "Buying a storage station that has started commercial operation and has a market trading record. What you buy is less the equipment than a verifiable cash flow that has built up month by month; the vehicle can be the assets or interests in the SPC.",
                 "/en/column-buyer-structures", "Four ways to buy a storage station", "/column-buyer-structures /en/glossary#term-operating-asset"),
                ("term-rtb", "RTB (ready to build)", None,
                 "A term from overseas battery M&A for a project developed to the point where construction can start. Our article cites European observations in which the developer premium steps up from early stage to advanced development to RTB. Our listings in Japan do not use the term; they use rights transfer, completed-asset sale and operating asset.",
                 "/en/column-buyer-structures", "Why the price steps up by stage", "/column-buyer-structures /en/glossary#term-form-of-acquisition"),
            ],
        },
    },
    "zh-glossary.html": {
        "set": f"{BASE}/zh-glossary#set",
        "page": f"{BASE}/zh-glossary",
        "count": [r"的(\d+)个术语", r"术语表\s*[・·]\s*(\d+)个术语"],
        "terms": {
            "c-0": [
                ("term-bess", "BESS（电池储能系统）・grid-scale battery storage", None,
                 "电网侧储能的英文说法。BESS 是 battery energy storage system 的缩写，日文写作「系統用蓄電池」；按日本电气事业法，接入电网的储能设施属于储能电站（蓄電所）。",
                 "#term-电网侧储能系統用蓄電池", "电网侧储能", "/zh-glossary#term-电网侧储能系統用蓄電池 /zh-glossary#term-储能电站电气事业法"),
            ],
            "c-1": [
                ("term-spread-arbitrage", "价差（spread）・套利（arbitrage）", None,
                 "在批发电力市场（JEPX）的低价时段充电、高价时段放电，赚取价差的交易。JEPX 把一天分成48个30分钟时段交易，2024年一天中最高价与最低价之差平均约20日元/kWh（2020年前后约4日元/kWh）。",
                 "/zh-column-revenue", "储能的3个收益来源", "/column-revenue /zh-column-revenue"),
            ],
            "c-3": [
                ("term-jcstar-spelling", "JCSTAR・JC STAR（JC-STAR 的写法）", None,
                 "JC-STAR 也写作 JCSTAR、JC STAR，日文写作「JCスター」，都是指 IPA 运营的物联网产品安全标签制度。",
                 "/zh-column-jcstar", "JC-STAR 是什么", "/zh-glossary#term-JCSTAR /column-jcstar"),
            ],
            "c-4": [
                ("term-rights-sale", "权利出售（権利渡し・権利売り）", None,
                 "日本对「权利转让」的另一种说法：在建设之前，转让接入系统研究答复与用地权利的交易。本公司的项目一览以「权利转让（开发中）」类别刊登。",
                 "#term-权利转让", "权利转让", "/zh-glossary#term-权利转让 /zh-glossary#term-取得形式取得の形"),
                ("term-secondary", "二手交易（secondary・取得运行中的储能电站）", None,
                 "取得已开始商业运行、拥有市场交易实绩的储能电站。买的与其说是设备，不如说是按月累积、可以核实的现金流；载体可以是资产，也可以是 SPC 的份额。",
                 "/zh-column-buyer-structures", "储能电站的4种买法", "/column-buyer-structures /zh-glossary#term-运行中项目稼働中案件"),
                ("term-rtb", "RTB（ready to build）", None,
                 "海外储能并购中的用语，指开发已推进到可以开工建设阶段的项目。本公司的文章介绍了欧洲的观测：从初期阶段、先行开发到 RTB，开发对价的溢价逐级上升。本公司在日本的项目一览不使用此词，而以权利转让、竣工后转让、运行中项目三类表示。",
                 "/zh-column-buyer-structures", "阶段越高价格越高的原因", "/column-buyer-structures /zh-glossary#term-取得形式取得の形"),
            ],
        },
    },
}


def gloss_term_html(t) -> str:
    tid, name, yomi, desc, href, label, src = t
    span = f"<span>{html.escape(yomi)}</span>" if yomi else ""
    return (f'<div class="g-term" id="{tid}" data-src="{html.escape(src)}"><dt>{html.escape(name)}{span}</dt>'
            f'<dd>{html.escape(desc)} <a href="{href}">{html.escape(label)} →</a></dd></div>\n')


def apply_glossary(path: str, src: str) -> str:
    cfg = GLOSS[path]
    for sec, terms in cfg["terms"].items():
        block = wrap(f"gloss-{sec}", "\n" + "".join(gloss_term_html(t) for t in terms))
        src = insert_before(src, "</dl>", block, after_from=f'<section class="md" id="{sec}">', path=path)
    # JSON-LD: 同じ @id の DefinedTermSet に語を足す（ノードは @id で1つにまとまる）
    defined = []
    for terms in cfg["terms"].values():
        for tid, name, _y, desc, _h, _l, _s in terms:
            defined.append({"@type": "DefinedTerm", "@id": f"{cfg['page']}#{tid}", "name": name,
                            "description": desc, "url": f"{cfg['page']}#{tid}", "inDefinedTermSet": cfg["set"]})
    ld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "@id": cfg["set"], "hasDefinedTerm": defined}
    block = wrap("gloss-ld", '\n<script type="application/ld+json">\n'
                 + json.dumps(ld, ensure_ascii=False, indent=1) + "\n</script>\n")
    src = insert_before(src, "</head>", block, path=path)
    # 語数を、置いた後の g-term の数に合わせる
    # （定義の文 <dd> の中の数は数えない・書き換えない）
    n = src.count('class="g-term"')
    parts = re.split(r"(<dd>.*?</dd>)", src, flags=re.S)
    for k in range(0, len(parts), 2):
        for pat in cfg["count"]:
            parts[k] = re.sub(pat, lambda m: m.group(0)[:m.start(1) - m.start(0)] + str(n) + m.group(0)[m.end(1) - m.start(0):], parts[k])
    return "".join(parts)


# ---------------------------------------------------------------- Q&A（日本語だけ）

QA_NEW = [
    ("q25", "2MW・8MWhとは、何kW・何kWhですか。",
     "<p>2MWは2,000kW、8MWhは8,000kWhです。MW（メガワット）は一度に出し入れできる電気の大きさ（出力）、MWh（メガワット時）は貯めておける電気の量（容量）で、別の単位です。</p>"
     "<p>容量を出力で割った時間を「継続時間」と呼び、2MW・8MWhなら4時間。定格の出力で4時間、放電し続けられる大きさです。</p>"
     "<p>いま普及の主流の「高圧2MW級」は、この組み合わせの設備1基で、敷地は原則1,000㎡前後です（Q1）。2,000kWの線を越えると特別高圧の設備と手続きになるので、高圧の案件は1,990kW前後で設計されます（Q31）。</p>",
     [("/glossary#term-出力MWと容量MWh", "用語集：出力（MW）と容量（MWh）"), ("/column-construction-cost", "系統用蓄電池の建設費")],
     "/qa#q1 /glossary#term-出力MWと容量MWh /glossary#term-継続時間 /glossary#term-高圧特別高圧低圧電圧区分"),
    ("q26", "会社（SPC）の株を買うのと、設備を買うのは、何が違いますか。",
     "<p>買っているものが違います。</p>"
     "<p>SPC持分の取得は、蓄電所を持つSPC（特別目的会社）の株式・社員持分・匿名組合出資持分を買う形です。モノではなく「器ごと」買うので、契約・許認可・系統連系上の地位を、法人ごとまとめて引き受けます。器の中身も一緒に引き受けるので、買う前に確かめる範囲が広がります。</p>"
     "<p>設備や権利を買う形は、建った設備と土地（完成渡し）、または土地と系統連系に係る権利（接続検討の回答・接続契約上の地位・工事費負担金）を買う形（権利譲渡）です。接続検討の申込者の名義を売主から買主に変える名義変更などを、個別に進めます。</p>"
     "<p>どちらが優れているかではなく、買い手が持っている力と、引き受けられるリスクで答えが変わります。</p>",
     [("/column-buyer-structures", "蓄電所の買い方は、4つある（権利・完成・実績・器）"), ("/column-transfer", "開発権の譲渡")],
     "/column-buyer-structures /glossary#term-SPC特別目的会社 /glossary#term-名義変更"),
    ("q27", "長期脱炭素電源オークション（LDA）の募集要綱は、どこで読めますか。",
     "<p>電力広域的運営推進機関（OCCTO）が公表しています。第4回（応札年度2026年度）の募集要綱は2026年9月2日に公表されました（<a href=\"https://www.occto.or.jp/assets/260902_boshuyoukou_long_2026.pdf\" target=\"_blank\" rel=\"noopener\">長期脱炭素電源オークション募集要綱（応札年度：2026年度）・PDF</a>）。</p>"
     "<p>応札の受付は2027年1月19日〜26日です。その前に事業者情報の登録（2026年10月13日〜16日）と電源等情報の登録（10月19日〜23日）があり、ここに間に合わなければ応札できません。</p>"
     "<p>蓄電池が参加できるのは、送電端3万kW（30MW）以上（第2回から）で、1日1回以上・連続6時間以上の運転を続けられるもの（第3回から）です。接続検討回答書の取得が応札の前提です。高圧2MW級の案件は、この要件に届きません。</p>",
     [("/column-lda", "長期脱炭素電源オークション（LDA）とは"), ("/column-auction", "メインオークションとLDAの違い")],
     "/column-lda https://www.occto.or.jp/assets/260902_boshuyoukou_long_2026.pdf"),
    ("q28", "接続検討は、申込みから回答まで、どう進みますか。",
     "<p>事前相談のあと、連系先の一般送配電事業者に接続検討を申し込みます。検討料は各社とも1地点20万円（税別）です。回答書は原則3か月（高圧で500kWに満たない逆変換装置は2か月）で届きます。</p>"
     "<p>回答書は入口の紙で、この時点では系統の席はまだありません。続きは次の順です。</p>"
     "<ul><li>回答日から1年以内に、発電側と需要側の契約申込みを同時に出す</li><li>保証金を入金して受付になり、席の順番が付く（連系予約）</li><li>原則6か月の技術検討のあと、連系承諾で席が確定する</li><li>承諾の日から、1か月以内に工事費負担金の契約、2か月以内に土地の使用権原の書類（非FIT・非FIPで2026年10月1日以降に受け付けた申込みから）、期日までに入金</li></ul>"
     "<p>回答書に書かれた連系までの工期は、回答日からではなく、工事費負担金を入金した日から数えます。</p>",
     [("/column-study-reply", "接続検討回答書を毎日読む当社が、最初に見る6か所"), ("/column-grid-rules", "接続検討・契約申込みの新ルール")],
     "/column-study-reply /column-development /column-grid-rules"),
    ("q29", "工事費負担金は、いつ、どう払いますか。",
     "<p>額は、契約申込みへの本回答（連系承諾）で示されます。ただし最終額ではありません。机上計算の概算額のまま負担金契約を結ぶことがあり、差額は工事の完了後に追加請求か払戻しで精算します。額は承諾と精算で2回動くので、承諾の額を最終額として買値や計画に置かないでください。</p>"
     "<p>承諾と同封か続けて、請求書（明細書と振込用紙）と工事費負担金契約書が届きます。</p>"
     "<p>負担金の契約は承諾の日から1か月以内に結び、入金は請求書の期日までです。期日は電力会社で違い、九州は発行日から1か月、中部は請求後1か月以内が原則です。分割で払う場合は、初回に50%（九州電力送配電の公表のフローでは50%以上）を払います。</p>"
     "<p>回答書に書かれた連系までの工期は、この入金の日から数えます。会計や税の扱いは、案件ごとに税理士にご確認ください。</p>",
     [("/column-study-reply-3", "連系承諾で確定するもの、まだ動くもの"), ("/column-grid", "系統連系工事費が10倍違う理由")],
     "/column-study-reply-3 /column-study-reply /column-low-voltage"),
    ("q30", "固定資産税（償却資産）は、かかりますか。",
     "<p>固定資産税は、土地・家屋・償却資産にかかる市町村の税です（東京23区は都）。償却資産は、土地と家屋のほかの事業用の資産です（<a href=\"https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/149767_08.html\" target=\"_blank\" rel=\"noopener\">総務省「固定資産税の概要」</a>）。</p>"
     "<p>総務省の概要では、標準税率は1.4%、償却資産の免税点は150万円（令和9年度分から180万円）、賦課期日はその年度の初日の属する年の1月1日です。償却資産の評価額は、取得価額から取得後の年数に応じた減価を引いた額で、最低限度は取得価額の5%です。</p>"
     "<p>当社が収支の目安を組むときも、毎年の費用に償却資産の税を入れています。蓄電池や PCS などのどの設備が、どの区分で、いくらの評価になるかは、所在地の市町村と税理士にご確認ください。</p>",
     [("/column-somosomo-20", "いくらで買って、いくら戻るのか（費用の目盛り）"), ("/column-tax", "即時償却・一括償却")],
     "/column-somosomo-20 https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/149767_08.html"),
    ("q31", "低圧・高圧・特別高圧は、何が違いますか。",
     "<p>系統につなぐときの受電電力による区分です。区分によって、受電設備・手続き・保安の重さが変わります。</p>"
     "<div class=\"tw\"><table><thead><tr><th></th><th>低圧</th><th>高圧</th><th>特別高圧</th></tr></thead><tbody>"
     "<tr><td>受電電力</td><td>50kW未満</td><td>50kW以上2,000kW未満</td><td>2,000kW以上</td></tr>"
     "<tr><td>接続検討</td><td>無い（負担金は申し込んだ後に決まる）</td><td>有る</td><td>有る</td></tr>"
     "<tr><td>JC-STAR★1が必須になる契約申込み</td><td>2027年10月から</td><td>2027年4月から</td><td>2027年4月から</td></tr>"
     "</tbody></table></div>"
     "<p>高圧の案件が1,990kW前後で設計されるのは、2,000kWの線を越えると特別高圧の設備と手続きになるためです。</p>"
     "<p>どの区分でも、蓄電所は電気事業法で出力にかかわらず事業用電気工作物で、保安規程と電気主任技術者が要ります。「低圧なら簡単」とは言えません。</p>",
     [("/column-low-voltage", "「低圧なら簡単」は通用しない"), ("/glossary#term-高圧特別高圧低圧電圧区分", "用語集：高圧・特別高圧・低圧")],
     "/glossary#term-高圧特別高圧低圧電圧区分 /glossary#term-JCSTAR1の義務化 /glossary#term-蓄電所電気事業法 /column-low-voltage"),
]


def apply_qa(path: str, src: str) -> str:
    sec_title = "言葉と手続きを、もう少し"
    items = []
    toc = [f'<li class="s">{sec_title}</li>']
    for qid, q, ans, cols, srcs in QA_NEW:
        links = " ・ ".join(f'<a href="{h}">{html.escape(t)}</a>' for h, t in cols)
        items.append(f'<div class="qa" id="{qid}" data-src="{html.escape(srcs)}"><h3>{html.escape(q)}</h3>'
                     f'<div class="a">{ans}</div><div class="cols">📖 関連コラム: {links}</div></div>')
        toc.append(f'<li><a href="#{qid}">{html.escape(q)}</a></li>')
    body = f'\n<h2 class="sec" id="sec-more">{sec_title}</h2>' + "".join(items) + "\n"
    src = insert_before(src, '\n\n<div class="cta-section" style="margin-top:56px', wrap("qa-more", body),
                        after_from='id="q24"', path=path)
    src = insert_before(src, "</ol></nav>", wrap("qa-toc", "".join(toc)), path=path)
    return src


# ---------------------------------------------------------------- 柱と連載の区画

SOMO = {
    "ja": ("/column-somosomo", ["蓄電池の、そもそも — なぜ日本に蓄電池が要るのか", "昔は蓄電池がなくても回っていたよね", "回る機械が減った系統では、何が消えるのか", "なぜ「10秒」なのか", "再エネが増えるほど、調整力が要るのか", "火力に調整させれば、足りるのでは", "原発が増えたら、蓄電池はいらなくなる？", "揚水を増やせば、足りるのでは", "市場で買えなかった調整力は、どこから来ているのか", "データセンターが増えると、なぜ蓄電池なのか", "太陽光は、これからどうなる", "火力の量は、原発の稼働は、需要は", "蓄電池は、どれだけ増えるのか", "国は、蓄電池を増やしたいのか", "インフラ投資としての蓄電池は、何に似ているのか", "稼ぎは細るって言うけど、本当？", "海外の真似をして、日本で儲かるか", "蓄電池は、将来どれだけ必要なのか", "蓄電池は、どこに置いても同じなのか", "いくらで買って、いくら戻るのか"]),
    "en": ("/en/column-somosomo", ["Battery Storage, From First Principles — why Japan needs batteries", "The grid used to run fine without batteries, didn't it?", "What disappears from a grid with fewer spinning machines?", "Why \"ten seconds\"?", "Does more renewables mean more balancing power is needed?", "Can't thermal just do the balancing?", "If nuclear grows, do we stop needing batteries?", "Wouldn't more pumped storage be enough?", "Where does the balancing power that the market failed to buy come from?", "Why do data centres point to batteries?", "What happens to solar from here?", "Thermal volume, nuclear operation, demand — what next?", "How much battery capacity is actually coming?", "Does the government actually want more batteries?", "What does battery storage resemble as an infrastructure investment?", "They say the earnings will thin out. Is that true?", "Can you copy the overseas playbook and make money in Japan?", "How much battery storage will Japan ultimately need?", "Is a battery the same wherever you put it?", "What do you pay, and what comes back?"]),
    "zh": ("/zh-column-somosomo", ["储能的根本——日本为什么需要储能", "过去没有储能，不也转得好好的吗", "旋转机械减少的电网，会失去什么", "为什么是“10秒”", "可再生能源越多，就越需要调整力吗", "让火电去调节，不就够了吗", "核电增加了，储能就不需要了吧？", "多建抽蓄，不就够了吗", "在市场上没买到的调整力，是从哪里来的", "数据中心一多，为什么答案是储能", "光伏，今后会怎样", "火电的量、核电的开机、需求", "储能会增加多少", "国家想让储能增加吗", "作为基础设施投资的储能，像什么", "都说收益会变薄，是真的吗？", "照搬海外做法，在日本能赚钱吗", "储能将来到底需要多少", "储能放在哪里都一样吗", "花多少钱买，能回来多少"]),
}

# 柱の頁（指令1）。/guide-* は別の持ち場が作っている最中なので、頁のファイルがリポジトリに
# あるものだけを出す（無い住所は出さない＝404 を張らない）。柱の頁が入ったら、この生成器を
# 回し直すと札と1行が足される（--check はその時「直しが要る」を返す）。


def page_exists(href: str) -> bool:
    rel = href.split("#")[0].lstrip("/")
    if not rel:
        return True
    return (ROOT / f"{rel}.html").exists() or (ROOT / rel / "index.html").exists() or (ROOT / rel).is_file()

PILLARS = {
    "ja": [
        ("/guide-balancing-market", "需給調整市場", "5つの商品・約定の実績・上限価格・前日取引化"),
        ("/guide-capacity-lda", "容量市場とLDA・長期契約", "メインオークション・LDA・トーリング契約"),
        ("/guide-revenue-cost", "収益と費用", "3つの収益源・建設費・毎年の費用"),
        ("/guide-buy-sell", "案件の売買", "4つの買い方・売買の順番・買う前の確認"),
        ("/guide-siting-risk", "立地と運用のリスク", "区域・騒音・災害・保険・O&M"),
        ("/column-study-reply", "接続検討と系統連系", "回答書・承諾・工事費負担金の読み方（連載）"),
        ("/column-investment-tax", "税（即時償却）", "大胆な投資促進税制の受付と手続き（連載）"),
        ("/column-subsidies", "補助金", "実効補助率と、使うかどうかの判断軸"),
        ("/column-jcstar", "JC-STAR", "★1の義務化はいつから・対象機器"),
    ],
    "en": [
        ("/en/guide-balancing-market", "Balancing market", "Five products, clearing results, price cap, day-ahead trading"),
        ("/en/guide-capacity-lda", "Capacity market, LDA and long-term contracts", "Main auction, LDA, tolling contracts"),
        ("/en/guide-revenue-cost", "Revenue and costs", "Three revenue sources, build cost, annual costs"),
        ("/en/guide-buy-sell", "Buying and selling projects", "Four ways to buy, the order of a sale, checks before buying"),
        ("/en/guide-siting-risk", "Siting and operating risks", "Zoning, noise, disasters, insurance, O&M"),
        ("/en/column-jcstar", "JC-STAR", "When the ★1 requirement applies and to which devices"),
        ("/en/guide-japan-bess-market", "Japan BESS market overview", "Three revenue markets, grid connection steps, ways to acquire a project, FEFTA"),
    ],
    "zh": [
        ("/zh-guide-balancing-market", "辅助服务市场", "5个商品・成交实绩・上限价格・日前交易化"),
        ("/zh-guide-capacity-lda", "容量市场与LDA・长期合同", "主拍卖・LDA・容量租赁合同"),
        ("/zh-guide-revenue-cost", "收益与费用", "3个收益来源・建设费・每年的费用"),
        ("/zh-guide-buy-sell", "项目买卖", "4种买法・买卖的顺序・购买前的确认"),
        ("/zh-guide-siting-risk", "选址与运营风险", "区域・噪音・灾害・保险・运维"),
        ("/zh-column-jcstar", "JC-STAR", "★1何时强制・对象设备"),
        ("/zh-guide-japan-bess-market", "日本电网侧储能市场概览", "三个收益市场・并网手续的顺序・项目的取得方式・外汇法"),
    ],
}


def somo_list(lang: str) -> str:
    base, titles = SOMO[lang]
    lis = []
    for i, t in enumerate(titles, start=1):
        href = base if i == 1 else f"{base}-{i}"
        lis.append(f'<li><a target="_top" href="{href}">{html.escape(t)}</a></li>')
    return "<ol class=\"g-somo\">" + "".join(lis) + "</ol>"


PILLAR_CSS = ("<style>.g-pillars{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:18px 0 8px;padding:0;list-style:none}"
              ".g-pillars a{display:block;height:100%;background:#fff;border-radius:14px;box-shadow:0 4px 14px rgba(31,42,72,.08);padding:14px 16px;text-decoration:none;color:#1F2A48;border-top:5px solid var(--acc,#7C4DDB)}"
              ".g-pillars a,.g-pillars a *{text-decoration:none!important;border-bottom:0!important}.g-pillars a:hover{box-shadow:0 8px 22px rgba(31,42,72,.14)}"
              ".g-pillars a strong{display:block;font-size:1rem;margin-bottom:4px}.g-pillars a span{font-size:.85rem;color:#5B6478;line-height:1.6}"
              ".g-somo{margin:12px 0 0;padding-left:1.6em;columns:2;column-gap:32px;font-size:.92rem;line-height:1.9}.g-somo a{color:#1F2A48}"
              "@media(max-width:720px){.g-somo{columns:1}}</style>")


def pillar_cards(lang: str) -> str:
    lis = "".join(f'<li><a target="_top" href="{h}"><strong>{html.escape(n)}</strong><span>{html.escape(d)}</span></a></li>'
                  for h, n, d in PILLARS[lang] if page_exists(h))
    return f'<ul class="g-pillars">{lis}</ul>'


def apply_grid_storage(path: str, src: str) -> str:
    body = ("\n<!-- PILLARS -->\n<section class=\"section\" id=\"pillars\" data-src=\"/knowledge\">" + PILLAR_CSS +
            "\n  <div class=\"wrap\">\n"
            "    <h2 class=\"head\">テーマごとに、<em>くわしく読む。</em></h2>\n"
            "    <p class=\"lead\">このページは「系統用蓄電池とは」の入口です。ここから先は、テーマごとに続けて読めるページに分けています。</p>\n"
            f"    {pillar_cards('ja')}\n"
            "    <h3 style=\"margin:34px 0 0;font-size:1.1rem;color:#1F2A48\">連載「蓄電池の、そもそも」</h3>\n"
            "    <p style=\"margin:6px 0 0\">なぜ日本に蓄電池が要るのかを、電力の仕組みから順に答える連載です。</p>\n"
            f"    {somo_list('ja')}\n"
            "  </div>\n</section>\n")
    return insert_before(src, "\n<!-- FAQ -->", wrap("pillars", body), path=path)


def apply_primer(path: str, src: str, lang: str) -> str:
    if lang == "en":
        h2, lead, h3, sub = ("Japan BESS by topic",
                             "This primer is the entry point. The pages below go deeper, one topic at a time.",
                             "Battery Storage, From First Principles",
                             "A series that answers, from how the grid works, why Japan needs batteries.")
    else:
        h2, lead, h3, sub = ("按主题深入阅读",
                             "本页是入门。下面的页面按主题逐一深入。",
                             "系列「储能的根本」",
                             "从电力系统的运作出发，依次回答日本为什么需要储能。")
    body = (f'\n<h2 id="topics" data-src="/{"en/knowledge" if lang == "en" else "zh-knowledge"}">{h2}</h2>{PILLAR_CSS}\n'
            f"<p>{lead}</p>\n{pillar_cards(lang)}\n<h3>{h3}</h3>\n<p>{sub}</p>\n{somo_list(lang)}\n")
    return insert_before(src, '\n<div class="cta-box">', wrap("pillars", body), path=path)


# /knowledge の分類ごとに、柱への1行（並びとナビは変えない）
KNOW_LINES = {
    "ja": {
        "basics": [("/grid-storage", "系統用蓄電池とは")],
        "market": [("/guide-balancing-market", "需給調整市場"), ("/guide-capacity-lda", "容量市場とLDA・長期契約"), ("/guide-revenue-cost", "収益と費用")],
        "rules": [("/column-investment-tax", "税（即時償却）"), ("/column-subsidies", "補助金"), ("/column-study-reply", "接続検討と系統連系"), ("/column-jcstar", "JC-STAR")],
        "deal": [("/guide-buy-sell", "案件の売買")],
        "land": [("/guide-siting-risk", "立地と運用のリスク")],
        "tech": [("/guide-siting-risk", "立地と運用のリスク"), ("/column-jcstar", "JC-STAR")],
    },
    "en": {
        "basics": [("/en/primer", "Japan grid-scale storage: a primer"), ("/en/guide-japan-bess-market", "Japan BESS market overview")],
        "land": [("/en/guide-siting-risk", "Siting and operating risks")],
        "market": [("/en/guide-balancing-market", "Balancing market"), ("/en/guide-capacity-lda", "Capacity market, LDA and long-term contracts"), ("/en/guide-revenue-cost", "Revenue and costs")],
        "rules": [("/en/column-jcstar", "JC-STAR")],
        "deal": [("/en/guide-buy-sell", "Buying and selling projects")],
        "tech": [("/en/guide-siting-risk", "Siting and operating risks"), ("/en/column-jcstar", "JC-STAR")],
    },
    "zh": {
        "basics": [("/zh-primer", "日本电网级储能入门"), ("/zh-guide-japan-bess-market", "日本电网侧储能市场概览")],
        "land": [("/zh-guide-siting-risk", "选址与运营风险")],
        "market": [("/zh-guide-balancing-market", "辅助服务市场"), ("/zh-guide-capacity-lda", "容量市场与LDA・长期合同"), ("/zh-guide-revenue-cost", "收益与费用")],
        "rules": [("/zh-column-jcstar", "JC-STAR")],
        "deal": [("/zh-guide-buy-sell", "项目买卖")],
        "tech": [("/zh-guide-siting-risk", "选址与运营风险"), ("/zh-column-jcstar", "JC-STAR")],
    },
}
KNOW_LABEL = {"ja": "このテーマの案内：", "en": "Guide to this topic: ", "zh": "本主题导读："}


def apply_knowledge(path: str, src: str, lang: str) -> str:
    if lang == "zh":
        blk_tpl, list_anchor = '<div class="kn-group" id="kn-cat-{}">', '<div class="kn-list">'
    else:
        blk_tpl, list_anchor = '<div class="cat-block" id="cat-{}">', '<div class="article-list"'
    for cat, links in KNOW_LINES[lang].items():
        links = [(h, t) for h, t in links if page_exists(h)]
        if not links:
            if lang == "zh":
                anchor = f'<span id="cat-{cat}" style="display:block;position:relative;top:-90px" aria-hidden="true"></span>\n  '
                src = insert_before(src, blk_tpl.format(cat), wrap(f"anchor-{cat}", anchor), path=path)
            continue
        a = " ・ ".join(f'<a target="_top" href="{h}">{html.escape(t)} →</a>' for h, t in links)
        line = f'<p class="cat-note" data-scix-pillar="{cat}" style="margin:-6px 0 18px">{KNOW_LABEL[lang]}{a}</p>\n      '
        src = insert_before(src, list_anchor, wrap(f"pillar-{cat}", line), after_from=blk_tpl.format(cat), path=path)
        if lang == "zh":   # 英日と同じ cat-* の錨（パンくずの分類の段の行き先）
            anchor = f'<span id="cat-{cat}" style="display:block;position:relative;top:-90px" aria-hidden="true"></span>\n  '
            src = insert_before(src, blk_tpl.format(cat), wrap(f"anchor-{cat}", anchor), path=path)
    return src


# ---------------------------------------------------------------- 英中の導線（指示5）

CTA_TEXT = {
    "en": ("Looking at projects for sale?",
           "Chikudensho Market lists them without registration — prefecture, size, voltage, sale type and procedural stage. Prices and documents follow free registration.",
           "See projects on Chikudensho Market →", "Contact us", "/en/contact"),
    "zh": ("在找在售的项目吗？",
           "在蓄电所市场无需注册即可查看所在县、规模、电压、交易方式与手续阶段；价格与资料在免费注册后可见。",
           "在蓄电所市场查看项目 →", "联系我们", "/zh-contact"),
}
BTN = "display:inline-block;padding:12px 22px;margin:8px 10px 0 0;font-size:.95rem;text-decoration:none"


def mid_cta(lang: str, mark: str = "hub-mid") -> str:
    h, p, b1, b2, href2 = CTA_TEXT[lang]
    return (f'\n<aside class="scix-hub-cta" data-cta="{mark}" style="box-sizing:border-box;width:calc(100% - 32px);max-width:1100px;margin:28px auto;padding:20px 24px;'
            f'background:#fff;border-radius:16px;box-shadow:0 6px 18px rgba(31,42,72,.08);border-left:6px solid #F97316">'
            f'<p style="margin:0 0 4px;font-weight:800;color:#1F2A48">{html.escape(h)}</p>'
            f'<p style="margin:0;color:#4A5468;font-size:.92rem;line-height:1.8">{html.escape(p)}</p>'
            f'<a class="btn-primary" target="_top" href="{MARKET_EN}" style="{BTN}">{html.escape(b1)}</a>'
            f'<a class="btn-secondary" target="_top" href="{href2}" style="{BTN}">{html.escape(b2)}</a></aside>\n')


def end_btn(lang: str) -> str:
    b1 = CTA_TEXT[lang][2]
    return (f'\n  <a class="btn-secondary" target="_top" href="{MARKET_EN}" data-cta="hub-end" '
            f'style="{BTN};margin-left:8px">{html.escape(b1)}</a>')


def contact_market(lang: str) -> str:
    if lang == "en":
        h, p, b = ("Before you write", "The projects themselves are listed on Chikudensho Market, with no registration needed to browse. If you have a question, please use the form below.",
                   "See projects on Chikudensho Market →")
    else:
        h, p, b = ("联系之前", "在售的项目本身已刊登在蓄电所市场，浏览无需注册。如有疑问，请使用下方的表单。", "在蓄电所市场查看项目 →")
    return (f'\n<aside class="scix-hub-cta" data-cta="contact-market" style="box-sizing:border-box;width:calc(100% - 32px);max-width:760px;margin:28px auto 8px;padding:20px 24px;'
            f'background:#fff;border-radius:16px;box-shadow:0 6px 18px rgba(31,42,72,.08);border-left:6px solid #F97316">'
            f'<p style="margin:0 0 4px;font-weight:800;color:#1F2A48">{html.escape(h)}</p>'
            f'<p style="margin:0;color:#4A5468;font-size:.92rem;line-height:1.8">{html.escape(p)}</p>'
            f'<a class="btn-primary" target="_top" href="{MARKET_EN}" style="{BTN}">{html.escape(b)}</a></aside>\n')


# (頁, 言葉, 途中の目印〔前に置く〕, 末尾の目印〔後に置く〕, 末尾の目印を探し始める所)
CTA_PAGES = [
    ("en/knowledge.html", "en", '<div class="cat-block" id="cat-market">', 'href="/en/contact" class="cb">Contact Us →</a>', '<div class="cta">'),
    ("zh-knowledge.html", "zh", '<!-- scix-g:anchor-market:begin -->', '<a class="cta-btn" href="/zh-contact">申请保密演示文稿 →</a>', None),
    ("en/glossary.html", "en", '<section class="md" id="c-2">', None, None),
    ("zh-glossary.html", "zh", '<section class="md" id="c-2">', None, None),
    ("en/qa.html", "en", '<h2 class="sec" id="sec-after">', 'en/contact" class="cta-btn">Contact us →</a>', '<div class="cta-section">'),
    ("zh-qa.html", "zh", '<h2 class="sec" id="sec-after">', 'zh-contact" class="cta-btn">联系我们 →</a>', '<div class="cta-section">'),
    ("en/primer.html", "en", '<h2 id="rights">', 'class="cta-btn">Start a confidential conversation →</a>', '<div class="cta-box">'),
    ("zh-primer.html", "zh", '<h2 id="rights">', 'class="cta-btn">开始保密沟通 →</a>', '<div class="cta-box">'),
    ("en/company.html", "en", None, 'href="/en/contact" class="btn-primary">Contact us →</a>', '<section class="cta" id="contact">'),
    ("en/faq.html", "en", '<section class="f-sec alt" id="terms">', None, None),
    ("en/market-entry-guide.html", "en", '<h2>5. Grid-connection mechanics, in brief</h2>', 'href="/en/contact" class="cta-button">Contact us →</a>', '<div class="cta-box">'),
]
# 今ある行き先がマーケットのリンクに、data-cta の印を付ける（無いときだけ・何度回しても同じ）
ATTR_MARKS = [
    ("en/faq.html", '<a class="f-sub" target="_top" href="https://dealroom.scix.co.jp/en">',
     '<a class="f-sub" data-cta="hub-end" target="_top" href="https://dealroom.scix.co.jp/en">'),
    ("en/faq.html", '<a href="https://dealroom.scix.co.jp/en/register" target="_top">',
     '<a href="https://dealroom.scix.co.jp/en/register" data-cta="faq-register" target="_top">'),
]
CONTACT_PAGES = [("en/contact.html", "en"), ("zh-contact.html", "zh")]


def apply_cta(path: str, src: str, lang: str, mid: str | None, end: str | None, end_from: str | None) -> str:
    if mid:
        src = insert_before(src, mid, wrap("cta-mid", mid_cta(lang)), path=path)
    if end:
        src = insert_after(src, end, wrap("cta-end", end_btn(lang)), after_from=end_from, path=path)
    return src


# ---------------------------------------------------------------- 画面のパンくず（英中のハブ）

CRUMB_STYLE = ("max-width:1100px;margin:0 auto;padding:14px 24px 0;font-family:'Noto Sans JP',sans-serif;"
               "font-size:12.5px;line-height:1.6;color:#8C8C8C")
CRUMB_PAGES = ["en/knowledge.html", "zh-knowledge.html", "en/faq.html"]


def breadcrumb_items(src: str):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "BreadcrumbList":
            return [(i["name"], i["item"]) for i in d["itemListElement"]]
    return None


def apply_crumb(path: str, src: str) -> str:
    items = breadcrumb_items(src)
    if not items:
        raise SystemExit(f"{path}: BreadcrumbList が無い")
    parts = []
    for k, (name, url) in enumerate(items):
        if k:
            parts.append('<span style="color:#C49A3C;margin:0 7px">›</span>')
        if k == len(items) - 1:
            parts.append(f'<span style="color:#8C8C8C">{html.escape(name)}</span>')
        else:
            href = url.replace(BASE, "") or "/"
            parts.append(f'<a href="{href}" style="color:#555555;text-decoration:none">{html.escape(name)}</a>')
    nav = f'\n<nav data-scix-breadcrumb aria-label="breadcrumb" style="{CRUMB_STYLE}">' + "".join(parts) + "</nav>"
    return insert_after(src, '<script src="/header.js"></script>', wrap("crumb", nav), after_from="<body", path=path)


# ---------------------------------------------------------------- JSON-LD の @id（指令5）

LD_PAGES = ["glossary.html", "grid-storage.html", "qa.html", "company.html", "en/faq.html", "en/glossary.html", "en/knowledge.html", "en/primer.html", "en/qa.html",
            "zh-glossary.html", "zh-knowledge.html", "zh-primer.html", "zh-qa.html",
            "en/company.html", "en/contact.html", "zh-contact.html", "en/market-entry-guide.html"]
# en/projects.html は scripts/build_market_data.py が全体を書く（@id と末尾の導線はそちらで出す）
LD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
TOP_TYPES_PARTOF = {"Article", "FAQPage", "CollectionPage", "ContactPage", "WebPage"}


def _enclosing(text: str, pos: int):
    """pos を含む一番内側の {…} の範囲（文字列の中の括弧は数えない）。"""
    depth, i, in_str = 0, pos, False
    # 後ろへ: 文字列の判定のため頭から走査して開き括弧の位置を積む
    stack, j, esc = [], 0, False
    while j < pos:
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                stack.append(j)
            elif c == "}":
                stack.pop()
        j += 1
    start = stack[-1]
    depth, j, in_str, esc = 0, start, False, False
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, j
        j += 1
    raise ValueError("括弧が閉じていない")


def _own_keys(obj_text: str) -> str:
    """直下の階層の文字だけ（入れ子の {…} を消す）。"""
    out, depth, in_str, esc = [], 0, False, False
    for c in obj_text[1:-1]:
        if in_str:
            if depth == 0:
                out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            if depth == 0:
                out.append(c)
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            out.append(c)
    return "".join(out)


def add_ids(block: str) -> str:
    for typ, ident in (("Organization", ORG_ID), ("WebSite", SITE_ID)):
        while True:
            changed = False
            for m in re.finditer(r'"@type":\s*"' + typ + r'"', block):
                s, e = _enclosing(block, m.start())
                if '"@id"' in _own_keys(block[s:e + 1]):
                    continue
                block = block[:m.end()] + f', "@id": "{ident}"' + block[m.end():]
                changed = True
                break
            if not changed:
                break
    # 頁の主のノードに WebSite の参照（isPartOf）が無ければ足す
    try:
        d = json.loads(block)
    except ValueError:
        return block
    if isinstance(d, dict) and d.get("@type") in TOP_TYPES_PARTOF and "isPartOf" not in d:
        m = re.search(r'"@type":\s*"' + d["@type"] + r'"', block)
        ref = f', "isPartOf": {{"@type": "WebSite", "@id": "{SITE_ID}", "name": "ScienceX", "url": "{BASE}/"}}'
        block = block[:m.end()] + ref + block[m.end():]
    return block


def apply_ld_ids(path: str, src: str) -> str:
    def fix(m):
        new = add_ids(m.group(2))
        json.loads(new)  # 壊していないことを確かめる
        return m.group(1) + new + m.group(3)
    return LD_RE.sub(fix, src)


# 代表の Person（/company・/en/company）に、本文にある事実だけを足す
PERSON_ADD = {
    "company.html": {
        "knowsAbout": ["系統用蓄電池", "蓄電所の案件の技術確認（技術DD）", "計測と制御（PCS・EMS）", "化学分析（GC/MS）",
                       "環境・エネルギー工学", "バイオマス転換・半炭化処理"],
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "熊本県立大学", "alternateName": "Prefectural University of Kumamoto"},
    },
    "en/company.html": {
        "knowsAbout": ["Grid-scale battery storage", "Technical due diligence of battery storage projects",
                       "Measurement and control (PCS, EMS)", "Chemical analysis (GC/MS)",
                       "Environmental and energy engineering", "Biomass conversion and torrefaction"],
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Prefectural University of Kumamoto", "alternateName": "熊本県立大学"},
    },
}


def apply_person(path: str, src: str) -> str:
    add = PERSON_ADD[path]
    anchor = '"honorificSuffix": "Ph.D. (Eng.)",'
    i = src.find(anchor)
    if i < 0:
        raise SystemExit(f"{path}: Person の目印が無い")
    # 同じ founder の中に無いときだけ足す
    s, e = _enclosing(src, i)
    if '"knowsAbout"' in src[s:e]:
        return src
    line_start = src.rfind("\n", 0, i) + 1
    indent = src[line_start:i]
    ins = (f'\n{indent}"knowsAbout": {json.dumps(add["knowsAbout"], ensure_ascii=False)},'
           f'\n{indent}"alumniOf": {json.dumps(add["alumniOf"], ensure_ascii=False)},')
    j = i + len(anchor)
    return src[:j] + ins + src[j:]


# ---------------------------------------------------------------- 本体

def build(path: str, src: str) -> str:
    src = strip_blocks(src)
    if path in GLOSS:
        src = apply_glossary(path, src)
    if path == "qa.html":
        src = apply_qa(path, src)
    if path == "grid-storage.html":
        src = apply_grid_storage(path, src)
    if path in ("en/primer.html", "zh-primer.html"):
        src = apply_primer(path, src, "en" if path.startswith("en/") else "zh")
    if path in ("knowledge.html", "en/knowledge.html", "zh-knowledge.html"):
        src = apply_knowledge(path, src, {"knowledge.html": "ja", "en/knowledge.html": "en"}.get(path, "zh"))
    for p, lang, mid, end, end_from in CTA_PAGES:
        if p == path:
            src = apply_cta(path, src, lang, mid, end, end_from)
    for p, lang in CONTACT_PAGES:
        if p == path:
            src = insert_before(src, '<!-- ===== MAIN CONTENT ===== -->', wrap("cta-contact", contact_market(lang) + "\n"), path=path)
    for p, old, new in ATTR_MARKS:
        if p == path:
            src = src.replace(old, new)
    if path in CRUMB_PAGES:
        src = apply_crumb(path, src)
    if path in LD_PAGES:
        src = apply_ld_ids(path, src)
    if path in PERSON_ADD:
        src = apply_person(path, src)
    return src


def targets():
    t = set(GLOSS) | {"qa.html", "grid-storage.html", "en/primer.html", "zh-primer.html",
                      "knowledge.html", "en/knowledge.html", "zh-knowledge.html"}
    t |= {p for p, *_ in CTA_PAGES} | {p for p, _ in CONTACT_PAGES} | set(CRUMB_PAGES) | set(LD_PAGES) | set(PERSON_ADD)
    return sorted(t)


def main() -> int:
    check = "--check" in sys.argv
    need = []
    for rel in targets():
        f = ROOT / rel
        old = f.read_text(encoding="utf-8")
        new = build(rel, old)
        if new != old:
            need.append(rel)
            if not check:
                f.write_text(new, encoding="utf-8")
    verb = "直しが要る" if check else "書いた"
    print(f"{verb}頁 {len(need)}／{len(targets())}: " + " ".join(need))
    return 1 if (check and need) else 0


if __name__ == "__main__":
    sys.exit(main())
