#!/bin/bash
# weekly_run.sh — scix.co.jp の週次自動更新（launchd ai.scix.web-weekly・日曜 06:00）
#
# 2026-09-19 新設（中島「自動公開は承認しなくて公開していい。進めて」）。
# 流れ: 台帳を最新に → ブリーフ生成 → main の作業ツリーで Claude が判断・編集 → 機械の検査（guard_diff.py）
#       → 通ったものだけ commit/push（Vercel が公開）→ 本番反映を待って IndexNow → 台帳に記帳 → Telegram 3行。
# 止まる条件: 検査に落ちた／Claude が失敗した／push できない。どれも「公開しない」側に倒れる。
# 公開は 2 コミット: ①中身（auto(seo): ／ auto(structure): …。Claude の編集と焼き直し）②記帳（chore(seo-log): …。sitemap の
#   lastmod と公開リポジトリの変更日台帳 docs/seo-change-log.md）。変更日台帳は毎週、表の同じ位置に行が足されるので、①に混ぜると
#   案内している差し戻し `git revert <sha>` が次の自動コミット 1 つで必ず衝突する。Telegram・タグ・変更台帳の commit は ①を指す。
# push のあとの変更台帳（Drive）への記帳は 3 回までやり直し、だめなら Telegram に出す。翌朝の収集が拾い直す（register_auto_commits.py）。
#
# Claude に渡す道具は allowedTools で絞る（読む・編集する・リポジトリ内の python3/grep を叩く）。
# git の commit/push/branch と Web 取得・サブエージェントは渡さない。公開はこのシェルだけが行う。
#
# 手で回す:      bash scripts/seo/weekly_run.sh
# 公開せず確認:  DRY_RUN=1 bash scripts/seo/weekly_run.sh   （作業ツリー ~/projects/.scix-web-weekly を残す）
# 差し戻し:      git revert <auto(seo) のコミット>  → push（IndexNow は Action が送る）
#
# コラムは書かない（2026-09-20 中島「Column は僕が書くから君は書かない」）: 週次も構成レビューも新しいページを作らない
#   （guard_diff.py が新規ファイルと class=new-column を止める）。足りない主題は column_ideas で Telegram に 1 行出すだけ。
#   中島さんが足したコラムの育成（内部リンク・ハブカード・新着・sitemap・JA_ONLY_COLUMNS の登録漏れ）は週次が続ける。
#
# 月1回の構成レビュー（MODE=structure・2026-09-20 追加。中島「ページのアクセスや検索ヒットをみて、ページ構成や流れを変えて、
#   よりヒットを多くする、問い合わせを多くするを検索エンジン対策を含めて自動でやってほしい」）:
#   月の第1日曜は、通常の週次が終わったあと、同じこのスクリプトが続けて MODE=structure を1回だけ走らせる
#   （新しい launchd は作らない）。構成（ハブの並び・トップの節の順・CTA の行き先・収益ページへの導線）の見直しを
#   Claude が 1〜3 件に絞って編集 → 検査（guard_diff.py --profile structure）→ **通れば週次と同じ手順で自動公開**:
#   最新の origin/main へ載せ直し（衝突したら公開しない）→ push → タグ auto/structure-YYYY-MM → 手元の main を早送り →
#   変更台帳に source=structure・check_days [14, 28] で記帳（14 日後・28 日後に前後比較。worse は翌週のブリーフ 8 節で差し戻し候補。
#   判定は GSC のクリックと CTR＝問い合わせ・送客の減りは 8 節の表の「注意」で週次が読む）
#   → Telegram 3 行（何を変えたか・根拠・戻し方 git revert <sha>）。IndexNow は push 時の GitHub Action が送る。
#   **例外: ナビ（header.js）を含む回は自動公開しない**（全ページに効く）。その回は全体を従来どおり枝 auto/structure-YYYY-MM へ
#   push して gh pr create（マージで公開・閉じれば不採用。一部だけ公開、をしない＝検査済みの単位を崩さない）。台帳は
#   「提案（未公開）」として ledger/proposals.jsonl、マージ後の記帳は毎朝の register_structure_merges.py。
#   週次は子プロセスで今までどおり走り、終了コードもそのまま返す＝構成レビューが失敗しても週次の結果は壊れない。
#   頻度が月1回の理由: Google の反映に 1〜2 週・効果測定に 2〜4 週・同じページを 14 日以内に 2 度変えない。
#   手で回す:  MODE=structure bash scripts/seo/weekly_run.sh        （日付に関係なく1回。今月のタグか枝が origin にあれば何もしない）
#   確認だけ:  MODE=structure DRY_RUN=1 bash scripts/seo/weekly_run.sh  （push も記帳も PR もしない。作業ツリー ~/projects/.scix-web-structure と proposal.diff を残す）
#   止める:    NO_STRUCTURE=1（第1日曜でも続けて走らせない）
#   戻す:      git revert <auto(structure) のコミット> → push
# 変数の直後に全角文字が続くときは ${VAR} と書く: /bin/bash 3.2 は UTF-8 のロケール（手で回す Terminal）だと「$VAR）」の
#   全角の 1 バイト目を変数名に含めてしまい、set -u で「VAR\357: unbound variable」になって止まる（launchd は LANG 無し＝出ない）。
#   selftest_publish.py が UTF-8 のロケールで一周させ、この書き方が残っていないことも見る。
set -uo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
MODE="${MODE:-weekly}"                             # weekly＝通常の週次／structure＝月1回の構成レビュー。どちらも検査を通れば公開（ナビを含む回だけ PR）
case "$MODE" in weekly|structure) ;; *) echo "MODE は weekly か structure（指定: ${MODE}）" >&2; exit 2 ;; esac
REPO="${SCIX_WEB_REPO:-$HOME/projects/scix-web}"
LEDGER="${SCIX_WEB_LEDGER:-$HOME/マイドライブ/9_システム/scix-web解析}"
STATE="${SCIX_WEB_STATE:-$HOME/.openclaw/workspace/state}"
MODEL="${SCIX_WEB_MODEL:-claude-opus-5-5}"        # 判断の質に効く所は Opus（2026-09-23〜 Opus 5.5）。Fable は同じ仕事に枠5倍（2026-09-17 実測）
EFFORT="${SCIX_WEB_EFFORT:-high}"                  # 思考の強さ（2026-09-25〜 Opus のジョブは high。対外の本文は Fable max）
MAX_TURNS="${SCIX_WEB_MAX_TURNS:-250}"
TIMEOUT_SEC="${SCIX_WEB_TIMEOUT:-5400}"
DRY_RUN="${DRY_RUN:-0}"
TODAY="$(date +%F)"
RUN_DIR="$LEDGER/weekly/$TODAY"
WT="${SCIX_WEB_WT:-$HOME/projects/.scix-web-weekly}"
LABEL="週次自動更新"
if [ "$MODE" = "structure" ]; then                 # 同じ日の週次の成果物（brief.md・changes.json・DRY_RUN の作業ツリー）を上書きしない
  RUN_DIR="$LEDGER/weekly/$TODAY/structure"
  WT="${SCIX_WEB_WT_STRUCTURE:-$HOME/projects/.scix-web-structure}"
  LABEL="構成レビュー"
fi
BASE_REF="${SCIX_WEB_BASE_REF:-origin/main}"       # 試験のときだけ別ブランチを指定できる
LOCK="$STATE/web_weekly.lock"                      # 週次と構成レビューで共用（同じリポジトリの worktree と fetch を同時に触らせない）

log() { echo "$(date '+%F %T') $*"; }
# 月の第1日曜か（launchd は日曜にしか起こさないが、手で回した日にも続けて走らないよう曜日も見る）
structure_due() {
  [ "${NO_STRUCTURE:-0}" = "1" ] && return 1
  [ "${FORCE_STRUCTURE:-0}" = "1" ] && return 0
  local dom dow
  dom="${SCIX_WEB_DOM:-$(date +%d)}"; dow="${SCIX_WEB_DOW:-$(date +%u)}"
  [ "$dow" = "7" ] && [ "$((10#$dom))" -ge 1 ] && [ "$((10#$dom))" -le 7 ]
}

# ---- 入口: 通常の週次は子プロセスで今までどおり走らせ、第1日曜だけ続けて構成レビューを1回走らせる。
if [ "$MODE" = "weekly" ] && [ "${SCIX_WEB_CHILD:-0}" != "1" ]; then
  SCIX_WEB_CHILD=1 MODE=weekly /bin/bash "$SELF"; WEEKLY_RC=$?
  if structure_due; then
    log "月の第1日曜: 通常の週次（rc=${WEEKLY_RC}）に続けて、構成レビュー（MODE=structure）を走らせる"
    SCIX_WEB_CHILD=1 SCIX_WEB_AFTER_WEEKLY=1 MODE=structure /bin/bash "$SELF" \
      || log "構成レビューは失敗か見送り（週次の結果 rc=$WEEKLY_RC には影響しない）"
  fi
  exit $WEEKLY_RC
fi
TG_GATE="${SCIX_TG_GATE:-$HOME/.openclaw/workspace/bin/tg_gate.py}"   # Telegram の関所（リポジトリの外。宛先も関所が持つ）
notify() {  # $1=本文 $2=種類（undo＝公開の戻し方・ask＝1問） $3=key（同じ用件は1回だけ）
  # Telegram は tg_gate を通す（種類・上限・送信台帳＝O13-2・O13-26・O13-27）。出せない種類は関所が行動ログに回す。
  #   失敗・変化なしは Telegram に出さず行動ログへ1行（applog）。
  if [ ! -f "$TG_GATE" ]; then log "Telegram の関所が無い（${TG_GATE}）。送らずに続ける"; return 0; fi
  local rc=0
  printf '%s' "$1" | python3 "$TG_GATE" send --kind "$2" --job web-weekly --key "$3" --message - --apply >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0) ;;
    6) log "Telegram: 同じ知らせは送り済みか上限（key=$3）" ;;
    9) log "Telegram: 届いたか不明（key=$3・送り直さない）" ;;
    *) log "Telegram 送信失敗 rc=${rc}（key=$3）" ;;
  esac
}
applog() {  # 行動ログに1行（O13-3）。Telegram には出さない
  [ -f "$TG_GATE" ] || return 0
  printf '%s' "$1" | python3 "$TG_GATE" send --kind log --job web-weekly --key "web-weekly-log:$(date +%F-%H%M%S)" --message - --apply >/dev/null 2>&1 || log "行動ログに書けない"
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
  log "失敗のため公開していない。朝ルーチンが bundle ⑦ でこのログを読む（Telegram には出さない）"
  applog "scix.co.jp ${MODE:-weekly} の自動更新は失敗して公開していない: $*"
  cleanup; exit 1
}
mj() { python3 -c "import json,sys; j=json.load(open(sys.argv[1])); exec(sys.argv[2])" "$RUN_DIR/changes.json" "$1"; }
# 今週書くコラムの主題（マニフェスト column_ideas の先頭）。中島「して。毎週日曜の6amに」（2026-09-20）
idea_line() {
  mj 'ideas=j.get("column_ideas") or []
i=ideas[0] if ideas else None
print(("✍️ 今週書くなら: "+str(i.get("title",""))+"（"+str(i.get("for",""))+"向け・"+("3言語" if str(i.get("langs"))=="3" else "JA")+"）— "+str(i.get("why",""))) if i else "✍️ 今週の主題提案: なし")' 2>/dev/null || echo "✍️ 今週の主題提案: 取得失敗"
}

# アクセスが減ったページ（ブリーフ 11 節＝brief.json の access_drops）。中島決定 2026-09-22:
#   トリガーはアクセス減。週次の Claude は外に出られないので本文の時点更新は自動でやらず、先頭の 1 本（原因の型・本文の時点つき）と本数を
#   1 行で知らせる。時点更新は CC の作業セッションで。
drop_line() {
  python3 - "$RUN_DIR/brief.json" <<'PY' 2>/dev/null || true
import json, sys
try:
    rows = json.load(open(sys.argv[1])).get("access_drops") or []
except Exception:
    rows = []
if rows:
    r = rows[0]
    f = lambda x: "-" if x is None else "%.1f" % x
    asof = ("%s＝%s日前" % (r.get("expr"), r.get("age_days"))) if r.get("expr") else "時点表現なし"
    more = " ほか%d本" % (len(rows) - 1) if len(rows) > 1 else ""
    print("📉 アクセスが減った: %s（28日 %s→%s・%+d%%・%s %s→%s位・%s）%s → %s。時点更新は CC の作業セッションで（週次は title・description まで）"
          % (r.get("page"), r.get("clicks_prev"), r.get("clicks_cur"), r.get("pct") or 0, r.get("judge"),
             f(r.get("pos_prev")), f(r.get("pos_cur")), asof, more, r.get("next")))
PY
}

# Claude が判断して編集する（このアカウントの枠＝OpenClaw 用。中島さんの枠には落とさない）。週次も構成レビューも同じ条件で起こす。
#    道具は明示した分だけ。許可の無い道具は -p モードでは黙って拒否される＝止まる側に倒れる。
run_claude() {  # $1=ユーザープロンプト  $2=システムプロンプトのファイル（作業ツリーの中）
  export CLAUDE_CONFIG_DIR="$CC_DIR"
  unset CLAUDE_CODE_OAUTH_TOKEN
  log "Claude 開始 model=$MODEL effort=$EFFORT turns<=$MAX_TURNS timeout=${TIMEOUT_SEC}s"
  ( cd "$WT" && perl -e 'alarm shift; exec @ARGV' "$TIMEOUT_SEC" \
      claude -p "$1" --model "$MODEL" --effort "$EFFORT" \
        --append-system-prompt-file "$2" \
        --permission-mode acceptEdits --strict-mcp-config \
        --allowedTools "Read" "Edit" "Write" "MultiEdit" "Glob" "Grep" "LS" "TodoWrite" \
          "Bash(python3 scripts/*)" "Bash(python3 -c *)" "Bash(grep *)" "Bash(rg *)" "Bash(ls *)" "Bash(wc *)" \
          "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(sed -n *)" "Bash(diff *)" "Bash(git status*)" \
          "Bash(git diff*)" "Bash(git log*)" "Bash(git show*)" "Bash(git add *)" "Bash(find *)" "Bash(sort *)" "Bash(uniq *)" \
        --max-turns "$MAX_TURNS" --output-format json \
      > "$RUN_DIR/claude_result.json" 2> "$RUN_DIR/claude_stderr.log" )
  RC=$?
  [ $RC -eq 0 ] || fail "Claude の実行が失敗（rc=${RC}）: $(tail -c 300 "$RUN_DIR/claude_stderr.log" | tr '\n' ' ')"
  python3 - "$RUN_DIR/claude_result.json" > "$RUN_DIR/claude_result.md" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
print(j.get("result", ""))
print(f"\n\n<!-- is_error={j.get('is_error')} cost_usd={j.get('total_cost_usd')} turns={j.get('num_turns')} duration_ms={j.get('duration_ms')} -->")
PY
  log "Claude 終了: $(tail -1 "$RUN_DIR/claude_result.md")"
}

# 公開（週次と、構成レビューの自動公開の経路で共用）。呼ぶ前に: 作業ツリー（cwd）で commit 済み・BASE_SHA＝作業ツリーを切った時点の origin/main。
# Claude が作業している間（最長90分）に main が進んでいることがある（毎朝06:50 の案件一覧の同期など）。
# そのまま push すると non-fast-forward で弾かれるので、先に最新の origin/main へ載せ直す。載せ直しで衝突したら公開しない（安全側）。
# 終わると SHA に **中身のコミット**（auto(seo): ／ auto(structure):）が入っている＝差し戻しで revert する対象。
# その上に記帳用のコミット（commit_log）が載っていても、タグ・Telegram・変更台帳の commit は中身のコミットを指す。
publish_main() {  # $1=タグ名
  git fetch -q origin || fail "push 前の git fetch"
  if [ "$(git rev-parse origin/main)" != "$BASE_SHA" ]; then
    log "作業中に main が進んだ（$BASE_SHA → $(git rev-parse --short origin/main)）。載せ直す。"
    git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" rebase -q origin/main \
      || { git rebase --abort >/dev/null 2>&1; fail "push 前の載せ直しで衝突した（公開していない）"; }
  fi
  SHA="$(git rev-list --reverse origin/main..HEAD | head -1)"   # 載せ直しのあとの、最初の 1 つ＝中身のコミット
  [ -n "$SHA" ] || fail "公開するコミットが無い"
  git tag -f "$1" "$SHA" >/dev/null 2>&1
  git push -q origin HEAD:main || fail "push（commit $SHA は作業ツリーに残っている）"
  git push -q origin "refs/tags/$1" >/dev/null 2>&1 || log "タグ $1 を push できなかった（公開は済んでいる）"
  log "公開 push 済み $SHA"
  # 手元の main を追いつかせる。これをしないと、06:50 の案件一覧の同期（手元の main に commit して push）が
  # non-fast-forward で弾かれ、以後ずっと手元と本番が分かれたままになる。main 以外に居るときは触らない。
  if [ "$(git -C "$REPO" rev-parse --abbrev-ref HEAD)" = "main" ]; then
    git -C "$REPO" pull -q --ff-only origin main >/dev/null 2>&1 || log "手元の main を追いつかせられなかった（次の同期が pull する）"
  fi
}

# 記帳用のコミット（sitemap の lastmod・公開リポジトリの変更日台帳）。呼ぶ前に: 中身をコミット済み・cwd＝作業ツリー・
# HTML_CHANGED＝マニフェストの HTML。中身のコミットと分ける理由は冒頭（差し戻しの git revert が後続の行と衝突しないように）。
stamp_and_log() {  # $1=record_changes.py の --source（auto|structure）
  if [ -n "$HTML_CHANGED" ]; then
    # shellcheck disable=SC2086
    python3 scripts/seo/stamp_sitemap.py $HTML_CHANGED >>"$RUN_DIR/collect.log" 2>&1
  fi
  python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" --source "$1" \
    --changelog "$WT/docs/seo-change-log.md" --dry-ledger >"$RUN_DIR/record.log" 2>&1 || fail "変更日台帳の記帳"
}
commit_log() {  # $1=--source  $2=中身のコミットの件名の接頭辞（auto(seo)|auto(structure)）
  local CONTENT
  CONTENT="$(git rev-parse --short=10 HEAD)"
  stamp_and_log "$1"
  git add -A -- . ':!.claude' || fail "git add（記帳）"
  git diff --cached --quiet && return 0
  git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" commit -q -F - <<EOF5 || fail "commit（記帳）"
chore(seo-log): $2 の sitemap lastmod と変更日台帳

中身のコミット（載せ直す前）: $CONTENT 。差し戻すときは中身のコミットだけを git revert する（この記帳は記録として残す）。
EOF5
}
# push のあとの変更台帳（Drive の ledger/changes.jsonl）への記帳。3 回までやり直す。だめなら 1（呼ぶ側が Telegram に出す。
# 翌朝の収集 register_auto_commits.py が origin/main とこの回のマニフェストから拾い直す＝効果測定から黙って外れない）。
record_ledger() {  # $1=--source
  local i
  for i in 1 2 3; do
    python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" --source "$1" --commit "$SHA" \
      >>"$RUN_DIR/record.log" 2>&1 && return 0
    log "台帳の記帳に失敗（$i 回目・公開は済んでいる）: $(tail -1 "$RUN_DIR/record.log" 2>/dev/null)"
    [ "$i" = "3" ] || sleep 5
  done
  return 1
}

# ---------------------------------------------------------------- 月1回の構成レビュー（MODE=structure）
# 検査を通れば週次と同じ手順で自動公開する（2026-09-20 中島。提案で止めない）。例外はナビ（header.js）を含む回だけ:
# 全ページに効くので、その回は全体を枝 auto/structure-YYYY-MM へ push → gh pr create（main・変更台帳・変更日台帳には触らない）。
run_structure() {
  local MONTH BRANCH TAG TITLE BODY PR_TITLE PR_URL PR_NUM LINE1 LINE2 LINE3 LEDGER_NOTE REASON ROUTE
  MONTH="$(date +%Y-%m)"
  BRANCH="${SCIX_WEB_STRUCTURE_BRANCH:-auto/structure-$MONTH}"   # PR の経路の枝
  TAG="auto/structure-$MONTH"                                    # 自動公開の経路のタグ（1か月に1回の目印も兼ねる）
  mkdir "$LOCK" 2>/dev/null || { log "前回の実行が残っている（${LOCK}）。構成レビューは見送る。"; exit 1; }
  mkdir -p "$RUN_DIR"
  cd "$REPO" || fail "リポジトリが無い: $REPO"
  CC_DIR="$(python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.openclaw/openclaw.json")))["agents"]["defaults"]["cliBackends"]["claude-cli"]["env"]["CLAUDE_CONFIG_DIR"]))' 2>/dev/null || true)"
  [ -n "$CC_DIR" ] && [ -d "$CC_DIR" ] || fail "CLAUDE_CONFIG_DIR が決まらない（openclaw.json）"
  [ "$(cd "$CC_DIR" && pwd -P)" != "$(cd "$HOME/.claude" && pwd -P)" ] || fail "CLAUDE_CONFIG_DIR が中島さんの枠（~/.claude）を指している（共通ルール O14-10）"

  # 1. ブリーフ（通常の節＋構成レビュー用の S1〜S8）。週次の直後なら台帳は取り直さない
  if [ "${SCIX_WEB_AFTER_WEEKLY:-0}" != "1" ] && [ "${NO_COLLECT:-0}" != "1" ]; then
    python3 scripts/seo/collect_daily.py --days 10 --no-health >>"$RUN_DIR/collect.log" 2>&1 || log "収集に一部失敗（続行）"
  fi
  python3 scripts/seo/build_brief.py --structure >>"$RUN_DIR/collect.log" 2>&1 || fail "ブリーフ生成（--structure）"
  [ -s "$RUN_DIR/brief.md" ] || fail "ブリーフが空"

  # 2. 今月ぶんがもう出ているなら走らせない（1か月に1回だけ。公開済み＝タグ／PR で提案中＝枝）→ 作業ツリー
  git fetch -q origin || fail "git fetch"
  if [ "$DRY_RUN" != "1" ]; then
    if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
      log "今月の構成レビューは公開済み（タグ ${TAG}）。1か月に1回だけ＝何もしない。"
      rmdir "$LOCK" 2>/dev/null; exit 0
    fi
    if git ls-remote --exit-code --heads origin "refs/heads/$BRANCH" >/dev/null 2>&1; then
      log "今月の提案の枝が既にある（${BRANCH}）。構成レビューは1か月に1回だけ＝何もしない。出し直すなら PR を閉じて枝を消す。"
      rmdir "$LOCK" 2>/dev/null; exit 0
    fi
  fi
  git worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"; git worktree prune >/dev/null 2>&1
  git worktree add -q --detach "$WT" "$BASE_REF" || fail "worktree を作れない（${BASE_REF}）"
  BASE_SHA="$(git -C "$WT" rev-parse HEAD)"
  [ -f "$WT/scripts/seo/structure_prompt.md" ] || fail "$BASE_REF に scripts/seo/structure_prompt.md が無い"

  # 3. Claude（アカウント・道具・モデルは週次と同じ）
  run_claude "今月（${MONTH}）の構成レビューを実行してください。ブリーフ: $RUN_DIR/brief.md 。マニフェストの出力先: $RUN_DIR/changes.json 。作業ディレクトリ（リポジトリ）: $WT 。検査は python3 scripts/seo/guard_diff.py --manifest $RUN_DIR/changes.json --profile structure 。" \
    "$WT/scripts/seo/structure_prompt.md"

  # 4. マニフェストと変更の有無。変更の有無は **マニフェストの changes の件数** で決める（git status だけで決めない）:
  #    Claude は仕上げで gen_knowledge_jsonld.py --write を走らせる。そのあと変更を取り下げて changes: [] にしても、
  #    焼き直しの差分（NEW バッジの期限切れ・ItemList の順）は作業ツリーに残る（git checkout／restore は渡していない）。
  #    それを「変更あり」と読むと、中身のない公開（か PR）が出て、その月の 1 回を使ってしまう。
  [ -s "$RUN_DIR/changes.json" ] || fail "マニフェスト changes.json が無い"
  cd "$WT" || fail "作業ツリーへ移動できない"
  git reset -q 2>/dev/null
  N_CHANGES="$(mj 'c=j.get("changes"); print(len(c) if isinstance(c, list) else 0)' 2>/dev/null)"
  case "$N_CHANGES" in ''|*[!0-9]*) fail "マニフェスト changes.json を読めない（JSON が壊れている）" ;; esac
  if [ "$N_CHANGES" = "0" ] || ! git status --porcelain --untracked-files=all | grep -q . ; then
    REASON="$(mj 'print(j.get("no_change_reason") or "理由の記載なし")' 2>/dev/null)"
    if [ "$N_CHANGES" = "0" ] && git status --porcelain --untracked-files=all | grep -q . ; then
      log "マニフェストは 0 件。作業ツリーに残っている差分は焼き直しだけ＝公開も PR もしない: $(git status --porcelain --untracked-files=all | head -5 | tr '\n' ' ')"
    fi
    log "今月は構成の変更なし: $REASON"
    applog "scix.co.jp 構成レビュー（${MONTH}）: 変更なし（${REASON}）"
    cleanup; exit 0
  fi

  # 5. 焼き直し → 検査（構成レビューのプロファイル）→ 経路。ナビ（header.js）を含む回は全体を PR へ（一部だけ公開、をしない）。
  #    経路は検査の出力と、シェル自身が見た差分・マニフェストの両方で決める（どちらかが PR と言えば PR＝公開しない側に倒す）
  python3 scripts/gen_knowledge_jsonld.py --write >>"$RUN_DIR/collect.log" 2>&1 || fail "gen_knowledge_jsonld"
  SCIX_WEB_REPO="$WT" python3 scripts/seo/guard_diff.py --manifest "$RUN_DIR/changes.json" --profile structure > "$RUN_DIR/guard.log" 2>&1 \
    || fail "検査で止めた: $(grep -- '^ -' "$RUN_DIR/guard.log" | head -5 | tr '\n' ' ')"
  ROUTE="publish"
  grep -q '^経路: 自動公開' "$RUN_DIR/guard.log" || ROUTE="pr"
  git status --porcelain --untracked-files=all -- header.js | grep -q . && ROUTE="pr"
  [ "$(mj 'print(int(any(c.get("class") == "nav" or "header.js" in (c.get("files") or []) for c in j.get("changes") or [])))' 2>/dev/null)" = "0" ] || ROUTE="pr"
  log "検査 OK。経路: ${ROUTE}（$(grep '^経路:' "$RUN_DIR/guard.log" | tail -1)）"
  TITLE="$(mj 'print(str(j.get("proposal_title") or (j.get("summary_lines") or ["構成の見直し"])[0])[:64])')"
  LINE1="$(mj 'print(str((j.get("summary_lines") or [""])[0])[:140])' 2>/dev/null)"

  if [ "$ROUTE" = "publish" ]; then
    # ---- 自動公開の経路（週次と同じ扱い: ①中身のコミット ②記帳のコミット＝sitemap の lastmod・公開リポジトリの変更日台帳）
    HTML_CHANGED="$(mj 'print("\n".join(f for c in j.get("changes",[]) for f in c.get("files",[])))' | grep -E '\.html$' | sort -u || true)"
    git add -A -- . ':!.claude' || fail "git add"
    git diff --cached > "$RUN_DIR/proposal.diff" 2>/dev/null
    if [ "$DRY_RUN" = "1" ]; then
      stamp_and_log structure   # 記帳のコミットに入るはずの差分（sitemap・変更日台帳）も作業ツリーに残す（proposal.diff は中身だけ）
      log "DRY_RUN: 経路は自動公開。push も記帳もしない。作業ツリー $WT と $RUN_DIR/proposal.diff を残す。題: auto(structure): $TITLE"
      git status --short
      rmdir "$LOCK" 2>/dev/null; exit 0
    fi
    BODY="$(mj 'print("\n".join("- "+l for l in (j.get("summary_lines") or [])[:3])); print(); print("\n".join("- "+", ".join(c.get("files",[]))+": "+str(c.get("summary","")) for c in j.get("changes",[])))')"
    git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" commit -q -F - <<EOF4 || fail "commit"
auto(structure): $TITLE

$BODY

scripts/seo/weekly_run.sh（MODE=structure）による月1回の構成レビュー（検査を通ったので自動公開）。
ブリーフとマニフェスト: 9_システム/scix-web解析/weekly/$TODAY/structure
差し戻し: git revert <このコミット>（sitemap の lastmod と変更日台帳は次の chore(seo-log) に分けてある＝衝突しない）
EOF4
    commit_log structure "auto(structure)"
    publish_main "$TAG"
    # 通知（1通3行: 何を変えたか・根拠・戻し方）。IndexNow は push 時の GitHub Action が送る
    LINE2="$(mj 'c=(j.get("changes") or [{}])[0]; print(str(c.get("rationale") or "")[:140])' 2>/dev/null)"
    LINE3="戻すなら: git revert ${SHA:0:10} → push（14 日後・28 日後に自動で測る。GSC の判定が worse なら週次が戻し、問い合わせ・送客の減りは週次ブリーフ 8 節の表で見て戻す）"
    LEDGER_NOTE=""
    if ! record_ledger structure; then
      LINE3="⚠️ 公開は済んだが台帳の記帳に失敗＝まだ効果測定の対象になっていない（明朝の収集 register_auto_commits.py が拾い直す）。戻すなら: git revert ${SHA:0:10} → push"
      LEDGER_NOTE="・⚠️ 台帳の記帳は失敗＝明朝の収集が拾い直す"
    fi
    notify "🧭 scix.co.jp 構成を見直して公開しました（${MONTH}）: $LINE1
根拠: $LINE2
$LINE3" undo "web-structure:${MONTH}"
    log "OK 構成レビュー 完了（自動公開${LEDGER_NOTE}）$TAG $SHA"
    cleanup
    exit 0
  fi

  # ---- PR の経路（ナビを含む回）。sitemap の lastmod と変更日台帳は PR に入れない
  #    （毎朝の案件一覧の同期・毎週の自動更新が同じ行を書くので、PR が開いている間に衝突する）
  git add -A -- . ':!.claude' || fail "git add"
  git diff --cached > "$RUN_DIR/proposal.diff" 2>/dev/null

  # PR の題と本文（公開リポジトリに載る＝マニフェストの公開欄だけ。private_note は載せない）
  PR_TITLE="auto(structure): $TITLE"
  python3 - "$RUN_DIR/changes.json" "$MONTH" "$TODAY" "$(tail -1 "$RUN_DIR/guard.log")" > "$RUN_DIR/pr_body.md" <<'PY' || fail "PR 本文の生成"
import json, sys
j = json.load(open(sys.argv[1])); month, today, guard = sys.argv[2], sys.argv[3], sys.argv[4]
L = [f"## 構成の見直し案（{month}・月1回の自動レビュー）", "",
     "ナビ（`header.js`）を含むので自動公開していません（全ページに効くため）。同じ回のほかの変更もまとめてここに入っています。", ""]
L += [f"- {l}" for l in (j.get("summary_lines") or [])[:3]]
for n, c in enumerate(j.get("changes") or [], 1):
    L += ["", f"### {n}. {c.get('summary', '')}", "",
          f"- 種別: `{c.get('class')}`／ファイル: {', '.join('`' + f + '`' for f in c.get('files') or [])}",
          f"- **根拠の数字**: {c.get('rationale', '')}"]
    if c.get("hypothesis"):
        L.append(f"- 仮説: {c['hypothesis']}")
    L += [f"- **何が増えれば成功か**: {c.get('kpi', '')}", f"- **いつ測るか**: {c.get('measure', '')}"]
    if c.get("before") or c.get("after"):
        L.append(f"- 変更前: {c.get('before', '')}／変更後: {c.get('after', '')}")
    if isinstance(c.get("nav_rule"), dict):
        L.append(f"- ナビの90日ルール: 申告 last_nav_change={c['nav_rule'].get('last_nav_change')}（検査が変更台帳と origin/main の履歴で照合済み）")
L += ["", "---", "", "**マージで公開、閉じれば不採用。**", "",
      f"- 機械の検査（`guard_diff.py --profile structure`）: {guard}",
      "- マージされると、翌朝の収集（`register_structure_merges.py`）が変更台帳へ記帳し、14日後・28日後に効果測定します。"
      "sitemap の lastmod と `docs/seo-change-log.md` はこの PR に入れていません（毎朝・毎週の自動コミットと同じ行で衝突するため）。",
      f"- ブリーフとマニフェスト: Drive `9_システム/scix-web解析/weekly/{today}/structure/`",
      "- 開いている間に main と衝突したら、閉じてください（翌月、その時点の数字でまた見直されます）。",
      "", "🤖 Generated with [Claude Code](https://claude.com/claude-code)"]
print("\n".join(L))
PY

  if [ "$DRY_RUN" = "1" ]; then
    log "DRY_RUN: 経路は PR（ナビを含む）。push も PR もしない。作業ツリー $WT と $RUN_DIR/proposal.diff・pr_body.md を残す。題: $PR_TITLE"
    git status --short
    rmdir "$LOCK" 2>/dev/null; exit 0
  fi

  # 6. commit → 枝へ push（main には push しない）→ PR
  git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" commit -q -F - <<EOF3 || fail "commit"
$PR_TITLE

$(mj 'print("\n".join("- "+l for l in (j.get("summary_lines") or [])[:3]))')

scripts/seo/weekly_run.sh（MODE=structure）による月1回の構成レビュー。ナビ（header.js）を含むので自動公開せず PR で提案。マージで公開、閉じれば不採用。
ブリーフとマニフェスト: 9_システム/scix-web解析/weekly/$TODAY/structure
EOF3
  SHA="$(git rev-parse HEAD)"
  git push -q origin "HEAD:refs/heads/$BRANCH" || fail "枝 $BRANCH への push（commit $SHA は作業ツリーに残っている）"
  log "提案の枝を push 済み $BRANCH ${SHA}（main には push していない）"
  PR_URL=""; PR_NUM=""
  if command -v gh >/dev/null 2>&1; then
    PR_URL="$(gh pr create --base main --head "$BRANCH" --title "$PR_TITLE" --body-file "$RUN_DIR/pr_body.md" 2>>"$RUN_DIR/gh.log" | grep -Eo 'https://[^ ]+/pull/[0-9]+' | tail -1)"
    PR_NUM="${PR_URL##*/}"
    case "$PR_NUM" in
      ''|*[!0-9]*) PR_NUM=""; PR_URL=""; log "gh pr create が失敗: $(tail -c 300 "$RUN_DIR/gh.log" 2>/dev/null | tr '\n' ' ')" ;;
    esac
  else
    log "gh が無い。枝だけ push した。"
  fi

  # 7. 台帳には「提案（未公開）」として残す。変更台帳・変更日台帳には書かない＝マージ後に register_structure_merges.py が記帳する
  if [ -n "$PR_NUM" ]; then
    python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" --proposal \
      --commit "$SHA" --branch "$BRANCH" --pr "$PR_NUM" --pr-url "$PR_URL" >"$RUN_DIR/record.log" 2>&1 || log "提案の記帳に失敗（PR は出ている）"
  else
    python3 scripts/seo/record_changes.py --manifest "$RUN_DIR/changes.json" --brief "$RUN_DIR/brief.json" --proposal \
      --commit "$SHA" --branch "$BRANCH" >"$RUN_DIR/record.log" 2>&1 || log "提案の記帳に失敗（枝は push 済み）"
  fi

  # 8. 通知（1通3行以内）
  if [ -n "$PR_NUM" ]; then
    notify "🧭 scix.co.jp 構成の見直し案（ナビを含むので自動公開せず）を PR #$PR_NUM に置きました。①マージして公開 ②閉じて不採用 $PR_URL" ask "web-structure-pr:${MONTH}"
  else
    notify "🧭 scix.co.jp 構成の見直し案（ナビを含む）を枝 $BRANCH に置きました（PR は作れなかった）。①PR を作ってマージ ②見送る https://github.com/nakashimashinya-a11y/scix-web/compare/main...$BRANCH" ask "web-structure-pr:${MONTH}"
  fi
  log "OK 構成レビュー 完了（PR の経路）$BRANCH ${PR_NUM:+PR #$PR_NUM }$SHA"
  cleanup
  exit 0
}

if [ "$MODE" = "structure" ]; then run_structure; exit 0; fi

mkdir "$LOCK" 2>/dev/null || { log "前回の実行が残っている（${LOCK}）。止める。"; exit 1; }
mkdir -p "$RUN_DIR"
cd "$REPO" || fail "リポジトリが無い: $REPO"
CC_DIR="$(python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.openclaw/openclaw.json")))["agents"]["defaults"]["cliBackends"]["claude-cli"]["env"]["CLAUDE_CONFIG_DIR"]))' 2>/dev/null || true)"
[ -n "$CC_DIR" ] && [ -d "$CC_DIR" ] || fail "CLAUDE_CONFIG_DIR が決まらない（openclaw.json）"
[ "$(cd "$CC_DIR" && pwd -P)" != "$(cd "$HOME/.claude" && pwd -P)" ] || fail "CLAUDE_CONFIG_DIR が中島さんの枠（~/.claude）を指している（共通ルール O14-10）"

# 1. 台帳を最新にしてブリーフ（NO_COLLECT=1 は試験用＝API を叩かず、いまの台帳のまま）
[ "${NO_COLLECT:-0}" = "1" ] || python3 scripts/seo/collect_daily.py --days 10 --no-health >>"$RUN_DIR/collect.log" 2>&1 || log "収集に一部失敗（続行）"
python3 scripts/seo/build_brief.py >>"$RUN_DIR/collect.log" 2>&1 || fail "ブリーフ生成"
[ -s "$RUN_DIR/brief.md" ] || fail "ブリーフが空"

# 2. 作業ツリー（origin/main の最新。人の未コミット作業と混ぜない）
git fetch -q origin || fail "git fetch"
git worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"; git worktree prune >/dev/null 2>&1
git worktree add -q --detach "$WT" "$BASE_REF" || fail "worktree を作れない（${BASE_REF}）"
BASE_SHA="$(git -C "$WT" rev-parse HEAD)"
[ -f "$WT/scripts/seo/guard_diff.py" ] || fail "$BASE_REF に scripts/seo が無い"

# 3. Claude が判断して編集する（起動の条件は上の run_claude）
PROMPT="今週（${TODAY}）の自動更新を実行してください。ブリーフ: $RUN_DIR/brief.md 。マニフェストの出力先: $RUN_DIR/changes.json 。作業ディレクトリ（リポジトリ）: $WT 。"
run_claude "$PROMPT" "$WT/scripts/seo/weekly_prompt.md"

# 4. マニフェストと変更の有無
[ -s "$RUN_DIR/changes.json" ] || fail "マニフェスト changes.json が無い"
cd "$WT" || fail "作業ツリーへ移動できない"
git reset -q 2>/dev/null   # Claude が git add していても、こちらで add し直す
if ! git status --porcelain --untracked-files=all | grep -q . ; then
  REASON="$(mj 'print(j.get("no_change_reason") or "理由の記載なし")' 2>/dev/null)"
  log "今週は変更なし: $REASON / $(idea_line)"
  applog "scix.co.jp 週次 ${TODAY}: 変更なし（${REASON}）"
  cleanup; exit 0
fi

# 5. 焼き直し → 検査
python3 scripts/gen_knowledge_jsonld.py --write >>"$RUN_DIR/collect.log" 2>&1 || fail "gen_knowledge_jsonld"
SCIX_WEB_REPO="$WT" python3 scripts/seo/guard_diff.py --manifest "$RUN_DIR/changes.json" > "$RUN_DIR/guard.log" 2>&1 \
  || fail "検査で止めた: $(grep -- '^ -' "$RUN_DIR/guard.log" | head -5 | tr '\n' ' ')"
# lastmod を進めるのはマニフェストに書かれたファイルだけ（NEW バッジ落ちなどの焼き直しで hub の日付を動かさない。新規ファイルは検査が止める）
HTML_CHANGED="$(mj 'print("\n".join(f for c in j.get("changes",[]) for f in c.get("files",[])))' | grep -E '\.html$' | sort -u || true)"

if [ "$DRY_RUN" = "1" ]; then
  stamp_and_log auto   # 記帳のコミットに入るはずの差分（sitemap の lastmod・変更日台帳）も作業ツリーに残す
  log "DRY_RUN: 公開しない。作業ツリー $WT を残す。"
  git status --short
  rmdir "$LOCK" 2>/dev/null; exit 0
fi

# 6. ①中身のコミット（Claude の編集と焼き直し。commit email は GitHub と一致させないと Vercel が Blocked にする）
TITLE="$(mj 'print((j.get("summary_lines") or ["自動更新"])[0][:70])')"
BODY="$(mj 'print("\n".join("- "+l for l in j.get("summary_lines",[]))); print(); print("\n".join("- "+", ".join(c.get("files",[]))+": "+str(c.get("summary","")) for c in j.get("changes",[])))')"
git add -A -- . ':!.claude' || fail "git add"
git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" commit -q -F - <<EOF2 || fail "commit"
auto(seo): $TITLE

$BODY

scripts/seo/weekly_run.sh による週次自動更新。ブリーフとマニフェスト: 9_システム/scix-web解析/weekly/$TODAY
差し戻し: git revert <このコミット>（sitemap の lastmod と変更日台帳は次の chore(seo-log) に分けてある＝衝突しない）
EOF2
# 7. ②記帳のコミット（sitemap の lastmod・公開リポジトリの変更日台帳）→ 最新の origin/main へ載せ直し → push（Vercel が数分で公開）
#    → タグ → 手元の main を早送り（衝突したら公開しない）→ 変更台帳（Drive）に記帳
commit_log auto "auto(seo)"
publish_main "auto/weekly-$TODAY"
LEDGER_NOTE=""
record_ledger auto || LEDGER_NOTE="
⚠️ 台帳の記帳に失敗＝まだ効果測定の対象になっていない（明朝の収集 register_auto_commits.py が拾い直す）"

# 8. 本番反映を待って IndexNow（Action も送るが、ここでも送って二重化。Bing は重複を受け付ける）
#   反映の判定は「変えたページの本番の中身が、今 push した版と同じか」（GitHub Action と同じ方式）。
#   2026-09-20 まで sitemap の今日の lastmod を `curl | grep -q` で見ていたが、pipefail の下では grep -q が先に
#   閉じて curl が rc≠0 になり、反映済みでも毎回10分空振りしていた。しかも今日の lastmod は毎朝の案件一覧の
#   同期でも立つので、判定としても当てにならなかった。
DEPLOYED=0
FIRST_HTML="$(printf '%s\n' "$HTML_CHANGED" | sed -n '1p')"
if [ -n "$FIRST_HTML" ]; then
  CHECK_URL="$(python3 -c 'import sys; sys.path.insert(0, "scripts/seo"); from common import file_to_url; print(file_to_url(sys.argv[1]) or "")' "$FIRST_HTML" 2>/dev/null || true)"
  WANT_SUM="$(git show "HEAD:$FIRST_HTML" 2>/dev/null | cksum | awk '{print $1":"$2}')"
  if [ -n "$CHECK_URL" ] && [ -n "$WANT_SUM" ]; then
    for i in $(seq 1 30); do
      sleep 20
      GOT_SUM="$( (curl -fsS -H 'Cache-Control: no-cache' "$CHECK_URL" 2>/dev/null || true) | cksum | awk '{print $1":"$2}')"
      if [ "$GOT_SUM" = "$WANT_SUM" ]; then DEPLOYED=1; break; fi
    done
  fi
fi
[ "$DEPLOYED" = "1" ] && log "本番に反映を確認（${FIRST_HTML}）" || log "本番反映を10分待ったが確認できない（${FIRST_HTML:-変えた HTML なし}。Action 側の送信に任せる）"
python3 scripts/ping_indexnow.py --changed-since "$BASE_SHA" >>"$RUN_DIR/collect.log" 2>&1 || log "IndexNow 送信失敗"

# 9. 通知（3行＋コミット）
LINES="$(mj 'print("\n".join("・"+l for l in j.get("summary_lines",[])[:3]))')"
STALE="$(drop_line)"
notify "🌐 scix.co.jp 週次自動更新 ${TODAY}（公開済み）
$LINES
$(idea_line)${STALE:+
$STALE}
https://github.com/nakashimashinya-a11y/scix-web/commit/${SHA:0:10}
差し戻すなら: git revert ${SHA:0:10} → push。ブリーフ: 9_システム/scix-web解析/weekly/$TODAY/$LEDGER_NOTE" undo "web-weekly:${TODAY}"
log "OK 週次自動更新 完了${LEDGER_NOTE:+（⚠️ 台帳の記帳は失敗＝明朝の収集が拾い直す）} $SHA"
cleanup
exit 0
