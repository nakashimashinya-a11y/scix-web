#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全頁の <head> にある Google アナリティクス（GA4）の区画を、決まった1つの形にそろえる。

2026-11-22 新設（中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」・Gemini の助言の指示4＝計測のノイズ）。
前は全頁に gtag の4行が直書きで、手元の確かめ（localhost・127.0.0.1）・プレビュー・自動操作のブラウザの閲覧まで GA4 に入っていた。

区画がすること（BLOCK）:
  (a) 住所が www.scix.co.jp 以外（localhost・127.0.0.1・プレビュー・file: など）なら送らない＝window['ga-disable-G-SNNK8MP9N9']=true を config の前に
  (b) 自動操作のブラウザ（navigator.webdriver が真）も送らない
  (c) 社内の印（header.js の 7c と同じ localStorage の鍵 scix_internal。?internal=1 で付き ?internal=0 で外れる）がある端末は、
      config に traffic_type:'internal' を付けて送る（GA4 のデータフィルタ「内部トラフィック」が traffic_type=internal を外す）。
      印の無い端末には traffic_type を付けない（付けるとフィルタを有効にした日から全部のデータが消える）。
gtag.js の読み込みの行（<script async src=...>）は前と同じ位置・同じ形のまま（Search Console の所有権の確認が読む）。

使い方:
    python3 scripts/build_ga_tag.py            # 全頁を決まった形に書き換えて、変えた頁の数を出す
    python3 scripts/build_ga_tag.py --check    # 書き換えずに、ずれている頁を出す（ずれていれば 1）
新しい頁を足したら、この台本を回す（scripts/seo/audit_pages.py --strict が、形の違う頁と区画の無い頁を止める）。
scripts/build_market_data.py（市場データ・管内別の一覧・市場ノートの頁の head）は BLOCK をここから読む。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GA_ID = "G-SNNK8MP9N9"
PROD_HOST = "www.scix.co.jp"
SKIP_DIRS = {".git", "node_modules"}

BLOCK = (
    "<!-- Google Analytics（scripts/build_ga_tag.py が全頁に入れる・手で直さない） -->\n"
    f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>\n'
    "<script>\n"
    "  window.dataLayer = window.dataLayer || [];\n"
    "  function gtag(){dataLayer.push(arguments);}\n"
    "  (function () {\n"
    "    var cfg = {}, q = null, mk = false;\n"
    f"    // 本番（{PROD_HOST}）以外の住所と、自動操作のブラウザ（navigator.webdriver）からは送らない\n"
    f"    try {{ if (location.hostname !== '{PROD_HOST}' || navigator.webdriver) window['ga-disable-{GA_ID}'] = true; }}\n"
    f"    catch (e) {{ window['ga-disable-{GA_ID}'] = true; }}\n"
    "    // 社内の印（?internal=1 で付く・?internal=0 で外れる・header.js の 7c と同じ鍵）。印のある端末だけ traffic_type を付ける\n"
    "    try { q = new URLSearchParams(location.search).get('internal'); } catch (e) { q = null; }\n"
    "    try {\n"
    "      if (q === '1') localStorage.setItem('scix_internal', '1');\n"
    "      else if (q === '0') localStorage.removeItem('scix_internal');\n"
    "      mk = localStorage.getItem('scix_internal') === '1';\n"
    "    } catch (e) { mk = q === '1'; }\n"
    "    if (mk) cfg.traffic_type = 'internal';\n"
    "    gtag('js', new Date());\n"
    f"    gtag('config', '{GA_ID}', cfg);\n"
    "  })();\n"
    "</script>"
)

# 前からの直書き（「<!-- Google Analytics -->」「<!-- Google tag (gtag.js) -->」の行つき）と、この台本が入れた形の両方に当たる
BLOCK_RX = re.compile(
    r"(?:<!-- Google (?:Analytics|tag)[^\n]*-->\n)*"
    r'<script async src="https://www\.googletagmanager\.com/gtag/js\?id=' + re.escape(GA_ID) + r'"></script>\n'
    r"<script>.*?</script>",
    re.S,
)
LOADER = f"googletagmanager.com/gtag/js?id={GA_ID}"


def html_files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if fn.endswith(".html"):
                yield os.path.relpath(os.path.join(dp, fn), ROOT)


def problem(src: str) -> str | None:
    """頁の中身を見て、区画が決まった形でなければ理由を返す（決まった形なら None）。"""
    found = BLOCK_RX.findall(src)
    if not found:
        return "GA の区画が無い" if LOADER not in src else "GA の区画が読めない形"
    if len(found) > 1 or src.count(LOADER) > 1:
        return f"GA の区画が {max(len(found), src.count(LOADER))} 個"
    if found[0] != BLOCK:
        return "GA の区画が古い形（build_ga_tag.py を回す）"
    head_end = src.find("</head>")
    if head_end >= 0 and src.find(BLOCK) > head_end:
        return "GA の区画が <head> の外"
    return None


def fixed(src: str) -> str:
    """区画を決まった形にした中身を返す。無ければ <head> の直後に入れる。2個以上や読めない形はそのまま（--check が出す）。"""
    found = BLOCK_RX.findall(src)
    if len(found) == 1 and src.count(LOADER) == 1:
        return BLOCK_RX.sub(lambda _m: BLOCK, src, count=1)
    if not found and LOADER not in src:
        m = re.search(r"<head[^>]*>\n?", src)
        if m:
            return src[:m.end()] + BLOCK + "\n" + src[m.end():]
    return src


def main() -> int:
    check = "--check" in sys.argv
    bad, changed, n = [], [], 0
    for rel in html_files():
        n += 1
        p = os.path.join(ROOT, rel)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        if check:
            why = problem(src)
            if why:
                bad.append((rel, why))
            continue
        out = fixed(src)
        if out != src:
            with open(p, "w", encoding="utf-8") as f:
                f.write(out)
            changed.append(rel)
        why = problem(out)
        if why:
            bad.append((rel, why))
    if check:
        print(f"GA の区画: {n} 頁を見て、ずれ {len(bad)} 頁")
    else:
        print(f"GA の区画: {n} 頁を見て、{len(changed)} 頁を書き換え・直せなかった頁 {len(bad)}")
    for rel, why in bad:
        print(f"  {rel}  {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
