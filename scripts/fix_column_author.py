#!/usr/bin/env python3
"""コラムの著者を1つにそろえる（構造化データと画面の著者の欄）。

  - Article の author を、/company にある Person の本体（@id https://www.scix.co.jp/company#shinya-nakashima）への参照にそろえる
    （@type・@id・name・url だけ。職名・所属・sameAs は /company の Person の本体に1つだけ置く）。url は日本語 /company・英語と中国語は /en/company。
  - 画面の著者の欄（<div class="author-box"> の .ab-name）の氏名に、同じ会社案内の頁へのリンクを付ける。
本文は触らない。何度回しても同じ結果になる。

    python3 scripts/fix_column_author.py          # 書き換える
    python3 scripts/fix_column_author.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指令5）。
"""
import json
import re
import sys

import column_blocks as cb

PID = "https://www.scix.co.jp/company#shinya-nakashima"
NAME = {"ja": "中島 晋也", "en": "Shinya Nakashima", "zh": "中岛晋也"}
URL = {"ja": "https://www.scix.co.jp/company", "en": "https://www.scix.co.jp/en/company", "zh": "https://www.scix.co.jp/en/company"}
HREF = {"ja": "/company", "en": "/en/company", "zh": "/en/company"}
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def obj_end(t, i):
    """t[i] == '{' の対の '}' の次の位置（文字列の中の括弧は数えない）。"""
    depth, instr, esc = 0, False, False
    for k in range(i, len(t)):
        c = t[k]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return None


def apply(r, s):
    lang = cb.lang_of(r)

    def ld(m):
        body = m.group(2)
        try:
            o = json.loads(body)
        except ValueError:
            return m.group(0)
        if not isinstance(o, dict) or "Article" not in str(o.get("@type")) or not isinstance(o.get("author"), dict):
            return m.group(0)
        if o["author"].get("@id") != PID:
            return m.group(0)
        a = re.search(r'"author"\s*:\s*\{', body)
        st = a.end() - 1
        en = obj_end(body, st)
        line = body[:a.start()].rsplit("\n", 1)[-1]
        ind = re.match(r"\s*", line).group(0)
        new = ("{\n" + ind + '  "@type": "Person",\n' + ind + '  "@id": "' + PID + '",\n'
               + ind + '  "name": ' + json.dumps(NAME[lang], ensure_ascii=False) + ",\n"
               + ind + '  "url": "' + URL[lang] + '"\n' + ind + "}")
        return m.group(1) + body[:st] + new + body[en:] + m.group(3)

    s = LD.sub(ld, s)
    s = re.sub(r'<span class="ab-name">(?!<a )(.*?)</span>',
               lambda m: f'<span class="ab-name"><a href="{HREF[lang]}" target="_top" rel="author">{m.group(1)}</a></span>', s, count=1)
    # 著者の欄が <div class="ab-name">氏名（肩書）…</div> の形の頁は、氏名の所だけにリンク
    s = re.sub(r'<div class="ab-name">(?!<a )(中島 晋也|中岛 ?晋也|Shinya Nakashima)',
               lambda m: f'<div class="ab-name"><a href="{HREF[lang]}" target="_top" rel="author">{m.group(1)}</a>', s, count=1)
    return s


if __name__ == "__main__":
    sys.exit(cb.run_all(apply, "--check" in sys.argv))
