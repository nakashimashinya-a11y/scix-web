#!/usr/bin/env python3
"""コラムの途中（h1 の後の最初の h2 の直前）に、読む人の立場に合わせた導線を1つ差す。

  買い手が読む記事・どちらでもない記事 → 蓄電所マーケットの案件の一覧（日本語 https://dealroom.scix.co.jp/ ・英語と中国語は /en）
  売り手が読む記事 → 日本語は /sell-form（無料の売却査定）・英語は /en/contact・中国語は /zh-contact
  土地の持ち主向けの4本（column-land-buyback・-lease・-value・-zoning と、その英語・中国語）には入れない（O16-5）。

日本語の頁で、1つ目の節の後に前からある「立場別の導線」（<aside data-scix-guide>）がマーケットか売却査定へのリンクを持っていれば、
文を重ねずにそれを途中の導線として生かし、そのリンクに計測の印（data-cta="mid"）だけを付ける。持っていない頁には区画を差す。
押されたかは header.js の a[data-cta] の委任（cta_click・placement=mid）で数える（onclick は書かない）。
本文と h1 は触らない。<!-- scix-mid-cta:begin/end --> の目印で囲み、何度回しても同じ結果になる。

    python3 scripts/add_column_mid_cta.py          # 書き換える
    python3 scripts/add_column_mid_cta.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指示2・5）。
登録なしで見られる範囲は蓄電所マーケットの /how と同じに書く（2026-11-23 中島「出し惜しみするな。全部出して売上UPだ」）。
"""
import re
import sys

import column_blocks as cb

# 売り手が読む記事（add_column_entrances.py の「売る話」と同じ線引き＝主ボタンは /sell-form・O16-43）
SELLER_RE = re.compile(r"transfer|^pricing$|study-reply|development")
MARKET = {"ja": "https://dealroom.scix.co.jp/", "en": "https://dealroom.scix.co.jp/en", "zh": "https://dealroom.scix.co.jp/en"}
SELL = {"ja": ("/sell-form", "sell_form"), "en": ("/en/contact", "contact"), "zh": ("/zh-contact", "contact")}
TEXT = {
    ("ja", "buy"): ("接続検討の回答が出た案件を、蓄電所マーケットで販売しています。案件名・県と市区町村・規模・電力の手続きの段・写真まで、登録なしで見られます。価格と資料は無料の登録のあとです。",
                    "蓄電所マーケットで案件を見る →"),
    ("ja", "sell"): ("接続検討の回答が出た案件をお持ちで、手放すか迷っているなら、無料の売却査定へ。当社が買い取るか、買い手におつなぎします。",
                     "無料で売却査定を依頼する →"),
    ("en", "buy"): ("Projects that hold a grid connection study response are for sale on Chikudensho Market. Project name, prefecture and city, "
                    "scale, grid procedure stage and photos can be viewed without registration; prices and documents follow free registration.",
                    "See projects on Chikudensho Market →"),
    ("en", "sell"): ("If you hold a project with a connection study response and are thinking of selling, we either buy it ourselves "
                     "or introduce you to a buyer.",
                     "Request a free sale assessment →"),
    ("zh", "buy"): ("已取得接入系统研究答复的项目，在蓄电所市场销售。项目名称、所在县市、规模、电力手续阶段与照片，无需注册即可查看；价格与资料在免费注册后查看。",
                    "在蓄电所市场查看在售项目（英文页面） →"),
    ("zh", "sell"): ("持有已取得接入系统研究答复的项目、正在考虑出售的，由本公司收购，或为您引荐买家。",
                     "申请免费出售评估 →"),
}
GUIDE_RE = re.compile(r"<!-- scix-guide: 立場別.*?</aside>", re.S)


def side(slug):
    return "sell" if SELLER_RE.search(slug) else "buy"


def guide_cta(s):
    """日本語の頁の前からある立場別の導線の区画（マーケットか売却査定へのリンクを持つ物）。"""
    m = GUIDE_RE.search(s)
    if m and re.search(r'href="(?:https://dealroom\.scix\.co\.jp/[^"]*|/sell-form)"', m.group(0)):
        return m
    return None


def mark_guide(s):
    m = guide_cta(s)
    if not m:
        return s

    def tag(a):
        t = a.group(0)
        if "data-cta=" in t:
            return t
        href = re.search(r'href="([^"]+)"', t).group(1)
        target = "market" if "dealroom.scix.co.jp" in href else "sell_form"
        return t[:-1] + f' data-cta="mid" data-cta-target="{target}">'

    g = re.sub(r'<a\b[^>]*href="(?:https://dealroom\.scix\.co\.jp/[^"]*|/sell-form)"[^>]*>', tag, m.group(0))
    return s[:m.start()] + g + s[m.end():]


def block(lang, sd):
    text, btn = TEXT[(lang, sd)]
    href, target = (MARKET[lang], "market") if sd == "buy" else SELL[lang]
    return cb.wrap("mid-cta", f'<aside class="scix-midcta" data-scix-midcta data-side="{sd}"><p>{cb.esc(text)}</p>'
                   f'<a class="scix-midcta-btn" target="_top" href="{href}" data-cta="mid" data-cta-target="{target}">{cb.esc(btn)}</a></aside>')


def apply(r, s):
    s = cb.strip(s, "mid-cta")
    slug = cb.slug_of(r)
    if slug in cb.LAND:
        return s
    lang = cb.lang_of(r)
    if lang == "ja" and guide_cta(s):
        return mark_guide(s)
    pos = cb.first_h2(s)
    if pos is None:
        print("置き場が見つからない:", r)
        return s
    return cb.place(s, "mid-cta", block(lang, side(slug)), pos)


if __name__ == "__main__":
    sys.exit(cb.run_all(apply, "--check" in sys.argv))
