#!/usr/bin/env python3
"""週次自動更新と月1回の構成レビューの安全弁。Claude が作業ツリーに加えた変更を、公開前に機械で検査する。
**自動フロー専用**（weekly_run.sh が呼ぶ）。人が PR で足すコラムはここを通らない。

    python3 scripts/seo/guard_diff.py --manifest <changes.json>     # 検査（0=通す／1=止める）
    python3 scripts/seo/guard_diff.py --manifest <changes.json> --profile structure   # 月1回の構成レビュー

止める理由は全部表示する。通らなければ weekly_run.sh は何も公開しない（作業ツリーを捨てる）。
検査の中身:
  - 触ってよいファイルだけか（HTML・sitemap・header.js の JA_ONLY_COLUMNS 行。変更日台帳はシェルが記帳するので Claude は書かない）
  - 触ってはいけないもの（フォーム・/fund・vercel.json・projects.json・scripts・.github・robots・img・files・削除）
  - **新規ファイルは 0**（O16-3。コラムは中島さんが書く）。新しいページは自動では作らない。
    マニフェストの class=new-column も止める。人が足したコラムの育成（内部リンク・ハブカード・sitemap・JA_ONLY_COLUMNS）は既存ファイルの変更なので通る
  - 量の上限（週次のマニフェストは 8 件まで・既存ページの変更 12 本まで＝O16-36／1ファイルの差し替え率）。差し替え率は行数に加えて **本文の字数** でも測る
    （body_units: <body> の見える文字。コラムは CSS と script が行の大半＝行数だけだと本文を総入れ替えしても 1 割に満たない）。
    週次: 本文の足し＋消し 50% 未満（O16-39＝半分未満。ちょうど半分も止める）・消し 25% まで。ハブ・トップは、マニフェストに無ければ焼き直しの範囲（600 字）まで、
    あっても足せるのは 1500 字まで（記事ぶんの節は足せない）。マニフェストに無いハブ・トップで、焼き直しの所（BAKE_PARTS）をそろえても
    差分が残るもの（焼き直しでない書き換え）は、凍結中なら止める（申告しないだけで凍結を抜けさせない）。焼き直しが書かない
    en/index.html・zh.html と構成レビューは、載っていない書き換えをそのまま止める
  - HTML の入れ子（Nest）: タグの開閉の不一致が変更前より増えていない／id つきの要素・section・footer の入れ子の位置
    （深さと祖先の id）が変わっていない／id つきの要素と節が消えていない（差し戻し class=rollback のファイルだけ消してよい）。
    行の多重集合では、閉じタグを置き去りにした節の移動と、素の並べ替えを区別できない
  - robots の noindex を足さない。ハブ・トップ（HUBS）の <style> と <script>（JSON-LD 以外）は変えない
    （ヒーローの中身が同じでも CSS・JS で消せる）
  - ファイルの削除だけの差分も止める（「変更なし」で通さない）
  - HTML の骨格（title・description・canonical・h1 1つ・header.js・JSON-LD が壊れていない・内部リンク切れ無し）
  - EN は title 70字以内・description 155字以内（Bing の指摘）
  - 禁止語（自称「中立」「neutral」「independent」＝O16-10。シナリオ名の「強気・中立・弱気」・「中立」シナリオ・技術中立・
    neutral scenario・the neutral case・carbon-／climate-／net-／technology-neutral・アンカーの id は自称ではないので止めない。
    引用符でくくっただけの自称・vendor-neutral・a neutral case manager などは止める。「中立」「neutral」はページ全体の出現（同じ行の前後 20 字の文脈）の前後で比べ、新しく現れた分だけ止める＝既存の行を
    動かすだけなら止めない。「一次情報」「一次ソース」＝T06-12・実績の主張＝O16-7・鍵らしき文字列は足した行に掛ける）
  - 非公開の禁止語（O16-7・O16-12。語そのものは公開リポジトリに置けない＝リポジトリの外の一覧
    ~/.config/scix-web/private_banned.tsv から読む。1 行＝正規表現<TAB>規則ID・# で始まる行は読み飛ばす）。足した HTML の行と
    マニフェストの公開される欄に掛ける。止める理由には規則IDとファイル（欄）だけを出し、語も式も出さない（ログ・Telegram・PR に写さない。
    同じ行を写すほかの理由も、その行に当たれば抜粋を出さない。抜粋は、切る前の文と出現を含む行の全体に当ててから写す＝窓の端で
    切れた語の残りも出さない）。一覧が無い・読めない・式が 0 個・壊れた行があるときは止める（黙って通さない）。
    SCIX_WEB_PRIVATE_BANNED は selftest が合成の一覧を指すためのもの（本番の weekly_run.sh は設定しない）
  - 足した本文に IRR・利回り・年利・リターン・手数料（率）・手付・募集（総・金）額・出資額・分配・配当・1口の数字（％・円）を新たに
    書かない（O16-8・O16-66。成功報酬・フィー・英語・中文の yield・return・fee・dividend・minimum investment・subscription・per unit・
    carry・carried interest・hurdle・收益率・回报率・手续费・认购・分红・年化も。「3%の手数料」「a 3% fee」「8% annual return」
    「5% p.a. return」のように数字が先に来る形と「年N%を目指す」も）。行の差分ではなく
    ページ全体の出現の前後で見る＝変更前のページに同じ書き方があれば数えない（既存の文・動かしただけの行・同じ行への書き足しは止めない）
  - 英語・中文のページ（en/・zh-・zh.html）に証券化（GK-TK・securitization・匿名組合・证券化）を新たに書かない（O16-69。数え方は上と同じ）
  - コラム（column-*・en/column-*・zh-column-*）で /fund を指す <a> の本数を増やさない（O16-67。既存のフッターの 1 本は数えるだけ。
    https://scix.co.jp/fund・//www.scix.co.jp/fund・相対の fund.html／../fund・リダイレクト・invest.scix.co.jp（vercel.json の host の
    rewrites に出るホストは、どのパスも自サイト）も site_path でそろえて数える。vercel.json が読めなければ止める）
  - 14 日以内に変えたページは変えない（O16-37・O16-38）。数え方はブリーフ 9 節と同じ build_brief.cooldown_pages(strict=True)
    （REPO の HEAD までのコミット＋変更台帳＝いま検査している未コミットの差分は数えない）。見るのはマニフェストの files（編集した
    ページ）。除くのは、元の commit の逆向きと確かめられた差し戻し（class=rollback。rollback_of が必須＝無ければ止める。
    足した行が元の commit で消えた行・消した行が元の commit で足した行であること。焼き直しの所をそろえるのは焼き直しが書くファイル
    （BAKE_PARTS）だけで、コラムなどは JSON-LD・<!--S:…-->・NEW バッジも比べる。そろえると差分が空なら確かめられない扱い。
    確かめられなければ普通の変更と同じに凍結を当て、節も消させない）と、週次のハブ・トップのカードの追加（class=hub＝O16-38 の例外。
    凍結中なら title・description・<head> は変えさせず、足した行が既存のカードと同じ形のカード＝コラムへのリンク 1 本だけで、
    そのコラムのカードが変更前のハブに無いか（登録漏れの手当て）を確かめる。それ以外が混じれば凍結を当てる）だけ。ハブ・トップでも class=hub 以外（title・description・internal-link…）は凍結を当てる。
    マニフェストに載せずにハブ・トップの title・description・<head> を変えるのも止める（焼き直しは「全N記事」の数字だけ）。
    凍結を確かめられない（台帳が無い・読めない・git の履歴を読めない）ときは止める
  - マニフェスト（何をなぜ変えたか）と実際の差分が一致している。各変更に pages（効果測定に使う URL パス）が要る
  - 公開される欄（コミットの件名と本文・変更日台帳・PR に載る summary_lines・proposal_title・summary・rationale・hypothesis・
    kpi・measure・before・after）に問い合わせの件数を書かない（LEAD_NUMBER_RES。件数は private_note へ＝Drive の台帳だけ）。
    同じ欄に案件ID（SHV-／HV-／UR-／GT- ＋数字）・円の金額（O16-19）と「一次情報」（T06-12）も書かない（本文の HTML には掛けない＝
    公開の案件一覧 projects.json 由来の ID がある）。週次・構成レビューの両方で見る。ただし before・after が公開されるのは構成レビューの
    PR 本文だけ＝週次の before・after には案件ID・金額・「一次情報」の検査を掛けない（件数の検査は掛ける）
  - トップ（index.html・en/index.html・zh.html）のヒーローより上は変えない（<body> の先頭〜<section class="hero"> の終わり）

--profile structure（月1回の構成レビュー＝weekly_run.sh の MODE=structure。**検査を通れば承認なしで公開**＝O16-25。
ナビ（header.js）を含む回だけは全体を PR に出す）で変わるところ:
  - 量: マニフェストは 3 件まで・1ファイルの差し替えは「並べ替えを除いた正味」で測る
    （行を多重集合で比べる。節やカードを動かしただけなら正味 0。正味の書き換え 1/4 まで・正味の削除 15% まで・
      見かけの差し替え（+と−の合計）は 120% まで＝動かした行は両方に数えられる）。本文の字数でも同じ上限（1/4・15%）
  - ハブ・トップ（HUBS）はヒーローより下だけ: <body> の先頭〜ヒーローの終わり（ハブは最初の </h1> まで）が同一、
    title・description・canonical も同一（数字だけの違いは無視＝「全N記事」の焼き直し）、<head> のほかの meta・link も同一
  - ハブ以外のページ（cta-route・funnel-block の対象）は title・description・h1 が同一（本文を書き換えない型）
  - pages は編集したページ（files の URL）だけ。送客先の収益ページは kpi_pages（任意）へ。pages は前後比較の対象と
    「14 日触らないページ」の二役で、GA4 のリードは着地ページに付く＝編集していない収益ページを入れると判定と凍結が狂う
  - <!--S:…--> の内側は並び順を問わず同じ中身であること（節ごと動かすのは可・中身を書き換えるのは不可）
  - header.js: JA_ONLY_COLUMNS の行に加えて **ナビ定義**（GROUP_PAGES 〜 var nav = […];）を変えてよい。ただし
    ナビ定義が変わっていたら「ナビの組み替えは90日に1回まで」を、マニフェストの申告（class=nav のエントリの
    nav_rule.last_nav_change）と、変更台帳＋origin/main の header.js の履歴（structure.nav_rule）とで照合する。
    ナビ定義と JA_ONLY_COLUMNS 以外（CSS・計測・更新メール）は変えられない
  - マニフェストの各変更に pages・hypothesis（仮説）・kpi（何が増えれば成功か）・measure（いつ何で測るか）が要る。
    rationale には根拠の数字が要る。class は hub-order / top-order / cta-route / funnel-block / nav
  - **収益ページ・フォームへの導線を減らさない**: 変更したファイルごとに、href が FUNNEL_TARGETS（/contact・/projects・
    /transfer・/investors・/fund・/sourcing・/land・/sell-form と EN/ZH のフォーム）を指す <a> の本数が、変更前より
    減っていたら止める（行き先の付け替えは可）。人の目が入らない分、「流れを良くする変更が導線を消す」事故を機械で止める
  - マニフェストの changes が 0 件なのに差分がある（焼き直しだけが残っている）なら止める＝中身のない公開をしない
  - 最後に公開の経路を 1 行で出す（「経路: 自動公開」か「経路: PR」）。header.js の変更か class=nav のエントリが
    1 つでもあれば、その回は全体が PR（一部だけ公開、をしない＝検査済みの単位を崩さない）。シェルはこの行と自分の目の両方で決める
  それ以外（触ってはいけないファイル・新規ファイル 0・title・canonical・JSON-LD・リンク切れ・鍵・自称中立・14 日の凍結など）は週次と同じ
  （凍結の数え方は build_brief.cooldown_pages(structure=True)。ハブ・トップも凍結を当てる＝構成系の記帳（hub・hub-order・top-order・
  nav・rollback・source=structure）だけで数えるので、コラムを足しただけの週は凍結されない。ハブ・トップ以外は週次と同じ）。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import argparse
import collections
import difflib
import html.parser
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, file_to_url, path_of  # noqa: E402

REPO = Path(os.environ.get("SCIX_WEB_REPO", Path.cwd()))
ALLOWED_HTML = re.compile(r"^(en/)?[a-z0-9-]+\.html$|^zh-[a-z0-9-]+\.html$")
FORBIDDEN = {"docs/seo-change-log.md", "fund.html", "contact.html", "sell-form.html", "thanks.html", "privacy.html", "404.html",
             "en/contact.html", "en/thanks.html", "zh-contact.html", "zh-thanks.html",
             "projects.json", "vercel.json", "robots.txt", "README.md", "CLAUDE.md"}
FORBIDDEN_PREFIX = ("scripts/", ".github/", "img/", "files/", "notes/", ".claude/", "docs/new-mac-setup.md")
HUBS = {"knowledge.html", "en/knowledge.html", "zh-knowledge.html", "index.html", "en/index.html", "zh.html"}
MAX_EXISTING = 12
MAX_NEW = 0                      # 新規ファイルは週次・構成レビューとも 0（O16-3。コラムを書くのは中島さん）
NO_NEW_PAGE = "新しいページは自動では作らない（コラムは中島さんが書く）"
MAX_WEEKLY_ENTRIES = 8           # 週次のマニフェストは 8 件まで（O16-36。既存ページ 12 本までは MAX_EXISTING）
MAX_REPLACE_RATIO = 0.5          # 週次: 差し替えはこの比率「未満」（O16-39＝本文の半分未満。ちょうど半分も止める）
MAX_DELETE_RATIO = 0.25
# 本文（<body> の見える文字。<style>・<script>・<!--S:…-->・コメントは除く）で測る量。行数で割ると、コラムは CSS と script が
# 行の大半なので本文を 100% 書き換えても 1 割に満たない（2026-09-20 実測）＝「コラムは書かない」の抜け道になる
TEXT_FLOOR = 1200                # 短いページの分母の下限（字）。節を 1 つ足しただけで比率が跳ねないように
HUB_BAKE_CHARS = 600             # 週次: マニフェストに載っていないハブ・トップは、焼き直し（NEW バッジ・件数）の範囲まで
HUB_MAX_ADD_CHARS = 1500         # 週次: ハブ・トップに足せる本文（カード数枚ぶん。記事 1 本ぶんの節は足せない）
HUB_MAX_DELETE_RATIO = 0.10      # 週次: ハブ・トップから消せる本文
CLASSES = {"title", "description", "body", "internal-link", "cta", "rollback", "hub", "faq", "structured-data"}
# 構成レビュー（--profile structure）
STRUCT_CLASSES = {"hub-order", "top-order", "cta-route", "funnel-block", "nav"}
STRUCT_MAX_ENTRIES = 3
STRUCT_MAX_REPLACE_RATIO = 1.2   # 見かけの差し替え（動かした行は + と − の両方に数えられる）
STRUCT_NET_RATIO = 0.25          # 並べ替えを除いた正味の書き換え（足した行＋消した行）
STRUCT_NET_DELETE = 0.15         # 正味の削除
HERO_TOPS = {"index.html", "en/index.html", "zh.html"}
# 収益ページとフォームへの導線（構成レビューでは、変更したファイルごとにこの本数を減らさない）
FUNNEL_TARGETS = {"/contact", "/projects", "/transfer", "/investors", "/fund", "/sourcing", "/land", "/sell-form",
                  "/en/contact", "/zh-contact"}
# コミットの件名と本文・変更日台帳（docs/seo-change-log.md）・PR の題と本文は公開リポジトリに載る（revert しても履歴に残る）。
# 問い合わせ（generate_lead）の件数・用件別は Drive の台帳側だけ＝公開される欄に書かせない。週次・構成レビューの両方で見る。
# 「語の直後に数字」だけでは、ブリーフ自身の言い回し（「問い合わせ（generate_lead）は 28 日で 3 件」「着地リード 前→後 は 2→0」）
# と、数字が先に来る形（「3 件の問い合わせ」）を素通しする（2026-09-20 実測）。止めすぎる側に倒してある＝止まったら private_note へ
_LEAD_WORD = (r"(?:generate_lead|リード(?!タイム)|問い?合わ?せ|引き合い|フォーム送信|送信完了|キーイベント|コンバージョン|intent"
              r"|(?<![A-Za-z])(?:CV|ＣＶ)(?![A-Za-z])|(?<![A-Za-z_])(?:key ?events?|leads?|inquir(?:y|ies)|conversions?)(?![A-Za-z_]))")
_NUM = r"[0-9０-９]+(?![0-9０-９])"
LEAD_NUMBER_RES = [
    # 語の直後に数字（「リード数 9」「intent=3」「リード 6 件」）。日付・順位・率の数字（「リードを 14 日後に」）は除く
    re.compile(_LEAD_WORD + r"(?:件数|数)?\s*[=:＝：はがをも]?\s*" + _NUM + r"(?!\s*(?:日|週|か月|ヶ月|カ月|月|年|位|節|％|%|\.[0-9]))", re.I),
    # 語のあと、同じ文の中に「N 件」「N→」「N から」（括弧・助詞・「前／後」が挟まる形）
    re.compile(_LEAD_WORD + r"[^。\n]{0,24}?" + _NUM + r"\s*(?:件|→|->|⇒|➡|から)", re.I),
    # 数字が先（「3 件の問い合わせ」「3 leads」）
    re.compile(_NUM + r"\s*件\s*[のを]?\s*" + _LEAD_WORD, re.I),
    re.compile(_NUM + r"\s*(?:leads?|inquir(?:y|ies)|conversions?)(?![A-Za-z_])", re.I),
]
PUBLIC_TOP_KEYS = ("proposal_title", "summary_lines")
PUBLIC_ENTRY_KEYS = ("summary", "rationale", "kpi", "measure", "hypothesis", "before", "after")


def lead_number(s) -> bool:
    return any(rx.search(str(s or "")) for rx in LEAD_NUMBER_RES)


ICHIJI_RE = re.compile(r"一次情報|一次ソース|[1１]次情報|[1１]次ソース")
ICHIJI_WHY = "「一次情報」「一次ソース」は書かない（T06-12: 公表資料・原文・原典・出典と書く）"
# O16-10: 自称の「中立」「neutral」を止める。外すのは自称でない決まった書き方だけ: シナリオ名（強気・中立・弱気／「中立：約…」
# 「中立＝…」・表の見出し <th>中立</th>・「中立」シナリオ／"neutral" scenario）、技術中立、carbon-／climate-／net-／technology-neutral、
# アンカーの id（#neutral・id="neutral"）。引用符でくくっただけの自称（当社は「中立」の立場・“neutral” party）と
# vendor-neutral・manufacturer-neutral・EPC-neutral は止める（2026-09-23 の確かめ: ハイフン・引用符を丸ごと外すと自称が素通りした）。
# 既存の行を動かす・手直しするときに止めすぎないよう、ページ全体の出現（前後 20 字の文脈）を前後で比べ、新しく現れた分だけ止める
_SCENARIO_AFTER = r"\s*[」』\"”'’]?\s*(?:シナリオ|ケース|(?i:scenarios?|cases?)\b)"
NEUTRAL_JA_RE = re.compile(r"(?<!技術)(?<!強気・)(?<!強気、)(?<!弱気・)(?<!弱気、)中立(?![＝=：:]|</t[hd]>|" + _SCENARIO_AFTER + ")")
# 英語で外すのは neutral scenario(s) と the neutral case(s) の形だけ（2026-09-23 の確かめ: 「neutral case(s)」を丸ごと外すと
# 「a neutral case manager」の自称が素通りした）。the neutral case でも、後ろに manager などの名詞が続けば自称として止める
_EN_SCENARIO_AFTER = r"[\"”'’]?\s*scenarios?\b"
_EN_CASE_AFTER = (r"[\"”'’]?\s+cases?\b(?![\s‐-]*(?:managers?|management|handl\w*|workers?|officers?|agents?|advis[eo]rs?|brokers?"
                  r"|consultants?|reviewers?|coordinators?)\b)")
NEUTRAL_EN_RE = re.compile(r"(?<!#)(?<!id=\")(?<!id=')(?<!\bcarbon[-‐ ])(?<!\bclimate[-‐ ])(?<!\bnet[-‐ ])(?<!\btechnology[-‐ ])"
                           r"(?:(?<!\bthe\s)(?<!\bthe\s[\"“'‘])\bneutral\b|\bneutral\b(?!" + _EN_CASE_AFTER + r"))"
                           r"(?!\s*" + _EN_SCENARIO_AFTER + ")", re.I)
NEUTRAL_RULES = [(NEUTRAL_JA_RE, "自称「中立」は禁止（O16-10: メーカー・EPCと資本関係がない、と事実で書く）"),
                 (NEUTRAL_EN_RE, "neutral/independent の自称は禁止（O16-10）")]


def _occurrences(rx, t: str, key):
    """rx の出現を key(t, m, 行の頭, 行の終わり) で数えた多重集合と、key ごとの「出現を含む行の全体」（出現が行をまたげば
    またいだ行まで）の一覧。"""
    c, lines = collections.Counter(), {}
    for m in rx.finditer(t):
        ls = t.rfind("\n", 0, m.start()) + 1
        le = t.find("\n", m.end())
        le = le if le >= 0 else len(t)
        k = key(t, m, ls, le)
        c[k] += 1
        lines.setdefault(k, []).append(t[ls:le])
    return c, lines


def new_occurrences(rx, before: str, after: str, key=lambda t, m, ls, le: m.group(0)) -> list:
    """変更後に増えた出現。[(key, その出現を含む行の全体の一覧)]。行の全体は、止める理由に抜粋を写す前に非公開の禁止語を
    当てるためのもの（抜粋の窓で切ると、窓の端にまたがった語の残りが出る＝2026-09-23 の確かめ）。"""
    ca, la = _occurrences(rx, after, key)
    cb, _ = _occurrences(rx, before, key)
    return [(k, la[k]) for k in ca - cb]


def _ctx20(t, m, ls, le):
    return re.sub(r"\s+", " ", t[max(ls, m.start() - 20):min(le, m.end() + 20)]).strip()


def new_contexts(rx, before: str, after: str) -> list:
    """rx の出現を、同じ行の前後 20 字の文脈（空白をそろえる）で数え、変更後に増えた分（[(文脈, 出現を含む行の全体の一覧)]）。
    行を動かす・字下げを変える・同じ行の離れた所を直すだけなら 0。新しく書いた文・出現のすぐ近くの書き換えは数える。"""
    return new_occurrences(rx, before, after, _ctx20)


BAD_WORDS = [(ICHIJI_RE, ICHIJI_WHY),
             # independent power producer（発電事業者）は止めない＝自称に使う名詞が続くときだけ
             (re.compile(r"\bindependent (?:advisor|adviser|broker|party|intermediary|marketplace|platform|firm|company)\b", re.I),
              "neutral/independent の自称は禁止（O16-10）"),
             (re.compile(r"当社の(成約|取引|導入)実績|成約実績|実績多数"), "実績の主張は出さない（O16-7）"),
             (re.compile(r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,}"), "鍵らしき文字列")]

# O16-8・O16-66: IRR・利回り・手数料（率）・手付・募集（総）額・分配・1口の金額をサイトに新たに書かない（英語・中文のページも）。
# 語のあと 16 字以内に数字＋％／円（「手数料は売買価格の N%」「Target yield of N%」「收益率 N%」「募集総額 N億円」「年利 N%」
# 「期待リターン N%」「最低出資額 N万円」「Minimum investment of JPY N million」「分红率 N%」「年化收益 N%」）と、
# 数字＋％が先に来る形（「出資額の N%を分配」「an N% IRR」「N%の手数料」「a N% fee」「N% management fee」「N% annual return」）。
# 既存のコラムには公表資料の数字（制度の想定 IRR・市場の利回りなど）がある＝ページ全体の出現の前後で比べ、増えた分だけ止める
# 成功報酬・フィー・carry・carried interest・hurdle も（2026-09-23 の確かめ #64 の言い換え）。フィーはフィード（FIP＝フィードイン
# プレミアム）・フィールド・フィーリングを除く。carry は「carry of／at／:」の形だけ（「lines carry 5% of flows」は拾わない）
_FUND_WORD = (r"(?:IRR|利回り|年利|リターン|手数料|成功報酬|フィー(?![ドダルリ])|手付|募集(?:総|金)?額|出資(?:金)?額|[1１一]口|分配|配当"
              r"|收益率|回报率|回報率|手续费|手續費|认购|認購|分红|分紅|年化"
              r"|(?i:\b(?:yields?|returns?|fees?|subscriptions?|per[ -]unit|dividends?|minimum investment|carried interest"
              r"|hurdle(?: rates?)?)\b)"
              r"|(?i:\bcarry\b)(?=\s*(?:(?i:of|at)\b|[:=(（])))")
_FUND_AMOUNT = (r"(?:[0-9０-９][0-9０-９,.]*\s*(?:％|%|万円|億円|円|万日元|亿日元|日元|(?i:(?:million |billion )?(?:yen|JPY)\b))"
                r"|(?:[¥￥]|(?i:JPY|yen)\s*)[0-9０-９][0-9０-９,.]*)")
# 数字＋％のあと（「の」「を」と英語の語 2 つまでを挟んでよい。p.a. のように「.」を含む語も）に来る語
_FUND_AFTER_PCT = (r"(?:分配|配当|利回り|手数料|成功報酬|フィー(?![ドダルリ])|リターン"
                   r"|(?i:yields?|returns?|fees?|IRR|dividends?|carried interest|carry|hurdle)\b)")
# 「年N%を目指す」（年率の目標＝利回りの言い換え）
_FUND_ANNUAL_TARGET = (r"年率?\s*[0-9０-９][0-9０-９,.]*\s*(?:％|%)\s*(?:程度|前後|以上|超)?\s*(?:を|の)?\s*"
                       r"(?:目指|めざ|目標|狙|ねら|確保)")
FUND_NUM_RE = re.compile(_FUND_WORD + r"[^。\n]{0,16}?" + _FUND_AMOUNT
                         + r"|[0-9０-９][0-9０-９,.]*\s*(?:％|%)\s*(?:を|の)?\s*(?:(?i:[a-z][a-z.]*)\s+){0,2}" + _FUND_AFTER_PCT
                         + r"|" + _FUND_ANNUAL_TARGET)
FUND_NUM_WHY = "サイトに IRR・利回り・リターン・手数料率・募集額・出資額・分配・1口金額を新たに書かない（O16-8・O16-66）"
# O16-69: 英語・中文のページには証券化（GK-TK）を載せない。ページ全体の出現の前後で比べ、増えた分だけ止める
# （既存の EN/ZH コラムに触れている文がある＝動かす・手直しするだけなら止めない）
SECURITIZATION_RE = re.compile(r"(?i:securiti[sz]\w*|GK\s*[-‐‑–−/・]?\s*TK(?![A-Za-z])|tokumei[- ]?kumiai)|TK出[資资]|[証证證]券化|匿名[組组]合")
SECURITIZATION_WHY = "英語・中文のページには証券化（GK-TK）を載せない（O16-69）"
# O16-67: コラムから /fund へ導線を張らない。コラム（JA・EN・ZH）で /fund を指す <a> の本数が増えたら止める
# （既存のコラムはフッターに /fund を 1 本ずつ持つ＝減らす・動かすのは止めない）
COLUMN_FILE_RE = re.compile(r"^(?:en/)?column-[a-z0-9-]+\.html$|^zh-column-[a-z0-9-]+\.html$")
FUND_LINK_WHY = "コラムから /fund へ導線を張らない（O16-67）"


def en_zh_page(path: str) -> bool:
    return path.startswith(("en/", "zh-")) or path == "zh.html"
# O16-19: 公開される欄（コミット・PR・変更日台帳）に案件ID・金額を写さない。本文の HTML には掛けない（公開の案件一覧
# projects.json 由来の ID がある）。\b は日本語の文字も語の文字に数える（「案件」の直後・「の」の直前で外れる）＝前後は英数字だけで切る
DEAL_ID_RE = re.compile(r"(?<![A-Za-z0-9])(?:SHV|HV|UR|GT)[-－][0-9０-９]{2,4}(?![0-9０-９])")
YEN_RE = re.compile(r"[0-9０-９][0-9０-９,.]*\s*[千万億兆]*\s*円|[¥￥]\s*[0-9０-９]|\bJPY\s*[0-9]"
                    r"|[0-9][0-9,.]*\s*(?:(?:million|billion|bn)\s*)?(?:yen|JPY)\b", re.I)
PUBLIC_ID_WHY = "コミット・PR・変更日台帳に案件ID・金額を写さない（O16-19）"


def public_text_problems(label: str, v) -> list:
    """公開される欄 1 つ分（問い合わせの件数 lead_number は呼ぶ側で見る）。案件ID・金額（O16-19）と「一次情報」（T06-12）。"""
    s = str(v or "")
    out = []
    if DEAL_ID_RE.search(s) or YEN_RE.search(s):
        out.append(f"{label}: {PUBLIC_ID_WHY}")
    if ICHIJI_RE.search(s):
        out.append(f"{label}: {ICHIJI_WHY}")
    return out


# O16-7・O16-12: 語そのものを公開リポジトリに書けない禁止語（O16-7・O16-12 が名指しする語。規則の本文は共通ルールにある）は、
# リポジトリの外の一覧から読む。止める理由には規則IDとファイル（欄）だけを出す＝語も式も、ログ・Telegram・PR 本文に写さない。
# 一覧が読めないときは止める（公開しない側に倒す）。SCIX_WEB_PRIVATE_BANNED は selftest が合成の一覧を指すためだけのもの
PRIVATE_BANNED_ENV = "SCIX_WEB_PRIVATE_BANNED"
PRIVATE_BANNED_DEFAULT = Path.home() / ".config" / "scix-web" / "private_banned.tsv"
PRIVATE_BANNED_UNREADABLE = "非公開の禁止語一覧が読めないので止める（O16-7・O16-12）"
PRIVATE_HIDDEN = "（非公開の禁止語に当たるので抜粋は出さない）"


def load_private_banned():
    """(式の一覧, 一覧の呼び名, 止める理由) を返す。式の一覧は [(compiled, 規則ID)]。理由には語も式も入れない（行番号と規則IDまで）。"""
    override = os.environ.get(PRIVATE_BANNED_ENV)
    label = f"{PRIVATE_BANNED_ENV} の一覧" if override else "~/.config/scix-web/private_banned.tsv"
    try:
        lines = Path(override or PRIVATE_BANNED_DEFAULT).read_text(encoding="utf-8-sig").splitlines()
    except Exception:  # noqa: BLE001 — 無い・権限が無い・UTF-8 でない。どれも止める
        return [], label, PRIVATE_BANNED_UNREADABLE
    pats = []
    for n, raw in enumerate(lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        rx, _, rid = raw.partition("\t")
        rid = rid.strip()
        if not rx or not rid:
            return [], label, f"{PRIVATE_BANNED_UNREADABLE}: {n} 行目が「正規表現<TAB>規則ID」になっていない（{label}）"
        try:
            pats.append((re.compile(rx), rid))
        except re.error:
            return [], label, f"{PRIVATE_BANNED_UNREADABLE}: {n} 行目（{rid}）の式が壊れている（{label}）"
    if not pats:
        return [], label, f"{PRIVATE_BANNED_UNREADABLE}: 式が 1 つも無い（{label}）"
    return pats, label, None


def private_hits(s, pats) -> list:
    """当たった規則IDだけを返す（語も式も返さない）。実体参照で書いた語も拾う。"""
    s = str(s or "")
    u = html.unescape(s)
    return sorted({rid for rx, rid in pats if rx.search(s) or rx.search(u)})


def shown(s, n: int, pats, whole=()) -> str:
    """止める理由に写す抜粋（先頭 n 字）。非公開の禁止語は、切る前の s の全体と、抜粋を取った元の行の全体（whole）に当て、
    どれかに当たれば抜粋を写さない（抜粋の端で語が切れると、式に当たらない語の残りが出る）。"""
    s = str(s or "")
    return PRIVATE_HIDDEN if private_hits(s, pats) or any(private_hits(w, pats) for w in whole) else s[:n]


# 毎朝の案件一覧の同期（scripts/inject_stats.py）が書く場所。週次がここを書き換えても翌朝に黙って戻るか、
# 静的一覧と JS の文言がずれたまま残る。projects.html の一覧を描く JS も同じ理由で週次の対象外。
SYNCED_RE = re.compile(r"<!--S:([a-z]+)-->(.*?)<!--/S:\1-->", re.S)
PAGE_JS_RE = re.compile(r"<script(?![^>]*ld\+json)[^>]*>(.*?)</script>", re.S)


# scripts/inject_stats.py の compute() が返すキーと同じ集合。ナレッジ側の kcount/kdate/knew は
# 週次シェル自身が検査の直前に gen_knowledge_jsonld.py --write で焼き直すので対象にしない。
INJECT_KEYS = {"list", "count", "mw", "prefs", "areas", "shv", "maxmw", "date", "pjnew"}


def synced_regions(text: str) -> list:
    return [(m.group(1), m.group(2)) for m in SYNCED_RE.finditer(text) if m.group(1) in INJECT_KEYS]


def hero_region(text: str):
    """<body> の先頭からヒーローの終わりまで。トップ＝<section class="hero">…</section>、それ以外（ハブ）＝最初の </h1>。
    <!--S:…--> の中身は同期・焼き直しが書くので空にして比べる。取れなければ None。"""
    b = text.find("<body")
    if b < 0:
        return None
    m = re.search(r'<section\b[^>]*class="hero"', text[b:])
    if m:
        end = text.find("</section>", b + m.start())
        end = end + len("</section>") if end >= 0 else -1
    else:
        end = text.find("</h1>", b)
        end = end + len("</h1>") if end >= 0 else -1
    if end < 0:
        return None
    return SYNCED_RE.sub(lambda x: f"<!--S:{x.group(1)}--><!--/S:{x.group(1)}-->", text[b:end])


def net_change(before: str, after: str):
    """並べ替えを除いた正味の変更。(足した行, 消した行, 元の行数)。空行は数えない。"""
    b = collections.Counter(l.strip() for l in before.splitlines() if l.strip())
    a = collections.Counter(l.strip() for l in after.splitlines() if l.strip())
    return sum((a - b).values()), sum((b - a).values()), max(1, sum(b.values()))


_INLINE_TAGS = ("a|span|strong|em|b|i|u|s|code|sup|sub|small|mark|abbr|time|cite|q|wbr|ruby|rt|rp|kbd|var|bdi|bdo|data|dfn|"
                "samp|ins|del|font|br")
_HIDDEN_RE = re.compile(r"<(script|style|svg|noscript|template)\b.*?</\1\s*>", re.S | re.I)
_ANY_S_RE = re.compile(r"<!--S:([a-z]+)-->.*?<!--/S:\1-->", re.S)


def body_units(text: str) -> collections.Counter:
    """本文の単位（文）の多重集合。<body> の見える文字だけ: <style>・<script>・SVG・コメント・<!--S:…-->（同期と焼き直しが
    書く所）は除く。インラインのタグ（a・span・strong…）は外してつなげ、ほかのタグと「。」で切る＝本文中にリンクを 1 本
    足しただけの文は変わらない。多重集合で比べるので、節やカードを動かしただけなら差は 0。"""
    b = text.find("<body")
    body = text[b:] if b >= 0 else text
    body = _HIDDEN_RE.sub("\n", body)
    body = _ANY_S_RE.sub("\n", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"</?(?:%s)\b[^>]*>" % _INLINE_TAGS, "", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "\n", body)
    units = collections.Counter()
    for line in html.unescape(body).splitlines():
        for s in re.split(r"(?<=[。．！？!?])|(?<=\.)\s+", line):
            s = re.sub(r"\s+", " ", s).strip()
            if s:
                units[s] += 1
    return units


def text_change(before: str, after: str):
    """本文の正味の変更（字数）。(足した字数, 消した字数, 元の字数)。書き換えた文は消した＋足したの両方に数える。"""
    b, a = body_units(before), body_units(after)

    def chars(c):
        return sum(len(k) * n for k, n in c.items())
    return chars(a - b), chars(b - a), max(1, chars(b))


_LD_RE = re.compile(r"<script\b[^>]*application/ld\+json[^>]*>.*?</script>", re.S | re.I)
_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)


def styles_and_scripts(text: str):
    """ページの <style> と <script>（JSON-LD 以外）の中身。ヒーローの中身が同じでも、CSS（.hero{display:none}）や JS で
    消せてしまうので、ハブ・トップではここも変えさせない。"""
    return _STYLE_RE.findall(text), PAGE_JS_RE.findall(text)


def head_rest(text: str):
    """<head> から <style>・<script>（JSON-LD を含む）を抜き、<!--S:…--> の中身を空にして数字を N にしたもの
    （「全N記事」の焼き直しは無視する）。robots・canonical・hreflang・og などの meta と link が残る。取れなければ None。"""
    a, b = text.find("<head"), text.find("</head>")
    if a < 0 or b < 0:
        return None
    h = re.sub(r"<script\b.*?</script>", "", _STYLE_RE.sub("", text[a:b]), flags=re.S | re.I)
    h = _ANY_S_RE.sub(lambda m: f"<!--S:{m.group(1)}--><!--/S:{m.group(1)}-->", h)
    return re.sub(r"[0-9０-９]+", "N", "\n".join(l.strip() for l in h.splitlines() if l.strip()))


_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
# 閉じタグを省いてよい要素（HTML の仕様）。親の閉じタグで黙って閉じる＝不一致に数えない
_IMPLIED_END = {"p", "li", "dt", "dd", "tr", "td", "th", "thead", "tbody", "tfoot", "option", "optgroup", "colgroup", "caption"}
_CLOSES_P = {"address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset", "figcaption", "figure", "footer",
             "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "menu", "nav", "ol", "p", "pre", "section",
             "table", "ul"}
_LANDMARKS = {"section", "article", "main", "footer", "header", "nav", "aside"}


class Nest(html.parser.HTMLParser):
    """タグの開閉の対応と、目印になる要素（id つきの要素・section／footer／main など）の入れ子の位置。
    行の多重集合では、閉じタグを置き去りにした節の移動（以降の節が全部その節の子になる）と、素の並べ替えとを区別できない。"""

    def __init__(self):
        super().__init__()
        self.stack = []                          # [(tag, id)]
        self.mismatch = 0                        # 相手のいない閉じタグ＋閉じタグに飛ばされた開きタグ＋a の中の a
        self.ids = {}                            # id → [(tag, 深さ, 祖先の id の列)]
        self.landmarks = collections.Counter()   # id の無い section／footer／… の (tag, 深さ, 祖先の id の列)

    def _pop_while(self, tags):
        while self.stack and self.stack[-1][0] in tags:
            self.stack.pop()

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            return
        if tag in _CLOSES_P:
            self._pop_while({"p"})
        if tag == "li":
            self._pop_while({"p", "li"})
        elif tag in ("dt", "dd"):
            self._pop_while({"p", "dt", "dd"})
        elif tag in ("td", "th"):
            self._pop_while({"p", "td", "th"})
        elif tag == "tr":
            self._pop_while({"p", "td", "th", "tr"})
        elif tag in ("thead", "tbody", "tfoot"):
            self._pop_while({"p", "td", "th", "tr", "thead", "tbody", "tfoot", "caption", "colgroup"})
        elif tag in ("option", "optgroup"):
            self._pop_while({"option"} | ({"optgroup"} if tag == "optgroup" else set()))
        elif tag == "a" and any(t == "a" for t, _ in self.stack):
            self.mismatch += 1                   # a の中に a（カードの閉じタグを置き去りにした移動）
        eid = dict(attrs).get("id")
        where = (tag, len(self.stack), tuple(i for _, i in self.stack if i))
        if eid:
            self.ids.setdefault(eid, []).append(where)
        elif tag in _LANDMARKS:
            self.landmarks[where] += 1
        self.stack.append((tag, eid))

    def handle_startendtag(self, tag, attrs):    # <path … /> など。開いて閉じるので積まない
        eid = dict(attrs).get("id")
        if eid:
            self.ids.setdefault(eid, []).append((tag, len(self.stack), tuple(i for _, i in self.stack if i)))

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.mismatch += sum(1 for t, _ in self.stack[i + 1:] if t not in _IMPLIED_END)
                del self.stack[i:]
                return
        self.mismatch += 1

    def broken(self) -> int:
        return self.mismatch + sum(1 for t, _ in self.stack if t not in _IMPLIED_END and t not in ("html", "body"))


def nesting_problems(path: str, before: str, after: str, allow_removal: bool) -> list:
    """HTML の入れ子が変更前より壊れていないか。allow_removal＝差し戻し（class=rollback）のファイル＝足した節を消してよい。"""
    nb, na = Nest(), Nest()
    nb.feed(before); nb.close(); na.feed(after); na.close()
    out = []
    if na.broken() > nb.broken():
        out.append(f"{path}: タグの開閉が合わない箇所が増えた（{nb.broken()} → {na.broken()}）＝閉じタグの置き去り・取りすぎ。"
                   "動かす塊は開きタグから閉じタグまで丸ごと切り取って貼る")
    moved = [f"#{i}（深さ {sorted(nb.ids[i])[0][1]}→{sorted(na.ids[i])[0][1]}"
             + (f"・#{sorted(na.ids[i])[0][2][-1]} の中" if sorted(na.ids[i])[0][2] else "") + "）"
             for i in nb.ids if i in na.ids and len(nb.ids[i]) == len(na.ids[i])
             and sorted(x[1:] for x in nb.ids[i]) != sorted(x[1:] for x in na.ids[i])]
    if moved:
        out.append(f"{path}: id つきの要素の入れ子の位置が変わった: {'・'.join(moved[:6])}{'…' if len(moved) > 6 else ''}"
                   "＝別の節の中に入り込んでいる（閉じタグの置き去りの疑い）。節・カテゴリは同じ親の中で動かす")
    if not allow_removal:
        lost = [i for i in nb.ids if i not in na.ids]
        if lost:
            out.append(f"{path}: id つきの要素が消えた: {'・'.join('#' + i for i in lost[:8])}"
                       "（節は消さない・アンカーの id は変えない＝ナビとトップから張られている）")
        gone = nb.landmarks - na.landmarks
        if gone:
            out.append(f"{path}: 節（{'・'.join(sorted({t for t, _, _ in gone}))}）が消えたか、入れ子の位置が変わった"
                       f"（{sum(gone.values())} 個）。節は消さない・同じ親の中で動かす")
    return out


def same_but_digits(x, y) -> bool:
    return re.sub(r"[0-9０-９]+", "N", (x or "").strip()) == re.sub(r"[0-9０-９]+", "N", (y or "").strip())


SITE_HOSTS = {"www.scix.co.jp", "scix.co.jp"}


VERCEL_UNREADABLE = ("vercel.json を読めないので止める（リダイレクトと invest.scix.co.jp 経由の /fund を数えられない＝"
                     "O16-67 の数え方が甘くなる）")


def vercel_routes():
    """vercel.json の redirects（source → destination）と、ホストで振り分ける rewrites（(ホスト, source) → destination。
    invest.scix.co.jp の / → /fund）。読めなければ None（呼ぶ側が止める。空で続けるとリダイレクトと invest 経由の /fund を
    数えなくなる＝甘くなる側）。"""
    try:
        v = json.loads((REPO / "vercel.json").read_text(encoding="utf-8"))
        if not isinstance(v, dict):
            raise ValueError("vercel.json がオブジェクトでない")
    except Exception:  # noqa: BLE001
        return None
    red = {r["source"]: r["destination"] for r in v.get("redirects") or []
           if isinstance(r, dict) and isinstance(r.get("source"), str) and isinstance(r.get("destination"), str)}
    host = {}
    for r in v.get("rewrites") or []:
        if not isinstance(r, dict) or not isinstance(r.get("destination"), str):
            continue
        for h in r.get("has") or []:
            if isinstance(h, dict) and h.get("type") == "host" and h.get("value"):
                host[(str(h["value"]).lower(), r.get("source"))] = r["destination"]
    return red, host


def _clean_path(p: str) -> str:
    if p.endswith(".html"):
        p = p[:-5]
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p or "/"


def site_path(href: str, page_url: str = BASE + "/", routes=None):
    """自サイトを指す href を URL パス（.html・末尾の / を外す）に。www の有無・http・//・相対（fund.html・../fund）・?query・#hash を
    そろえ、vercel.json の redirects とホストの rewrites（invest.scix.co.jp → /fund）も 1 段たどる。外のサイト・mailto などは None。
    vercel.json の host の rewrites に出てくるホスト（invest.scix.co.jp）は同じデプロイ＝自サイトとして数え、rewrite の無いパス
    （/fund・/fund.html）もそのまま同じパスに読む（2026-09-23 の確かめ: invest.scix.co.jp/fund が外部扱いで 0 本だった）。
    common.path_of は https://www.scix.co.jp の形しかそろえない（2026-09-23 の確かめ: https://scix.co.jp/fund・//www…・相対が 0 本だった）。"""
    try:
        u = urllib.parse.urlsplit(urllib.parse.urljoin(page_url, (href or "").strip()))
    except ValueError:
        return None
    if u.scheme not in ("http", "https"):
        return None
    red, rw = routes if routes is not None else ({}, {})
    host, p = (u.hostname or "").lower(), u.path or "/"
    if (host, p) in rw:
        p = rw[(host, p)]
    elif host not in SITE_HOSTS and host not in {h for h, _ in rw}:
        return None
    p = _clean_path(p)
    return _clean_path(red.get(p, p))


def funnel_links(text: str, page_url: str = BASE + "/", routes=None) -> collections.Counter:
    """収益ページ・フォーム（FUNNEL_TARGETS）を指す <a href> の本数（行き先別）。自サイトの書き方（絶対 URL の www の有無・//・相対・
    ?query・#hash・.html・末尾の /・リダイレクト）は site_path でそろえてから数える。page_url は相対リンクの基準（そのページの URL）。
    コメントアウトした <a> は数えない（＝消したのと同じ扱い）。"""
    pg = Page(); pg.feed(text)
    c = collections.Counter()
    for href in pg.links:
        p = site_path(href, page_url, routes)
        if p in FUNNEL_TARGETS:
            c[p] += 1
    return c


def pr_route(entries: list, changed: list) -> bool:
    """構成レビューの公開の経路。ナビ（header.js）は全ページに効くので自動公開しない＝header.js の差分か、
    class=nav／files に header.js のエントリが 1 つでもあれば、その回は全体を PR に出す。"""
    return "header.js" in changed or any(
        e.get("class") == "nav" or "header.js" in (e.get("files") or []) for e in entries if isinstance(e, dict))


def check_header_js(profile: str, entries: list, problems: list, pats=()) -> None:
    """header.js。週次＝JA_ONLY_COLUMNS の行だけ。構成レビュー＝加えてナビ定義（90日ルールを台帳と照合）。
    pats＝非公開の禁止語（行の抜粋を写す前に、切る前の行の全体に当てる）。"""
    if profile != "structure":
        diff = sh("git", "diff", "--", "header.js")
        for line in diff.splitlines():
            if line.startswith(("+++", "---", "@@", "diff", "index")):
                continue
            if line.startswith(("+", "-")) and not re.match(r"^[+-]\s*'/column-[a-z0-9-]+',?\s*$", line):
                problems.append(f"header.js は JA_ONLY_COLUMNS の行しか変えられない: {shown(line, 80, pats)}")
        return
    import structure as st
    before = sh("git", "show", "HEAD:header.js")
    after = (REPO / "header.js").read_text(encoding="utf-8")
    nb, na = st.nav_block(before), st.nav_block(after)
    if nb is None or na is None:
        problems.append("header.js: ナビ定義（var GROUP_PAGES 〜 var nav = […];）を見つけられない＝検査できないので止める")
        return
    if st.header_without_nav(before) != st.header_without_nav(after):
        problems.append("header.js はナビ定義と JA_ONLY_COLUMNS 以外（CSS・計測・更新メール・言語切替）を変えられない")
    m = st.JA_ONLY_RE.search(after)
    for line in (m.group(2).splitlines() if m else []):
        if line.strip() and not re.match(r"^\s*'/column-[a-z0-9-]+',?\s*$", line):
            problems.append(f"header.js: JA_ONLY_COLUMNS の行の形が想定外: {shown(line.strip(), 60, pats)}")
    if nb == na:
        return
    # ナビ定義が変わった → 90日ルール。申告（マニフェスト）と実績（変更台帳＋origin/main の履歴）の両方が要る
    navs = [e for e in entries if e.get("class") == "nav" and "header.js" in (e.get("files") or [])]
    if not navs:
        problems.append("header.js のナビ定義が変わっているのに、マニフェストに class=nav（files に header.js）のエントリが無い")
    rule = st.nav_rule(cwd=REPO)
    if rule["last"]:
        problems.append(f"ナビの組み替えは {st.NAV_FREEZE_DAYS} 日に1回まで: 直近のナビ変更は {rule['last']}"
                        f"（{rule['days_since']} 日前・{rule['changes'][0]['source']} {rule['changes'][0]['ref']}）。"
                        f"次に提案してよいのは {rule['next_ok']} 以降")
    for e in navs:
        decl = e.get("nav_rule")
        if not isinstance(decl, dict) or "last_nav_change" not in decl:
            problems.append("class=nav のエントリに nav_rule.last_nav_change の申告が無い（直近90日にナビ変更が無ければ null）")
        elif decl.get("last_nav_change") != rule["last"]:
            problems.append(f"ナビ変更の申告が台帳と合わない: 申告 {decl.get('last_nav_change')}／台帳・履歴 {rule['last']}")


def sh(*args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout


# 週次のシェルが検査の前に回す焼き直し（scripts/gen_knowledge_jsonld.py --write）が書くファイルと、そのファイルで書く所。
# ld＝ナレッジのハブの ItemList（<!-- scix-knowledge-jsonld --> の JSON-LD 2 つ）・s＝<!--S:kcount／kdate／knew--> の中身・
# new＝カードの NEW バッジ（.is-new と <span class="new">）・count＝<head> の「全N記事」
BAKE_PARTS = {"knowledge.html": {"ld", "s", "new", "count"}, "en/knowledge.html": {"ld"}, "zh-knowledge.html": {"ld"},
              "index.html": {"s"}}
_BAKE_LD_RE = re.compile(r"<!-- scix-knowledge-jsonld -->.*?</script>\s*<script type=\"application/ld\+json\">.*?</script>", re.S)
_BAKE_S_RE = re.compile(r"<!--S:(kcount|kdate|knew)-->.*?<!--/S:\1-->", re.S)
BAKE_WHAT = "焼き直しの所（ハブの ItemList・<!--S:kcount／kdate／knew-->・NEW バッジ・全N記事）"


def _bake_norm_lines(text: str, path: str) -> list:
    """差し戻しの照合と、凍結中のハブ・トップのカードの検査に使う行の列。焼き直しが書くファイル（BAKE_PARTS）では、焼き直しが
    書く所だけそろえる。ほかのファイル（コラムなど）はそろえない＝JSON-LD・<!--S:…-->・NEW バッジの書き換えも差分に数える
    （2026-09-23 の確かめ: どのファイルでも JSON-LD をそろえていたので、JSON-LD だけの書き換えが差分 0＝「確かめられた差し戻し」になった）。
    空行は数えない（前後の空白は削る）。"""
    parts, t = BAKE_PARTS.get(path, set()), text
    if "ld" in parts:
        t = _BAKE_LD_RE.sub("<!-- scix-knowledge-jsonld -->", t)
    if "s" in parts:
        t = _BAKE_S_RE.sub(lambda m: f"<!--S:{m.group(1)}--><!--/S:{m.group(1)}-->", t)
    if "new" in parts:
        t = t.replace('<span class="new">NEW</span>', "").replace(" is-new", "")
    if "count" in parts:
        t = re.sub(r"全[0-9０-９]+記事", "全N記事", t)
    return [l.strip() for l in t.splitlines() if l.strip()]


def _plus_minus(a: list, b: list):
    """行の列 a → b の差分（並びも見る）。(足した行の多重集合, 消した行の多重集合)。動かした塊は両方に入る。"""
    plus, minus = collections.Counter(), collections.Counter()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            minus.update(a[i1:i2])
        if op in ("replace", "insert"):
            plus.update(b[j1:j2])
    return plus, minus


def rollback_unverified(sha, path: str, before: str, after: str):
    """差し戻し（class=rollback）が、元の commit（rollback_of）の逆向きの差分かを確かめる。確かめられたら None、
    だめなら理由（止める理由の文に添える）。足した行が元の commit で消えた行であり、消した行が元の commit で足した行であること
    （焼き直しの差・並べ替えも同じ物差しで比べる）。焼き直しの所をそろえると差分が空になる（焼き直しの所しか変えていない）ときも
    確かめられない扱い＝何も戻していない。確かめられないファイルは普通の変更として 14 日の凍結を当て、節も消させない。"""
    sha = str(sha or "").strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return "rollback_of に戻す元の commit（SHA）が無い"
    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", sha + "^{commit}"], cwd=REPO, capture_output=True, text=True)
    full = r.stdout.strip()
    if r.returncode != 0 or not full:
        return f"rollback_of の commit {sha} が見つからない"
    if subprocess.run(["git", "merge-base", "--is-ancestor", full, "HEAD"], cwd=REPO, capture_output=True).returncode != 0:
        return f"rollback_of の commit {sha} が HEAD の履歴に無い"
    new = subprocess.run(["git", "show", f"{full}:{path}"], cwd=REPO, capture_output=True, text=True)
    old = subprocess.run(["git", "show", f"{full}^:{path}"], cwd=REPO, capture_output=True, text=True)
    if new.returncode != 0:
        return f"commit {sha} に {path} が無い"
    o_old, o_new = _bake_norm_lines(old.stdout if old.returncode == 0 else "", path), _bake_norm_lines(new.stdout, path)
    if o_old == o_new:
        return f"commit {sha} は {path} を変えていない"
    o_plus, o_minus = _plus_minus(o_old, o_new)
    plus, minus = _plus_minus(_bake_norm_lines(before, path), _bake_norm_lines(after, path))
    if not (plus or minus):
        return f"{BAKE_WHAT}と前後の空白のほかに差分が無い＝commit {sha} の逆向きと確かめられない（何も戻していない）"
    extra_plus, extra_minus = plus - o_minus, minus - o_plus
    if extra_plus or extra_minus:
        return (f"commit {sha} の逆向きの差分と確かめられない（元の commit で消えていない行を {sum(extra_plus.values())} 行足した・"
                f"元の commit で足していない行を {sum(extra_minus.values())} 行消した）")
    return None


COLUMN_PATH_RE = re.compile(r"^/(?:en/)?column-[a-z0-9-]+$|^/zh-column-[a-z0-9-]+$")
_A_SPAN_RE = re.compile(r"<a\b[^>]*>.*?</a\s*>", re.S | re.I)


class _Shape(html.parser.HTMLParser):
    """要素の形: 開きタグの列（タグ名・class・href と class 以外の属性の名前）と、<a> の href。文字の中身は見ない。"""

    def __init__(self):
        super().__init__()
        self.tags, self.hrefs = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a.get("class") or "", tuple(sorted(k for k in a if k not in ("href", "class")))))
        if tag == "a":
            self.hrefs.append(a.get("href") or "")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def card_shape(span: str):
    """<a class=…>…</a> がカードなら形（開きタグの列）を、でなければ None。カード＝class つきの <a> の中に要素があり、<a> は
    それ 1 本だけ（中にリンクを入れない）で、行き先がコラム（/column-…・/en/column-…・/zh-column-…）。"""
    p = _Shape(); p.feed(span); p.close()
    if len(p.hrefs) != 1 or len(p.tags) < 2 or p.tags[0][0] != "a" or not p.tags[0][1]:
        return None
    return tuple(p.tags) if COLUMN_PATH_RE.match(site_path(p.hrefs[0]) or "") else None


def _card_column(span: str):
    """カード（card_shape が形を返す <a>）の行き先のコラムの URL パス。"""
    p = _Shape(); p.feed(span); p.close()
    return site_path(p.hrefs[0]) if p.hrefs else None


def card_only_change(path: str, before: str, after: str) -> bool:
    """週次の class=hub（O16-38 の例外＝カードの登録漏れの手当て）か。焼き直しの所（BAKE_PARTS）をそろえたうえで、変更前の
    ページにあるカードと同じ形のカード（コラムへのリンク 1 本）を足しただけで、足したカードを抜くと変更前と同じ行の列に戻ること。
    足したカードの行き先のコラムは、変更前のハブのカードに無いこと（1 本のコラムに 1 枚まで。既にカードのあるコラムの複製に
    宣伝文を書いて足すのは登録漏れの手当てではない＝2026-09-23 の確かめ）。
    焼き直しだけ（そろえると差分なし）も True。段落・見出し・カードでないリンク・消した行・書き換えた行があれば False。"""
    b = _bake_norm_lines(before, path)
    a = "\n".join(_bake_norm_lines(after, path))
    if a.splitlines() == b:
        return True
    bt = "\n".join(b)
    before_cards = [s for s in _A_SPAN_RE.findall(bt) if card_shape(s)]
    shapes = {card_shape(s) for s in before_cards}
    carded = {_card_column(s) for s in before_cards}
    added = collections.Counter(_A_SPAN_RE.findall(a)) - collections.Counter(_A_SPAN_RE.findall(bt))
    if not added or not shapes:
        return False
    for span, n in added.items():
        col = _card_column(span)
        if card_shape(span) not in shapes or n != 1 or not col or col in carded:
            return False
        carded.add(col)   # 同じコラムのカードを 2 枚足すのも止める
        a = a.replace(span, "", n)
    return [l.strip() for l in a.splitlines() if l.strip()] == b


def head_changed(before: str, after: str) -> bool:
    """title・description・canonical（数字だけの違いは無視＝「全N記事」の焼き直し）と、<head> のほかの meta・link が変わったか。"""
    pb, pa = Page(), Page()
    pb.feed(before); pa.feed(after)
    same = (same_but_digits(pb.title, pa.title) and same_but_digits(pb.desc, pa.desc) and pb.canonical == pa.canonical)
    return not same or head_rest(before) is None or head_rest(before) != head_rest(after)


def unlisted_hub_edits(changed: list, listed: set) -> list:
    """マニフェストの files に無いのに、焼き直しの所（BAKE_PARTS）をそろえても差分が残るハブ・トップ＝焼き直しでない書き換え。
    焼き直しが書かないファイル（en/index.html・zh.html）は、どんな差分でもここに入る。"""
    out = []
    for f in changed:
        if f in HUBS and f not in listed:
            before, after = sh("git", "show", f"HEAD:{f}"), (REPO / f).read_text(encoding="utf-8", errors="replace")
            if _bake_norm_lines(before, f) != _bake_norm_lines(after, f):
                out.append(f)
    return out


def cooldown_problems(entries: list, changed: list, structure: bool, rollback_why: dict, unlisted=()) -> list:
    """O16-37・O16-38: 14 日以内に変えたページ（ブリーフ 9 節「今週触らないページ」）は変えない。
    数え方は build_brief.cooldown_pages() と同じ（REPO の HEAD までのコミット＋変更台帳）。いま検査している未コミットの差分は、
    コミットにも変更台帳（push のあとに記帳）にもまだ無い＝数えない。見るのはマニフェストの files（編集したページ）: pages は測る
    対象で、internal-link・hub では編集していないリンク先や人が足した新しいコラムが入る。
    除くのは、元の commit の逆向きと確かめられた差し戻し（rollback_why[ファイル] が None）だけ。確かめられない差し戻しは普通の変更と同じ。
    ハブ・トップ（HUBS）: 構成レビューは凍結を当てる（cooldown_pages(structure=True) がハブ・トップを構成系の記帳だけで数える＝
    コラムを足しただけの週は凍結されない）。週次は O16-38 の例外（カードの追加＝class=hub）だけ凍結を当てず、その場合も凍結中なら
    title・description・<head> は変えさせず、足した行が既存のカードと同じ形のカード（コラムへのリンク 1 本）だけであることを
    確かめる（card_only_change。それ以外が混じれば凍結を当てる＝申告した class だけで抜けさせない）。
    class=hub 以外（title・description・internal-link…）は凍結を当てる。
    unlisted＝マニフェストに載せずに焼き直しでない書き換えをしたハブ・トップ（unlisted_hub_edits）。凍結を当てる＝凍結中なら
    焼き直しだけの差分であることを求める（申告しないだけで凍結を抜けさせない。カードを足すなら class=hub で files に書く）。
    凍結を確かめられないときは止める（台帳が無い・git の HEAD や履歴を読めない・読み込みの失敗）。"""
    targets = {}     # 凍結を当てるページ → ファイル
    hub_cards = {}   # 週次: class=hub だけで触ったハブ・トップ（凍結中なら <head> を見る）
    unlisted_pages = set()
    for f in unlisted:
        u = file_to_url(f)
        if u:
            targets.setdefault(path_of(u), f)
            unlisted_pages.add(path_of(u))
    for e in entries:
        if not isinstance(e, dict):
            continue
        cls = e.get("class")
        for f in e.get("files") or []:
            u = file_to_url(f) if isinstance(f, str) and f in changed else None
            if not u:
                continue
            if cls == "rollback" and rollback_why.get(f, "") is None:
                continue   # 確かめられた差し戻し
            if not structure and cls == "hub" and f in HUBS:
                hub_cards.setdefault(path_of(u), f)
                continue
            targets.setdefault(path_of(u), f)
    if not (targets or hub_cards):
        return []
    try:
        import build_brief as bb  # noqa: PLC0415 — 読み込みは定数の定義だけ（API も台帳の書き込みも無い）
        bb.REPO = REPO            # 検査と同じリポジトリの履歴を読む（common.REPO は SCIX_WEB_REPO が無いと ~/projects/scix-web を指す）
        if not sh("git", "rev-parse", "--verify", "HEAD").strip():
            raise RuntimeError(f"git の HEAD を読めない（{REPO}）")
        if not (bb.LEDGER / "ledger").is_dir():
            raise FileNotFoundError(f"変更台帳の置き場が無い（{bb.LEDGER / 'ledger'}）")
        cd = bb.cooldown_pages(structure=structure, strict=True)   # git log の失敗も例外にする（黙って凍結ゼロにしない）
    except Exception as ex:  # noqa: BLE001
        return [f"凍結ページを確かめられないので止める（O16-37）: {str(ex)[:160]}"]
    out = []
    for page in sorted(targets):
        if page in cd:
            f = targets[page]
            why = rollback_why.get(f)
            out.append(f"{page}: 14日以内に変えたページは変えない（O16-37・O16-38。前回 {cd[page][0]} {cd[page][1]}）"
                       + (f"。class=rollback だが {why}" if why else "")
                       + ("。マニフェストに載せずに、焼き直しの所のほかを変えている（載せなければ焼き直しだけ。"
                          "カードの登録漏れの手当ては class=hub で files に書く）" if page in unlisted_pages else ""))
    for page in sorted(hub_cards):
        if page in cd and page not in targets:
            f = hub_cards[page]
            hb, ha = sh("git", "show", f"HEAD:{f}"), (REPO / f).read_text(encoding="utf-8", errors="replace")
            if head_changed(hb, ha):
                out.append(f"{page}: 凍結中のハブ・トップは、カードの追加（class=hub）でも title・description・<head> を変えない"
                           f"（O16-37・O16-38。前回 {cd[page][0]} {cd[page][1]}）")
            elif not card_only_change(f, hb, ha):
                # 申告した class だけで凍結を外さない: 足した行が既存のカードと同じ形のカード（コラムへのリンク 1 本）だけかを確かめる
                out.append(f"{page}: 14日以内に変えたページは変えない（O16-37・O16-38。前回 {cd[page][0]} {cd[page][1]}）。"
                           "class=hub で凍結を外せるのはカードの追加だけ（既存のカードと同じ要素と class・コラムへのリンク 1 本・"
                           "変更前のハブにカードの無いコラム＝登録漏れの手当て）。カードでない段落・リンク・見出し、既にカードのある"
                           "コラムのカード、消した行・書き換えた行がある")
    return out


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""; self._t = False; self._title_seen = False; self.desc = None; self.canonical = None; self.h1 = 0
        self.header_js = False; self.inline_header = False; self.ld = []; self._ld = None
        self.links = []; self.hreflang = {}; self.robots = []; self.h1_text = ""; self._h1 = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "title":
            # ページの title は最初の 1 つだけ。本文のインライン SVG にも <title id="fig2-title"> があり、連結すると
            # 「title の重複」が黙って外れ、EN の 70 字検査が図つきページを誤って止める（2026-09-20）
            if not self._title_seen: self._t = True; self._title_seen = True
        elif tag == "meta" and (a.get("name") or "").lower() == "description": self.desc = a.get("content", "")
        elif tag == "meta" and (a.get("name") or "").lower() in ("robots", "googlebot"): self.robots.append((a.get("content") or "").lower())
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical": self.canonical = a.get("href")
            elif rel == "alternate" and a.get("hreflang"): self.hreflang[a["hreflang"]] = a.get("href")
        elif tag == "h1": self.h1 += 1; self._h1 = True
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json": self._ld = ""
            elif a.get("src") == "/header.js": self.header_js = True
        elif tag == "header" and "scix-header" in cls: self.inline_header = True
        elif tag == "a" and a.get("href"): self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title": self._t = False
        elif tag == "h1": self._h1 = False
        elif tag == "script" and self._ld is not None:
            try: self.ld.append(json.loads(self._ld))
            except json.JSONDecodeError: self.ld.append(None)
            self._ld = None

    def handle_data(self, data):
        if self._t: self.title += data
        elif self._ld is not None: self._ld += data
        elif self._h1: self.h1_text += data

    def noindex(self) -> bool:
        return any("noindex" in r or r.strip() == "none" for r in self.robots)


def resolves(href: str, redirects: set, sitemap_paths: set) -> bool:
    if not href.startswith("/") or href.startswith("//"):
        return True
    p = href.split("#")[0].split("?")[0]
    if not p or p == "/":
        return True
    if p in redirects or p in sitemap_paths:
        return True
    if p.startswith(("/img/", "/files/")):
        return (REPO / p.lstrip("/")).exists()
    if p == "/en":
        return (REPO / "en" / "index.html").exists()
    if p.endswith("/"):
        p = p[:-1]
    return (REPO / (p.lstrip("/") + ".html")).exists() or (REPO / p.lstrip("/")).exists() or (REPO / (p.lstrip("/") + ".txt")).exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--profile", choices=("weekly", "structure"), default="weekly",
                    help="structure＝月1回の構成レビュー（並べ替えの分だけ量を緩め、導線の本数を守り、ナビは90日ルールを照合して PR の経路へ）")
    a = ap.parse_args()
    structure = a.profile == "structure"
    problems = []

    status = [l for l in sh("git", "status", "--porcelain", "--untracked-files=all").splitlines() if l.strip()]
    changed, added, deleted = [], [], []
    for l in status:
        code, path = l[:2], l[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if "D" in code:
            deleted.append(path)
        elif "?" in code or "A" in code:
            added.append(path)
        else:
            changed.append(path)
    if not (changed or added or deleted):   # 削除だけの差分を「変更なし」で通さない（下の「削除は禁止」へ進ませる）
        print("変更なし"); return 0
    for p in deleted:
        problems.append(f"削除は禁止: {p}")
    if len(added) > MAX_NEW:   # 週次・構成レビューとも新規ファイルは 0。中身の検査には進まない
        for p in added:
            problems.append(f"新規ファイル {p}: {NO_NEW_PAGE}")
    # O16-7・O16-12: 非公開の禁止語（リポジトリの外の一覧）。読めなければ止める＝一覧が無いまま公開しない
    private_pats, private_label, private_err = load_private_banned()
    if private_err:
        problems.append(private_err)

    def private_problem(where: str, s) -> list:
        return [f"{where}: 非公開の禁止語（{rid}）に当たる。語は出さない＝{private_label} の {rid} と O16-7・O16-12 を見て外す"
                for rid in private_hits(s, private_pats)]

    manifest = {}
    try:
        manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        problems.append(f"マニフェストが読めない: {e}")
    entries = manifest.get("changes") or []
    listed = set()
    if structure and len(entries) > STRUCT_MAX_ENTRIES:
        problems.append(f"構成の変更は {STRUCT_MAX_ENTRIES} 件まで（{len(entries)} 件）")
    if not structure and len(entries) > MAX_WEEKLY_ENTRIES:
        problems.append(f"週次の変更は {MAX_WEEKLY_ENTRIES} 件まで（{len(entries)} 件・O16-36）")
    if structure:
        if not entries:
            # 差分はあるのに変更が 0 件＝焼き直し（NEW バッジ落ち・ItemList の順）だけが残っている。公開も PR もしない
            problems.append("構成レビュー: マニフェストの changes が 0 件なのに差分がある（焼き直しの差分だけでは変更にならない。"
                            "変更なしなら changes: [] と no_change_reason のまま終えてよい＝シェルは公開も PR もしない）")
    # コミットの件名・PR の題にもなる欄（proposal_title）を含め、公開される欄は全部見る。週次のコミット本文・変更日台帳も公開＝週次でも見る
    for k in PUBLIC_TOP_KEYS:
        v = manifest.get(k)
        for l in (v if isinstance(v, list) else [v] if v else []):
            if lead_number(l):
                problems.append(f"{k}: 問い合わせの件数は公開される欄（コミットの件名と本文・変更日台帳・PR の題と本文）に書かない"
                                f"（件数は private_note へ＝Drive の台帳にだけ残る）: {shown(l, 60, private_pats)}")
            problems.extend(public_text_problems(k, l))   # 案件ID・金額（O16-19）と「一次情報」（T06-12）。欄の中身は写さない
            problems.extend(private_problem(k, l))        # O16-7・O16-12（規則IDだけ）
    for i, e in enumerate(entries):
        # pages は週次でも必須: 空のまま変更台帳に入ると効果測定の対象が無い
        for k in ("files", "class", "summary", "rationale", "kpi", "pages") + (("hypothesis", "measure") if structure else ()):
            if not e.get(k):
                problems.append(f"マニフェスト {i}: {k} が無い")
        pg_ = e.get("pages")
        if pg_ and not (isinstance(pg_, list) and all(isinstance(p, str) and p.startswith("/") for p in pg_)):
            problems.append(f"マニフェスト {i}: pages は URL パス（/ で始まる文字列）の配列で書く: {shown(pg_, 80, private_pats)}")
        if e.get("class") == "new-column":
            problems.append(f"マニフェスト {i}: class=new-column は使えない。{NO_NEW_PAGE}。足りない主題は column_ideas に出す")
        if e.get("class") == "rollback" and not str(e.get("rollback_of") or "").strip():
            problems.append(f"マニフェスト {i}: class=rollback には rollback_of（戻す元の commit）が要る")
        elif e.get("class") not in (STRUCT_CLASSES if structure else CLASSES):
            problems.append(f"マニフェスト {i}: class が想定外 {e.get('class')}")
        for k in PUBLIC_ENTRY_KEYS:   # どれもコミット・変更日台帳・PR 本文に出る（週次の rationale・kpi も変更日台帳の行になる）
            if lead_number(e.get(k)):
                problems.append(f"マニフェスト {i}: {k} に問い合わせの件数を書かない（コミット・変更日台帳・PR は公開。件数は private_note へ）")
            # 案件ID・金額・「一次情報」: before／after が公開されるのは構成レビューの PR 本文だけ（週次のコミット文と変更日台帳には
            # 載らない）＝週次では見ない（元の title に円の金額があるページの title を直すと止まっていた）
            if structure or k not in ("before", "after"):
                problems.extend(public_text_problems(f"マニフェスト {i}: {k}", e.get(k)))
            problems.extend(private_problem(f"マニフェスト {i}: {k}", e.get(k)))
        if structure:
            if not re.search(r"[0-9０-９]", str(e.get("rationale", ""))):
                problems.append(f"マニフェスト {i}: rationale に根拠の数字が無い")
            # pages は「測る対象」と「14 日触らないページ」の二役。GA4 のリードは着地ページに付く＝編集していない送客先の収益ページを
            # 入れると、無関係な直着地のリードや検索の揺れで better／worse が決まり、その収益ページが週次で 14 日凍結される
            own = {path_of(file_to_url(f)) for f in e.get("files") or [] if isinstance(f, str) and file_to_url(f)}
            extra = [p for p in (pg_ if isinstance(pg_, list) else []) if isinstance(p, str) and p not in own]
            if extra and e.get("class") != "nav":
                problems.append(f"マニフェスト {i}: pages は編集したページ（files の URL）だけ: {shown(' '.join(extra), 80, private_pats)}。"
                                "送客先の収益ページは kpi_pages に書く（前後比較にも凍結にも使わない＝ブリーフ 8 節の参考列）")
            kp = e.get("kpi_pages")
            if kp is not None and not (isinstance(kp, list) and all(isinstance(p, str) and p.startswith("/") for p in kp)):
                problems.append(f"マニフェスト {i}: kpi_pages は URL パス（/ で始まる文字列）の配列で書く: {shown(kp, 80, private_pats)}")
        if len(str(e.get("summary", ""))) > 300:
            problems.append(f"マニフェスト {i}: summary が長すぎる")
        for f in e.get("files") or []:
            listed.add(f)
    for f in listed:
        if f not in changed and f not in added:
            problems.append(f"マニフェストにあるが実際には変わっていない: {f}")
    # 差し戻し（class=rollback・週次だけ）は、元の commit（rollback_of）の逆向きの差分かを確かめる。None＝確かめられた
    rollback_why = {}
    for e in entries:
        if not isinstance(e, dict) or e.get("class") != "rollback":
            continue
        for f in e.get("files") or []:
            if isinstance(f, str) and f in changed and ALLOWED_HTML.match(f) and f not in rollback_why:
                rollback_why[f] = rollback_unverified(e.get("rollback_of"), f, sh("git", "show", f"HEAD:{f}"),
                                                      (REPO / f).read_text(encoding="utf-8", errors="replace"))
    # マニフェストに載せずに、焼き直しの所のほかを変えたハブ・トップ（2026-09-23 の確かめ #66: 申告しないだけで凍結を抜けられた）。
    # 焼き直しが書かないファイル（en/index.html・zh.html）と構成レビューは、載っていない変更をそのまま止める。
    # 週次の焼き直しが書くファイルは凍結を当てる（凍結中でなければ、下の焼き直しの範囲 600 字と <head> の検査）
    unlisted = unlisted_hub_edits(changed, listed)
    for f in unlisted:
        if structure or f not in BAKE_PARTS:
            problems.append(f"マニフェストに載っていない変更: {f}（焼き直しの所のほかに差分がある。ハブ・トップを触ったら files に書く）")
    # 14 日以内に変えたページ（ブリーフ 9 節）は変えない（O16-37・O16-38）。確かめられなければ止める
    problems.extend(cooldown_problems(entries, changed, structure, rollback_why,
                                      [] if structure else [f for f in unlisted if f in BAKE_PARTS]))
    # 確かめられた差し戻しのファイルだけ、足した節（id つきの要素・section）を消してよい
    rollback_files = {f for f, why in rollback_why.items() if why is None}

    redirects = set()
    try:
        redirects = {r["source"] for r in json.load(open(REPO / "vercel.json", encoding="utf-8")).get("redirects", [])}
    except Exception:  # noqa: BLE001
        pass
    sitemap_text = (REPO / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
    sitemap_paths = {path_of(u) for u in sitemap_urls}

    all_titles = {}
    for f in list(REPO.glob("*.html")) + list((REPO / "en").glob("*.html")):
        m = re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8", errors="replace"), re.S)
        if m:   # Page と同じ読み方にそろえる（最初の <title>・実体参照は戻す＝「O&amp;M」の title も重複を見つけられる）
            all_titles.setdefault(html.unescape(m.group(1)).strip(), []).append(str(f.relative_to(REPO)))

    n_existing = 0
    funnel_before = funnel_after = 0
    routes = vercel_routes()   # 導線の本数を数えるときに、リダイレクトとホストの rewrites（invest.scix.co.jp → /fund）をたどる
    if routes is None:         # 読めなければ止める（空で続けると /fund の数え方が甘くなる）
        problems.append(VERCEL_UNREADABLE)
        routes = ({}, {})
    for path in changed + added:
        if path in FORBIDDEN or path.startswith(FORBIDDEN_PREFIX):
            problems.append(f"触ってはいけないファイル: {path}"); continue
        if path in added:
            continue   # 新規ファイルは上で止めてある（中身は見ない）
        if path == "sitemap.xml":
            continue
        if path == "header.js":
            check_header_js(a.profile, entries, problems, private_pats)
            continue
        if not ALLOWED_HTML.match(path):
            problems.append(f"想定外のファイル: {path}"); continue
        if path not in listed and path not in HUBS:
            problems.append(f"マニフェストに載っていない変更: {path}")
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
        before = sh("git", "show", f"HEAD:{path}")
        # 本文（見える文字）の正味の変更。行数の比率は CSS と script に薄められるので、書き換えの量はこちらで測る
        t_add, t_del, t_base = text_change(before, text)
        t_room = max(t_base, TEXT_FLOOR)
        if structure:
            if path not in HUBS:
                n_existing += 1
            num = sh("git", "diff", "--numstat", "--", path).split()
            total = max(1, len(before.splitlines()))
            if len(num) >= 2 and (int(num[0]) + int(num[1])) / total > STRUCT_MAX_REPLACE_RATIO:
                problems.append(f"{path}: 差し替えが大きすぎる（+{num[0]}/-{num[1]} of {total}行）")
            add_, del_, base = net_change(before, text)
            if (add_ + del_) / base > STRUCT_NET_RATIO:
                problems.append(f"{path}: 並べ替えを除いた正味の書き換えが大きすぎる（足した行 {add_}・消した行 {del_} of {base}行・上限 {STRUCT_NET_RATIO:.0%}）")
            if del_ / base > STRUCT_NET_DELETE:
                problems.append(f"{path}: 正味の削除が多すぎる（{del_} of {base}行・上限 {STRUCT_NET_DELETE:.0%}）")
            if (t_add + t_del) / t_room > STRUCT_NET_RATIO:
                problems.append(f"{path}: 本文の正味の書き換えが大きすぎる（足した {t_add} 字・消した {t_del} 字 of {t_base} 字・上限 {STRUCT_NET_RATIO:.0%}）。"
                                "構成レビューは動かす・行き先を変える・導線を足すまで。本文は書き換えない")
            if t_del / t_base > STRUCT_NET_DELETE:
                problems.append(f"{path}: 本文の正味の削除が多すぎる（{t_del} of {t_base} 字・上限 {STRUCT_NET_DELETE:.0%}）")
            # 収益ページ・フォームへの導線は、ファイルごとに減らさない（行き先の付け替えは可）
            page_url = file_to_url(path) or BASE + "/"
            fb, fa = funnel_links(before, page_url, routes), funnel_links(text, page_url, routes)
            funnel_before += sum(fb.values()); funnel_after += sum(fa.values())
            if sum(fa.values()) < sum(fb.values()):
                lost = "・".join(f"{t} {fb[t]}→{fa[t]}" for t in sorted(fb) if fa[t] < fb[t])
                problems.append(f"{path}: 収益ページ・フォームへの導線が減っている（{sum(fb.values())} → {sum(fa.values())} 本。{lost}）。"
                                "構成を変えても導線は消さない（行き先の付け替え・置き場所の移動は同じファイルの中で）")
        elif path not in HUBS:
            n_existing += 1
            num = sh("git", "diff", "--numstat", "--", path).split()
            if len(num) >= 2:
                add_, del_ = int(num[0]), int(num[1])
                total = max(1, len(text.splitlines()))
                if (add_ + del_) / total >= MAX_REPLACE_RATIO:   # O16-39: 半分「未満」
                    problems.append(f"{path}: 差し替えが大きすぎる（+{add_}/-{del_} of {total}行・{MAX_REPLACE_RATIO:.0%} 未満に収める）")
                if del_ / total > MAX_DELETE_RATIO:
                    problems.append(f"{path}: 削除が多すぎる（-{del_} of {total}行）")
            if (t_add + t_del) / t_room >= MAX_REPLACE_RATIO:   # O16-39: 本文の半分「未満」（ちょうど半分も止める）
                problems.append(f"{path}: 本文の書き換えが大きすぎる（足した {t_add} 字・消した {t_del} 字 of {t_base} 字・{MAX_REPLACE_RATIO:.0%} 未満に収める＝O16-39）。"
                                "既存ページの本文を別の記事に置き換えない（コラムを書くのは中島さん）")
            if t_del / t_base > MAX_DELETE_RATIO:
                problems.append(f"{path}: 本文の削除・書き換えが多すぎる（{t_del} of {t_base} 字・上限 {MAX_DELETE_RATIO:.0%}）")
        elif path not in listed:
            # 週次のハブ・トップはマニフェストに書かなくても通る（焼き直しが触るため）。ただし焼き直しの範囲（NEW バッジ・件数）まで
            if t_add + t_del > HUB_BAKE_CHARS:
                problems.append(f"{path}: マニフェストに載っていないのに本文が変わっている（足した {t_add} 字・消した {t_del} 字。"
                                f"焼き直しの範囲は {HUB_BAKE_CHARS} 字まで）。ハブ・トップを触ったら files に書く")
            if head_changed(before, text):   # 焼き直しが <head> で変えるのは「全N記事」の数字と JSON-LD だけ
                problems.append(f"{path}: マニフェストに載っていないのに title・description・<head> が変わっている"
                                "（焼き直しが変えるのは「全N記事」の数字と JSON-LD だけ）。ハブ・トップを触ったら files に書く")
        else:
            if t_add > HUB_MAX_ADD_CHARS:
                problems.append(f"{path}: ハブ・トップに足した本文が多すぎる（{t_add} 字・上限 {HUB_MAX_ADD_CHARS} 字）。"
                                "カードの登録漏れの手当てまで。記事ぶんの節は足さない（構成は月 1 回の構成レビューの仕事）")
            if t_del / t_base > HUB_MAX_DELETE_RATIO:
                problems.append(f"{path}: ハブ・トップの本文の削除が多すぎる（{t_del} of {t_base} 字・上限 {HUB_MAX_DELETE_RATIO:.0%}）")
        problems.extend(nesting_problems(path, before, text, allow_removal=(not structure and path in rollback_files)))
        sb, sa = synced_regions(before), synced_regions(text)
        if (sorted(sb) != sorted(sa)) if structure else (sb != sa):   # 構成レビューは節ごと動かすのを許す＝並び順を問わず同じ中身
            problems.append(f"{path}: <!--S:…--> の内側は毎朝の同期が書く場所（件数・一覧・新着）。"
                            + ("節ごと動かすのはよいが、中身は変えない" if structure else "週次では触らない"))
        if path == "projects.html" and PAGE_JS_RE.findall(before) != PAGE_JS_RE.findall(text):
            problems.append("projects.html: 一覧を描く JS は自動では触らない（scripts/inject_stats.py の静的一覧と文言をそろえてある）")
        if path in HERO_TOPS or (structure and path in HUBS):
            hb, ha = hero_region(before), hero_region(text)
            if hb is None or ha is None:
                problems.append(f"{path}: ヒーローの範囲（<body> 〜 hero の終わり）を取れない＝検査できないので止める")
            elif hb != ha:
                problems.append(f"{path}: ヒーローより上は変えない（<body> の先頭〜"
                                + ("<section class=\"hero\"> の終わり" if 'class="hero"' in hb else "最初の </h1>") + "）")
        if path in HUBS and styles_and_scripts(before) != styles_and_scripts(text):
            # ヒーローの中身が同じでも CSS（.hero{display:none}）や JS で消せる。ハブ・トップの見た目の土台は人が変える
            problems.append(f"{path}: ハブ・トップの <style> と <script>（JSON-LD 以外）は自動では変えない"
                            "（節の見た目は既存の class と、節の開きタグの style 属性で）")
        pg = Page(); pg.feed(text)
        pb = Page(); pb.feed(before)
        if pg.noindex() and not pb.noindex():
            problems.append(f"{path}: robots の noindex を足さない（検索から落ちる）")
        if structure and path in HUBS:
            if not (same_but_digits(pb.title, pg.title) and same_but_digits(pb.desc, pg.desc) and pb.canonical == pg.canonical):
                problems.append(f"{path}: 構成レビューではハブ・トップの title／description／canonical を変えない")
            elif head_rest(before) is None or head_rest(before) != head_rest(text):
                problems.append(f"{path}: 構成レビューではハブ・トップの <head>（meta・link・hreflang・og）を変えない")
        elif structure:
            # cta-route／funnel-block は本文を書き換えない型＝ハブ以外のページも、何のページかを決める所は同じであること
            if (pb.title.strip(), (pb.desc or "").strip(), pb.h1_text.strip()) != (pg.title.strip(), (pg.desc or "").strip(), pg.h1_text.strip()):
                problems.append(f"{path}: 構成レビューでは title／description／h1 を変えない（中身の手直しは週次の仕事）")
        url = file_to_url(path)
        if not pg.title.strip():
            problems.append(f"{path}: title が無い")
        else:
            others = [o for o in all_titles.get(pg.title.strip(), []) if o != path]
            if others:
                problems.append(f"{path}: title が他ページと重複 {others}")
        if pg.desc is None or not pg.desc.strip():
            problems.append(f"{path}: description が無い")
        if not pg.canonical or path_of(pg.canonical) != path_of(url or ""):
            problems.append(f"{path}: canonical が自分を指していない（{pg.canonical}）")
        if pg.h1 != 1:
            problems.append(f"{path}: h1 が {pg.h1} 個")
        if not pg.header_js:
            problems.append(f"{path}: /header.js を読んでいない")
        if pg.inline_header:
            problems.append(f"{path}: ヘッダーの直書き")
        if None in pg.ld:
            problems.append(f"{path}: JSON-LD が壊れている")
        if path.startswith("en/"):
            if len(pg.title.strip()) > 70:
                problems.append(f"{path}: EN title が70字超（{len(pg.title.strip())}）")
            if pg.desc and len(pg.desc) > 155:
                problems.append(f"{path}: EN description が155字超（{len(pg.desc)}）")
        else:
            if pg.desc and len(pg.desc) > 170:
                problems.append(f"{path}: description が長すぎる（{len(pg.desc)}字・目安120）")
        for href in set(pg.links):
            if not resolves(href, redirects, sitemap_paths):
                problems.append(f"{path}: 内部リンク切れ {href}")
        for lang, href in pg.hreflang.items():
            if href and href.startswith(BASE) and not resolves(path_of(href), redirects, sitemap_paths):
                problems.append(f"{path}: hreflang {lang} の先が無い {href}")
        # 禁止語（追加行だけ見る）。非公開の禁止語（O16-7・O16-12）は規則IDだけ出し、その行はほかの理由でも写さない
        private_seen = set()
        for line in sh("git", "diff", "--", path).splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for rx, why in BAD_WORDS:
                if rx.search(line):
                    problems.append(f"{path}: {why}: {shown(line[1:], 89, private_pats).strip()}")
            for p_ in private_problem(path, line[1:]):
                if p_ not in private_seen:
                    private_seen.add(p_)
                    problems.append(p_)
        # O16-10: 自称の「中立」「neutral」。ページ全体の出現（同じ行の前後 20 字の文脈）の前後で比べ、新しく現れた分だけ止める。
        # 抜粋（前後 20 字の窓）を写す前に、出現を含む行の全体に非公開の禁止語を当てる（窓の端で切れた語の残りを出さない）
        for rx, why in NEUTRAL_RULES:
            for m, whole in new_contexts(rx, before, text):
                problems.append(f"{path}: {why}: {shown(m, 89, private_pats, whole)}")
        # IRR・利回り・手数料率・手付・募集額・1口の数字（O16-8・O16-66）。足した行の差分ではなく、ページ全体の出現の前後で比べる
        # ＝既存の文（公表資料の数字）・動かしただけの行・既存の行への書き足しは止めず、新しく書いた分だけ止める
        for m, whole in new_occurrences(FUND_NUM_RE, before, text):
            problems.append(f"{path}: {FUND_NUM_WHY}: {shown(m, 80, private_pats, whole)}")
        # O16-69: 英語・中文のページに証券化（GK-TK）を新たに書かない（ページ全体の出現の前後。既存の文を動かす・直すのは止めない）
        if en_zh_page(path):
            for m, whole in new_occurrences(SECURITIZATION_RE, before, text, key=lambda t, m, ls, le: m.group(0).lower()):
                problems.append(f"{path}: {SECURITIZATION_WHY}: {shown(m, 40, private_pats, whole)}")
        # O16-67: コラムから /fund への導線を増やさない（既存のフッターの 1 本は数えるだけ）
        if COLUMN_FILE_RE.match(path):
            page_url = file_to_url(path) or BASE + "/"
            fund_b, fund_a = funnel_links(before, page_url, routes)["/fund"], funnel_links(text, page_url, routes)["/fund"]
            if fund_a > fund_b:
                problems.append(f"{path}: {FUND_LINK_WHY}（/fund を指すリンク {fund_b} → {fund_a} 本）")
    if n_existing > MAX_EXISTING:
        problems.append(f"既存ページの変更が多すぎる（{n_existing} > {MAX_EXISTING}）")
    # sitemap の整合
    if "sitemap.xml" in changed:
        try:
            import xml.dom.minidom
            xml.dom.minidom.parseString(sitemap_text)
        except Exception as e:  # noqa: BLE001
            problems.append(f"sitemap.xml が XML として壊れている: {e}")
        for u in sitemap_urls:
            if not resolves(path_of(u), redirects, set()):
                problems.append(f"sitemap.xml: 実体の無い URL {u}")

    if problems:
        print("止める理由:")
        for p in problems:
            # 最後の網: ファイル名・リンク先・欄の抜粋など、どの理由に語が紛れても伏せてから出す（語も式も出さない）
            for rx, rid in private_pats:
                p = rx.sub(f"〔伏せ字 {rid}〕", p)
            print(" -", p)
        return 1
    if structure:
        # 公開の経路。シェル（weekly_run.sh）はこの行と、自分で見た header.js の差分の両方で決める（どちらかが PR なら PR）
        print("経路: PR（header.js の変更を含む＝ナビは全ページに効くので自動公開しない。この回は全体を PR に出す）"
              if pr_route(entries, changed) else "経路: 自動公開（ナビを含まない）")
    print(f"OK{'（structure）' if structure else ''} 既存 {n_existing}・新規 {len(added)}・マニフェスト {len(entries)} 件"
          + (f"・収益ページとフォームへの導線 {funnel_before}→{funnel_after} 本" if structure else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
