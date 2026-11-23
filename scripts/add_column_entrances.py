#!/usr/bin/env python3
"""コラム（column-*.html）の末尾に「この話題に近い入口」と非公開案件ページ登録のボタンを足す。

コラム本文は触らない。フッターの直前に、印のコメントで囲った1区画を入れる。
もう入っていれば作り直す（何度走らせても同じ）。

英語・中国語のコラム（en/column-*.html・zh-column-*.html）にも、言葉ごとの文と行き先で同じ区画を足す（2026-11-22 中島「これ全部やって。
売上UPのために徹底的に進めて。すべて漏らさずやって。」＝Gemini の助言の指示2・5）。行き先は 蓄電所マーケット（https://dealroom.scix.co.jp/en）・
問い合わせ（/en/contact・/zh-contact）・ナレッジ。頁の末尾に前から導線（cta-section・cta-block・scix-column-cta）がある頁は入口の札だけにし、
無い頁（英語30・中国語27）は先頭の札を主ボタンの色にする（同じ行き先のボタンを2つ並べない）。押されたかは header.js の a[data-cta] の委任（cta_click・placement=end）で数える。
土地の持ち主向けの頁（column-land-value の英語・中国語）には、売る・買う入口のほかを足さない（O16-5＝土地を呼ぶ札を作らない）。

    python3 scripts/add_column_entrances.py          # 書き換える
    python3 scripts/add_column_entrances.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
"""
import glob
import json
import os
import re
import sys

REG = "https://dealroom.scix.co.jp/register"
MARKET = "https://dealroom.scix.co.jp/"
# 買う話のコラムの末尾に、蓄電所マーケットの今ある案件（登録なし）を電圧・エリアで絞った入口を1行（2026-11-21 中島「SEO対策…やって公開、実行」）。
# 行き先は絞り込みの検索（?voltage=・?area=）でなく、マーケットの静的な入口の頁 /catalog/voltage/<…>・/catalog/area/<…>（正規の住所が自分・
# 件数0の入口は404になるので、projects.json に1件も無い電圧・エリアはマーケットのトップ / へ落とす＝2026-11-22 中島「Seo 対策も徹底してやって」）。
# 売る話のコラムには出さない（主ボタンは /sell-form＝O16-43）。
FILTERS = [("voltage", "特別高圧", "extra-high-voltage"), ("voltage", "高圧", "high-voltage"),
           ("area", "北海道", "hokkaido"), ("area", "東北", "tohoku"), ("area", "東京", "tokyo"), ("area", "中部", "chubu"),
           ("area", "北陸", "hokuriku"), ("area", "関西", "kansai"), ("area", "中国", "chugoku"), ("area", "四国", "shikoku"),
           ("area", "九州", "kyushu")]
# 市場の数字（月報・市場データ・エリアの頁）への静的なリンク。話題が合うコラムだけ入口の区画に1行（札の字は行き先の h1＝O16-27 の考え方）。
# /fund へは足さない（O16-67）。
DATA_RE = re.compile(r"balancing|eprx|day-ahead|price-cap|bidding-ceiling|capacity|auction|^lda$|merchant|trading|long-term|revenue|area-data")
AREA_RE = re.compile(r"regional-revenue|area-data")
REPORT = ("/report", "蓄電所の市場ノート")
REPORT_DATA = ("/report/data", "蓄電所の市場データ")
REPORT_AREAS = [("/report/area/tokyo", "東京エリアの市場データ"), ("/report/area/kyushu", "九州エリアの市場データ")]
BEGIN = "<!-- scix-entrances:begin -->"
END = "<!-- scix-entrances:end -->"
DOORS = {
    "overseas": ("/en", "海外の投資家の方へ", "English page"),
    "major": ("/for/major", "大手事業者・電力・商社の方へ", "特別高圧と高圧"),
    "sme": ("/for/sme", "事業会社の方へ（高圧1件から）", "1件から買う"),
    "dealers": ("/partners", "案件・投資家をご紹介いただける方へ", "紹介の窓口"),   # 前は /for/dealers（2026-11-23 /partners#dealers へ寄せて転送）
    # 売る話のコラム（2026-11-15 売り手の目で歩いた点検＝売る話の末尾が買う入口だけで、どれが自分向けか迷う）
    "sell": ("/sell-form", "無料で売却査定を依頼する", "5行で届きます"),
    "sourcing": ("/sourcing", "売るまでの流れと、用意するもの", "案件・権利を売る"),
    "msell": ("https://dealroom.scix.co.jp/needs", "蓄電所マーケットで自分で売る", "売りたい方へ"),
}
# 話題 → 入口3つ（上から順に近い）。どれにも当たらなければ既定。
RULES = [
    (r"transfer|^pricing$|study-reply|development",
     ["sell", "sourcing", "msell"]),
    (r"foreign|jcstar|eprx|merchant|trading|day-ahead|capacity|balancing|price-cap|regional-revenue|auction|nonfirm|long-term",
     ["overseas", "major", "sme"]),
    (r"financing|buyer|options|investment-tax|tax|cashflow|insurance|om\b|equipment|construction|low-voltage|pricing|project-price|contract|transfer|revenue",
     ["sme", "major", "dealers"]),
    (r"land|zoning|noise|development|grid|area|hazard|biz|four-labels|aggregator|lda|somosomo|study",
     ["dealers", "major", "sme"]),
]
DEFAULT = ["major", "sme", "dealers"]


def _projects():
    try:
        return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "projects.json"), encoding="utf-8"))["projects"]
    except (OSError, ValueError, KeyError):
        return []


# エリアの入口のうち、マーケット側で正規の住所が別の頁にある物（北海道はエリア＝県なので /catalog/pref/hokkaido が正規）。
# 重なる頁へ張るとリンクの重みが正規の頁に届かないので、正規の住所へ直接張る。
CANONICAL_PATH = {("area", "hokkaido"): "catalog/pref/hokkaido"}


def filter_href(kind, label, slug, ps):
    """静的な入口の頁。その電圧・エリアの案件が1件も無ければ（入口は404）マーケットのトップへ。"""
    n = sum(1 for x in ps if x.get(kind) == label)
    return MARKET + (CANONICAL_PATH.get((kind, slug), "catalog/%s/%s" % (kind, slug)) if n else "")


def data_line(name):
    """話題が合うコラムの、市場の数字への静的リンクの1行（無ければ空）。"""
    if not DATA_RE.search(name):
        return ""
    items = [REPORT_DATA, REPORT] + (REPORT_AREAS if AREA_RE.search(name) else [])
    return ('  <p style="margin:10px 0 0;font-size:13px;line-height:2.1;color:#555555">市場の数字：'
            + "・".join('<a target="_top" href="%s" style="color:#1F2A48;font-weight:700">%s</a>' % it for it in items)
            + "</p>\n")


def doors_for(name):
    for pat, keys in RULES:
        if re.search(pat, name):
            return keys
    return DEFAULT


def block(name, ps):
    seller = doors_for(name)[0] == "sell"
    btn_href, btn_text, btn_ev = ("/sell-form", "無料で売却査定を依頼する →", "column_end_sell") if seller else (REG, "蓄電所マーケットに無料登録 →", "column_end")
    cards = "".join(
        '<a target="_top" href="%s" style="display:block;padding:14px 16px;border:1px solid #E6E6E6;background:#fff;'
        'text-decoration:none;color:#1F2A48;font-weight:700;font-size:14px;line-height:1.6">%s'
        '<span style="display:block;font-weight:400;font-size:12px;color:#8C8C8C">%s →</span></a>' % DOORS[k]
        for k in doors_for(name)
    )
    return (
        BEGIN + "\n"
        '<div style="max-width:760px;margin:28px auto 0;padding:0 28px;font-family:\'Noto Sans JP\',sans-serif">\n'
        '  <h3 style="font-size:14px;color:#8C8C8C;margin:0 0 12px;font-weight:700">この話題に近い入口</h3>\n'
        '  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">' + cards + "</div>\n"
        + ("" if seller else
           '  <p style="margin:14px 0 0;font-size:13px;line-height:2.1;color:#555555">今ある案件を見る（登録なし）：'
           + "・".join('<a target="_top" href="%s" style="color:#1F2A48;font-weight:700">%s</a>'
                       % (filter_href(k, v, slug, ps), v + ("" if k == "voltage" else "エリア"))
                       for k, v, slug in FILTERS)
           + "</p>\n")
        + data_line(name)
        + '  <p style="margin:18px 0 0;text-align:center"><a target="_top" href="' + btn_href + '" '
        "onclick=\"window.gtag&&gtag('event','" + ("cta_click" if seller else "dr2_register_click") + "',{target:'" + btn_ev + "'})\" "
        'style="display:inline-block;background:#1F2A48;color:#fff;font-weight:700;font-size:14px;padding:13px 30px;text-decoration:none">' + btn_text + '</a></p>\n'
        "</div>\n" + END + "\n"
    )


# ---- 英語・中国語（2026-11-22） ----
INTL = {
    "en": dict(pre="en/column-", font="'Noto Sans JP',sans-serif", h="Where to go next",
               doors={"market": ("https://dealroom.scix.co.jp/en", "Projects for sale on Chikudensho Market", "No registration to browse", "market"),
                      "sell": ("/en/contact", "Selling a project? Contact us", "We buy it or introduce a buyer", "contact"),
                      "know": ("/en/knowledge", "Knowledge — regulation, technology and business", "All columns", "site-en/knowledge"),
                      "data": ("/en/report/data", "Battery Storage Market Data", "JEPX and capacity prices", "site-en/report/data")}),
    "zh": dict(pre="zh-column-", font="'Noto Sans SC','Noto Sans JP',sans-serif", h="下一步",
               doors={"market": ("https://dealroom.scix.co.jp/en", "蓄电所市场的在售项目（英文页面）", "无需注册即可查看", "market"),
                      "sell": ("/zh-contact", "想出售项目，请联系我们", "由本公司收购，或为您引荐买家", "contact"),
                      "know": ("/zh-knowledge", "洞见：日本电网级储能的制度、收益、市场结构", "全部文章", "site-zh-knowledge"),
                      "data": ("/en/report/data", "市场数据（英文页面）", "JEPX 与容量市场价格", "site-en/report/data")}),
}
END_CTA_RE = re.compile(r'class="(?:cta-section|cta-block|cta)[ "]|scix-column-cta')


def has_end_cta(s):
    """著者の箱より後ろに、前からある末尾の導線（マーケット・問い合わせ・売却査定へのリンク）があるか。"""
    i = s.find('class="author-box"')
    tail = s[i:] if i >= 0 else ""
    f = re.search(r"<!-- ScienceX Footer|<style>\s*\.scix-footer|<footer", tail)
    tail = tail[: f.start()] if f else tail
    return bool(re.search(r'href="[^"]*(?:dealroom\.scix\.co\.jp|contact|sell-form)[^"]*"', tail))


def block_intl(lang, name, end_cta):
    L = INTL[lang]
    land = name.startswith("land-")
    seller = doors_for(name)[0] == "sell"
    keys = ["sell", "market"] if (seller or land) else ["market", "sell"]
    if not land:
        keys.append("data" if DATA_RE.search(name) else "know")
    # 前からある末尾の導線が無い頁は、先頭の札（買い手の記事はマーケット・売り手の記事は問い合わせ）を主ボタンの色にする
    # （同じ行き先のボタンを札の下にもう1つ並べない）
    def card(i, k):
        d = L["doors"][k]
        main = (i == 0 and not end_cta)
        bg, fg, sub = ("#1F2A48", "#fff", "rgba(255,255,255,.78)") if main else ("#fff", "#1F2A48", "#8C8C8C")
        return ('<a target="_top" href="%s" data-cta="end" data-cta-target="%s" style="display:block;padding:14px 16px;border:1px solid %s;background:%s;'
                'text-decoration:none;color:%s;font-weight:700;font-size:14px;line-height:1.6">%s'
                '<span style="display:block;font-weight:400;font-size:12px;color:%s">%s →</span></a>'
                % (d[0], d[3], "#1F2A48" if main else "#E6E6E6", bg, fg, d[1], sub, d[2]))
    cards = "".join(card(i, k) for i, k in enumerate(keys))
    return (
        BEGIN + "\n"
        '<div style="max-width:760px;margin:28px auto 0;padding:0 28px;font-family:%s">\n' % L["font"]
        + '  <h3 style="font-size:14px;color:#8C8C8C;margin:0 0 12px;font-weight:700">%s</h3>\n' % L["h"]
        + '  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">' + cards + "</div>\n"
        + "</div>\n" + END + "\n"
    )


def insert(p, s, blk):
    s2 = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n\n*", "", s, flags=re.S)
    m = re.search(r"<!-- ScienceX Footer|<style>\s*\.scix-footer|<footer class=\"scix-footer\"|<footer style=\"background-color:#1F2A48", s2)
    if not m:
        print("フッターの位置が見つからない:", p)
        return None
    return s2[:m.start()] + blk(s2) + "\n" + s2[m.start():]


def main():
    check = "--check" in sys.argv
    bad = 0
    ps = _projects()
    jobs = [(p, lambda s2, n=p[len("column-"):-len(".html")]: block(n, ps)) for p in sorted(glob.glob("column-*.html"))]
    for lang, L in INTL.items():
        for p in sorted(glob.glob(L["pre"] + "*.html")):
            n = p[len(L["pre"]):-len(".html")]
            jobs.append((p, lambda s2, n=n, lang=lang: block_intl(lang, n, has_end_cta(s2))))
    for p, blk in jobs:
        s = open(p, encoding="utf-8").read()
        out = insert(p, s, blk)
        if out is None:
            bad = 1
            continue
        if out != s:
            if check:
                print("ずれ:", p)
                bad = 1
            else:
                open(p, "w", encoding="utf-8").write(out)
    return bad


if __name__ == "__main__":
    sys.exit(main())
