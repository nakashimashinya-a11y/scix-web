#!/usr/bin/env python3
"""市場ノートの古い住所（/report…・/en/report…）が、vercel.json の転送で新しい住所（/research…）へ届き、
その先にファイルがあることを手元で確かめる試験（2026-11-25・住所を /report から /research へ移した回）。外へは出ない。

    python3 scripts/selftest_report_redirects.py      # 全部通れば 0、1つでも落ちれば 1

見ること:
  ・古い住所 → 転送は1回だけ・恒久（permanent＝308）・行き先は期待どおり
  ・行き先の住所は cleanUrls の解決（x・x.html・x/index.html）でリポジトリのファイルに当たる
  ・新しい住所（/research…）にはどの転送も当たらない（輪にならない・入口の /research に効かない）
  ・つなぎの rewrites（/research/:path+ → /report/:path+）が残っていない
Vercel の source の書き方のうち、ここで使う形（固定の住所と、末尾の :name* / :name+）だけを読む。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
FAIL = []


def ok(cond, msg):
    print(("OK  " if cond else "NG  ") + msg)
    if not cond:
        FAIL.append(msg)


def to_rx(source):
    """'/report/:path*' → 正規表現と名前。:x* は0段以上、:x+ は1段以上、:x は1段。ほかの書き方は使っていない前提。"""
    names, out, i = [], "", 0
    for m in re.finditer(r"/:(\w+)([*+]?)", source):
        out += re.escape(source[i:m.start()])
        names.append(m.group(1))
        out += {"*": r"(?:/(.*))?", "+": r"/(.+)", "": r"/([^/]+)"}[m.group(2)]
        i = m.end()
    out += re.escape(source[i:])
    return re.compile("^" + out + "$"), names


def redirect(path):
    for r in CONF.get("redirects", []):
        if "has" in r or "(" in r["source"]:
            continue
        rx, names = to_rx(r["source"])
        m = rx.match(path)
        if not m:
            continue
        dest = r["destination"]
        for n, v in zip(names, m.groups()):
            dest = dest.replace("/:" + n + "*", ("/" + v) if v else "").replace("/:" + n + "+", "/" + (v or "")).replace(":" + n, v or "")
        return dest, bool(r.get("permanent"))
    return None, None


def has_file(path):
    rel = path.lstrip("/")
    for c in (rel, rel + ".html", os.path.join(rel, "index.html")):
        f = os.path.join(ROOT, c)
        if c and os.path.isfile(f):
            return True
    return False


months = sorted(d for d in os.listdir(os.path.join(ROOT, "research")) if re.match(r"^\d{4}-\d{2}$", d))
en_months = sorted(d for d in os.listdir(os.path.join(ROOT, "en", "research")) if re.match(r"^\d{4}-\d{2}$", d))
pairs = [("/report", "/research"), ("/report/flash", "/research/flash"), ("/report/data", "/research/data"),
         ("/report/area/tokyo", "/research/area/tokyo"), ("/report/area/kyushu", "/research/area/kyushu"),
         ("/report/latest.json", "/research/latest.json"), ("/report/flash/latest.json", "/research/flash/latest.json"),
         ("/report/flash/jepx-daily.csv", "/research/flash/jepx-daily.csv"),
         ("/report/data/jepx-spot-monthly.csv", "/research/data/jepx-spot-monthly.csv"),
         ("/en/report", "/en/research"), ("/en/report/flash", "/en/research/flash"), ("/en/report/data", "/en/research/data"),
         ("/en/report/flash/jepx-daily.csv", "/en/research/flash/jepx-daily.csv")]
for k in months:
    pairs.append((f"/report/{k}", f"/research/{k}"))
    pairs.append((f"/report/{k}/scix-bess-monthly-{k}.pdf", f"/research/{k}/scix-bess-monthly-{k}.pdf"))
    imgs = sorted(f for f in os.listdir(os.path.join(ROOT, "research", k)) if f.endswith(".png"))
    if imgs:
        pairs.append((f"/report/{k}/{imgs[0]}", f"/research/{k}/{imgs[0]}"))
for k in en_months:
    pairs.append((f"/en/report/{k}", f"/en/research/{k}"))
    pairs.append((f"/en/report/{k}/scix-bess-monthly-{k}-en.pdf", f"/en/research/{k}/scix-bess-monthly-{k}-en.pdf"))
flash_svg = sorted(f for f in os.listdir(os.path.join(ROOT, "research", "flash")) if f.endswith(".svg"))
if flash_svg:
    pairs.append((f"/report/flash/{flash_svg[0]}", f"/research/flash/{flash_svg[0]}"))

for old, want in pairs:
    dest, perm = redirect(old)
    ok(dest == want and perm, f"{old} → {dest} （期待 {want}・恒久={perm}）")
    ok(has_file(want), f"{want} にファイルがある")
    again, _ = redirect(want)
    ok(again is None, f"{want} にはもう転送が当たらない（{again}）")

for p in ["/research", "/en/research", "/research/flash", "/research/2026-11"]:
    ok(redirect(p)[0] is None and has_file(p), f"{p} は転送なしで開く")
ok(not any("research" in r["source"] and "report" in r["destination"] for r in CONF.get("rewrites", [])), "つなぎの rewrites（/research → /report）が残っていない")
ok(not os.path.exists(os.path.join(ROOT, "report")) and not os.path.exists(os.path.join(ROOT, "en", "report")), "report/・en/report/ のフォルダが残っていない")
ok(not os.path.exists(os.path.join(ROOT, "research.html")), "手書きの research.html が残っていない（/research は research/index.html）")

print(f"\n{len(pairs)} 組・落ちた {len(FAIL)}")
sys.exit(1 if FAIL else 0)
