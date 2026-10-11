#!/usr/bin/env python3
"""一次オフライン（1-1）の時間帯別の落札量加重平均価格（コラム50 市場編）。

aggregate_column50.py の読み取り関数を使い、速報値の P1（4/1〜8/31）と P2（9/1〜--end）を
時間帯（4時間ごと6本: 0〜4時・4〜8時・…・20〜24時）× 管区（電源属地別）で集計する。
式: Σ(平均落札価格×落札量)÷Σ落札量。落札量0のコマは除く。価格は表示値（精算前）。
python3 scripts/eprx/time_of_day_column50.py [データ根] [出力先] [--end 2026-09-29]
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aggregate_column50 as ag  # noqa: E402

BANDS = [(1, 8, '0〜4時'), (9, 16, '4〜8時'), (17, 24, '8〜12時'),
         (25, 32, '12〜16時'), (33, 40, '16〜20時'), (41, 48, '20〜24時')]


def band_of(b):
    for lo, hi, name in BANDS:
        if lo <= b <= hi:
            return name
    raise ValueError(b)


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    end = ag.DEF_END
    if '--end' in argv:
        end = argv[argv.index('--end') + 1]
        args = [a for a in args if a != end]
    root = os.path.expanduser(args[0] if args else ag.DEF_ROOT)
    out = args[1] if len(args) > 1 else ag.DEF_OUT
    end8 = end.replace('-', '')
    found = ag.find_files(root)
    paths = found.get(('prompt', '1-1'))
    if not paths:
        raise SystemExit('1-1 の速報値が見つからない: ' + root)
    slots, metas, dropped = ag.load_series('prompt', paths, end8, ag.MAIN)
    acc = {}
    for key, (d, _f) in slots.items():
        m = ag.KEY_RE.match(key)
        day, b = m.group(1), int(m.group(2))
        per = 'P1' if day <= ag.P1_HI else 'P2'
        bn = band_of(b)
        for j, col in enumerate(ag.COLS):
            vol, avg = d['vol'][j], d['avg'][j]
            if vol is None or vol <= 0 or avg is None:
                continue
            a = acc.setdefault((per, bn, col), [0.0, 0.0, 0])
            a[0] += avg * vol
            a[1] += vol
            a[2] += 1
    rows = []
    for per in ('P1', 'P2'):
        for _lo, _hi, bn in BANDS:
            for col, name in zip(ag.COLS, ag.NAMES):
                a = acc.get((per, bn, col))
                w = a[0] / a[1] if a and a[1] else ''
                rows.append({'区分': '速報', '商品': '1-1', '期間': per, '時間帯': bn,
                             '管区': name, '加重平均': w,
                             '落札量の和_MWコマ': a[1] if a else 0,
                             '対象コマ数': a[2] if a else 0})
    path = os.path.join(out, 'eprx_1-1_time_of_day.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print('出力:', path, len(rows), '行')
    for per in ('P1', 'P2'):
        line = []
        for _lo, _hi, bn in BANDS:
            a = acc.get((per, bn, '合計'))
            line.append('%s %.2f' % (bn, a[0] / a[1]))
        print(per, '全国:', ' / '.join(line))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
