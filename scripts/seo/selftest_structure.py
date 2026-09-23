#!/usr/bin/env python3
"""構成レビュー（guard_diff.py --profile structure・structure.py・register_structure_merges.py）を合成差分で確かめる。
週次の検査のうち「コラムは書かない＝新規ファイル 0・class=new-column は無い」（2026-09-20）もここで確かめる。
人の目が入らない分の検査（2026-09-20 のレビューで再現した抜け）もここ: 閉じタグを置き去りにした節の移動・節の削除・削除だけの差分・
ヒーローを消す CSS・noindex・既存コラムの本文の総入れ替え・ハブへの記事ぶんの書き足し・公開欄の問い合わせの件数（自然な言い回し・
週次プロファイル）・pages に入れた送客先の収益ページ・週次が差し戻した直後のハブの凍結・非公開の禁止語（O16-7・O16-12。
合成の一覧を SCIX_WEB_PRIVATE_BANNED で指す＝止める理由に語も式も出さない・一覧が読めなければ止める）。
2026-09-23 の確かめ役の指摘の分: 差し戻しは rollback_of の逆向きと確かめたときだけ凍結を外す・ハブ・トップの凍結（週次はカードの追加
だけ例外・構成レビューは差し戻し直後に止める）・英中のファンドの数字（yield・fee・收益率）と「手数料は N%」・コラムの /fund リンク
（O16-67）・英中の証券化（O16-69）・自称でない「中立」「neutral」・週次の before／after の金額・cooldown_pages(strict=True)。
同じ日の 2 回目の確かめの分: vendor-neutral・引用符でくくった自称は止める・JSON-LD だけ／焼き直しの所だけの差し戻しは凍結を外さない・
凍結中のハブの class=hub はカードの形の追加だけ・/fund の書き方（www 無し・//・相対・invest.scix.co.jp）・数字が先のファンドの数字。
4 回目の確かめの分: マニフェストに載せないハブ・トップは焼き直しだけ（凍結中・en/index.html・構成レビュー）・既にカードのあるコラムの
カードは登録漏れの手当てではない・抜粋の窓の端で切れた非公開の禁止語の残りを出さない・invest.scix.co.jp のほかのパスと vercel.json が
読めないとき・a neutral case manager・成功報酬／フィー／carry／hurdle／p.a.／年N%を目指す。
公開の手順（2 コミット・差し戻しが衝突しない・記帳の失敗と拾い直し）は selftest_publish.py、効果測定とブリーフ 8 節は selftest_ramp.py。

    python3 scripts/seo/selftest_structure.py        # 0=全部通った（--keep で一時ディレクトリを残す）

一時ディレクトリにこのリポジトリの複製（git clone --shared＝元には書かない）と空の台帳を作り、そこで
「通る例・弾く例」を1つずつ作って検査に掛ける。本物の台帳・作業ツリー・origin には触らない。
ナビの90日ルールは日付で結果が変わるので、複製の中に「今日ナビを変えた履歴」と「90日より前の履歴しか無い ref」を
作って SCIX_WEB_REF で読ませる。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent.parent
GUARD = HERE / "guard_diff.py"
REGISTER = HERE / "register_structure_merges.py"
TODAY = datetime.date.today()
results = []


def run(args, cwd, env=None, check=False):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))}: {r.stderr[:300]}")
    return r


def git(repo, *args, env=None):
    return run(["git", *args], repo, env=env, check=True).stdout.strip()


def entry(files, pages, cls, **kw):
    e = {"files": files, "pages": pages, "class": cls, "summary": "ハブのカテゴリ順を流入の多い順に",
         "rationale": "ハブ→収益・市場のコラム 120 遷移・土地・用地 55 遷移（28日・合成の数字）。並びは土地が先",
         "hypothesis": "読まれているカテゴリを先に置けばハブからコラムへの遷移が増える",
         "kpi": "ハブ → コラムの遷移（S6 のハブから）と、コラム → 収益ページの遷移",
         "measure": "マージの14日後・28日後に GA4 の遷移で比べる"}
    e.update(kw)
    return e


# 非公開の禁止語（O16-7・O16-12）の合成の一覧。本物の語は公開リポジトリに置けない＝検査は ~/.config/scix-web/private_banned.tsv を
# 読むが、selftest は SCIX_WEB_PRIVATE_BANNED でこの合成の一覧を指す（CI など本物の一覧が無い所でも同じ結果になる）
SYN_BANNED = "# 合成の一覧（selftest 専用）\nゼクシ(?:リアル|テスト)語\tSYN-1\n(?i:zxq-?value)\tSYN-2\n"
SYN_SHOWN = ("ゼクシ", "zxq", "Zxq", "(?:")   # 止める理由に出てはいけないもの（語と式）


def syn_amount(tpl, n):
    """合成の金額（selftest 専用・実データではない）を実行時に組む。公開リポジトリの本文には金額の形の文字列を置かない
    （O16-19。テストに書いてよい金額は合成の % だけ）。円の検出（公開される欄の金額・ファンドの数字の円）を確かめるためだけに使う。"""
    return tpl.format(n)


class Case:
    def __init__(self, repo, ledger, tmp):
        self.repo, self.ledger, self.tmp = repo, ledger, tmp
        self.banned = tmp / "private_banned.tsv"
        self.banned.write_text(SYN_BANNED, encoding="utf-8")

    def reset(self):
        git(self.repo, "checkout", "-q", "--", ".")
        git(self.repo, "clean", "-fdq")

    def guard(self, name, manifest, expect_ok, needle=None, profile="structure", ref=None, banned=None, forbid=()):
        mf = self.tmp / "changes.json"
        mf.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, SCIX_WEB_REPO=str(self.repo), SCIX_WEB_LEDGER=str(self.ledger),
                   SCIX_WEB_PRIVATE_BANNED=str(banned or self.banned))
        env.pop("SCIX_WEB_REF", None)
        if ref:
            env["SCIX_WEB_REF"] = ref
        r = run([sys.executable, str(GUARD), "--manifest", str(mf), "--profile", profile], self.repo, env=env)
        out = r.stdout + r.stderr
        needles = [needle] if isinstance(needle, str) else list(needle or [])   # 複数なら全部が出力に出ていること
        ok = ((r.returncode == 0) == expect_ok and all(n in out for n in needles)
              and not any(f in out for f in forbid))                             # forbid は 1 つも出ていないこと
        results.append((ok, name, "通す" if expect_ok else "止める", out.strip().splitlines()[-1][:110] if out.strip() else ""))
        if not ok:
            print(f"--- {name} の出力 ---\n{out}")
        self.reset()


def edit(repo, rel, fn):
    p = repo / rel
    s = p.read_text(encoding="utf-8")
    t = fn(s)
    assert t != s, f"{rel}: 編集が空振り"
    p.write_text(t, encoding="utf-8")


def swap_cat_blocks(s):
    """knowledge.html の cat-land と cat-market を入れ替える（並べ替えだけ＝正味の書き換え 0）。"""
    starts = [m.start() for m in re.finditer(r'<div class="cat-block[^"]*" id="cat-', s)]
    ids = re.findall(r'<div class="cat-block[^"]*" id="(cat-[a-z]+)"', s)
    i = ids.index("cat-land")
    a, b, c = starts[i], starts[i + 1], starts[i + 2]
    return s[:a] + s[b:c] + s[a:b] + s[c:]


def swap_top_sections(s):
    """index.html の #knowledge と #find を入れ替える（ヒーローより下）。"""
    m1 = re.search(r'<section class="knowledge-top" id="knowledge">.*?</section>', s, re.S)
    m2 = re.search(r'<section class="strengths" id="find">.*?</section>', s, re.S)
    assert m1 and m2 and m1.end() <= m2.start()
    return s[:m1.start()] + m2.group(0) + s[m1.end():m2.start()] + m1.group(0) + s[m2.end():]


def drop_one_funnel_link(s):
    """ハブの本文から、収益ページ（/projects）へのリンクを 1 本だけ消す（ほかは触らない）。"""
    m = re.search(r'<a\b[^>]*href="/projects"[^>]*>.*?</a>', s, re.S)
    assert m, "knowledge.html に /projects へのリンクが無い（selftest を直す）"
    return s[:m.start()] + s[m.end():]


def reroute_one_funnel_link(s):
    """収益ページへのリンクの行き先を 1 本だけ付け替える（/contact → /projects。本数は変わらない）。"""
    assert 'href="/contact"' in s, "/contact へのリンクが無い（selftest を直す）"
    return s.replace('href="/contact"', 'href="/projects"', 1)


def hero_below_next_section(s):
    """index.html のヒーローを、次の節（#knowledge）の下へ動かす（中身は 1 文字も変えない）。"""
    h = re.search(r'<section class="hero">.*?</section>', s, re.S)
    k = re.search(r'<section class="knowledge-top" id="knowledge">.*?</section>', s, re.S)
    assert h and k and h.end() <= k.start()
    return s[:h.start()] + s[h.end():k.end()] + "\n" + h.group(0) + s[k.end():]


# 登録漏れの手当て（class=hub）に使うコラム＝ファイルはあるのにハブにカードの無いコラム。main が複製の中で探して入れる
# （既にカードのあるコラムのカードは「登録漏れの手当て」ではない＝凍結中のハブでは止まる。2026-09-23 の確かめ）
CARD_COL = "/column-auction"
ZH_CARD_COL = "/zh-column-auction"
JA_CARD_RE = r'<a target="_top" href="(/column-[^"]+)" class="ac'
ZH_CARD_RE = r'<a class="kn-card" href="(/zh-column-[^"]+)"'


def uncarded_column(repo, hub, card_re, pattern):
    """ハブにカードの無い既存コラムの URL パス（名前順の最初）。"""
    carded = set(re.findall(card_re, (repo / hub).read_text(encoding="utf-8")))
    cols = sorted("/" + f.name[:-5] for f in repo.glob(pattern) if "/" + f.name[:-5] not in carded)
    assert cols, f"{hub} にカードの無いコラムが無い（selftest を直す）"
    return cols[0]


def selftest_card(href=None, ad="selftest"):
    return ('      <a target="_top" href="%s" class="ac">\n        <div class="am"><span class="an">COLUMN</span>'
            '<span class="at">selftest</span></div>\n        <h3>selftest: 登録漏れのカード</h3>\n'
            '        <p class="ad">%s</p>\n        <div class="aa">→</div>\n      </a>\n') % (href or CARD_COL, ad)


def add_card_for_existing(s, card=None):
    """ハブの cat-market の先頭に、ハブにカードの無い既存コラム（CARD_COL）のカードを 1 枚足す（週次の「登録漏れの手当て」と同じ形）。"""
    card = card or selftest_card()
    a = s.index('id="cat-market"')
    pos = s.rfind("\n", 0, a + re.search(r'<a [^>]*class="ac', s[a:]).start()) + 1
    return s[:pos] + card + s[pos:]


def add_zh_card(s):
    """中文ハブ（zh-knowledge.html）の最初の kn-card の前に、カードの無い既存の中文コラムのカードを 1 枚足す（既存のカードと同じ形）。"""
    card = ('    <a class="kn-card" href="%s">\n      <div class="kn-tag">COLUMN · selftest</div>\n'
            '      <div class="kn-title">selftest：登录遗漏的卡片</div>\n      <div class="kn-desc">selftest</div>\n    </a>\n') % ZH_CARD_COL
    i = s.index('    <a class="kn-card"')
    return s[:i] + card + s[i:]


def move_section_leaving_close(s):
    """index.html の #find を、閉じ </section> を元の場所に置き去りにして #flow の前へ動かす。行の多重集合は同じ（正味 0）だが、
    #flow 以降の節と footer が全部 #find の子になる（＝公開されると以降の見出しが紺地の白文字の規則を引き継ぐ）。"""
    L = s.splitlines(keepends=True)
    a = next(i for i, l in enumerate(L) if '<section class="strengths" id="find">' in l)
    e = next(i for i in range(a, len(L)) if L[i].strip() == "</section>")
    f = next(i for i, l in enumerate(L) if 'id="flow"' in l)
    assert a < e < f
    return "".join(L[:a] + L[e:f] + L[a:e] + L[f:])


def move_cat_block_leaving_close(s):
    """knowledge.html の cat-land を、閉じ </div> を置き去りにして cat-basics の前へ動かす。同じ div どうしなので開閉の数は
    合ったまま＝cat-basics が cat-land の子になる。"""
    L = s.splitlines(keepends=True)
    a = next(i for i, l in enumerate(L) if 'id="cat-land"' in l)
    b = next(i for i, l in enumerate(L) if 'id="cat-market"' in l)
    end = max(i for i in range(a, b) if L[i].strip() == "</div>")
    bas = next(i for i, l in enumerate(L) if 'id="cat-basics"' in l)
    assert bas < a < end < b
    return "".join(L[:bas] + L[a:end] + L[bas:a] + L[end:])


def drop_section(sid):
    def fn(s):
        m = re.search(r'<section\b[^>]*id="%s".*?</section>\n' % sid, s, re.S)
        assert m, f"#{sid} の節が無い（selftest を直す）"
        return s[:m.start()] + s[m.end():]
    return fn


def rewrite_body_text(s):
    """既存コラムの本文（<article>／<main> の中の p・h2・h3・li）と h1・title を、別の主題の文に総入れ替えする
    （タグと行数はそのまま＝行数の比率では 1 割に満たない）。"""
    n = [0]

    def repl(m):
        n[0] += 1
        return f"{m.group(1)}selftest の別の主題の文 {n[0]}。元の記事とは関係のない内容に置き換えた。{m.group(3)}"
    b = s.index("<body")
    body = re.sub(r"(<(p|h2|h3|li)\b[^>]*>)(?:(?!</\2>).)+(</\2>)", repl, s[b:], flags=re.S)
    out = s[:b] + body
    out = re.sub(r"(<h1\b[^>]*>).*?(</h1>)", r"\g<1>selftest: 別の主題の記事\g<2>", out, count=1, flags=re.S)
    return re.sub(r"<title>.*?</title>", "<title>selftest: 別の主題の記事｜ScienceX</title>", out, count=1, flags=re.S)


def add_article_section(s):
    """ハブのフッターの前に、記事 1 本ぶんの節を足す（ヒーローより下）。"""
    para = "".join(f"<p>selftest の段落 {i}。ハブの下に記事の本文を書き足している。系統用蓄電池の市場と制度についての長い説明が続く想定の文。</p>\n" for i in range(40))
    i = s.index("<footer")
    return s[:i] + '<div class="selftest-article">\n<h2>selftest: ハブに書き足した記事</h2>\n' + para + "</div>\n" + s[i:]


def nav_swap(s):
    """「買う」の引き出しの中で /projects と /transfer の順を入れ替える（ナビ定義の変更）。"""
    a = "      ['/projects', '販売中の案件一覧'],\n"
    b = "      ['/transfer', '買うまでの流れ'],\n"
    assert a + b in s, "header.js のナビ定義が想定と違う（selftest を直す）"
    return s.replace(a + b, b + a, 1)


def main() -> int:
    global CARD_COL, ZH_CARD_COL
    keep = "--keep" in sys.argv
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="scix-structure-selftest-"))
    try:
        repo, ledger = tmp / "repo", tmp / "ledger"
        (ledger / "ledger").mkdir(parents=True)
        head = git(SRC, "rev-parse", "HEAD")
        run(["git", "clone", "-q", "--shared", "--no-checkout", str(SRC), str(repo)], tmp, check=True)
        git(repo, "checkout", "-q", "--detach", head)
        git(repo, "config", "user.name", "selftest"); git(repo, "config", "user.email", "selftest@example.invalid")
        # 90日より前の履歴しか無い ref（＝直近90日のナビ変更なし）と、今日ナビを変えた ref
        old = (TODAY - datetime.timedelta(days=200)).isoformat() + "T00:00:00"
        env_old = dict(os.environ, GIT_AUTHOR_DATE=old, GIT_COMMITTER_DATE=old)
        quiet = git(repo, "commit-tree", head + "^{tree}", "-m", "selftest: 履歴の無い根", env=env_old)
        git(repo, "update-ref", "refs/heads/selftest-quiet", quiet)
        git(repo, "checkout", "-q", "-b", "selftest-navchanged", quiet)
        edit(repo, "header.js", nav_swap)
        git(repo, "commit", "-qam", "selftest: ナビを組み替えた (#999)")
        git(repo, "checkout", "-q", "--detach", quiet)
        c = Case(repo, ledger, tmp)
        CARD_COL = uncarded_column(repo, "knowledge.html", JA_CARD_RE, "column-*.html")
        ZH_CARD_COL = uncarded_column(repo, "zh-knowledge.html", ZH_CARD_RE, "zh-column-*.html")
        def hub(**kw):
            return dict(entry(["knowledge.html"], ["/knowledge"], "hub-order"), **kw)

        # ---- 通す例
        edit(repo, "knowledge.html", swap_cat_blocks)
        run([sys.executable, "scripts/gen_knowledge_jsonld.py", "--write"], repo)
        c.guard("ハブのカテゴリ順を入れ替え（並べ替えだけ）→ 経路は自動公開", {"changes": [hub()]}, True,
                ("OK（structure）", "経路: 自動公開"), ref="selftest-quiet")

        edit(repo, "index.html", swap_top_sections)
        c.guard("トップの節を入れ替え（ヒーローより下・S マーカーごと移動）",
                {"changes": [entry(["index.html"], ["/"], "top-order")]}, True, ref="selftest-quiet")
        edit(repo, "index.html", swap_top_sections)
        edit(repo, "knowledge.html", lambda s: s.replace('<div class="cat-block', '<p class="selftest"><a href="/projects">販売中の案件一覧</a></p>\n'
                                                         '<div class="cat-block', 1))
        c.guard("構成: マニフェストに載せずにハブを書き換えたら止める（焼き直しの所のほかに差分がある）",
                {"changes": [entry(["index.html"], ["/"], "top-order")]}, False, "マニフェストに載っていない変更: knowledge.html", ref="selftest-quiet")

        edit(repo, "header.js", nav_swap)
        nav = entry(["header.js"], ["/"], "nav", nav_rule={"last_nav_change": None})
        c.guard("ナビの組み替え（直近90日に変更なし・申告 null）→ 検査は通るが経路は PR", {"changes": [nav]}, True,
                ("OK（structure）", "経路: PR"), ref="selftest-quiet")

        edit(repo, "knowledge.html", swap_cat_blocks)
        run([sys.executable, "scripts/gen_knowledge_jsonld.py", "--write"], repo)
        edit(repo, "header.js", nav_swap)
        c.guard("ハブの並べ替え＋ナビの組み替え → その回は全体が PR（一部だけ公開、をしない）", {"changes": [hub(), nav]}, True,
                "経路: PR", ref="selftest-quiet")

        # ---- 収益ページ・フォームへの導線の本数（人の目が入らない分、流れを変える変更が導線を消す事故を止める）
        edit(repo, "knowledge.html", drop_one_funnel_link)
        c.guard("収益ページ（/projects）へのリンクを 1 本消した", {"changes": [dict(hub(), **{"class": "funnel-block"})]}, False,
                ("導線が減っている", "/projects"), ref="selftest-quiet")
        edit(repo, "knowledge.html", lambda s: s.replace('href="/projects"', 'href="/knowledge"', 1))
        c.guard("収益ページへのリンクを、収益ページでない行き先に付け替えた（＝1 本減った）", {"changes": [dict(hub(), **{"class": "funnel-block"})]},
                False, "導線が減っている", ref="selftest-quiet")
        edit(repo, "knowledge.html", reroute_one_funnel_link)
        c.guard("行き先の付け替え（/contact → /projects・本数は同じ）は通す", {"changes": [dict(hub(), **{"class": "funnel-block"})]}, True,
                "経路: 自動公開", ref="selftest-quiet")
        edit(repo, "knowledge.html", lambda s: s.replace('</body>', '<p><a href="/investors?ref=hub#top">投資家の方へ</a></p>\n</body>', 1))
        c.guard("導線を 1 本足す（?query・#hash つきでも数える）", {"changes": [dict(hub(), **{"class": "funnel-block"})]}, True,
                "収益ページとフォームへの導線", ref="selftest-quiet")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("hypothesis（仮説）が無い", {"changes": [hub(hypothesis="")]}, False, "hypothesis が無い")

        # ---- 弾く例: ナビ
        edit(repo, "header.js", nav_swap)
        c.guard("ナビの組み替え（履歴に今日のナビ変更あり）", {"changes": [nav]}, False, "日に1回まで", ref="selftest-navchanged")

        edit(repo, "header.js", nav_swap)
        c.guard("ナビの組み替え（申告なし）", {"changes": [entry(["header.js"], ["/"], "nav")]}, False,
                "nav_rule.last_nav_change の申告が無い", ref="selftest-quiet")

        edit(repo, "header.js", nav_swap)
        c.guard("ナビの組み替え（class=nav のエントリなし）", {"changes": [hub(files=["header.js"])]}, False,
                "class=nav", ref="selftest-quiet")

        led = ledger / "ledger" / "changes.jsonl"
        d30 = str(TODAY - datetime.timedelta(days=30))
        led.write_text(json.dumps({"id": "structure-x-1", "date": d30, "class": "nav", "pages": ["/"],
                                   "summary": "ナビ変更", "nav_change": True}, ensure_ascii=False) + "\n", encoding="utf-8")
        edit(repo, "header.js", nav_swap)
        c.guard("ナビの組み替え（変更台帳に30日前のナビ変更・申告は null）", {"changes": [nav]}, False,
                "申告が台帳と合わない", ref="selftest-quiet")
        led.unlink()

        edit(repo, "header.js", lambda s: s.replace(".scix-nav-dd{position:relative;", ".scix-nav-dd{position:static;", 1))
        c.guard("header.js の CSS を変更", {"changes": [nav]}, False, "ナビ定義と JA_ONLY_COLUMNS 以外", ref="selftest-quiet")

        edit(repo, "header.js", nav_swap)
        c.guard("週次プロファイルでナビを変更", {"changes": [dict(hub(files=["header.js"]), **{"class": "hub"})]}, False,
                "JA_ONLY_COLUMNS の行しか", profile="weekly")

        # ---- 弾く例: ヒーロー・S マーカー・量
        edit(repo, "index.html", lambda s: s.replace('<div class="hero-label">', '<div class="hero-label">NEW ', 1))
        c.guard("トップのヒーローを書き換え", {"changes": [entry(["index.html"], ["/"], "top-order")]}, False, "ヒーローより上は変えない")

        edit(repo, "index.html", lambda s: s.replace('<div class="hero-label">', '<div class="hero-label">NEW ', 1))
        c.guard("週次プロファイルでもトップのヒーローは弾く", {"changes": [dict(entry(["index.html"], ["/"], "hub"))]}, False,
                "ヒーローより上は変えない", profile="weekly")

        edit(repo, "index.html", hero_below_next_section)
        c.guard("トップのヒーローを次の節の下へ動かした（中身は同じ）", {"changes": [entry(["index.html"], ["/"], "top-order")]}, False,
                "ヒーローより上は変えない")

        edit(repo, "knowledge.html", lambda s: s.replace("<h1>系統用蓄電池のナレッジ</h1>", "<h1>蓄電池のナレッジ集</h1>", 1))
        c.guard("ハブの h1 を書き換え", {"changes": [hub()]}, False, "ヒーローより上は変えない")

        edit(repo, "index.html", lambda s: re.sub(r"(<!--S:shv-->)\d+", r"\g<1>99", s, count=1))
        c.guard("S マーカーの中身を書き換え", {"changes": [entry(["index.html"], ["/"], "top-order")]}, False, "<!--S:")

        def rewrite(s):
            lines = s.splitlines()
            a = next(i for i, l in enumerate(lines) if 'id="cat-land"' in l)
            for i in range(a, a + int(len(lines) * 0.2)):
                if lines[i].strip() and "<!--" not in lines[i]:
                    lines[i] = lines[i] + " "  # 行は同じでも strip で同一になるので中身を変える
                    lines[i] = lines[i].replace("蓄電", "蓄 電") if "蓄電" in lines[i] else lines[i].rstrip() + "<!-- x%d -->" % i
            return "\n".join(lines) + "\n"
        edit(repo, "knowledge.html", rewrite)
        c.guard("ハブを正味で大きく書き換え", {"changes": [hub()]}, False, "正味の書き換えが大きすぎる")

        edit(repo, "knowledge.html", lambda s: re.sub(r"<title>.*?</title>", "<title>ナレッジ一覧｜ScienceX</title>", s, count=1, flags=re.S))
        c.guard("ハブの title を変更", {"changes": [hub()]}, False, "title／description／canonical を変えない")

        (repo / "column-selftest.html").write_text((repo / "column-trading.html").read_text(encoding="utf-8"), encoding="utf-8")
        c.guard("新規ファイル", {"changes": [entry(["column-selftest.html"], ["/column-selftest"], "funnel-block")]}, False,
                "新しいページは自動では作らない")

        # ---- 人の目が入らない分の検査（2026-09-20 のレビューで再現した抜け）
        #   HTML の入れ子: 行の多重集合は同じでも、閉じタグを置き去りにすると以降の節が全部その節の子になる
        top = entry(["index.html"], ["/"], "top-order")
        edit(repo, "index.html", move_section_leaving_close)
        c.guard("トップの節を、閉じ </section> を置き去りにして動かした（行の集合は同じ）", {"changes": [top]}, False,
                ("タグの開閉が合わない箇所が増えた", "入れ子の位置が変わった", "#flow"))
        edit(repo, "knowledge.html", move_cat_block_leaving_close)
        c.guard("ハブのカテゴリを、閉じ </div> を置き去りにして動かした（開閉の数は合ったまま）", {"changes": [hub()]}, False,
                ("入れ子の位置が変わった", "#cat-basics"))
        edit(repo, "index.html", drop_section("position"))
        c.guard("トップの節を丸ごと消した（導線リンクの無い節・削除は 15% 以内）", {"changes": [top]}, False, ("id つきの要素が消えた", "#position"))
        edit(repo, "index.html", move_section_leaving_close)
        c.guard("週次プロファイルでも、閉じタグの置き去りは止める", {"changes": [dict(top, **{"class": "hub"})]}, False,
                "タグの開閉が合わない箇所が増えた", profile="weekly")
        #   削除だけの差分（「変更なし」で素通りしていた）
        for prof in ("weekly", "structure"):
            (repo / "column-noise.html").unlink()
            c.guard(f"{prof}: ファイルの削除だけの差分は止める（「変更なし」で通さない）", {"changes": []}, False, "削除は禁止: column-noise.html", profile=prof)
        #   ヒーローを CSS で消す・noindex を足す（<body> のヒーローの中身は同じ）
        def hide_hero(s):
            i = s.index("</style>")
            return s[:i] + ".hero{display:none}\n" + s[i:]
        edit(repo, "index.html", hide_hero)
        c.guard("トップの <style> にヒーローを消す規則を足した", {"changes": [top]}, False, "<style> と <script>")
        edit(repo, "index.html", hide_hero)
        c.guard("週次プロファイルでも、トップの <style> は変えさせない", {"changes": [dict(top, **{"class": "hub"})]}, False,
                "<style> と <script>", profile="weekly")
        noindex = lambda s: s.replace("</head>", '<meta name="robots" content="noindex,nofollow">\n</head>', 1)  # noqa: E731
        edit(repo, "knowledge.html", noindex)
        c.guard("ハブに robots noindex を足した", {"changes": [hub()]}, False, "noindex を足さない")
        edit(repo, "column-auction.html", noindex)
        c.guard("週次: コラムに robots noindex を足した", {"changes": [dict(entry(["column-auction.html"], ["/column-auction"], "body"))]}, False,
                "noindex を足さない", profile="weekly")
        edit(repo, "knowledge.html", lambda s: s.replace('<link rel="alternate" hreflang="en"', '<link rel="alternate" hreflang="en-US"', 1))
        c.guard("ハブの <head> の hreflang を書き換えた", {"changes": [hub()]}, False, "<head>（meta・link・hreflang・og）を変えない")
        #   既存コラムの本文の総入れ替え（行数では 1 割未満＝「コラムは書かない」の抜け道だった）
        col = "column-somosomo-19.html"
        edit(repo, col, rewrite_body_text)
        c.guard("週次: 既存コラムの本文・h1・title を別の主題に総入れ替え（class=body）", {"changes": [entry([col], ["/" + col[:-5]], "body")]}, False,
                ("本文の書き換えが大きすぎる", "本文の削除・書き換えが多すぎる"), profile="weekly")
        edit(repo, col, rewrite_body_text)
        c.guard("構成: 同じ総入れ替えを class=cta-route と申告", {"changes": [entry([col], ["/" + col[:-5]], "cta-route")]}, False,
                ("本文の正味の書き換えが大きすぎる", "title／description／h1 を変えない"))
        edit(repo, col, lambda s: re.sub(r"(<h1\b[^>]*>).*?(</h1>)", r"\g<1>selftest: 見出しだけ変えた\g<2>", s, count=1, flags=re.S))
        c.guard("構成: コラムの h1 だけを書き換え（cta-route は本文を書き換えない型）", {"changes": [entry([col], ["/" + col[:-5]], "cta-route")]}, False,
                "title／description／h1 を変えない")
        edit(repo, "knowledge.html", add_article_section)
        c.guard("週次: ハブに記事ぶんの節を足し、マニフェストは 0 件", {"changes": [], "no_change_reason": "x"}, False,
                "マニフェストに載っていないのに本文が変わっている", profile="weekly")
        edit(repo, "knowledge.html", add_article_section)
        c.guard("週次: ハブに記事ぶんの節を足した（files に書いても量で止める）", {"changes": [dict(hub(), **{"class": "hub"})]}, False,
                "ハブ・トップに足した本文が多すぎる", profile="weekly")
        #   差し戻し（class=rollback）: 元の commit（rollback_of）の逆向きと確かめられたファイルだけ、凍結を外し・足した節を消してよい
        edit(repo, "land.html", drop_section("representative"))
        c.guard("週次: id つきの節を消した（class=body）", {"changes": [entry(["land.html"], ["/land"], "body")]}, False,
                "id つきの要素が消えた", profile="weekly")
        rb_sec = '<section class="section" id="selftest-rb">\n<h2>selftest: 足した節</h2>\n<p>selftest の節の本文。</p>\n</section>\n'
        edit(repo, "land.html", lambda s: s[:s.index("<footer")] + rb_sec + s[s.index("<footer"):])
        git(repo, "commit", "-qam", "feat(land): selftest の節を足した（元の commit＝今日＝land.html は 14 日凍結）")
        rb_sha = git(repo, "rev-parse", "HEAD")
        undo_rb = lambda s: s.replace(rb_sec, "", 1)  # noqa: E731
        def rb(**kw):
            return {"changes": [entry(["land.html"], ["/land"], "rollback", **kw)]}
        edit(repo, "land.html", undo_rb)
        c.guard("週次: 元の commit の逆向きと確かめられた差し戻しは、凍結中でも・足した節を消しても通す", rb(rollback_of=rb_sha[:10]), True,
                profile="weekly")
        edit(repo, "land.html", undo_rb)
        c.guard("週次: rollback_of の無い差し戻しは止める", rb(), False, "rollback_of（戻す元の commit）が要る", profile="weekly")
        edit(repo, "land.html", lambda s: s.replace("</body>", '<p><a href="/projects">販売中の案件一覧</a></p>\n</body>', 1))
        c.guard("週次: 凍結中のページへの普通の手直しを rollback と申告しても、逆向きと確かめられなければ凍結で止める", rb(rollback_of=rb_sha),
                False, ("/land: 14日以内に変えたページは変えない", "逆向きの差分と確かめられない"), profile="weekly")
        edit(repo, "land.html", drop_section("representative"))
        c.guard("週次: 元の commit が足していない節を rollback で消したら止める（凍結・節の削除）", rb(rollback_of=rb_sha), False,
                ("/land: 14日以内に変えたページは変えない", "id つきの要素が消えた"), profile="weekly")
        edit(repo, "land.html", undo_rb)
        c.guard("週次: rollback_of が HEAD の履歴に無い commit なら確かめられない＝凍結で止める", rb(rollback_of="0123456789abcdef"), False,
                ("/land: 14日以内に変えたページは変えない", "class=rollback だが"), profile="weekly")
        #   JSON-LD だけ・焼き直しの所だけの書き換えを rollback と申告しても、凍結を外さない（2026-09-23 の確かめ #78）
        edit(repo, "land.html", lambda s: s.replace('"description": "', '"description": "selftest: ', 1))
        c.guard("週次: 凍結中のコラムの JSON-LD だけを rollback と申告して書き換えたら凍結で止める（コラムは JSON-LD も比べる）",
                rb(rollback_of=rb_sha), False, ("/land: 14日以内に変えたページは変えない", "逆向きの差分と確かめられない"), profile="weekly")
        edit(repo, "knowledge.html", add_card_for_existing)
        git(repo, "commit", "-qam", "feat(knowledge): selftest のカードを足した（元の commit＝今日＝/knowledge は 14 日凍結）")
        kb_sha = git(repo, "rev-parse", "HEAD")
        def rbk(**kw):
            return {"changes": [entry(["knowledge.html"], ["/knowledge"], "rollback", **kw)]}
        edit(repo, "knowledge.html", lambda s: s.replace('<span class="new">NEW</span>', "", 1))
        c.guard("週次: ハブの NEW バッジだけ（焼き直しの所だけ）を rollback と申告しても、差分が空＝確かめられない＝凍結で止める",
                rbk(rollback_of=kb_sha), False, ("/knowledge: 14日以内に変えたページは変えない", "焼き直しの所"), profile="weekly")
        edit(repo, "knowledge.html", lambda s: s.replace(selftest_card(), "", 1))
        c.guard("週次: ハブに足したカードを抜く差し戻し（元の commit の逆向き）は、凍結中でも通す", rbk(rollback_of=kb_sha), True,
                profile="weekly")
        git(repo, "checkout", "-q", "--detach", quiet)
        #   pages は編集したページだけ（送客先の収益ページは kpi_pages）
        edit(repo, "knowledge.html", reroute_one_funnel_link)
        c.guard("pages に、編集していない送客先の収益ページを入れた",
                {"changes": [dict(hub(pages=["/knowledge", "/investors"]), **{"class": "funnel-block"})]}, False,
                ("pages は編集したページ", "/investors", "kpi_pages"))
        edit(repo, "knowledge.html", reroute_one_funnel_link)
        c.guard("送客先は kpi_pages に書けば通す", {"changes": [dict(hub(kpi_pages=["/investors", "/projects"]), **{"class": "funnel-block"})]},
                True, "経路: 自動公開", ref="selftest-quiet")
        edit(repo, "knowledge.html", reroute_one_funnel_link)
        c.guard("kpi_pages が URL パスでない", {"changes": [dict(hub(kpi_pages="/investors"), **{"class": "funnel-block"})]}, False, "kpi_pages は URL パス")

        # ---- 弾く例: マニフェスト
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("マニフェスト 4 件", {"changes": [hub(), hub(), hub(), hub()]}, False, "3 件まで")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("measure が無い", {"changes": [hub(measure="")]}, False, "measure が無い")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("rationale に数字が無い", {"changes": [hub(rationale="読まれているカテゴリを先に")]}, False, "根拠の数字が無い")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("公開欄に問い合わせの件数", {"changes": [hub(rationale="28日のリード 6 件のうちコラム着地は 1 件")]}, False, "問い合わせの件数")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("週次の class（title）は構成レビューでは使えない", {"changes": [dict(hub(), **{"class": "title"})]}, False, "class が想定外")

        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("公開欄（PR の題 proposal_title）に問い合わせの件数",
                {"proposal_title": "問い合わせ 6 件のうちハブ経由 4 件 → ハブの並びを変える", "changes": [hub()]}, False, "proposal_title")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("公開欄（before／after）に問い合わせの件数", {"changes": [hub(before="問い合わせ 6 件", after="リード数 9")]}, False, "after に問い合わせの件数")
        #   ブリーフ自身の言い回し（括弧・「前→後」が挟まる形・数字が先の形・語彙）。どれも以前は素通しした。数字はどれも合成（実データではない）
        leaks = [("rationale", "S2 の遷移 40。問い合わせ（generate_lead）は 28 日で 3 件、うちハブ着地は 1 件"),
                 ("kpi", "フォーム送信が 28 日で 3 件 → 5 件"), ("hypothesis", "3 件の問い合わせが 5 件に増える"),
                 ("measure", "リード前 1 → 後 3 を 14 日後に確かめる"), ("summary", "CV 3 件のページを先頭へ")]
        for k, v in leaks:
            edit(repo, "knowledge.html", swap_cat_blocks)
            c.guard(f"公開欄（{k}）に問い合わせの件数: {v[:24]}…", {"changes": [hub(**{k: v})]}, False, f"{k} に問い合わせの件数")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("公開欄（summary_lines）に「着地リード 前→後 は 2→0」", {"summary_lines": ["着地リード 前→後 は 2→0 のページを先頭へ"], "changes": [hub()]},
                False, "summary_lines: 問い合わせの件数")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("件数でない数字（日付・遷移・リードタイム）は止めない",
                {"summary_lines": ["効果は 14 日後・28 日後の CTR と着地リードで見る"],
                 "changes": [hub(kpi="ハブ → コラムの遷移と、GA4 の着地→generate_lead", measure="着地リードを 14 日後・28 日後に見る",
                                 summary="連系のリードタイム 18→12 か月の説明があるカテゴリを先に")]}, True, ref="selftest-quiet")
        #   週次プロファイルでも同じ検査（構成の変更の差し戻しの根拠は「着地リード 前→後」の表＝週次の公開欄に写りやすい）
        edit(repo, "column-auction.html", lambda s: s.replace("</body>", '<p><a href="/projects">販売中の案件一覧</a></p>\n</body>', 1))
        rb = entry(["column-auction.html"], ["/column-auction"], "rollback", rationale="構成の変更が worse。着地リード 9→0・問い合わせ 9 件が 0 件に")
        c.guard("週次: 差し戻しの根拠に問い合わせの件数を書いた", {"summary_lines": ["着地リード 9→0 の変更を戻した"], "changes": [rb]}, False,
                ("summary_lines: 問い合わせの件数", "rationale に問い合わせの件数"), profile="weekly")
        # 提案なし（changes: []）なのに焼き直しの差分だけが残っている → 中身のない PR を出さない
        edit(repo, "knowledge.html", lambda s: s.replace(' is-new"', '"', 1).replace('<span class="new">NEW</span>', "", 1))
        c.guard("マニフェスト 0 件なのに差分（焼き直しだけ）", {"changes": [], "no_change_reason": "根拠が弱い"}, False, "changes が 0 件なのに差分がある")

        # ---- 週次プロファイル: pages は必須（空のまま台帳に入ると 14 日後の立ち上がり判定の対象が無い）
        def weekly_entry(files, pages, cls="internal-link"):
            e = entry(files, pages, cls); e.pop("measure", None)
            return e
        def link(s):   # 本文の末尾に内部リンクを 1 本足す（週次の internal-link と同じ形の小さな変更）
            return s.replace("</body>", '<p><a href="/projects">販売中の案件一覧</a></p>\n</body>', 1)
        edit(repo, "column-auction.html", link)
        c.guard("週次: pages が無いマニフェストは止める", {"changes": [weekly_entry(["column-auction.html"], [])]}, False, "pages が無い", profile="weekly")
        edit(repo, "column-auction.html", link)
        c.guard("週次: pages が URL パスでない", {"changes": [weekly_entry(["column-auction.html"], ["https://www.scix.co.jp/column-auction"])]},
                False, "pages は URL パス", profile="weekly")
        edit(repo, "column-auction.html", link)
        c.guard("週次: pages があれば通す", {"changes": [weekly_entry(["column-auction.html"], ["/column-auction"])]}, True, profile="weekly")

        # ---- 凍結: ハブ・トップ（O16-38 の例外はカードの追加だけ）・構成レビューの差し戻し直後のハブ
        def led_put(*rows):
            led.write_text("".join(json.dumps(dict({"source": "auto", "date": str(TODAY), "summary": "selftest"}, **r), ensure_ascii=False) + "\n"
                                   for r in rows), encoding="utf-8")
        led_put({"id": "w-rollback", "class": "rollback", "pages": ["/knowledge"]})
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("構成: 週次が差し戻した直後（台帳に class=rollback）のハブの hub-order は凍結で止める", {"changes": [hub()]}, False,
                "/knowledge: 14日以内に変えたページは変えない", ref="selftest-quiet")
        led_put({"id": "w-title", "class": "title", "pages": ["/knowledge"]})
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("構成: 台帳の title の変更ではハブを凍結しない＝hub-order は通す（コラムを足しただけの週と同じ）", {"changes": [hub()]}, True,
                "経路: 自動公開", ref="selftest-quiet")
        led_put({"id": "w-t2", "class": "title", "pages": ["/", "/knowledge", "/zh-knowledge"]})   # 週次の数え方では /・/knowledge・/zh-knowledge が凍結中
        top_title = lambda s: re.sub(r"<title>.*?</title>", "<title>selftest: トップの title を書き換えた｜ScienceX</title>", s, count=1, flags=re.S)  # noqa: E731
        edit(repo, "index.html", top_title)
        c.guard("週次: 凍結中のトップの title を class=title で変えたら凍結で止める", {"changes": [weekly_entry(["index.html"], ["/"], "title")]},
                False, "/: 14日以内に変えたページは変えない", profile="weekly")
        edit(repo, "index.html", top_title)
        c.guard("週次: 凍結中のトップの title を class=hub と申告しても、<head> を変えたら止める", {"changes": [weekly_entry(["index.html"], ["/"], "hub")]},
                False, "カードの追加（class=hub）でも title", profile="weekly")
        edit(repo, "index.html", top_title)
        c.guard("週次: マニフェストに載せずにトップの title を変えたら止める", {"changes": [], "no_change_reason": "x"}, False,
                "マニフェストに載っていないのに title", profile="weekly")
        edit(repo, "knowledge.html", add_card_for_existing)
        c.guard("週次: 凍結中のハブでも、カードの追加（class=hub）は O16-38 の例外として通す",
                {"changes": [weekly_entry(["knowledge.html"], ["/column-auction"], "hub")]}, True, profile="weekly")
        edit(repo, "knowledge.html", add_card_for_existing)
        c.guard("週次: 凍結中のハブへの内部リンク（class=internal-link）は凍結で止める",
                {"changes": [weekly_entry(["knowledge.html"], ["/column-auction"], "internal-link")]}, False,
                "/knowledge: 14日以内に変えたページは変えない", profile="weekly")
        #   class=hub と申告しても、足した行がカードの形でなければ凍結を当てる（2026-09-23 の確かめ #66: 申告した class だけで抜けていた）
        hubk = {"changes": [weekly_entry(["knowledge.html"], ["/knowledge"], "hub")]}
        edit(repo, "knowledge.html", lambda s: s.replace('<div class="cat-block', '<p class="selftest"><a href="/projects">販売中の案件一覧</a></p>\n'
                                                         '<div class="cat-block', 1))
        c.guard("週次: 凍結中のハブに、カードでない段落（/projects へのリンク）を class=hub と申告して足したら凍結で止める", hubk, False,
                ("/knowledge: 14日以内に変えたページは変えない", "カードの追加だけ"), profile="weekly")
        edit(repo, "knowledge.html", lambda s: add_card_for_existing(s, selftest_card("/projects")))
        c.guard("週次: 凍結中のハブに、カードの形でも行き先がコラムでないもの（/projects）を class=hub で足したら凍結で止める", hubk, False,
                "カードの追加だけ", profile="weekly")
        edit(repo, "knowledge.html", lambda s: add_card_for_existing(s, selftest_card(ad="selftest <strong>販売中</strong>")))
        c.guard("週次: 凍結中のハブに、既存のカードと要素が違うカード（中に strong）を class=hub で足したら凍結で止める", hubk, False,
                "カードの追加だけ", profile="weekly")
        edit(repo, "knowledge.html", lambda s: add_card_for_existing(s).replace("<h3>", "<h3>selftest: ", 1))
        c.guard("週次: 凍結中のハブに、カードの追加と既存のカードの見出しの書き換えを class=hub で混ぜたら凍結で止める", hubk, False,
                "カードの追加だけ", profile="weekly")
        edit(repo, "zh-knowledge.html", add_zh_card)
        c.guard("週次: 凍結中の中文ハブでも、既存のカードと同じ形（kn-card）のカードの追加は通す",
                {"changes": [weekly_entry(["zh-knowledge.html"], [ZH_CARD_COL], "hub")]}, True, profile="weekly")
        #   足したカードのコラムが、変更前のハブに既にカードのあるコラムなら止める（2026-09-23 の確かめ #66 の残り: 既存のカードを
        #   複製して宣伝文に書き換えたカードが通った）。同じコラムのカードを 2 枚足すのも止める
        carded_col = re.search(JA_CARD_RE, (repo / "knowledge.html").read_text(encoding="utf-8")).group(1)
        edit(repo, "knowledge.html", lambda s: add_card_for_existing(s, selftest_card(carded_col, "selftest: 販売中の案件は一覧から")))
        c.guard("週次: 凍結中のハブに、既にカードのあるコラムのカード（宣伝文）を class=hub で足したら凍結で止める", hubk, False,
                ("/knowledge: 14日以内に変えたページは変えない", "既にカードのあるコラム"), profile="weekly")
        edit(repo, "knowledge.html", lambda s: add_card_for_existing(add_card_for_existing(s), selftest_card(ad="selftest 2")))
        c.guard("週次: 凍結中のハブに、同じコラムのカードを 2 枚、class=hub で足したら凍結で止める", hubk, False,
                "カードの追加だけ", profile="weekly")
        #   マニフェストに載せないハブ・トップの書き換え（2026-09-23 の確かめ #66: 申告しないだけで凍結を抜けられた）
        en_only = {"changes": [weekly_entry(["en/column-auction.html"], ["/en/column-auction"])]}
        edit(repo, "knowledge.html", lambda s: s.replace('<div class="cat-block', '<p class="selftest"><a href="/projects">販売中の案件一覧</a></p>\n'
                                                         '<div class="cat-block', 1))
        edit(repo, "en/column-auction.html", link)
        c.guard("週次: 凍結中のハブをマニフェストに載せずに書き換えたら（焼き直しでない差分）凍結で止める", en_only, False,
                ("/knowledge: 14日以内に変えたページは変えない", "マニフェストに載せずに"), profile="weekly")
        edit(repo, "knowledge.html", add_card_for_existing)
        edit(repo, "en/column-auction.html", link)
        c.guard("週次: 凍結中のハブへのカードの追加も、マニフェストに載せなければ止める（class=hub で files に書く）", en_only, False,
                ("/knowledge: 14日以内に変えたページは変えない", "class=hub で files に書く"), profile="weekly")
        edit(repo, "knowledge.html", lambda s: s.replace(' is-new"', '"', 1).replace('<span class="new">NEW</span>', "", 1))
        edit(repo, "en/column-auction.html", link)
        c.guard("週次: 凍結中のハブでも、焼き直しの所だけ（NEW バッジ落ち）ならマニフェストに載せなくても通す", en_only, True, profile="weekly")
        edit(repo, "en/index.html", lambda s: s.replace("<footer", '<p class="selftest"><a href="/en/contact">Contact</a></p>\n<footer', 1))
        edit(repo, "en/column-auction.html", link)
        c.guard("週次: 焼き直しが書かないトップ（en/index.html）の書き換えは、凍結の外でもマニフェストに無ければ止める", en_only, False,
                "マニフェストに載っていない変更: en/index.html", profile="weekly")
        led.unlink()

        # ---- O16-8・O16-66: ファンドの数字（英中の yield・fee と「手数料は N%」も）。既存の文を動かしただけなら止めない
        def add_p(t):
            return lambda s: s.replace("</body>", f"<p>{t}</p>\n</body>", 1)
        def wk1(f, **kw):
            return {"changes": [dict(weekly_entry([f], ["/" + f[:-5]]), **kw)]}
        edit(repo, "en/column-auction.html", add_p("selftest: projects of this kind yield 8% annually; fee 3%."))
        c.guard("週次: EN に yield N%・fee N% を足したら止める", wk1("en/column-auction.html"), False, ("O16-8", "yield 8%", "fee 3%"), profile="weekly")
        edit(repo, "column-auction.html", add_p("selftest の手数料は売買価格の 9% とする。selftest の出資額の 7% を分配する。"))
        c.guard("週次: 「手数料は N%」「N% を分配」を足したら止める（出資額も語に入れた＝「出資額の N%」で拾う）", wk1("column-auction.html"), False,
                ("手数料は売買価格の 9%", "出資額の 7%"),
                profile="weekly")
        edit(repo, "zh-column-auction.html", add_p("selftest：内部收益率8%，手续费 3%。"))
        c.guard("週次: ZH に收益率・手续费の数字を足したら止める", wk1("zh-column-auction.html"), False, ("收益率8%", "手续费 3%"), profile="weekly")
        sys.path.insert(0, str(HERE))
        import guard_diff as gd  # noqa: PLC0415 — 式だけ使う
        mv = None
        for f in sorted(repo.glob("column-*.html")):
            L = f.read_text(encoding="utf-8").splitlines(keepends=True)
            i = next((i for i, l in enumerate(L) if gd.FUND_NUM_RE.search(l) and re.fullmatch(r"\s*<p>.*</p>\s*", l) and l.count("<p") == 1), None)
            if i is not None:
                mv = (f.name, L[i])
                break
        assert mv, "ファンドの数字を含む <p> の行が既存コラムに無い（selftest を直す）"
        edit(repo, mv[0], lambda s: s.replace(mv[1], "", 1).replace("</body>", mv[1] + "</body>", 1))
        c.guard("週次: 既存のファンドの数字の文を動かしただけなら通す（ページ全体の出現の前後で比べる）", wk1(mv[0]), True, profile="weekly")
        #   数字が先に来る形と言い換え（2026-09-23 の確かめ #64）。合成の文だけ（実データではない）
        fund_pos = ["3%の手数料", "a 3% fee", "3% management fee", "8% annual return", "年利5%", "期待リターン8%", syn_amount("募集金額{}億円", 10),
                    syn_amount("最低出資額 {}万円", 100), syn_amount("Minimum investment of JPY {} million", 10), "dividend of 5%", "分红率5%", "年化收益8%", "利益の 7% を分配",
                    # 2026-09-23 の 4 回目の確かめの言い換え（成功報酬・フィー・carry・carried interest・hurdle・p.a.・年N%を目指す）
                    "成功報酬 3%", "3%のフィー", "carry of 20%", "20% carried interest", "hurdle rate of 8%", "5% p.a. return", "年8%を目指す"]
        miss = [x for x in fund_pos if not gd.FUND_NUM_RE.search(x)]
        results.append((not miss, "式: 数字が先の形・言い換え（手数料・fee・return・年利・リターン・募集金額・出資額・minimum investment・dividend・分红・年化・"
                        "成功報酬・フィー・carry・hurdle・p.a.・年N%を目指す）を拾う",
                        "式", f"拾えなかった {miss}" if miss else f"{len(fund_pos)} 文とも拾う"))
        fund_neg = ["SOC 90%", "上位 3% のコラム", "3% of capacity", "効率は 85%", "出力の 3% を失う", "distribution losses of 5%",
                    "地価が5%上昇", "劣化率 2%/年", "2% p.a. degradation", "FIP（フィードインプレミアム）の上乗せは 3%", "lines carry 5% of flows",
                    "年3%の成長を見込む"]
        hits = [x for x in fund_neg if gd.FUND_NUM_RE.search(x)]
        results.append((not hits, "式: ファンドでない数字（SOC・効率・上位 N%・capacity・地価・劣化・フィードイン・carry N% of flows）は拾わない",
                        "式", f"拾った {hits}" if hits else ""))
        edit(repo, "en/column-auction.html", add_p("selftest: a 3% management fee and an 8% annual return; " + syn_amount("minimum investment of JPY {} million.", 10)))
        c.guard("週次: EN に数字が先の fee・return と minimum investment を足したら止める", wk1("en/column-auction.html"), False,
                ("O16-8", "3% management fee", "8% annual return", syn_amount("JPY {}", 10)), profile="weekly")
        edit(repo, "column-auction.html", add_p("selftest の年利5%、期待リターン8%、3%の手数料。"))
        c.guard("週次: JA に年利・リターン・「N%の手数料」を足したら止める", wk1("column-auction.html"), False,
                ("年利5%", "リターン8%", "3%の手数料"), profile="weekly")

        # ---- O16-67: コラムから /fund へ導線を張らない／O16-69: 英語・中文のページに証券化（GK-TK）を載せない
        edit(repo, "en/column-auction.html", add_p('<a href="/fund">Fund</a>'))
        c.guard("週次: EN コラムに /fund へのリンクを足したら止める（O16-67）", wk1("en/column-auction.html"), False, ("O16-67", "/fund を指すリンク"), profile="weekly")
        edit(repo, "column-auction.html", add_p('<a href="https://www.scix.co.jp/fund?ref=col">ファンドの案内</a>'))
        c.guard("週次: JA コラムでも /fund（絶対 URL・?query つき）へのリンクを足したら止める", wk1("column-auction.html"), False,
                "/fund を指すリンク", profile="weekly")
        #   www 無し・//・相対・invest.scix.co.jp（vercel.json の rewrites で /fund）も同じ /fund に数える（2026-09-23 の確かめ #70）
        for href, f in (("https://scix.co.jp/fund", "en/column-auction.html"), ("//www.scix.co.jp/fund", "column-auction.html"),
                        ("fund.html", "column-auction.html"), ("../fund", "en/column-auction.html"),
                        ("https://invest.scix.co.jp/", "zh-column-auction.html"),
                        # host の rewrites に出るホストは、rewrite の無いパスも自サイト（2026-09-23 の 4 回目の確かめ #70 の残り）
                        ("https://invest.scix.co.jp/fund", "en/column-auction.html"), ("https://invest.scix.co.jp/fund.html", "column-auction.html")):
            edit(repo, f, add_p(f'<a href="{href}">selftest</a>'))
            c.guard(f"週次: コラムから /fund への導線は書き方を変えても止める（{href}・{f}）", wk1(f), False,
                    ("O16-67", "/fund を指すリンク"), profile="weekly")
        edit(repo, "column-auction.html", add_p('<a href="https://www.example.com/fund/detail/1">selftest の外部</a>'))
        c.guard("週次: 外のサイトの /fund（別のドメイン）は数えない（通す）", wk1("column-auction.html"), True, profile="weekly")
        #   vercel.json が読めなければ止める（空で続けるとリダイレクトと invest 経由の /fund を数えない＝甘くなる側）
        edit(repo, "vercel.json", lambda s: s.rstrip()[:-1])
        edit(repo, "en/column-auction.html", link)
        c.guard("週次: vercel.json が読めなければ止める（O16-67 の数え方が甘くなる）", wk1("en/column-auction.html"), False,
                "vercel.json を読めないので止める", profile="weekly")
        edit(repo, "en/column-auction.html", add_p("selftest: securitization via GK-TK structures."))
        c.guard("週次: EN に証券化（GK-TK）を足したら止める（O16-69）", wk1("en/column-auction.html"), False, ("O16-69", "gk-tk"), profile="weekly")
        edit(repo, "zh-column-auction.html", add_p("selftest：证券化。"))
        c.guard("週次: ZH に证券化を足したら止める（O16-69）", wk1("zh-column-auction.html"), False, "O16-69", profile="weekly")
        edit(repo, "column-auction.html", add_p("selftest：証券化の語は JA では止めない。"))
        c.guard("週次: JA のページの「証券化」は O16-69 の対象外（通す）", wk1("column-auction.html"), True, profile="weekly")

        # ---- O16-10: 自称でない「中立」「neutral」は止めない（シナリオ名・引用符・carbon-neutral）。自称は止める
        edit(repo, "column-auction.html", add_p("selftest：強気・中立・弱気の 3 シナリオ。中立：約 5 割。"))
        c.guard("週次: シナリオ名の「中立」は自称ではない（通す）", wk1("column-auction.html"), True, profile="weekly")
        edit(repo, "en/column-auction.html", add_p('selftest: carbon-neutral fuels and a "neutral" scenario.'))
        c.guard("週次: carbon-neutral・引用符の \"neutral\" は自称ではない（通す）", wk1("en/column-auction.html"), True, profile="weekly")
        edit(repo, "en/column-auction.html", add_p("selftest: we are a neutral intermediary."))
        c.guard("週次: 自称の neutral は止める", wk1("en/column-auction.html"), False, "neutral/independent の自称は禁止", profile="weekly")
        #   ハイフン・引用符を丸ごと外すと自称が素通りした（2026-09-23 の確かめ #76）。外すのは carbon-／climate-／net-／technology- だけ
        for f, t, needle in (("en/column-auction.html", "selftest: a vendor-neutral marketplace.", "neutral/independent の自称は禁止"),
                             ("en/column-auction.html", "selftest: a manufacturer-neutral broker and an EPC-neutral platform.",
                              "neutral/independent の自称は禁止"),
                             ("en/column-auction.html", "selftest: we act as a “neutral” party.", "neutral/independent の自称は禁止"),
                             ("column-auction.html", "selftest：当社は「中立」の立場です。", "自称「中立」は禁止")):
            edit(repo, f, add_p(t))
            c.guard(f"週次: 自称は止める（{t.split(': ', 1)[-1].split('：', 1)[-1][:28]}）", wk1(f), False, needle, profile="weekly")
        #   英語で外すのは neutral scenario と the neutral case の形だけ（2026-09-23 の 4 回目の確かめ #76 の残り）
        for t in ("selftest: We act as a neutral case manager for your sale.", "selftest: As the neutral case manager, we handle your sale.",
                  "selftest: neutral cases are what we handle."):
            edit(repo, "en/column-auction.html", add_p(t))
            c.guard(f"週次: 自称は止める（{t.split(': ', 1)[-1][:32]}）", wk1("en/column-auction.html"), False, "neutral/independent の自称は禁止",
                    profile="weekly")
        edit(repo, "en/column-auction.html", add_p("selftest: in the neutral case, prices fall; the “neutral” scenarios differ; The neutral cases vary."))
        c.guard("週次: the neutral case・neutral scenario は自称ではない（通す）", wk1("en/column-auction.html"), True, profile="weekly")
        edit(repo, "en/column-auction.html", add_p("selftest: climate-neutral, net-neutral and technology-neutral rules; the neutral case."))
        c.guard("週次: climate-／net-／technology-neutral と neutral case は自称ではない（通す）", wk1("en/column-auction.html"), True,
                profile="weekly")
        edit(repo, "column-auction.html", add_p("selftest：「中立」シナリオと中立ケース。"))
        c.guard("週次: 「中立」シナリオ・中立ケースは自称ではない（通す）", wk1("column-auction.html"), True, profile="weekly")
        #   既存の引用符つきの行（自己診断の文言）を手直ししても、新しく現れた「中立」「neutral」ではない＝止めない（ページ全体の前後で比べる）
        for f, a_, b_ in (("en/column-subsidies.html", "The three strategies are roughly tied.", "The three strategies are roughly even."),
                          ("column-subsidies.html", "3戦略がほぼ拮抗", "3戦略がほぼ互角")):
            edit(repo, f, lambda s, a_=a_, b_=b_: s.replace(a_, b_, 1))
            c.guard(f"週次: 既存の引用符つきの「中立」「neutral」の行の、離れた所を直すだけなら止めない（{f}）", wk1(f), True, profile="weekly")

        # ---- 公開される欄の案件ID・金額（O16-19）: 週次の before／after は公開されない＝掛けない。構成レビューは PR 本文に載る＝掛ける
        edit(repo, "column-auction.html", link)
        c.guard("週次: before に円の金額（元の title）があっても止めない（週次の before／after は公開されない）",
                wk1("column-auction.html", before=syn_amount("title: selftest の費用は 1 件 {} 万円", 9), after="title: selftest の費用の目安"), True, profile="weekly")
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("構成: before に円の金額は止める（PR 本文に載る）", {"changes": [hub(before=syn_amount("並び: selftest の {} 万円のカテゴリが先", 9))]}, False,
                "before: コミット・PR・変更日台帳に案件ID・金額を写さない", ref="selftest-quiet")

        # ---- cooldown_pages(strict=True): git の履歴を読めないときは例外（検査が止める）。ブリーフ用（strict=False）は落とさない
        nogit, empty_led = tmp / "not-a-repo", tmp / "ledger-empty"
        nogit.mkdir(); (empty_led / "ledger").mkdir(parents=True)
        code = ("import json, pathlib, sys; sys.path.insert(0, %r); import build_brief as b; b.REPO = pathlib.Path(%r)\n"
                "try:\n    b.cooldown_pages(strict=True); print('noraise')\nexcept Exception:\n    print('raised')\n"
                "print(json.dumps(b.cooldown_pages()))") % (str(HERE), str(nogit))
        r = run([sys.executable, "-c", code], tmp, env=dict(os.environ, SCIX_WEB_LEDGER=str(empty_led)))
        results.append((r.returncode == 0 and r.stdout.split()[:2] == ["raised", "{}"],
                        "凍結: git の履歴を読めないとき、検査用（strict=True）は例外・ブリーフ用は落とさず空", "凍結",
                        (r.stdout.strip() + " " + r.stderr.strip()[-80:])[:110]))

        # ---- 非公開の禁止語（O16-7・O16-12）。合成の一覧（SYN-1・SYN-2）で確かめる。止める理由は規則IDだけ＝語も式も出さない
        def add_line(html_line):
            return lambda s: s.replace("</body>", html_line + "\n</body>", 1)
        wk = {"changes": [weekly_entry(["column-auction.html"], ["/column-auction"])]}
        edit(repo, "column-auction.html", add_line("<p>ゼクシリアル語の説明</p>"))
        c.guard("週次: 非公開の禁止語を足した行は止める（規則IDだけ出す）", wk, False, "column-auction.html: 非公開の禁止語（SYN-1）",
                profile="weekly", forbid=SYN_SHOWN)
        edit(repo, "column-auction.html", add_line("<p>&#12476;&#12463;&#12471;テスト語</p>"))
        c.guard("週次: 実体参照で書いた非公開の禁止語も止める", wk, False, "非公開の禁止語（SYN-1）", profile="weekly", forbid=SYN_SHOWN)
        edit(repo, "column-auction.html", add_line("<p>中立の立場。利回りはZxq-value比で 12%</p>"))
        c.guard("週次: 同じ行を写すほかの理由（自称中立・利回りの数字）も、非公開の禁止語の行は抜粋を出さない", wk, False,
                ("自称「中立」", "O16-8", "非公開の禁止語（SYN-2）", "抜粋は出さない"), profile="weekly", forbid=SYN_SHOWN)
        #   抜粋の窓（前後 20 字）の端で語が切れても、語の残りを出さない＝出現を含む行の全体に当てる（2026-09-23 の 4 回目の確かめ）
        edit(repo, "column-auction.html", add_line("<p>ゼクシリアル語の説明とは別に、当社は完全に中立の立場です。</p>"))
        c.guard("週次: 自称「中立」の抜粋の窓の端で非公開の禁止語が切れても、語の残りを出さない", wk, False,
                ("自称「中立」", "抜粋は出さない", "非公開の禁止語（SYN-1）"), profile="weekly", forbid=SYN_SHOWN + ("クシリアル", "シリアル語"))
        edit(repo, "column-auction.html", add_line('<p><a href="/zxq-value">x</a></p>'))
        c.guard("週次: リンク先など、ほかの理由に紛れた語も伏せる", wk, False, ("内部リンク切れ", "伏せ字 SYN-2"), profile="weekly",
                forbid=SYN_SHOWN)
        edit(repo, "column-auction.html", link)
        c.guard("週次: 公開される欄（summary_lines・summary）の非公開の禁止語も止める（件数の理由も抜粋を出さない）",
                {"summary_lines": ["ゼクシテスト語のページは問い合わせ 3 件"],
                 "changes": [dict(weekly_entry(["column-auction.html"], ["/column-auction"]), summary="Zxq-value へのリンクを足した")]},
                False, ("summary_lines: 非公開の禁止語（SYN-1）", "マニフェスト 0: summary: 非公開の禁止語（SYN-2）",
                        "summary_lines: 問い合わせの件数"), profile="weekly", forbid=SYN_SHOWN)
        edit(repo, "knowledge.html", swap_cat_blocks)
        c.guard("構成レビュー: 公開される欄の非公開の禁止語も止める", {"changes": [hub(summary="ゼクシリアル語のカテゴリを先に")]}, False,
                "マニフェスト 0: summary: 非公開の禁止語（SYN-1）", ref="selftest-quiet", forbid=SYN_SHOWN)
        #   一覧が無い・式が 0 個・壊れた行 → 止める（黙って通さない）。本番の一覧（~/.config/scix-web/private_banned.tsv）が消えた回と同じ
        edit(repo, "column-auction.html", link)
        c.guard("週次: 非公開の禁止語一覧が無ければ止める", wk, False, "非公開の禁止語一覧が読めないので止める（O16-7・O16-12）",
                profile="weekly", banned=tmp / "no-such-list.tsv")
        (tmp / "banned_empty.tsv").write_text("# 式なし\n\n", encoding="utf-8")
        edit(repo, "column-auction.html", link)
        c.guard("週次: 一覧に式が 1 つも無ければ止める", wk, False, ("非公開の禁止語一覧が読めないので止める", "式が 1 つも無い"),
                profile="weekly", banned=tmp / "banned_empty.tsv")
        (tmp / "banned_broken.tsv").write_text("ゼクシ[語\tSYN-9\n", encoding="utf-8")
        edit(repo, "column-auction.html", link)
        c.guard("週次: 壊れた式の行があれば止める（式は出さない）", wk, False, ("非公開の禁止語一覧が読めないので止める", "SYN-9"),
                profile="weekly", banned=tmp / "banned_broken.tsv", forbid=("ゼクシ[",))

        # ---- 週次プロファイル: コラムは書かない（2026-09-20 中島）。新規ファイル 0・class=new-column は無い
        def new_column(name="column-selftest.html"):   # 既存コラムを写した「骨格は完璧な新コラム」でも止まること
            (repo / name).write_text((repo / "column-trading.html").read_text(encoding="utf-8").replace("/column-trading", "/" + name[:-5]), encoding="utf-8")
        new_column()
        c.guard("週次: 新規 HTML を 1 本足したら止める（class=body で申告しても）",
                {"changes": [weekly_entry(["column-selftest.html"], ["/column-selftest"], "body")]}, False,
                "新しいページは自動では作らない（コラムは中島さんが書く）", profile="weekly")
        new_column("en/column-selftest.html")
        c.guard("週次: EN の新規翻訳（新しいファイル）も止める",
                {"changes": [weekly_entry(["en/column-selftest.html"], ["/en/column-selftest"], "body")]}, False,
                "新規ファイル en/column-selftest.html", profile="weekly")
        edit(repo, "column-auction.html", link)
        c.guard("週次: class=new-column のマニフェストは止める（ファイルは既存でも）",
                {"changes": [weekly_entry(["column-auction.html"], ["/column-auction"], "new-column")]}, False,
                "class=new-column は使えない", profile="weekly")
        edit(repo, "knowledge.html", add_card_for_existing)
        c.guard("週次: 人が足したコラムの育成（ハブにカードを足す）は今までどおり通す",
                {"changes": [dict(weekly_entry(["knowledge.html"], ["/column-auction"], "hub"))]}, True, profile="weekly")

        # ---- title は最初の 1 つだけ読む（本文のインライン SVG の <title id="fig…"> を連結しない）
        grid_title = re.search(r"<title>(.*?)</title>", (repo / "column-grid.html").read_text(encoding="utf-8"), re.S).group(1)
        assert (repo / "column-tax.html").read_text(encoding="utf-8").count("<title") >= 2, "column-tax.html に SVG の title が無い（selftest を直す）"
        edit(repo, "column-tax.html", lambda s: re.sub(r"<title>.*?</title>", lambda m: "<title>" + grid_title + "</title>", s, count=1, flags=re.S))
        c.guard("週次: SVG 図つきコラムでも title の重複を止める", {"changes": [weekly_entry(["column-tax.html"], ["/column-tax"], "title")]},
                False, "title が他ページと重複", profile="weekly")
        amp = next((f for f in sorted(repo.glob("column-*.html")) if "&amp;" in (re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8"), re.S) or [""])[0]), None)
        assert amp is not None and amp.name != "column-tax.html", "title に &amp; を持つコラムが無い（selftest を直す）"
        amp_title = re.search(r"<title>(.*?)</title>", amp.read_text(encoding="utf-8"), re.S).group(1)
        edit(repo, "column-tax.html", lambda s: re.sub(r"<title>.*?</title>", lambda m: "<title>" + amp_title + "</title>", s, count=1, flags=re.S))
        c.guard("週次: 実体参照（&amp;）入りの title でも重複を止める", {"changes": [weekly_entry(["column-tax.html"], ["/column-tax"], "title")]},
                False, "title が他ページと重複", profile="weekly")
        edit(repo, "en/column-tax.html", lambda s: s.replace("</body>", '<p><a href="/en/contact">Contact</a></p>\n</body>', 1))
        c.guard("週次: SVG 図つきの EN コラムを title 70 字で誤って止めない",
                {"changes": [weekly_entry(["en/column-tax.html"], ["/en/column-tax"])]}, True, profile="weekly")

        # ---- 週次プロファイル: ナレッジの件数（gen_knowledge_jsonld.py が焼く）は同期の検査に掛けない
        edit(repo, "knowledge.html", lambda s: re.sub(r"(<!--S:kcount-->)(\d+)", lambda m: m.group(1) + str(int(m.group(2)) + 1), s))
        c.guard("週次: kcount の焼き直しは通す", {"changes": [dict(hub(), **{"class": "hub"})]}, True, profile="weekly")

        # ---- マージの記帳（register_structure_merges.py）
        prop = {"id": "structure-" + TODAY.strftime("%Y%m") + "-1", "date": str(TODAY), "status": "proposed", "pr": 999,
                "branch": "auto/structure-" + TODAY.strftime("%Y-%m"), "commit": "0" * 40, "files": ["header.js"],
                "pages": ["/"], "class": "nav", "summary": "ナビ", "rationale": "x 1", "kpi": "k", "measure": "m", "before": {}}
        stale = dict(prop, id="structure-old-1", pr=12345, date=str(TODAY - datetime.timedelta(days=90)))
        (ledger / "ledger" / "proposals.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in (prop, stale)) + "\n", encoding="utf-8")
        env = dict(os.environ, SCIX_WEB_REPO=str(repo), SCIX_WEB_LEDGER=str(ledger), SCIX_WEB_REF="selftest-navchanged")
        r = run([sys.executable, str(REGISTER)], repo, env=env)
        ch = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines()] if led.exists() else []
        pr = [json.loads(l) for l in (ledger / "ledger" / "proposals.jsonl").read_text(encoding="utf-8").splitlines()]
        ok = (r.returncode == 0 and len(ch) == 1 and ch[0]["id"] == prop["id"] and ch[0]["source"] == "structure"
              and ch[0].get("nav_change") is True and ch[0]["pr"] == 999 and ch[0]["check_days"] == [14, 28]
              and {p["id"]: p["status"] for p in pr} == {prop["id"]: "merged", "structure-old-1": "expired"})
        results.append((ok, "マージされた提案を変更台帳へ（(#999) のコミットを見つける・60日超は expired）", "記帳", (r.stdout + r.stderr).strip()[:110]))
        r2 = run([sys.executable, str(REGISTER)], repo, env=env)
        ch2 = led.read_text(encoding="utf-8").splitlines()
        results.append((r2.returncode == 0 and len(ch2) == 1, "記帳は何度走っても重複しない", "記帳", (r2.stdout + r2.stderr).strip()[:110]))
        # 記帳されたナビ変更は、次の検査で90日ルールに掛かる（台帳側から）
        edit(repo, "header.js", nav_swap)
        c.guard("記帳後はナビの組み替えを台帳が止める", {"changes": [nav]}, False, "日に1回まで", ref="selftest-quiet")

        # ---- PR 番号の無い提案（gh が失敗して枝だけ push した月）のマージの記帳
        #   A＝PR #95 つき・先にマージ／B＝番号なし・後からマージ（A のマージコミットに当たっても探すのを打ち切らない）
        #   Bdup＝B と同じ中身の出し直し（二重に数えない）／X＝番号なし・変更 2 件（同じ提案の 2 行が同じマージコミットに当たる）
        ledger2 = tmp / "ledger2"; (ledger2 / "ledger").mkdir(parents=True)
        def link_tail(s):
            return s.replace("</body>", '<p><a href="/projects">販売中の案件一覧</a></p>\n</body>', 1)
        def side(name, base, edits, msg):
            git(repo, "checkout", "-q", "-b", name, base)
            for rel, fn in edits:
                edit(repo, rel, fn)
            git(repo, "commit", "-qam", msg)
            return git(repo, "rev-parse", "HEAD")
        def land(src, files, msg):   # squash マージ相当: main2 に同じ中身を 1 コミットで入れる
            git(repo, "checkout", "-q", "selftest-main2")
            git(repo, "checkout", src, "--", *files)
            git(repo, "commit", "-qam", msg)
            return git(repo, "rev-parse", "HEAD")
        git(repo, "checkout", "-q", "-b", "selftest-main2", quiet)
        ca = side("selftest-side-a", "selftest-main2", [("index.html", swap_top_sections)], "auto(structure): A")
        m_a = land("selftest-side-a", ["index.html"], "auto(structure): A (#95)")
        cb = side("selftest-side-b", "selftest-main2", [("knowledge.html", swap_cat_blocks)], "auto(structure): B")
        cb2 = side("selftest-side-b2", "selftest-main2", [("knowledge.html", swap_cat_blocks)], "auto(structure): B の出し直し")
        m_b = land("selftest-side-b", ["knowledge.html"], "構成の見直し（compare の URL から手で PR を作ってマージ）")
        cx = side("selftest-side-x", "selftest-main2", [("column-auction.html", link_tail), ("column-grid.html", link_tail)], "auto(structure): X")
        m_x = land("selftest-side-x", ["column-auction.html", "column-grid.html"], "構成の見直し X（手でマージ）")
        git(repo, "checkout", "-q", "selftest-main2")
        edit(repo, "column-tax.html", link_tail)
        git(repo, "commit", "-qam", "feat(column): 関係ない後続のコミット（B・X と同じ中身を持ち続ける）")
        git(repo, "checkout", "-q", "--detach", quiet)
        def prop2(pid, commit, files, pages, pr=None):
            return {"id": pid, "date": str(TODAY), "status": "proposed", "pr": pr, "branch": "auto/structure-x", "commit": commit,
                    "files": files, "pages": pages, "class": "hub-order", "summary": pid, "rationale": "x 1", "kpi": "k", "measure": "m", "before": {}}
        rows2 = [prop2("structure-B-1", cb, ["knowledge.html"], ["/knowledge"]),
                 prop2("structure-B-1b", cb2, ["knowledge.html"], ["/knowledge"]),
                 prop2("structure-X-1", cx, ["column-auction.html"], ["/column-auction"]),
                 prop2("structure-X-2", cx, ["column-grid.html"], ["/column-grid"]),
                 prop2("structure-A-1", ca, ["index.html"], ["/"], pr=95)]
        (ledger2 / "ledger" / "proposals.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows2) + "\n", encoding="utf-8")
        env2 = dict(os.environ, SCIX_WEB_REPO=str(repo), SCIX_WEB_LEDGER=str(ledger2), SCIX_WEB_REF="selftest-main2")
        for n in (1, 2):
            r3 = run([sys.executable, str(REGISTER)], repo, env=env2)
            ch3 = [json.loads(l) for l in (ledger2 / "ledger" / "changes.jsonl").read_text(encoding="utf-8").splitlines()]
            pr3 = {p["id"]: p for p in (json.loads(l) for l in (ledger2 / "ledger" / "proposals.jsonl").read_text(encoding="utf-8").splitlines())}
            ok = (r3.returncode == 0
                  and sorted(e["id"] for e in ch3) == ["structure-A-1", "structure-B-1", "structure-X-1", "structure-X-2"]
                  and {e["id"]: e["commit"] for e in ch3} == {"structure-A-1": m_a, "structure-B-1": m_b, "structure-X-1": m_x, "structure-X-2": m_x}
                  and pr3["structure-B-1b"]["status"] == "proposed"
                  and all(pr3[i]["status"] == "merged" for i in ("structure-A-1", "structure-B-1", "structure-X-1", "structure-X-2")))
            results.append((ok, f"PR 番号なしの提案: 前の PR のマージで打ち切らない・同じ提案の 2 行目も記帳・出し直しは二重に数えない（{n} 回目）",
                            "記帳", (r3.stdout + r3.stderr).strip().splitlines()[0][:110] if (r3.stdout + r3.stderr).strip() else ""))

        # ---- ブリーフ 9 節: 構成レビュー用は、ハブ・トップの凍結を変更台帳の構成系エントリだけで決める
        #   （コラムを足したコミット・ハブを触った全コミットで凍結すると、毎週コラムを足す運用では常に凍結される）
        def add_card(s):
            card = ('      <a target="_top" href="/column-selftest" class="ac is-new">\n        <div class="am"><span class="an">COLUMN 99</span>'
                    '<span class="new">NEW</span><span class="at">selftest</span></div>\n        <h3>selftest のコラム</h3>\n'
                    '        <p class="ad">selftest</p>\n        <div class="aa">→</div>\n      </a>\n')
            a = s.index('id="cat-market"')
            pos = s.rfind("\n", 0, a + re.search(r'<a [^>]*class="ac', s[a:]).start()) + 1
            return s[:pos] + card + s[pos:]
        ledger3 = tmp / "ledger3"; (ledger3 / "ledger").mkdir(parents=True)
        def cooldown(structure, expr="sorted(b.cooldown_pages(structure=%s))"):
            code = ("import json,sys; sys.path.insert(0, %r); import build_brief as b, structure as st; "
                    "print(json.dumps(" + expr + "))") % ((str(HERE), structure) if "%s" in expr else (str(HERE),))
            r = run([sys.executable, "-c", code], repo, env=dict(os.environ, SCIX_WEB_REPO=str(repo), SCIX_WEB_LEDGER=str(ledger3)))
            return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else ["ERR " + r.stderr[-200:]]
        def ledger_rows(rows):
            (ledger3 / "ledger" / "changes.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
        def led_row(id_, cls, pages, source="auto", days_ago=3):
            return {"id": id_, "date": str(TODAY - datetime.timedelta(days=days_ago)), "class": cls, "source": source,
                    "pages": pages, "files": [], "summary": id_, "check_days": [14, 28], "measured": {}}
        hubtop = ("/", "/knowledge", "/en", "/en/knowledge", "/zh", "/zh-knowledge")
        git(repo, "checkout", "-q", "-b", "selftest-cool", quiet)
        (repo / "column-selftest.html").write_text(re.sub(r'("datePublished":\s*")\d{4}-\d{2}-\d{2}', r"\g<1>" + str(TODAY),
                                                   (repo / "column-trading.html").read_text(encoding="utf-8")), encoding="utf-8")
        edit(repo, "knowledge.html", add_card)
        g = run([sys.executable, "scripts/gen_knowledge_jsonld.py", "--write"], repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat(column): COLUMN 99 selftest を公開")
        touched = git(repo, "show", "--name-only", "--format=", "HEAD").split()
        cs, cw = cooldown(True), cooldown(False)
        ok = (g.returncode == 0 and "knowledge.html" in touched and "index.html" in touched
              and "/" not in cs and "/knowledge" not in cs and "/column-selftest" in cs and "/" in cw and "/knowledge" in cw)
        results.append((ok, "9 節: コラムを 1 本足しただけのコミットでは、構成レビュー用のブリーフはハブ・トップを凍結しない（週次用は従来どおり凍結）",
                        "凍結", f"structure={[p for p in cs if p in hubtop]} weekly={[p for p in cw if p in hubtop]}"))
        loose0 = cooldown(True, "st.unrecorded_layout_commits(14, cwd=b.REPO)")
        edit(repo, "knowledge.html", swap_cat_blocks)
        git(repo, "commit", "-qam", "feat(knowledge): カテゴリの順を入れ替えた")
        cs = cooldown(True)
        loose = cooldown(True, "st.unrecorded_layout_commits(14, cwd=b.REPO)")
        results.append(("/knowledge" not in cs and loose0 == [] and [x[0] for x in loose] == ["/knowledge"],
                        "9 節: 台帳に記帳の無いハブの並べ替えは凍結しない（git の履歴では決めない）。参考の行には出る（コラムを足しただけのコミットは出ない）",
                        "凍結", f"structure={[p for p in cs if p in hubtop]} 参考={[x[0] for x in loose]}"))
        # 変更台帳: 構成系でない class（title・new-column）ではハブ・トップを凍結しない。構成系（hub／hub-order／top-order／nav／source=structure）は凍結
        ledger_rows([led_row("w-title", "title", ["/knowledge", "/column-auction"]),
                     led_row("w-newcol", "new-column", ["/column-selftest", "/"], source="manual-auto")])
        cs, cw = cooldown(True), cooldown(False)
        results.append(("/knowledge" not in cs and "/" not in cs and "/column-auction" in cs and "/knowledge" in cw,
                        "9 節: 台帳の title・new-column のエントリでは、構成レビュー用のハブ・トップは凍結しない（ハブ以外のページと週次用は凍結）",
                        "凍結", f"structure={[p for p in cs if p in hubtop]} weekly={[p for p in cw if p in hubtop]}"))
        # 週次が構成の変更を差し戻した（class=rollback・source=auto・pages は元の変更と同じ）直後は、そのハブ・トップを凍結する
        ledger_rows([led_row("s-old-hub", "hub-order", ["/knowledge"], source="structure", days_ago=28),
                     led_row("w-rollback", "rollback", ["/knowledge"], days_ago=7),
                     led_row("w-rollback-today", "rollback", ["/en/knowledge"], days_ago=0)])
        cs = cooldown(True)
        results.append(([p for p in cs if p in hubtop] == ["/en/knowledge", "/knowledge"],
                        "9 節: 週次が差し戻した（class=rollback）ハブは、構成レビュー用のブリーフでも 14 日凍結する（7 日前・同じ朝）",
                        "凍結", f"structure={[p for p in cs if p in hubtop]}"))
        ledger_rows([led_row("w-hub", "hub", ["/knowledge"], source="manual"),
                     led_row("s-cta", "cta-route", ["/", "/column-grid"], source="structure"),
                     led_row("s-top", "top-order", ["/en"], source="structure"),
                     led_row("s-nav", "nav", ["/zh"], source="structure"),
                     led_row("s-old", "hub-order", ["/zh-knowledge"], source="structure", days_ago=20)])
        cs = cooldown(True)
        brief9 = cooldown(True, "b.hub_top_freeze_lines(b.cooldown_pages(structure=True))")
        now9 = brief9[0].split("いま凍結中のハブ・トップ")[-1] if brief9 else ""
        results.append(([p for p in cs if p in hubtop] == ["/", "/en", "/knowledge", "/zh"] and "/column-grid" in cs
                        and len(brief9) == 1 and "/knowledge（" in now9 and "/zh-knowledge（" not in now9,   # 凍結中のページは参考の行に出さない
                        "9 節: 台帳の構成系エントリ（hub・source=structure・top-order・nav）はハブ・トップを凍結する。14 日を過ぎたものは外れる",
                        "凍結", f"structure={[p for p in cs if p in hubtop]}"))

        # ---- 暦に無い datePublished（正規表現は桁数しか見ない）で効果測定・ブリーフを止めない＝git の初回コミット日へ落ちる
        edit(repo, "column-selftest.html", lambda s: re.sub(r'("datePublished":\s*")\d{4}-\d{2}-\d{2}', r"\g<1>2026-09-31", s, count=1))
        git(repo, "commit", "-qam", "selftest: 暦に無い公開日")
        code = ("import json,sys; sys.path.insert(0, %r); import newpages as n; "
                "print(json.dumps([[r['published'], r['published_by']] for r in n.site_pages() if r['page'] == '/column-selftest']))" % str(HERE))
        r4 = run([sys.executable, "-c", code], repo, env=dict(os.environ, SCIX_WEB_REPO=str(repo), SCIX_WEB_LEDGER=str(ledger2 / "none"),
                                                              SCIX_WEB_REF="selftest-cool"))
        got4 = json.loads(r4.stdout.strip().splitlines()[-1]) if r4.returncode == 0 and r4.stdout.strip() else r4.stderr[-200:]
        results.append((got4 == [[str(TODAY), "git"]], "暦に無い datePublished は無いものとして扱う（git の初回コミット日）", "公開日", str(got4)[:110]))
        git(repo, "checkout", "-q", "--detach", quiet)

        bad = [x for x in results if not x[0]]
        for ok_, name, kind_, tail in results:
            print(f"{'ok  ' if ok_ else 'FAIL'} [{kind_}] {name}" + (f" — {tail}" if tail else ""))
        print(f"\n{len(results) - len(bad)}/{len(results)} 通過（一時ディレクトリ {tmp}{'・残す' if keep else ''}）")
        return 1 if bad else 0
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
