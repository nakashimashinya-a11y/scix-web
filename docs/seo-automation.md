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
| 毎日 07:10 | GSC（検索語×ページ・端末・国）・GA4（着地・回遊・内部遷移・イベント）・本番 HTML の健診を台帳に蓄積。**手動 PR で足した新規ページを変更台帳へ自動で記帳**（`register_new_pages.py`）。期限が来た変更の効果測定。**サイトの変更はしない** | launchd `ai.scix.web-metrics` → `scripts/seo/collect_daily.py` | 台帳 Drive `9_システム/scix-web解析/` |
| 日曜 06:00 | 台帳からブリーフ → Claude（Opus）が判断・編集 → 機械の検査 → 通ったものだけ commit/push（Vercel が公開）→ IndexNow → Telegram 3 行＋「✍️ 今週書くなら」（コラム主題の提案。マニフェスト `column_ideas`） | launchd `ai.scix.web-weekly` → `scripts/seo/weekly_run.sh` | 作業ツリー `~/projects/.scix-web-weekly` |
| 変更の 2 週後・4 週後 | 前後 14 日の GSC（クリック・CTR・順位）と GA4（着地→リード）を比べ、better / flat / worse を台帳に書く。worse は翌週の候補「差し戻し」。**新規ページは前後比較をせず立ち上がりで判定**（下の節） | `collect_daily.py` の中で `measure_changes.py` | `scix-web解析/ledger/` |
| main への push の都度 | 変わった HTML を IndexNow へ（Bing・Yandex 等）。Google は sitemap の lastmod と GSC の手動リクエスト | GitHub Action `.github/workflows/indexnow-on-push.yml` | |

両ジョブは実行前に `git pull --ff-only origin main` を打つ（launchd の plist 側）。GitHub で PR をマージすればローカルの main も追いつき、手で pull しなくてよい。ローカルに未 push のコミットがあれば pull は黙って見送られ、そのまま動く。

ナビや構成そのものの再検討は月 1 回、ナビの組み替えは四半期に 1 回まで（週次では触らない＝`header.js` は `JA_ONLY_COLUMNS` 以外を検査で弾く）。

## 新規ページ（毎週足すコラム）の流れ — 毎日の記録 → 週次の方針 → 効果測定

2026-09-20 追加。それまでは、人が PR で足したコラムが変更台帳に載らず（直近 28 日の新規 HTML 85 本のうち台帳にあったのは 1 本）、ブリーフにも新規ページの節が無く、効果測定は前の窓が 0 なので 1 クリックで必ず better になっていた。

| いつ | 何が | どこに |
|---|---|---|
| 毎日 07:10（収集のあと・効果測定の前）。週次の冒頭でも同じものが走る | `scripts/seo/register_new_pages.py` が **origin/main の git 履歴** から直近 28 日に足された `*.html` を拾って記帳。3 言語版（`column-x.html`・`en/column-x.html`・`zh-column-x.html`）は 1 エントリ。id は `new-<slug>` 固定＝何度走っても重複しない。台帳のどれかのエントリの `pages` に既に居るページは足さない（手で記帳した PR・週次の自動 new-column と二重にしない）。JA 先行で EN/ZH を後から足したときは `new-<slug>-en-zh` に残りだけ。`404`・`thanks`・noindex は除く | `ledger/changes.jsonl`（`source: "manual-auto"`・`class: "new-column"`／コラム以外は `"new-page"`・`check_days: [14, 28]`） |
| 公開の 14 日後・28 日後（GSC がその日まで届いたら） | `measure_changes.py` が class `new-column`／`new-page` を **立ち上がり**（`mode: "ramp"`）で判定。14 日: 公開日〜+14 日に表示が 1 以上あれば `shown`、無ければ `not-shown`。28 日: 公開翌日〜+28 日の表示を、**同じ言語の既存コラム**（健診のページ一覧＝sitemap。公開 60 日以内の新規は母集団から外す。表示ゼロのコラムも入れる）の同じ 28 日の表示の中央値と比べて `above-median`／`below-median`、表示ゼロは `not-shown`。ページごとの判定は `by_page`、エントリの判定は主たるページ（JA→EN→ZH の順で最初）。判定済みのレコードは触らない | `ledger/changes.jsonl` の `measured`・`ledger/measurements.jsonl` |
| 日曜 06:00（ブリーフ） | `build_brief.py` の **10 節「新規ページ（公開 60 日以内）の立ち上がり」**: ページ／公開日（Article JSON-LD の `datePublished`、無ければ git の初回コミット日）／経過日数／初表示日／28 日の表示・クリック／GA4 着地／サイト内被リンク数（自分自身は除く）／旗。旗は「公開14日超で表示ゼロ」「被リンク1以下」「sitemap 未登録」「JA専用の登録漏れ」。旗つきを先に最大 40 行。**10b**「sitemap にあるのに 90 日表示ゼロ（公開 14 日以上）」最大 20 行。8 節には `not-shown` のまま直近 28 日も表示ゼロのページが **要手当て** として出る（worse と同じ位置。ただし差し戻しではなく育成）。自動記帳のエントリは 8 節の表には並べず件数だけ | `weekly/<日付>/brief.md`・`brief.json` の `new_pages`・`zero_impression`。`最新.md` にも 10 節を短く |
| 日曜 06:00（Claude） | `weekly_prompt.md`「今週やること」7『新規ページの育成』: 旗・要手当てのページへ、関連コラム・ハブから内部リンクを足す（**リンクを置く側が 9 節「今週触らないページ」なら置かない**）。その週に人が足したコラムのハブカード・新着・sitemap・`JA_ONLY_COLUMNS` の登録漏れを点検。1 週の変更件数の上限は変えない | 公開は従来どおりシェルと `guard_diff.py` |

どれも台帳と git だけで決定論に作る（追加 API なし）。ページ一覧と公開日は作業ツリーではなく `origin/main` から読む（別ブランチに居ても、未コミットの原稿があっても結果が変わらない。`origin/main` が無いときは記帳しない）。試すときは `SCIX_WEB_LEDGER=<複製>` で台帳の向き先を変える（`common.py`）。

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
python3 scripts/seo/register_new_pages.py --dry         # 新規ページの自動記帳を書かずに一覧（--days 60 で窓を広げる）
python3 scripts/seo/selftest_ramp.py                    # 立ち上がり判定の合成テスト（一時ディレクトリ・本物の台帳に触らない）
SCIX_WEB_LEDGER=/private/tmp/ledger-copy python3 scripts/seo/collect_daily.py --no-gsc --no-ga4 --no-health   # 複製した台帳で記帳→計測→最新.md だけ試す
git revert <auto(seo) のコミット> && git push           # 差し戻し（IndexNow は Action が送る）
launchctl bootout gui/$(id -u)/ai.scix.web-weekly       # 週次を止める
```

GA4 のトークンが無いときは GA4 だけ飛ばして動く。取得は `python3 scripts/seo/ga4_auth.py`（ブラウザで 1 回許可）。

## 数字の置き場

公開リポジトリ（この docs と change-log）には GSC の数字だけ。GA4 のリード数・用件別は Drive の台帳側（`scix-web解析/`）。Web 版 Claude・スマホは `scix-web解析/最新.md`（毎朝の写し・読み取り専用）。
