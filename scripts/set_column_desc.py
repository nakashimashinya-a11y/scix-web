#!/usr/bin/env python3
"""コラムの説明（meta description・og:description・twitter:description・Article の description）を、データの1本にそろえる。

データは scripts/data/column_desc.json（{頁: 説明}）。上位の検索の語でまだ頁に無い語（ハイフン無しの jcstar・「〜とは」・言い換え）を、
本文の中身の範囲で説明に入れた物（題と h1 は変えない・数字は本文の物だけ＝O16-8）。データに無い頁は触らない。

    python3 scripts/set_column_desc.py          # 書き換える
    python3 scripts/set_column_desc.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指示1）。
"""
import html
import json
import os
import re
import sys

import column_blocks as cb

DATA = cb.load("column_desc.json")
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
STR = re.compile(r'("description"\s*:\s*)("(?:[^"\\]|\\.)*")')


def apply(r, s):
    d = DATA.get(r)
    if not d:
        return s
    a = html.escape(d, quote=True)
    s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + a + m.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + a + m.group(2), s, count=1)
    s = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")', lambda m: m.group(1) + a + m.group(2), s, count=1)

    def ld(m):
        try:
            o = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        if not isinstance(o, dict) or o.get("@type") not in ("Article", "BlogPosting", "TechArticle", "NewsArticle") or "description" not in o:
            return m.group(0)
        old = o["description"]
        body = m.group(2)
        for x in STR.finditer(body):
            if json.loads(x.group(2)) == old:
                body = body[:x.start(2)] + json.dumps(d, ensure_ascii=False) + body[x.end(2):]
                break
        return m.group(1) + body + m.group(3)

    return LD.sub(ld, s)


if __name__ == "__main__":
    files = [os.path.join(cb.ROOT, p) for p in sorted(DATA)]
    sys.exit(cb.run_all(apply, "--check" in sys.argv, files))
