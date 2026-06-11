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

DEFAULT_D2 = os.environ.get(
    "SCIX_DEALROOM2_DIR",
    "/Users/dr.shinyanakashima/Library/CloudStorage/GoogleDrive-s@scix.co.jp/"
    "マイドライブ/書類GD/1AI営業支援/scix/scix-dealroom2",
)
D1_DB = "scix-dealroom-db"

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


def wrangler_json(command):
    """dealroom2 ディレクトリで wrangler d1 を実行し results を返す。"""
    try:
        out = subprocess.run(
            ["npx", "wrangler", "d1", "execute", D1_DB, "--remote", "--json", "--command", command],
            cwd=DEFAULT_D2, capture_output=True, text=True, timeout=120,
        )
        data = json.loads(out.stdout)
        return data[0]["results"]
    except Exception as e:  # noqa
        print(f"[warn] wrangler query failed ({e}); 続行（D1分はスキップ）", file=sys.stderr)
        return []


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
    ap.add_argument("--end", default=os.path.join(DEFAULT_D2, "data", "projects-end.json"))
    args = ap.parse_args()
    today = datetime.date.today()

    with open(args.end, encoding="utf-8") as f:
        end = json.load(f)
    base = list(end.get("projects", []))

    new_rows = wrangler_json("SELECT * FROM dealroom2_new_projects")
    for r in new_rows:
        base.append(r)

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
    for p in base:
        pid = p.get("id")
        if not pid:
            skipped_no_id += 1
            continue
        o = apply_overlay(p, overlays.get(pid))
        if str(o.get("dealroom2Visible") or "") == "off":
            hidden += 1
            continue
        public.append(to_public(o, today))

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
    out_path = os.path.abspath(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # サマリ（stderr）
    from collections import Counter
    print(f"[ok] wrote {out_path}", file=sys.stderr)
    print(f"  total visible: {len(public)}  (hidden/off: {hidden}, no-id skipped: {skipped_no_id})", file=sys.stderr)
    print(f"  area: {dict(Counter(r['area'] for r in public))}", file=sys.stderr)
    print(f"  voltage: {dict(Counter(r['voltage'] for r in public))}", file=sys.stderr)
    print(f"  status: {dict(Counter(r['status'] for r in public))}", file=sys.stderr)
    print(f"  scheme: {dict(Counter(r['scheme'] for r in public))}", file=sys.stderr)
    missing = [r["id"] for r in public if not r["pref"] or not r["area"]]
    if missing:
        print(f"  [warn] pref/area 欠落: {missing}", file=sys.stderr)


if __name__ == "__main__":
    main()
