#!/usr/bin/env python3
"""weekly_run.sh の公開の経路（MODE=structure の自動公開・MODE=weekly）を、偽の origin とスタブで一周させて確かめる。

    python3 scripts/seo/selftest_publish.py        # 0=全部通った（--keep で一時ディレクトリを残す）

本物には触らない: origin は一時ディレクトリの bare リポジトリ、リポジトリ・台帳・ロック・作業ツリー・HOME も一時ディレクトリ。
claude・openclaw・gh・curl・sleep はスタブで、PATH は「スタブ＋/usr/bin:/bin」だけ（本物の claude／gh／openclaw は見えない）。
IndexNow（scripts/ping_indexnow.py）は複製の中で何もしないスクリプトに差し替える＝外へ出ない。python3 は /usr/bin/python3（3.9）。
確かめること（2026-09-20 のレビューで再現した欠陥）:
  1. 公開は 2 コミット: 中身（auto(structure): ／ auto(seo):）と記帳（chore(seo-log):＝sitemap の lastmod・変更日台帳）。
     タグ・Telegram の `git revert <sha>`・変更台帳の commit は中身のコミットを指す
  2. 構成レビューの公開 → 翌週の週次の公開のあとでも、案内どおりの `git revert <中身のコミット>` が衝突しない
     （同じコミットに変更日台帳の行を入れていた頃は、次の自動コミット 1 つで必ず衝突した）
  3. push のあとで変更台帳（Drive）に書けなかった回: Telegram に出す（「自動で測る」と言い切らない）。翌朝の拾い直し
     （register_auto_commits.py）が同じ形で記帳する・2 回走っても重複しない・記帳済みのコミットは足さない
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent.parent
TODAY = datetime.date.today()
MONTH = TODAY.strftime("%Y-%m")
results = []

CLAUDE_STUB = r'''
import json, os, pathlib, re, sys
sys.path.insert(0, os.environ["STUB_HERE"])
import selftest_structure as ss
prompt = sys.argv[sys.argv.index("-p") + 1]
out = pathlib.Path(re.search(r"マニフェストの出力先: (\S+)", prompt).group(1))
scenario = os.environ["STUB_SCENARIO"]
if scenario == "structure":      # ハブのカテゴリ順を入れ替える（並べ替えだけ）
    p = pathlib.Path("knowledge.html")
    p.write_text(ss.swap_cat_blocks(p.read_text(encoding="utf-8")), encoding="utf-8")
    man = {"proposal_title": "selftest: ハブのカテゴリ順を流入の多い順に", "summary_lines": ["selftest: ハブのカテゴリ順を入れ替えた"],
           "changes": [ss.entry(["knowledge.html"], ["/knowledge"], "hub-order", kpi_pages=["/projects"], private_note="selftest の非公開メモ")]}
elif scenario == "structure-top":   # 同じ日の 2 回目の構成レビュー: /knowledge は 1 回目の hub-order で凍結中（O16-37）＝トップの節の順を変える
    p = pathlib.Path("index.html")
    p.write_text(ss.swap_top_sections(p.read_text(encoding="utf-8")), encoding="utf-8")
    man = {"proposal_title": "selftest: トップの節の順を入れ替え", "summary_lines": ["selftest: トップの節の順を入れ替えた"],
           "changes": [ss.entry(["index.html"], ["/"], "top-order", summary="トップの節の順を入れ替えた")]}
else:                            # 週次: コラムの末尾に内部リンクを 1 本
    # 14 日以内に触ったページは検査が止める（O16-37）。複製は本物の履歴を持つ＝日によって凍結が変わるので、凍結していないコラムを選ぶ
    import build_brief as bb
    bb.REPO = pathlib.Path.cwd()
    frozen = bb.cooldown_pages()
    cands = [pathlib.Path("column-auction.html")] + [f for g in ("column-*.html", "en/column-*.html", "zh-column-*.html")
                                                     for f in sorted(pathlib.Path(".").glob(g))]
    p = next(f for f in cands if "/" + str(f)[:-5] not in frozen)
    p.write_text(p.read_text(encoding="utf-8").replace("</body>", '<p><a href="/projects">販売中の案件一覧</a></p>\n</body>', 1), encoding="utf-8")
    e = ss.entry([str(p)], ["/" + str(p)[:-5]], "internal-link", summary="selftest: /projects への内部リンク"); e.pop("measure")
    man = {"summary_lines": ["selftest: コラムに /projects への内部リンク"], "column_ideas": [], "changes": [e]}
out.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
if os.environ.get("STUB_ADVANCE_MAIN") == "1":   # Claude の作業中に main が進んだ（毎朝の案件一覧の同期など）＝push の前に載せ直しになる
    import subprocess
    repo, adv = os.environ["SCIX_WEB_REPO"], os.environ["STUB_TMP"] + "/advance"
    g = ["git", "-C", repo, "-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid"]
    subprocess.run(g + ["worktree", "add", "-q", "--detach", adv, "origin/main"], check=True)
    with open(adv + "/README.md", "a", encoding="utf-8") as f:
        f.write("\nselftest: main が進んだ\n")
    g2 = ["git", "-C", adv, "-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid"]
    subprocess.run(g2 + ["commit", "-qam", "selftest: 作業中に main が進んだ"], check=True)
    subprocess.run(g2 + ["push", "-q", "origin", "HEAD:main"], check=True)
    subprocess.run(g + ["worktree", "remove", "--force", adv], check=True)
print(json.dumps({"result": "selftest", "is_error": False, "total_cost_usd": 0, "num_turns": 1, "duration_ms": 1}))
'''


def run(args, cwd, env=None, check=False):
    r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=True, text=True, errors="replace", env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))}: {r.stderr[:400]}")
    return r


def git(repo, *args):
    return run(["git", "-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid", *args], repo, check=True).stdout.strip()


def check(name, ok, tail=""):
    results.append((bool(ok), name, str(tail)[:160]))


def main() -> int:
    keep = "--keep" in sys.argv
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="scix-publish-selftest-"))
    try:
        origin, repo, ledger, state, home, bin_ = (tmp / n for n in ("origin.git", "repo", "ledger", "state", "home", "bin"))
        for p in (ledger / "ledger", state, home / ".openclaw", home / "ccdir", bin_):
            p.mkdir(parents=True)
        # ---- 偽の origin と、その複製（手元の main 相当）。作業ツリーの scripts/seo（未コミットの分も）を載せる
        head = git(SRC, "rev-parse", "HEAD")
        run(["git", "clone", "-q", "--bare", "--shared", SRC, origin], tmp, check=True)
        run(["git", "clone", "-q", "--shared", "--no-checkout", SRC, repo], tmp, check=True)
        git(repo, "remote", "set-url", "origin", str(origin))      # 元のリポジトリへは push しない
        for r_ in (origin, repo):                                   # 複製に付いてきた本物の自動公開のタグ（今日の週次・今月の構成）を外す
            for t in git(r_, "tag", "-l", "auto/*").split():
                git(r_, "tag", "-d", t)
        git(repo, "checkout", "-q", "-B", "main", head)
        for f in (SRC / "scripts" / "seo").iterdir():
            if f.is_file():
                shutil.copy2(f, repo / "scripts" / "seo" / f.name)
        (repo / "scripts" / "ping_indexnow.py").write_text("#!/usr/bin/env python3\nprint('selftest: IndexNow は送らない')\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--allow-empty", "-m", "selftest: 作業ツリーの scripts/seo・IndexNow は送らない")
        git(repo, "push", "-q", "-f", "origin", "main")
        git(repo, "fetch", "-q", "origin")
        assert git(repo, "remote", "get-url", "origin") == str(origin)

        # ---- スタブ
        (home / ".openclaw" / "openclaw.json").write_text(json.dumps(
            {"agents": {"defaults": {"cliBackends": {"claude-cli": {"env": {"CLAUDE_CONFIG_DIR": str(home / "ccdir")}}}}}}), encoding="utf-8")
        (tmp / "claude_stub.py").write_text(CLAUDE_STUB, encoding="utf-8")
        stubs = {"claude": f'#!/bin/bash\nexec python3 "{tmp}/claude_stub.py" "$@"\n',
                 "openclaw": f'#!/bin/bash\nprintf "%s\\n----\\n" "$*" >> "{tmp}/telegram.log"\n',
                 "gh": "#!/bin/bash\nexit 1\n", "curl": "#!/bin/bash\nexit 1\n", "sleep": "#!/bin/bash\nexit 0\n"}
        # Telegram は関所（~/.openclaw/workspace/bin/tg_gate.py）を通る。一時 HOME には無いので、関所のスタブを SCIX_TG_GATE で指す
        # （送る種類は telegram.log、行動ログ＝kind=log は actionlog.log に書く）
        (tmp / "tg_gate_stub.py").write_text(
            "import sys\n"
            "a = sys.argv[1:]\n"
            "kind = a[a.index('--kind') + 1] if '--kind' in a else '?'\n"
            "key = a[a.index('--key') + 1] if '--key' in a else '?'\n"
            "msg = sys.stdin.read()\n"
            f"out = {str(tmp)!r} + ('/actionlog.log' if kind == 'log' else '/telegram.log')\n"
            "open(out, 'a', encoding='utf-8').write('%s\\n----\\n' % msg)\n"
            f"open({str(tmp)!r} + '/tg_meta.log', 'a', encoding='utf-8').write('kind=%s key=%s\\n' % (kind, key))\n",
            encoding="utf-8")
        for name, body in stubs.items():
            p = bin_ / name
            p.write_text(body, encoding="utf-8")
            p.chmod(p.stat().st_mode | stat.S_IXUSR)
        # 非公開の禁止語（O16-7・O16-12）の一覧は本物の HOME（~/.config/scix-web）にある＝一時 HOME には無い。
        # 検査は一覧が無いと止めるので、合成の一覧を SCIX_WEB_PRIVATE_BANNED で指す
        (tmp / "private_banned.tsv").write_text("# 合成の一覧（selftest 専用）\nゼクシ(?:リアル|テスト)語\tSYN-1\n", encoding="utf-8")
        base_env = {"HOME": str(home), "PATH": f"{bin_}:/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
                    "SCIX_WEB_PRIVATE_BANNED": str(tmp / "private_banned.tsv"),
                    # Telegram は関所のスタブで受ける（git revert の案内・台帳の記帳の失敗の文面を確かめる）
                    "SCIX_TG_GATE": str(tmp / "tg_gate_stub.py"),
                    "SCIX_WEB_REPO": str(repo), "SCIX_WEB_LEDGER": str(ledger), "SCIX_WEB_STATE": str(state),
                    "SCIX_WEB_WT": str(tmp / "wt-weekly"), "SCIX_WEB_WT_STRUCTURE": str(tmp / "wt-structure"),
                    "NO_COLLECT": "1", "NO_STRUCTURE": "1", "STUB_HERE": str(HERE), "STUB_TMP": str(tmp),
                    "https_proxy": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9"}

        def weekly_run(mode, scenario, **extra):
            env = dict(base_env, MODE=mode, STUB_SCENARIO=scenario, **extra)
            (tmp / "telegram.log").write_text("", encoding="utf-8")
            r = run(["/bin/bash", repo / "scripts" / "seo" / "weekly_run.sh"], repo, env=env)
            return r, (tmp / "telegram.log").read_text(encoding="utf-8")

        def main_log(n=6):
            return [l.split("\t") for l in git(repo, "log", "origin/main", f"-n{n}", "--format=%H%x09%s").splitlines()]

        def files_of(sha):
            return set(git(repo, "show", "--name-only", "--format=", sha).split())

        def ledger_rows():
            p = ledger / "ledger" / "changes.jsonl"
            return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

        # /bin/bash 3.2 は UTF-8 のロケールだと「$VAR）」の全角の 1 バイト目を変数名に含める（set -u で止まる）。この一周も LANG=UTF-8 で回す
        sh_text = (SRC / "scripts" / "seo" / "weekly_run.sh").read_text(encoding="utf-8")
        loose = [f"{n}: {m.group(0)}" for n, l in enumerate(sh_text.splitlines(), 1) if not l.lstrip().startswith("#")
                 for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])", l)]
        check("weekly_run.sh: 変数の直後に全角文字が続く所は ${VAR} と書いてある", not loose, loose[:5])
        claude_seen = run(["/bin/bash", "-c", "command -v claude; command -v gh; command -v openclaw"], tmp, env=base_env).stdout.split()
        check("スタブだけが見えている（本物の claude／gh／openclaw を起こさない）", claude_seen == [str(bin_ / n) for n in ("claude", "gh", "openclaw")], claude_seen)

        # ---- 1. 構成レビューの自動公開: 2 コミット・タグ・Telegram・変更台帳
        r, tg = weekly_run("structure", "structure")
        log = main_log()
        ok_shape = len(log) >= 2 and log[0][1].startswith("chore(seo-log): auto(structure)") and log[1][1].startswith("auto(structure): ")
        s_sha = next((h for h, subj in log if subj.startswith("auto(structure): ")), "")   # 中身のコミット（差し戻しで revert する対象）
        check("構成レビュー: 公開は 2 コミット（中身 auto(structure): の上に記帳 chore(seo-log):）", r.returncode == 0 and ok_shape,
              (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
        if ok_shape:
            check("構成レビュー: 中身のコミットに変更日台帳と sitemap を入れない／記帳のコミットはその 2 つだけ",
                  not ({"docs/seo-change-log.md", "sitemap.xml"} & files_of(s_sha)) and "knowledge.html" in files_of(s_sha)
                  and files_of(log[0][0]) == {"docs/seo-change-log.md", "sitemap.xml"}, f"{sorted(files_of(s_sha))} / {sorted(files_of(log[0][0]))}")
            tag = run(["git", "ls-remote", "--tags", "origin", f"refs/tags/auto/structure-{MONTH}"], repo).stdout.split()
            led = [e for e in ledger_rows() if e.get("source") == "structure"]
            check("構成レビュー: タグ・Telegram の git revert・変更台帳の commit が中身のコミットを指す",
                  tag[:1] == [s_sha] and f"git revert {s_sha[:10]}" in tg and [e.get("commit") for e in led] == [s_sha]
                  and led[0].get("kpi_pages") == ["/projects"] and led[0].get("private_note"), f"tag={tag[:1]} ledger={[e.get('commit', '')[:10] for e in led]}")
            check("構成レビュー: Telegram は 3 行・「GSC の判定が worse なら」と言う（問い合わせの減りまで自動で戻すとは言わない）",
                  "GSC の判定が worse なら週次が戻し" in tg and "悪ければ週次が戻す" not in tg and len(tg.split("--message ")[-1].strip().splitlines()) <= 4, tg[-200:])
            pub = (run(["git", "show", f"{log[0][0]}:docs/seo-change-log.md"], repo).stdout + git(repo, "log", "-2", "--format=%B", "origin/main"))
            check("構成レビュー: private_note は公開リポジトリ（変更日台帳・コミット文）に出ない", "selftest の非公開メモ" not in pub)

        # ---- 2. 翌週の週次の公開 → 構成レビューの中身のコミットを案内どおり revert（衝突しない）
        #    週次の作業中に main が進む（載せ直し）: 2 コミットとも載せ直され、SHA・タグ・変更台帳は載せ直したあとの中身のコミット
        r, tg = weekly_run("weekly", "weekly", STUB_ADVANCE_MAIN="1")
        log = main_log()
        ok_w = (len(log) >= 5 and log[0][1].startswith("chore(seo-log): auto(seo)") and log[1][1].startswith("auto(seo): ")
                and log[2][1] == "selftest: 作業中に main が進んだ")
        wtag = run(["git", "ls-remote", "--tags", "origin", f"refs/tags/auto/weekly-{TODAY}"], repo).stdout.split()
        check("週次: 作業中に main が進んでも、公開は 2 コミット（中身 auto(seo): の上に記帳）・タグと変更台帳の commit は載せ直したあとの中身のコミット",
              r.returncode == 0 and ok_w and [e.get("commit") for e in ledger_rows() if e.get("source") == "auto"] == [log[1][0]]
              and wtag[:1] == [log[1][0]] and f"git revert {log[1][0][:10]}" in tg,
              (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
        if s_sha and any(subj.startswith("auto(seo): ") for _, subj in log):   # 2 コミットの形でなくても、案内どおりの revert は試す
            git(repo, "checkout", "-q", "main"); git(repo, "reset", "-q", "--hard", "origin/main")
            rv = run(["git", "-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid", "revert", "--no-edit", s_sha], repo)
            touched = files_of("HEAD") if rv.returncode == 0 else set()
            check("差し戻し: 週次が 1 回入ったあとでも `git revert <auto(structure) の中身のコミット>` が衝突しない",
                  rv.returncode == 0 and "knowledge.html" in touched and "docs/seo-change-log.md" not in touched,
                  (rv.stdout + rv.stderr).strip().splitlines()[-1] if (rv.stdout + rv.stderr).strip() else "")
            run(["git", "revert", "--abort"], repo); git(repo, "reset", "-q", "--hard", "origin/main")

        # ---- 3. push のあとで変更台帳に書けない回 → Telegram に出す → 翌朝の拾い直し
        run(["git", "push", "-q", "origin", f":refs/tags/auto/structure-{MONTH}"], repo)   # 同じ月にもう 1 回走らせるため
        run(["git", "tag", "-d", f"auto/structure-{MONTH}"], repo)
        led_file = ledger / "ledger" / "changes.jsonl"
        n_before = len(ledger_rows())
        led_file.parent.mkdir(parents=True, exist_ok=True); led_file.touch()   # 上の回が何も記帳していなくても、ここで落とさない
        led_file.chmod(0o444)
        # 1 回目の hub-order で /knowledge は構成レビューでも 14 日凍結（変更台帳の source=structure）＝2 回目はトップの節の順を変える
        r, tg = weekly_run("structure", "structure-top")
        led_file.chmod(0o644)
        log = main_log()
        b_sha = log[1][0] if len(log) > 1 and log[1][1].startswith("auto(structure): ") else ""
        check("記帳の失敗: 公開は済み（rc=0）・変更台帳は増えていない・Telegram に「台帳の記帳に失敗」（自動で測ると言い切らない）",
              r.returncode == 0 and b_sha and b_sha != s_sha and len(ledger_rows()) == n_before and "台帳の記帳に失敗" in tg
              and "register_auto_commits.py" in tg and "自動で測る" not in tg and f"git revert {b_sha[:10]}" in tg, tg[-220:])
        env_py = dict(base_env)
        rec = run(["python3", repo / "scripts" / "seo" / "register_auto_commits.py"], repo, env=env_py)
        rows = ledger_rows()
        new = rows[n_before:]
        check("拾い直し: 翌朝の収集が origin/main とその回のマニフェストから記帳する（source=structure・commit＝中身のコミット・id は重ならない）",
              rec.returncode == 0 and len(new) == 1 and new[0].get("commit") == b_sha and new[0].get("source") == "structure"
              and new[0].get("date") == str(TODAY) and new[0].get("recovered") is True and new[0].get("check_days") == [14, 28]
              and len({e["id"] for e in rows}) == len(rows), (rec.stdout + rec.stderr).strip()[:160])
        rec2 = run(["python3", repo / "scripts" / "seo" / "register_auto_commits.py"], repo, env=env_py)
        check("拾い直し: 2 回走っても重複しない・記帳済みの auto(seo)／auto(structure) のコミットは足さない",
              rec2.returncode == 0 and len(ledger_rows()) == n_before + 1, (rec2.stdout + rec2.stderr).strip()[:160])

        bad = [x for x in results if not x[0]]
        for ok_, name, tail in results:
            print(f"{'ok  ' if ok_ else 'FAIL'} {name}" + (f" — {tail}" if tail and not ok_ else ""))
        print(f"\n{len(results) - len(bad)}/{len(results)} 通過（一時ディレクトリ {tmp}{'・残す' if keep or bad else ''}）")
        if bad:
            keep = True
        return 1 if bad else 0
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
