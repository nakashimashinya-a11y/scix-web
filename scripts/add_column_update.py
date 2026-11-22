#!/usr/bin/env python3
"""コラムの本文の頭（要点の枠の下）に、日付つきの「追記」の枠を差す。本文の古くなった数字の、その後の公表値を書く所。

データは scripts/data/column_update.json（{頁: {label, text, sources:[{name,url,date}], more?:{href,text}}}）。
英語の頁の出典の名前は scripts/data/column_update_src_en.json で英訳の題を添えた形に替える（原題は残す）。
書くのは公表資料（官公庁・OCCTO・EPRX・JEPX・電力会社）を原本で確かめた事と、当社の月報の数字だけ（O16-8）。
本文と h1 は触らない。<!-- scix-update:begin/end --> の目印で囲み、何度回しても同じ結果になる。

    python3 scripts/add_column_update.py          # 書き換える
    python3 scripts/add_column_update.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指示1・古い数字への追記）。
"""
import re
import sys

import column_blocks as cb

LABEL = {"ja": "2026年11月時点の追記", "en": "Update as of November 2026", "zh": "2026年11月补记"}
SRC = {"ja": "出典：", "en": "Sources: ", "zh": "出处："}
SEP = {"ja": "／", "en": "; ", "zh": "／"}
MORE = {"ja": "続きの記事：", "en": "Follow-up: ", "zh": "后续文章："}
DATA = cb.load("column_update.json")
# 英語の頁の出典: 日本語の原題だけの名前に英訳の題を添え（原題は残す）、日本語の日付の注を英語にする。
# {"names": {データの名前: 英語の頁に出す名前}, "dates": {データの日付: 英語の頁に出す日付}}
SRC_EN = cb.load("column_update_src_en.json")


def src_html(lang, x):
    if lang == "en":
        x = dict(x, name=SRC_EN["names"].get(x["name"], x["name"]),
                 date=SRC_EN["dates"].get(x.get("date") or "", x.get("date") or ""))
    own = x["url"].startswith("https://www.scix.co.jp/")
    a = (f'<a href="{cb.esc(x["url"])}" target="_top">' if own else f'<a href="{cb.esc(x["url"])}" target="_blank" rel="noopener">') + cb.esc(x["name"]) + "</a>"
    d = x.get("date") or ""
    if d and not re.search(r"\d{4}年|\d{4}-\d\d-\d\d|\d{1,2} [A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{1,2}, \d{4}", x["name"]):
        a += f" ({cb.esc(d)})" if lang == "en" else f"（{cb.esc(d)}）"
    return a


def block(lang, u):
    label = LABEL[lang]   # 言葉ごとに札の字をそろえる（データの label は使わない）
    srcs = SEP[lang].join(src_html(lang, x) for x in u.get("sources", []))
    inner = (f'<aside class="scix-update" data-scix-update><div class="su-t">{cb.esc(label)}</div>'
             f'<p>{cb.esc(u["text"])}</p>')
    if u.get("more"):
        t = u["more"]["text"].rstrip(" →")
        inner += f'<p class="su-more">{MORE[lang]}<a target="_top" href="{cb.esc(u["more"]["href"])}">{cb.esc(t)} →</a></p>'
    if srcs:
        inner += f'<p class="su-src">{SRC[lang]}{srcs}</p>'
    inner += "</aside>"
    return cb.wrap("update", inner)


def apply(r, s):
    s = cb.strip(s, "update")
    u = DATA.get(r)
    if not u:
        return s
    pos = cb.top_anchor(s)
    if pos is None:
        print("置き場が見つからない:", r)
        return s
    return cb.place(s, "update", block(cb.lang_of(r), u), pos)


if __name__ == "__main__":
    sys.exit(cb.run_all(apply, "--check" in sys.argv))
