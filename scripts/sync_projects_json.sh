#!/bin/bash
# sync_projects_json.sh — 公開案件一覧を毎朝ライブDR2に合わせる（launchd ai.scix.projects-json から実行）
#
# 2026-09-05 新設。中島さん判断①「公開項目の拡張と再生成の定期化＝そうする」に基づく。
# それまでは手で回す運用で、実際には46日間止まり、売却済みの案件が載り続けていた。
#
# やること: D1から再生成 → 変化が無ければ無音で終わる → 変化があれば main へ commit/push（Vercelが公開）
#   「変化」は案件の出入りだけでなく、既存案件の公開項目（連系の見込み・月数・進み具合・規模など）の変更も含む
#   （2026-09-20 まで ID の集合しか比べておらず、DR2 で連系時期を直しても次に案件が出入りする日まで出なかった）。
#   変化が無い日も静的一覧だけは焼き直す（月が替わると「◯年◯月ごろ」の出し分けが変わるため）。
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

# 手元の main を本番（origin/main）に合わせてから始める。週次自動更新や PR のマージで origin が先へ進んでいると、
# 手元で commit しても push が non-fast-forward で弾かれる。未 push の commit が手元に残っている場合は載せ直す。
# どうしても合わせられないときは黙って進めない: 比較相手が古い手元の projects.json になり、
# 「OK 変化なし」と記録しながら本番が古いまま、という静かな陳腐化になる。
if [ "$DRY_RUN" != "1" ] && [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ]; then
  if git fetch -q origin 2>/dev/null; then
    if [ "$(git rev-list --count main..origin/main)" != "0" ] || [ "$(git rev-list --count origin/main..main)" != "0" ]; then
      git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" pull -q --rebase --autostash origin main \
        || { git rebase --abort >/dev/null 2>&1; fail "手元の main を origin/main に合わせられない（分岐している）。git status を見て手で直す。"; }
      # autostash の復元が衝突しても pull は 0 を返す。未マージのファイルが残っていたら進めない
      [ -z "$(git ls-files -u)" ] || fail "手元の未コミット変更を戻すときに衝突した（変更は git stash に残っている）。git status を見て手で直す。"
      log "手元の main を origin/main に合わせた"
      # 前回 push できずに手元へ残った同期 commit があれば、ここで出す（出せなければ止まる＝黙って本番が古いままにしない）
      if [ "$(git rev-list --count origin/main..main)" != "0" ]; then
        git push -q origin main || fail "手元に残っていた未 push の commit を出せない"
        log "手元に残っていた未 push の commit を出した"
      fi
      # pull でこのスクリプト自身が新しくなったら、古い判定のまま進めずに読み直す（1回だけ）
      if [ -z "${SCIX_SYNC_REEXEC:-}" ] && ! git diff --quiet "ORIG_HEAD" HEAD -- scripts/sync_projects_json.sh 2>/dev/null; then
        log "同期スクリプトが更新された。読み直す。"
        rm -f "$TMP"; SCIX_SYNC_REEXEC=1 exec bash "$REPO/scripts/sync_projects_json.sh"
      fi
    fi
  else
    log "git fetch に失敗（続行。push で弾かれたら下で止まる）"
  fi
fi

# 生成。D1が引けなければ build 側が非ゼロで止まる（部分的な一覧を書かない）。
# トークン更新の直後に1回だけ失敗することがある（2026-09-05 実測）ので、間を置いて3回まで試す。
GEN_OK=0
for attempt in 1 2 3; do
  if SCIX_WRANGLER="$WR" python3 scripts/build_projects_json.py --out "$TMP" --prev "$REPO/projects.json"; then
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
def load(p):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("schema", 1), {x.get("id"): x for x in d.get("projects", [])}
(cs, cur), (ns, new) = load(cur_path), load(new_path)
added, removed = sorted(set(new) - set(cur)), sorted(set(cur) - set(new))
# 既存案件の公開項目の変更。掲載日・更新日そのものの違いは数えない（中身が変われば生成側が更新日を動かす）
SKIP = {"firstSeen", "updatedAt"}
changed = []
for i in sorted(set(cur) & set(new)):
    keys = sorted(k for k in (set(cur[i]) | set(new[i])) - SKIP if cur[i].get(k) != new[i].get(k))
    if keys:
        changed.append(f"{i}({'/'.join(keys)})")
if not added and not removed and not changed and cs == ns:
    print("SAME")
elif cur and (len(cur) - len(new)) / len(cur) > max_shrink:
    print(f"SHRINK\t{len(cur)}\t{len(new)}\t{','.join(removed)}")
else:
    delta = f"+{len(added)}/-{len(removed)}" + (f"・項目変更{len(changed)}件" if changed else "")
    # 移行の回は全件が変わる。commit 文が長くなりすぎないよう 30 件で切る
    ch = ",".join(changed[:30]) + (f" ほか{len(changed)-30}件" if len(changed) > 30 else "")
    print(f"DIFF\t{len(cur)}\t{len(new)}\t{delta}\t{','.join(added)}\t{','.join(removed)}\t{ch}")
PY
)" || { rm -f "$TMP"; fail "差分判定に失敗した"; }

KIND="$(printf '%s' "$VERDICT" | cut -f1)"

case "$KIND" in
  SAME)
    rm -f "$TMP"
    # 中身は同じでも、月が替わると静的一覧の「◯年◯月ごろ」と件数の出し分けが変わる。ずれていたら焼き直して出す。
    if [ "$DRY_RUN" != "1" ] && [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] \
       && git diff --quiet -- index.html projects.html sitemap.xml && git diff --cached --quiet \
       && ! python3 scripts/inject_stats.py --check >/dev/null 2>&1; then
      python3 scripts/inject_stats.py >/dev/null || fail "静的一覧の焼き直しに失敗"
      git add index.html projects.html || fail "git add に失敗"
      git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" \
          commit -q -m "chore(projects): 静的一覧を焼き直し（案件の中身は変化なし・日付の出し分けだけ）" || fail "commit に失敗"
      git push -q origin main || fail "push に失敗（commit は手元に残っている。次回の冒頭で出し直す）"
      log "OK 変化なし。静的一覧だけ焼き直して公開した"; exit 0
    fi
    log "OK 変化なし（公開一覧は最新）"; exit 0 ;;
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
CHANGED="$(printf '%s' "$VERDICT" | cut -f7)"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN ${OLD}→${NEW}（${DELTA}） 追加=${ADDED:-なし} 削除=${REMOVED:-なし} 項目変更=${CHANGED:-なし}"
  rm -f "$TMP"; exit 0
fi

# 作業ツリーを汚さない。下で git add する3ファイルのどれかに未コミットの変更があれば、人の作業中とみなして見送る。
# （projects.json だけを見ていた頃は、書きかけの index.html / projects.html が同期の commit に混ざって本番に出る穴があった）
if ! git diff --quiet -- projects.json index.html projects.html sitemap.xml || ! git diff --cached --quiet; then
  rm -f "$TMP"; fail "projects.json / index.html / projects.html / sitemap.xml に未コミットの変更がある。人の作業中とみなして見送る。"
fi
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] || { rm -f "$TMP"; fail "main 以外（$BRANCH）なので見送る。"; }

# ここから先は作業ツリーに生成物を書く。途中で落ちたら必ず元に戻す（残骸が残ると、翌朝はそれと比べて
# 「変化なし」と記録しながら本番は古いまま、になる）。commit まで行けば解除する。
rollback_generated() {
  git reset -q HEAD -- projects.json index.html projects.html sitemap.xml >/dev/null 2>&1
  git checkout -q -- projects.json index.html projects.html sitemap.xml >/dev/null 2>&1
}
trap rollback_generated EXIT
cp "$TMP" projects.json && rm -f "$TMP"
# トップに焼き込んである件数・MW・都道府県数も一緒に更新する（JSでは描かない）
python3 scripts/inject_stats.py || fail "件数の焼き込みに失敗"
# 毎朝更新していることを検索エンジンに伝える（Google は sitemap の lastmod を見る。Bing 等は push 時の Action が IndexNow）。
# 実際に変わった HTML だけ。失敗しても同期は止めない。
STAMP=""
git diff --quiet -- projects.html || STAMP="$STAMP projects.html"
git diff --quiet -- index.html || STAMP="$STAMP index.html"
# shellcheck disable=SC2086
[ -n "$STAMP" ] && { python3 scripts/seo/stamp_sitemap.py $STAMP >/dev/null 2>&1 || log "sitemap の lastmod 更新に失敗（続行）"; }
git add projects.json index.html projects.html sitemap.xml || fail "git add に失敗"
git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" \
    commit -q -m "chore(projects): 公開案件一覧をDR2に同期（${OLD}→${NEW}件・${DELTA}）

追加: ${ADDED:-なし}
削除: ${REMOVED:-なし}
項目変更: ${CHANGED:-なし}

scripts/sync_projects_json.sh による自動同期。" || fail "commit に失敗"
trap - EXIT   # commit できた。ここから先で落ちても commit は手元に残り、次回の冒頭で出し直す

if ! git push -q origin main 2>/dev/null; then
  # 生成している数十秒の間に origin が進んだ。1回だけ載せ直して出し直す。
  log "push が弾かれた。origin/main に載せ直して出し直す。"
  git -c user.name="Shinya Nakashima" -c user.email="nakashima.shinya@me.com" pull -q --rebase --autostash origin main \
    || { git rebase --abort >/dev/null 2>&1; fail "push に失敗し、載せ直しもできなかった（commit は手元に残っている。次回の冒頭で出し直す）"; }
  [ -z "$(git ls-files -u)" ] || fail "載せ直しのあと、手元の未コミット変更を戻すときに衝突した（変更は git stash に残っている）"
  git push -q origin main || fail "push に失敗（commit は手元に残っている。次回の冒頭で出し直す）"
fi
log "OK ${OLD}→${NEW}件（${DELTA}）を公開した。追加=${ADDED:-なし} 削除=${REMOVED:-なし} 項目変更=${CHANGED:-なし}"
