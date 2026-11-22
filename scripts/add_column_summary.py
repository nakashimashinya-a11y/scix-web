#!/usr/bin/env python3
"""コラムの本文の頭（h1 の下・本文の前）に「3行で言うと」の要点の枠を差す。

データは scripts/data/column_summary.json（{頁: [3行]}）。3行は本文の言い方と数字だけで作った物（O16-8）。
本文と h1 は触らない。<!-- scix-summary:begin/end --> の目印で囲み、何度回しても同じ結果になる。
データに無い頁は、前に差した枠があれば消すだけ（頁の中に元からある .sum3 には触らない）。

    python3 scripts/add_column_summary.py          # 書き換える
    python3 scripts/add_column_summary.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指示3）。
"""
import sys

import column_blocks as cb

LABEL = {"ja": "3行で言うと", "en": "In three lines", "zh": "三句话说清"}
DATA = cb.load("column_summary.json")


def block(lang, lines):
    lis = "".join(f"<li>{cb.esc(x)}</li>" for x in lines)
    return cb.wrap("summary", f'<div class="sum3" data-scix-summary><div class="s3-t">{LABEL[lang]}</div><ol>{lis}</ol></div>')


def apply(r, s):
    s = cb.strip(s, "summary")
    lines = DATA.get(r)
    if not lines:
        return s
    pos = cb.top_anchor(s)
    if pos is None:
        print("置き場が見つからない:", r)
        return s
    return cb.place(s, "summary", block(cb.lang_of(r), lines), pos)


if __name__ == "__main__":
    sys.exit(cb.run_all(apply, "--check" in sys.argv))
