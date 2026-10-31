#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projects.json（公開セーフ項目だけ）から、市場データのページと管内別の案件一覧ページを焼き直す。

2026-10-29 新設。中島「DR2 は限定公開情報。でもなにか使える方法無いかな」→ 公開セーフ項目（管内・県・電圧・MW/MWh・
状態・取得の形・連系の見込み・掲載日）の集計だけで、他社に無い「売り案件の市場データ」を作る。価格・住所・売主は無い
（projects.json に入っていない＝規則 O07-20・O16-19）。

生成するもの（全文を書き直す。手で直さない。週次の検査は FORBIDDEN で触らない）:
  market-data.html            系統用蓄電池の売り案件 市場データ（当社観測）
  projects-<slug>.html ×9      管内別の案件一覧（東京・中部・九州・関西・中国・東北・北海道・北陸・四国）
                              件数が MIN_INDEX 未満の管内は noindex（薄いページを索引に出さない）

使い方:
    python3 scripts/build_market_data.py            # 書き換えて差分を報告
    python3 scripts/build_market_data.py --check    # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
  en/projects.html            英語の案件一覧（海外の買い手向け・1枚・価格なし・2026-10-31 新設）
毎朝の同期（scripts/sync_projects_json.sh）が inject_stats.py の直後に呼ぶ。
"""
from __future__ import annotations  # launchd の python3 は 3.9

import datetime
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from inject_stats import NEW_DAYS, _esc, cod_sort_key, cod_text, is_new  # noqa: E402

BASE = "https://www.scix.co.jp"
MIN_INDEX = 5   # 管内の件数がこれ未満なら noindex
AREAS = [
    ("東京", "tokyo", "東京電力パワーグリッド"),
    ("中部", "chubu", "中部電力パワーグリッド"),
    ("九州", "kyushu", "九州電力送配電"),
    ("関西", "kansai", "関西電力送配電"),
    ("中国", "chugoku", "中国電力ネットワーク"),
    ("東北", "tohoku", "東北電力ネットワーク"),
    ("北海道", "hokkaido", "北海道電力ネットワーク"),
    ("北陸", "hokuriku", "北陸電力送配電"),
    ("四国", "shikoku", "四国電力送配電"),
]
OUTPUTS = ["market-data.html", "en/projects.html"] + [f"projects-{slug}.html" for _, slug, _ in AREAS]


# ---------------------------------------------------------------- 集計
def fiscal_half(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    fy = y if m >= 4 else y - 1
    return f"{fy}年度{'上期' if 4 <= m <= 9 else '下期'}"


def stats(ps, today):
    today_ym = today.strftime("%Y-%m")
    mws = [p["mw"] for p in ps if isinstance(p.get("mw"), (int, float))]
    mwhs = [p["mwh"] for p in ps if isinstance(p.get("mwh"), (int, float))]
    lead = sorted(p["leadMonths"] for p in ps if isinstance(p.get("leadMonths"), (int, float)))
    ym = [p["codYm"] for p in ps if p.get("codYm") and p["codYm"] >= today_ym and not p.get("live")]
    half = Counter(fiscal_half(x) for x in ym)
    bands = Counter()
    for n in lead:
        bands["6か月以内" if n <= 6 else "7〜12か月" if n <= 12 else "13〜24か月" if n <= 24 else "25か月以上"] += 1
    fs = Counter((p.get("firstSeen") or "")[:7] for p in ps if p.get("firstSeen"))
    return {
        "n": len(ps),
        "mw": round(sum(mws)),
        "mwh": round(sum(mwhs)),
        "mw_median": (sorted(mws)[len(mws) // 2] if mws else None),
        "volt": Counter(p.get("voltage") for p in ps if p.get("voltage")),
        "area": Counter(p.get("area") for p in ps if p.get("area")),
        "area_mw": {a: round(sum(p["mw"] for p in ps if p.get("area") == a and isinstance(p.get("mw"), (int, float))))
                    for a in {p.get("area") for p in ps if p.get("area")}},
        "pref": Counter(p.get("pref") for p in ps if p.get("pref")),
        "scheme": Counter(p.get("scheme") or "確認中" for p in ps),
        "status": Counter(p.get("status") or "確認中" for p in ps),
        "live": sum(1 for p in ps if p.get("live")),
        "ym_known": len(ym), "half": half,
        "lead": lead, "lead_median": (lead[len(lead) // 2] if lead else None), "bands": bands,
        "basis": Counter(p.get("leadBasis") or "unspecified" for p in ps if isinstance(p.get("leadMonths"), (int, float))),
        "undecided": sum(1 for p in ps if not p.get("live") and not (p.get("codYm") and p["codYm"] >= today_ym)),
        "new14": sum(1 for p in ps if is_new(p, today)),
        "first_seen": sorted(fs.items())[-6:],
    }


# ---------------------------------------------------------------- 部品
def bar_rows(pairs, total, unit="件"):
    """横棒の行。pairs=[(ラベル, 値)]。CSS だけで描く（JS 無し）。"""
    if not pairs or not total:
        return "<p class=\"md-note\">該当なし</p>"
    mx = max(v for _, v in pairs) or 1
    out = ['<div class="md-bars">']
    for label, v in pairs:
        pct = v / total * 100
        out.append(f'<div class="md-bar"><span class="md-bar-l">{_esc(label)}</span>'
                   f'<span class="md-bar-t"><span class="md-bar-f" style="width:{v / mx * 100:.1f}%"></span></span>'
                   f'<span class="md-bar-v">{v}{unit}<small>（{pct:.0f}%）</small></span></div>')
    out.append("</div>")
    return "\n".join(out)


def rows_html(ps, today):
    """管内ページの静的一覧。/projects の静的一覧（inject_stats.render_list）と同じ文言・同じ並び。"""
    today_ym = today.strftime("%Y-%m")

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)
    lines = ['<ul class="pj-static">']
    for p in sorted(ps, key=key):
        mw = p.get("mw"); mwh = p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        cod = cod_text(p, today_ym)
        parts = [f"{_esc(p.get('pref') or '所在県 確認中')}", _esc(p.get("voltage") or "—"), size,
                 _esc(cod if p.get("live") else "連系の見込み " + cod)]
        if not p.get("live"):
            parts.append(_esc(p.get("status") or "—"))
        parts.append(_esc(p.get("scheme") or "取得の形 確認中"))
        if is_new(p, today):
            parts.append(f"新着（{_esc(p['firstSeen'])} 掲載）")
        pid = _esc(p.get("id") or "")
        lines.append(f'<li id="p-{pid}"><a href="/projects#p-{pid}"><b>{pid}</b></a>　' + "｜".join(parts) + "</li>")
    lines.append("</ul>")
    return "\n".join(lines)


CSS = """
:root{--navy:#1F2A48;--navy-light:#2D3A5C;--gold:#C49A3C;--green:#1A7A4C;--white:#fff;--off-white:#F5F5F3;--text:#1F2A48;--text-2:#555555;--text-3:#8C8C8C;--border:#E6E6E6;--sans:'Noto Sans JP',sans-serif;--serif:'Noto Sans JP',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}html{font-size:16px;scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--text);background:var(--white);line-height:1.9;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.container{max-width:1100px;margin:0 auto;padding:0 24px}
.section-label{font-size:.7rem;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-bottom:12px}
.hero{padding:64px 0 40px;background:linear-gradient(160deg,var(--white) 0%,var(--off-white) 60%,#EEEEEC 100%)}
.hero h1{font-family:var(--serif);font-size:clamp(1.5rem,3.4vw,2.2rem);font-weight:700;color:var(--navy);line-height:1.5;margin-bottom:16px}
.hero p{font-size:.95rem;color:var(--text-2);max-width:760px}
.badge{display:inline-block;margin-bottom:16px;padding:5px 14px;background:rgba(26,122,76,.1);color:var(--green);font-size:.72rem;font-weight:600;letter-spacing:1px;border-radius:4px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:28px 0 0}
.kpi div{background:var(--white);border:1px solid var(--border);border-radius:8px;padding:16px 18px}
.kpi b{display:block;font-family:var(--serif);font-size:1.6rem;color:var(--navy);line-height:1.3}
.kpi span{font-size:.78rem;color:var(--text-2)}
section.md{padding:40px 0;border-top:1px solid var(--border)}
h2.md-h{font-family:var(--serif);font-size:1.25rem;font-weight:600;color:var(--navy);margin-bottom:10px}
.md-lead{font-size:.92rem;color:var(--text-2);margin-bottom:18px;max-width:760px}
.md-bars{max-width:760px}.md-bar{display:grid;grid-template-columns:9.5em 1fr 8.5em;align-items:center;gap:10px;font-size:.88rem;padding:4px 0}
.md-bar-l{color:var(--text)}.md-bar-t{height:12px;background:#EFECE6;border-radius:3px;overflow:hidden}.md-bar-f{display:block;height:100%;background:var(--gold)}
.md-bar-v{color:var(--text-2);text-align:right}.md-bar-v small{color:var(--text-3);font-size:.8em;margin-left:2px}
.md-note{font-size:.84rem;color:var(--text-3);margin-top:8px}
.md-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px 40px}
table.md-t{border-collapse:collapse;font-size:.88rem;max-width:760px;width:100%}.md-t th,.md-t td{border-bottom:1px solid var(--border);padding:7px 10px;text-align:left}.md-t th{color:var(--text-2);font-weight:500;background:var(--off-white)}.md-t td.n{text-align:right;font-variant-numeric:tabular-nums}
.areas{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;max-width:900px}
.areas a{display:block;border:1px solid var(--border);border-radius:8px;padding:14px 16px;text-decoration:none;color:var(--text);background:var(--white)}
.areas a:hover{border-color:var(--gold)}.areas b{display:block;color:var(--navy);font-size:1rem}.areas span{font-size:.82rem;color:var(--text-2)}
.pj-static{list-style:none;padding:0;margin:0;border-top:1px solid var(--border);max-width:900px}
.pj-static li{padding:9px 0;border-bottom:1px solid var(--border);font-size:.88rem;line-height:1.7}.pj-static li a{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--gold)}
.cite{margin-top:28px;background:var(--off-white);border:1px solid var(--border);border-radius:8px;padding:16px 20px;font-size:.86rem;line-height:1.9;max-width:760px}
.cite .cite-h{font-size:.8em;font-weight:700;color:var(--gold);letter-spacing:.08em;margin-bottom:6px}
.cta{padding:56px 0;background:linear-gradient(160deg,var(--navy) 0%,var(--navy-light) 100%);text-align:center;color:#fff}
.cta h2{font-family:var(--serif);font-size:1.4rem;font-weight:600;margin-bottom:10px}.cta p{color:rgba(255,255,255,.8);font-size:.92rem;margin-bottom:22px}
.btn-primary{display:inline-flex;align-items:center;gap:8px;padding:14px 32px;background:var(--gold);color:var(--navy);font-size:.9rem;font-weight:600;text-decoration:none;border-radius:4px;margin:4px}
.btn-secondary{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:transparent;color:#fff;font-size:.88rem;font-weight:600;text-decoration:none;border-radius:4px;border:1px solid rgba(255,255,255,.45);margin:4px}
.scix-footer{background-color:#1F2A48;color:rgba(255,255,255,0.85);font-family:'Noto Sans JP',sans-serif;font-weight:300;font-size:12.5px;line-height:1.9;padding:44px 28px 32px;width:100%}
.scix-footer-inner{display:flex;flex-direction:column;align-items:center;gap:28px}.scix-footer-logo img{height:48px;width:auto;display:block;opacity:.95}
.scix-footer-info{text-align:center}.scix-footer-copyright{font-size:11px;letter-spacing:.04em;color:rgba(255,255,255,.55);margin-top:20px}
.scix-footer-company{font-size:12.5px;line-height:2;color:rgba(255,255,255,.8)}.scix-footer-company .company-name{font-weight:500;font-size:13.5px;color:rgba(255,255,255,.92);margin-bottom:2px}
.scix-footer-company .representative{margin-top:4px;color:rgba(255,255,255,.6);font-size:12px}.scix-footer-company a{color:rgba(255,255,255,.8);text-decoration:none}.scix-footer-company a:hover{color:#C49A3C}
.scix-footer-divider{width:60px;border:none;border-top:1px solid rgba(196,154,60,.5)}
@media(max-width:640px){.md-bar{grid-template-columns:7em 1fr 7em;font-size:.82rem}.hero{padding:48px 0 32px}}
"""

FOOTER = """<footer class="scix-footer">
  <div class="scix-footer-inner">
    <a href="https://www.scix.co.jp/" class="scix-footer-logo" aria-label="ScienceX ホーム">
      <img width="300" height="118" src="/img/logo-white.png" alt="ScienceX サイエンスエックス株式会社" loading="lazy" />
    </a>
    <hr class="scix-footer-divider" />
    <div class="scix-footer-info">
      <div class="scix-footer-company">
        <div class="company-name">サイエンスエックス株式会社</div>
        〒103-0016 東京都中央区日本橋小網町8-2<br>
        BIZMARKS日本橋茅場町<br>
        TEL: <a href="tel:0366913484">03-6691-3484</a><br>
        MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>
        <div class="representative">代表取締役 中島 晋也（工学博士）</div>
      </div>
      <div class="scix-footer-nav" style="margin-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:10px 22px;justify-content:center;">
        <a href="/grid-storage" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">蓄電池事業のしくみ</a>
        <a href="/transfer" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件を買う</a>
        <a href="/projects" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">販売中の案件一覧</a>
        <a href="/market-data" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">売り案件の市場データ</a>
        <a href="/sourcing" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件・権利を売る</a>
        <a href="/sell-form" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">案件・権利の売却査定</a>
        <a href="/knowledge" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">ナレッジ</a>
        <a href="/qa" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">入門Q&amp;A</a>
        <a href="/company" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">会社案内</a>
        <a href="/contact" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">お問い合わせ</a>
        <a href="/investors" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">系統用蓄電池への投資</a>
        <a href="/fund" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">系統用蓄電池ファンド</a>
        <a href="/privacy" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">プライバシーポリシー</a>
      </div>
      <div class="scix-footer-copyright">&copy; 2025–2026 Science X Inc. All Rights Reserved.</div>
    </div>
  </div>
</footer>"""

FONTS = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Noto+Sans+JP:wght@400;500;700;900&display=swap"


def head(title, desc, path, jsonld, robots="index,follow,max-image-preview:large"):
    url = BASE + path
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<link rel="icon" type="image/svg+xml" href="/img/favicon.svg">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-SNNK8MP9N9"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-SNNK8MP9N9');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ja" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{_esc(title)}">
<meta property="og:description" content="{_esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="ScienceX">
<meta property="og:image" content="{BASE}/img/ogp-x.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(title)}">
<meta name="twitter:description" content="{_esc(desc)}">
<meta name="twitter:image" content="{BASE}/img/ogp-x.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONTS}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONTS}"></noscript>
<style>{CSS}</style>
{jsonld}
<link rel="stylesheet" href="/theme.css">
</head>
<body>
<script src="/header.js"></script>
"""


def ld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=1) + '\n</script>'


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def nav_crumbs(items):
    sep = '<span style="color:#C49A3C;margin:0 7px">›</span>'
    parts = [f'<a href="{u}" style="color:#555555;text-decoration:none">{_esc(n)}</a>' for n, u in items[:-1]]
    parts.append(f'<span style="color:#8C8C8C">{_esc(items[-1][0])}</span>')
    return ('<nav data-scix-breadcrumb aria-label="breadcrumb" style="max-width:1100px;margin:0 auto;padding:14px 24px 0;'
            "font-family:'Noto Sans JP',sans-serif;font-size:12.5px;line-height:1.6;color:#8C8C8C\">" + sep.join(parts) + '</nav>')


ORG = {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "サイエンスエックス株式会社",
       "url": BASE + "/"}

CTA = """<section class="cta"><div class="container">
  <h2>案件そのものは、一覧でご覧いただけます</h2>
  <p>所在県・規模・連系の見込み・進み具合までは秘密保持契約なしで公開しています。売りたい方は、査定は無料で、最初の連絡は5行で足ります。</p>
  <a class="btn-primary" href="/projects">販売中の案件を見る →</a>
  <a class="btn-secondary" href="/sell-form">案件・権利の売却査定（無料）</a>
</div></section>
"""

NOTE_SCOPE = ("ここで数えているのは、当社に持ち込まれ、一覧への掲載を了承いただいた系統用蓄電池（蓄電所）の売り案件です。"
              "日本の市場全体の統計ではなく、当社の観測です。価格・地番・売主は載せていません（秘密保持契約の後に個別にお出しします）。"
              "数字は毎朝、案件一覧と同じデータから自動で集計し直しています。")


# ---------------------------------------------------------------- ページ
def render_market(ps, today, generated):
    s = stats(ps, today)
    path = "/market-data"
    title = f"系統用蓄電池の売り案件 市場データ｜管内別の件数・規模・連系の見込み（{s['n']}件・毎朝更新）｜サイエンスエックス"
    desc = (f"当社が扱う系統用蓄電池（蓄電所）の売り案件{s['n']}件・合計{s['mw']:,}MWを、管内別・都道府県別・電圧別・取得の形・"
            f"連系の見込み・回答書の工期で集計。接続検討の回答が出た案件だけ。毎朝更新。価格は秘密保持契約の後に個別に。")
    area_pairs = [(f"{a}（{nm}）", s["area"].get(a, 0)) for a, _, nm in AREAS if s["area"].get(a)]
    other_areas = [(a, n) for a, n in s["area"].items() if a not in {x[0] for x in AREAS}]
    area_pairs += [(a, n) for a, n in other_areas]
    half_pairs = sorted(s["half"].items())
    band_order = ["6か月以内", "7〜12か月", "13〜24か月", "25か月以上"]
    band_pairs = [(b, s["bands"][b]) for b in band_order if s["bands"].get(b)]
    basis_label = {"payment": "工事費負担金の入金から", "apply": "接続契約の申込みから", "contract": "ご契約から", "unspecified": "起点の記載なし（回答書の記載のまま）"}
    basis_pairs = [(basis_label.get(k, k), v) for k, v in s["basis"].most_common()]
    month_rows = "".join(f"<tr><td>{_esc(m)}</td><td class=\"n\">{n}</td></tr>" for m, n in s["first_seen"])
    pref_rows = "".join(f"<tr><td>{_esc(p)}</td><td class=\"n\">{n}</td></tr>" for p, n in s["pref"].most_common(10))
    area_table = "".join(
        f'<tr><td><a href="/projects-{slug}">{_esc(a)}（{_esc(nm)}）</a></td><td class="n">{s["area"].get(a, 0)}</td>'
        f'<td class="n">{s["area_mw"].get(a, 0):,}</td></tr>' for a, slug, nm in AREAS if s["area"].get(a))
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "WebPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "ja", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/", "name": "ScienceX"}, "publisher": ORG}),
        ld({"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + path + "#dataset",
            "name": "系統用蓄電池の売り案件 市場データ（サイエンスエックス観測）",
            "description": "系統用蓄電池（蓄電所）の売り案件の件数・規模・電圧区分・取得の形・連系の見込み・回答書の工期を、管内別・都道府県別に集計したデータ。接続検討の回答が出た案件のみ。価格・地番・売主は含まない。毎朝更新。",
            "url": BASE + path, "inLanguage": "ja", "creator": ORG, "publisher": ORG, "isAccessibleForFree": True,
            "dateModified": generated, "temporalCoverage": f"2026-06/{generated[:7]}",
            "spatialCoverage": {"@type": "Place", "name": "日本（9電力管内）"},
            "keywords": ["系統用蓄電池", "蓄電所", "売り案件", "市場データ", "連系の見込み", "工事費負担金", "権利譲渡", "完成渡し"],
            "creditText": f"出典: サイエンスエックス株式会社『系統用蓄電池の売り案件 市場データ』{BASE}{path}",
            "distribution": {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/projects.json"},
            "mainEntityOfPage": BASE + path}),
        ld(crumbs([("ホーム", BASE + "/"), ("案件一覧", BASE + "/projects"), ("売り案件の市場データ", BASE + path)])),
    ])
    body = f"""{nav_crumbs([("ホーム", "/"), ("案件一覧", "/projects"), ("売り案件の市場データ", path)])}
<section class="hero"><div class="container">
  <span class="badge">毎朝更新・当社観測</span>
  <div class="section-label">Market Data</div>
  <h1>系統用蓄電池の売り案件 市場データ</h1>
  <p>当社が扱う売り案件{s['n']}件を、管内・都道府県・電圧・取得の形・連系の見込み・回答書の工期で数えました。どの管内に何件あり、いつ連系する見込みで、権利で買える案件と完成渡しの案件がどれだけあるか。案件を探す前の見当付けと、売る前の相場観（件数の分布）にお使いください。{_esc(generated)} 時点です。</p>
  <div class="kpi">
    <div><b>{s['n']}件</b><span>販売中の案件</span></div>
    <div><b>{s['mw']:,}MW</b><span>合計出力（{s['mwh']:,}MWh）</span></div>
    <div><b>{len(s['pref'])}都道府県</b><span>{len(s['area'])}管内</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}件</b><span>特別高圧（10MW以上）</span></div>
    <div><b>{s['new14']}件</b><span>この{NEW_DAYS}日の新着</span></div>
  </div>
  <p class="md-note" style="margin-top:14px">{NOTE_SCOPE}</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">By Area</div>
  <h2 class="md-h">管内別の件数と規模</h2>
  <p class="md-lead">一般送配電事業者の管内ごとの件数です。管内名を押すと、その管内の案件一覧に移ります。</p>
  <div class="md-grid">
    <div>{bar_rows(area_pairs, s['n'])}</div>
    <div><table class="md-t"><thead><tr><th>管内</th><th>件数</th><th>合計MW</th></tr></thead><tbody>{area_table}</tbody></table></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">By Prefecture</div>
  <h2 class="md-h">都道府県別（上位10）</h2>
  <p class="md-lead">案件の多い都道府県です。{len(s['pref'])}都道府県に案件があります。</p>
  <table class="md-t"><thead><tr><th>都道府県</th><th>件数</th></tr></thead><tbody>{pref_rows}</tbody></table>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Voltage / Scheme / Stage</div>
  <h2 class="md-h">電圧区分・取得の形・進み具合</h2>
  <p class="md-lead">高圧は2MW級が中心で、特別高圧は10MW以上です。取得の形は、権利で買って自分で建てる「権利譲渡」と、建った状態で受け取る「完成渡し」に分かれます。進み具合は、接続検討の回答までか、契約申込みの本回答まで進んで工事費負担金が確定しているか、連系済みかです。</p>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">電圧区分</h3>{bar_rows(s['volt'].most_common(), s['n'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">取得の形</h3>{bar_rows(s['scheme'].most_common(), s['n'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">進み具合</h3>{bar_rows(s['status'].most_common(), s['n'])}</div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Connection Timing</div>
  <h2 class="md-h">連系の見込み</h2>
  <p class="md-lead">運転開始の予定が決まっている案件は年度の上期・下期で、決まっていない案件は接続検討回答書に書かれた「連系までにかかる月数」で数えました。予定が決まっているのは{s['ym_known']}件、月数だけが分かるのは{len(s['lead'])}件、時期を確認中が{s['undecided'] - len([1 for p in ps if not p.get('live') and not (p.get('codYm') and p['codYm'] >= today.strftime('%Y-%m')) and isinstance(p.get('leadMonths'), (int, float))])}件です。月数は回答書の記載で、工事費負担金の入金から数えるものが中心です。</p>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">運転開始の予定（年度・半期）</h3>{bar_rows(half_pairs, s['ym_known'])}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">回答書の工期（連系までの月数）{f'　中央値 {s["lead_median"]}か月' if s['lead_median'] else ''}</h3>{bar_rows(band_pairs, len(s['lead']))}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">月数の起点</h3>{bar_rows(basis_pairs, len(s['lead']))}</div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">New Listings</div>
  <h2 class="md-h">掲載の推移</h2>
  <p class="md-lead">月ごとに一覧へ載せた件数です。売却済み・売り止めで外した案件は含みません。</p>
  <table class="md-t"><thead><tr><th>掲載月</th><th>件数</th></tr></thead><tbody>{month_rows}</tbody></table>
  <div class="cite"><div class="cite-h">このデータの引用について</div>本ページの数値は、出典を明記していただければ、記事・資料・社内検討にそのままお使いいただけます。推奨する出典表記: 「出典: サイエンスエックス株式会社『系統用蓄電池の売り案件 市場データ』{BASE}{path}（確認日 YYYY-MM-DD）」。元データは <a href="/projects.json">projects.json</a>（公開項目のみ）です。数字の読み方は <a href="/column-project-price">蓄電所は、いくらで買えるのか</a>（取得価格の中央値）と <a href="/column-study-reply">接続検討回答書を毎日読む当社が、最初に見る6か所</a> に。</div>
</div></section>
{CTA}{FOOTER}
</body>
</html>
"""
    return head(title, desc, path, jsonld) + body


def render_area(ps_all, area, slug, operator, today, generated):
    ps = [p for p in ps_all if p.get("area") == area]
    s = stats(ps, today)
    path = f"/projects-{slug}"
    n = s["n"]
    title = f"{area}電力管内（{operator}）の系統用蓄電池 売り案件 {n}件｜高圧・特別高圧・連系の見込み｜サイエンスエックス"
    if area in ("東京", "中部", "九州", "関西", "中国", "東北", "北海道", "北陸", "四国"):
        title = f"{operator}管内の系統用蓄電池 売り案件 {n}件｜連系の見込み・取得の形｜サイエンスエックス"
    desc = (f"{operator}管内（{area}エリア）で当社が扱う系統用蓄電池（蓄電所）の売り案件{n}件・合計{s['mw']:,}MW。"
            f"都道府県・電圧・規模・連系の見込み・進み具合・取得の形まで秘密保持契約なしで公開。接続検討の回答が出た案件だけ。毎朝更新。")
    robots = "index,follow,max-image-preview:large" if n >= MIN_INDEX else "noindex,follow"
    pref_pairs = s["pref"].most_common()
    half_pairs = sorted(s["half"].items())
    band_order = ["6か月以内", "7〜12か月", "13〜24か月", "25か月以上"]
    band_pairs = [(b, s["bands"][b]) for b in band_order if s["bands"].get(b)]
    items = [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/projects#p-{p.get('id')}",
              "name": f"{p.get('id')} {p.get('pref') or ''} {p.get('voltage') or ''} {p.get('mw') or ''}MW"}
             for i, p in enumerate(sorted(ps, key=lambda p: cod_sort_key(p, today.strftime('%Y-%m'))))]
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": BASE + path + "#webpage", "url": BASE + path,
            "name": title, "description": desc, "inLanguage": "ja", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/", "name": "ScienceX"}, "publisher": ORG,
            "mainEntity": {"@type": "ItemList", "numberOfItems": n, "itemListElement": items}}),
        ld(crumbs([("ホーム", BASE + "/"), ("案件一覧", BASE + "/projects"), (f"{area}電力管内", BASE + path)])),
    ])
    others = "　".join(f'<a href="/projects-{sl}">{_esc(a)}（{s_all}件）</a>'
                      for a, sl, _ in AREAS if a != area for s_all in [sum(1 for p in ps_all if p.get("area") == a)] if s_all)
    list_html = rows_html(ps, today) if ps else '<p class="md-note">いまこの管内に販売中の案件はありません。新しく載ったら、ここと <a href="/projects">案件一覧</a> に出ます。</p>'
    body = f"""{nav_crumbs([("ホーム", "/"), ("案件一覧", "/projects"), (f"{area}電力管内", path)])}
<section class="hero"><div class="container">
  <span class="badge">NDA不要・毎朝更新</span>
  <div class="section-label">Projects by Area</div>
  <h1>{_esc(operator)}管内の系統用蓄電池 売り案件 {n}件</h1>
  <p>{_esc(area)}エリア（{_esc(operator)}管内）で当社が扱う、接続検討の回答が出た系統用蓄電池（蓄電所）の案件です。所在県・電圧・規模・連系の見込み・進み具合・取得の形までは秘密保持契約なしでご覧いただけます。地番・売主・価格は本ページでは開示していません。{_esc(generated)} 時点です。</p>
  <div class="kpi">
    <div><b>{n}件</b><span>販売中の案件</span></div>
    <div><b>{s['mw']:,}MW</b><span>合計出力（{s['mwh']:,}MWh）</span></div>
    <div><b>{s['volt'].get('高圧', 0)}件</b><span>高圧（2MW級が中心）</span></div>
    <div><b>{s['volt'].get('特別高圧', 0)}件</b><span>特別高圧（10MW以上）</span></div>
    <div><b>{s['scheme'].get('権利譲渡', 0)}件</b><span>権利譲渡（自分で建てる）</span></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Overview</div>
  <h2 class="md-h">{_esc(area)}エリアの案件の内訳</h2>
  <div class="md-grid">
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">都道府県</h3>{bar_rows(pref_pairs, n)}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">運転開始の予定（年度・半期）</h3>{bar_rows(half_pairs, s['ym_known'])}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">回答書の工期（連系までの月数）{f'　中央値 {s["lead_median"]}か月' if s['lead_median'] else ''}</h3>{bar_rows(band_pairs, len(s['lead']))}</div>
    <div><h3 style="font-size:.95rem;color:var(--navy);margin-bottom:6px">進み具合</h3>{bar_rows(s['status'].most_common(), n)}
      <h3 style="font-size:.95rem;color:var(--navy);margin:14px 0 6px">取得の形</h3>{bar_rows(s['scheme'].most_common(), n)}</div>
  </div>
  <p class="md-note" style="margin-top:14px">{NOTE_SCOPE} 全国の集計は <a href="/market-data">売り案件の市場データ</a> に。</p>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Projects</div>
  <h2 class="md-h">{_esc(operator)}管内の案件一覧（{n}件・{_esc(generated)} 更新）</h2>
  <p class="md-lead">連系が早い順です。案件番号を押すと、全国の一覧の該当行に移ります。そこで案件にチェックを入れると、資料をまとめて請求できます。</p>
  {list_html}
  <p class="md-note" style="margin-top:16px">ほかの管内: {others}</p>
</div></section>
{CTA}{FOOTER}
</body>
</html>
"""
    return head(title, desc, path, jsonld, robots) + body


# ---------------------------------------------------------------- 英語の案件一覧（en/projects.html）
# 公開してよい項目（projects.json の PUBLIC_KEYS）だけを使う。価格・住所・売主は持っていないので出せない。
EN_AREA = {"北海道": "Hokkaido", "東北": "Tohoku", "東京": "Tokyo", "中部": "Chubu", "北陸": "Hokuriku", "関西": "Kansai",
           "中国": "Chugoku", "四国": "Shikoku", "九州": "Kyushu", "沖縄": "Okinawa"}
EN_PREF = {
    "北海道": "Hokkaido", "青森県": "Aomori", "岩手県": "Iwate", "宮城県": "Miyagi", "秋田県": "Akita", "山形県": "Yamagata",
    "福島県": "Fukushima", "茨城県": "Ibaraki", "栃木県": "Tochigi", "群馬県": "Gunma", "埼玉県": "Saitama", "千葉県": "Chiba",
    "東京都": "Tokyo", "神奈川県": "Kanagawa", "新潟県": "Niigata", "富山県": "Toyama", "石川県": "Ishikawa", "福井県": "Fukui",
    "山梨県": "Yamanashi", "長野県": "Nagano", "岐阜県": "Gifu", "静岡県": "Shizuoka", "愛知県": "Aichi", "三重県": "Mie",
    "滋賀県": "Shiga", "京都府": "Kyoto", "大阪府": "Osaka", "兵庫県": "Hyogo", "奈良県": "Nara", "和歌山県": "Wakayama",
    "鳥取県": "Tottori", "島根県": "Shimane", "岡山県": "Okayama", "広島県": "Hiroshima", "山口県": "Yamaguchi",
    "徳島県": "Tokushima", "香川県": "Kagawa", "愛媛県": "Ehime", "高知県": "Kochi", "福岡県": "Fukuoka", "佐賀県": "Saga",
    "長崎県": "Nagasaki", "熊本県": "Kumamoto", "大分県": "Oita", "宮崎県": "Miyazaki", "鹿児島県": "Kagoshima",
    "沖縄県": "Okinawa",
}
EN_VOLT = {"高圧": "High voltage", "特別高圧": "Extra-high voltage", "低圧": "Low voltage"}
EN_STATUS = {"接続検討回答済": "Grid connection study answered", "負担金確定": "Grid cost confirmed", "連系済": "Grid-connected"}
EN_SCHEME = {"完成渡し": "Completed-build handover", "権利譲渡": "Transfer of rights"}
EN_LEAD = {"payment": "about {n} months after grid cost payment", "apply": "about {n} months after connection application",
           "contract": "about {n} months after contract", "unspecified": "about {n} months of grid work"}
EN_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

EN_CSS = """
.pj-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:26px 0 0}
.pj-sum div{background:var(--white);border:1px solid var(--border);border-radius:8px;padding:14px 18px}
.pj-sum b{display:block;font-size:1.5rem;color:var(--navy);line-height:1.3}.pj-sum span{font-size:.78rem;color:var(--text-2)}
.pj-filter{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:flex-end;margin:0 0 14px}
.pj-filter label{display:flex;flex-direction:column;font-size:.76rem;color:var(--text-2);gap:4px;min-width:0}
.pj-filter select{font:inherit;font-size:.9rem;padding:8px 10px;border:1px solid #C9C9C9;border-radius:6px;background:#fff;color:var(--navy);max-width:100%}
.pj-count{font-size:.86rem;color:var(--text-2);margin-left:auto}
.pj-t{border-collapse:collapse;width:100%;font-size:.86rem}
.pj-t th,.pj-t td{border-bottom:1px solid var(--border);padding:8px 10px;text-align:left;vertical-align:top}
.pj-t th{background:var(--off-white);color:var(--text-2);font-weight:500;white-space:nowrap}
.pj-t td.n,.pj-t th.n{text-align:right;font-variant-numeric:tabular-nums}
.pj-t tr[hidden]{display:none!important}
.pj-new{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:3px;background:rgba(26,122,76,.12);color:var(--green);font-size:.7rem;font-weight:600}
.pj-none{display:none;padding:18px 0;color:var(--text-2)}
.pj-dr{background:var(--off-white);border:1px solid var(--border);border-radius:8px;padding:22px 24px;max-width:860px}
.pj-dr ol{margin:10px 0 18px 1.3em;font-size:.92rem;color:var(--text-2)}
@media(max-width:700px){
  .pj-t,.pj-t tbody,.pj-t tr,.pj-t td{display:block;width:100%}
  .pj-t thead{display:none}
  .pj-t tr{border:1px solid var(--border);border-radius:8px;margin-bottom:10px;padding:6px 12px}
  .pj-t td{border:none;padding:3px 0;text-align:left!important;display:flex;justify-content:space-between;gap:12px}
  .pj-t td::before{content:attr(data-l);color:var(--text-3);font-size:.78rem;flex:0 0 38%}
  .pj-count{margin-left:0;width:100%}
  .pj-filter label{flex:1 1 44%}
}
"""

EN_FOOTER = """<footer class="scix-footer">
  <div class="scix-footer-inner">
    <a href="https://www.scix.co.jp/en" class="scix-footer-logo" aria-label="ScienceX Home">
      <img width="300" height="118" src="/img/logo-white.png" alt="ScienceX — Science X Inc." loading="lazy" />
    </a>
    <hr class="scix-footer-divider" />
    <div class="scix-footer-info">
      <div class="scix-footer-company">
        <div class="company-name">Science X Inc.</div>
        8-2 Nihonbashi Koamicho, Chuo-ku, Tokyo 103-0016<br>
        BIZMARKS Nihonbashi Kayabacho<br>
        TEL: <a href="tel:0366913484">03-6691-3484</a><br>
        MAIL: <a href="mailto:s@scix.co.jp">s@scix.co.jp</a>
        <div class="representative">Shinya Nakashima, Ph.D. (Eng.), Representative Director</div>
      </div>
      <div class="scix-footer-nav" style="margin-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:10px 22px;justify-content:center;">
        <a href="/en" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Home</a>
        <a href="/en/projects" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Projects</a>
        <a href="/en/knowledge" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Knowledge</a>
        <a href="/en/qa" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Q&amp;A</a>
        <a href="/en/glossary" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Glossary</a>
        <a href="/en/market-entry-guide" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Market Entry Guide</a>
        <a href="/en/contact" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Contact</a>
        <a href="/privacy" style="color:rgba(255,255,255,0.7);text-decoration:none;border-bottom:1px solid rgba(196,154,60,0.4);">Privacy Policy</a>
      </div>
      <div class="scix-footer-copyright">&copy; 2025–2026 Science X Inc. All Rights Reserved.</div>
    </div>
  </div>
</footer>"""


def en_cod(p, today_ym):
    """Expected COD（連系の見込み）の英語表示。inject_stats.cod_text と同じ規則（年月が過去なら出さない）。"""
    if p.get("live"):
        return "Grid-connected"
    ym = p.get("codYm")
    ym = ym if (ym and ym >= today_ym) else None
    n = p.get("leadMonths")
    lead = EN_LEAD.get(p.get("leadBasis") or "unspecified", EN_LEAD["unspecified"]).format(n=n) if n else ""
    if ym:
        return f"{EN_MON[int(ym[5:7]) - 1]} {ym[:4]}" + (f" ({lead})" if lead else "")
    return lead or "Under review"


def render_en_projects(ps, today, generated):
    today_ym = today.strftime("%Y-%m")
    path = "/en/projects"
    url = BASE + path
    n = len(ps)
    mw = round(sum(p.get("mw") or 0 for p in ps))
    volt = Counter(p.get("voltage") for p in ps)
    prefs = len({p.get("pref") for p in ps if p.get("pref")})

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)

    ps = sorted(ps, key=key)
    title = "Japan Grid-Scale BESS Projects Listed by ScienceX | High-Voltage & Extra-High-Voltage"
    desc = (f"{n} grid-scale battery storage (BESS) projects in Japan listed by ScienceX, about {mw:,} MW in total: "
            "high-voltage (~2 MW) and extra-high-voltage, from development rights with grid connection answers to grid-connected assets. "
            "Area, prefecture, voltage, size, status and expected COD. No prices shown. Updated daily.")
    areas = [a for a in EN_AREA if any(p.get("area") == a for p in ps)]
    area_opts = "".join(f'<option value="{_esc(a)}">{EN_AREA[a]}</option>' for a in areas)
    volt_opts = "".join(f'<option value="{_esc(v)}">{EN_VOLT[v]}</option>' for v in EN_VOLT if volt.get(v))
    stat_opts = "".join(f'<option value="{_esc(k)}">{v}</option>' for k, v in EN_STATUS.items() if any(p.get("status") == k for p in ps))
    rows = []
    for p in ps:
        pid = _esc(p.get("id") or "")
        m, mh = p.get("mw"), p.get("mwh")
        new = '<span class="pj-new">New</span>' if is_new(p, today) else ""
        rows.append(
            f'<tr id="p-{pid}" data-area="{_esc(p.get("area") or "")}" data-volt="{_esc(p.get("voltage") or "")}" data-status="{_esc(p.get("status") or "")}">'
            f'<td data-l="ID">{pid}{new}</td>'
            f'<td data-l="Area">{EN_AREA.get(p.get("area"), "TBC")}</td>'
            f'<td data-l="Prefecture">{EN_PREF.get(p.get("pref"), "Under review")}</td>'
            f'<td data-l="Voltage">{EN_VOLT.get(p.get("voltage"), "—")}</td>'
            f'<td class="n" data-l="MW">{f"{m:g}" if isinstance(m, (int, float)) else "—"}</td>'
            f'<td class="n" data-l="MWh">{f"{mh:g}" if isinstance(mh, (int, float)) else "—"}</td>'
            f'<td data-l="Status">{EN_STATUS.get(p.get("status"), "—")}</td>'
            f'<td data-l="Structure">{EN_SCHEME.get(p.get("scheme"), "Under review")}</td>'
            f'<td data-l="Expected COD">{_esc(en_cod(p, today_ym))}</td></tr>')
    items = [{"@type": "ListItem", "position": i + 1, "name": f"{p.get('id')} {EN_PREF.get(p.get('pref'), '')} {EN_VOLT.get(p.get('voltage'), '')} {p.get('mw') or ''} MW".replace("  ", " ")}
             for i, p in enumerate(ps)]
    jsonld = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": title,
            "description": desc, "inLanguage": "en", "dateModified": generated,
            "isPartOf": {"@type": "WebSite", "url": BASE + "/en", "name": "ScienceX"},
            "publisher": {"@type": "Organization", "@id": BASE + "/#organization", "name": "ScienceX", "legalName": "Science X Inc.", "url": BASE + "/en"},
            "mainEntity": {"@type": "ItemList", "numberOfItems": n, "itemListElement": items}}),
        ld(crumbs([("Home", BASE + "/en"), ("Projects", url)])),
    ])
    head_html = (head(title, desc, path, jsonld)
                 .replace('<html lang="ja">', '<html lang="en">')
                 .replace(f'<link rel="alternate" hreflang="ja" href="{url}">',
                          f'<link rel="alternate" hreflang="en" href="{url}">\n<link rel="alternate" hreflang="ja" href="{BASE}/projects">')
                 .replace('content="ja_JP"', 'content="en_US"')
                 .replace(f'{BASE}/img/ogp-x.png', f'{BASE}/img/ogp-x-en.png')
                 .replace(f"<style>{CSS}</style>", f"<style>{CSS}{EN_CSS}</style>"))
    body = f"""<section class="hero"><div class="container">
  <span class="badge">Updated daily · {_esc(generated)}</span>
  <div class="section-label">Projects</div>
  <h1>Japan grid-scale BESS projects available through ScienceX</h1>
  <p>High-voltage (~2 MW) and extra-high-voltage battery storage projects, from development rights with grid connection answers to grid-connected assets. Area, prefecture, voltage, size, status and expected COD are shown below. Prices, exact sites and counterparties are not published here.</p>
  <div class="pj-sum">
    <div><b>{n}</b><span>Listed projects</span></div>
    <div><b>{mw:,} MW</b><span>Total output</span></div>
    <div><b>{volt.get('高圧', 0)}</b><span>High voltage (~2 MW class)</span></div>
    <div><b>{volt.get('特別高圧', 0)}</b><span>Extra-high voltage</span></div>
    <div><b>{prefs}</b><span>Prefectures</span></div>
  </div>
</div></section>

<section class="md"><div class="container">
  <div class="section-label">Listed projects</div>
  <h2 class="md-h">Project list ({n} projects · updated {_esc(generated)})</h2>
  <p class="md-lead">Sorted by earliest expected COD (commercial operation date). Use the filters to narrow the list.</p>
  <div class="pj-filter">
    <label>Area<select id="f-area"><option value="">All areas</option>{area_opts}</select></label>
    <label>Voltage<select id="f-volt"><option value="">All voltage classes</option>{volt_opts}</select></label>
    <label>Status<select id="f-status"><option value="">All statuses</option>{stat_opts}</select></label>
    <span class="pj-count" id="pj-count" aria-live="polite">{n} of {n} projects</span>
  </div>
  <table class="pj-t" id="pj-table">
    <thead><tr><th>ID</th><th>Area</th><th>Prefecture</th><th>Voltage</th><th class="n">MW</th><th class="n">MWh</th><th>Status</th><th>Structure</th><th>Expected COD</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>
  <p class="pj-none" id="pj-none">No listed project matches these filters.</p>
  <p class="md-note" style="margin-top:14px">Area = the grid area of the transmission and distribution operator (Tokyo, Chubu, Kyushu and so on). Status: &ldquo;Grid connection study answered&rdquo; means the utility has issued its answer on the connection study; &ldquo;Grid cost confirmed&rdquo; means the grid construction cost has been fixed; &ldquo;Grid-connected&rdquo; means the project is already connected. Structure: &ldquo;Completed-build handover&rdquo; or &ldquo;Transfer of rights&rdquo; (the buyer builds). Expected COD is an estimate taken from the utility&rsquo;s answer and may change. These are ScienceX&rsquo;s own listings, not statistics for the whole Japanese market.</p>
</div></section>

<section class="md" id="dealroom"><div class="container">
  <div class="section-label">DealRoom</div>
  <h2 class="md-h">Detailed materials are in DealRoom, after an NDA</h2>
  <div class="pj-dr">
    <p class="md-lead" style="margin-bottom:6px">This list is an anonymous teaser. Site details, technical documents, grid-utility correspondence and the Q&amp;A for each project are shown in DealRoom, our members-only data room.</p>
    <ol>
      <li>Register on DealRoom (free of charge).</li>
      <li>Sign a confidentiality undertaking (NDA), in English or in Japanese, and email the signed PDF to us; there is no postal step.</li>
      <li>After our review, we enable your login and you can open the detailed information and documents for each project.</li>
    </ol>
    <a class="btn-primary" href="https://scix-dealroom2.pages.dev/en/register" rel="nofollow" onclick="window.gtag&&gtag('event','dr2_promo_click',{{target:'register_en'}})">Register on DealRoom &rarr;</a>
    <a class="btn-secondary" style="color:var(--navy);border-color:var(--navy)" href="/en/contact?intent=dealroom" onclick="window.gtag&&gtag('event','dr2_promo_click',{{target:'apply_en'}})">Or apply through our contact form</a>
    <p class="md-note" style="margin-top:12px">Undertaking (PDF, fillable): <a href="/files/scix-nda-pledge-en.pdf">English</a> / <a href="/files/scix-nda-pledge.pdf">Japanese</a>. Either version may be submitted.</p>
  </div>
</div></section>

<section class="cta"><div class="container">
  <h2>Looking for something specific?</h2>
  <p>Tell us the area, voltage class, size and timing you are looking for, and we will tell you which listed projects fit. Questions about NDA, structure or process are welcome.</p>
  <a class="btn-primary" href="/en/contact">Contact ScienceX &rarr;</a>
</div></section>
<script>
(function(){{
  var rows=[].slice.call(document.querySelectorAll('#pj-table tbody tr'));
  var sel={{area:document.getElementById('f-area'),volt:document.getElementById('f-volt'),status:document.getElementById('f-status')}};
  var cnt=document.getElementById('pj-count'),none=document.getElementById('pj-none');
  function apply(){{
    var shown=0;
    rows.forEach(function(r){{
      var ok=(!sel.area.value||r.dataset.area===sel.area.value)&&(!sel.volt.value||r.dataset.volt===sel.volt.value)&&(!sel.status.value||r.dataset.status===sel.status.value);
      r.hidden=!ok; if(ok)shown++;
    }});
    cnt.textContent=shown+' of '+rows.length+' projects';
    none.style.display=shown?'none':'block';
  }}
  Object.keys(sel).forEach(function(k){{sel[k].addEventListener('change',apply);}});
}})();
</script>
{EN_FOOTER}
</body>
</html>
"""
    return head_html + body


def main():
    check = "--check" in sys.argv
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        data = json.load(f)
    ps = data.get("projects", [])
    generated = data.get("generatedAt") or datetime.date.today().isoformat()
    today = datetime.date.today()
    pages = {"market-data.html": render_market(ps, today, generated)}
    for area, slug, operator in AREAS:
        pages[f"projects-{slug}.html"] = render_area(ps, area, slug, operator, today, generated)
    pages["en/projects.html"] = render_en_projects(ps, today, generated)
    changed = []
    for name, html in pages.items():
        path = os.path.join(ROOT, name)
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if cur != html:
            changed.append(name)
            if not check:
                open(path, "w", encoding="utf-8").write(html)
    if check:
        print(f"[check] 要更新 {len(changed)} ファイル" + (": " + " ".join(changed) if changed else ""))
        return 1 if changed else 0
    print(f"[ok] {len(changed)} ファイルを更新（{len(ps)}件・{generated}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
