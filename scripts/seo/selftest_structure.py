#!/usr/bin/env python3
"""構成レビュー（guard_diff.py --profile structure・structure.py・register_structure_merges.py）を合成差分で確かめる。

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
        ok = (r.returncode == 0) == expect_ok and (needle is None or needle in out)
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
        c.guard("ハブのカテゴリ順を入れ替え（並べ替えだけ）", {"changes": [hub()]}, True, "OK（structure）", ref="selftest-quiet")

        edit(repo, "index.html", swap_top_sections)
        c.guard("トップの節を入れ替え（ヒーローより下・S マーカーごと移動）",
                {"changes": [entry(["index.html"], ["/"], "top-order")]}, True, ref="selftest-quiet")

        edit(repo, "header.js", nav_swap)
        nav = entry(["header.js"], ["/"], "nav", nav_rule={"last_nav_change": None})
        c.guard("ナビの組み替え（直近90日に変更なし・申告 null）", {"changes": [nav]}, True, ref="selftest-quiet")

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
                "新規ファイルを作らない")

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
