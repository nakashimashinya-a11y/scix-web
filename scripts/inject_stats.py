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


NEW_DAYS = 14   # 「新着」と呼ぶ日数。projects.html の JS（NEW_DAYS）と同じ値にする

# 連系までの月数の言い方。起点が回答書から取れているものだけ起点を言う。projects.html の JS（LEAD_TEXT）と同じ文言にする。
LEAD_TEXT = {
    "payment": "工事費負担金の入金から約{n}か月",
    "apply": "接続契約の申込みから約{n}か月",
    "contract": "ご契約から約{n}か月",
    "unspecified": "連系工事に約{n}か月",
}


def cod_text(p, today_ym):
    """連系の見込みの表示。projects.html の codView() と同じ規則・同じ文言にする（片方だけ直すと、
    JS を実行しない読み手＝AI検索と、画面で見る読み手とで表示が割れる）。
      連系済み・稼働中 ／ 2027年6月ごろ ／ 2027年6月ごろ（工事費負担金の入金から約8か月）／ 工事費負担金の入金から約12か月 ／ 時期を確認中
    年月が過去になっていたら出さない（同期が止まった日の保険。ふだんは生成側が落としている）。"""
    if p.get("live"):
        return "連系済み・稼働中"
    ym = p.get("codYm")
    ym = ym if (ym and ym >= today_ym) else None
    n = p.get("leadMonths")
    lead = LEAD_TEXT.get(p.get("leadBasis") or "unspecified", LEAD_TEXT["unspecified"]).format(n=n) if n else ""
    if ym:
        return f"{ym[:4]}年{int(ym[5:7])}月ごろ" + (f"（{lead}）" if lead else "")
    return lead or "時期を確認中"


def cod_sort_key(p, today_ym):
    """連系が早い順。連系済み → 年月の早い順 → 月数の短い順 → 確認中。"""
    if p.get("live"):
        return "0000-00"
    ym = p.get("codYm")
    if ym and ym >= today_ym:
        return ym
    n = p.get("leadMonths")
    return ("8000-%03d" % n) if n else "9999-99"


def is_new(p, today):
    import datetime
    fs = p.get("firstSeen")
    if not fs:
        return False
    try:
        return (today - datetime.date.fromisoformat(fs)).days <= NEW_DAYS
    except ValueError:
        return False


def render_list(ps, generated_at):
    """/projects 用の静的一覧。JSが動かない読み手（検索エンジンの一次クロール・AI検索）が
    全件の中身を読めるようにする。JSが動けばカードUIに置き換わる。
    載せるのは projects.json の公開項目だけ。並びはJSの既定と同じ「連系が早い順・確認中は最後」。"""
    import datetime
    today = datetime.date.today()
    today_ym = today.strftime("%Y-%m")

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)

    from collections import Counter
    volt = Counter(p.get("voltage") for p in ps if p.get("voltage"))
    area = Counter(p.get("area") for p in ps if p.get("area"))
    prefs = len({p.get("pref") for p in ps if p.get("pref")})
    area_txt = "・".join(f"{a}{n}" for a, n in area.most_common())
    n_new = sum(1 for p in ps if is_new(p, today))
    lines = [
        f'<h2 class="pj-static-h">販売中の案件 {len(ps)}件（{_esc(generated_at)} 更新）</h2>',
        f'<p class="pj-static-sum">高圧 {volt.get("高圧", 0)}件・特別高圧 {volt.get("特別高圧", 0)}件 ／ '
        f'{prefs}都道府県 ／ 管内: {_esc(area_txt)}'
        + (f' ／ この{NEW_DAYS}日の新着 {n_new}件' if n_new else '') + '</p>',
        '<ul class="pj-static">',
    ]
    for p in sorted(ps, key=key):
        mw = p.get("mw"); mwh = p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        cod = cod_text(p, today_ym)
        parts = [
            f"{_esc(p.get('pref') or '所在県 確認中')}（{_esc(p.get('area') or '—')}管内）",
            _esc(p.get("voltage") or "—"), size,
            _esc(cod if p.get("live") else "連系の見込み " + cod),
        ]
        if not p.get("live"):          # 連系済みは上の欄で言っているので、進み具合の「連系済」を重ねない
            parts.append(_esc(p.get("status") or "—"))
        parts.append(_esc(p.get("scheme") or "取得の形 確認中"))
        if is_new(p, today):
            parts.append(f"新着（{_esc(p['firstSeen'])} 掲載）")
        pid = _esc(p.get("id") or "")
        lines.append(f'<li id="p-{pid}"><b>{pid}</b>　' + "｜".join(parts) + "</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def render_new_line(ps):
    """トップに出す1行。直近の新着があれば件数と ID、無ければ空（行ごと消える）。"""
    import datetime
    today = datetime.date.today()
    fresh = sorted((p for p in ps if is_new(p, today)), key=lambda p: p.get("firstSeen") or "", reverse=True)
    if not fresh:
        return ""
    ids = "・".join(_esc(p.get("id") or "") for p in fresh[:4]) + (" ほか" if len(fresh) > 4 else "")
    return (f'<br><a target="_top" href="/projects?sort=new" style="color:inherit">'
            f'この{NEW_DAYS}日の新着 {len(fresh)}件（{ids}）</a>')


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
        "pjnew": render_new_line(ps),
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
                    stale.append(f"{n} {k}: {m.group(2)[:60]} → {v[:60]}")
                return m.group(1) + v + m.group(3)
            out = pattern.sub(repl, out)
        if out != src:
            changed += 1
            if not check:
                open(path, "w", encoding="utf-8").write(out)

    for line in stale:
        head = line.split(":")[0]
        print("  " + (head + ": (再生成)" if head.endswith((" list", " pjnew")) else line))
    if check:
        print(f"[check] 要更新 {changed} ファイル")
        return 1 if changed else 0
    print(f"[ok] {changed} ファイルを更新（件数 {stats['count']}・{stats['mw']}MW・"
          f"{stats['prefs']}都道府県・特高{stats['shv']}件・{stats['date']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
