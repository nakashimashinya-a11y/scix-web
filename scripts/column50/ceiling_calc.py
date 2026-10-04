#!/usr/bin/env python3
"""COLUMN 50 試算編: 需給調整市場ガイドラインの「一定額」を2MW/8MWhで置く。

式（需給調整市場ガイドライン 2026年3月13日改定 p.6-7）:
  一定額 = (当年度分の固定費 - 他市場収益) / 想定応札量
  当年度分の固定費を回収した後は A種 0.33円/ΔkW・30分
入力は inputs.json（公表値と仮置き）だけから読む。値を直書きしない。
出力: docs/research/column-50/ceiling_*.csv と ceiling_tables.md
python3 scripts/column50/ceiling_calc.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "docs", "research", "column-50")
AREAS = ["北海道", "東北", "東京", "中部", "北陸",
         "関西", "中国", "四国", "九州"]


def load_inputs(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_occto_alpha(path):
    """occto_coefficients.md の「### 4h」「### 3h」の表（エリア×12か月・%表示）を読み、
    12か月の単純平均（小数）を返す。様式2の期待容量＝各月の係数×各月の放電可能電力の
    12か月平均（放電可能電力が毎月同じなら、放電可能電力×この平均）。"""
    out, cur = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t.startswith("### "):
                cur = t[4:].split("（")[0].strip()
                if cur not in ("4h", "3h"):
                    cur = None
                continue
            if cur and t.startswith("|") and not t.startswith("|---"):
                cells = [x.strip() for x in t.strip("|").split("|")]
                if cells[0] in AREAS:
                    vals = [float(x.rstrip("%")) / 100.0 for x in cells[1:13]]
                    if len(vals) != 12:
                        raise SystemExit("12か月そろっていない: %s %s" % (cur, cells[0]))
                    out.setdefault("occto2029_" + cur, {})[cells[0]] = sum(vals) / 12.0
    for k, v in out.items():
        if sorted(v) != sorted(AREAS):
            raise SystemExit("9エリアそろっていない: " + k)
    return out


def depreciation(capex, rate, life, year):
    """定額法。最終年は備忘価額1円を残す。"""
    per = round(capex * rate)
    if year < life:
        return per
    if year == life:
        return capex - per * (life - 1) - 1
    return 0


def asset_value(capex, year, first, later, floor_ratio):
    """固定資産税の評価額（賦課期日1月1日時点）。year は運開年度の通し番号。

    1年目は賦課期日に未取得（課税なし）。2年目が取得後の初回。
    端数処理（課税標準の千円未満切捨て等）は省く。
    """
    if year < 2:
        return 0.0
    v = capex * first * later ** (year - 2)
    return max(v, capex * floor_ratio)


def one_year(c, area, year, kw, kwh, unit_capex, r, alpha,
             deduct_from):
    capex = unit_capex * kwh
    dep = depreciation(capex, c["dep_rate"], c["dep_life"], year)
    rep = c["repair_yen_per_kw_year"] * kw
    gsc = round(c["gen_side_charge_yen_per_kw_month"][area] * kw * 12)
    tax = asset_value(capex, year, c["tax_first_ratio"],
                      c["tax_later_ratio"], c["tax_floor_ratio"])
    tax = round(tax * c["tax_rate"])
    fixed = dep + rep + gsc + tax
    price = c["capacity_area_price_yen_per_kw"][area]
    # 期待容量は様式2と同じく kW の整数に四捨五入してから単価を掛ける
    expected_kw = int(kw * alpha + 0.5)
    ded = expected_kw * price if year >= deduct_from else 0
    q = kw * 48 * 365 * r
    upper = fixed - ded
    b = upper / q
    a = c["a_type_yen"]
    applied = a if upper <= 0 else max(b, a)
    return {"area": area, "year": year, "kw": kw, "kwh": kwh,
            "capex": capex, "r": r, "alpha": alpha,
            "depreciation": dep, "repair": rep, "gen_side_charge": gsc,
            "property_tax": tax, "fixed_total": fixed,
            "expected_kw": expected_kw, "area_price": price,
            "capacity_deduction": ded, "upper_amount": upper,
            "bid_volume_q": q, "b_type_raw": b,
            "no_deduction_raw": fixed / q, "applied": applied,
            "applied_rule": "A種" if applied == a else "B種"}


def run_case(c, area, kw, kwh, unit_capex, r, alpha, years):
    return [one_year(c, area, y, kw, kwh, unit_capex, r, alpha,
                     c["deduct_from_year"]) for y in years]


def write_csv(path, rows):
    keys = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def fmt3(x):
    return "%.3f" % x


def main():
    c = load_inputs(os.path.join(HERE, "inputs.json"))
    os.makedirs(OUT, exist_ok=True)
    occto = os.path.join(OUT, "occto_coefficients.md")
    if os.path.exists(occto):
        c["alpha"].update(load_occto_alpha(occto))
    base = c["base"]
    years = list(range(1, 21))
    alpha_key = c["alpha_basis"]
    rows = []
    for area in AREAS:
        alpha = c["alpha"][alpha_key][area]
        rows += run_case(c, area, base["kw"], base["kwh"],
                         base["unit_capex_yen_per_kwh"], base["r"],
                         alpha, years)
    write_csv(os.path.join(OUT, "ceiling_by_area_year.csv"), rows)
    sens = []
    sarea = c["sensitivity_area"]
    alpha = c["alpha"][alpha_key][sarea]
    cases = [("基準", base["unit_capex_yen_per_kwh"], base["r"],
              base["kwh"], alpha)]
    for k, m in (("CAPEX+20%", 1.2), ("CAPEX-20%", 0.8)):
        cases.append((k, base["unit_capex_yen_per_kwh"] * m,
                      base["r"], base["kwh"], alpha))
    for r in c["sensitivity_r"]:
        cases.append(("r=%d%%" % round(r * 100),
                      base["unit_capex_yen_per_kwh"], r,
                      base["kwh"], alpha))
    cases.append(("2時間電池（控除なし）", base["unit_capex_yen_per_kwh"],
                  base["r"], base["kw"] * 2, 0.0))
    cases.append(("控除なし（α=0）", base["unit_capex_yen_per_kwh"],
                  base["r"], base["kwh"], 0.0))
    for k in c.get("alpha_sensitivity", []):
        cases.append(("調整係数=%s" % k, base["unit_capex_yen_per_kwh"],
                      base["r"], base["kwh"], c["alpha"][k][sarea]))
    for name, uc, r, kwh, a in cases:
        for row in run_case(c, sarea, base["kw"], kwh, uc, r, a, years):
            row = dict(row)
            row["case"] = name
            sens.append(row)
    write_csv(os.path.join(OUT, "ceiling_sensitivity.csv"), sens)
    pick = c["report_years"]
    lines = ["# COLUMN 50 試算（scripts/column50/ceiling_calc.py の出力）",
             "", "調整係数の基準: %s" % alpha_key, "",
             "| エリア | " + " | ".join(sorted(c["alpha"])) + " |",
             "|---|" + "---|" * len(c["alpha"])]
    for area in AREAS:
        lines.append("| %s | %s |" % (area, " | ".join(
            "%.6f" % c["alpha"][k][area] for k in sorted(c["alpha"]))))
    lines += ["",
             "## 9エリア（基準: r=%s・CAPEX %s円/kWh）"
             % (base["r"], base["unit_capex_yen_per_kwh"]), "",
             "| エリア | α | " + " | ".join("%d年目" % y for y in pick)
             + " |", "|---|---|" + "---|" * len(pick)]
    for area in AREAS:
        rr = [x for x in rows if x["area"] == area]
        vals = [fmt3(rr[y - 1]["applied"]) for y in pick]
        lines.append("| %s | %s | %s |" % (
            area, rr[0]["alpha"], " | ".join(vals)))
    lines += ["", "## 感度（%s）" % sarea, "",
              "| ケース | " + " | ".join("%d年目" % y for y in pick)
              + " |", "|---|" + "---|" * len(pick)]
    for name, *_ in cases:
        rr = [x for x in sens if x["case"] == name]
        vals = [fmt3(rr[y - 1]["applied"]) for y in pick]
        lines.append("| %s | %s |" % (name, " | ".join(vals)))
    lines += ["", "## %s 基準の内訳（円）" % sarea, "",
              "| 年目 | 償却 | 修繕 | 発電側課金 | 固定資産税 | 固定費計"
              " | 容量控除 | 上限額 | Q | B種の計算値 | 採る値 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    rr = [x for x in sens if x["case"] == "基準"]
    for x in rr:
        lines.append("| %d | %d | %d | %d | %d | %d | %d | %d | %d"
                     " | %s | %s %s |" % (
                         x["year"], x["depreciation"], x["repair"],
                         x["gen_side_charge"], x["property_tax"],
                         x["fixed_total"], x["capacity_deduction"],
                         x["upper_amount"], x["bid_volume_q"],
                         "%.4f" % x["b_type_raw"], fmt3(x["applied"]),
                         x["applied_rule"]))
    with open(os.path.join(OUT, "ceiling_tables.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
