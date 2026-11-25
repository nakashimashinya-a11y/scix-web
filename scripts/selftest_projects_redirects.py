#!/usr/bin/env python3
"""やめた案件一覧の頁（/projects・/projects-<管内>・/en/projects）が、vercel.json の転送で蓄電所マーケットへ届くことを
手元で確かめる試験（2026-11-25・中島「この画面は古いからもういらないよね」）。外へは出ない。

    python3 scripts/selftest_projects_redirects.py      # 全部通れば 0、1つでも落ちれば 1

見ること:
  ・古い住所 → 転送は1回だけ・恒久（permanent＝308）・行き先は期待どおり（出所の印 src は頁の印 site-projects… と同じ形）
  ・古い住所のファイルがリポジトリに残っていない（転送だけが答える）
  ・ほかの転送の行き先に /projects… が残っていない（転送が2回にならない）
  ・サイトの頁（*.html・sitemap.xml・llms.txt・フィード）に、やめた頁への内側のリンクが残っていない
行き先の頁が本当に開くか（200）は外のサイトなので、ここでは見ない（切り替えの手順の curl で見る）。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
M = "https://dealroom.scix.co.jp"
AREAS = ["hokkaido", "tohoku", "tokyo", "chubu", "hokuriku", "kansai", "chugoku", "shikoku", "kyushu"]
FAIL = []


def ok(cond, msg):
    print(("OK  " if cond else "NG  ") + msg)
    if not cond:
        FAIL.append(msg)


def redirect(path):
    for r in CONF.get("redirects", []):
        if "has" in r or ":" in r["source"] or "(" in r["source"]:
            continue
        if r["source"] == path:
            return r["destination"], bool(r.get("permanent"))
    return None, None


pairs = [("/projects", f"{M}/?src=site-projects"), ("/en/projects", f"{M}/en?src=site-projects-en"),
         ("/overview", f"{M}/?src=site-projects")]
pairs += [(f"/projects-{a}", f"{M}/catalog/area/{a}?src=site-projects-{a}") for a in AREAS]
for old, want in pairs:
    dest, perm = redirect(old)
    ok(dest == want and perm, f"{old} → {dest} （期待 {want}・恒久={perm}）")
    f = old.lstrip("/")
    ok(not os.path.exists(os.path.join(ROOT, f + ".html")) and not os.path.exists(os.path.join(ROOT, f, "index.html")),
       f"{old} のファイルが残っていない")

ok(not any(re.match(r"^/(en/)?projects(-[a-z]+)?$", r["destination"]) for r in CONF.get("redirects", [])),
   "ほかの転送の行き先に /projects… が残っていない")
ok(os.path.exists(os.path.join(ROOT, "projects.json")), "projects.json は残っている（市場データ・マーケットの入口・ほかの台本が読む）")

files = subprocess.run(["git", "-C", ROOT, "ls-files", "*.html", "sitemap.xml", "llms.txt", "feed.xml", "projects-feed.xml", "smartnews.xml"],
                       capture_output=True, text=True).stdout.split()
LINK = re.compile(r"""(?:href|src|<loc>|\]\()=?["']?(?:https://www\.scix\.co\.jp)?/(?:en/)?projects(?:-[a-z]+)?(?:\.html)?(?=["'#?)<\s])""")
left = []
for rel in files:
    s = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
    n = len(LINK.findall(s))
    if n:
        left.append(f"{rel}（{n}）")
ok(not left, "やめた頁への内側のリンクが残っていない" + ("：" + "・".join(left) if left else ""))

print(f"\n{len(pairs)} 組・落ちた {len(FAIL)}")
sys.exit(1 if FAIL else 0)
