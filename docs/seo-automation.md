# 週次自動更新（docs/seo-automation.md）

2026-09-19 新設。中島「検索エンジンのアクセス履歴やサイトの滞在や移動内容も全部データをとって、より引き合いや問い合わせが増えるように、自動的にアップデートしてほしい」「自動公開は承認しなくて公開していい」。

## なぜ週1か（毎日・3日に1回にしなかった理由）

- Search Console のデータは 2〜3 日遅れ、GA4 は 1〜2 日遅れで届く
- 問い合わせ（generate_lead）は週 6 件前後。1 日単位の増減は揺れでしかない
- Google が title の変更を反映するのに 1〜2 週間。同じページを週の途中でまた変えると、どの変更が効いたか永久に分からない
- 台帳 `docs/seo-change-log.md` はもともと「確認日＝2 週後・4 週後」で運用していた

## 4 層（＋月 1 回の構成レビュー）

| 周期 | 何が | 誰が | 場所 |
|---|---|---|---|
| 毎日 07:10 | GSC（検索語×ページ・端末・国）・GA4（着地・回遊・内部遷移・イベント）・本番 HTML の健診を台帳に蓄積。**手動 PR で足した新規ページを変更台帳へ自動で記帳**（`register_new_pages.py`）。期限が来た変更の効果測定。**サイトの変更はしない** | launchd `ai.scix.web-metrics` → `scripts/seo/collect_daily.py` | 台帳 Drive `9_システム/scix-web解析/` |
| 日曜 06:00 | 台帳からブリーフ → Claude（Opus）が判断・編集 → 機械の検査 → 通ったものだけ commit/push（Vercel が公開）→ IndexNow → Telegram 3 行＋「✍️ 今週書くなら」（コラム主題の提案。マニフェスト `column_ideas`） | launchd `ai.scix.web-weekly` → `scripts/seo/weekly_run.sh` | 作業ツリー `~/projects/.scix-web-weekly` |
| 月の第 1 日曜（週次の直後） | **構成レビュー**: 台帳からブリーフ（通常の節＋構成用の S1〜S8）→ Claude（Opus）が構成の変更を 1〜3 件に絞って編集 → 機械の検査（`--profile structure`）→ **公開しない**＝枝 `auto/structure-YYYY-MM` へ push して PR（マージで公開・閉じれば不採用）→ Telegram 3 行。マージされたら翌朝の収集が変更台帳へ記帳（`register_structure_merges.py`） | 同じ launchd `ai.scix.web-weekly` → `weekly_run.sh` が続けて `MODE=structure` を 1 回（新しい plist なし） | 作業ツリー `~/projects/.scix-web-structure`・台帳 `weekly/<日付>/structure/`・`ledger/proposals.jsonl` |
| 変更の 2 週後・4 週後 | 前後 14 日の GSC（クリック・CTR・順位）と GA4（着地→リード）を比べ、better / flat / worse を台帳に書く。worse は翌週の候補「差し戻し」。**新規ページは前後比較をせず立ち上がりで判定**（下の節） | `collect_daily.py` の中で `measure_changes.py` | `scix-web解析/ledger/` |
| main への push の都度 | 変わった HTML を IndexNow へ（Bing・Yandex 等）。Google は sitemap の lastmod と GSC の手動リクエスト | GitHub Action `.github/workflows/indexnow-on-push.yml` | |

両ジョブは実行前に `git pull --ff-only origin main` を打つ（launchd の plist 側）。GitHub で PR をマージすればローカルの main も追いつき、手で pull しなくてよい。ローカルに未 push のコミットがあれば pull は黙って見送られ、そのまま動く。

ページの **中身** は週次が毎週 3〜8 件変える。**構成**（ハブの並び・トップの節の順・CTA の行き先・収益ページへの導線・ナビ）は月 1 回、下の「月 1 回の構成レビュー」が PR で提案する（自動では公開しない）。ナビの組み替えは 90 日に 1 回まで＝週次では `header.js` の `JA_ONLY_COLUMNS` 以外を検査で弾き、構成レビューではナビ定義の変更を見つけたら変更台帳と `origin/main` の履歴で 90 日ルールを照合する。

## 月 1 回の構成レビュー（第 1 日曜）— 自動公開ではなく PR で提案

2026-09-20 追加。中島「何週間かに一度ページ内容やページ構成を変える」。ページ内容は週次がやっている。構成は週次が触れない（ナビ・ヒーロー・半分超の書き換えを検査が弾く）ので、月 1 回、別の枠で見直す。構成の変更は効き方が大きく戻しにくいので **承認なしでは公開しない**。

| 段 | 何が | どこに |
|---|---|---|
| 起動 | `weekly_run.sh` は通常の週次を子プロセスで今までどおり走らせ、その日が **月の第 1 日曜**（`date +%d` が 01〜07 かつ日曜）なら、続けて自分自身を `MODE=structure` で 1 回だけ起こす。週次の終了コードはそのまま返る＝構成レビューが失敗しても週次の結果は壊れない。同じ月の枝 `auto/structure-YYYY-MM` が origin に既にあれば Claude を起こさずに終わる（1 か月に 1 回だけ）。ロックは週次と共用。`NO_STRUCTURE=1` で抑止、`FORCE_STRUCTURE=1` で日付に関係なく続けて走らせる | launchd は `ai.scix.web-weekly` のまま（plist は増やさない） |
| ブリーフ | `build_brief.py --structure` が通常の 1〜10 節のあとに **S1〜S8** を足す: S1 ナビのクリック（GA4 `nav_click` をグループ別）と **ナビの組み替えを提案してよいか**（90 日ルールの判定）／S2 遷移の太さ（トップ・ハブ・コラム・収益ページ・その他の 5×5 と、トップから・ハブから・各収益ページへ・収益ページ→フォーム）／S3 収益ページへの送客が多いコラム上位と、読まれているのに送客ゼロのコラム（標準の CTA ブロックの有無つき）／S4 28 日セッション 0 のページ／S5 サイト内被リンク 1 以下の孤立ページ／S6 カテゴリ別の本数と流入（JA・EN・ZH のハブの並び順どおり）／S7 トップの節の並びと、その節のリンク先への遷移／S8 これまでの提案。台帳と git（`origin/main` の `knowledge.html`・`index.html`・`header.js`）だけで決定論に作る（`scripts/seo/structure.py`） | `weekly/<日付>/structure/brief.md`・`brief.json` の `structure`。週次の `brief.md` は上書きしない |
| Claude | `scripts/seo/structure_prompt.md`。ブリーフを根拠に構成の変更を **1〜3 件に絞って実際に編集**（0 件も可）。型は `hub-order`（ハブのカテゴリ順・カード順・立場別の入口）／`top-order`（トップのヒーローより下の節の順と見出し）／`cta-route`（コラム末尾の CTA の行き先）／`funnel-block`（収益ページへの導線ブロック）／`nav`（S1 が「提案してよい」と言うときだけ）。各変更に **どの数字が根拠か（`rationale`）・何が増えれば成功か（`kpi`）・いつ測るか（`measure`）** をマニフェストに書く。起動の条件（アカウント・`allowedTools`・モデル Opus・タイムアウト）は週次と同じ関数 `run_claude` | `weekly/<日付>/structure/changes.json` |
| 検査 | `guard_diff.py --profile structure`（下の節） | `guard.log` |
| 提案 | 作業ツリーで commit（`auto(structure): …`）→ `git push origin HEAD:refs/heads/auto/structure-YYYY-MM` → `gh pr create`（本文＝マニフェストの要約・根拠の数字・成功の定義・測る日・「マージで公開、閉じれば不採用」）。**main へは push しない・IndexNow も送らない**。sitemap の lastmod と `docs/seo-change-log.md` は PR に入れない（毎朝の案件一覧の同期と毎週の自動更新が同じ行を書くので、PR が開いている間に衝突する）。`gh` が無い／失敗なら Telegram に枝名と compare の URL。`DRY_RUN=1` は push も PR もせず、作業ツリーと `proposal.diff`・`pr_body.md` を残す | PR・`weekly/<日付>/structure/pr_body.md` |
| 記帳 | 台帳には **提案（PR 番号つき・未公開）** として `ledger/proposals.jsonl` に `status: proposed` で残す。変更台帳（`changes.jsonl`）には書かない＝公開されるまで効果測定も「今週触らないページ」も動かさない | `ledger/proposals.jsonl` |
| Telegram | 1 通 3 行以内:「構成の見直し案を PR #NN に置きました／根拠 1 行／マージで公開」。提案なしの月は 1 行 | |
| マージ後 | 毎朝の収集が `register_structure_merges.py` を呼ぶ（新規ページの自動記帳 `register_new_pages.py` とは別）。`origin/main` の履歴だけを見て、件名が `…(#NN)`（squash マージ）か `Merge pull request #NN` のコミットを探し、見つけたら **変更日＝マージコミットの日付** で変更台帳へ足す（id は提案と同じ＝重複しない・`source: "structure"`・`check_days: [14, 28]`・`class: nav` は `nav_change: true`）。以後は `measure_changes.py` が 14 日後・28 日後に前後比較。PR 番号が無い提案は、提案のコミットと同じ中身のファイルを持つコミットで照合する。60 日マージされなかった提案は `expired`（不採用とみなす。PR を閉じたかどうかは `gh` が要るので見ない） | `ledger/changes.jsonl`・`ledger/proposals.jsonl` |

**未対応（割り切り）**:
- マージ後に sitemap の lastmod は進まない（PR に入れていない）。Bing 等へは push 時の Action が IndexNow を送る。Google へ急ぐなら GSC の URL 検査から手動で。
- 公開リポジトリの変更日台帳 `docs/seo-change-log.md` に行は足さない（Drive の変更台帳だけ）。残したければマージ後に手で。
- PR が開いている間に main が同じ場所を変えると（例: トップの `#find` 節を動かす提案と、その節の中の `<!--S:shv-->` の件数の更新）GitHub 上で衝突する。閉じれば翌月その時点の数字でまた提案される。載せ直しは手動。
- S7（トップの節）の「リンク先への遷移」は節ごとのクリックではなく、行き先ごとの遷移を節へ割り当てた近似（同じ行き先を複数の節が持つと両方に数える）。節ごとに測るにはトップのリンクに計測用のパラメータが要る。
- S1 の `nav_click` は 2026-09-17 の計測開始。グループ別までで、引き出しの中のどの行き先かは取っていない（GA4 のカスタムディメンションが要る）。

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

週次（既定の `--profile weekly`）で触ってよいのは HTML・sitemap・`header.js` の `JA_ONLY_COLUMNS` 行だけ（`docs/seo-change-log.md` はマニフェストからシェルが記帳する）。フォーム（contact / sell-form / thanks / privacy）・`/fund`・`vercel.json`・`projects.json`・`robots.txt`・`scripts/`・`.github/`・`img/`・`files/`・削除は弾く。
既存ページ 12 本／新規 3 本まで、1 ファイルの差し替えは半分未満・削除は 1/4 未満。title・description・canonical・h1 1 つ・`/header.js`・JSON-LD・内部リンク切れ・EN の title 70 字／description 155 字・新コラムの必須ブロック（監修・Article author=Person・パンくず・CTA・sitemap 登録・JA 専用の登録）・自称「中立」・実績の主張・鍵らしき文字列・マニフェストと差分の不一致。トップ（`index.html`・`en/index.html`・`zh.html`）は `<body>` の先頭からヒーローの終わりまでが同一であること。`<!--S:…-->` の内側は毎朝の同期が書く場所＝変えない（ナレッジの件数・最終更新・新着 `kcount`／`kdate`／`knew` は週次のシェル自身が `gen_knowledge_jsonld.py` で焼き直すので対象外。2026-09-20 までは新コラムを足した週に件数が変わり、この検査で週ごと止まる状態だった）。

**`--profile structure`（月 1 回の構成レビュー）で変わるところ**:
- 量: マニフェスト 3 件まで・新規ファイル 0。1 ファイルの差し替えは **並べ替えを除いた正味** で測る（行を多重集合で比べる＝節やカードを動かしただけなら 0）。正味の書き換え 1/4 まで・正味の削除 15% まで・見かけの差し替え（+ と − の合計）120% まで（動かした行は両方に数えられる）。既存ページ 12 本までは同じ
- ハブ・トップはヒーローより下だけ: `<body>` の先頭〜ヒーローの終わり（トップ＝`<section class="hero">` の終わり、ハブ＝最初の `</h1>`）が同一。title・description・canonical も同一（数字だけの違いは無視＝「全 N 記事」の焼き直し）
- `<!--S:…-->` の内側は並び順を問わず同じ中身（節ごと動かすのは可・中身の書き換えは不可）
- `header.js`: `JA_ONLY_COLUMNS` に加えて **ナビ定義**（`GROUP_PAGES` 〜 `var nav = […];`）を変えてよい。ナビ定義が変わっていたら、マニフェストの `class: nav` のエントリの申告（`nav_rule.last_nav_change`。直近 90 日に無ければ `null`）と、変更台帳（`class: nav`／`nav_change`）＋ `origin/main` の `header.js` の履歴（ナビ定義が親コミットと違うコミット）から計算した直近のナビ変更日とを照合する。直近 90 日にナビ変更があれば止める・申告が合わなければ止める・申告が無ければ止める。ナビ定義と `JA_ONLY_COLUMNS` 以外（CSS・計測・更新メール・言語切替）は変えられない
- マニフェストの各変更に `pages`・`measure` が要る。`rationale` には数字が要る。`class` は hub-order / top-order / cta-route / funnel-block / nav。**PR の本文は公開リポジトリに載る** ので、公開される欄（`summary_lines`・`summary`・`rationale`・`hypothesis`・`kpi`・`measure`）に問い合わせの件数らしき書き方があれば止める（件数は `private_note` へ＝Drive の台帳にだけ残る）
- それ以外（触ってはいけないファイル・title・canonical・h1・JSON-LD・リンク切れ・鍵・自称中立・実績の主張など）は週次と同じ

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
python3 scripts/seo/build_brief.py --structure --stdout # 構成レビュー用のブリーフ（S1〜S8 つき）を見る
MODE=structure DRY_RUN=1 bash scripts/seo/weekly_run.sh # 構成レビューを push も PR もせずに一周（作業ツリー ~/projects/.scix-web-structure と proposal.diff を残す）
MODE=structure bash scripts/seo/weekly_run.sh           # 構成レビューを手で 1 回（日付に関係なく。今月の枝が既にあれば何もしない）
NO_STRUCTURE=1 bash scripts/seo/weekly_run.sh           # 第 1 日曜でも構成レビューを続けて走らせない
python3 scripts/seo/register_structure_merges.py --dry  # 提案の状態（proposed / merged / expired）と、記帳されるはずのマージを見る
python3 scripts/seo/selftest_structure.py               # 構成レビューの検査・マージの記帳の合成テスト（複製の中で。本物に触らない）
# weekly_run.sh を本物に触らずに試す向き先: SCIX_WEB_REPO（複製のリポジトリ。origin も複製に）・SCIX_WEB_LEDGER・SCIX_WEB_STATE（ロック）・
#   SCIX_WEB_WT／SCIX_WEB_WT_STRUCTURE（作業ツリー）・NO_COLLECT=1（API を叩かない）。claude・openclaw・gh は PATH の先頭にスタブを置く
SCIX_WEB_LEDGER=/private/tmp/ledger-copy python3 scripts/seo/collect_daily.py --no-gsc --no-ga4 --no-health   # 複製した台帳で記帳→計測→最新.md だけ試す
git revert <auto(seo) のコミット> && git push           # 差し戻し（IndexNow は Action が送る）
launchctl bootout gui/$(id -u)/ai.scix.web-weekly       # 週次を止める
```

GA4 のトークンが無いときは GA4 だけ飛ばして動く。取得は `python3 scripts/seo/ga4_auth.py`（ブラウザで 1 回許可）。

## 数字の置き場

公開リポジトリ（この docs と change-log）には GSC の数字だけ。GA4 のリード数・用件別は Drive の台帳側（`scix-web解析/`）。Web 版 Claude・スマホは `scix-web解析/最新.md`（毎朝の写し・読み取り専用）。
