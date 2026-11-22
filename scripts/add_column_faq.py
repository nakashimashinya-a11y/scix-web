#!/usr/bin/env python3
"""コラムの末尾に「よくある質問」を画面に出す（検索の語で足りない問いを、本文の答えで）。

データは scripts/data/column_faq.json（{頁: [{q, a, link?}]}）。答えは本文の言い方と数字だけで作った物（O16-8）。
  - 頁に「よくある質問」の節が前からあれば、その節の最後の問いの後ろに足す（前からある問いの形＝faq-item・h3・highlight-box に合わせる）。
  - 無ければ、著者の箱の直前に新しい節を置く。
  - FAQPage の構造化データは新しく足さない（Google が 2026-05-07 に検索結果での表示を終えた）。前から FAQPage がある頁だけ、
    足した問いを同じ文で FAQPage にも入れ、画面と構造化データを同じに保つ。
本文と h1 は触らない。<!-- scix-faq:begin/end --> の目印で囲み、何度回しても同じ結果になる。

    python3 scripts/add_column_faq.py          # 書き換える
    python3 scripts/add_column_faq.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指示3）。
"""
import json
import os
import re
import sys

import column_blocks as cb

H2 = {"ja": "よくある質問", "en": "Frequently asked questions", "zh": "常见问题"}
PDF = {"ja": "原本（PDF）", "en": "Source (PDF)", "zh": "原文（PDF）"}
FAQ_H2 = re.compile(r"<h2[^>]*>[^<]*(?:よくある質問|FAQ|Frequently [Aa]sked|常见问题)[^<]*</h2>")
DATA = cb.load("column_faq.json")
JSONLD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def label_of(url):
    """内側の頁へのリンクの字＝行き先の h1（無ければ title の「｜」の前）。"""
    p = url.split("#")[0].strip("/")
    f = os.path.join(cb.ROOT, p + ".html")
    if not os.path.isfile(f):
        return None
    s = open(f, encoding="utf-8").read()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    if m:
        t = re.sub(r"<br\s*/?>", " ", m.group(1))
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()
    else:
        m = re.search(r"<title>(.*?)</title>", s, re.S)
        t = re.split(r"\s*[｜|]\s*", m.group(1))[0].strip() if m else None
    import html as _h
    return _h.unescape(t) if t else None


def link_html(lang, link):
    if link.startswith("http"):
        return f' <a href="{cb.esc(link)}" target="_blank" rel="noopener">{PDF[lang] if link.lower().endswith(".pdf") else cb.esc(link)} →</a>'
    t = label_of(link)
    return f' <a target="_top" href="{cb.esc(link)}">{cb.esc(t)} →</a>' if t else ""


def item(style, lang, q):
    a = cb.esc(q["a"]) + (link_html(lang, q["link"]) if q.get("link") else "")
    if style == "h3q":
        return f"<h3>Q. {cb.esc(q['q'])}</h3>\n<p>{a}</p>\n"
    if style == "hl-h4":
        return f'<div class="highlight-box">\n<h4>{cb.esc(q["q"])}</h4>\n<p style="margin:8px 0 0">{a}</p>\n</div>\n'
    if style == "hl-zh":
        return f'<div class="highlight-box">\n<strong>问：{cb.esc(q["q"])}</strong><br>\n答：{a}\n</div>\n'
    if style == "div":
        return f'<div class="faq-item">\n  <div class="faq-q">{cb.esc(q["q"])}</div>\n  <div class="faq-a">{a}</div>\n</div>\n'
    return f'<div class="faq-item"><h3 class="faq-q">{cb.esc(q["q"])}</h3><p class="faq-a">{a}</p></div>\n'


def div_end(s, start):
    """start の <div の閉じ </div> の終わりの位置。"""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", s[start:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return start + m.end()
    return None


def existing_section(s):
    """前からある「よくある質問」の節: (問いの形, 最後の問いの終わり) か None。"""
    m = FAQ_H2.search(s, cb.h1_end(s))
    if not m:
        return None
    rest = s[m.end():]
    ends = [x for x in (rest.find("<h2"), rest.find('<div class="author-box"'), rest.find("<!-- scix-")) if x >= 0]
    sec = rest[: min(ends)] if ends else rest
    base = m.end()
    if '<div class="faq-item"' in sec:
        st = base + sec.rfind('<div class="faq-item"')
        return "div", div_end(s, st)
    if re.search(r"<h3>Q\.", sec):
        st = base + [x.start() for x in re.finditer(r"<h3>Q\.", sec)][-1]
        e = s.find("</p>", st)
        return "h3q", e + 4
    if '<div class="highlight-box">' in sec:
        st = base + sec.rfind('<div class="highlight-box">')
        inner = s[st:div_end(s, st)]
        return ("hl-h4" if "<h4>" in inner else "hl-zh"), div_end(s, st)
    return None


def plain(t):
    return re.sub(r"\s+", " ", t).strip()


def fix_jsonld(s, items):
    """前からある FAQPage に、画面に足した問いを同じ文で入れる（無い頁には足さない）。"""
    names = {plain(q["q"]) for q in items}

    def sub(m):
        body = m.group(2)
        if '"FAQPage"' not in body:
            return m.group(0)
        try:
            o = json.loads(body)
        except ValueError:
            return m.group(0)
        if not isinstance(o, dict) or o.get("@type") != "FAQPage":
            return m.group(0)
        ents = [e for e in o.get("mainEntity", []) if plain(e.get("name", "")) not in names]
        ents += [{"@type": "Question", "name": plain(q["q"]), "acceptedAnswer": {"@type": "Answer", "text": plain(q["a"])}} for q in items]
        o["mainEntity"] = ents
        return m.group(1) + "\n" + json.dumps(o, ensure_ascii=False, indent=2) + "\n" + m.group(3)

    return JSONLD.sub(sub, s)


def apply(r, s):
    s = cb.strip(s, "faq")
    items = DATA.get(r)
    if not items:
        return s
    lang = cb.lang_of(r)
    ex = existing_section(s)
    if ex and ex[1]:
        style, at = ex
        if s[at:at + 1] == "\n":
            at += 1
        blk = cb.wrap("faq", "".join(item(style, lang, q) for q in items))
        s = s[:at] + blk + s[at:]
    else:
        pos = cb.end_anchor(s)
        if pos is None:
            print("置き場が見つからない:", r)
            return s
        idattr = ' id="faq"' if 'id="faq"' not in s else ""
        inner = (f'<section class="scix-faq" data-scix-faq{idattr}>\n<h2>{H2[lang]}</h2>\n'
                 + "".join(item("new", lang, q) for q in items) + "</section>")
        s = cb.place(s, "faq", cb.wrap("faq", inner), pos)
    return fix_jsonld(s, items)


if __name__ == "__main__":
    sys.exit(cb.run_all(apply, "--check" in sys.argv))
