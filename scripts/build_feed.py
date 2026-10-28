#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSS を作る（標準ライブラリのみ・ビルド工程なしの静的サイト用）。

  feed.xml           日本語コラム column-*.html の新しい順 30 本
  projects-feed.xml  projects.json の新着案件（直近 60 日。無ければ最新 20 件）

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
