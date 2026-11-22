#!/usr/bin/env python3
"""/llms.txt（機械向けの案内）を、sitemap の頁の題と説明から作る。

載せるのは今ある頁（sitemap.xml にある頁）の題・説明・住所だけ。題と説明は各頁の <title>・meta description そのまま
（言い換えない・足さない）。新しい主張・実績・利回り・手数料は書かない（O16-8）。手で直さない。

    python3 scripts/build_llms_txt.py           # llms.txt を書く
    python3 scripts/build_llms_txt.py --check   # 書かずに、ずれているかだけ見る（ずれていれば 1）

2026-11-22 中島「Seo 対策も徹底してやって」。
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.scix.co.jp"
OUT = os.path.join(ROOT, "llms.txt")


def file_of(url):
    p = url[len(BASE):].strip("/")
    for c in ([p + ".html", p + "/index.html"] if p else ["index.html"]):
        if os.path.isfile(os.path.join(ROOT, c)):
            return os.path.join(ROOT, c)
    return None


def head_of(path):
    s = open(path, encoding="utf-8").read()
    s = s[: s.find("</head>")]
    t = re.search(r"<title>(.*?)</title>", s, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', s)
    return (html.unescape(t.group(1)).strip() if t else ""), (html.unescape(d.group(1)).strip() if d else "")


def lang_of(url):
    p = url[len(BASE):]
    if p == "/en" or p.startswith("/en/"):
        return "en"
    if p == "/zh" or p.startswith("/zh-"):
        return "zh"
    return "ja"


def build():
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    urls = []
    for u in re.findall(r"<loc>([^<]+)</loc>", sm):
        if u not in urls:
            urls.append(u)
    groups = {"ja": [], "en": [], "zh": []}
    for u in urls:
        f = file_of(u)
        if not f:
            continue
        t, d = head_of(f)
        groups[lang_of(u)].append((u, t, d))
    top_t, top_d = head_of(os.path.join(ROOT, "index.html"))
    out = ["# ScienceX（サイエンスエックス株式会社）", "", "> " + top_d, "",
           "このファイルは、サイトにある頁の題と説明の一覧です（各頁の title と description をそのまま載せています）。", ""]
    names = {"ja": "日本語の頁", "en": "English pages", "zh": "中文页面"}
    for lg in ("ja", "en", "zh"):
        out.append("## " + names[lg])
        out.append("")
        for u, t, d in groups[lg]:
            out.append(f"- [{t}]({u})" + (f": {d}" if d else ""))
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else None
        if cur != text:
            print("ずれ: llms.txt")
            return 1
        return 0
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"llms.txt を書いた: {text.count(chr(10) + '- [')} 頁")
    return 0


if __name__ == "__main__":
    sys.exit(main())
