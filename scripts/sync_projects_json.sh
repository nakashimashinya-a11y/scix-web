#!/bin/bash
# sync_projects_json.sh — 公開案件一覧を毎朝ライブDR2に合わせる（launchd ai.scix.projects-json から実行）
#
# 2026-09-05 新設。中島さん判断①「公開項目の拡張と再生成の定期化＝そうする」に基づく。
# それまでは手で回す運用で、実際には46日間止まり、売却済みの案件が載り続けていた。
#
# やること: D1から再生成 → 変化が無ければ無音で終わる → 変化があれば main へ commit/push（Vercelが公開）
# やらないこと: 壊れた一覧の公開。D1が引けない・差分が異常に大きいときは触らずに止める。
#
# 手で回すとき:  bash scripts/sync_projects_json.sh
# 変更せず確認:  DRY_RUN=1 bash scripts/sync_projects_json.sh

set -uo pipefail

REPO="${SCIX_WEB_REPO:-$HOME/projects/scix-web}"
WR="$HOME/.config/scix-cockpit/wr"
TMP="$(mktemp -t projects_new)".json
DRY_RUN="${DRY_RUN:-0}"
# 一覧がこの割合より大きく減ったら、事故を疑って公開しない（D1の部分読みなど）
MAX_SHRINK_RATIO="${MAX_SHRINK_RATIO:-0.30}"

log() { echo "$(date '+%F %T') $*"; }
fail() { log "NG $*"; exit 1; }

cd "$REPO" || fail "リポジトリが無い: $REPO"
[ -x "$WR" ] || fail "wrangler ラッパーが無い: $WR"

# 生成。D1が引けなければ build 側が非ゼロで止まる（部分的な一覧を書かない）。
# トークン更新の直後に1回だけ失敗することがある（2026-09-05 実測）ので、間を置いて3回まで試す。
GEN_OK=0
for attempt in 1 2 3; do
  if SCIX_WRANGLER="$WR" python3 scripts/build_projects_json.py --out "$TMP"; then
    GEN_OK=1; break
  fi
  log "再生成の試行 $attempt が失敗。20秒待って再試行する。"
  sleep 20
done
[ "$GEN_OK" = "1" ] || {
  rm -f "$TMP"; fail "再生成に3回とも失敗した（D1を読めていない）。projects.json は触っていない。"
}

# 差分判定と安全弁
VERDICT="$(python3 - "$REPO/projects.json" "$TMP" "$MAX_SHRINK_RATIO" <<'PY'
import json, sys
cur_path, new_path, max_shrink = sys.argv[1], sys.argv[2], float(sys.argv[3])
def ids(p):
    with open(p, encoding="utf-8") as f:
        return {x.get("id") for x in json.load(f).get("projects", [])}
cur, new = ids(cur_path), ids(new_path)
added, removed = sorted(new - cur), sorted(cur - new)
if not added and not removed:
    print("SAME")
elif cur and (len(cur) - len(new)) / len(cur) > max_shrink:
    print(f"SHRINK\t{len(cur)}\t{len(new)}\t{','.join(removed)}")
else:
    print(f"DIFF\t{len(cur)}\t{len(new)}\t+{len(added)}/-{len(removed)}\t"
          f"{','.join(added)}\t{','.join(removed)}")
PY
)" || { rm -f "$TMP"; fail "差分判定に失敗した"; }

KIND="$(printf '%s' "$VERDICT" | cut -f1)"

case "$KIND" in
  SAME)
    rm -f "$TMP"; log "OK 変化なし（公開一覧は最新）"; exit 0 ;;
  SHRINK)
    OLD="$(printf '%s' "$VERDICT" | cut -f2)"; NEW="$(printf '%s' "$VERDICT" | cut -f3)"
    cp "$TMP" /tmp/projects_json_shrink.json; rm -f "$TMP"
    fail "件数が急に減った（${OLD}→${NEW}）ので公開しない。/tmp/projects_json_shrink.json を見て、
      正しければ MAX_SHRINK_RATIO=1 で手動実行する。" ;;
  DIFF) : ;;
  *) rm -f "$TMP"; fail "差分判定の出力が想定外: $VERDICT" ;;
esac

OLD="$(printf '%s' "$VERDICT" | cut -f2)"
NEW="$(printf '%s' "$VERDICT" | cut -f3)"
DELTA="$(printf '%s' "$VERDICT" | cut -f4)"
ADDED="$(printf '%s' "$VERDICT" | cut -f5)"
REMOVED="$(printf '%s' "$VERDICT" | cut -f6)"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN ${OLD}→${NEW}（${DELTA}） 追加=${ADDED:-なし} 削除=${REMOVED:-なし}"
  rm -f "$TMP"; exit 0
fi

# 作業ツリーを汚さない。projects.json 以外に手を付けている最中なら見送る。
if ! git diff --quiet -- projects.json; then
  rm -f "$TMP"; fail "projects.json に未コミットの変更がある。人の作業中とみなして見送る。"
fi
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] || { rm -f "$TMP"; fail "main 以外（$BRANCH）なので見送る。"; }

cp "$TMP" projects.json && rm -f "$TMP"
# トップに焼き込んである件数・MW・都道府県数も一緒に更新する（JSでは描かない）
python3 scripts/inject_stats.py || fail "件数の焼き込みに失敗"
git add projects.json index.html projects.html || fail "git add に失敗"
git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" \
    commit -q -m "chore(projects): 公開案件一覧をDR2に同期（${OLD}→${NEW}件・${DELTA}）

追加: ${ADDED:-なし}
削除: ${REMOVED:-なし}

scripts/sync_projects_json.sh による自動同期。" || fail "commit に失敗"

git push -q origin main || fail "push に失敗（commit は残っている）"
log "OK ${OLD}→${NEW}件（${DELTA}）を公開した。追加=${ADDED:-なし} 削除=${REMOVED:-なし}"
