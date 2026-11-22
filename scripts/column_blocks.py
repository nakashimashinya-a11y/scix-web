"""コラムの頁（column-*.html・en/column-*.html・zh-column-*.html）に、本文の外の区画を差す生成器の共通部品。

区画は <!-- scix-<名>:begin --> … <!-- scix-<名>:end --> の目印で囲み、生成器は自分の区画を消してから同じ場所に作り直す
（何度回しても同じ結果）。本文（中島さんの文）と h1 は触らない。

置き場は2つ:
  上（top）: 本文の頭＝<div class="article-body"> の直後。その箱が無い頁は h1 の後の最初の h2 の直前。
             並びは 要点（summary）→ 追記（update）。
  途中（mid）: h1 の後の最初の h2 の直前（mid-cta）。上の区画と同じ所になる頁では、上の区画の後ろに並ぶ。
  末尾（end）: 著者の箱（<div class="author-box">）の直前。並びは よくある質問（faq）→ 役割分け（role）。
"""
import glob
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "scripts", "data")
LAND = {"land-buyback", "land-lease", "land-value", "land-zoning"}   # 土地の持ち主向けの4本（O16-5・導線を入れない）
ORDER = {"summary": 0, "update": 1, "mid-cta": 9, "faq": 20, "role": 21}
BLOCK_RE = re.compile(r"<!-- scix-([a-z][a-z0-9-]*):begin -->.*?<!-- scix-\1:end -->\n?", re.S)


def column_files():
    return sorted(glob.glob(os.path.join(ROOT, "column-*.html"))) + sorted(glob.glob(os.path.join(ROOT, "en", "column-*.html"))) \
        + sorted(glob.glob(os.path.join(ROOT, "zh-column-*.html")))


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def lang_of(relpath):
    return "en" if relpath.startswith("en/") else ("zh" if relpath.startswith("zh-") else "ja")


def slug_of(relpath):
    return re.sub(r"^(?:en/column-|zh-column-|column-)", "", relpath)[:-5]


def url_of(relpath):
    return "/" + relpath[:-5]


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        import json
        return json.load(fh)


def esc(t):
    return html.escape(t, quote=False)


def mark(name):
    return f"<!-- scix-{name}:begin -->", f"<!-- scix-{name}:end -->"


def strip(s, name):
    b, e = mark(name)
    return re.sub(re.escape(b) + r".*?" + re.escape(e) + r"\n?", "", s, flags=re.S)


def h1_end(s):
    m = re.search(r"</h1>", s)
    return m.end() if m else 0


def first_h2(s):
    m = re.search(r"<h2\b", s[h1_end(s):])
    return h1_end(s) + m.start() if m else None


def top_anchor(s):
    m = re.search(r'<div class="article-body"[^>]*>\n?', s)
    if m and m.start() > h1_end(s) - 1:
        return m.end()
    return first_h2(s)


def end_anchor(s):
    m = re.search(r'<div class="author-box"', s)
    return m.start() if m else None


def _run(s, pos):
    """pos を含む、目印つきの区画の並び（空白だけを挟んで続く物）を返す: [(名, 始, 終)]。"""
    run = []
    # 前へ
    p = pos
    while True:
        t = s[:p].rstrip()
        m = re.search(r"<!-- scix-([a-z][a-z0-9-]*):end -->$", t)
        if not m or m.group(1) not in ORDER:
            break
        b = t.rfind(f"<!-- scix-{m.group(1)}:begin -->")
        if b < 0:
            break
        run.insert(0, (m.group(1), b, len(t)))
        p = b
    # 後ろへ
    p = pos
    while True:
        t = s[p:]
        lead = len(t) - len(t.lstrip())
        m = re.match(r"<!-- scix-([a-z][a-z0-9-]*):begin -->", t.lstrip())
        if not m or m.group(1) not in ORDER:
            break
        e = s.find(f"<!-- scix-{m.group(1)}:end -->", p)
        if e < 0:
            break
        e += len(f"<!-- scix-{m.group(1)}:end -->")
        run.append((m.group(1), p + lead, e))
        p = e
    return run


def place(s, name, block, pos):
    """自分の区画は消してある前提で、pos の位置の区画の並びの中に、決まった順で block を差す。"""
    run = _run(s, pos)
    me = ORDER[name]
    at = pos
    before = [r for r in run if ORDER[r[0]] < me]
    after = [r for r in run if ORDER[r[0]] > me]
    if before:
        at = max(r[2] for r in before)
        if at < len(s) and s[at] == "\n":   # 区画の終わりの改行1つだけ（その後ろの空行は元の頁の物）
            at += 1
    elif after:
        at = min(r[1] for r in after)
    if not block.endswith("\n"):
        block += "\n"
    return s[:at] + block + s[at:]


def wrap(name, inner):
    b, e = mark(name)
    return b + "\n" + inner.rstrip("\n") + "\n" + e + "\n"


def run_all(fn, check, files=None):
    """fn(rel, s) -> 新しい s。--check ならずれだけ数える。"""
    bad = 0
    for p in (files or column_files()):
        r = rel(p)
        s = open(p, encoding="utf-8").read()
        out = fn(r, s)
        if out != s:
            if check:
                print("ずれ:", r)
                bad = 1
            else:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(out)
    return bad
