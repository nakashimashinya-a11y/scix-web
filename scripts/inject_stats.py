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


DR2_REGISTER = "https://scix-dealroom2.pages.dev/register.html"
BAND_EVERY = 10   # 一覧の何行ごとに DealRoom の帯を挟むか。projects.html の JS（BAND_EVERY）と同じ値にする


def cod_bucket(p, today_ym):
    """絞り込みの「連系」の区分。キー（live/thisfy/nextfy/later/lead/tbd）はトップやコラムのリンクと
    GA4 のイベント値で使っているので変えない。年度は4月始まり。"""
    if p.get("live"):
        return "live"
    ym = p.get("codYm")
    if not (ym and ym >= today_ym):
        return "lead" if p.get("leadMonths") else "tbd"
    y, m = int(ym[:4]), int(ym[5:7])
    fy = y if m >= 4 else y - 1
    today_fy = int(today_ym[:4]) if int(today_ym[5:7]) >= 4 else int(today_ym[:4]) - 1
    if fy <= today_fy:
        return "thisfy"
    return "nextfy" if fy == today_fy + 1 else "later"


COD_LABELS = [("live", "連系済み"), ("thisfy", "今年度内"), ("nextfy", "来年度"),
              ("later", "再来年度以降"), ("lead", "月数でご案内"), ("tbd", "確認中")]


def _select(sid, label, options):
    opts = "".join(f'<option value="{_esc(v)}">{_esc(t)}</option>' for v, t in options)
    return (f'<label class="pj-f"><span>{label}</span><select id="{sid}">'
            f'<option value="all">すべて</option>{opts}</select></label>')


def band_row(cols):
    return (f'<tr class="pj-band"><td colspan="{cols}"><span>価格・所在地・資料は DealRoom で見られます（無料登録・誓約書）</span>'
            f'<a target="_top" rel="nofollow" href="{DR2_REGISTER}" class="pj-band-btn" '
            f"onclick=\"window.gtag&&gtag('event','dr2_promo_click',{{target:'band'}})\">DealRoom に登録 →</a></td></tr>")


def render_list(ps, generated_at):
    """/projects の一覧（絞り込み・表）。静的に焼くので、JS を実行しない読み手（検索エンジンの一次クロール・
    AI検索）も全件の中身を読める。JS は絞り込みと並べ替えだけを受け持つ（行の見た目は変えない）。
    載せるのは projects.json の公開項目だけ（価格・住所・売主は元から無い）。
    並びの既定は「連系が早い順・確認中は最後」。右端の 🔒 の列は DealRoom（登録）への入口。"""
    import datetime
    today = datetime.date.today()
    today_ym = today.strftime("%Y-%m")

    def key(p):
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        return (cod_sort_key(p, today_ym), -num)

    n_new = sum(1 for p in ps if is_new(p, today))
    uniq = lambda vals: [v for v in dict.fromkeys(vals) if v]
    buckets = {cod_bucket(p, today_ym) for p in ps}
    filters = (
        '<div class="pj-filters">'
        + _select("fArea", "管内", [(a, a) for a in uniq(p.get("area") for p in ps)])
        + _select("fVoltage", "電圧", [(v, v) for v in uniq(p.get("voltage") for p in ps)])
        + _select("fScheme", "取得の形", [(v, v) for v in uniq(p.get("scheme") for p in ps)])
        + _select("fCod", "連系の見込み", [(k, t) for k, t in COD_LABELS if k in buckets])
        + '<label class="pj-f"><span>並び順</span><select id="sortSel">'
          '<option value="cod">連系が早い順</option><option value="mw">規模が大きい順</option>'
          '<option value="new">新着順</option></select></label></div>')
    count_line = (f'<div class="count-line" id="countLine">全 {len(ps)} 件'
                  f'　｜　{_esc(generated_at)} 更新' + (f'　｜　この{NEW_DAYS}日の新着 {n_new} 件' if n_new else '') + '</div>')
    head = ('<thead><tr><th>案件</th><th>所在地</th><th>電圧</th><th>規模</th><th>連系の見込み</th>'
            '<th>進み具合</th><th>取得の形</th><th class="c-lock">🔒 価格・所在地・資料</th></tr></thead>')
    rows = []
    for i, p in enumerate(sorted(ps, key=key), 1):
        mw = p.get("mw"); mwh = p.get("mwh")
        size = (f"{mw:g}MW" if isinstance(mw, (int, float)) else "—") + \
               (f"／{mwh:g}MWh" if isinstance(mwh, (int, float)) else "")
        pid = _esc(p.get("id") or "")
        num = int("".join(ch for ch in (p.get("id") or "") if ch.isdigit()) or 0)
        tag = f'<span class="tag-new">新着 {int(p["firstSeen"][5:7])}/{int(p["firstSeen"][8:10])}</span>' if is_new(p, today) else ""
        attrs = (f'data-area="{_esc(p.get("area") or "")}" data-volt="{_esc(p.get("voltage") or "")}" '
                 f'data-scheme="{_esc(p.get("scheme") or "")}" data-cod="{cod_bucket(p, today_ym)}" '
                 f'data-codkey="{cod_sort_key(p, today_ym)}" data-mw="{mw if isinstance(mw, (int, float)) else 0}" '
                 f'data-first="{_esc(p.get("firstSeen") or "")}" data-num="{num}"')
        rows.append(
            f'<tr class="pj-row" id="p-{pid}" {attrs}>'
            f'<td class="c-id" data-l="案件"><label class="pick"><input type="checkbox" data-pick="{pid}" aria-label="{pid} を資料請求に加える"></label><b>{pid}</b>{tag}</td>'
            f'<td data-l="所在地">{_esc(p.get("pref") or "所在県 確認中")}<small>（{_esc(p.get("area") or "—")}管内）</small></td>'
            f'<td data-l="電圧">{_esc(p.get("voltage") or "—")}</td>'
            f'<td data-l="規模">{_esc(size)}</td>'
            f'<td data-l="連系の見込み">{_esc(cod_text(p, today_ym))}</td>'
            f'<td data-l="進み具合">{_esc(p.get("status") or "—")}</td>'
            f'<td data-l="取得の形">{_esc(p.get("scheme") or "確認中")}</td>'
            f'<td class="c-lock" data-l="🔒 価格・所在地・資料"><a class="pj-lock" target="_top" rel="nofollow" href="{DR2_REGISTER}" '
            f"onclick=\"window.gtag&&gtag('event','dr2_promo_click',{{target:'row'}})\">DealRoom で見る</a></td></tr>")
        if i % BAND_EVERY == 0 and i != len(ps):
            rows.append(band_row(8))
    rows.append(band_row(8))
    return (filters + "\n" + count_line + "\n"
            '<table class="pj-table" id="pjTable">' + head + "<tbody>\n" + "\n".join(rows) + "\n</tbody></table>"
            '<p class="state-msg" id="stateMsg" style="display:none">該当する案件はありません。絞り込みを変えてください。</p>')


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
        "hv": str(sum(1 for p in ps if p.get("voltage") == "高圧")),
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
