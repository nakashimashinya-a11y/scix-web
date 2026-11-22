#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""柱の頁（まとまりの案内）を、文のデータ scripts/data/guides/<slug>.<lang>.md から作る。

作る頁: guide-<名>.html（日本語）・en/guide-<名>.html（英語）・zh-guide-<名>.html（中国語）。データがある言葉だけ。
中身は、当社のコラムの要点を知りたい順に並べた案内（コラムの原稿ではない＝O16-1）。文はデータのとおりに出し、言い換えない・足さない。
生成器が足すのは決まった枠だけ: 冒頭の「3行で言うと」・目次・導線（最初の見出しの前と末尾・data-cta つき）・このまとまりのコラムの一覧・
画面の「よくある質問」・パンくず・構造化データ（CollectionPage＋BreadcrumbList＋ItemList。著者・発行は Organization の @id）。
Article・FAQPage・HowTo は付けない（FAQPage は 2026-05-07 に Google が検索結果での表示を終えた）。「監修」とは書かない。

文のデータの書き方（scripts/data/guides/<slug>.<lang>.md）:
    ---
    slug / lang / title / h1 / h1_sub（任意）/ description / columns（まとまりのコラム。カンマ区切り）/ published / modified
    ---
    ## @lead   頁の冒頭の1段（無ければ description を出す）
    ## @tldr   3行で言うと（「- 」の行）
    ## @top    最初の見出しの前の導線の文（任意。無ければ言葉ごとの決まった文）
    ## <章の題>  本文。「more: 」で始まる行は「くわしくは」の行。[](/path) は行き先の頁の題で埋める
    ## @next   末尾の導線
    ## @faq    「### 問い」＋答え
本文の書式: 段落・「- 」の並び（字下げの行は続き）・「1. 」の番号の並び・| の表・### の小見出し・**太字**・[字](住所)・裸の URL・
「→ [字](住所)」の行（ボタン風のリンク）・「出典:」「Sources:」「出处：」で始まる行（出典の行）。

    python3 scripts/build_guides.py          # 頁を書く
    python3 scripts/build_guides.py --check  # 書かずに、頁がデータとずれていないか・決まりに触れていないかを見る（あれば 1）

2026-11-22 中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」（Gemini の助言の指令1＝まとまりと柱の頁）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_ga_tag as ga_tag  # noqa: E402  GA の区画（全頁で同じ形）

DATA = os.path.join(ROOT, "scripts", "data", "guides")
BASE = "https://www.scix.co.jp"
MARKET = "dealroom.scix.co.jp"
ORG_ID = BASE + "/#organization"
SITE_ID = BASE + "/#website"

FONT_JA = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&display=swap"
FONT_ZH = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&family=Noto+Sans+SC:wght@400;500;700;900&display=swap"

L = {
    "ja": dict(
        html_lang="ja", in_lang="ja", hreflang="ja", og_locale="ja_JP", og_img="/img/ogp-m.png", font=FONT_JA,
        family="'Noto Sans JP',sans-serif", home=("ホーム", "/"), kn=("ナレッジ", "/knowledge"),
        back="← ナレッジ一覧に戻る", tag="ガイド", date_label="作成", tldr="3行で言うと", toc="この頁の目次",
        faq="よくある質問", cols="このテーマのコラム（{n}本）", next="次にすること", logo_alt="ScienceX",
        top=("いま売りに出ている案件は、蓄電所マーケットで登録なしで見られます。所在県・規模・電圧・買い方・手続きの段・運転開始の見込みまで載せています。"
             "価格と資料は無料登録のあとです。"),
        top_btn=("蓄電所マーケットで案件を見る →", "https://dealroom.scix.co.jp/"),
        top_sub=("接続検討の回答が出た案件をお持ちの方は、当社が買い取るか、買い手におつなぎします。",
                 [("案件・権利の売却査定（無料）", "/sell-form"), ("お問い合わせ", "/contact")], "・"),
        contact=("ご質問・個別のご相談は", "お問い合わせ", "/contact", "から。"),
        cols_note="各コラムに、数字の集計の窓と出典があります。",
    ),
    "en": dict(
        html_lang="en", in_lang="en", hreflang="en", og_locale="en_US", og_img="/img/ogp-m-en.png", font=FONT_JA,
        family="'Noto Sans JP',sans-serif", home=("Home", "/en"), kn=("Knowledge", "/en/knowledge"),
        back="← Back to Knowledge", tag="Guide", date_label="Published", tldr="In three lines", toc="On this page",
        faq="Frequently asked questions", cols="Columns in this guide ({n})", next="What to do next", logo_alt="ScienceX",
        top=("If you are buying, grid-scale BESS projects in Japan that hold a connection study response are for sale on Chikudensho Market, "
             "open to view without registration. If you are selling, we either buy the project ourselves or introduce you to a buyer."),
        top_btn=("See projects on Chikudensho Market →", "https://dealroom.scix.co.jp/en"),
        top_sub=("Questions are welcome through the contact form.", [("Contact us", "/en/contact")], " · "),
        contact=("Questions are welcome through the", "contact form", "/en/contact", "."),
        cols_note="Each column gives the data window and sources for its figures.",
    ),
    "zh": dict(
        html_lang="zh-CN", in_lang="zh-CN", hreflang="zh-CN", og_locale="zh_CN", og_img="/img/ogp-m-zh.png", font=FONT_ZH,
        family="'Noto Sans SC','Noto Sans JP',sans-serif", home=("首页", "/zh"), kn=("洞见", "/zh-knowledge"),
        back="← 返回洞见一览", tag="指南", date_label="发布", tldr="三句话说清", toc="本页目录",
        faq="常见问题", cols="本主题的专栏（{n}篇）", next="下一步", logo_alt="ScienceX",
        top=("所在县、规模、电压、购买方式、手续阶段与预计投运时间，无需登记即可在蓄电所市场（Chikudensho Market）查看；"
             "所列仅限已取得接入系统研究答复的项目。蓄电所市场的画面只有日文和英文，中文读者请用英文画面。"),
        top_btn=("在蓄电所市场（Chikudensho Market）查看案件 →", "https://dealroom.scix.co.jp/en"),
        top_sub=("持有已取得接入系统研究答复的项目，可由本公司收购，或为您介绍买方。", [("联系我们", "/zh-contact")], "・"),
        contact=("如有疑问，欢迎通过", "联系我们", "/zh-contact", "咨询。"),
        cols_note="各专栏写明了数字的统计区间与出处。",
    ),
}
SUFFIX_RX = re.compile(r"\s*(｜|\|)\s*(サイエンスエックス|ScienceX|Science X)\s*$")

# 決まりに触れる語（頁の画面の文で見る）。どれか1つでも出たら --check が止める。
BANNED = [
    (re.compile(r"中立|neutral", re.I), "「中立」を自称しない（O16-10）"),
    (re.compile(r"監修|监修|supervised by", re.I), "「監修」と書かない"),
    (re.compile(r'href="/fund'), "/fund へのリンクを足さない（O16-67）"),
    (re.compile(r"利回り|GK-TK|TK-GK|匿名組合|仕入れて売|resell|买断|转售|采购并出售", re.I), "書かない語（O16-8・O16-10・O16-69）"),
    (re.compile(r"(手数料|手续费|佣金|commission|fee)[^。.\n]{0,20}\d+(\.\d+)?\s*[%％]", re.I), "手数料の率を書かない（O16-8）"),
    (re.compile(r"IRR[^。.\n]{0,20}\d+(\.\d+)?\s*[%％]"), "IRR の数字を書かない（O16-8）"),
    (re.compile(r"土地の持ち主|土地をお持ちの方|地主の方|for landowners|landowners? (?:who|looking)|土地所有者朋友|土地的所有者", re.I), "土地の持ち主を呼ばない（O16-5）"),
]


# ---------------- データを読む ----------------
def read_data(path: str) -> dict:
    t = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        raise SystemExit(f"front matter が無い: {path}")
    fm = {}
    for ln in m.group(1).splitlines():
        k, _, v = ln.partition(":")
        fm[k.strip()] = v.strip()
    secs, cur = [], None
    for ln in t[m.end():].splitlines():
        if ln.startswith("## "):
            cur = [ln[3:].strip(), []]
            secs.append(cur)
        elif cur is not None:
            cur[1].append(ln.rstrip())
    fm["columns"] = [c.strip() for c in fm.get("columns", "").split(",") if c.strip()]
    fm["sections"] = secs
    return fm


def path_of(slug: str, lang: str) -> str:
    return {"ja": "/" + slug, "en": "/en/" + slug, "zh": "/zh-" + slug}[lang]


def file_of(p: str) -> str | None:
    """サイトの住所（/…・#・? を除く）→ リポジトリのファイル（無ければ None）。"""
    p = p.split("#")[0].split("?")[0].strip("/")
    for cand in ([p + ".html", p + "/index.html"] if p else ["index.html"]):
        if os.path.isfile(os.path.join(ROOT, cand)):
            return cand
    return None


_TITLES: dict = {}


def short_title(t: str) -> str:
    """一覧の札の字: 題の最初の区切り（—・──）の前。前が短すぎれば題のまま。"""
    m = re.split(r"\s*(?:──|—)\s*", t, maxsplit=1)
    return m[0] if len(m) > 1 and len(m[0]) >= 6 else t


def page_title(p: str, generated: dict) -> str:
    """行き先の頁の題（<title> から会社名を落とした物）。このとき作る頁はその題。"""
    key = p.split("#")[0].rstrip("/") or "/"
    if key in generated:
        return generated[key]
    if key not in _TITLES:
        f = file_of(key)
        t = ""
        if f:
            s = open(os.path.join(ROOT, f), encoding="utf-8").read()
            m = re.search(r"<title>(.*?)</title>", s, re.S)
            t = SUFFIX_RX.sub("", html.unescape(m.group(1)).strip()) if m else ""
        _TITLES[key] = t
    return _TITLES[key]


# ---------------- 文を HTML に ----------------
def cta_target(href: str) -> str:
    if MARKET in href:
        return "market"
    h = href.split("#")[0].split("?")[0]
    if h == "/sell-form":
        return "sell_form"
    if h in ("/contact", "/en/contact", "/zh-contact"):
        return "contact"
    return ""


def a_tag(text: str, href: str, cta: str | None, cls: str = "") -> str:
    attrs = [f'href="{html.escape(href, quote=True)}"']
    if href.startswith("http") and MARKET not in href and "www.scix.co.jp" not in href:
        attrs.append('target="_blank" rel="noopener"')
    else:
        attrs.append('target="_top"')
    if cls:
        attrs.append(f'class="{cls}"')
    if cta:
        attrs.append(f'data-cta="{cta}"')
        t = cta_target(href)
        if t:
            attrs.append(f'data-cta-target="{t}"')
    return f"<a {' '.join(attrs)}>{text}</a>"


def inline(s: str, ctx: dict) -> str:
    """**太字**・[字](住所)・裸の URL。字は HTML に逃がす。"""
    links = []

    def keep_link(m):
        text, href = m.group(1), m.group(2)
        if not text:
            text = page_title(href, ctx["generated"]) or href
            if not page_title(href, ctx["generated"]):
                ctx["errors"].append(f"{ctx['where']}: 題を引けないリンク {href}")
        links.append((text, href))
        return f"\x00{len(links) - 1}\x00"

    s = re.sub(r"\[([^\]]*)\]\(([^)\s]+)\)", keep_link, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def bare(m):
        u = m.group(0)
        links.append((u, u))
        return f"\x00{len(links) - 1}\x00"

    s = re.sub(r"https?://[A-Za-z0-9._~:/?#@!$&'*+,;=%-]+[A-Za-z0-9/_=-]", bare, s)

    def back(m):
        text, href = links[int(m.group(1))]
        ctx["links"].append(href)
        inner = text if "\x00" in text else html.escape(text, quote=False)
        inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)
        return a_tag(inner, href, ctx.get("cta"))

    return re.sub(r"\x00(\d+)\x00", back, s)


def blocks(lines: list, ctx: dict) -> str:
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(x, ctx) for x in para) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("more: "):
            flush()
            out.append('<p class="guide-more">' + inline(s[6:], ctx) + "</p>")
            i += 1; continue
        if s.startswith("→ "):
            flush()
            out.append('<p class="guide-go">' + inline(s, ctx) + "</p>")
            i += 1; continue
        if re.match(r"^(出典|Sources|出处)\s*[:：]", s):
            flush()
            out.append('<div class="source">' + inline(s, ctx) + "</div>")
            i += 1; continue
        if s.startswith("### "):
            flush()
            out.append("<h3>" + inline(s[4:], ctx) + "</h3>")
            i += 1; continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            h = "".join(f'<th scope="col">{inline(c, ctx)}</th>' for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f'<div class="table-wrap"><table class="comparison-table"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        m_ul = re.match(r"^- (.*)$", ln)
        m_ol = re.match(r"^\d+\. (.*)$", ln)
        if m_ul or m_ol:
            flush()
            tag = "ul" if m_ul else "ol"
            items = []
            while i < len(lines):
                cur = lines[i]
                mm = re.match(r"^- (.*)$", cur) if tag == "ul" else re.match(r"^\d+\. (.*)$", cur)
                if mm:
                    items.append([mm.group(1)])
                elif cur.startswith("  ") and cur.strip() and items:
                    items[-1].append(cur.strip())
                else:
                    break
                i += 1
            lis = "".join("<li>" + "<br>".join(inline(x, ctx) for x in it) + "</li>" for it in items)
            out.append(f"<{tag}>{lis}</{tag}>")
            continue
        para.append(s)
        i += 1
    flush()
    return "\n".join(out)


def faq_items(lines: list, ctx: dict):
    items, cur = [], None
    for ln in lines:
        if ln.startswith("### "):
            cur = [ln[4:].strip(), []]
            items.append(cur)
        elif cur is not None:
            cur[1].append(ln)
    return [(q, blocks(a, ctx)) for q, a in items]


# ---------------- 頁を組む ----------------
CSS = """:root{--navy:#1F2A48;--navy-light:#2D3A5C;--accent:#C49A3C;--accent-light:#D4AF5C;--green:#1A7A4C;--text:#1F2A48;--text-light:#666666;--light-bg:#F7F7F7;--border:#E6E6E6;--white:#FFFFFF}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:%(family)s;color:var(--text);line-height:1.95;background:var(--white);font-size:15.5px}
.article-header{background:linear-gradient(165deg,#141B30 0%%,var(--navy) 45%%,var(--navy-light) 100%%);padding:72px 24px 64px;text-align:center;position:relative}
.article-header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:var(--accent)}
.header-inner{max-width:720px;margin:0 auto}
.header-meta{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:20px}
.header-tag{display:inline-block;padding:4px 14px;background:rgba(196,154,60,0.15);color:var(--accent-light);font-size:12px;font-weight:600;letter-spacing:0.08em;border-radius:2px}
.header-date{font-size:13px;color:rgba(255,255,255,0.5);letter-spacing:.05em}
.article-header h1{font-size:clamp(22px,4vw,32px);font-weight:600;color:var(--white);line-height:1.55;margin-bottom:16px}
.article-header h1 em{font-style:normal;color:var(--accent-light)}
.header-desc{font-size:14px;color:rgba(255,255,255,0.6);line-height:1.85;max-width:560px;margin:0 auto}
.article-body{max-width:720px;margin:0 auto;padding:48px 24px 80px}
h2{font-size:1.35em;font-weight:600;color:var(--navy);margin:48px 0 16px;padding-bottom:10px;border-bottom:2px solid var(--accent);line-height:1.5}
h3{font-size:1.05em;font-weight:600;color:var(--navy);margin:28px 0 10px;line-height:1.5}
p{margin-bottom:20px}
ul,ol{margin:0 0 20px 1.4em}
li{margin-bottom:8px}
.highlight-box{background:var(--light-bg);border-left:4px solid var(--accent);padding:24px 28px;margin:28px 0;border-radius:0 6px 6px 0;font-size:.95em;line-height:2}
.highlight-box .box-label{font-weight:700;color:var(--navy);margin-bottom:6px}
.highlight-box ul{margin-bottom:0}
.source{font-size:.78em;color:var(--text-light);margin:-8px 0 20px}
.table-wrap{overflow-x:auto;margin:28px 0}
.comparison-table{width:100%%;border-collapse:collapse;font-size:.88em}
.comparison-table th{background:var(--navy);color:#fff;padding:12px 16px;text-align:left;font-weight:500;font-size:.88em}
.comparison-table td{padding:12px 16px;border-bottom:1px solid var(--border);vertical-align:top}
.comparison-table tr:nth-child(even){background:var(--light-bg)}
.guide-more{font-size:.9em;background:var(--light-bg);border:1px solid var(--border);border-radius:6px;padding:10px 16px}
.guide-more a,.guide-go a,.article-body p a,.article-body li a{color:var(--navy);font-weight:600;text-decoration:none;border-bottom:1px solid var(--accent)}
.guide-go{font-weight:600}
.guide-toc{margin:28px 0;padding:16px 22px;border:1px solid var(--border);border-radius:6px;font-size:.92em}
.guide-toc .box-label{font-weight:700;margin-bottom:6px}
.guide-toc ol{margin:0 0 0 1.4em}
.guide-toc li{margin-bottom:2px}
.guide-toc a{color:var(--navy);text-decoration:none}
.guide-cta-top{margin:28px 0;padding:18px 22px;background:#F7F7F7;border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:6px;font-size:.95em;line-height:1.85}
.guide-cta-top p{margin-bottom:12px}
.guide-cta-top .sub{margin:12px 0 0;font-size:.92em;color:#555555}
.cta-btn{display:inline-block;background:var(--accent);color:#1F2A48;padding:12px 28px;border-radius:4px;font-weight:700;font-size:.92em;text-decoration:none}
.guide-cols ul{list-style:none;margin:0;padding:0}
.guide-cols li{border-bottom:1px solid var(--border);margin:0;padding:10px 0}
.guide-cols li a{color:var(--navy);font-weight:600;text-decoration:none}
.guide-cols .note{font-size:.85em;color:var(--text-light)}
.faq-item{border-bottom:1px solid var(--border);padding:20px 0}
.faq-item:last-child{border-bottom:none}
.faq-q{font-weight:700;color:var(--navy);margin-bottom:10px}
.faq-q::before{content:'Q. ';color:var(--accent)}
.faq-a{font-size:.95em;color:var(--text)}
.faq-a p:last-child{margin-bottom:0}
.back-link{display:inline-flex;align-items:center;gap:6px;color:var(--accent);text-decoration:none;font-size:.88em;font-weight:500;margin-bottom:32px}
.cta-section{background:linear-gradient(160deg,var(--navy),var(--navy-light));padding:40px 28px;border-radius:8px;margin-top:48px}
.cta-section h2{color:#fff;border-bottom:0;margin:0 0 16px;padding:0}
.cta-section p,.cta-section li{color:rgba(255,255,255,.8)}
@media(max-width:768px){.article-body{padding:32px 16px 60px}h2{font-size:1.2em}.comparison-table{font-size:.8em}.comparison-table th,.comparison-table td{padding:8px 10px}}
"""


def jsonld(o) -> str:
    return '<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>"


def render(d: dict, langs: set, generated: dict) -> tuple[str, list, list]:
    lg = d["lang"]
    c = L[lg]
    slug = d["slug"]
    me = path_of(slug, lg)
    url = BASE + me
    ctx = {"generated": generated, "errors": [], "links": [], "where": f"{slug}.{lg}", "cta": None}
    secs = d["sections"]
    sec = {k: v for k, v in secs if k.startswith("@")}
    chapters = [(k, v) for k, v in secs if not k.startswith("@")]
    title, desc, h1 = d["title"], d["description"], d["h1"]

    # 冒頭
    lead = sec.get("@lead")
    head_desc = " ".join(x.strip() for x in lead if x.strip()) if lead else desc
    h1_html = html.escape(h1) + (f'<br><em>{html.escape(d["h1_sub"])}</em>' if d.get("h1_sub") else "")
    tldr = blocks(sec.get("@tldr", []), ctx)

    # 最初の見出しの前の導線
    ctx["cta"] = "top"
    top_lines = [x for x in sec.get("@top", []) if x.strip()]
    top_text = [x for x in top_lines if not x.strip().startswith("→ ")]
    if top_text:
        top_p = blocks(top_text, ctx)
    else:
        top_p = "<p>" + html.escape(c["top"]) + "</p>"
    btn = a_tag(html.escape(c["top_btn"][0]), c["top_btn"][1], "top", "cta-btn")
    ctx["links"].append(c["top_btn"][1])
    sub_txt, sub_links, sep = c["top_sub"]
    sub = html.escape(sub_txt) + " " + sep.join(a_tag(html.escape(t), h, "top") for t, h in sub_links)
    ctx["links"] += [h for _, h in sub_links]
    top_html = f'<aside class="guide-cta-top" data-scix-guide-cta="top">\n{top_p}\n<p>{btn}</p>\n<p class="sub">{sub}</p>\n</aside>'
    ctx["cta"] = None

    # 目次と章
    toc, body = [], []
    for n, (k, v) in enumerate(chapters, 1):
        hid = f"g{n}"
        toc.append(f'<li><a href="#{hid}">{html.escape(k)}</a></li>')
        ctx["where"] = f"{slug}.{lg} §{n}"
        body.append(f'<h2 id="{hid}">{n}. {html.escape(k)}</h2>\n' + blocks(v, ctx))
    toc.append(f'<li><a href="#cols">{html.escape(c["cols"].format(n=len(d["columns"])))}</a></li>')
    toc.append(f'<li><a href="#faq">{html.escape(c["faq"])}</a></li>')

    # まとまりのコラムの一覧（ItemList と同じ物を画面に）
    items = []
    for cs in d["columns"]:
        p = "/" + cs
        t = short_title(page_title(p, generated))
        if not file_of(p) or not t:
            ctx["errors"].append(f"{slug}.{lg}: まとまりのコラムが無い {p}")
            continue
        items.append((p, t))
    cols_html = "\n".join(f'<li>{a_tag(html.escape(t), p, None)}</li>' for p, t in items)
    ctx["links"] += [p for p, _ in items]

    # よくある質問（画面に出す。FAQPage は付けない）
    ctx["where"] = f"{slug}.{lg} faq"
    faqs = faq_items(sec.get("@faq", []), ctx)
    faq_html = "\n".join(f'<div class="faq-item">\n  <div class="faq-q">{html.escape(q)}</div>\n  <div class="faq-a">{a}</div>\n</div>' for q, a in faqs)

    # 末尾の導線
    ctx["cta"] = "end"
    ctx["where"] = f"{slug}.{lg} next"
    n0 = len(ctx["links"])
    nxt = blocks(sec.get("@next", []), ctx)
    end_links = ctx["links"][n0:]
    pre, lab, href, post = c["contact"]
    if not any(cta_target(h) == "contact" for h in end_links):
        nxt += f'\n<p>{html.escape(pre)} {a_tag(html.escape(lab), href, "end")}{html.escape(post)}</p>'
        ctx["links"].append(href)
        end_links.append(href)
    ctx["cta"] = None
    end_html = f'<div class="cta-section" data-scix-guide-cta="end">\n<h2>{html.escape(c["next"])}</h2>\n{nxt}\n</div>'

    # head
    alts = [(L[x]["hreflang"], BASE + path_of(slug, x)) for x in ("ja", "en", "zh") if x in langs]
    xdef = BASE + path_of(slug, "en" if "en" in langs else "ja")
    alt_html = "\n".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in alts)
    alt_html += f'\n<link rel="alternate" hreflang="x-default" href="{xdef}">'
    org = {"@type": "Organization", "@id": ORG_ID, "name": "Science X Inc.", "alternateName": "サイエンスエックス株式会社",
           "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + "/img/logo-navy.png"}}
    ld_page = {
        "@context": "https://schema.org", "@type": "CollectionPage", "@id": url + "#webpage", "url": url,
        "name": title, "description": desc, "inLanguage": c["in_lang"],
        "isPartOf": {"@type": "WebSite", "@id": SITE_ID, "url": BASE + "/", "name": "ScienceX"},
        "author": org, "publisher": {"@id": ORG_ID},
        "datePublished": d["published"], "dateModified": d["modified"],
        "image": {"@type": "ImageObject", "url": BASE + c["og_img"], "width": 1200, "height": 630},
        "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#itemlist"},
    }
    ld_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": c["home"][0], "item": BASE + (c["home"][1] if c["home"][1] != "/" else "/")},
        {"@type": "ListItem", "position": 2, "name": c["kn"][0], "item": BASE + c["kn"][1]},
        {"@type": "ListItem", "position": 3, "name": h1, "item": url}]}
    ld_list = {"@context": "https://schema.org", "@type": "ItemList", "@id": url + "#itemlist", "name": c["cols"].format(n=len(items)),
               "numberOfItems": len(items), "itemListElement": [
                   {"@type": "ListItem", "position": i, "url": BASE + p, "name": t} for i, (p, t) in enumerate(items, 1)]}
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    crumb = (f'<nav data-scix-breadcrumb aria-label="breadcrumb" style="max-width:760px;margin:0 auto;padding:14px 24px 0;font-family:{c["family"]};'
             f'font-size:12.5px;line-height:1.6;color:#8C8C8C"><a href="{c["home"][1]}" style="color:#555555;text-decoration:none">{e(c["home"][0])}</a>'
             f'<span style="color:#C49A3C;margin:0 7px">›</span><a href="{c["kn"][1]}" style="color:#555555;text-decoration:none">{e(c["kn"][0])}</a>'
             f'<span style="color:#C49A3C;margin:0 7px">›</span><span style="color:#8C8C8C">{e(h1)}</span></nav>')
    footer = open(os.path.join(DATA, "_parts", f"footer.{lg}.part"), encoding="utf-8").read().rstrip("\n")
    date_disp = d["published"].replace("-", ".")
    page = f"""<!DOCTYPE html>
<html lang="{c['html_lang']}">
<head>
<link rel="icon" type="image/svg+xml" href="/img/favicon.svg">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
{ga_tag.BLOCK}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- scripts/build_guides.py が scripts/data/guides/{slug}.{lg}.md から作る頁（手で直さない） -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{c['font']}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{c['font']}"></noscript>
<style>
{CSS % {"family": c["family"]}}</style>
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">
{alt_html}
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}{c['og_img']}">
<meta property="og:site_name" content="ScienceX">
<meta property="og:locale" content="{c['og_locale']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{BASE}{c['og_img']}">
{jsonld(ld_page)}
{jsonld(ld_bc)}
{jsonld(ld_list)}
<link rel="stylesheet" href="/theme.css">
</head>
<body>
<script src="/header.js"></script>
{crumb}
<div class="article-header">
  <div class="header-inner">
    <div class="header-meta">
      <span class="header-tag">{e(c['tag'])}</span>
      <time class="header-date" datetime="{d['published']}">{e(c['date_label'])} {date_disp}</time>
    </div>
    <h1>{h1_html}</h1>
    <p class="header-desc">{e(head_desc)}</p>
  </div>
</div>
<div class="article-body">
<a target="_top" href="{c['kn'][1]}" class="back-link">{e(c['back'])}</a>

<div class="highlight-box" data-scix-guide-tldr>
<div class="box-label">{e(c['tldr'])}</div>
{tldr}
</div>

{top_html}

<nav class="guide-toc" aria-label="{e(c['toc'])}">
<div class="box-label">{e(c['toc'])}</div>
<ol>
{chr(10).join(toc)}
</ol>
</nav>

{chr(10).join(body)}

<section class="guide-cols" id="cols">
<h2>{e(c['cols'].format(n=len(items)))}</h2>
<p class="note">{e(c['cols_note'])}</p>
<ul>
{cols_html}
</ul>
</section>

<section id="faq">
<h2>{e(c['faq'])}</h2>
{faq_html}
</section>

{end_html}

</div>

{footer}
</body>
</html>
"""
    return page, ctx["errors"], ctx["links"] + [x for x in []],


def visible_text(page: str) -> str:
    b = page[page.find("<body"):page.find("<!-- ScienceX Footer")]
    b = re.sub(r"<(script|style)\b.*?</\1>", " ", b, flags=re.S)
    return b


def check_page(rel: str, page: str, links: list, d: dict) -> list:
    errs = []
    vis = visible_text(page)
    txt = html.unescape(re.sub(r"<[^>]+>", " ", vis))
    for rx, why in BANNED:
        m = rx.search(vis) if "href" in rx.pattern else rx.search(txt)
        if m:
            errs.append(f"{rel}: {why}（{m.group(0)[:30]}）")
    for h in links:
        if h.startswith("#") or h.startswith("http"):
            if h.startswith("http") and "www.scix.co.jp" in h and not file_of(h.split("www.scix.co.jp", 1)[1]):
                errs.append(f"{rel}: 行き先が無い {h}")
            continue
        if not file_of(h):
            errs.append(f"{rel}: 行き先の頁が無い {h}")
    for place in ("top", "end"):
        tg = re.findall(rf'data-cta="{place}"(?: data-cta-target="([a-z_]+)")?', page)
        if "market" not in tg:
            errs.append(f"{rel}: {place} の導線に蓄電所マーケットが無い")
        if "contact" not in tg and "sell_form" not in tg:
            errs.append(f"{rel}: {place} の導線に問い合わせが無い")
    if not d["sections"] or not any(k == "@tldr" for k, _ in d["sections"]):
        errs.append(f"{rel}: 3行で言うと が無い")
    if not any(k == "@faq" for k, _ in d["sections"]):
        errs.append(f"{rel}: よくある質問 が無い")
    if '"FAQPage"' in page or '"HowTo"' in page or '"Article"' in page:
        errs.append(f"{rel}: 付けない構造化データ（Article・FAQPage・HowTo）がある")
    return errs


SM_BEGIN = "  <!-- 柱の頁（scripts/build_guides.py が書く・手で直さない） -->"
SM_END = "  <!-- /柱の頁 -->"


def sitemap_text(datas: list, langs: dict) -> str:
    """sitemap.xml の柱の頁の区画（hreflang つき・lastmod＝頁の dateModified）。区画が無ければ </urlset> の前に足す。"""
    rows = []
    for d in datas:
        url = BASE + path_of(d["slug"], d["lang"])
        ls = langs[d["slug"]]
        alt = "".join(f'<xhtml:link rel="alternate" hreflang="{L[x]["hreflang"]}" href="{BASE + path_of(d["slug"], x)}"/>'
                      for x in ("ja", "en", "zh") if x in ls)
        alt += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE + path_of(d["slug"], "en" if "en" in ls else "ja")}"/>'
        rows.append(f"  <url><loc>{url}</loc>{alt}<priority>0.8</priority><lastmod>{d['modified']}</lastmod></url>")
    block = SM_BEGIN + "\n" + "\n".join(rows) + "\n" + SM_END
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    if SM_BEGIN in sm:
        return re.sub(re.escape(SM_BEGIN) + r".*?" + re.escape(SM_END), lambda _m: block, sm, count=1, flags=re.S)
    return sm.replace("</urlset>", block + "\n</urlset>", 1)


def build() -> tuple[dict, list]:
    datas = [read_data(p) for p in sorted(glob.glob(os.path.join(DATA, "*.md")))]
    langs: dict = {}
    for d in datas:
        langs.setdefault(d["slug"], set()).add(d["lang"])
    generated = {path_of(d["slug"], d["lang"]): SUFFIX_RX.sub("", d["title"]) for d in datas}
    out, errs = {}, []
    for d in datas:
        page, e, links = render(d, langs[d["slug"]], generated)
        rel = path_of(d["slug"], d["lang"]).lstrip("/") + ".html"
        errs += e + check_page(rel, page, links, d)
        out[rel] = page
    order = {"ja": 0, "en": 1, "zh": 2}
    out["sitemap.xml"] = sitemap_text(sorted(datas, key=lambda d: (order[d["lang"]], d["slug"])), langs)
    return out, errs


def main() -> int:
    out, errs = build()
    if "--check" in sys.argv:
        drift = [r for r, p in out.items() if not os.path.isfile(os.path.join(ROOT, r)) or open(os.path.join(ROOT, r), encoding="utf-8").read() != p]
        for r in drift:
            print(f"ずれ: {r}（python3 scripts/build_guides.py を回す）")
        for e in errs:
            print("決まり:", e)
        print(f"柱の頁 {len(out) - 1} 本＋sitemap の区画・ずれ {len(drift)}・決まりの指摘 {len(errs)}")
        return 1 if (drift or errs) else 0
    for r, p in out.items():
        fp = os.path.join(ROOT, r)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w", encoding="utf-8").write(p)
    for e in errs:
        print("決まり:", e)
    print(f"柱の頁を書いた: {len(out) - 1} 本＋sitemap の区画（決まりの指摘 {len(errs)}）")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
