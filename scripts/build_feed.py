#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSS を作る（標準ライブラリのみ・ビルド工程なしの静的サイト用）。

  feed.xml           日本語コラム column-*.html の新しい順 30 本
  projects-feed.xml  projects.json の新着案件（直近 60 日。無ければ最新 20 件）
  smartnews.xml      SmartNews 用の SmartFormat 2.2（全文・新しい順 20 本・1MB 未満）。申請の前提（2026-10-30）

案件の項目は projects.json の公開セーフ項目だけ（価格・住所・売主は元から無い）。
毎朝の scripts/sync_projects_json.sh が inject_stats.py の直後に呼ぶ。

使い方:
    python3 scripts/build_feed.py            # 書く
    python3 scripts/build_feed.py --check    # 書かず、ずれているかだけ（ずれていれば exit 1）
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import email.utils
import glob
import html
from html.parser import HTMLParser
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.scix.co.jp"
JST = datetime.timezone(datetime.timedelta(hours=9))
COLUMN_LIMIT = 30
PROJECT_DAYS = 60
PROJECT_FALLBACK = 20


def esc(s):
    return html.escape(str(s), quote=False)


def rfc822(d: datetime.date) -> str:
    dt = datetime.datetime(d.year, d.month, d.day, 9, 0, tzinfo=JST)
    return email.utils.format_datetime(dt)


def first_commit_date(path):
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%as", "--", path],
                             cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.split()
        return datetime.date.fromisoformat(out[-1]) if out else None
    except Exception:
        return None


def date_published(src, path):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and node.get("@type") == "Article" and node.get("datePublished"):
                try:
                    return datetime.date.fromisoformat(str(node["datePublished"])[:10])
                except ValueError:
                    pass
    return first_commit_date(path)


def column_items():
    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "column-*.html"))):
        name = os.path.basename(path)
        src = open(path, encoding="utf-8").read()
        t = re.search(r"<title>(.*?)</title>", src, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', src, re.S)
        if not t:
            continue
        pub = date_published(src, name)
        if not pub:
            continue
        items.append({
            "title": html.unescape(t.group(1)).split("｜")[0].strip(),
            "link": f"{BASE}/{name[:-5]}",
            "desc": html.unescape(d.group(1)).strip() if d else "",
            "date": pub,
        })
    items.sort(key=lambda x: (x["date"], x["link"]), reverse=True)
    return items[:COLUMN_LIMIT]


def project_items(today):
    import inject_stats as st
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        ps = json.load(f).get("projects", [])
    today_ym = today.strftime("%Y-%m")
    dated = []
    for p in ps:
        try:
            dated.append((datetime.date.fromisoformat(p.get("firstSeen") or ""), p))
        except ValueError:
            continue
    dated.sort(key=lambda x: (x[0], x[1].get("id") or ""), reverse=True)
    recent = [x for x in dated if (today - x[0]).days <= PROJECT_DAYS]
    chosen = recent if recent else dated[:PROJECT_FALLBACK]
    items = []
    for d, p in chosen:
        mw, mwh = p.get("mw"), p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        pid = p.get("id") or ""
        head = f"{pid} {p.get('pref') or '所在県 確認中'}（{p.get('area') or '—'}管内）"
        title = "｜".join([head, p.get("voltage") or "—", size, p.get("scheme") or "取得の形 確認中"])
        cod = st.cod_text(p, today_ym)
        desc = "｜".join([p.get("voltage") or "—", size,
                         cod if p.get("live") else "連系の見込み " + cod]
                        + ([] if p.get("live") else [p.get("status") or "—"])
                        + [p.get("scheme") or "取得の形 確認中"])
        items.append({"title": title, "link": f"{BASE}/projects#p-{pid}", "desc": desc, "date": d})
    return items


SMARTNEWS_LIMIT = 20
SN_ALLOWED = {"a", "b", "blockquote", "br", "caption", "code", "dd", "div", "dl", "dt", "em", "figcaption", "figure",
              "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "section", "small", "span",
              "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul"}
SN_DROP_WHOLE = {"script", "style", "svg", "aside", "form", "button", "iframe", "noscript"}
SN_KEEP_ATTR = {"a": ("href",), "img": ("src", "alt", "width", "height")}


class _SNSanitizer(HTMLParser):
    """記事本文を SmartFormat の content:encoded 用に削る: 許可タグだけ残し、script/style/svg/aside は中身ごと落とし、
    導線の箱（data-scix-*）・CTA・署名・戻る/次へのリンクを落とし、style 属性を外し、リンクを絶対 URL にする。"""

    def __init__(self, link=""):
        super().__init__(convert_charrefs=True)
        self.link = link
        self.out = []
        self.drop = 0          # 中身ごと落とす深さ
        self.skip_div = []     # 落とす div/a の入れ子（True=落とす）

    def _abs(self, u):
        if u.startswith("/"):
            return BASE + u
        if u.startswith("#"):
            return self.link + u
        return u

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.drop:
            if tag not in ("br", "img", "hr"):
                self.drop += 1
            return
        cls = a.get("class", "") or ""
        if tag in SN_DROP_WHOLE or any(k.startswith("data-scix-") for k in a) \
           or (tag == "div" and ("author-box" in cls or "press-note" in cls or "series" in cls or cls.split() and cls.split()[0] == "toc")) \
           or (tag == "a" and ("back-link" in cls or "next-link" in cls)) \
           or (tag == "p" and "press-note" in cls):
            self.drop = 1
            return
        if tag not in SN_ALLOWED:
            return
        keep = []
        for k in SN_KEEP_ATTR.get(tag, ()):
            if a.get(k):
                v = a[k]
                if k in ("href", "src"):
                    v = self._abs(v)
                keep.append(f'{k}="{html.escape(v, quote=True)}"')
        if tag == "img" and not a.get("src"):
            return
        self.out.append("<" + tag + (" " + " ".join(keep) if keep else "") + (" />" if tag in ("br", "img", "hr") else ">"))

    def handle_endtag(self, tag):
        if self.drop:
            if tag not in ("br", "img", "hr"):
                self.drop -= 1
            return
        if tag in SN_ALLOWED and tag not in ("br", "img", "hr"):
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.drop:
            return
        self.out.append(html.escape(data, quote=False))


def sn_body(src, link=""):
    """<div class="article-body"> の中身（CTA の前まで）を許可タグだけにして返す。"""
    i = src.find('<div class="article-body">')
    if i < 0:
        return ""
    j = src.find("<!-- scix-column-cta", i)
    if j < 0:
        j = src.find("<!-- ScienceX Footer", i)
    body = src[i + len('<div class="article-body">'):j if j > 0 else None]
    p = _SNSanitizer(link)
    p.feed(body)
    out = "".join(p.out)
    out = re.sub(r"<(p|div|section|span|figure)>\s*</\1>", "", out)   # 空の箱
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def smartnews_items():
    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "column-*.html"))):
        name = os.path.basename(path)
        src = open(path, encoding="utf-8").read()
        t = re.search(r"<title>(.*?)</title>", src, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', src, re.S)
        if not t:
            continue
        pub = date_published(src, name)
        if not pub:
            continue
        tag = re.search(r'class="header-tag">([^<]*)<', src)
        og = re.search(r'<meta property="og:image" content="([^"]*)"', src)
        items.append({
            "title": html.unescape(t.group(1)).split("｜")[0].strip(),
            "link": f"{BASE}/{name[:-5]}",
            "desc": html.unescape(d.group(1)).strip() if d else "",
            "date": pub,
            "category": html.unescape(tag.group(1)).strip() if tag else "系統用蓄電池",
            "thumb": (og.group(1) if og else f"{BASE}/img/ogp.png"),
            "body": sn_body(src, f"{BASE}/{name[:-5]}"),
        })
    items.sort(key=lambda x: (x["date"], x["link"]), reverse=True)
    return [x for x in items if x["body"]][:SMARTNEWS_LIMIT]


def render_smartnews(items):
    last = max((i["date"] for i in items), default=datetime.date.today())
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
           'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/" '
           'xmlns:snf="http://www.smartnews.be/snf">',
           '<channel>',
           '<title>サイエンスエックス ナレッジ</title>',
           f'<link>{BASE}/knowledge</link>',
           '<description>系統用蓄電池の制度・市場・売買の解説</description>',
           f'<pubDate>{rfc822(last)}</pubDate>',
           '<language>ja</language>',
           '<copyright>© Science X Inc.</copyright>',
           '<ttl>60</ttl>',
           f'<snf:logo><url>{BASE}/img/press/logo-navy-700x100.png</url></snf:logo>',
           f'<snf:darkModeLogo><url>{BASE}/img/press/logo-white-700x100.png</url></snf:darkModeLogo>']
    for i in items:
        body = i["body"].replace("]]>", "]]]]><![CDATA[>")
        out += ['<item>',
                f'<title>{esc(i["title"])}</title>',
                f'<link>{esc(i["link"])}</link>',
                f'<guid>{esc(i["link"])}</guid>',
                f'<description><![CDATA[{i["desc"].replace("]]>", "")}]]></description>',
                f'<pubDate>{rfc822(i["date"])}</pubDate>',
                f'<content:encoded><![CDATA[<img src="{i["thumb"]}" alt="{esc(i["title"])}" />\n{body}\n'
                f'<p>元の記事（図表つき）: <a href="{i["link"]}">{i["link"]}</a></p>]]></content:encoded>',
                f'<category>{esc(i["category"])},系統用蓄電池,蓄電所</category>',
                '<dc:creator>中島 晋也</dc:creator>',
                '<dc:language>ja</dc:language>',
                f'<media:thumbnail url="{esc(i["thumb"])}" />',
                '<media:status>active</media:status>',
                '</item>']
    out += ['</channel>', '</rss>', '']
    return "\n".join(out)


def render(title, link, desc, self_url, items):
    last = max((i["date"] for i in items), default=None)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           '<channel>',
           f'<title>{esc(title)}</title>',
           f'<link>{esc(link)}</link>',
           f'<description>{esc(desc)}</description>',
           '<language>ja</language>',
           f'<atom:link href="{esc(self_url)}" rel="self" type="application/rss+xml"/>']
    if last:
        out.append(f'<lastBuildDate>{rfc822(last)}</lastBuildDate>')
    for i in items:
        out += ['<item>',
                f'<title>{esc(i["title"])}</title>',
                f'<link>{esc(i["link"])}</link>',
                f'<description>{esc(i["desc"])}</description>',
                f'<pubDate>{rfc822(i["date"])}</pubDate>',
                f'<guid isPermaLink="true">{esc(i["link"])}</guid>',
                '</item>']
    out += ['</channel>', '</rss>', '']
    return "\n".join(out)


def main():
    check = "--check" in sys.argv
    today = datetime.datetime.now(JST).date()
    files = {
        "feed.xml": render("サイエンスエックス ナレッジ（系統用蓄電池）", f"{BASE}/knowledge",
                           "系統用蓄電池の制度・市場・税制・用地・売買の解説コラムの新着。",
                           f"{BASE}/feed.xml", column_items()),
        "projects-feed.xml": render("サイエンスエックス 販売中の系統用蓄電池案件（新着）", f"{BASE}/projects",
                                    "サイエンスエックスが販売中の系統用蓄電池案件の新着。公開できる項目のみ。",
                                    f"{BASE}/projects-feed.xml", project_items(today)),
        "smartnews.xml": render_smartnews(smartnews_items()),
    }
    stale = []
    for name, body in files.items():
        path = os.path.join(ROOT, name)
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if cur != body:
            stale.append(name)
            if not check:
                open(path, "w", encoding="utf-8").write(body)
    if check:
        print(f"[check] 要更新 {len(stale)} ファイル" + (": " + " ".join(stale) if stale else ""))
        return 1 if stale else 0
    print(f"[ok] {len(stale)} ファイルを更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
