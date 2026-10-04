#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EPRX 取引結果CSV → コラム50 用の集計（標準ライブラリだけ・python3.9 可）。

商品 1-0（一次調整力・1次オンライン）・1-1（一次オフライン）・4-0（複合商品）を、
9管区＋全国、期間 P1（2026-04-01〜08-31）・P2（2026-09-01〜--end）で集計する。
速報値と確報値は別々に出す（混ぜない）。確報値は「合計（確報値）」の行だけ使う。
電源種別別（速報値・全国）も同じ期間で集計する。
式・列名・出典・規約の注意は同じフォルダの README.md。

使い方:
  python3 scripts/eprx/aggregate_column50.py [データ根] [出力先] [--end YYYY-MM-DD]
  python3 scripts/eprx/aggregate_column50.py --check [データ根]
"""
import argparse
import csv
import datetime
import io
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEF_ROOT = '~/マイドライブ/9_システム/外部資料/EPRX'
DEF_OUT = os.path.join(REPO, 'docs', 'research', 'column-50')
DEF_END = '2026-09-29'

AREAS = ['北海道', '東北', '東京', '中部', '北陸', '関西', '中国', '四国', '九州']
COLS = AREAS + ['合計']  # CSV の列。出力では「合計」を「全国」と書く
NAMES = AREAS + ['全国']
TYPES = ['火力発電', '水力・揚水発電', '蓄電池', 'VPP', '合計']  # 電源種別別の列（原文）
PRODUCTS = [
    ('1-0', '一次調整力（1次オンライン）'),
    ('1-1', '一次オフライン'),
    ('4-0', '複合商品'),
]
KINDS = [('prompt', '速報'), ('result', '確報')]
RT_KIND, RT_LABEL = 'rt_prompt', '電源種別別'
SUB = {'prompt': '速報値', 'result': '確報値', 'rt_prompt': '電源種別別'}  # 置き場のフォルダ
LABEL = {'prompt': '速報値', 'result': '確報値', 'rt_prompt': '速報値'}  # P 行の表示
P1_LO, P1_HI, P2_LO = '20260401', '20260831', '20260901'
# ΔkW 上限価格［円/ΔkW・30分］（一次・一次オフライン・複合）。上限超の札も約定し、精算で上限に切られる
CAP = {'P1': 15.0, 'P2': 10.0}
THRESHOLD = 10.0
BLOCKS = 48
FIRST_MONTH = '202604'
NAME_RE = re.compile(r'^(\d{6})_(1-0|1-1|4-0)_(prompt|result|rt_prompt)\.csv$')
KEY_RE = re.compile(r'^(\d{8})B(\d{2})$')
KUBUN_COL, KUBUN_SUM = '調達区分', '合計（確報値）'

# 使う項目名 → 欄。速報値は「落札」、確報値の「合計（確報値）」は「約定」の語（実ファイルで確認）
FIELDS = {'募集量（TSO別）[MW]': 'bosyu', '応札量合計（電源属地別）[MW]': 'osatsu'}
for _w in ('落札', '約定'):
    FIELDS[_w + '量合計（電源属地別）[MW]'] = 'vol'
    FIELDS['平均' + _w + '価格（電源属地別）[円/kW・30分]'] = 'avg'
    FIELDS['最高' + _w + '価格（電源属地別）[円/kW・30分]'] = 'max'
    FIELDS[_w + '量合計（TSO別）[MW]'] = 'tvol'
    FIELDS['平均' + _w + '価格（TSO別）[円/kW・30分]'] = 'tavg'
MAIN = {'cols': COLS, 'fields': FIELDS,
        'need': ('bosyu', 'osatsu', 'vol', 'avg', 'max', 'tvol', 'tavg')}
# 電源種別別（全国・速報値だけ）の項目名
RT = {'cols': TYPES, 'need': ('vol', 'avg', 'max'),
      'fields': {'落札量合計[MW]': 'vol', '平均落札価格[円/kW・30分]': 'avg',
                 '最高落札価格[円/kW・30分]': 'max'}}

# 研究の実測（2026/9/1 B01・1-0 速報）。--check で読み取り関数と照合する
CHECK_FILE, CHECK_KEY = '202609_1-0_prompt.csv', '20260901B01'
CHECK_EXPECT = [
    ('東北', 'max', 15.0), ('東北', 'avg', 6.91), ('東北', 'osatsu', 79.309),
    ('東北', 'bosyu', 175.0), ('東京', 'max', 10.0), ('東京', 'avg', 4.04),
    ('四国', 'avg', 0.64), ('四国', 'osatsu', 214.473), ('四国', 'bosyu', 41.0),
    ('合計', 'vol', 1459.181), ('合計', 'avg', 3.53),
]


class DataError(Exception):
    """CSV の形が想定と違う。黙って進めずに止める。"""


def nfc(s):
    return unicodedata.normalize('NFC', s)


def ymd(d):
    return datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8]))


def iso(d):
    return '%s-%s-%s' % (d[:4], d[4:6], d[6:8])


def md_day(d):
    """'YYYY-MM-DD' か 'YYYYMMDD' → 'M/D'"""
    d = d.replace('-', '')
    return '%d/%d' % (int(d[4:6]), int(d[6:8]))


def day_range(lo, hi):
    out, d, end = [], ymd(lo), ymd(hi)
    while d <= end:
        out.append(d.strftime('%Y%m%d'))
        d += datetime.timedelta(days=1)
    return out


def date_runs(days):
    """'YYYYMMDD' の並び → 続く日を 'YYYY-MM-DD〜YYYY-MM-DD' にまとめた文字列"""
    runs = []
    for d in days:
        if runs and (ymd(d) - ymd(runs[-1][-1])).days == 1:
            runs[-1].append(d)
        else:
            runs.append([d])
    return ' '.join(iso(r[0]) if len(r) == 1 else iso(r[0]) + '〜' + iso(r[-1]) for r in runs)


def num(s, where):
    """数値の文字列 → float。「-」と空は None（数値なし）。ほかの文字は止める。"""
    s = s.strip()
    if s in ('-', ''):
        return None
    try:
        return float(s)
    except ValueError:
        raise DataError('%s: 数値でない値 %r' % (where, s))


def read_csv(path, spec=MAIN):
    """取引結果CSV 1本 → (meta, slots)。slots は 'YYYYMMDDBnn' → {欄: [spec の列の値]}。"""
    name = nfc(os.path.basename(path))
    with io.open(path, encoding='cp932', newline='') as fh:
        rows = [r for r in csv.reader(fh) if r]
    heads = [r[0] for r in rows[:3]]
    if heads != ['H', 'P', 'TT'] or len(rows[1]) < 5:
        raise DataError('%s: 先頭3行が H・P・TT でない %r' % (name, heads))
    if rows[-1][0] != 'E':
        raise DataError(name + ': 最後の行が E でない（途中で切れている？）')
    p, tt = rows[1], rows[2]
    meta = {'file': name, 'label': p[1], 'month': p[2], 'product': p[3],
            'nblocks': int(p[4]), 'items': {}, 'dash': 0}
    lack = [c for c in ['取引情報'] + spec['cols'] if c not in tt]
    if lack:
        raise DataError('%s: TT 行に列が無い %r' % (name, lack))
    ii = tt.index('取引情報')
    ci = [tt.index(c) for c in spec['cols']]
    si = tt.index(KUBUN_COL) if KUBUN_COL in tt else None
    slots, seen = {}, set()
    for r in rows[3:-1]:
        if not KEY_RE.match(r[0]):
            raise DataError('%s: キーの形が違う %r' % (name, r[0]))
        if si is not None and r[si] != KUBUN_SUM:
            continue
        seen.add(r[ii])
        f = spec['fields'].get(r[ii])
        if f is None:
            continue
        where = '%s %s %s' % (name, r[0], r[ii])
        d = slots.setdefault(r[0], {})
        if f in d:
            raise DataError(where + ': 同じ欄が2行ある')
        d[f] = [num(r[i], where) for i in ci]
        meta['dash'] += sum(1 for i in ci if r[i].strip() == '-')
        meta['items'][f] = r[ii]
    if not slots:
        raise DataError('%s: 使える行が無い。項目名 %r' % (name, sorted(seen)))
    for key, d in slots.items():
        miss = [f for f in spec['need'] if f not in d]
        if miss:
            raise DataError('%s %s: 欄が欠けている %r。項目名 %r' % (name, key, miss, sorted(seen)))
    return meta, slots


def find_files(root):
    """データ根の下の 速報値/・確報値/・電源種別別/ から {(kind, 商品): {YYYYMM: パス}} を作る。"""
    found, seen = {}, {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        parent = nfc(os.path.basename(dirpath))
        for fn in sorted(filenames):
            m = NAME_RE.match(nfc(fn))
            if not m:
                continue
            month, code, kind = m.groups()
            if parent != SUB[kind] or month < FIRST_MONTH:
                continue
            path = os.path.join(dirpath, fn)
            if nfc(fn) in seen:
                raise DataError('同じ名前のファイルが2か所にある: %s / %s' % (seen[nfc(fn)], path))
            seen[nfc(fn)] = path
            found.setdefault((kind, code), {})[month] = path
    return found


def load_series(kind, paths, end, spec):
    """{YYYYMM: パス} → (slots, metas, 除いた日)。slots は キー → (欄の辞書, ファイル名)。"""
    slots, metas, dropped = {}, [], set()
    for month in sorted(paths):
        meta, part = read_csv(paths[month], spec)
        if meta['label'] != LABEL[kind] or meta['month'] != month:
            msg = '%s: P 行が %s・%s（ファイル名と合わない）'
            raise DataError(msg % (meta['file'], meta['label'], meta['month']))
        if meta['nblocks'] != BLOCKS:
            raise DataError('%s: ブロック数が %d（48 のはず）' % (meta['file'], meta['nblocks']))
        for key, d in part.items():
            m = KEY_RE.match(key)
            if key[:6] != month or not 1 <= int(m.group(2)) <= BLOCKS:
                raise DataError('%s: キー %s が年月・ブロック数と合わない' % (meta['file'], key))
            if m.group(1) > end:
                dropped.add(m.group(1))
                continue
            slots[key] = (d, meta['file'])
        metas.append(meta)
    return slots, metas, sorted(dropped)


def new_acc():
    return {'pv': 0.0, 'v': 0.0, 'excl': 0, 'tpv': 0.0, 'tv': 0.0, 'texcl': 0,
            'max': None, 'maxdays': set(), 'maxn': 0, 'ge': 0, 'gedays': set(),
            'over': 0, 'overdays': set(), 'bo1': 0.0, 'os1': 0.0, 'skip1': 0,
            'os2': 0.0, 'v2': 0.0, 'skip2': 0,
            'sum': {'bosyu': 0.0, 'osatsu': 0.0, 'vol': 0.0, 'tvol': 0.0}}


def add_slot(a, d, j, day, cap):
    """1コマ・1列を足し込む（電源種別別の CSV に無い欄は飛ばす）。"""
    vol, avg, mx = d['vol'][j], d['avg'][j], d['max'][j]
    if vol is None or vol <= 0 or avg is None:
        a['excl'] += 1  # 落札量0か「-」は加重平均から除く
    else:
        a['pv'] += avg * vol
        a['v'] += vol
    if mx is not None:
        if a['max'] is None or mx > a['max']:
            a['max'], a['maxdays'], a['maxn'] = mx, set([day]), 1
        elif mx == a['max']:
            a['maxdays'].add(day)
            a['maxn'] += 1
        if mx >= THRESHOLD:
            a['ge'] += 1
            a['gedays'].add(day)
        if mx > cap:
            a['over'] += 1
            a['overdays'].add(day)
    for f in a['sum']:
        if f in d and d[f][j] is not None:
            a['sum'][f] += d[f][j]
    if 'tvol' in d:
        tv, ta = d['tvol'][j], d['tavg'][j]
        if tv is None or tv <= 0 or ta is None:
            a['texcl'] += 1
        else:
            a['tpv'] += ta * tv
            a['tv'] += tv
    if 'bosyu' in d:
        bo, os_ = d['bosyu'][j], d['osatsu'][j]
        if bo is None or os_ is None:
            a['skip1'] += 1
        else:
            a['bo1'] += bo
            a['os1'] += os_
        if vol is None or os_ is None:
            a['skip2'] += 1
        else:
            a['v2'] += vol
            a['os2'] += os_


def div(a, b):
    return a / b if b else None


def finish(a):
    has = a['max'] is not None and a['max'] > 0
    return {
        'wavg': div(a['pv'], a['v']), 'pv': a['pv'], 'v': a['v'], 'excl': a['excl'],
        'max': a['max'] if has else None,
        'maxday': iso(min(a['maxdays'])) if has else '',
        'maxdays': len(a['maxdays']) if has else '',
        'maxn': a['maxn'] if has else '',
        'ge': a['ge'], 'gedays': len(a['gedays']),
        'over': a['over'], 'overdays': len(a['overdays']),
        'ob': div(a['os1'], a['bo1']), 'skip1': a['skip1'],
        'vo': div(a['v2'], a['os2']), 'skip2': a['skip2'],
        'twavg': div(a['tpv'], a['tv']), 'texcl': a['texcl'],
        'sum': a['sum'],
    }


def summarize(slots, lo, hi, cap, ncols):
    """期間 [lo, hi] のコマ → (info, 列ごとの指標)。"""
    keys = sorted(k for k in slots if lo <= k[:8] <= hi)
    accs = [new_acc() for _ in range(ncols)]
    files, per_day = set(), {}
    for k in keys:
        d, fn = slots[k]
        files.add(fn)
        day = k[:8]
        per_day[day] = per_day.get(day, 0) + 1
        for j in range(ncols):
            add_slot(accs[j], d, j, day, cap)
    expect = day_range(lo, hi) if lo <= hi else []
    info = {'lo': lo, 'hi': hi, 'n': len(keys), 'days': sorted(per_day),
            'files': sorted(files),
            'missing': [x for x in expect if per_day.get(x, 0) < BLOCKS]}
    return info, [finish(a) for a in accs]


def periods(end):
    return [('P1', P1_LO, min(P1_HI, end)), ('P2', P2_LO, end)]


def run_all(root, end):
    """全部の系列を読む → (res, log)。res[(区分, 商品, 期間)] = (info, 指標)。"""
    found = find_files(root)
    res, log = {}, {}
    for kind, klabel in KINDS + [(RT_KIND, RT_LABEL)]:
        spec = RT if kind == RT_KIND else MAIN
        for code, _ in PRODUCTS:
            paths = found.get((kind, code), {})
            slots, metas, dropped = {}, [], []
            if paths:
                slots, metas, dropped = load_series(kind, paths, end, spec)
            log[(klabel, code)] = {'months': sorted(paths), 'dropped': dropped,
                                   'dash': sum(m['dash'] for m in metas)}
            for pname, lo, hi in periods(end):
                res[(klabel, code, pname)] = summarize(slots, lo, hi, CAP[pname],
                                                       len(spec['cols']))
    return res, log


def cell(x):
    if x is None:
        return ''
    if isinstance(x, float):
        return repr(x)
    return x


HEAD = ['区分', '商品', '商品名', '期間', '期間の範囲', '管区',
        '加重平均', '最高', '最高日', '≧10コマ数', '≧10日数', '応札/募集', '落札/応札',
        '参考_TSO別加重平均', '対象コマ数', '除外コマ数', '最初の受渡日', '最後の受渡日',
        '最高の出た日数', '最高の出たコマ数', '上限', '上限超コマ数', '上限超日数',
        'TSO別_除外コマ数', '応札/募集_除外コマ数', '落札/応札_除外コマ数', '欠けている日',
        'Σ募集量', 'Σ応札量', 'Σ落札量', 'Σ落札量TSO別', '元ファイル一覧']
RT_HEAD = ['区分', '商品', '商品名', '期間', '期間の範囲', '電源種別',
           '加重平均', '最高', '最高日', '≧10コマ数', '≧10日数', 'Σ落札量', '落札量シェア',
           '対象コマ数', '除外コマ数', '最初の受渡日', '最後の受渡日', '最高の出た日数',
           '最高の出たコマ数', '上限', '上限超コマ数', '上限超日数', '欠けている日', '元ファイル一覧']


def blank_row(head, base, pname):
    out = [''] * (len(head) - len(base))
    out[head.index('対象コマ数') - len(base)] = 0
    out[head.index('上限') - len(base)] = CAP[pname]
    out[head.index('欠けている日') - len(base)] = '（データ無し）'
    return base + out


def csv_rows(res):
    out = []
    for _, klabel in KINDS:
        for code, pname_ in PRODUCTS:
            for pname in ('P1', 'P2'):
                info, mets = res[(klabel, code, pname)]
                rng = iso(info['lo']) + '〜' + iso(info['hi'])
                for name, m in zip(NAMES, mets):
                    base = [klabel, code, pname_, pname, rng, name]
                    if info['n'] == 0:
                        out.append(blank_row(HEAD, base, pname))
                        continue
                    s = m['sum']
                    out.append(base + [
                        m['wavg'], m['max'], m['maxday'], m['ge'], m['gedays'],
                        m['ob'], m['vo'], m['twavg'], info['n'], m['excl'],
                        iso(info['days'][0]), iso(info['days'][-1]),
                        m['maxdays'], m['maxn'], CAP[pname], m['over'], m['overdays'],
                        m['texcl'], m['skip1'], m['skip2'], date_runs(info['missing']),
                        s['bosyu'], s['osatsu'], s['vol'], s['tvol'], ';'.join(info['files'])])
    return out


def rt_rows(res, log):
    """電源種別別の行。ファイルが1本も無い商品は行を作らない（md に注記）。"""
    out = []
    for code, pname_ in PRODUCTS:
        if not log[(RT_LABEL, code)]['months']:
            continue
        for pname in ('P1', 'P2'):
            info, mets = res[(RT_LABEL, code, pname)]
            rng = iso(info['lo']) + '〜' + iso(info['hi'])
            total = mets[-1]['sum']['vol']
            for name, m in zip(TYPES, mets):
                base = ['速報', code, pname_, pname, rng, name]
                if info['n'] == 0:
                    out.append(blank_row(RT_HEAD, base, pname))
                    continue
                out.append(base + [
                    m['wavg'], m['max'], m['maxday'], m['ge'], m['gedays'],
                    m['sum']['vol'], div(m['sum']['vol'], total), info['n'], m['excl'],
                    iso(info['days'][0]), iso(info['days'][-1]), m['maxdays'], m['maxn'],
                    CAP[pname], m['over'], m['overdays'], date_runs(info['missing']),
                    ';'.join(info['files'])])
    return out


def write_csv(path, head, rows):
    with io.open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(head)
        for r in rows:
            w.writerow([cell(x) for x in r])


def f2(x):
    return '—' if x is None or x == '' else '%.2f' % x


def comma(n):
    return '{:,}'.format(n)


def pct(x):
    return '—' if x is None else '%.1f%%' % (x * 100)


def md_value(key, m, info):
    if info['n'] == 0:
        return '—'
    if key in ('wavg', 'twavg', 'ob'):
        return f2(m[key])
    if key == 'vo':
        return pct(m['vo'])
    if key == 'max':
        if m['max'] is None:
            return '—'
        more = '' if m['maxdays'] == 1 else ' ほか%d日' % (m['maxdays'] - 1)
        return '%.2f（%s%s）' % (m['max'], md_day(m['maxday']), more)
    if key == 'ge':
        return '%sコマ／%d日' % (comma(m['ge']), m['gedays'])
    if key == 'over':
        return '%sコマ／%d日' % (comma(m['over']), m['overdays'])
    if key == 'excl':
        return '%s／%s' % (comma(m['excl']), comma(info['n']))
    raise KeyError(key)


SECTIONS = [
    ('wavg', '落札量加重平均価格［円/kW・30分］',
     'Σ(平均落札価格×落札量)÷Σ落札量（電源属地別）。落札量0のコマは除く（最後の表）。'),
    ('max', '最高落札価格の期間内最大値［円/kW・30分］（最初に出た日）',
     '電源属地別の表示値。同じ値が別の日にも出たときは「ほかN日」。'),
    ('ge', '最高落札価格 ≧10円 のコマ数／日数',
     '日数は1コマでも該当した受渡日の数。表示値で数えた。P2 の10円超の表示値は精算で10円に切られる。'),
    ('over', '最高落札価格の表示値が上限を超えたコマ数／日数（P1 ＞15円・P2 ＞10円）',
     '上限超の札も約定し、精算で上限に切られる（README）。'),
    ('ob', '応札量÷募集量［倍］',
     '分子は電源属地別、分母は TSO 別で基準が違う（管区の値はエリアをまたぐ応札・調達を含む。全国は同じ基準）。'),
    ('vo', '落札量÷応札量', '電源属地別どうし。'),
    ('twavg', '参考: TSO別 平均落札価格の加重平均［円/kW・30分］',
     'Σ(平均落札価格[TSO別]×落札量[TSO別])÷Σ落札量[TSO別]。'),
    ('excl', '加重平均から除いたコマ数／対象コマ数',
     '除いたのは落札量0のコマ（重み0なので加重平均の値は変わらない）。'),
]


def md_table(head, rows, right=True):
    sep = ['---'] + ['---:' if right else '---'] * (len(head) - 1)
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join(sep) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(r) + ' |')
    return out


def col_label(klabel, pname, info):
    if info['n'] == 0:
        return '%s %s<br>データ無し' % (klabel, pname)
    span = md_day(info['days'][0]) + '〜' + md_day(info['days'][-1])
    return '%s %s<br>%s' % (klabel, pname, span)


def src_label(files):
    if len(files) == 1:
        return files[0]
    return '%s〜%s（%d本）' % (files[0][:6], files[-1][:6], len(files))


def md_rt(res, log):
    """md の末尾: 電源種別別（速報・全国）の表。"""
    L = ['', '## 電源種別別（速報値・全国）', '',
         '`電源種別別/{YYYYMM}_{商品}_rt_prompt.csv`（全国だけ・速報値だけ）。'
         '電源種別は CSV の列名のまま。加重平均＝Σ(平均落札価格×落札量合計)÷Σ落札量合計'
         '（落札量0のコマは除く）、最高＝最高落札価格の期間内最大値、シェア＝その種別の'
         'Σ落札量合計÷「合計」列のΣ落札量合計。']
    for code, pname_ in PRODUCTS:
        L += ['', '### %s %s（電源種別別）' % (code, pname_), '']
        if not log[(RT_LABEL, code)]['months']:
            L.append('電源種別別のファイルが無い（`電源種別別/{YYYYMM}_%s_rt_prompt.csv` '
                     'が置かれたら次の実行で入る）。' % code)
            continue
        infos = [res[(RT_LABEL, code, p)][0] for p in ('P1', 'P2')]
        spans = []
        for p, info in zip(('P1', 'P2'), infos):
            if info['n'] == 0:
                spans.append('%s データ無し' % p)
            else:
                spans.append('%s %s〜%s（%s）' % (p, md_day(info['days'][0]),
                                                md_day(info['days'][-1]),
                                                src_label(info['files'])))
        L += ['受渡日: ' + '、'.join(spans) + '。', '']
        head = ['電源種別', '加重平均 P1', '加重平均 P2', '最高 P1', '最高 P2',
                '≧10円 P1', '≧10円 P2', '落札量シェア P1', '落札量シェア P2']
        body = []
        for j, name in enumerate(TYPES):
            r = [name]
            for key in ('wavg', 'max', 'ge', 'share'):
                for p in ('P1', 'P2'):
                    info, mets = res[(RT_LABEL, code, p)]
                    if key == 'share':
                        tot = mets[-1]['sum']['vol']
                        v = div(mets[j]['sum']['vol'], tot) if info['n'] else None
                        r.append(pct(v))
                    else:
                        r.append(md_value(key, mets[j], info))
            body.append(r)
        L += md_table(head, body)
    return L


def write_md(path, res, log, end):
    L = ['# EPRX 取引結果の集計（コラム50用）', '']
    L.append('生成 %s・`scripts/eprx/aggregate_column50.py --end %s`。'
             % (datetime.date.today().isoformat(), iso(end)))
    L.append('式・CSV の項目名・出典・取得日・規約の注意は `scripts/eprx/README.md`、'
             '丸めない値は `eprx_summary.csv`・`eprx_by_type.csv`。')
    L += ['', '- 価格は 円/kW・30分（税抜）。管区は電源属地別（電源のあるエリア）、'
          '全国は CSV の「合計」列。',
          '- 速報と確報は別々に集計した（混ぜない）。確報は「合計（確報値）」の行。',
          '- P1 = 4/1〜8/31（ΔkW 上限 15.00円）、P2 = 9/1〜%s（上限 10.00円）。' % md_day(end),
          '- 最高落札価格は CSV の表示値。上限を超える表示値（P1 は15円超、P2 は10円超）があり、'
          '精算では上限で切られる。≧10円・上限超の数と加重平均は表示値のまま。',
          '- 表の「—」はデータが無いセル。', '']
    L += ['## 受渡日の範囲', '']
    rows = []
    for _, klabel in KINDS:
        for code, _n in PRODUCTS:
            for pname in ('P1', 'P2'):
                info, _m = res[(klabel, code, pname)]
                if info['n'] == 0:
                    rows.append([klabel, code, pname, '—', '—', '0', '0', '（データ無し）', '—'])
                    continue
                rows.append([klabel, code, pname, iso(info['days'][0]), iso(info['days'][-1]),
                             str(len(info['days'])), comma(info['n']),
                             date_runs(info['missing']) or 'なし', src_label(info['files'])])
    head = ['区分', '商品', '期間', '最初', '最後', '日数', 'コマ数', '欠けている日', '元ファイル']
    L += md_table(head, rows, right=False)
    cut = ['%s %s: %s' % (k, c, date_runs(v['dropped']))
           for (k, c), v in sorted(log.items()) if v['dropped']]
    if cut:
        L += ['', '--end より後で集計に入れなかった受渡日: ' + '／'.join(cut)]
    for code, pname_ in PRODUCTS:
        L += ['', '## %s %s' % (code, pname_)]
        cols = [(k, p) for _, k in KINDS for p in ('P1', 'P2')]
        head = ['管区'] + [col_label(k, p, res[(k, code, p)][0]) for k, p in cols]
        for key, title, note in SECTIONS:
            L += ['', '### ' + title, '', note, '']
            body = []
            for j, name in enumerate(NAMES):
                r = [name]
                for k, p in cols:
                    info, mets = res[(k, code, p)]
                    r.append(md_value(key, mets[j], info))
                body.append(r)
            L += md_table(head, body)
    L += md_rt(res, log)
    L.append('')
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(L))


def run_check(root):
    """研究の1コマ実測を、集計と同じ読み取り関数で再現して照合する。"""
    path = find_files(root).get(('prompt', '1-0'), {}).get(CHECK_FILE[:6])
    if not path:
        print('検算: %s が見つからない' % CHECK_FILE)
        return 2
    meta, slots = read_csv(path)
    d = slots[CHECK_KEY]
    print('検算: %s %s（%s・%s）' % (meta['file'], CHECK_KEY, meta['label'], meta['product']))
    ok = True
    for area, f, want in CHECK_EXPECT:
        got = d[f][COLS.index(area)]
        hit = got is not None and abs(got - want) < 1e-9
        ok = ok and hit
        print('  %s | %s | 研究 %s | 読み取り %s | %s'
              % (area, meta['items'][f], want, got, '一致' if hit else '★不一致'))
    pv = sum(d['avg'][j] * d['vol'][j] for j in range(len(AREAS)))
    v = sum(d['vol'][j] for j in range(len(AREAS)))
    print('  参考: 9管区の積み上げ Σ(平均×落札量)/Σ落札量 = %r（合計列 %r）' % (pv / v, d['avg'][-1]))
    print('検算: ' + ('全部一致' if ok else '不一致あり'))
    return 0 if ok else 1


def print_log(root, end, res, log):
    print('データの根: %s　--end %s' % (root, iso(end)))
    for (klabel, code), v in sorted(log.items()):
        ms = v['months']
        span = '%s〜%s（%d本）' % (ms[0], ms[-1], len(ms)) if ms else 'ファイル無し'
        extra = '　--end で除外: %s' % date_runs(v['dropped']) if v['dropped'] else ''
        print('  %s %s: %s　使った行の「-」%d%s' % (klabel, code, span, v['dash'], extra))
    print('全国の加重平均（合計列 / 9管区の積み上げ / 差）:')
    for key in sorted(k for k in res if k[0] != RT_LABEL):
        info, mets = res[key]
        if info['n'] == 0:
            continue
        pv = sum(m['pv'] for m in mets[:len(AREAS)])
        v = sum(m['v'] for m in mets[:len(AREAS)])
        nat = mets[-1]['wavg']
        print('  %s %s %s: %.6f / %.6f / %+.6f' % (key + (nat, pv / v, nat - pv / v)))
    print('電源種別別「合計」と本表の速報・全国（Σ落札量 / 加重平均 / ≧10コマ数）:')
    for key in sorted(k for k in res if k[0] == RT_LABEL):
        info, mets = res[key]
        if info['n'] == 0:
            continue
        a, b = mets[-1], res[('速報',) + key[1:]][1][-1]
        same = (abs(a['sum']['vol'] - b['sum']['vol']) < 1e-6 and a['ge'] == b['ge']
                and abs(a['wavg'] - b['wavg']) < 1e-9)
        print('  %s %s: %.3f / %.3f | %.6f / %.6f | %d / %d | %s' % (
            key[1], key[2], a['sum']['vol'], b['sum']['vol'], a['wavg'], b['wavg'],
            a['ge'], b['ge'], '一致' if same else '★食い違い'))


def main(argv=None):
    ap = argparse.ArgumentParser(description='EPRX 取引結果CSV → コラム50 用の集計')
    ap.add_argument('data_root', nargs='?', default=DEF_ROOT, help='データの根（既定 %(default)s）')
    ap.add_argument('out_dir', nargs='?', default=DEF_OUT, help='出力先（既定 docs/research/column-50）')
    ap.add_argument('--end', default=DEF_END, help='P2 の最後の受渡日（既定 %(default)s・この日を含む）')
    ap.add_argument('--check', action='store_true', help='2026/9/1 B01 の1コマを研究の実測と照合する')
    a = ap.parse_args(argv)
    root = os.path.expanduser(a.data_root)
    if not os.path.isdir(root):
        print('データの根が無い: ' + root, file=sys.stderr)
        return 2
    if a.check:
        return run_check(root)
    end = datetime.datetime.strptime(a.end, '%Y-%m-%d').strftime('%Y%m%d')
    res, log = run_all(root, end)
    out = os.path.expanduser(a.out_dir)
    if not os.path.isdir(out):
        os.makedirs(out)
    rows, trows = csv_rows(res), rt_rows(res, log)
    write_csv(os.path.join(out, 'eprx_summary.csv'), HEAD, rows)
    write_csv(os.path.join(out, 'eprx_by_type.csv'), RT_HEAD, trows)
    write_md(os.path.join(out, 'eprx_summary.md'), res, log, end)
    print_log(root, end, res, log)
    print('出力: %s（%d行）' % (os.path.join(out, 'eprx_summary.csv'), len(rows)))
    print('出力: %s（%d行）' % (os.path.join(out, 'eprx_by_type.csv'), len(trows)))
    print('出力: %s' % os.path.join(out, 'eprx_summary.md'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except DataError as e:
        print('止めた: %s' % e, file=sys.stderr)
        sys.exit(1)
