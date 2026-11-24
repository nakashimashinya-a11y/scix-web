#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全頁の <head> にある Google アナリティクス（GA4）の区画を、決まった1つの形にそろえる。
あわせて、入力の欄の無い公開の頁にだけ LinkedIn Insight タグの区画（LI_BLOCK）を GA の区画のすぐ後に置く（下の「LinkedIn」）。

2026-11-22 新設（中島「これ全部やって。売上UPのために徹底的に進めて。すべて漏らさずやって。」・Gemini の助言の指示4＝計測のノイズ）。
前は全頁に gtag の4行が直書きで、手元の確かめ（localhost・127.0.0.1）・プレビュー・自動操作のブラウザの閲覧まで GA4 に入っていた。

区画がすること（BLOCK）:
  (a) 住所が www.scix.co.jp 以外（localhost・127.0.0.1・プレビュー・file: など）なら送らない＝window['ga-disable-G-SNNK8MP9N9']=true を config の前に
  (b) 自動操作のブラウザ（navigator.webdriver が真）も送らない
  (c) 社内の印（header.js の 7c と同じ localStorage の鍵 scix_internal。?internal=1 で付き ?internal=0 で外れる）がある端末は、
      config に traffic_type:'internal' を付けて送る（GA4 のデータフィルタ「内部トラフィック」が traffic_type=internal を外す）。
      印の無い端末には traffic_type を付けない（付けるとフィルタを有効にした日から全部のデータが消える）。
gtag.js の読み込みの行（<script async src=...>）は前と同じ位置・同じ形のまま（Search Console の所有権の確認が読む）。

LinkedIn Insight タグ（2026-11-25 追加・中島「全部よい」＝LinkedIn 広告の効果の測定。公開の頁だけに置く）:
  LinkedIn との約束で、機微な情報を集める・含む頁には置かない。ここでは、お名前・メールアドレスなどを入れる欄（フォーム）のある頁を全部外す
  （LI_SKIP_PAGES の頁と、頁の中に入力のフォームがある頁＝has_entry_form。頁の中の記事の検索の欄と、試算の目盛り・チェックの欄は入力に数えない）。
  区画は GA と同じく、本番の住所（www.scix.co.jp・scix.co.jp）以外・自動操作のブラウザ・社内の印のある端末では読み込まない。
  さらに、読み込む直前（DOMContentLoaded）にもう一度、頁に入力のフォームが無いかを見て、あれば読まない
  （header.js の「メールのお知らせ」の箱＝.scix-nl は除く。記事の末尾に足されるメールアドレスだけの箱で、コラムと市場ノートにも置くため）。
  画像の1px（noscript）は置かない（住所の確かめができず、プレビューからも送られるため）。
  お知らせの文は privacy.html・en/privacy.html・zh-privacy.html の 8 項。

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

LI_PARTNER_ID = "10484516"   # LinkedIn の partner id（頁のソースに出る公開の番号）
LI_BLOCK = (
    "<!-- LinkedIn Insight タグ（scripts/build_ga_tag.py が入力の欄の無い公開の頁にだけ入れる・手で直さない） -->\n"
    "<script>\n"
    "  (function () {\n"
    "    var h = '', q = null, mk = false;\n"
    "    // 本番（www.scix.co.jp・scix.co.jp）以外の住所と、自動操作のブラウザ（navigator.webdriver）では読まない\n"
    "    try { h = location.hostname; if (navigator.webdriver) return; } catch (e) { return; }\n"
    "    if (h !== 'www.scix.co.jp' && h !== 'scix.co.jp') return;\n"
    "    // 社内の印（GA の区画と同じ鍵 scix_internal・?internal=1）のある端末では読まない\n"
    "    try { q = new URLSearchParams(location.search).get('internal'); } catch (e) { q = null; }\n"
    "    try { mk = localStorage.getItem('scix_internal') === '1'; } catch (e) { mk = false; }\n"
    "    if (q === '1' || mk) return;\n"
    "    function hasEntryForm() {\n"
    "      // 入力のフォーム（お問い合わせ・売却の相談など）のある頁では読まない。記事の検索の欄と、メールのお知らせの箱（.scix-nl）は除く\n"
    "      var els = document.querySelectorAll('form, textarea, input[type=\"email\"], input[type=\"tel\"], input[type=\"password\"]');\n"
    "      for (var i = 0; i < els.length; i++) {\n"
    "        var el = els[i];\n"
    "        if (el.closest && el.closest('.scix-nl')) continue;\n"
    "        if (el.tagName === 'FORM' && el.getAttribute('role') === 'search') continue;\n"
    "        if (el.closest && el.closest('form[role=\"search\"]')) continue;\n"
    "        return true;\n"
    "      }\n"
    "      return false;\n"
    "    }\n"
    "    function load() {\n"
    "      try { if (hasEntryForm()) return; } catch (e) { return; }\n"
    f"      window._linkedin_partner_id = '{LI_PARTNER_ID}';\n"
    "      window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];\n"
    "      window._linkedin_data_partner_ids.push(window._linkedin_partner_id);\n"
    "      if (!window.lintrk) { window.lintrk = function (a, b) { window.lintrk.q.push([a, b]); }; window.lintrk.q = []; }\n"
    "      var s = document.getElementsByTagName('script')[0], b = document.createElement('script');\n"
    "      b.type = 'text/javascript'; b.async = true;\n"
    "      b.src = 'https://snap.licdn.com/li.lms-analytics/insight.min.js';\n"
    "      s.parentNode.insertBefore(b, s);\n"
    "    }\n"
    "    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();\n"
    "  })();\n"
    "</script>"
)
# 生成の台本（build_market_data・build_guides・build_newsroom）が head に入れる形。どれも入力のフォームの無い公開の頁
TAGS = BLOCK + "\n" + LI_BLOCK

# LinkedIn のタグを置かない頁（入力のフォームの頁・送信の後の頁・404）。ほかに has_entry_form に当たる頁も外す
LI_SKIP_PAGES = {
    "contact.html", "en/contact.html", "zh-contact.html",
    "sell-form.html", "fund.html",
    "thanks.html", "en/thanks.html", "zh-thanks.html",
    "404.html",
}
LI_RX = re.compile(r"<!-- LinkedIn Insight タグ[^\n]*-->\n<script>.*?</script>\n?", re.S)
LI_MARK = "snap.licdn.com/li.lms-analytics/insight.min.js"
_FORM_RX = re.compile(r"<form\b[^>]*>", re.I)
_FIELD_RX = re.compile(r"<textarea\b|<input\b[^>]*type=[\"']?(?:email|tel|password)\b", re.I)


def has_entry_form(src: str) -> bool:
    """頁の HTML に入力のフォームがあるか（role="search" の検索の欄だけのフォームは数えない）。"""
    for m in _FORM_RX.finditer(src):
        if not re.search(r"role=[\"']?search", m.group(0), re.I):
            return True
    return bool(_FIELD_RX.search(src))


def li_wanted(rel: str, src: str) -> bool:
    """この頁に LinkedIn のタグを置くか。"""
    return rel.replace(os.sep, "/") not in LI_SKIP_PAGES and not has_entry_form(src)


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


def problem(src: str, rel: str | None = None) -> str | None:
    """頁の中身を見て、区画が決まった形でなければ理由を返す（決まった形なら None）。
    rel（頁の住所）を渡すと、LinkedIn のタグの有る無しも見る。"""
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
    if rel is not None:
        n_li = src.count(LI_MARK)
        if li_wanted(rel, src):
            if n_li != 1 or (BLOCK + "\n" + LI_BLOCK) not in src:
                return "LinkedIn のタグが無いか古い形（build_ga_tag.py を回す）"
        elif n_li:
            return "入力のフォームのある頁に LinkedIn のタグがある（build_ga_tag.py を回す）"
    return None


def fixed(src: str, rel: str | None = None) -> str:
    """区画を決まった形にした中身を返す。無ければ <head> の直後に入れる。2個以上や読めない形はそのまま（--check が出す）。
    rel を渡すと、LinkedIn のタグを GA の区画のすぐ後に置く（置かない頁からは外す）。"""
    out = src
    found = BLOCK_RX.findall(src)
    if len(found) == 1 and src.count(LOADER) == 1:
        out = BLOCK_RX.sub(lambda _m: BLOCK, src, count=1)
    elif not found and LOADER not in src:
        m = re.search(r"<head[^>]*>\n?", src)
        if m:
            out = src[:m.end()] + BLOCK + "\n" + src[m.end():]
    if rel is None or out.count(BLOCK) != 1:
        return out
    out = LI_RX.sub("", out)
    if li_wanted(rel, out):
        out = out.replace(BLOCK, BLOCK + "\n" + LI_BLOCK, 1)
    return out


def main() -> int:
    check = "--check" in sys.argv
    bad, changed, n = [], [], 0
    for rel in html_files():
        n += 1
        p = os.path.join(ROOT, rel)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        if check:
            why = problem(src, rel)
            if why:
                bad.append((rel, why))
            continue
        out = fixed(src, rel)
        if out != src:
            with open(p, "w", encoding="utf-8") as f:
                f.write(out)
            changed.append(rel)
        why = problem(out, rel)
        if why:
            bad.append((rel, why))
    if check:
        print(f"GA の区画: {n} 頁を見て、ずれ {len(bad)} 頁")
    else:
        print(f"GA の区画: {n} 頁を見て、{len(changed)} 頁を書き換え・直せなかった頁 {len(bad)}")
    if "--li-list" in sys.argv:
        for rel in html_files():
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            if not li_wanted(rel, src):
                print(f"  LinkedIn のタグを置かない頁: {rel}")
    for rel, why in bad:
        print(f"  {rel}  {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
