# 週次自動更新（docs/seo-automation.md）

2026-09-19 新設。中島「検索エンジンのアクセス履歴やサイトの滞在や移動内容も全部データをとって、より引き合いや問い合わせが増えるように、自動的にアップデートしてほしい」「自動公開は承認しなくて公開していい」。

## なぜ週1か（毎日・3日に1回にしなかった理由）

- Search Console のデータは 2〜3 日遅れ、GA4 は 1〜2 日遅れで届く
- 問い合わせ（generate_lead）は週 6 件前後。1 日単位の増減は揺れでしかない
- Google が title の変更を反映するのに 1〜2 週間。同じページを週の途中でまた変えると、どの変更が効いたか永久に分からない
- 台帳 `docs/seo-change-log.md` はもともと「確認日＝2 週後・4 週後」で運用していた

## 4 層

| 周期 | 何が | 誰が | 場所 |
|---|---|---|---|
| 毎日 07:10 | GSC（検索語×ページ・端末・国）・GA4（着地・回遊・内部遷移・イベント）・本番 HTML の健診を台帳に蓄積。期限が来た変更の効果測定。**変更はしない** | launchd `ai.scix.web-metrics` → `scripts/seo/collect_daily.py` | 台帳 Drive `9_システム/scix-web解析/` |
| 月曜 07:30 | 台帳からブリーフ → Claude（Opus）が判断・編集 → 機械の検査 → 通ったものだけ commit/push（Vercel が公開）→ IndexNow → Telegram 3 行 | launchd `ai.scix.web-weekly` → `scripts/seo/weekly_run.sh` | 作業ツリー `~/projects/.scix-web-weekly` |
| 変更の 2 週後・4 週後 | 前後 14 日の GSC（クリック・CTR・順位）と GA4（着地→リード）を比べ、better / flat / worse を台帳に書く。worse は翌週の候補「差し戻し」 | `collect_daily.py` の中で `measure_changes.py` | `scix-web解析/ledger/` |
| main への push の都度 | 変わった HTML を IndexNow へ（Bing・Yandex 等）。Google は sitemap の lastmod と GSC の手動リクエスト | GitHub Action `.github/workflows/indexnow-on-push.yml` | |

ナビや構成そのものの再検討は月 1 回、ナビの組み替えは四半期に 1 回まで（週次では触らない＝`header.js` は `JA_ONLY_COLUMNS` 以外を検査で弾く）。

## 週次の Claude に渡すもの・渡さないもの

- 渡す: ブリーフ（`scix-web解析/weekly/<日付>/brief.md`）・規約の正本（scix-web の記憶 6 本）・リポジトリの CLAUDE.md・読む／編集する／リポジトリ内の python3 を叩く道具
- 渡さない: git commit / push / branch、gh、Web 取得、サブエージェント。**公開はシェルだけが行い、その前に `guard_diff.py` が検査する**
- 動かすアカウント: OpenClaw 用（`~/.openclaw/openclaw.json` の `CLAUDE_CONFIG_DIR`）。中島さん自身の枠には落とさない。モデルは Opus（Fable は同じ仕事に枠 5 倍・2026-09-17 実測）

## 検査（guard_diff.py）で止まるもの

触ってよいのは HTML・sitemap・`header.js` の `JA_ONLY_COLUMNS` 行だけ（`docs/seo-change-log.md` はマニフェストからシェルが記帳する）。フォーム（contact / sell-form / thanks / privacy）・`/fund`・`vercel.json`・`projects.json`・`robots.txt`・`scripts/`・`.github/`・`img/`・`files/`・削除は弾く。
既存ページ 12 本／新規 3 本まで、1 ファイルの差し替えは半分未満・削除は 1/4 未満。title・description・canonical・h1 1 つ・`/header.js`・JSON-LD・内部リンク切れ・EN の title 70 字／description 155 字・新コラムの必須ブロック（監修・Article author=Person・パンくず・CTA・sitemap 登録・JA 専用の登録）・自称「中立」・実績の主張・鍵らしき文字列・マニフェストと差分の不一致。

## 試験結果（2026-09-19 DRY_RUN）

Opus・53 ターン・7 分で 3 件: `/land` の Q&A に「蓄電所そのものを売りたい」節と /sourcing への導線（「系統用蓄電所 物件 売りたい」42 表示・0 クリック・23.7 位が /land 着地）、`/zh-column-financing` の title/description 短縮（152 表示・0 クリック）、`/zh-column-low-voltage` の description 172→128 字。凍結ページ（09-05／09-17 の変更）と票割れになる新コラムは見送った。検査 OK。差分は台帳 `weekly/2026-09-19/dryrun.diff`。

## 手で回す・止める・戻す

```bash
python3 scripts/seo/collect_daily.py --days 30          # 台帳を取り直す
python3 scripts/seo/build_brief.py --stdout             # ブリーフを見る
DRY_RUN=1 bash scripts/seo/weekly_run.sh                # 公開せずに一周（作業ツリーを残す）
bash scripts/seo/weekly_run.sh                          # 本番と同じ一周
python3 scripts/seo/measure_changes.py --list           # 効果測定の台帳
git revert <auto(seo) のコミット> && git push           # 差し戻し（IndexNow は Action が送る）
launchctl bootout gui/$(id -u)/ai.scix.web-weekly       # 週次を止める
```

GA4 のトークンが無いときは GA4 だけ飛ばして動く。取得は `python3 scripts/seo/ga4_auth.py`（ブラウザで 1 回許可）。

## 数字の置き場

公開リポジトリ（この docs と change-log）には GSC の数字だけ。GA4 のリード数・用件別は Drive の台帳側（`scix-web解析/`）。Web 版 Claude・スマホは `scix-web解析/最新.md`（毎朝の写し・読み取り専用）。
