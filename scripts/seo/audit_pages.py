#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全頁の <head> と構造化データを、手元のファイルだけで機械に点検する（本番に触らない・外へ要求しない）。

見るもの（頁ごと）:
  title      無い・重なり（別の頁と同じ）・長すぎ（表示幅 > TITLE_MAX）
  description 無い・重なり・短すぎ（< DESC_MIN）・長すぎ（> DESC_MAX）
  h1         0 本か 2 本以上
  canonical  無い・自分の住所（https://www.scix.co.jp/<path>・.html なし）を指していない
  hreflang   相手の頁のファイルが無い・相手から戻りの hreflang が無い（対になっていない）
  JSON-LD    読めない（JSON の誤り）・コラムに Article が無い・BreadcrumbList が無い
  OGP        og:title・og:description・og:image が無い・og:image の画像がリポジトリに無い
  img        alt が無い
  sitemap    index の頁が sitemap に無い・sitemap の住所にファイルが無い・noindex の頁が sitemap にある
  トップ3頁  最初の節が class の先頭 hero の節で、案件のカード（id="top-cards"・<!--S:cards-->の焼いた行）から始まる・価格を書いていない・
             /site-cards.js を読む・最初の節に会社案内とお問い合わせのリンクがある（2026-11-22 トップ＝蓄電所マーケットのカードの一覧）
表示幅は全角2・半角1で数える（検索結果の切れ目のおおよそ）。

使い方:
    python3 scripts/seo/audit_pages.py            # 要約と、問題ごとの頁の一覧
    python3 scripts/seo/audit_pages.py --json     # 機械向け
    python3 scripts/seo/audit_pages.py --strict   # 「直すべき」が1つでもあれば終了コード 1
2026-11-21 新設（中島「SEO対策…やって公開、実行」）。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = "https://www.scix.co.jp"
TITLE_MAX = 70     # 表示幅（全角2）。おおよそ全角35字
DESC_MIN = 70      # 全角35字
DESC_MAX = 250     # 全角125字
SKIP_DIRS = {".git", "node_modules", "files", "docs", "scripts", ".github", "img", "api"}
SKIP_FILES = {"404.html", "thanks.html", "en/thanks.html", "zh-thanks.html"}


def width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None; self._in_title = False; self._buf = []
        self.desc = None; self.canonical = None; self.robots = ""
        self.h1 = 0; self.og = {}; self.alts = {}; self.ld = []; self._in_ld = False
        self.img_noalt = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "title" and self.title is None:
            self._in_title = True; self._buf = []
        elif tag == "meta":
            n = a.get("name", "").lower(); p = a.get("property", "").lower()
            if n == "description" and self.desc is None:
                self.desc = a.get("content", "")
            elif n == "robots":
                self.robots = a.get("content", "").lower()
            elif p.startswith("og:"):
                self.og.setdefault(p, a.get("content", ""))
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "canonical" and self.canonical is None:
                self.canonical = a.get("href", "")
            elif rel == "alternate" and a.get("hreflang"):
                self.alts[a["hreflang"]] = a.get("href", "")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ld = True; self._buf = []
        elif tag == "img":
            if "alt" not in a:
                self.img_noalt.append(a.get("src", "")[:80])

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self.title = "".join(self._buf).strip(); self._in_title = False
        elif tag == "script" and self._in_ld:
            self.ld.append("".join(self._buf)); self._in_ld = False

    def handle_data(self, data):
        if self._in_title or self._in_ld:
            self._buf.append(data)


def url_of(rel: str) -> str:
    """ファイルの相対パス → 本番の住所（cleanUrls・index は親の住所）。"""
    p = rel[:-5] if rel.endswith(".html") else rel
    if p == "index":
        return BASE + "/"
    if p.endswith("/index"):
        p = p[: -len("/index")]
    return BASE + "/" + p


def file_of(url: str) -> str | None:
    """本番の住所 → リポジトリのファイル（無ければ None）。"""
    if not url.startswith(BASE):
        return None
    p = url[len(BASE):].split("#")[0].split("?")[0].strip("/")
    for cand in ([p + ".html", p + "/index.html"] if p else ["index.html"]):
        if os.path.isfile(os.path.join(ROOT, cand)):
            return cand
    return None


def ld_types(blocks):
    types, bad = set(), 0
    def walk(o):
        if isinstance(o, dict):
            t = o.get("@type")
            for x in (t if isinstance(t, list) else [t]):
                if x:
                    types.add(x)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for b in blocks:
        try:
            walk(json.loads(b))
        except Exception:
            bad += 1
    return types, bad


def pages():
    for dp, dns, fns in os.walk(ROOT):
        rel_dir = os.path.relpath(dp, ROOT)
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            if fn.endswith(".html"):
                rel = os.path.normpath(os.path.join(rel_dir, fn))
                if rel not in SKIP_FILES and not fn.startswith("google"):
                    yield rel


TOPS = ("index.html", "en/index.html", "zh.html")
CARDS_RX = re.compile(r"<!--S:cards-->(.*?)<!--/S:cards-->", re.S)
PRICE_RX = re.compile(r"[¥￥]|円|万円|JPY|yen|日元|\d\s*%")


def top_issues(rel: str, src: str):
    """トップ（日英中）の並び。最初の節＝案件のカード。実績・価格・手数料の率を焼いた行に書かない（O16-7・O16-8・O16-19）。"""
    out = []
    b = src.find("<body")
    m = re.search(r"<section\b([^>]*)>(.*?)</section>", src[b:], re.S) if b >= 0 else None
    if not m:
        return [("トップの最初の節が読めない", "")]
    attrs, first = m.group(1), m.group(2)
    if not re.search(r'class="hero(?:\s[^"]*)?"', attrs):
        out.append(("トップの最初の節が hero でない", attrs[:60]))
    if 'id="top-cards"' not in first:
        out.append(("トップの最初の節に案件のカード（#top-cards）が無い", ""))
    cards = CARDS_RX.search(first)
    n = len(re.findall(r'<article class="sc"', cards.group(1))) if cards else 0
    if not cards or n < 1:
        out.append(("トップに焼いた案件の行（<!--S:cards-->）が無い", str(n)))
    elif PRICE_RX.search(re.sub(r"<[^>]+>", " ", cards.group(1))):
        out.append(("トップの焼いた案件の行に価格・率の語がある", ""))
    for need, label in (("/company", "会社案内"), ("/contact", "お問い合わせ")):
        if need not in first.replace("/zh-contact", "/contact").replace("/en/company", "/company").replace("/en/contact", "/contact"):
            out.append((f"トップの最初の節に {label} のリンクが無い", ""))
    if "/site-cards.js" not in src:
        out.append(("トップが /site-cards.js を読んでいない", ""))
    return out


def is_column(rel: str) -> bool:
    b = os.path.basename(rel)
    return b.startswith("column-") or b.startswith("zh-column-")


def main():
    as_json = "--json" in sys.argv
    strict = "--strict" in sys.argv
    sm_text = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    sm_locs = set(re.findall(r"<loc>([^<]+)</loc>", sm_text))
    info = {}
    for rel in sorted(pages()):
        h = Head()
        try:
            h.feed(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except Exception as e:  # 読めない頁も黙らせない
            info[rel] = {"error": str(e)}
            continue
        info[rel] = h

    issues = defaultdict(list)   # 種類 → [(頁, 詳細)]
    by_title, by_desc = defaultdict(list), defaultdict(list)
    for rel, h in info.items():
        if isinstance(h, dict):
            issues["読めない"].append((rel, h["error"])); continue
        noindex = "noindex" in h.robots
        me = url_of(rel)
        if not h.title:
            issues["title 無し"].append((rel, ""))
        else:
            if not noindex:
                by_title[h.title].append(rel)
            if width(h.title) > TITLE_MAX:
                issues["title 長すぎ"].append((rel, f"{width(h.title)} {h.title}"))
        if not h.desc:
            issues["description 無し"].append((rel, ""))
        else:
            if not noindex:
                by_desc[h.desc].append(rel)
            w = width(h.desc)
            if w < DESC_MIN:
                issues["description 短すぎ"].append((rel, f"{w} {h.desc}"))
            elif w > DESC_MAX:
                issues["description 長すぎ"].append((rel, f"{w}"))
        if h.h1 != 1:
            issues["h1 が1本でない"].append((rel, str(h.h1)))
        if not h.canonical:
            issues["canonical 無し"].append((rel, ""))
        elif h.canonical.rstrip("/") != me.rstrip("/") and not noindex:
            issues["canonical が自分でない"].append((rel, h.canonical))
        for lang, href in h.alts.items():
            if lang == "x-default":
                continue
            f = file_of(href)
            if not f:
                issues["hreflang の相手が無い"].append((rel, f"{lang} {href}"))
                continue
            other = info.get(f)
            if isinstance(other, Head) and other.alts and me.rstrip("/") not in {u.rstrip("/") for u in other.alts.values()}:
                issues["hreflang が対になっていない"].append((rel, f"{lang} → {f}"))
        types, bad = ld_types(h.ld)
        if bad:
            issues["JSON-LD が読めない"].append((rel, f"{bad} 個"))
        if is_column(rel) and not ({"Article", "BlogPosting", "NewsArticle", "TechArticle"} & types):
            issues["コラムに Article 無し"].append((rel, ""))
        if rel not in ("index.html", "en/index.html", "zh.html") and "BreadcrumbList" not in types and not noindex:
            issues["BreadcrumbList 無し"].append((rel, ""))
        for k in ("og:title", "og:description", "og:image"):
            if not h.og.get(k):
                issues[f"{k} 無し"].append((rel, ""))
        img = h.og.get("og:image", "")
        if img.startswith(BASE):
            ip = img[len(BASE):].split("?")[0].lstrip("/")
            if not os.path.isfile(os.path.join(ROOT, ip)):
                issues["og:image の画像が無い"].append((rel, img))
        for src in h.img_noalt:
            issues["img の alt 無し"].append((rel, src))
        in_sm = me in sm_locs or me.rstrip("/") in sm_locs
        if noindex and in_sm:
            issues["noindex なのに sitemap にある"].append((rel, ""))
        if not noindex and not in_sm:
            issues["sitemap に無い"].append((rel, me))
    for rel in TOPS:
        if isinstance(info.get(rel), Head):
            for k, d in top_issues(rel, open(os.path.join(ROOT, rel), encoding="utf-8").read()):
                issues[k].append((rel, d))
    for t, rels in by_title.items():
        if len(rels) > 1:
            issues["title 重なり"].append((", ".join(rels), t))
    for d, rels in by_desc.items():
        if len(rels) > 1:
            issues["description 重なり"].append((", ".join(rels), d[:60]))
    for loc in sorted(sm_locs):
        if not file_of(loc):
            issues["sitemap の住所にファイルが無い"].append((loc, ""))

    if as_json:
        print(json.dumps({k: v for k, v in issues.items()}, ensure_ascii=False, indent=1))
    else:
        print(f"頁 {len(info)} 本・sitemap {len(sm_locs)} 本")
        for k in sorted(issues, key=lambda k: -len(issues[k])):
            print(f"\n## {k}（{len(issues[k])}）")
            for rel, d in issues[k][:400]:
                print(f"  {rel}  {d}")
    return 1 if (strict and issues) else 0


if __name__ == "__main__":
    sys.exit(main())
