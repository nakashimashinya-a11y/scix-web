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

出力フィールド（守秘準拠・NDA前=都道府県レベルまで）:
  id / area(管内) / pref(都道府県) / voltage / mw / mwh / cod(連系予定年度) / status(進捗) / scheme
必ず除外: name・住所(地番)・lat/lng・price・seller・社内memo

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
               "depositStatus", "operationStartDate", "dealroom2Visible"]
OVERLAY_NUM = ["mw", "capacity", "maxPower"]


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
        return PREF_ALIASES.get(m.group(1), m.group(1))
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


def fiscal_year(date_str):
    """'2027-04-01' → '2027年度'（4月始まり）。連系日が無ければ None。"""
    if not date_str:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})", str(date_str))
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    fy = y if mo >= 4 else y - 1
    return f"{fy}年度"


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
        "cod": fiscal_year(p.get("connectionDate")),
        "status": derive_status(p, today),
        "scheme": norm_scheme(p.get("saleType")),
    }
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "projects.json"))
    ap.add_argument("--end", default=None,
                    help="projects-end.json のパス（既定は dealroom2 ディレクトリの data/ 配下）")
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
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                prev = json.load(f)
            before_ids = {p.get("id") for p in prev.get("projects", [])}
            before_generated = prev.get("generatedAt")
        except (OSError, json.JSONDecodeError):
            pass

    with open(args.end, encoding="utf-8") as f:
        end = json.load(f)
    base = list(end.get("projects", []))

    new_rows = wrangler_json("SELECT * FROM dealroom2_new_projects")
    # 既存(projects-end)に在る案件は D1 新規側で重複追加しない（公開の二重カード防止・2026-07-20）
    base_ids = {p.get("id") for p in base}
    for r in new_rows:
        rid = r.get("id")
        if rid in base_ids:
            continue
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

    out = {
        "generatedAt": today.isoformat(),
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
