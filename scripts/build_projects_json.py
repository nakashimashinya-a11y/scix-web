#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案B: dealroom2 の案件データから、公開サイト scix.co.jp/projects 用の
公開セーフな projects.json を自動生成する（nightly から実行可能）。

source は functions/api/projects.ts と同じ:
  - data/projects-end.json（既存案件）
  - D1 dealroom2_new_projects（D1のみの新規案件）
  - D1 deal_edits（overlay。dealroom2Visible='off' は除外）
を merge/overlay/filter したうえで、**匿名のティーザー項目のみ**に落とす。

出力フィールド（守秘準拠・NDA前=都道府県レベルまで。2026-09-05 判断①で公開可とされた範囲）:
  id / area(管内) / pref(都道府県) / voltage / mw / mwh / status(進捗) / scheme
  cod(連系見込みの年度) / codYm(同・年月) / leadMonths(連系までの月数) / leadBasis(その起点)
  live(連系済み・稼働中) / firstSeen(この一覧に載った日) / updatedAt(公開項目が変わった日)
必ず除外: name・住所(地番)・lat/lng・price・seller・社内memo・**DR2 の自由記述そのもの**
  （運転開始予定や負担金の欄には売主の説明・金額が混じる。出すのは年月・整数・列挙値だけ）

連系の見込みの読み方（2026-09-20 改修）:
  DR2 の connectionDate は「回答日」（接続検討回答書が出た日＝過去の実績日）で、連系予定ではない。
  2026-09 まではこれを連系見込みとして読んでいたため、128件中115件が「要確認／未定」になっていた。
  連系予定は operationStartDate（運転開始予定日）、月数は leadMonthsFromPayment（工事費負担金の入金後）・
  leadMonthsFromApply（接続契約申込みの受付後）・constructionMonths（起点の明示なし）にある。

使い方:
  python3 scripts/build_projects_json.py            # 既定パスで生成し ./projects.json を上書き
  SCIX_DEALROOM2_DIR=/path python3 scripts/build_projects_json.py --out projects.json
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

def _resolve_d2_dir():
    """dealroom2 アプリのディレクトリを決める。

    環境変数 SCIX_DEALROOM2_DIR があればそれを使う。無ければ既知の候補を順に探す。
    ⚠️ 実在しないパスを既定値にして黙って先へ進むと、D1 が引けないまま
    projects-end.json だけの短い一覧を「最新」として書き出してしまう（2026-09 に発覚）。
    見つからなければ None を返し、呼び出し側で止める。
    """
    env = os.environ.get("SCIX_DEALROOM2_DIR")
    if env:
        return env if os.path.isdir(env) else None
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "マイドライブ/9_システム/1AI営業支援/scix/scix-dealroom2"),
        os.path.join(home, "Library/CloudStorage/GoogleDrive-s@scix.co.jp/"
                           "マイドライブ/9_システム/1AI営業支援/scix/scix-dealroom2"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


DEFAULT_D2 = _resolve_d2_dir()
D1_DB = "scix-dealroom-db"

# 公開してよい販売ステータスはこれだけ。売却済み・交渉中・準備中は一覧に出さない。
# （2026-09 まで絞り込みが無く、売却済みの案件が「販売中」として載り続けていた）
PUBLIC_SALES_STATUS = {"販売中"}

# 一般送配電事業者 → 電力管内（都道府県の上位の地域区分）
AREA_MAP = {
    "北海道電力ネットワーク": "北海道",
    "東北電力ネットワーク": "東北",
    "東京電力PG": "東京", "東京電力パワーグリッド": "東京",
    "中部電力PG": "中部", "中部電力パワーグリッド": "中部",
    "北陸電力送配電": "北陸",
    "関西電力送配電": "関西",
    "中国電力ネットワーク": "中国",
    "四国電力送配電": "四国",
    "九州電力送配電": "九州",
    "沖縄電力": "沖縄",
}

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]
# 「京都」「大阪」など県を欠く表記の補正
PREF_ALIASES = {"京都": "京都府", "大阪": "大阪府", "東京": "東京都", "北海道": "北海道"}

# 各都道府県 → 管内（gridOperator が無い案件のフォールバック）
PREF_TO_AREA = {
    "北海道": "北海道",
    "青森県": "東北", "岩手県": "東北", "宮城県": "東北", "秋田県": "東北", "山形県": "東北", "福島県": "東北",
    "茨城県": "東京", "栃木県": "東京", "群馬県": "東京", "埼玉県": "東京", "千葉県": "東京", "東京都": "東京", "神奈川県": "東京", "山梨県": "東京",
    "新潟県": "東北", "長野県": "中部", "静岡県": "中部", "愛知県": "中部", "岐阜県": "中部", "三重県": "中部",
    "富山県": "北陸", "石川県": "北陸", "福井県": "北陸",
    "滋賀県": "関西", "京都府": "関西", "大阪府": "関西", "兵庫県": "関西", "奈良県": "関西", "和歌山県": "関西",
    "鳥取県": "中国", "島根県": "中国", "岡山県": "中国", "広島県": "中国", "山口県": "中国",
    "徳島県": "四国", "香川県": "四国", "愛媛県": "四国", "高知県": "四国",
    "福岡県": "九州", "佐賀県": "九州", "長崎県": "九州", "熊本県": "九州", "大分県": "九州", "宮崎県": "九州", "鹿児島県": "九州",
    "沖縄県": "沖縄",
}

# projects.ts と同じ overlay 対象（公開出力に関係するものだけ）
OVERLAY_STR = ["status", "voltage", "gridOperator", "area", "connectionDate", "saleType",
               "depositStatus", "operationStartDate", "dealroom2Visible", "constructionCostStatus"]
OVERLAY_NUM = ["mw", "capacity", "maxPower",
               "constructionMonths", "leadMonthsFromPayment", "leadMonthsFromApply"]

# projects.json の1件が持つキー（順序もこのとおり）。.github/workflows/projects-freshness.yml の
# allowed と CLAUDE.md の「公開してよい項目」と3か所そろえる。
PUBLIC_KEYS = ["id", "area", "pref", "voltage", "mw", "mwh", "cod", "codYm", "leadMonths", "leadBasis",
               "live", "status", "scheme", "firstSeen", "updatedAt"]
# 掲載日・更新日の持ち回りで「中身が変わったか」を比べる対象（日付そのものは比べない）
CONTENT_KEYS = [k for k in PUBLIC_KEYS if k not in ("firstSeen", "updatedAt")]
SCHEMA = 2   # 1 = 2026-09-20 まで（cod/codYm が回答日由来）。2 = 運転開始予定＋月数＋掲載日


class D1Unavailable(RuntimeError):
    """D1 が引けなかった。部分的な一覧を書き出さずに止めるための例外。"""


def wrangler_json(command):
    """dealroom2 ディレクトリで wrangler d1 を実行し results を返す。

    ⚠️ 失敗を握りつぶさない。D1 が引けないまま続けると、D1 にしか無い案件
    （新規登録分）が丸ごと落ちた一覧を「最新」として公開してしまう。
    """
    # 非対話（launchd・cron）では npx wrangler の OAuth が失効する。
    # SCIX_WRANGLER にトークン自動更新ラッパー（~/.config/scix-cockpit/wr）を渡せるようにする。
    wrangler = os.environ.get("SCIX_WRANGLER")
    argv = ([wrangler] if wrangler else ["npx", "wrangler"]) + [
        "d1", "execute", D1_DB, "--remote", "--json", "--command", command]
    try:
        out = subprocess.run(
            argv, cwd=DEFAULT_D2, capture_output=True, text=True, timeout=180,
        )
    except Exception as e:  # noqa
        raise D1Unavailable(f"wrangler の起動に失敗: {e}")
    if out.returncode != 0:
        tail = (out.stderr or out.stdout or "").strip().splitlines()[-3:]
        raise D1Unavailable(f"wrangler が exit {out.returncode}: {' / '.join(tail)}")
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError as e:
        raise D1Unavailable(f"wrangler の出力が JSON でない: {e}")
    if isinstance(data, list):
        return data[0]["results"]
    if isinstance(data, dict) and "result" in data:
        return data["result"][0]["results"]
    raise D1Unavailable(f"wrangler の出力の形が想定外: {type(data).__name__}")


def extract_pref(address):
    if not address:
        return None
    a = address.strip()
    for p in PREFECTURES:
        if a.startswith(p):
            return p
    m = re.match(r"^(.+?[都道府県])", a)
    if m:
        cand = PREF_ALIASES.get(m.group(1), m.group(1))
        return cand if cand in PREFECTURES else None   # 47都道府県に無い文字列（町名・郵便番号つき）は出さない
    return None


def norm_voltage(v):
    if not v:
        return None
    v = str(v).strip()
    if v in ("特高", "特別高圧", "特高圧"):
        return "特別高圧"
    if v in ("高圧",):
        return "高圧"
    return v


def norm_scheme(s):
    if not s:
        return None
    s = str(s).strip()
    if "完成" in s or "ターンキー" in s:
        return "完成渡し"
    if "権利" in s or "EPC" in s.upper():
        # 「EPCフリー」=買い手が自らEPC選定＝開発段階の権利譲渡に相当
        return "権利譲渡"
    return "権利譲渡"


# 運転開始予定として採ってよいのは「欄の全体が年月（と無害な添え字）だけ」のもの。
# 先頭一致や部分一致で拾うと、「未定（希望日は不可との回答）」のような注記の中の日付を見込みとして出してしまう。
_YM_PATTERNS = [
    re.compile(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?\s*(?:以降|頃|ごろ)?$"),
    re.compile(r"^(\d{4})/(\d{1,2})(?:/\d{1,2})?\s*(?:以降|頃|ごろ)?$"),
    re.compile(r"^(\d{4})年\s*(\d{1,2})月(?:\s*\d{1,2}日)?\s*(?:以降|頃|ごろ|予定|（予定）|\(予定\))?$"),
]
# 連系済みは、欄の全体が決まり文句のときだけ（部分一致だと「太陽光は稼働中」のような文で蓄電池まで稼働中になる）
_LIVE_PATTERNS = [
    re.compile(r"^(?:運転開始済み?|運開済み?|稼働中|連系済み?)$"),
    re.compile(r"^需給調整市場.{0,12}参加.{0,6}稼働実績あり$"),
]
_CONTRACT_MONTHS = re.compile(
    r"^(?:ご?契約後|契約締結後)\s*(?:約)?\s*(\d{1,2})\s*(?:か|ヶ|ケ|カ|ヵ|箇)月\s*(?:程度|以内|前後|ほど)?$")
_LOOSE_YM = re.compile(r"(20\d{2})\s*[-/年]\s*(\d{1,2})")
# 月数が分からない案件で、工事費負担金が支払済と確認できないときに「これより手前の年月は守れない」とみなす月数
MIN_LEAD_MONTHS = {"高圧": 6, "特別高圧": 12}


def parse_ym_strict(value):
    """欄の全体が年月として読めるときだけ (年, 月) を返す。注記つき・範囲・「年内」は None。"""
    if value is None:
        return None
    v = str(value).strip().replace("　", " ")
    for pat in _YM_PATTERNS:
        m = pat.match(v)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            if 2000 <= y <= 2100 and 1 <= mo <= 12:
                return (y, mo)
    return None


def _ym_str(ym):
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else None


def _fy_str(ym):
    if not ym:
        return None
    return f"{ym[0] if ym[1] >= 4 else ym[0] - 1}年度"


def _add_months(ym, n):
    idx = ym[0] * 12 + (ym[1] - 1) + int(n)
    return (idx // 12, idx % 12 + 1)


def _pos_int(v):
    """'12' / 12 / 12.0 → 12。0以下・120超・数でないものは None（D1 の --json は NULL を 'null' と出す）。"""
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 120 else None


def grid_cost_paid(p):
    """工事費負担金の支払状況を内部判定用に3値へ。**公開はしない**（判断①の範囲外）。
    自由記述（「1割入金済み・残額は買主負担」など）は unknown に倒す。"""
    v = str(p.get("constructionCostStatus") or "").strip()
    if v.startswith(("支払済", "支払い済", "入金済")):
        return "paid"
    if v.startswith(("未払", "未納")):
        return "unpaid"
    return "unknown"


def is_live(p):
    """連系済み・稼働中。DR2 に専用の列が無いので、販売ステータスの明示か、運転開始予定欄の全体が決まり文句のときだけ。"""
    if str(p.get("status") or "").strip() in ("連系済", "稼働中", "運転中"):
        return True
    v = str(p.get("operationStartDate") or "").strip()
    return any(pat.match(v) for pat in _LIVE_PATTERNS)


def lead_info(p):
    """連系までの月数と起点。起点が回答書から明示で取れているものを優先する。
      payment     = 工事費負担金の入金後（leadMonthsFromPayment）
      apply       = 接続契約申込みの受付後（leadMonthsFromApply）
      contract    = 契約後（運転開始予定欄が「契約後Nか月」とだけ書かれている案件。cod_info が先に判定する）
      unspecified = constructionMonths。DR2 では起点が混在している＝起点を言い切らない
    """
    n = _pos_int(p.get("leadMonthsFromPayment"))
    if n:
        return n, "payment"
    n = _pos_int(p.get("leadMonthsFromApply"))
    if n:
        return n, "apply"
    n = _pos_int(p.get("constructionMonths"))
    if n:
        return n, "unspecified"
    return None, None


def cod_info(p, today):
    """連系の見込み（年月）と月数を決める。返り値 (codYm文字列|None, leadMonths|None, leadBasis|None, live)。

    年月は「守れる見込み」だけを出す:
      - 元は operationStartDate（運転開始予定日）。connectionDate は回答日なので、運転開始予定が**空のときだけ**、
        未来日なら保険で使う（文章が入っていて読めないときは使わない＝「不可と回答された希望日」を拾わない）
      - 過去の年月は出さない
      - 工事費負担金が支払済と確認できない案件は、今日入金しても間に合わない年月を出さない
        （月数が分かる案件は「今月＋月数」、分からない案件は電圧区分ごとの最短工期 MIN_LEAD_MONTHS で判定）
      - 支払済の案件は時計がもう回っているので、月数は出さない（年月が無ければ確認中）
      - 年月が月数よりずっと先（＋12か月超）なら月数は付けない（入金時期が先という意味で、並べると矛盾して見える）
      - 運転開始予定欄に読めない文章があり、その中の年月が「今月＋月数」よりずっと先なら、短い月数だけを出さない
    """
    if is_live(p):
        return None, None, None, True
    raw = str(p.get("operationStartDate") or "").strip()
    if raw.lower() == "null":
        raw = ""
    # 売主が運転開始予定を「契約後Nか月」と書いている案件は、それが一番正確な言い方。日付の保険より優先する
    m = _CONTRACT_MONTHS.match(raw)
    if m and _pos_int(m.group(1)):
        return None, _pos_int(m.group(1)), "contract", False
    this_month = (today.year, today.month)
    ym = parse_ym_strict(raw)
    if not ym and not raw:
        alt = parse_ym_strict(p.get("connectionDate"))
        if alt and alt >= this_month:
            ym = alt
    if ym and ym < this_month:
        ym = None
    months, basis = lead_info(p)
    paid = grid_cost_paid(p)
    if paid == "paid":
        return _ym_str(ym), None, None, False
    if ym:
        floor = months if months else MIN_LEAD_MONTHS.get(norm_voltage(p.get("voltage")), 6)
        if _add_months(this_month, floor) > ym:
            ym = None
    if ym and months and ym > _add_months(this_month, months + 12):
        months, basis = None, None
    if not ym and months and raw:
        hints = [(int(y), int(mo)) for y, mo in _LOOSE_YM.findall(raw) if 1 <= int(mo) <= 12]
        if hints and max(hints) > _add_months(this_month, months + 12):
            months, basis = None, None
    return _ym_str(ym), months, basis, False


def derive_status(p, today):
    """過剰主張を避けた進捗ラベル。
    連系予定日が過去でも「実際に連系済み」とは限らない（計画日が後ろ倒しの可能性）ため、
    『連系済』は明示の status override がある場合のみ表示し、原則は負担金/接続検討の2段階に留める。"""
    st = str(p.get("status") or "").strip()
    if st in ("連系済", "稼働中", "運転中"):
        return "連系済"
    dep = str(p.get("depositStatus") or "").strip()
    if dep in ("支払済", "入金済"):
        return "負担金確定"
    # それ以外は dealroom 在庫の前提である「接続検討回答済」を保守的に表示
    return "接続検討回答済"


def apply_overlay(p, edits):
    if not edits:
        return p
    out = dict(p)
    for f in OVERLAY_STR:
        if f in edits and edits[f] != "":
            out[f] = edits[f]
    for f in OVERLAY_NUM:
        if f in edits and edits[f] != "":
            try:
                out[f] = float(edits[f])
            except ValueError:
                pass
    return out


def to_public(p, today):
    pref = extract_pref(p.get("address"))
    area = AREA_MAP.get(str(p.get("gridOperator") or "").strip())
    if not area and pref:
        area = PREF_TO_AREA.get(pref)
    mw = p.get("mw")
    mwh = p.get("capacityMwh")
    if mwh is None and isinstance(p.get("capacity"), (int, float)):
        mwh = round(p["capacity"] / 100) / 10  # kWh → MWh
    rec = {
        "id": p.get("id"),
        "area": area,
        "pref": pref,
        "voltage": norm_voltage(p.get("voltage")),
        "mw": round(float(mw), 2) if isinstance(mw, (int, float)) else None,
        "mwh": round(float(mwh), 1) if isinstance(mwh, (int, float)) else None,
        "cod": None, "codYm": None, "leadMonths": None, "leadBasis": None, "live": False,
        "status": derive_status(p, today),
        "scheme": norm_scheme(p.get("saleType")),
        "firstSeen": None, "updatedAt": None,   # main() が前回の一覧から持ち回る
    }
    ym, months, basis, live = cod_info(p, today)
    rec["codYm"] = ym
    rec["cod"] = _fy_str(parse_ym_strict(ym)) if ym else None
    rec["leadMonths"], rec["leadBasis"], rec["live"] = months, basis, live
    if live:
        rec["status"] = "連系済"
    return {k: rec.get(k) for k in PUBLIC_KEYS}


def first_seen_from_git(repo_dir, rel_path="projects.json"):
    """掲載日の初期値を git の履歴から起こす（schema 1→2 の移行で1回だけ使う）。
    古い順に projects.json の版をたどり、各 id が「今の掲載が始まった日」を返す。いったん消えて戻った id は戻った日。
    git が使えない・履歴が無いときは {} を返す（その場合は掲載日なしで始まる）。"""
    try:
        log = subprocess.run(["git", "-C", repo_dir, "log", "--reverse", "--format=%H %cs", "--", rel_path],
                             capture_output=True, text=True, timeout=60)
        if log.returncode != 0:
            return {}
        seen, prev_ids = {}, set()
        for line in log.stdout.splitlines():
            sha, day = line.split()[:2]
            blob = subprocess.run(["git", "-C", repo_dir, "show", f"{sha}:{rel_path}"],
                                  capture_output=True, text=True, timeout=30)
            if blob.returncode != 0:
                continue
            try:
                ids = {x.get("id") for x in json.loads(blob.stdout).get("projects", [])}
            except (json.JSONDecodeError, AttributeError):
                continue
            for i in ids - prev_ids:
                seen[i] = day
            prev_ids = ids
        return {i: d for i, d in seen.items() if i in prev_ids}
    except Exception:  # noqa: BLE001 — 掲載日が起こせないだけで一覧の生成は止めない
        return {}


def selftest():
    """連系の見込みの読み取り規則の自己検査（CI の py39-import.yml から呼ぶ。D1 は引かない）。
    ⚠️ ここは公開リポジトリ。**実案件の文言・ID・金額を写さない**。検査データは型だけ似せた合成の文にする。"""
    t = datetime.date(2026, 9, 20)
    HV, SHV = {"voltage": "高圧"}, {"voltage": "特別高圧"}
    def c(d, base=HV):
        x = dict(base); x.update(d); return x
    cases = [
        # (案件の欄, 期待する (codYm, leadMonths, leadBasis, live))
        (c({"operationStartDate": "2027-06"}), ("2027-06", None, None, False)),
        (c({"operationStartDate": "2027/6"}), ("2027-06", None, None, False)),
        (c({"operationStartDate": "2027年8月（予定）"}), ("2027-08", None, None, False)),
        (c({"operationStartDate": "2027-12-08"}), ("2027-12", None, None, False)),
        # 回答日（過去）は連系見込みに使わない
        (c({"connectionDate": "2025-02-01"}), (None, None, None, False)),
        (c({"connectionDate": "2025-02-01", "operationStartDate": "2027-12"}), ("2027-12", None, None, False)),
        # 運転開始予定が空で、回答日の欄に未来日が入っているときだけ保険で使う
        (c({"connectionDate": "2027-11-30"}), ("2027-11", None, None, False)),
        # 文章が入っていて読めないときは、回答日の欄の保険も使わない（不可と回答された希望日を拾わない）
        (c({"operationStartDate": "未定（希望日は不可との回答。調整中）", "connectionDate": "2027-07-01",
            "leadMonthsFromPayment": "8"}), (None, 8, "payment", False)),
        # 注記つきの日付は年月として採らない
        (c({"operationStartDate": "2027年3月1日（申請時の希望日。再設定が必要）", "leadMonthsFromPayment": 18}),
         (None, 18, "payment", False)),
        (c({"operationStartDate": "2030〜2031年頃"}), (None, None, None, False)),
        (c({"operationStartDate": "2026年内予定"}), (None, None, None, False)),
        # 今から入金しても間に合わない年月は出さず、月数にする
        (c({"operationStartDate": "2027-01", "leadMonthsFromPayment": 12, "constructionCostStatus": "未払"}),
         (None, 12, "payment", False)),
        (c({"operationStartDate": "2027-01", "constructionMonths": 12}), (None, 12, "unspecified", False)),
        # 月数が分からない案件は、電圧区分ごとの最短工期より手前の年月を出さない
        (c({"operationStartDate": "2026/9", "depositStatus": "未払"}), (None, None, None, False)),
        (c({"operationStartDate": "2026-12"}), (None, None, None, False)),
        (c({"operationStartDate": "2027-03"}), ("2027-03", None, None, False)),
        (c({"operationStartDate": "2027-06"}, SHV), (None, None, None, False)),
        (c({"operationStartDate": "2027-09"}, SHV), ("2027-09", None, None, False)),
        # 間に合うなら年月＋月数
        (c({"operationStartDate": "2027-10", "leadMonthsFromPayment": 8}), ("2027-10", 8, "payment", False)),
        # 年月が月数よりずっと先なら月数は付けない／「以降」は年月として読む
        (c({"operationStartDate": "2031-11以降", "leadMonthsFromPayment": 7, "leadMonthsFromApply": 85}),
         ("2031-11", None, None, False)),
        # 読めない文章の中にずっと先の年月があるとき、短い月数だけを出さない
        (c({"operationStartDate": "2031年11月頃の見込み（系統側の工事待ち）", "leadMonthsFromPayment": 7}),
         (None, None, None, False)),
        # 支払済なら月数は出さない（年月が無ければ確認中）
        (c({"operationStartDate": "2026-10", "leadMonthsFromPayment": 12, "constructionCostStatus": "支払済"}),
         ("2026-10", None, None, False)),
        (c({"operationStartDate": "2025-10-25", "constructionMonths": 4, "constructionCostStatus": "支払済"}),
         (None, None, None, False)),
        # 自由記述の支払状況は「支払済」と見なさない
        (c({"operationStartDate": "2027-01", "leadMonthsFromPayment": 12,
            "constructionCostStatus": "一部入金済み・残額は別途"}), (None, 12, "payment", False)),
        # 起点の優先順
        (c({"leadMonthsFromApply": 24, "constructionMonths": 30}), (None, 24, "apply", False)),
        (c({"operationStartDate": "契約後6か月"}), (None, 6, "contract", False)),
        (c({"operationStartDate": "契約後 約6ヶ月程度", "connectionDate": "2027-11-30", "constructionMonths": 9,
            "constructionCostStatus": "支払済"}), (None, 6, "contract", False)),
        (c({"constructionMonths": "null"}), (None, None, None, False)),
        # 過去の予定は出さない
        (c({"operationStartDate": "2025-12", "constructionMonths": 9}), (None, 9, "unspecified", False)),
        # 連系済みは欄の全体が決まり文句のときだけ
        (c({"operationStartDate": "運転開始済み"}), (None, None, None, True)),
        (c({"operationStartDate": "需給調整市場に参加・稼働実績あり", "constructionMonths": 9}), (None, None, None, True)),
        (c({"operationStartDate": "併設の太陽光は稼働中。蓄電池は2027-08予定", "constructionMonths": 9}),
         (None, 9, "unspecified", False)),
    ]
    bad = 0
    for src, want in cases:
        got = cod_info(src, t)
        if got != want:
            bad += 1
            print(f"NG {src} → {got}（期待 {want}）", file=sys.stderr)
    # 公開キーに自由記述・住所の断片が紛れ込まないこと
    rec = to_public({"id": "HV-0", "address": "架空市見本町1-2-3", "voltage": "高圧", "status": "販売中",
                     "operationStartDate": "売主の説明では12か月（99万円入金済み）",
                     "constructionCostStatus": "一部（99万円）入金済み"}, t)
    dump = json.dumps(rec, ensure_ascii=False)
    if list(rec) != PUBLIC_KEYS or "99" in dump or "見本町" in dump or rec["pref"] is not None:
        bad += 1
        print(f"NG 公開項目に想定外の値: {rec}", file=sys.stderr)
    n = len(cases) + 1
    print(f"selftest: {n - bad}/{n} OK", file=sys.stderr)
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "projects.json"))
    ap.add_argument("--end", default=None,
                    help="projects-end.json のパス（既定は dealroom2 ディレクトリの data/ 配下）")
    ap.add_argument("--prev", default=None,
                    help="掲載日・更新日を持ち回る元（前回の projects.json）。既定は --out と同じファイル")
    args = ap.parse_args()
    today = datetime.date.today()

    if not DEFAULT_D2:
        print("[error] dealroom2 のディレクトリが見つからない。"
              "SCIX_DEALROOM2_DIR を指定して再実行する。", file=sys.stderr)
        return 2
    if args.end is None:
        args.end = os.path.join(DEFAULT_D2, "data", "projects-end.json")

    # 生成前の一覧（差分を出すため）
    out_path = os.path.abspath(args.out)
    before_ids = set()
    before_generated = None
    prev_by_id, prev_schema = {}, None
    prev_path = os.path.abspath(args.prev) if args.prev else out_path
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev = json.load(f)
            prev_by_id = {p.get("id"): p for p in prev.get("projects", [])}
            before_ids = set(prev_by_id)
            before_generated = prev.get("generatedAt")
            prev_schema = prev.get("schema", 1)
        except (OSError, json.JSONDecodeError):
            pass

    # DR2 は 2026-06-22 に D1（dealroom2_new_projects）へ一元化済み。旧 projects-end.json は DR2 側でも
    # import 停止・ロールバック用の残置なので、D1 を正にする。旧ファイルは D1 に無い id の保険にだけ使う
    # （2026-09-20 実測: 旧ファイルの案件は全て D1 にあり、旧ファイル側の古い日付が公開に出ている案件があった）。
    base = list(wrangler_json("SELECT * FROM dealroom2_new_projects"))
    base_ids = {p.get("id") for p in base}
    try:
        with open(args.end, encoding="utf-8") as f:
            end = json.load(f)
    except (OSError, json.JSONDecodeError):
        end = {}
    for r in end.get("projects", []):
        rid = r.get("id")
        if rid and rid not in base_ids:
            base.append(r)
            base_ids.add(rid)

    edit_rows = wrangler_json(
        "SELECT deal_id, field, value FROM deal_edits WHERE field IN ("
        + ",".join("'%s'" % f for f in (OVERLAY_STR + OVERLAY_NUM)) + ")"
    )
    overlays = {}
    for r in edit_rows:
        overlays.setdefault(r["deal_id"], {})[r["field"]] = r["value"]

    public = []
    raw_by_id = {}
    hidden = 0
    skipped_no_id = 0
    not_for_sale = {}
    for p in base:
        pid = p.get("id")
        if not pid:
            skipped_no_id += 1
            continue
        o = apply_overlay(p, overlays.get(pid))
        if str(o.get("dealroom2Visible") or "") == "off":
            hidden += 1
            continue
        # 販売中だけを公開する。売却済み・交渉中・準備中は落とす。
        sales = str(o.get("status") or "").strip()
        if sales not in PUBLIC_SALES_STATUS:
            not_for_sale[sales or "(空欄)"] = not_for_sale.get(sales or "(空欄)", 0) + 1
            continue
        public.append(to_public(o, today))
        raw_by_id.setdefault(pid, o)

    # 最終dedup（id重複を保険で排除・先勝ち。base内やD1側の想定外重複に備える・2026-07-20）
    seen_ids = set()
    deduped = []
    for rec in public:
        if rec["id"] in seen_ids:
            continue
        seen_ids.add(rec["id"])
        deduped.append(rec)
    public = deduped

    # no（=番号）降順で並べたいが公開には no を出さないため id 由来でソート
    def sort_key(rec):
        m = re.search(r"(\d+)", rec["id"] or "")
        return -(int(m.group(1)) if m else 0)
    public.sort(key=sort_key)

    # 掲載日（firstSeen）と更新日（updatedAt）を前回の一覧から持ち回る。
    #   新しく載った id  → 掲載日 = 今日
    #   中身が変わった id → 更新日 = 今日（掲載日・更新日そのものの違いは数えない）
    # schema 1 からの移行の回は全件の中身が変わって見えるので、更新日は付けず、掲載日を git の履歴から起こす。
    #   連系の見込みは今日の日付にも依存する（月が替わると年月が落ちる）。DR2 を誰も触っていないのに
    #   「更新」が一斉に付かないよう、前回の生成日の時点で作り直した中身が前回と同じなら、時間の経過だけとみなす。
    migrating = bool(prev_by_id) and prev_schema != SCHEMA
    git_seen = first_seen_from_git(os.path.dirname(prev_path)) if (migrating or not prev_by_id) else {}
    try:
        prev_day = datetime.date.fromisoformat(before_generated) if before_generated else None
    except ValueError:
        prev_day = None
    for rec in public:
        old = prev_by_id.get(rec["id"])
        if old is None:
            rec["firstSeen"] = git_seen.get(rec["id"]) if not prev_by_id else today.isoformat()
            continue
        rec["firstSeen"] = old.get("firstSeen") or git_seen.get(rec["id"])
        rec["updatedAt"] = old.get("updatedAt")
        if migrating or all(old.get(k) == rec.get(k) for k in CONTENT_KEYS):
            continue
        as_of_prev = to_public(raw_by_id[rec["id"]], prev_day) if prev_day else None
        if as_of_prev and all(old.get(k) == as_of_prev.get(k) for k in CONTENT_KEYS):
            continue   # 元データは同じ。日付が進んだだけ
        rec["updatedAt"] = today.isoformat()

    out = {
        "generatedAt": today.isoformat(),
        "schema": SCHEMA,
        "source": "dealroom2 (auto-export / public-safe subset)",
        "projectCount": len(public),
        "projects": public,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # サマリ（stderr）
    from collections import Counter
    print(f"[ok] wrote {out_path}", file=sys.stderr)
    print(f"  total visible: {len(public)}  (hidden/off: {hidden}, no-id skipped: {skipped_no_id})", file=sys.stderr)
    print(f"  除外（販売中以外）: {not_for_sale or 'なし'}", file=sys.stderr)
    print(f"  area: {dict(Counter(r['area'] for r in public))}", file=sys.stderr)
    print(f"  voltage: {dict(Counter(r['voltage'] for r in public))}", file=sys.stderr)
    print(f"  status: {dict(Counter(r['status'] for r in public))}", file=sys.stderr)
    print(f"  scheme: {dict(Counter(r['scheme'] for r in public))}", file=sys.stderr)
    def _cod_kind(r):
        if r["live"]:
            return "連系済み"
        if r["codYm"]:
            return "年月＋月数" if r["leadMonths"] else "年月"
        return ("月数のみ(%s)" % r["leadBasis"]) if r["leadMonths"] else "確認中"
    print(f"  連系の見込み: {dict(Counter(_cod_kind(r) for r in public))}", file=sys.stderr)

    after_ids = {r["id"] for r in public}
    if before_ids:
        added = sorted(after_ids - before_ids)
        removed = sorted(before_ids - after_ids)
        print(f"  差分（前回 {before_generated} / {len(before_ids)}件 → 今回 {len(after_ids)}件）:",
              file=sys.stderr)
        print(f"    追加 {len(added)}件: {', '.join(added) or 'なし'}", file=sys.stderr)
        print(f"    削除 {len(removed)}件: {', '.join(removed) or 'なし'}", file=sys.stderr)

    missing = [r["id"] for r in public if not r["pref"] or not r["area"]]
    if missing:
        print(f"  [warn] pref/area 欠落: {missing}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except D1Unavailable as e:
        # 部分的な一覧を書き出さない。commit させないため非ゼロで終わる。
        print(f"[error] D1 を読めなかったので projects.json を更新しない: {e}", file=sys.stderr)
        sys.exit(3)
