#!/usr/bin/env python3
"""変更した HTML の sitemap <lastmod> を今日にする（変更したページだけ。全体を触らない）。

    python3 scripts/seo/stamp_sitemap.py column-x.html en/column-x.html
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import file_to_url  # noqa: E402


def main() -> int:
    files = [f for f in sys.argv[1:] if f.endswith(".html")]
    if not files:
        return 0
    text = open("sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    n = 0
    for f in files:
        url = file_to_url(f)
        if not url:
            continue
        pat = re.compile(r"(<loc>" + re.escape(url) + r"</loc>.*?<lastmod>)([^<]+)(</lastmod>)", re.S)
        text, k = pat.subn(lambda m: m.group(1) + today + m.group(3), text, count=1)
        if k:
            n += 1
        else:
            print(f"sitemap に無い: {url}", file=sys.stderr)
    open("sitemap.xml", "w", encoding="utf-8").write(text)
    print(f"lastmod を {today} にした: {n} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
