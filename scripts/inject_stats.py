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
TARGETS = ["index.html", "en/index.html", "zh.html", "company.html", "en/company.html", "zh-company.html", "projects.html"]
# トップ3頁の言葉（<!--S:cards-->・<!--S:count-->・<!--S:date--> の言葉）。projects.html は日本語。
# 会社案内（company.html・en/company.html・zh-company.html）は冒頭の札の <!--S:count-->・<!--S:prefs--> だけを焼く
TARGET_LANG = {"index.html": "ja", "en/index.html": "en", "zh.html": "zh", "company.html": "ja", "en/company.html": "en", "zh-company.html": "zh", "projects.html": "ja"}


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


DR2_REGISTER = "https://dealroom.scix.co.jp/register"
DR2_CATALOG = "https://dealroom.scix.co.jp/catalog"   # 案件ごとの公開の頁は {DR2_CATALOG}/<id>（マーケットの sitemap に載る・売れたら 410）。
# 行のリンクは公開の頁へ（2026-11-21 中島「SEO対策…やって公開」）。前は一覧の #p-<id> へ nofollow で飛ばしていた＝検索エンジンが案件の頁を辿れなかった。
# 出所の印 ?src= は header.js（7a）が押す直前に足す（静的な href は印なし＝検索エンジンが読む住所を1つにする）。
BAND_EVERY = 10   # 一覧の何行ごとに蓄電所マーケットの帯を挟むか。projects.html の JS（BAND_EVERY）と同じ値にする


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
    return (f'<tr class="pj-band"><td colspan="{cols}"><span>価格と資料は蓄電所マーケットで見られます（無料登録・登録画面で秘密保持の誓約に同意）</span>'
            f'<a target="_top" rel="nofollow" href="{DR2_REGISTER}" class="pj-band-btn" '
            f"onclick=\"window.gtag&&gtag('event','dr2_promo_click',{{target:'band'}})\">無料登録して価格と資料を見る →</a></td></tr>")


def render_list(ps, generated_at):
    """/projects の一覧（絞り込み・表）。静的に焼くので、JS を実行しない読み手（検索エンジンの一次クロール・
    AI検索）も全件の中身を読める。JS は絞り込みと並べ替えだけを受け持つ（行の見た目は変えない）。
    載せるのは projects.json の公開項目だけ（価格・住所・売主は元から無い）。
    並びの既定は「連系が早い順・確認中は最後」。右端の 🔒 の列は蓄電所マーケット（その案件の頁）への入口。"""
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
        + _select("fScheme", "買い方", [(v, v) for v in uniq(p.get("scheme") for p in ps)])
        + _select("fCod", "連系の見込み", [(k, t) for k, t in COD_LABELS if k in buckets])
        + '<label class="pj-f"><span>並び順</span><select id="sortSel">'
          '<option value="cod">連系が早い順</option><option value="mw">規模が大きい順</option>'
          '<option value="new">新着順</option></select></label></div>')
    count_line = (f'<div class="count-line" id="countLine">全 {len(ps)} 件'
                  f'　｜　{_esc(generated_at)} 更新' + (f'　｜　この{NEW_DAYS}日の新着 {n_new} 件' if n_new else '') + '</div>')
    head = ('<thead><tr><th>案件</th><th>所在地</th><th>電圧</th><th>規模</th><th>連系の見込み</th>'
            '<th>電力の手続き</th><th>買い方</th><th class="c-lock">🔒 価格・所在地・資料</th></tr></thead>')
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
            f'<td data-l="電力の手続き">{_esc(p.get("status") or "—")}</td>'
            f'<td data-l="買い方">{_esc(p.get("scheme") or "確認中")}</td>'
            f'<td class="c-lock" data-l="🔒 価格・所在地・資料"><a class="pj-lock" target="_top" href="{DR2_CATALOG}/{pid}" '
            f"onclick=\"window.gtag&&gtag('event','dr2_promo_click',{{target:'row'}})\">価格と資料を見る</a></td></tr>")
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
    return (f'<a target="_top" href="/projects?sort=new" style="color:inherit">'
            f'この{NEW_DAYS}日の新着 {len(fresh)}件（{ids}）</a>')


# ---------------------------------------------------------------- トップの匿名の案件カード（<!--S:cards-->）
# トップ（日英中）の最初の節に、projects.json（公開項目だけ）から焼いた匿名の行を12件置く。画面（/site-cards.js）が蓄電所マーケットの
# ログイン前のカードを読めたときだけ、同じ場所を写真つきのカードに差し替える。読めない（マーケット停止・巡回・遅い）ときは、この行が残る
# ＝上の半分が空かず、検索に見える本文（売り案件の行）も残る。案件名・市区町村・写真・価格は projects.json に無いので、ここにも出ない。
# 行のリンクはマーケットの案件ごとの公開の頁（日本語 /catalog/<id>・英語と中国語は /en/catalog/<id>）。出所の印は header.js が押す直前に足す。
CARDS_N = 12
MARKET_ORIGIN = "https://dealroom.scix.co.jp"
CARD_ART = {"高圧": ("hv", "/img/market/deals.svg"), "特別高圧": ("ehv", "/img/market/how.svg"), "低圧": ("lv", "/img/market/wants.svg")}
# 電力の手続きの段（projects.json の status の3値）→ 帯の長さ（%）。マーケットの8段のうち、接続検討の回答・工事費負担金・完工の位置
STATUS_PCT = {"接続検討回答済": 13, "負担金確定": 75, "連系済": 88}
CARD_TEXT = {
    "ja": {"vol": {"高圧": "高圧", "特別高圧": "特別高圧", "低圧": "低圧"}, "pick": "新着", "none": "所在県 確認中",
           "name": lambda pref, v, mw: f"{pref}の{v}案件", "loc": lambda pref, area: f"{pref}（{area}管内）" if area else pref,
           "scheme": {"完成渡し": "完成渡し", "権利譲渡": "権利渡し", "権利渡し": "権利渡し"},
           "out": "出力", "cap": "容量", "cod": "連系の見込み", "now": "電力の手続き",
           "status": {"接続検討回答済": "接続検討 回答あり", "負担金確定": "負担金 確定", "連系済": "連系済み"}},
    "en": {"vol": {"高圧": "High voltage", "特別高圧": "Extra-high voltage", "低圧": "Low voltage"}, "pick": "New", "none": "Prefecture to be confirmed",
           "name": lambda pref, v, mw: f"{v} project in {pref}", "loc": lambda pref, area: f"{pref} ({area} area)" if area else pref,
           "scheme": {"完成渡し": "Sold on completion", "権利譲渡": "Rights transfer", "権利渡し": "Rights transfer"},
           "out": "Output", "cap": "Capacity", "cod": "Grid connection", "now": "Grid procedure",
           "status": {"接続検討回答済": "Connection study answered", "負担金確定": "Grid cost confirmed", "連系済": "Grid-connected"}},
    "zh": {"vol": {"高圧": "高压", "特別高圧": "特别高压", "低圧": "低压"}, "pick": "新上架", "none": "所在县待确认",
           "name": lambda pref, v, mw: f"{pref}的{v}项目", "loc": lambda pref, area: f"{pref}（{area}区域）" if area else pref,
           "scheme": {"完成渡し": "竣工后转让", "権利譲渡": "权利转让", "権利渡し": "权利转让"},
           "out": "输出功率", "cap": "容量", "cod": "并网预期", "now": "电力手续",
           "status": {"接続検討回答済": "已取得接入系统研究答复", "負担金確定": "并网工程费已确定", "連系済": "已并网"}},
}


# 中国語のカードの県名・管内名は、日本の字（県・東・島…）を簡体字に替える（熊本県→熊本县・関西→关西）。名簿の値は日本語のまま
ZH_PLACE = str.maketrans({"県": "县", "東": "东", "島": "岛", "岡": "冈", "賀": "贺", "児": "儿", "縄": "绳", "沖": "冲",
                          "鳥": "鸟", "愛": "爱", "徳": "德", "広": "广", "馬": "马", "潟": "泻", "長": "长", "庫": "库",
                          "宮": "宫", "葉": "叶", "関": "关", "陸": "陆", "栃": "枥"})


def zh_place(s):
    return (s or "").translate(ZH_PLACE)


def card_cod(p, today_ym, lang):
    """カードの「連系の見込み」。ja は cod_text と同じ規則・短い言い方。en は build_market_data.en_cod と同じ規則。"""
    if p.get("live"):
        return {"ja": "連系済み・稼働中", "en": "Grid-connected", "zh": "已并网运行"}[lang]
    ym = p.get("codYm")
    ym = ym if (ym and ym >= today_ym) else None
    n = p.get("leadMonths")
    if ym:
        y, m = ym[:4], int(ym[5:7])
        return {"ja": f"{y}年{m}月ごろ",
                "en": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m - 1]} {y}",
                "zh": f"约{y}年{m}月"}[lang]
    if n:
        return {"ja": f"連系まで約{n}か月", "en": f"About {n} months", "zh": f"约{n}个月"}[lang]
    return {"ja": "時期を確認中", "en": "Under review", "zh": "待确认"}[lang]


def render_cards(ps, lang="ja", today=None):
    """トップの最初の節に置く匿名の案件カード12件（新着順）。使う項目は projects.json の公開項目だけ。"""
    import datetime
    today = today or datetime.date.today()
    today_ym = today.strftime("%Y-%m")
    t = CARD_TEXT[lang]
    if lang != "ja":
        import build_market_data as bmd   # 英語の県名・管内名（同じ表を2か所に持たない）。ここで読む＝import の輪を作らない
        en_pref, en_area = bmd.EN_PREF, bmd.EN_AREA
    ps = [p for p in ps if p.get("id")]
    ps = sorted(ps, key=lambda p: (p.get("firstSeen") or "", int("".join(ch for ch in p["id"] if ch.isdigit()) or 0)), reverse=True)[:CARDS_N]
    out = []
    for i, p in enumerate(ps):
        pid = _esc(p["id"])
        volt = p.get("voltage") or ""
        vk, art = CARD_ART.get(volt, ("hv", CARD_ART["高圧"][1]))
        pref_ja = p.get("pref") or ""
        area_ja = p.get("area") or ""
        pref = (en_pref.get(pref_ja, pref_ja) if lang == "en" else zh_place(pref_ja) if lang == "zh" else pref_ja) or t["none"]
        area = en_area.get(area_ja, area_ja) if lang == "en" else zh_place(area_ja) if lang == "zh" else area_ja
        vname = t["vol"].get(volt, volt)
        mw, mwh = p.get("mw"), p.get("mwh")
        cells = []
        if isinstance(mw, (int, float)):
            cells.append(f'<div><small>{t["out"]}</small><b>{mw:g}<i class="u"> MW</i></b></div>')
        if isinstance(mwh, (int, float)):
            cells.append(f'<div><small>{t["cap"]}</small><b>{mwh:g}<i class="u"> MWh</i></b></div>')
        cells.append(f'<div><small>{t["cod"]}</small><b>{_esc(card_cod(p, today_ym, lang))}</b></div>')
        spec = f'<div class="sc-spec" style="--n:{len(cells)}">' + "".join(cells) + "</div>"
        st = p.get("status") or ""
        gs = (f'<div class="sc-gs"><div class="bar"><i style="width:{STATUS_PCT.get(st, 0)}%"></i></div>'
              f'<span class="now">{t["now"]}: <b>{_esc(t["status"].get(st, st) or "—")}</b></span></div>')
        scheme = t["scheme"].get(p.get("scheme") or "", "")
        tags = (f'<span class="vtag {vk}">{_esc(vname)}</span>' if vname else "") + \
               (f'<span class="atag">{_esc(scheme)}</span>' if scheme else "") + f'<span class="atag sc-idtag">{pid}</span>'
        new = f'<div class="sc-tl"><span class="sc-new">{t["pick"]}</span></div>' if is_new(p, today) else ""
        prefix = "/en/catalog/" if lang != "ja" else "/catalog/"
        href = MARKET_ORIGIN + prefix + p["id"]
        name = t["name"](pref, vname, mw)
        lazy = "" if i < 4 else ' loading="lazy"'   # 最初の4枚だけ先に読む（LCP の候補）
        out.append(
            f'<article class="sc" data-id="{pid}"><div class="sc-img" data-v="{vk}">'
            f'<img class="art" src="{art}" width="640" height="360" alt=""{lazy} decoding="async">{new}</div>'
            f'<div class="sc-body"><h3 class="sc-name"><a class="sc-lk" target="_top" href="{_esc(href)}" data-placement="card">{_esc(name)}</a></h3>'
            f'<div class="sc-loc">{_esc(t["loc"](pref, area))}</div><div class="sc-tags">{tags}</div>{spec}{gs}</div></article>')
    return "\n" + "\n".join(out) + "\n"


def compute(projects_json):
    with open(projects_json, encoding="utf-8") as f:
        data = json.load(f)
    ps = data.get("projects", [])
    mw_total = sum(p["mw"] for p in ps if isinstance(p.get("mw"), (int, float)))
    mws = [p["mw"] for p in ps if isinstance(p.get("mw"), (int, float))]
    return {
        "_ps": ps,
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
    ps = stats.pop("_ps")
    changed, stale = 0, []

    for name in TARGETS:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        out = src
        # 言葉ごとの中身（トップ3頁のカード）。印が無い頁は何も書かない
        per_page = dict(stats)
        if "<!--S:cards-->" in src:
            per_page["cards"] = render_cards(ps, TARGET_LANG.get(name, "ja"))
        for key, value in per_page.items():
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
        print("  " + (head + ": (再生成)" if head.endswith((" list", " pjnew", " cards")) else line))
    if check:
        print(f"[check] 要更新 {changed} ファイル")
        return 1 if changed else 0
    print(f"[ok] {changed} ファイルを更新（件数 {stats['count']}・{stats['mw']}MW・"
          f"{stats['prefs']}都道府県・特高{stats['shv']}件・{stats['date']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
