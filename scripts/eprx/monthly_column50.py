#!/usr/bin/env python3
"""一次オフライン（1-1）・速報値の月別の落札量加重平均（全国＝CSV の「合計」列、と9管区）。コラム50 市場編。

式は aggregate_column50.py と同じ: Σ(平均落札価格×落札量)÷Σ落札量。落札量0のコマは除く。--end 以降は入れない。
python3 scripts/eprx/monthly_column50.py [データ根] [出力先] [--end 2026-09-29]
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aggregate_column50 as ag  # noqa: E402


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    end = ag.DEF_END
    if '--end' in argv:
        end = argv[argv.index('--end') + 1]
        args = [a for a in args if a != end]
    root = os.path.expanduser(args[0] if args else ag.DEF_ROOT)
    out = args[1] if len(args) > 1 else ag.DEF_OUT
    slots, _m, _d = ag.load_series('prompt', ag.find_files(root)[('prompt', '1-1')], end.replace('-', ''), ag.MAIN)
    acc = {}
    for key, (d, _f) in slots.items():
        month = key[:6]
        for j, name in enumerate(ag.NAMES):
            vol, avg = d['vol'][j], d['avg'][j]
            if vol is None or vol <= 0 or avg is None:
                continue
            a = acc.setdefault((month, name), [0.0, 0.0, 0])
            a[0] += avg * vol
            a[1] += vol
            a[2] += 1
    rows = [{'区分': '速報', '商品': '1-1', '月': m, '管区': n, '加重平均': a[0] / a[1], '対象コマ数': a[2]}
            for (m, n), a in sorted(acc.items())]
    path = os.path.join(out, 'eprx_1-1_monthly.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print('出力:', path)
    for r in rows:
        if r['管区'] in ('全国', '東北', '東京', '中部', '九州'):
            print(r['月'], r['管区'], '%.2f' % r['加重平均'], r['対象コマ数'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
