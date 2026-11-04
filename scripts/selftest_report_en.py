#!/usr/bin/env python3
"""build_reports.py の英語ページの自己試験（架空の文・外部アクセス無し）: python3 scripts/selftest_report_en.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_reports as B

EN = """# Grid-Scale Battery Storage Monthly Report, October 2026

Science X Inc.  Published November 1, 2026

Intro.

## 1. Three things

- First move.

(Figure 1  Average price (yen/kWh))

- Source: JEPX. Our tally.

---
Newsletter "X": https://www.linkedin.com/newsletters/123/
"""
fails = []


def ok(c, msg):
    if not c:
        fails.append(msg)


d = B.parse_md(EN, "en")
ok(d["issued"] == "2026-11-01", "issued")
ok(d["intro"] == "Intro.", "intro")
ok(d["sections"][0]["items"] == [("li", "First move."), ("fig", "Figure 1  Average price (yen/kWh)"), ("li", "Source: JEPX. Our tally.")], d["sections"][0]["items"])
ok(d["newsletter"].endswith("/123/"), "newsletter")
m = {"key": "2026-10"}
for bad in ("our seller list", "purchase price", "track record", "SHV-123", "a@example.com", "https://drive.google.com/x"):
    ok(B.safety_scan(m, bad, "", "en"), "should flag: " + bad)
ok(not B.safety_scan(m, "Selling rights, a 2MW site, sold out.", "", "en"), "false positive")
sec = B.render_section(d["sections"][0], {1: "x"}, "2026-10", set(), "en")
ok('src="/en/report/2026-10/f1.png"' in sec and '<p class="md-note">Source: JEPX' in sec, "render_section en")
sm = '<urlset>\n  <url><loc>https://www.scix.co.jp/report</loc><xhtml:link rel="alternate" hreflang="ja" href="https://www.scix.co.jp/report"/><priority>0.7</priority><lastmod>2026-11-01</lastmod></url>\n</urlset>\n'
rows = [{"key": "2026-10", "issued": "2026-11-01"}]
out = B.sitemap_add(sm, rows, rows)
ok('hreflang="en" href="https://www.scix.co.jp/en/report/2026-10"' in out and out.count("<loc>https://www.scix.co.jp/report</loc>") == 1, "sitemap en")
ok(B.sitemap_add(sm, rows) .count('hreflang="en"') == 0, "sitemap without en keeps ja only")
fa = B.en_fig_by_number({9: "p9", 12: "p12", 16: "p16", 18: "p18", 1: "p1"})   # 2026-11-05〜 図1＝f9（3つの稼ぎ口）・図2＝f1・図4＝f12（値差）・図7＝f18（管区ごとの約定率）・図8＝f16（一次の席の取り合い）
ok(fa.get(1) == "p9" and fa.get(2) == "p1" and fa.get(4) == "p12" and fa.get(7) == "p18" and fa.get(8) == "p16" and 3 not in fa, fa)
print("\n".join("NG " + str(f) for f in fails) if fails else "OK report_en")
sys.exit(1 if fails else 0)
