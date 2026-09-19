#!/bin/bash
# weekly_run.sh — scix.co.jp の週次自動更新（launchd ai.scix.web-weekly・月曜 07:30）
#
# 2026-09-19 新設（中島「自動公開は承認しなくて公開していい。進めて」）。
# 流れ: 台帳を最新に → ブリーフ生成 → main の作業ツリーで Claude が判断・編集 → 機械の検査（guard_diff.py）
#       → 通ったものだけ commit/push（Vercel が公開）→ 本番反映を待って IndexNow → 台帳に記帳 → Telegram 3行。
# 止まる条件: 検査に落ちた／Claude が失敗した／push できない。どれも「公開しない」側に倒れる。
#
# Claude に渡す道具は allowedTools で絞る（読む・編集する・リポジトリ内の python3/grep を叩く）。
# git の commit/push/branch と Web 取得・サブエージェントは渡さない。公開はこのシェルだけが行う。
#
# 手で回す:      bash scripts/seo/weekly_run.sh
# 公開せず確認:  DRY_RUN=1 bash scripts/seo/weekly_run.sh   （作業ツリー ~/projects/.scix-web-weekly を残す）
# 差し戻し:      git revert <auto(seo) のコミット>  → push（IndexNow は Action が送る）
set -uo pipefail

REPO="${SCIX_WEB_REPO:-$HOME/projects/scix-web}"
LEDGER="${SCIX_WEB_LEDGER:-$HOME/マイドライブ/9_システム/scix-web解析}"
STATE="$HOME/.openclaw/workspace/state"
MODEL="${SCIX_WEB_MODEL:-claude-opus-5}"          # 判断の質に効く所は Opus。Fable は同じ仕事に枠5倍（2026-09-17 実測）
MAX_TURNS="${SCIX_WEB_MAX_TURNS:-250}"
TIMEOUT_SEC="${SCIX_WEB_TIMEOUT:-5400}"
DRY_RUN="${DRY_RUN:-0}"
TODAY="$(date +%F)"
RUN_DIR="$LEDGER/weekly/$TODAY"
WT="$HOME/projects/.scix-web-weekly"
LOCK="$STATE/web_weekly.lock"
TG_TARGET="8811825170"

log() { echo "$(date '+%F %T') $*"; }
notify() {
  openclaw message send --channel telegram --target "$TG_TARGET" --message "$1" >/dev/null 2>&1 \
    || log "Telegram 送信失敗（本文: ${1:0:120}）"
}
cleanup() {
  if [ "$DRY_RUN" != "1" ]; then
    git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"
    git -C "$REPO" worktree prune >/dev/null 2>&1
  fi
  rmdir "$LOCK" 2>/dev/null
}
fail() {
  log "NG $*"
  notify "🌐 scix.co.jp 週次自動更新 $TODAY: 失敗（$*）。公開はしていない。ログ: $RUN_DIR"
  cleanup; exit 1
}
mj() { python3 -c "import json,sys; j=json.load(open(sys.argv[1])); exec(sys.argv[2])" "$RUN_DIR/changes.json" "$1"; }

mkdir "$LOCK" 2>/dev/null || { log "前回の実行が残っている（$LOCK）。止める。"; exit 1; }
mkdir -p "$RUN_DIR"
cd "$REPO" || fail "リポジトリが無い: $REPO"
CC_DIR="$(python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.openclaw/openclaw.json")))["agents"]["defaults"]["cliBackends"]["claude-cli"]["env"]["CLAUDE_CONFIG_DIR"]))' 2>/dev/null || true)"
[ -n "$CC_DIR" ] && [ -d "$CC_DIR" ] || fail "CLAUDE_CONFIG_DIR が決まらない（openclaw.json）"

# 1. 台帳を最新にしてブリーフ
python3 scripts/seo/collect_daily.py --days 10 --no-health >>"$RUN_DIR/collect.log" 2>&1 || log "収集に一部失敗（続行）"
python3 scripts/seo/build_brief.py >>"$RUN_DIR/collect.log" 2>&1 || fail "ブリーフ生成"
[ -s "$RUN_DIR/brief.md" ] || fail "ブリーフが空"

# 2. 作業ツリー（origin/main の最新。人の未コミット作業と混ぜない）
git fetch -q origin main || fail "git fetch"
git worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"; git worktree prune >/dev/null 2>&1
git worktree add -q --detach "$WT" origin/main || fail "worktree を作れない"
BASE_SHA="$(git -C "$WT" rev-parse HEAD)"
[ -f "$WT/scripts/seo/guard_diff.py" ] || fail "origin/main に scripts/seo が無い"

# 3. Claude が判断して編集する（このアカウントの枠＝OpenClaw 用。中島さんの枠には落とさない）
#    道具は明示した分だけ。許可の無い道具は -p モードでは黙って拒否される＝止まる側に倒れる。
PROMPT="今週（$TODAY）の自動更新を実行してください。ブリーフ: $RUN_DIR/brief.md 。マニフェストの出力先: $RUN_DIR/changes.json 。作業ディレクトリ（リポジトリ）: $WT 。"
export CLAUDE_CONFIG_DIR="$CC_DIR"
unset CLAUDE_CODE_OAUTH_TOKEN
log "Claude 開始 model=$MODEL turns<=$MAX_TURNS timeout=${TIMEOUT_SEC}s"
( cd "$WT" && perl -e 'alarm shift; exec @ARGV' "$TIMEOUT_SEC" \
    claude -p "$PROMPT" --model "$MODEL" \
      --append-system-prompt-file "$WT/scripts/seo/weekly_prompt.md" \
      --permission-mode acceptEdits --strict-mcp-config \
      --allowedTools "Read" "Edit" "Write" "MultiEdit" "Glob" "Grep" "LS" "TodoWrite" \
        "Bash(python3 scripts/*)" "Bash(python3 -c *)" "Bash(grep *)" "Bash(rg *)" "Bash(ls *)" "Bash(wc *)" \
        "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(sed -n *)" "Bash(diff *)" "Bash(git status*)" \
        "Bash(git diff*)" "Bash(git log*)" "Bash(git show*)" "Bash(git add *)" "Bash(find *)" "Bash(sort *)" "Bash(uniq *)" \
      --max-turns "$MAX_TURNS" --output-format json \
    > "$RUN_DIR/claude_result.json" 2> "$RUN_DIR/claude_stderr.log" )
RC=$?
[ $RC -eq 0 ] || fail "Claude の実行が失敗（rc=$RC）: $(tail -c 300 "$RUN_DIR/claude_stderr.log" | tr '\n' ' ')"
python3 - "$RUN_DIR/claude_result.json" > "$RUN_DIR/claude_result.md" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
print(j.get("result", ""))
print(f"\n\n<!-- is_error={j.get('is_error')} cost_usd={j.get('total_cost_usd')} turns={j.get('num_turns')} duration_ms={j.get('duration_ms')} -->")
PY
log "Claude 終了: $(tail -1 "$RUN_DIR/claude_result.md")"

# 4. マニフェストと変更の有無
[ -s "$RUN_DIR/changes.json" ] || fail "マニフェスト changes.json が無い"
cd "$WT" || fail "作業ツリーへ移動できない"
git reset -q 2>/dev/null   # Claude が git add していても、こちらで add し直す
if ! git status --porcelain --untracked-files=all | grep -q . ; then
  REASON="$(mj 'print(j.get("no_change_reason") or "理由の記載なし")' 2>/dev/null)"
  log "今週は変更なし: $REASON"
  notify "🌐 scix.co.jp 週次自動更新 $TODAY: 今週は変更なし。$REASON"
  cleanup; exit 0
fi

# 5. 焼き直し → 検査 → sitemap
python3 scripts/gen_knowledge_jsonld.py --write >>"$RUN_DIR/collect.log" 2>&1 || fail "gen_knowledge_jsonld"
SCIX_WEB_REPO="$WT" python3 scripts/seo/guard_diff.py --manifest "$RUN_DIR/changes.json" > "$RUN_DIR/guard.log" 2>&1 \
  || fail "検査で止めた: $(grep -- '^ -' "$RUN_DIR/guard.log" | head -5 | tr '\n' ' ')"
HTML_CHANGED="$(git status --porcelain --untracked-files=all | awk '{print $2}' | grep -E '\.html$' || true)"
if [ -n "$HTML_CHANGED" ]; then
  # shellcheck disable=SC2086
  python3 scripts/seo/stamp_sitemap.py $HTML_CHANGED >>"$RUN_DIR/collect.log" 2>&1
fi

# 6. 公開リポジトリの変更日台帳に行を足す（コミットに含める）
python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" \
  --changelog "$WT/docs/seo-change-log.md" --dry-ledger >"$RUN_DIR/record.log" 2>&1 || fail "変更日台帳の記帳"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: 公開しない。作業ツリー $WT を残す。"
  git status --short
  rmdir "$LOCK" 2>/dev/null; exit 0
fi

# 7. commit → push（Vercel が数分で公開。commit email は GitHub と一致させないと Vercel が Blocked にする）
TITLE="$(mj 'print((j.get("summary_lines") or ["自動更新"])[0][:70])')"
BODY="$(mj 'print("\n".join("- "+l for l in j.get("summary_lines",[]))); print(); print("\n".join("- "+", ".join(c.get("files",[]))+": "+str(c.get("summary","")) for c in j.get("changes",[])))')"
git add -A -- . ':!.claude' || fail "git add"
git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" commit -q -F - <<EOF2 || fail "commit"
auto(seo): $TITLE

$BODY

scripts/seo/weekly_run.sh による週次自動更新。ブリーフとマニフェスト: 9_システム/scix-web解析/weekly/$TODAY
差し戻し: git revert <このコミット>
EOF2
SHA="$(git rev-parse HEAD)"
git tag -f "auto/weekly-$TODAY" >/dev/null 2>&1
git push -q origin HEAD:main || fail "push（commit $SHA は作業ツリーに残っている）"
git push -q origin "auto/weekly-$TODAY" >/dev/null 2>&1 || true
log "公開 push 済み $SHA"
python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" --commit "$SHA" \
  >>"$RUN_DIR/record.log" 2>&1 || log "台帳の記帳に失敗（公開は済んでいる）"

# 8. 本番反映を待って IndexNow（Action も送るが、ここでも送って二重化。Bing は重複を受け付ける）
DEPLOYED=0
for i in $(seq 1 30); do
  sleep 20
  if curl -fsS -H 'Cache-Control: no-cache' https://www.scix.co.jp/sitemap.xml 2>/dev/null | grep -q "<lastmod>$TODAY</lastmod>"; then DEPLOYED=1; break; fi
done
[ "$DEPLOYED" = "1" ] && log "本番に反映を確認" || log "本番反映を10分待ったが sitemap に今日の lastmod が見えない（Action 側の送信に任せる）"
python3 scripts/ping_indexnow.py --changed-since "$BASE_SHA" >>"$RUN_DIR/collect.log" 2>&1 || log "IndexNow 送信失敗"

# 9. 通知（3行＋コミット）
LINES="$(mj 'print("\n".join("・"+l for l in j.get("summary_lines",[])[:3]))')"
notify "🌐 scix.co.jp 週次自動更新 $TODAY（公開済み）
$LINES
https://github.com/nakashimashinya-a11y/scix-web/commit/${SHA:0:10}
差し戻すなら: git revert ${SHA:0:10} → push。ブリーフ: 9_システム/scix-web解析/weekly/$TODAY/"
log "OK 週次自動更新 完了 $SHA"
cleanup
exit 0
