#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projects.json の集計値を HTML のマーカーへ静的に焼き込む。

なぜJSで描かないか: サイトへの流入のうち AI Assistant 経由はCVRが最も高く、
その経路はJavaScriptを実行しない。fetch で件数を入れると、その読み手には
H1が「販売中の案件、件。」と読まれてしまう。だから毎朝の同期でHTMLに直接書く。

マーカーの形:  <!--S:count-->127<!--/S:count-->
中身だけを置き換えるので、HTMLの構造には触れない。

使い方:
    python3 scripts/inject_stats.py            # 書き換えて差分を報告
    python3 scripts/inject_stats.py --check    # 書き換えずに、ずれているかだけ見る
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["index.html", "projects.html"]


def _esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render_list(ps, generated_at):
    """/projects 用の静的一覧。JSが動かない読み手（検索エンジンの一次クロール・AI検索）が
    127件の中身を読めるようにする。JSが動けばカードUIに置き換わる。
    載せるのは projects.json の公開項目だけ。並びはJSの既定と同じ「連系が早い順・未定は最後」。"""
    import datetime
    today_ym = datetime.date.today().strftime("%Y-%m")

    def cod_view(p):
        ym = p.get("codYm")
        if ym and ym >= today_ym:
            return f"連系の見込み {ym[:4]}年{int(ym[5:7])}月"
        if ym or p.get("cod"):
            return "連系の見込み 要確認"
        return "連系の見込み 未定"

    def key(p):
        ym = p.get("codYm")
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return ((ym if ym and ym >= today_ym else "9999-99"), -num)

    from collections import Counter
    volt = Counter(p.get("voltage") for p in ps if p.get("voltage"))
    area = Counter(p.get("area") for p in ps if p.get("area"))
    prefs = len({p.get("pref") for p in ps if p.get("pref")})
    area_txt = "・".join(f"{a}{n}" for a, n in area.most_common())
    lines = [
        f'<h2 class="pj-static-h">販売中の案件 {len(ps)}件（{_esc(generated_at)} 更新）</h2>',
        f'<p class="pj-static-sum">高圧 {volt.get("高圧", 0)}件・特別高圧 {volt.get("特別高圧", 0)}件 ／ '
        f'{prefs}都道府県 ／ 管内: {_esc(area_txt)}</p>',
        '<ul class="pj-static">',
    ]
    for p in sorted(ps, key=key):
        mw = p.get("mw"); mwh = p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        parts = [
            f"{_esc(p.get('pref') or '所在県 確認中')}（{_esc(p.get('area') or '—')}管内）",
            _esc(p.get("voltage") or "—"), size, cod_view(p),
            _esc(p.get("status") or "—"), _esc(p.get("scheme") or "取得の形 確認中"),
        ]
        pid = _esc(p.get("id") or "")
        lines.append(f'<li id="p-{pid}"><b>{pid}</b>　' + "｜".join(parts) + "</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def compute(projects_json):
    with open(projects_json, encoding="utf-8") as f:
        data = json.load(f)
    ps = data.get("projects", [])
    mw_total = sum(p["mw"] for p in ps if isinstance(p.get("mw"), (int, float)))
    mws = [p["mw"] for p in ps if isinstance(p.get("mw"), (int, float))]
    return {
        "list": render_list(ps, data.get("generatedAt", "")),
        "count": f"{len(ps):,}",
        "mw": f"{round(mw_total):,}",
        "prefs": str(len({p.get("pref") for p in ps if p.get("pref")})),
        "areas": str(len({p.get("area") for p in ps if p.get("area")})),
        "shv": str(sum(1 for p in ps if p.get("voltage") == "特別高圧")),
        "maxmw": f"{round(max(mws)) if mws else 0:,}",
        "date": data.get("generatedAt", ""),
    }


def main():
    check = "--check" in sys.argv
    stats = compute(os.path.join(ROOT, "projects.json"))
    changed, stale = 0, []

    for name in TARGETS:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        out = src
        for key, value in stats.items():
            pattern = re.compile(
                r"(<!--S:" + key + r"-->)(.*?)(<!--/S:" + key + r"-->)", re.S)
            def repl(m, v=value, k=key, n=name):
                if m.group(2) != v:
                    stale.append(f"{n} {k}: {m.group(2)} → {v}")
                return m.group(1) + v + m.group(3)
            out = pattern.sub(repl, out)
        if out != src:
            changed += 1
            if not check:
                open(path, "w", encoding="utf-8").write(out)

    for line in stale:
        print("  " + (line if not line.split(":")[1].strip().startswith("list") else line.split("→")[0] + "→ (一覧を再生成)"))
    if check:
        print(f"[check] 要更新 {changed} ファイル")
        return 1 if changed else 0
    print(f"[ok] {changed} ファイルを更新（件数 {stats['count']}・{stats['mw']}MW・"
          f"{stats['prefs']}都道府県・特高{stats['shv']}件・{stats['date']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
