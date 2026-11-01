#!/usr/bin/env python3
"""コラム（column-*.html）の末尾に「この話題に近い入口」と DealRoom 登録のボタンを足す。

コラム本文は触らない（O16-1）。フッターの直前に、印のコメントで囲った1区画を入れる。
もう入っていれば作り直す（何度走らせても同じ）。

    python3 scripts/add_column_entrances.py          # 書き換える
    python3 scripts/add_column_entrances.py --check  # 書き換えずに、ずれているかだけ見る（ずれていれば 1）
"""
import glob
import re
import sys

REG = "https://scix-dealroom2.pages.dev/register"
BEGIN = "<!-- scix-entrances:begin -->"
END = "<!-- scix-entrances:end -->"
DOORS = {
    "overseas": ("/en", "海外の投資家の方へ", "English page"),
    "major": ("/for/major", "大手事業者・電力・商社の方へ", "特別高圧と高圧"),
    "sme": ("/for/sme", "事業会社の方へ（高圧1件から）", "1件から買う"),
    "dealers": ("/for/dealers", "案件をご紹介いただける方へ", "紹介の窓口"),
}
# 話題 → 入口3つ（上から順に近い）。どれにも当たらなければ既定。
RULES = [
    (r"foreign|jcstar|eprx|merchant|trading|day-ahead|capacity|balancing|price-cap|regional-revenue|auction|nonfirm|long-term",
     ["overseas", "major", "sme"]),
    (r"financing|buyer|options|investment-tax|tax|cashflow|insurance|om\b|equipment|construction|low-voltage|pricing|project-price|contract|transfer|revenue",
     ["sme", "major", "dealers"]),
    (r"land|zoning|noise|development|grid|area|hazard|biz|four-labels|aggregator|lda|somosomo|study",
     ["dealers", "major", "sme"]),
]
DEFAULT = ["major", "sme", "dealers"]


def doors_for(name):
    for pat, keys in RULES:
        if re.search(pat, name):
            return keys
    return DEFAULT


def block(name):
    cards = "".join(
        '<a target="_top" href="%s" style="display:block;padding:14px 16px;border:1px solid #E6E6E6;background:#fff;'
        'text-decoration:none;color:#1F2A48;font-weight:700;font-size:14px;line-height:1.6">%s'
        '<span style="display:block;font-weight:400;font-size:12px;color:#8C8C8C">%s →</span></a>' % DOORS[k]
        for k in doors_for(name)
    )
    return (
        BEGIN + "\n"
        '<div style="max-width:760px;margin:28px auto 0;padding:0 28px;font-family:\'Noto Sans JP\',sans-serif">\n'
        '  <h3 style="font-size:14px;color:#8C8C8C;margin:0 0 12px;font-weight:700">この話題に近い入口</h3>\n'
        '  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">' + cards + "</div>\n"
        '  <p style="margin:18px 0 0;text-align:center"><a target="_top" href="' + REG + '" '
        "onclick=\"window.gtag&&gtag('event','dr2_register_click',{target:'column_end'})\" "
        'style="display:inline-block;background:#1F2A48;color:#fff;font-weight:700;font-size:14px;padding:13px 30px;text-decoration:none">DealRoom に登録 →</a></p>\n'
        "</div>\n" + END + "\n"
    )


def main():
    check = "--check" in sys.argv
    bad = 0
    for p in sorted(glob.glob("column-*.html")):
        s = open(p, encoding="utf-8").read()
        name = p[len("column-"):-len(".html")]
        s2 = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n\n*", "", s, flags=re.S)
        m = re.search(r"<!-- ScienceX Footer|<style>\s*\.scix-footer|<footer class=\"scix-footer\"|<footer style=\"background-color:#1F2A48", s2)
        if not m:
            print("フッターの位置が見つからない:", p)
            bad = 1
            continue
        out = s2[:m.start()] + block(name) + "\n" + s2[m.start():]
        if out != s:
            if check:
                print("ずれ:", p)
                bad = 1
            else:
                open(p, "w", encoding="utf-8").write(out)
    return bad


if __name__ == "__main__":
    sys.exit(main())
