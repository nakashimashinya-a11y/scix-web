#!/usr/bin/env python3
"""構成レビュー（guard_diff.py --profile structure・structure.py・register_structure_merges.py）を合成差分で確かめる。
週次の検査のうち「コラムは書かない＝新規ファイル 0・class=new-column は無い」（2026-09-20）もここで確かめる。

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


class Case:
    def __init__(self, repo, ledger, tmp):
        self.repo, self.ledger, self.tmp = repo, ledger, tmp

    def reset(self):
        git(self.repo, "checkout", "-q", "--", ".")
        git(self.repo, "clean", "-fdq")

    def guard(self, name, manifest, expect_ok, needle=None, profile="structure", ref=None):
        mf = self.tmp / "changes.json"
        mf.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, SCIX_WEB_REPO=str(self.repo), SCIX_WEB_LEDGER=str(self.ledger))
        env.pop("SCIX_WEB_REF", None)
        if ref:
            env["SCIX_WEB_REF"] = ref
        r = run([sys.executable, str(GUARD), "--manifest", str(mf), "--profile", profile], self.repo, env=env)
        out = r.stdout + r.stderr
        needles = [needle] if isinstance(needle, str) else list(needle or [])   # 複数なら全部が出力に出ていること
        ok = (r.returncode == 0) == expect_ok and all(n in out for n in needles)
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


def add_card_for_existing(s):
    """ハブの cat-market の先頭に、既存コラム（/column-auction）のカードを 1 枚足す（週次の「登録漏れの手当て」と同じ形）。"""
    card = ('      <a target="_top" href="/column-auction" class="ac">\n        <div class="am"><span class="an">COLUMN</span>'
            '<span class="at">selftest</span></div>\n        <h3>selftest: 登録漏れのカード</h3>\n'
            '        <p class="ad">selftest</p>\n        <div class="aa">→</div>\n      </a>\n')
    a = s.index('id="cat-market"')
    pos = s.rfind("\n", 0, a + re.search(r'<a [^>]*class="ac', s[a:]).start()) + 1
    return s[:pos] + card + s[pos:]


def nav_swap(s):
    """「買う」の引き出しの中で /projects と /transfer の順を入れ替える（ナビ定義の変更）。"""
    a = "      ['/projects', '販売中の案件一覧'],\n"
    b = "      ['/transfer', '買うまでの流れ'],\n"
    assert a + b in s, "header.js のナビ定義が想定と違う（selftest を直す）"
    return s.replace(a + b, b + a, 1)


def main() -> int:
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
