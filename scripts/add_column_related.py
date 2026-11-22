#!/usr/bin/env python3
"""英語・中国語のコラムに、日本語の対と同じ「あわせて読む」と、用語集へのリンクを足す。

日本語のコラムは、1つ目の節のあとに「この記事の用語」（用語集へのリンク）と「あわせて読む」を置いている。英語・中国語のコラムには
それが無い頁が多く（あわせて読む: 英13・中65頁／用語集: 英70・中70頁）、受けのリンクが少ない頁（/en/column-day-ahead・/en/projects など）が
できていた。日本語の対の頁の「あわせて読む」の行き先を、英語・中国語の対の頁（あるものだけ）に写し、札の字は行き先の頁の h1（その言葉の題）を使う。
用語は日本語の対の頁の用語集の項目を、3つの用語集の並び（61項目が同じ順）で英語・中国語の項目に写す。

  - 日本語の対が無い頁・日本語の対の頁に「あわせて読む」が無い頁は足さない。
  - 手で作った「あわせて読む」・用語集がある頁は作り直さない（足りない行き先だけ末尾に足す）。
  - 本文は書き換えない。1つ目の節のあと（2つ目の h2 の直前）に、印のコメントつきで入れる。もう入っていれば作り直す（何度走らせても同じ）。
  - 市場の数字の話題（需給調整・容量・卸電力）の頁には、英語の市場データ・市場ノート（/en/report/data・/en/report）への静的リンクを1行
    （中国語の頁へは英語の頁である旨を添える）。/fund へは足さない（O16-67）。

語が重なる頁どうしの役割分け（2026-11-22 中島「これ全部やって。…すべて漏らさずやって。」＝Gemini の助言の指令3）:
  scripts/data/column_roles.json（[{from, to, text}]）の組を、日本語・英語・中国語のコラムの末尾（よくある質問の後・著者の箱の前）に
  「近い話題は、こちらの記事で」の1区画で張る。字は行き先の題に合わせた物（別の目を通した材料）。<!-- scix-role:begin/end --> で囲む。

    python3 scripts/add_column_related.py          # 書き換える
    python3 scripts/add_column_related.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「Seo 対策も徹底してやって」。
"""
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MARK_RN = "<!-- scix-related-block:begin -->"
MARK_END = "<!-- scix-related-block:end -->"
DATA_RE = re.compile(r"balancing|eprx|day-ahead|price-cap|bidding-ceiling|capacity|auction|^lda$|merchant|trading|long-term|revenue|area-data")

STYLE_BOX = "margin:32px 0;padding:14px 20px 10px;background:#F7F7F7;border:1px solid #E6E6E6;border-left:4px solid #C49A3C;border-radius:6px"
STYLE_GUIDE = "margin:32px 0;padding:14px 20px 12px;background:#F7F7F7;border:1px solid #E6E6E6;border-left:4px solid #C49A3C;border-radius:6px"
LINK = "display:block;color:#1F2A48;text-decoration:none;font-weight:600;font-size:14.5px;line-height:1.7;padding:6px 0"
LANGS = {
    "en": dict(pre="en/column-", url="/en/column-", gl="/en/glossary", gl_name="glossary", terms="Terms used here:", rn="Related reading",
               font="'Noto Sans JP',sans-serif", report=[("/en/report/data", "Battery Storage Market Data"), ("/en/report", "Battery Storage Market Notes")],
               numbers="Market numbers:", sep=" · ", slash=" / "),
    "zh": dict(pre="zh-column-", url="/zh-column-", gl="/zh-glossary", gl_name="术语表", terms="本文术语：", rn="相关文章",
               font="'Noto Sans SC','Noto Sans JP',sans-serif", report=[("/en/report/data", "市场数据（英文页面）"), ("/en/report", "市场笔记（英文页面）")],
               numbers="市场数字：", sep="・", slash="／"),
}
# 受けが少ない頁へ、話題の合う頁から（相手の言葉の頁・あるものだけ）。(話題の slug の正規表現, 行き先の頁) 。行き先は読み込みの札が頁の h1・題。
EXTRA = {
    "en": [
        (r"^(balancing-market|price-cap|eprx|bidding-ceiling.*|somosomo-14)$", "/en/column-day-ahead"),
        (r"^(transfer|buyer-structures|project-price|financing|options|buyer-check)$", "/en/projects"),
        (r"^(transfer|foreign-investor|buyer-structures)$", "/en/faq"),
        (r"^(foreign-investor|revenue|cashflow|financing|trading)$", "/en/primer"),
        (r"^(bidding-ceiling-calc|bidding-ceiling-law|bidding-ceiling-market)$", "/en/column-bidding-ceiling-monitoring"),
        (r"^(lda|auction|merchant|revenue|regional-revenue|long-term-contract|somosomo-10)$", "/en/column-capacity-market"),
    ],
    "zh": [
        (r"^(transfer|construction-cost|pricing|financing|options|buyer-check)$", "/zh-column-project-price"),
        (r"^(foreign-investor|revenue|cashflow|financing|trading)$", "/zh-primer"),
        (r"^(balancing-saturation-floor|balancing-saturation-supply|balancing-saturation-volume)$", "/zh-column-balancing-saturation"),
        (r"^(bidding-ceiling-calc|bidding-ceiling-law|bidding-ceiling-market)$", "/zh-column-bidding-ceiling-monitoring"),
    ],
}


def read(p):
    return open(p, encoding="utf-8").read()


def file_of(url):
    p = url.strip("/")
    return p + ".html" if os.path.isfile(p + ".html") else None


def label_of(url, lang):
    """行き先の頁の札の字。コラムは h1（<br>は空白に）、それ以外は題の「｜」「 | 」より前。"""
    f = file_of(url)
    if not f:
        return None
    s = read(f)
    if "/column-" in url:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        t = re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", re.sub(r"<(?!br)[^>]+>", "", m.group(1)))).strip() if m else None
    else:
        m = re.search(r"<title>(.*?)</title>", s, re.S)
        t = re.split(r"\s*[｜|]\s*", html.unescape(m.group(1)))[0].strip() if m else None
    return html.escape(t, quote=False) if t else None


def glossary(f):
    s = read(f)
    return [(i, re.sub(r"<[^>]+>", "", d).strip()) for i, d in re.findall(r'id="(term-[^"]+)"><dt>(.*?)(?:<span>.*?</span>)?</dt>', s, re.S)]


sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    ROLES = __import__("json").load(open(os.path.join(ROOT, "scripts", "data", "column_roles.json"), encoding="utf-8"))
except OSError:
    ROLES = []
G = {"ja": glossary("glossary.html"), "en": glossary("en/glossary.html"), "zh": glossary("zh-glossary.html")}
assert len(G["ja"]) == len(G["en"]) == len(G["zh"]), "用語集の項目の数がそろっていない"


def term_label(lang, dt):
    dt = html.unescape(dt)
    if lang == "en":
        t = re.split(r"\s+\(", dt)[0]
        if len(t) > 40:
            t = t.split(",")[0]
    else:
        t = re.split(r"[（(]", dt)[0]
        if len(t) < 2:
            t = dt
    return html.escape(t.strip(), quote=False)


def ja_pair(slug):
    f = f"column-{slug}.html"
    if not os.path.isfile(f):
        return None, [], []
    s = read(f)
    rn = re.search(r"<aside data-scix-readnext.*?</aside>", s, re.S)
    hrefs = []
    if rn:
        for h in re.findall(r'href="(/column-[a-z0-9-]+)(?:#[^"]*)?"', rn.group(0)):
            if h not in hrefs:
                hrefs.append(h)
    gd = re.search(r"<aside data-scix-guide.*?</aside>", s, re.S)
    terms = []
    if gd:
        for tid in re.findall(r'href="/glossary#(term-[^"]+)"', gd.group(0)):
            if tid not in terms:
                terms.append(tid)
    return s, hrefs, terms


def block(lang, slug, items, terms, extras_present):
    """入れる区画（あわせて読む・用語・市場の数字）。"""
    L = LANGS[lang]
    out = []
    if items:
        out.append(f"<!-- scix-readnext: {L['rn']} -->\n<aside data-scix-readnext style=\"{STYLE_BOX};font-family:{L['font']}\">\n"
                   f"  <div style=\"font-size:12px;font-weight:700;color:#555555;letter-spacing:.08em;margin-bottom:2px\">{L['rn']}</div>\n"
                   + "".join(f"  <a target=\"_top\" href=\"{u}\" style=\"{LINK}\">{t} →</a>\n" for u, t in items) + "</aside>\n")
    guide = ""
    if terms:
        links = L["sep"].join(f'<a target="_top" href="{L["gl"]}#{i}" style="color:#1F2A48">{t}</a>' for i, t in terms)
        guide += (f'  <p style="margin:0;font-size:13px;color:#555555">{L["terms"]} {links}{L["slash"]}'
                  f'<a target="_top" href="{L["gl"]}" style="color:#1F2A48">{L["gl_name"]}</a></p>\n')
    else:
        guide += (f'  <p style="margin:0;font-size:13px;color:#555555">{L["terms"]} '
                  f'<a target="_top" href="{L["gl"]}" style="color:#1F2A48">{L["gl_name"]}</a></p>\n')
    if DATA_RE.search(slug):
        nums = L["sep"].join(f'<a target="_top" href="{u}" style="color:#1F2A48;font-weight:600">{t}</a>' for u, t in L["report"])
        guide += f'  <p style="margin:8px 0 0;font-size:13px;color:#555555">{L["numbers"]} {nums}</p>\n'
    out.append(f"<!-- scix-guide: glossary -->\n<aside data-scix-guide style=\"{STYLE_GUIDE};font-family:{L['font']};font-size:14.5px;line-height:1.8;color:#1F2A48\">\n"
               + guide + "</aside>\n")
    return MARK_RN + "\n" + "".join(out) + MARK_END + "\n"


def process(path, lang):
    s = read(path)
    L = LANGS[lang]
    slug = path[len(L["pre"]):-5]
    s0 = re.sub(re.escape(MARK_RN) + r".*?" + re.escape(MARK_END) + r"\n?", "", s, flags=re.S)   # 前回の区画は作り直す
    _, ja_hrefs, ja_terms = ja_pair(slug)
    if not _:
        return s
    me = L["url"] + slug
    has_rn = "data-scix-readnext" in s0
    has_guide = "data-scix-guide" in s0
    items, seen = [], {me}
    if not has_rn:
        for h in ja_hrefs:
            u = L["url"] + h[len("/column-"):]
            if u not in seen and file_of(u):
                lb = label_of(u, lang)
                if lb:
                    items.append((u, lb)); seen.add(u)
    # 受けの少ない頁への足し（作る区画・手で作った区画のどちらにも）
    extra_urls = [u for pat, u in EXTRA[lang] if re.match(pat, slug) and u != me]
    present = set(re.findall(r'href="([^"#?]+)', re.search(r"<aside data-scix-readnext.*?</aside>", s0, re.S).group(0))) if has_rn else set()
    add_extra = []
    for u in extra_urls:
        if u not in seen and u not in present and file_of(u):
            lb = label_of(u, lang)
            if lb:
                add_extra.append((u, lb)); seen.add(u)
    if has_rn and add_extra:
        # 手で作った「あわせて読む」の末尾に足す
        def app(m):
            return m.group(0)[: -len("</aside>")] + "".join(f"  <a target=\"_top\" href=\"{u}\" style=\"{LINK}\">{t} →</a>\n" for u, t in add_extra) + "</aside>"
        s0 = re.sub(r"<aside data-scix-readnext.*?</aside>", app, s0, count=1, flags=re.S)
        add_extra = []
    items += add_extra
    ja_idx = {x[0]: i for i, x in enumerate(G["ja"])}
    terms = [(G[lang][ja_idx[t]][0], term_label(lang, G[lang][ja_idx[t]][1])) for t in ja_terms if t in ja_idx]
    need_guide = not has_guide
    # 手で作った用語集（guide）がある頁に、市場の数字の行だけ足す
    if has_guide and DATA_RE.search(slug) and "/en/report" not in re.search(r"<aside data-scix-guide.*?</aside>", s0, re.S).group(0):
        nums = L["sep"].join(f'<a target="_top" href="{u}" style="color:#1F2A48;font-weight:600">{t}</a>' for u, t in L["report"])
        line = f'  <p style="margin:8px 0 0;font-size:13px;color:#555555">{L["numbers"]} {nums}</p>\n'
        s0 = re.sub(r"(<aside data-scix-guide.*?)(</aside>)", lambda m: m.group(1) + line + m.group(2), s0, count=1, flags=re.S)
    if not items and not need_guide:
        return s0
    blk = block(lang, slug, items, terms, False)
    if not need_guide:   # 用語集は既にある＝あわせて読むだけ
        blk = blk[: blk.index("<!-- scix-guide: glossary -->")] + MARK_END + "\n"
    if not items:        # あわせて読むは既にある（または行き先が無い）＝用語集だけ
        a = blk.index("<!-- scix-guide: glossary -->")
        blk = MARK_RN + "\n" + blk[a:]
    # 入れる位置: 2つ目の h2 の直前（日本語の頁と同じ＝1つ目の節のあと）。h2 が1本以下の頁は著者の箱か CTA の前。
    h2 = [m.start() for m in re.finditer(r"<h2\b", s0[s0.find('class="article-body"') if 'class="article-body"' in s0 else 0:])]
    base = s0.find('class="article-body"') if 'class="article-body"' in s0 else 0
    if len(h2) >= 2:
        pos = base + h2[1]
    else:
        m = re.search(r'<div class="author-box"|<div class="cta-section"|<section class="cta', s0)
        if not m:
            print("入れる位置が見つからない:", path)
            return s0
        pos = m.start()
    return s0[:pos] + blk + s0[pos:]


ROLE_H = {"ja": "近い話題は、こちらの記事で", "en": "Covered in more detail elsewhere", "zh": "相关话题，详见以下文章"}


def roles_apply(r, s):
    import column_blocks as cb
    s = cb.strip(s, "role")
    me = cb.url_of(r)
    links = [x for x in ROLES if x["from"] == me]
    if not links:
        return s
    lang = cb.lang_of(r)
    items = "".join('<a target="_top" href="%s">%s →</a>' % (html.escape(x["to"]), html.escape(re.sub(r"\s*→\s*$", "", x["text"]), quote=False))
                    for x in links)
    pos = cb.end_anchor(s)
    if pos is None:
        print("役割分けの置き場が見つからない:", r)
        return s
    blk = cb.wrap("role", f'<aside class="scix-role" data-scix-role><div class="sr-t">{ROLE_H[lang]}</div>{items}</aside>')
    return cb.place(s, "role", blk, pos)


def main():
    check = "--check" in sys.argv
    bad = 0
    for lang, L in LANGS.items():
        for p in sorted(glob.glob(L["pre"] + "*.html")):
            s = read(p)
            out = process(p, lang)
            if out != s:
                if check:
                    print("ずれ:", p); bad = 1
                else:
                    open(p, "w", encoding="utf-8").write(out)
    import column_blocks as cb
    bad = max(bad, cb.run_all(roles_apply, check))
    return bad


if __name__ == "__main__":
    sys.exit(main())
