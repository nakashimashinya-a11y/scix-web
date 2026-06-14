#!/usr/bin/env python3
"""IndexNow へ sitemap.xml の全URLを送信する。Bing/Yandex/Seznam/Naver が即時クロールに反映。
（Google は IndexNow 非対応だが、当サイトは流入2位が Bing のため効果大）

使い方:
  python3 tools/indexnow_submit.py            # sitemap全URL送信
  python3 tools/indexnow_submit.py URL [URL]  # 個別URLだけ送信（更新したページのみ）
前提: {KEY}.txt が本番ルート(https://www.scix.co.jp/{KEY}.txt)に配信済みであること。
"""
import json, sys, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = 'www.scix.co.jp'
KEY = (ROOT/'.indexnow-key').read_text().strip()
KEY_LOCATION = f'https://{HOST}/{KEY}.txt'
ENDPOINT = 'https://api.indexnow.org/indexnow'


def sitemap_urls():
    xml = (ROOT/'sitemap.xml').read_text(encoding='utf-8')
    return re.findall(r'<loc>([^<]+)</loc>', xml)


def submit(urls):
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': KEY_LOCATION,
                       'urlList': urls}).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f'IndexNow HTTP {r.status} — submitted {len(urls)} URLs (key {KEY[:8]}…)')


if __name__ == '__main__':
    urls = sys.argv[1:] or sitemap_urls()
    print(f'submitting {len(urls)} URLs to IndexNow…')
    submit(urls)
