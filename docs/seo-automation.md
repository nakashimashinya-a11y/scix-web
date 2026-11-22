# 週次自動更新（docs/seo-automation.md）

2026-09-19 新設。検索エンジンのアクセス履歴・サイトの滞在・移動のデータを全部とり、引き合いと問い合わせが増えるように自動で更新する。自動公開は承認なしで行う。

2026-09-20 役割の確定。コラムは代表が書き、自動の側は書かない。自動の側の役割は、ページのアクセスと検索ヒットを見て、ページ構成や流れを変え、ヒットと問い合わせを増やすこと（検索エンジン対策を含む）。

- **コラムは書かない**（週次も構成レビューも）。新しいページ・EN/ZH の新規翻訳も作らない。検査（`guard_diff.py`）が新規ファイルと `class: new-column` を止める。足りない主題は `column_ideas` として Telegram に 1 行出すだけ（代表が書く主題の材料）。代表が足したコラムの育成（内部リンク・ハブカード・新着・sitemap・`JA_ONLY_COLUMNS` の登録漏れの手当て）は週次が続ける
- **構成と流れの変更は、検査を通れば承認なしで公開する**（提案で止めない）。例外はナビ（`header.js`）を含む回だけ＝全ページに効くので、その回は全体を PR に出す

## なぜ週1か（毎日・3日に1回にしなかった理由）

- Search Console のデータは 2〜3 日遅れ、GA4 は 1〜2 日遅れで届く
- 問い合わせ（generate_lead）は週 6 件前後。1 日単位の増減は揺れでしかない
- Google が title の変更を反映するのに 1〜2 週間。同じページを週の途中でまた変えると、どの変更が効いたか永久に分からない
- 台帳 `docs/seo-change-log.md` はもともと「確認日＝2 週後・4 週後」で運用していた

## 4 層（＋月 1 回の構成レビュー）

| 周期 | 何が | 誰が | 場所 |
|---|---|---|---|
| 毎日 07:10 | GSC（検索語×ページ・端末・国）・GA4（着地・回遊・内部遷移・イベント）・本番 HTML の健診を台帳に蓄積。**手動 PR で足した新規ページを変更台帳へ自動で記帳**（`register_new_pages.py`）。**自動で公開したのに変更台帳に無いコミットの拾い直し**（`register_auto_commits.py`＝push のあとの記帳が失敗した回）。期限が来た変更の効果測定。**サイトの変更はしない** | launchd `ai.scix.web-metrics` → `scripts/seo/collect_daily.py` | 台帳 Drive `9_システム/scix-web解析/` |
| 日曜 06:00 | 台帳からブリーフ → Claude（Opus）が **既存ページ** を判断・編集（新しいページは作らない） → 機械の検査 → 通ったものだけ commit/push（Vercel が公開。**2 コミット**: 中身 `auto(seo): …` と、記帳 `chore(seo-log): …`＝sitemap の lastmod・変更日台帳）→ IndexNow → Telegram 3 行＋「✍️ 今週書くなら」（コラム主題の提案。マニフェスト `column_ideas`） | launchd `ai.scix.web-weekly` → `scripts/seo/weekly_run.sh` | 作業ツリー `~/projects/.scix-web-weekly` |
| 月の第 1 日曜（週次の直後） | **構成レビュー**: 台帳からブリーフ（通常の節＋構成用の S1〜S8）→ Claude（Opus）が構成の変更を 1〜3 件に絞って編集 → 機械の検査（`--profile structure`）→ **通れば週次と同じ手順で自動公開**（最新の origin/main へ載せ直し → push → タグ `auto/structure-YYYY-MM` → 変更台帳に `source: structure` で記帳）→ Telegram 3 行。**ナビ（`header.js`）を含む回だけ** 公開せず、枝 `auto/structure-YYYY-MM` へ push して PR（マージされたら翌朝の収集が記帳＝`register_structure_merges.py`） | 同じ launchd `ai.scix.web-weekly` → `weekly_run.sh` が続けて `MODE=structure` を 1 回（新しい plist なし） | 作業ツリー `~/projects/.scix-web-structure`・台帳 `weekly/<日付>/structure/`・`ledger/changes.jsonl`（PR の経路は `ledger/proposals.jsonl`） |
| 変更の 2 週後・4 週後 | 前後 14 日の GSC（クリック・CTR・順位）と GA4（着地→リード）を比べ、better / flat / worse を台帳に書く。worse は翌週の候補「差し戻し」。**新規ページは前後比較をせず立ち上がりで判定**（下の節） | `collect_daily.py` の中で `measure_changes.py` | `scix-web解析/ledger/` |
| main への push の都度 | 変わった HTML を IndexNow へ（Bing・Yandex 等）。Google は sitemap の lastmod と GSC の手動リクエスト | GitHub Action `.github/workflows/indexnow-on-push.yml` | |

両ジョブは実行前に `git pull --ff-only origin main` を打つ（launchd の plist 側）。GitHub で PR をマージすればローカルの main も追いつき、手で pull しなくてよい。ローカルに未 push のコミットがあれば pull は黙って見送られ、そのまま動く。

ページの **中身** は週次が毎週 3〜8 件変える（既存ページだけ。コラムは書かない）。**構成**（ハブの並び・トップの節の順・CTA の行き先・収益ページへの導線）は月 1 回、下の「月 1 回の構成レビュー」が変えて、検査を通れば自動で公開する。ナビだけは自動公開しない＝ナビを含む回は PR。ナビの組み替えは 90 日に 1 回まで＝週次では `header.js` の `JA_ONLY_COLUMNS` 以外を検査で弾き、構成レビューではナビ定義の変更を見つけたら変更台帳と `origin/main` の履歴で 90 日ルールを照合する。

## 月 1 回の構成レビュー（第 1 日曜）— 検査を通れば自動公開（ナビを含む回だけ PR）

2026-09-20 追加・同日に自動公開へ変更。数週間に一度、ページ内容とページ構成を変え、ヒットと問い合わせを増やす。ページ内容は週次がやっている。構成は週次が触れない（ナビ・ヒーロー・半分超の書き換えを検査が弾く）ので、月 1 回、別の枠で見直す。目的は **検索からのヒットを増やす・問い合わせを増やす**。当初は「効き方が大きく戻しにくいので PR で提案」だったが、提案で止めず **検査を通れば承認なしで公開** する。人の目が入らない分は、検査（HTML の入れ子・節と id が消えていないこと・導線の本数・ヒーローと `<head>`／`<style>`／`<script>`・本文の字数で測る量・触れないファイル）と、14 日後・28 日後の効果測定で受ける。判定（better／flat／worse）は GSC のクリックと CTR で決まり、worse は週次が差し戻す。**問い合わせ・送客が減っても worse にはならない**＝週次のブリーフ 8 節の表が「注意」（リード減・送客減）を付け、週次の Claude が差し戻すかを決める（機械が自動で戻すのは GSC の worse だけ、と読む）。

**頻度は月 1 回のまま**: Google の反映に 1〜2 週・効果測定に 2〜4 週かかり、同じページを 14 日以内に 2 度変えない（どの変更が効いたか分からなくなる）ため。

| 段 | 何が | どこに |
|---|---|---|
| 起動 | `weekly_run.sh` は通常の週次を子プロセスで今までどおり走らせ、その日が **月の第 1 日曜**（`date +%d` が 01〜07 かつ日曜）なら、続けて自分自身を `MODE=structure` で 1 回だけ起こす。週次の終了コードはそのまま返る＝構成レビューが失敗しても週次の結果は壊れない。同じ月のタグ `auto/structure-YYYY-MM`（自動公開済み）か枝 `auto/structure-YYYY-MM`（PR で提案中）が origin に既にあれば Claude を起こさずに終わる（1 か月に 1 回だけ）。ロックは週次と共用。`NO_STRUCTURE=1` で抑止、`FORCE_STRUCTURE=1` で日付に関係なく続けて走らせる | launchd は `ai.scix.web-weekly` のまま（plist は増やさない） |
| ブリーフ | `build_brief.py --structure` が通常の 1〜10 節のあとに **S1〜S8** を足す: S1 ナビのクリック（GA4 `nav_click` をグループ別）と **ナビの組み替えを提案してよいか**（90 日ルールの判定）／S2 遷移の太さ（トップ・ハブ・コラム・収益ページ・その他の 5×5 と、トップから・ハブから・各収益ページへ・収益ページ→フォーム）／S3 収益ページへの送客が多いコラム上位と、読まれているのに送客ゼロのコラム（標準の CTA ブロックの有無つき）／S4 28 日セッション 0 のページ／S5 サイト内被リンク 1 以下の孤立ページ／S6 カテゴリ別の本数と流入（JA・EN・ZH のハブの並び順どおり）／S7 トップの節の並びと、その節のリンク先への遷移／S8 これまでの構成の変更（自動公開・判定つき）と PR の提案。**8 節の末尾に「構成の変更」の表**: 変更台帳の `source: structure` ごとに、測る対象のページ（＝編集したページ）に着地したセッションと問い合わせ（generate_lead）の前後・そのページから送客先（`kpi_pages`。無ければ収益ページ全部）への遷移の前後・commit・判定・**注意**（14 日の窓がそろった行にだけ。リード減＝前 2 件以上が半分以下／送客減＝前 10 以上が 7 割未満）（週次のブリーフにも出る＝worse と注意つきの行が翌週の差し戻し候補。数字は Drive のブリーフと `brief.json` の `structure_changes` にだけ出す。`最新.md`・公開リポジトリ・コミット文・PR には出さない）。台帳と git（`origin/main` の `knowledge.html`・`index.html`・`header.js`）だけで決定論に作る（`scripts/seo/structure.py`）。**9 節「今週触らないページ」のハブ・トップだけ数え方が違う**: 週次は直近 14 日にそのファイルを触った全コミットで凍結するが、ハブ・トップはコラムを 1 本足すたびにカード・件数・新着が変わる＝ほぼ常に凍結され、hub-order／top-order を一度も提案できない。構成レビュー用のブリーフでは、ハブ・トップ（`/`・`/en`・`/zh`・`/knowledge`・`/en/knowledge`・`/zh-knowledge`）の凍結を **変更台帳の構成系のエントリだけ** で決める（`structure.is_structure_entry`＝class が hub／hub-order／top-order／nav／rollback（週次が構成の変更を差し戻した直後に、同じハブをまた並べ替えない）、または `source: structure`＝構成レビューが公開したもの（自動公開・PR のマージ）で、そのページが `pages` に載っている 14 日以内の変更）。git の履歴と、title・description・new-column などのエントリでは凍結しない。人が手で構成を変えたときは、変更台帳に class=hub で記帳してあれば凍結される（効果測定もそこから走る）。記帳の無いまま並び・見出し・本文が変わったコミット（`structure.unrecorded_layout_commits`＝カードの追加と焼き直しを抜いた骨格の比較）は、凍結せずに「参考」として 9 節の末尾に出す＝28 日の数字に変更前の期間が混ざることを Claude に知らせる。ハブ・トップ以外のページは週次と同じ数え方 | `weekly/<日付>/structure/brief.md`・`brief.json` の `structure`。週次の `brief.md` は上書きしない |
| Claude | `scripts/seo/structure_prompt.md`。ブリーフを根拠に構成の変更を **1〜3 件に絞って実際に編集**（0 件も可）。**新しいページは作らない**。見る材料の優先順: ①収益ページ・フォームへの送客が細い所 ②読まれているのに送客ゼロのコラムの出口 ③ハブのカテゴリ順・カード順と実際のクリック ④孤立ページ ⑤トップのヒーローより下の節の順。型は `hub-order`（ハブのカテゴリ順・カード順・立場別の入口）／`top-order`（トップのヒーローより下の節の順と見出し。節は消さない）／`cta-route`（コラム末尾の CTA の行き先）／`funnel-block`（収益ページへの導線ブロック）／`nav`（S1 が「提案してよい」と言うときだけ。**入れるとその回は全体が PR**）。各変更に **どの数字が根拠か（`rationale`）・仮説（`hypothesis`）・何が増えれば成功か（`kpi`）・いつ測るか（`measure`）** をマニフェストに書く。`pages` は **編集したページだけ**（前後比較の対象と「14 日触らないページ」の二役。GA4 のリードは着地ページに付くので、編集していない送客先の収益ページを入れると判定と凍結が狂う＝検査で止まる）。送客先は `kpi_pages`（任意・8 節の表の参考列だけ）。起動の条件（アカウント・`allowedTools`・モデル Opus・タイムアウト）は週次と同じ関数 `run_claude` | `weekly/<日付>/structure/changes.json` |
| 検査 | `guard_diff.py --profile structure`（下の節） | `guard.log` |
| 変更の有無 | **マニフェストの `changes` の件数で決める**（`git status` だけで決めない）。Claude は仕上げで `gen_knowledge_jsonld.py --write` を走らせるので、変更を取り下げて `changes: []` にしても焼き直しの差分（NEW バッジの期限切れ・ItemList の順）が作業ツリーに残る。`changes` が空なら差分があっても公開も PR もせず、「今月は変更なし＋`no_change_reason`」を通知して終わる（タグも枝も作らない＝同じ月に手で回し直せる）。検査（`--profile structure`）も「0 件なのに差分がある」を止める | |
| 経路 | 検査の最後の行（「経路: 自動公開」／「経路: PR」）と、シェル自身が見た `header.js` の差分・マニフェスト（`class: nav`／`files` に `header.js`）の **どれかが PR と言えば PR**（公開しない側に倒す）。ナビは全ページに効くので自動公開しない。混じっていたら **その回は全体を PR**（一部だけ公開、をしない＝検査済みの単位を崩さない） | `guard.log` |
| 公開（ナビを含まない回） | 週次と同じ手順（シェルの `commit_log`・`publish_main` を共用）: **①中身のコミット**（`auto(structure): …`・Claude の編集と焼き直し・本文に差し戻し方）→ **②記帳のコミット**（`chore(seo-log): …`＝sitemap の lastmod（マニフェストの HTML だけ）と、公開リポジトリの変更日台帳 `docs/seo-change-log.md` の行）→ 最新の `origin/main` へ載せ直し（**衝突したら公開しない**）→ `git push origin HEAD:main` → タグ `auto/structure-YYYY-MM`（①を指す）→ 手元の main を早送り。2 つに分ける理由: 変更日台帳は毎週、表の同じ位置に行が足される＝①に混ぜると、案内している `git revert <sha>` が次の自動コミット 1 つで必ず衝突する。IndexNow は push 時の GitHub Action が送る（シェルは本番反映を待たない）。`DRY_RUN=1` は push も記帳もせず、作業ツリーと `proposal.diff` を残す | main・タグ `auto/structure-YYYY-MM` |
| 記帳（公開した回） | `record_changes.py --source structure --commit <①の sha>` が変更台帳へ: id `structure-YYYYMM-N`・`source: "structure"`・各変更の `class`・`pages`・`kpi_pages`・`measure`・`private_note`・`check_days: [14, 28]`。push のあとなので、失敗しても公開は取り消せない＝**3 回までやり直し、だめなら Telegram の 3 行目を「台帳の記帳に失敗＝まだ効果測定の対象になっていない」に差し替える**。翌朝の収集が `register_auto_commits.py` で拾い直す（`origin/main` の件名 `auto(seo):`／`auto(structure):` のコミットのうち変更台帳に commit が無いものを、その回のマニフェスト `weekly/<日付>[/structure]/changes.json` から記帳。変更日＝コミットの日付・`recovered: true`。同じ commit は二重に記帳しない）。以後は週次の変更と同じ流れ＝`measure_changes.py` が 14 日後・28 日後に前後比較（GSC のクリック・CTR と、そのページ着地のリード）し、**worse は翌週の週次ブリーフ 8 節に出て差し戻し候補**（週次が `class: rollback` で戻す）。ハブ・トップは 14 日間「今週触らないページ」になる | `ledger/changes.jsonl` |
| PR（ナビを含む回） | 作業ツリーで commit（`auto(structure): …`）→ `git push origin HEAD:refs/heads/auto/structure-YYYY-MM` → `gh pr create`（本文＝マニフェストの要約・根拠の数字・成功の定義・測る日・「マージで公開、閉じれば不採用」）。**main へは push しない・IndexNow も送らない**。sitemap の lastmod と `docs/seo-change-log.md` は PR に入れない（毎朝の案件一覧の同期と毎週の自動更新が同じ行を書くので、PR が開いている間に衝突する）。`gh` が無い／失敗なら Telegram に枝名と compare の URL。`DRY_RUN=1` は push も PR もせず、作業ツリーと `proposal.diff`・`pr_body.md` を残す | PR・`weekly/<日付>/structure/pr_body.md` |
| 記帳（PR の回） | 台帳には **提案（PR 番号つき・未公開）** として `ledger/proposals.jsonl` に `status: proposed` で残す。変更台帳（`changes.jsonl`）には書かない＝公開されるまで効果測定も「今週触らないページ」も動かさない | `ledger/proposals.jsonl` |
| Telegram | 1 通 3 行以内。公開した回:「構成を見直して公開しました＋何を変えたか／根拠 1 行／戻すなら `git revert <①の sha>` → push（GSC の判定が worse なら週次が戻し、問い合わせ・送客の減りは 8 節の表で見て戻す）」。台帳の記帳に失敗した回は 3 行目がその警告になる。PR の回:「構成の見直し案（ナビを含むので自動公開せず）を PR #NN に置きました／根拠 1 行／マージで公開」。変更なしの月は 1 行 | |
| マージ後（PR の回だけ） | 毎朝の収集が `register_structure_merges.py` を呼ぶ（新規ページの自動記帳 `register_new_pages.py` とは別）。`origin/main` の履歴だけを見て、件名が `…(#NN)`（squash マージ）か `Merge pull request #NN` のコミットを探し、見つけたら **変更日＝マージコミットの日付** で変更台帳へ足す（id は提案と同じ＝重複しない・`source: "structure"`・`check_days: [14, 28]`・`class: nav` は `nav_change: true`）。以後は `measure_changes.py` が 14 日後・28 日後に前後比較。PR 番号が無い提案は、提案のコミットと同じ中身のファイルを **最初に持ち込んだ** コミット（親コミットでは違う中身）で照合する。同じ提案の別の行（マニフェストの変更 1 件ごとに 1 行）は同じマージコミットに当たってよく、別の提案が記帳済みのマージコミットは飛ばして先を探す（そこで打ち切らない）。60 日マージされなかった提案は `expired`（不採用とみなす。PR を閉じたかどうかは `gh` が要るので見ない） | `ledger/changes.jsonl`・`ledger/proposals.jsonl` |

**未対応（割り切り）**:
- PR の回だけ: マージ後に sitemap の lastmod は進まない（PR に入れていない）。Bing 等へは push 時の Action が IndexNow を送る。Google へ急ぐなら GSC の URL 検査から手動で。自動公開の回は週次と同じく lastmod を進める。
- PR の回だけ: 公開リポジトリの変更日台帳 `docs/seo-change-log.md` に行は足さない（Drive の変更台帳だけ）。残したければマージ後に手で。自動公開の回は週次と同じく行を足す。
- PR が開いている間に main が同じ場所を変えると（例: トップの `#find` 節を動かす提案と、その節の中の `<!--S:shv-->` の件数の更新）GitHub 上で衝突する。閉じれば翌月その時点の数字でまた提案される。載せ直しは手動。
- S7（トップの節）の「リンク先への遷移」は節ごとのクリックではなく、行き先ごとの遷移を節へ割り当てた近似（同じ行き先を複数の節が持つと両方に数える）。節ごとに測るにはトップのリンクに計測用のパラメータが要る。
- S1 の `nav_click` は 2026-09-17 の計測開始。グループ別までで、引き出しの中のどの行き先かは取っていない（GA4 のカスタムディメンションが要る）。
- 構成の変更の効果測定は、週次の変更と同じ判定式（GSC のクリックと CTR が主・着地リードが増えれば better）。**問い合わせ・送客が減っても worse にはならない**（件数が少なく、機械の判定に入れると誤って戻す回数が増えるため入れていない）。代わりに 8 節の表の「注意」（リード減・送客減）を週次の Claude が読んで、差し戻すかを決める。逆に、構成の変更と関係のない GSC の揺れで worse が付くこともある＝週次は着地・リード・送客も見てから戻す。ハブの並べ替えのように「ハブ → コラムの遷移」が本来の KPI の変更は、判定が flat でもブリーフ S2・S6 の遷移で読む。
- 差し戻しの `git revert <①の sha>` は、同じファイルの同じ場所をその後の変更が触っていれば衝突する（ハブはコラムを足すたびにカードが増える）。記帳のコミットとは衝突しない。衝突したら、その場所だけ手で戻す。
- 入れ子の検査は、id つきの要素を別の深さ・別の親へ動かす変更も止める（閉じタグの置き去りと区別できないため）。意図した移動なら同じ親の中で。
- 第 1 日曜の回が検査・衝突で止まった月は、その月は構成の変更なし（次の日曜に自動では回し直さない。手で `MODE=structure` を回せば、タグも枝も無いのでもう一度走る）。
- 導線の本数の検査は `<a href>` を数える。ボタンの `onclick`・`header.js` が描くナビは数に入らない（ナビは PR の経路で人が見る）。

## 新規ページ（代表が毎週足すコラム）の流れ — 毎日の記録 → 週次の育成 → 効果測定

2026-09-20 追加。それまでは、人が PR で足したコラムが変更台帳に載らず（直近 28 日の新規 HTML 85 本のうち台帳にあったのは 1 本）、ブリーフにも新規ページの節が無く、効果測定は前の窓が 0 なので 1 クリックで必ず better になっていた。 **コラムを書くのは代表**（2026-09-20）。自動の側は新しいページを作らず、足されたページを記録し、育て、測るだけ。

| いつ | 何が | どこに |
|---|---|---|
| 毎日 07:10（収集のあと・効果測定の前）。週次の冒頭でも同じものが走る | `scripts/seo/register_new_pages.py` が **origin/main の git 履歴** から直近 28 日に足された `*.html` を拾って記帳。3 言語版（`column-x.html`・`en/column-x.html`・`zh-column-x.html`）は 1 エントリ。id は `new-<slug>` 固定＝何度走っても重複しない。台帳のどれかのエントリの `pages` に既に居るページは足さない（手で記帳した PR・2026-09-20 までの週次の自動 new-column と二重にしない）。JA 先行で EN/ZH を後から足したときは `new-<slug>-en-zh` に残りだけ。`404`・`thanks`・noindex は除く | `ledger/changes.jsonl`（`source: "manual-auto"`・`class: "new-column"`／コラム以外は `"new-page"`・`check_days: [14, 28]`） |
| 公開の 14 日後・28 日後（GSC がその日まで届いたら） | `measure_changes.py` が class `new-column`／`new-page` を **立ち上がり**（`mode: "ramp"`）で判定。14 日: 公開日〜+14 日に表示が 1 以上あれば `shown`、無ければ `not-shown`。28 日: 公開翌日〜+28 日の表示を、**同じ言語の既存コラム**（健診のページ一覧＝sitemap。公開 60 日以内の新規は母集団から外す。表示ゼロのコラムも入れる）の同じ 28 日の表示の中央値と比べて `above-median`／`below-median`、表示ゼロは `not-shown`。ページごとの判定は `by_page`、エントリの判定は主たるページ（JA→EN→ZH の順で最初）。判定済みのレコードは触らない。**1 件の不正で全体を止めない**: エントリごとに例外を受けて飛ばす（ログに id）。`pages` が空の新規ページは `insufficient` で閉じる。暦に無い `datePublished`（例 `2026-09-31`）は無いものとして git の初回コミット日を使う。`measurements.jsonl` への追記は `changes.jsonl` を書き戻したあと＝途中で落ちても同じ行が毎朝増えない | `ledger/changes.jsonl` の `measured`・`ledger/measurements.jsonl` |
| 日曜 06:00（ブリーフ） | `build_brief.py` の **10 節「新規ページ（公開 60 日以内）の立ち上がり」**: ページ／公開日（Article JSON-LD の `datePublished`、無ければ git の初回コミット日）／経過日数／初表示日／28 日の表示・クリック／GA4 着地／サイト内被リンク数（自分自身は除く）／旗。旗は「公開14日超で表示ゼロ」「被リンク1以下」「sitemap 未登録」「JA専用の登録漏れ」。旗つきを先に最大 40 行。**10b**「sitemap にあるのに 90 日表示ゼロ（公開 14 日以上）」最大 20 行。8 節には `not-shown` のまま直近 28 日も表示ゼロのページが **要手当て** として出る（worse と同じ位置。ただし差し戻しではなく育成）。自動記帳のエントリは 8 節の表には並べず件数だけ | `weekly/<日付>/brief.md`・`brief.json` の `new_pages`・`zero_impression`。`最新.md` にも 10 節を短く |
| 日曜 06:00（Claude） | `weekly_prompt.md`「今週やること」7『新規ページの育成』: 旗・要手当てのページへ、関連コラム・ハブから内部リンクを足す（**リンクを置く側が 9 節「今週触らないページ」なら置かない**）。その週に人が足したコラムのハブカード・新着・sitemap・`JA_ONLY_COLUMNS` の登録漏れを点検。1 週の変更件数の上限は変えない | 公開は従来どおりシェルと `guard_diff.py` |
| 日曜 06:00（ブリーフ・Telegram） | `build_brief.py` の **11 節「アクセスが減ったページ」**（`scripts/seo/access_drop.py`・決定論）: 4 節と同じ基準（28 日クリックが前 28 日の 7 割未満・前 28 日 20 クリック以上）で減ったページに、**原因の型**（順位落ち／表示減／CTR落ち）と**本文の時点**（本文が名乗る「◯年◯月時点／版／現在／更新」の最新日付。「公表」「改定」は外部文書の日付なので見ない）と**次の手**（時点が 90 日以上前 → 本文の時点更新（CC）／CTR落ちだけ → title・description（週次）／それ以外 → 本文の受け皿を見直す（CC 判断））を添えて、失ったクリック順に表で出す。**週次の Claude は外部サイトに出られないので、一次資料が要る時点更新は自動でやらない**（`weekly_prompt.md`: CC の行の日付・件数は直さない）。日曜朝の Telegram に先頭の 1 本と本数を 1 行（`weekly_run.sh` の `drop_line`）＝時点更新は CC の作業セッションで代表の指示で（2026-09-22 中島決定「トリガーはアクセス減」。同日の /column-jcstar・/column-lda PR #95 が型）。`最新.md` にも上位 10 本 | `weekly/<日付>/brief.md` 11 節・`brief.json` の `access_drops` |

どれも台帳と git だけで決定論に作る（追加 API なし）。ページ一覧と公開日は作業ツリーではなく `origin/main` から読む（別ブランチに居ても、未コミットの原稿があっても結果が変わらない。`origin/main` が無いときは記帳しない）。試すときは `SCIX_WEB_LEDGER=<複製>` で台帳の向き先を変える（`common.py`）。

## 週次の Claude に渡すもの・渡さないもの

- 渡す: ブリーフ（`scix-web解析/weekly/<日付>/brief.md`）・規約の正本（scix-web の記憶 6 本）・リポジトリの CLAUDE.md・読む／編集する／リポジトリ内の python3 を叩く道具
- 渡さない: git commit / push / branch、gh、Web 取得、サブエージェント。**公開はシェルだけが行い、その前に `guard_diff.py` が検査する**
- 動かすアカウント: OpenClaw 用（`~/.openclaw/openclaw.json` の `CLAUDE_CONFIG_DIR`）。代表自身の枠には落とさない。モデルは Opus（Fable は同じ仕事に枠 5 倍・2026-09-17 実測）

## 検査（guard_diff.py）で止まるもの

週次（既定の `--profile weekly`）で触ってよいのは HTML・sitemap・`header.js` の `JA_ONLY_COLUMNS` 行だけ（`docs/seo-change-log.md` はマニフェストからシェルが記帳する）。フォーム（contact / sell-form / thanks / privacy）・`/fund`・`vercel.json`・`projects.json`・`robots.txt`・`scripts/`・`.github/`・`img/`・`files/`・削除は弾く。
**新規ファイルは 0**（2026-09-20〜。「新しいページは自動では作らない（コラムは代表が書く）」で止める。マニフェストの `class: new-column` も止める。検査は自動フロー専用＝代表が PR で足すコラムはここを通らない。新コラムの必須ブロックの検査は、書かなくなったので外した）。既存ページ 12 本まで、1 ファイルの差し替えは半分未満・削除は 1/4 未満＝**行数と、本文の字数（`<body>` の見える文字。`<style>`・`<script>`・`<!--S:…-->` は除く）の両方** で測る。コラムは CSS と script が行の大半で、行数だけだと本文を総入れ替えしても 1 割に満たない＝代表のコラムが同じ URL のまま別の記事に置き換わる抜け道だった。ハブ・トップは、マニフェストに書かなければ焼き直しの範囲（本文 600 字）まで、書いても足せるのは 1500 字・消せるのは 1 割まで（記事ぶんの節は足せない）。**HTML の入れ子**: タグの開閉の不一致が変更前より増えていないこと、id つきの要素・`<section>`・`<footer>` の入れ子の位置（深さと祖先の id）が変わっていないこと、id つきの要素と節が消えていないこと（差し戻し `class: rollback` のファイルだけ消してよい）。**ファイルの削除だけの差分も止める**（以前は「変更なし」で通っていた）。**robots の noindex を足さない。ハブ・トップの `<style>` と `<script>`（JSON-LD 以外）は変えない**（ヒーローの中身が同じでも CSS・JS で消せる）。**公開される欄（`summary_lines`・`summary`・`rationale`・`hypothesis`・`kpi`・`before`・`after`）に問い合わせの件数を書かない**（コミット文と変更日台帳は公開。件数は `private_note` へ＝Drive の台帳にだけ残る。「語の直後の数字」だけでなく、括弧や「前→後」が挟まる形・数字が先の形・フォーム送信／CV も止める）。マニフェストの各変更に `pages`（`/` で始まる URL パス）が要る（空のまま変更台帳に入ると効果測定の対象が無い）。title（**ページの最初の `<title>` だけ**を読む。本文のインライン SVG の `<title id="fig…">` を連結すると、重複の検査が黙って外れ、EN の 70 字検査が図つきコラムを誤って止める）・description・canonical・h1 1 つ・`/header.js`・JSON-LD・内部リンク切れ・EN の title 70 字／description 155 字・自称「中立」・実績の主張・鍵らしき文字列・マニフェストと差分の不一致。トップ（`index.html`・`en/index.html`・`zh.html`）は `<body>` の先頭からヒーローの終わりまでが同一であること。`<!--S:…-->` の内側は毎朝の同期が書く場所＝変えない（ナレッジの件数・最終更新・新着 `kcount`／`kdate`／`knew` は週次のシェル自身が `gen_knowledge_jsonld.py` で焼き直すので対象外）。`projects.html` の `<script>` も変えない。

**規則の番号で止めるもの**（2026-09-23 に足した・直した分。週次・構成レビューの両方。止める理由には規則の番号が出る）:
- **量**: 週次のマニフェストは 8 件まで・既存ページは 12 本まで
- **14 日の凍結**: 数え方はブリーフ 9 節と同じ `build_brief.cooldown_pages(strict=True)`（git の履歴・変更台帳を読めなければ止める＝黙って「凍結ゼロ」で通さない）。見るのはマニフェストの `files`（編集したページ）。ハブ・トップも対象: 週次はカードの追加（`class: hub`＝サイトの決まり の例外）だけ凍結を当てず、そのときも凍結中なら title・description・`<head>` は変えさせない（`class: title`・`internal-link` などは凍結を当てる）。凍結中のハブ・トップで `class: hub` のときは、足した行が既存のカードと同じ形のカード（同じ要素と class・中にリンクが無い・行き先はコラム 1 本）だけで、そのコラムのカードが変更前のハブに無い（登録漏れの手当て。既にカードのあるコラムの 2 枚目は不可）かを確かめ、段落・リンク・見出し・消した行・書き換えた行が混じれば凍結を当てる（申告した class だけでは凍結を外さない）。マニフェストに載せないハブ・トップは焼き直しだけ: 焼き直しの所をそろえても差分が残れば、凍結中なら止める（申告しないだけで凍結を抜けさせない）。焼き直しが書かない `en/index.html`・`zh.html` と構成レビューは、載っていない書き換えをそのまま止める。構成レビューは、構成系の記帳（hub・hub-order・top-order・nav・rollback・`source: structure`）だけで数えた凍結を当てる（週次が差し戻した直後のハブは並べ替えない。コラムを足しただけの週は凍結されない）。マニフェストに載せずにハブ・トップの title・description・`<head>` を変えるのも止める（焼き直しが変えるのは「全N記事」の数字と JSON-LD だけ）
- **差し戻し**（`class: rollback`）: `rollback_of`（戻す元の commit）が必須。いまの差分が元の commit の逆向き（足した行が元の commit で消えた行・消した行が元の commit で足した行。焼き直しの差と並べ替えも同じ物差し）と確かめられたファイルだけ、凍結を外し・足した節の削除を許す。確かめられなければ普通の変更と同じに扱う（凍結中なら止まる）。焼き直しの所（ナレッジのハブの ItemList・`<!--S:kcount／kdate／knew-->`・NEW バッジ・「全N記事」）をそろえるのは `gen_knowledge_jsonld.py --write` が書くファイルだけで、コラムなどは JSON-LD・`<!--S:…-->`・NEW バッジも比べる。そろえると差分が空（焼き直しの所しか変えていない）なら確かめられない扱い。元の commit はブリーフ 8 節の表の commit 列
- **非公開の禁止語**: 語はリポジトリの外の一覧 `~/.config/scix-web/private_banned.tsv`（1 行＝正規表現<TAB>規則ID）から読み、止める理由には規則IDとファイル（欄）だけを出す。ほかの理由が抜粋を写すときも、切る前の文と出現を含む行の全体に当て、当たれば抜粋を出さない（窓の端で切れた語の残りも出さない）。一覧が無い・読めない・式が 0 個・壊れた行があれば **毎週「読めないので止める」で公開されない**（Telegram には出ない＝ログを朝ルーチンが読む）。clone では戻らないので、新しい Mac には旧 Mac から rsync で移す（`docs/new-mac-setup.md`）
- **公開される欄の案件ID・金額・「一次情報」**: `proposal_title`・`summary_lines`・`summary`・`rationale`・`hypothesis`・`kpi`・`measure`・`before`・`after`。ただし `before`・`after` が公開されるのは構成レビューの PR 本文だけ＝週次の `before`・`after` には掛けない（元の title に円の金額があるページを直すと止まっていた）
- **ファンドの数字**: IRR・利回り・年利・リターン・手数料（率）・手付・募集（総・金）額・出資額・分配・配当・1口と、成功報酬・フィーと、英語・中文の yield・return・fee・dividend・minimum investment・subscription・per unit・carry・carried interest・hurdle・收益率・回报率・手续费・认购・分红・年化のあとの数字（％・円）。数字が先に来る形（「3%の手数料」「a 3% fee」「3% management fee」「8% annual return」「5% p.a. return」「20% carried interest」）と「年N%を目指す」も。ページ全体の出現の前後で比べ、増えた分だけ止める（既存の公表資料の数字・文を動かしただけの行は止めない）
- **コラムから /fund への導線**: コラム（JA・EN・ZH）で `/fund` を指す `<a>` の本数が増えたら止める（既存のフッターの 1 本は数えるだけ）。書き方はそろえて数える: `https://scix.co.jp/fund`（www 無し）・`//www.scix.co.jp/fund`・相対の `fund.html`／`../fund`・`vercel.json` のリダイレクトと `invest.scix.co.jp`（rewrites で /fund。host の rewrites に出るホストは `/fund`・`/fund.html` などほかのパスも自サイト）。外のサイトの `/fund` は数えない。`vercel.json` が読めなければ止める（数え方が甘くなるので）
- **英語・中文のページの証券化**: `en/`・`zh-`・`zh.html` に GK-TK・securitization・匿名組合・证券化 を新たに書いたら止める（ページ全体の出現の前後。代表の決定で今あるページは対象外＝これから足す分だけ。検査は今ある文を数えない）
- **自称の「中立」「neutral」**: ページ全体の出現（同じ行の前後 20 字の文脈）の前後で比べ、新しく現れた分だけ止める（既存の行を動かす・離れた所を直すだけなら止めない）。止めないのはシナリオ名（強気・中立・弱気／「中立：約…」・表の見出し・「中立」シナリオ／neutral scenario・the neutral case）・技術中立・carbon-／climate-／net-／technology-neutral・アンカーの id だけ。引用符でくくっただけの自称（当社は「中立」の立場・“neutral” party）と vendor-neutral・manufacturer-neutral・EPC-neutral・a neutral case manager は止める

**`--profile structure`（月 1 回の構成レビュー）で変わるところ**（承認なしで公開するので、人の目の代わりをここが持つ）:
- 量: マニフェスト 3 件まで・新規ファイル 0・削除なし。1 ファイルの差し替えは **並べ替えを除いた正味** で測る（行を多重集合で比べる＝節やカードを動かしただけなら 0）。正味の書き換え 1/4 まで・正味の削除 15% まで・見かけの差し替え（+ と − の合計）120% まで（動かした行は両方に数えられる）。本文の字数でも同じ上限（1/4・15%）。既存ページ 12 本までは同じ
- HTML の入れ子・節と id が消えていないこと（上の週次と同じ検査。構成レビューに差し戻しの例外は無い）。行の多重集合は、閉じタグを置き去りにした節の移動（以降の節が全部その節の子になる）と素の並べ替えを区別できないので、ここで止める
- ハブ・トップはヒーローより下だけ: `<body>` の先頭〜ヒーローの終わり（トップ＝`<section class="hero">` の終わり、ハブ＝最初の `</h1>`）が同一。title・description・canonical も同一（数字だけの違いは無視＝「全 N 記事」の焼き直し）。`<head>` のほかの meta・link（robots・hreflang・og）と、ページの `<style>`・`<script>` も同一。ハブ・トップ以外のページ（cta-route・funnel-block の対象）は title・description・h1 が同一
- **収益ページ・フォームへの導線を減らさない**: 変更したファイルごとに、href が `/contact`・`/projects`・`/transfer`・`/investors`・`/fund`・`/sourcing`・`/sell-form`（EN/ZH のフォーム `/en/contact`・`/zh-contact` も）を指す `<a>` の本数が、変更前より減っていたら止める（`?query`・`#hash`・`.html`・自サイトの絶対 URL はそろえて数える。コメントアウトは消したのと同じ）。行き先の付け替えと、同じファイルの中での置き場所の移動は通る。ファイルごとに見る＝総数も減らない。流れを良くするつもりの変更が導線を消す事故を止める
- `<!--S:…-->` の内側は並び順を問わず同じ中身（節ごと動かすのは可・中身の書き換えは不可）
- `header.js`: `JA_ONLY_COLUMNS` に加えて **ナビ定義**（`GROUP_PAGES` 〜 `var nav = […];`）を変えてよい。ナビ定義が変わっていたら、マニフェストの `class: nav` のエントリの申告（`nav_rule.last_nav_change`。直近 90 日に無ければ `null`）と、変更台帳（`class: nav`／`nav_change`）＋ `origin/main` の `header.js` の履歴（ナビ定義が親コミットと違うコミット）から計算した直近のナビ変更日とを照合する。直近 90 日にナビ変更があれば止める・申告が合わなければ止める・申告が無ければ止める。ナビ定義と `JA_ONLY_COLUMNS` 以外（CSS・計測・更新メール・言語切替）は変えられない
- マニフェストの各変更に `pages`・`hypothesis`（仮説）・`kpi`（何が増えれば成功か）・`measure`（いつ何で測るか）が要る。`pages` は編集したページ（`files` の URL）だけ＝送客先の収益ページは `kpi_pages` へ（`class: nav` は除く）。`rationale` には数字が要る。`class` は hub-order / top-order / cta-route / funnel-block / nav。**コミットの件名と本文・変更日台帳・PR の題と本文は公開リポジトリに載る** ので、公開される欄（`proposal_title`・`summary_lines`・`summary`・`rationale`・`hypothesis`・`kpi`・`measure`・`before`・`after`）に問い合わせの件数らしき書き方があれば止める（件数は `private_note` へ＝Drive の台帳にだけ残る）。マニフェストが 0 件なのに差分がある（焼き直しだけ）も止める
- 最後に **経路** を 1 行で出す:「経路: 自動公開（ナビを含まない）」か「経路: PR（header.js の変更を含む…）」。`header.js` の差分か、`class: nav`／`files` に `header.js` のエントリが 1 つでもあれば PR
- それ以外（触ってはいけないファイル・title・canonical・h1・JSON-LD・リンク切れ・鍵・自称中立・実績の主張・上の「規則の番号で止めるもの」など）は週次と同じ。14 日の凍結はハブ・トップにも当てる（構成系の記帳だけで数える）

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
python3 scripts/seo/register_new_pages.py --days 60     # main へマージした初回だけ 1 回: ブリーフ 10 節（公開 60 日以内）のページを全部台帳に載せる（毎朝の既定は 28 日）
python3 scripts/seo/selftest_ramp.py                    # 立ち上がり判定と、構成の変更（source=structure）の前後比較・ブリーフ 8 節の合成テスト（一時ディレクトリ・本物の台帳に触らない）
python3 scripts/seo/build_brief.py --structure --stdout # 構成レビュー用のブリーフ（S1〜S8 つき）を見る
MODE=structure DRY_RUN=1 bash scripts/seo/weekly_run.sh # 構成レビューを push も記帳も PR もせずに一周（ログに経路が出る）（作業ツリー ~/projects/.scix-web-structure と proposal.diff を残す）
MODE=structure bash scripts/seo/weekly_run.sh           # 構成レビューを手で 1 回（日付に関係なく。検査を通れば公開。今月のタグか枝が origin に既にあれば何もしない）
NO_STRUCTURE=1 bash scripts/seo/weekly_run.sh           # 第 1 日曜でも構成レビューを続けて走らせない
python3 scripts/seo/register_structure_merges.py --dry  # PR の経路（ナビを含む回）の提案の状態（proposed / merged / expired）と、記帳されるはずのマージを見る
python3 scripts/seo/selftest_structure.py               # 検査（新規ファイル 0・導線の本数・ヒーロー・入れ子・本文の量・公開欄の件数・経路・凍結と差し戻し・規則の番号で止めるもの）とマージの記帳の合成テスト（複製の中で。本物に触らない）
python3 scripts/seo/selftest_publish.py                 # weekly_run.sh を偽の origin とスタブ（claude・openclaw・gh・curl）で一周: 2 コミット・差し戻しが衝突しない・記帳の失敗と拾い直し
python3 scripts/seo/register_auto_commits.py --dry      # 自動で公開したのに変更台帳に無いコミット（記帳の失敗）を、書かずに一覧
# weekly_run.sh を本物に触らずに試す向き先: SCIX_WEB_REPO（複製のリポジトリ。origin も複製に）・SCIX_WEB_LEDGER・SCIX_WEB_STATE（ロック）・
#   SCIX_WEB_WT／SCIX_WEB_WT_STRUCTURE（作業ツリー）・NO_COLLECT=1（API を叩かない）。claude・openclaw・gh・curl は PATH の先頭にスタブを置く
#   （launchd 同等の `env -i HOME=$HOME /bin/bash -lc` は PATH を作り直すので、その中で先頭に足して `command -v claude` で確かめる）。
#   MODE=weekly を通すと最後に scripts/ping_indexnow.py が本物の IndexNow へ送る＝https_proxy=http://127.0.0.1:9 を付けて外へ出さない
SCIX_WEB_LEDGER=/private/tmp/ledger-copy python3 scripts/seo/collect_daily.py --no-gsc --no-ga4 --no-health   # 複製した台帳で記帳→計測→最新.md だけ試す
git revert <auto(seo)／auto(structure) のコミット> && git push   # 差し戻し（IndexNow は Action が送る）。すぐ上の chore(seo-log) は記帳（sitemap の lastmod・変更日台帳）＝revert しない
launchctl bootout gui/$(id -u)/ai.scix.web-weekly       # 週次を止める
```

GA4 のトークンが無いときは GA4 だけ飛ばして動く。取得は `python3 scripts/seo/ga4_auth.py`（ブラウザで 1 回許可）。

## 頁の形の検査と、機械で作る頁の部品（2026-11-22 中島「Seo 対策も徹底してやって」）

| 物 | 何をするか | 使い方 |
|---|---|---|
| `scripts/seo/audit_pages.py` | 全頁の head・構造化データ・sitemap を手元のファイルだけで点検する。FAQPage の問いが本文にあるか・Article の author／publisher の `@id`・ロゴ（紺）・パンくずにアンカーが無いか・`max-image-preview:large`・sitemap の hreflang／lastmod が頁と同じか・llms.txt・コラム末尾の入口の行き先（絞り込みの検索や件数0の入口を指さない）・市場データの表（caption・th scope・time・「いちばん新しい行の1文」の数字が表にあるか）・月報の画像の幅高さ・英語中国語のコラムの対のリンク。題と説明の長さは「注意」で `--strict` に数えない。トップ3頁（index.html・en/index.html・zh.html）も同じ検査を受ける（2026-11-22 に除外を外した） | `python3 scripts/seo/audit_pages.py --strict`（PR の前に通す） |
| `scripts/add_column_entrances.py` | 日本語のコラム末尾の入口の区画（マーケットの静的な入口・市場の数字への静的リンク）を作り直す | `python3 scripts/add_column_entrances.py [--check]`（projects.json の件数が変わって件数0の入口ができたら回す） |
| `scripts/add_column_related.py` | 英語・中国語のコラムに、日本語の対と同じ「あわせて読む」・用語集・市場の数字のリンクを作る | `python3 scripts/add_column_related.py [--check]` |
| `scripts/build_llms_txt.py` | `/llms.txt`（sitemap の頁の題と説明の一覧）を作る。title・description を変えたら回す | `python3 scripts/build_llms_txt.py [--check]` |
| `scripts/seo/market_side.py` | 週のブリーフの「12. マーケット側の検索」（ホスト別・dealroom の頁の種類別・語の定点25語・URL 検査の定点20本）。URL 検査は週に1回、台帳 `inspect_market/` に溜める（案件の頁は projects.json から実行時に選ぶ＝案件の住所をコードに書かない。301 で移る古い入口 /catalog・/wanted は入れず、移った先の /・/needs を見る） | `collect_daily.py` が自動（`--inspect` で今日取る） |

sitemap の lastmod は頁の JSON-LD `dateModified` と同じ値にし、前の値より古くしない。題・説明・区画・リンクなど頁を変えた日に、その頁だけ `stamp_sitemap.py <頁>` で今日にする（lastmod と一緒に `dateModified`・`article:modified_time` も同じ日に動く）。構造化データ・robots・img の寸法だけの直しは頁を変えた日に数えない。月報の頁・市場データの頁は生成器（`build_reports.py`・`build_report_data.py`）が「発行日と今の sitemap の値の新しいほう」を JSON-LD と sitemap の両方に書くので、焼き直しで日付が戻らない。`sync_sitemap_lastmod.py --write` は頁の dateModified があればその値に揃え、無ければ最後の commit の日（広い直しの直後に回さない）。

トップ3頁（`/`・`/en`・`/zh`）の作り替え（#237）は、sitemap.xml と変更台帳の2本が、同じ週に入る広い直し（#238 など）と行の並びで衝突した。取り込む側は、sitemap.xml を先に入った main の版にしたうえで `python3 scripts/seo/stamp_sitemap.py index.html en/index.html zh.html` でトップ3行の lastmod を今日にし直す（自分の側の版にすると、main が進めた lastmod と x-default が戻る）。変更台帳（`docs/seo-change-log.md`）は同じ日の行の並びで衝突するので、衝突の印だけ消して両方の行を残す。

## 数字の置き場

公開リポジトリ（この docs と change-log）には GSC の数字だけ。GA4 のリード数・用件別は Drive の台帳側（`scix-web解析/`）。Web 版 Claude・スマホは `scix-web解析/最新.md`（毎朝の写し・読み取り専用）。

## SmartNews 用の全文フィード（2026-10-30）
`scripts/build_feed.py` が `feed.xml`・`projects-feed.xml` と一緒に `smartnews.xml`（SmartFormat 2.2・全文・新しい順20本・1MB 未満）を焼く。本文は記事の `.article-body` から導線の箱（`data-scix-*`）・目次・連載の箱・署名・CTA を外し、`style`/`target` 属性を落とし、リンクと錨を絶対 URL にしたもの。SmartNews の申請（`_作成物/20261029_被リンク施策/08`）の前提で、検証は https://sf-validator.smartnews.com/ 。

## 出所の印・送客の数え方・社内の閲覧（2026-11-21）
2つのレポートが十分に読まれていないという見直しの第1段（測る分）。`header.js` の「7. 測る仕組み」。頁の見た目・中身・読み込み直後の href は変えない。

| 仕組み | 中身 | 見る所 |
|---|---|---|
| 出所の印 | 蓄電所マーケット（dealroom.scix.co.jp）へのリンクを押す（触る）直前に `src=<頁の印>` を足す（すでに src があれば替えない・`lang=en` などは残す）。印はコラム `col-<slug>`・市場ノート `report`／`report-<YYYY-MM>`・ナレッジの一覧 `knowledge`・トップ `top`・ほか `site-<頁>`。英語は末尾 `-en`、中国語は `-zh`。形はマーケットの `public/src-mark.js`・`functions/_lib/signup_src.ts` と同じ（英数と `_-`・64字まで・最初の印を上書きしない） | マーケットの登録の `dealroom2_users.signup_src` |
| 送客の数 | GA4 `market_click`（from_path・src_mark・placement＝header/card/hero/body/end/footer（card＝トップの案件カード）・link_path・legacy_event・legacy_target）。前からの各頁の `dr2_promo_click`・`dr2_register_click` は内訳として残し legacy_* に写す＝**マーケットへの送客は market_click だけで数える（足さない）** | GA4 のイベント |
| 問い合わせの出所 | `/api/contact` へ送るフォームに隠し欄 `_entry_page`（最初に着いた頁）・`_entry_ref`（その前のサイトのホスト名だけ）・`_prev_page`（直前の頁）・`_src`・`_utm`（sessionStorage・最初の印を優先）。頁の住所は path だけ。受け口 `web-contact.ts` は「_」で始まる欄を断らずに本文から外す＝受け口に記録の行を足すまでは残らない。/fund のフォームは送る中身を手で組むので付かない | 受け口を直したあとの通知メール・記録 |
| 社内の閲覧 | 一度 `https://www.scix.co.jp/?internal=1` を開いた端末は GA4 の利用者の印 `internal_user=1`（`?internal=0` で外す・localStorage）。gtag.js が header.js より先に読まれた頁では、その頁の最初の page_view に印が乗らないことがある。2026-11-22 から、各頁の head の GA の区画（`scripts/build_ga_tag.py`）が同じ鍵を読み、印のある端末だけ config に `traffic_type: internal` を付ける（最初の page_view から乗る） | GA4 のデータフィルタ「内部トラフィック」（有効にすると外れる）・`collect_daily.py --exclude-internal` |
| 導線の押下 | `<a data-cta="<置き場>" data-cta-target="<行き先の名>">` を押すと `cta_click`（placement・target・src_mark・from_path・link_path）。押した頁の道は from_path で送る（`page_path` は gtag が予約語として外し、g/collect に届かない＝2026-11-22 実測。market_click は前からの page_path も残すが届くのは from_path だけ。頁の住所そのものは dl＝page_location で届く）。target が無ければ行き先から market／contact／sell_form／site-<頁>。onclick で cta_click を送る前からのリンクには足さない。マーケットへのリンクは market_click も1回出る（送客は market_click で数える） | GA4 のイベント |

GA4 の管理画面（カスタム定義）で登録が要る物（代表）: ユーザー スコープ `internal_user`／イベント スコープ `src_mark`・`placement`・`legacy_target`。`internal_user` を登録するまで、`collect_daily.py --exclude-internal` は外さずに数えてログに出す（既定は今のまま外さない）。

## GA の区画と、数える側の機械らしい群（2026-11-22）

- **区画**: 全 html の `<head>` の gtag は `scripts/build_ga_tag.py` の1つの形（手で直さない・頁を足したら回す・`--check` でずれを見る・`audit_pages.py --strict` が止める）。住所が `www.scix.co.jp` 以外（localhost・127.0.0.1・プレビュー・file:）と、`navigator.webdriver` が真のブラウザは `ga-disable-G-SNNK8MP9N9` で送らない。社内の印のある端末だけ `traffic_type: internal`。
- **注意**: `--headless=new` でリモートデバッグを付けただけの Chrome は `navigator.webdriver` が偽のまま（2026-11-22 実測）。本番の住所を headless で開く確かめは、`--enable-automation` を付けるか、GA4 の送り先を `--host-resolver-rules` で手元に向ける。
- **収集**: `collect_daily.py` は GA4 のどの表も `hostName=www.scix.co.jp` だけで取る（外した住所の数は台帳の `hosts`）。取り方を変える前の日を取り直すときは `--days 90 --ga4-refresh-all --no-gsc --no-health`。主に見る数は engagedSessions。台帳の `mix`（国×経路×画面×着地）から、着地なし・画面 1280x1200／800x600・日本以外の Direct／Unassigned を機械らしい群として別枠に数える（`common.bot_reason`・本体の数からは引かない）。`ai` はチャネル AI Assistant か参照元が AI の名前（`common.AI_SOURCE_RX`）。
- **ブリーフ**: 1 節にエンゲージのあるセッション（主に見る数）、5e に題の直しを見る語（表示100以上・同じ順位帯の語の CTR 中央値の半分未満・20位まで）、13 節に人らしい来訪と機械らしい群・国×経路・AI 経由。数字は Drive のブリーフにだけ出す。

## トップの案件カードと上の帯の並び（2026-11-22）

トップ3頁（`/`・`/en`・`/zh`）の最初の節は、蓄電所マーケットの案件のカードの一覧（`<section class="hero x-top hero-market" id="market">`。class の先頭は hero のまま＝`guard_diff.py` の「ヒーローより上は変えない」の範囲が、カードの節の終わりまでになる）。

- **焼いた行（土台）**: `scripts/inject_stats.py` が毎朝 `projects.json`（公開項目だけ）から、`<!--S:cards-->` の中に匿名の行12件（新着順・県・電圧・規模・渡し方・連系の見込み）を言葉ごと（日・英・中）に焼く。案件名・市区町村・写真・価格はこのリポジトリに置かない（O16-19）。行のリンクはマーケットの案件ごとの公開の頁（`/catalog/<id>`・英語と中国語は `/en/catalog/<id>`）。
- **画面の差し替え**: `/site-cards.js`（コードだけ）が `https://dealroom.scix.co.jp/api/open/cards?limit=12&lang=<ja|en>` を読み（3秒で打ち切り・Cookie なし）、読めたときだけ同じ場所を写真つきのカードに差し替える。読めない（マーケット停止・CORS が閉じている・遅い・形が違う）ときは何もしない＝焼いた行のまま。中国語の頁は英語のカードを中国語の字の枠で出す。カードのリンクの出所の印は `src=top-card`（英語 `-en`・中国語 `-zh`）・GA4 の `market_click` の placement は `card`（`header.js` の 7a・7b）。
- **確かめ**: 手元は `python3 -m http.server 3847`。CORS は scix.co.jp の2つの住所だけなので、手元ではカードは焼いた行のまま出る（落ちたときの形の確かめを兼ねる）。マーケットの口が読める形は、`/site-cards.js` のマーケットの住所だけを手元の見本に替えて確かめる。`python3 scripts/seo/audit_pages.py` がトップ3頁の並び（最初の節・カード・価格の語が無いこと・`/site-cards.js`）を見る。
- **戻し方**: マージの commit を `git revert`（`chore(seo-log):` は revert しない）。マーケット側の口だけを止めたいときは、マーケットの CORS を外せばよい（トップは焼いた行で残る）。
- **出す順番（マーケットが先・この順を変えない）**: （①②は 2026-11-22 に済んだ＝マーケットの口と入口は本番に出ていて、手元で本番の口につないで確かめた。残りは③以降）①マーケットの口と入口（枝 open-list）を本番へ出す → ②本番を curl で確かめる（`/api/open/cards?limit=12` が200で JSON・scix.co.jp の2つの Origin だけに `Access-Control-Allow-Origin`・`/needs` と `/en/needs` がログイン画面を挟まず売りたいの入口に着く・ログイン前の `/deal?id=` が登録の画面へ・`/?voltage=high-voltage` の絞りが一覧で効く）→ ③この PR をマージ（確かめる前に出すと、口が閉じている間は写真が無く、英語の Sell・中国語の 出售 がログイン画面に着く）→ ④マージの直後に Drive の変更台帳へ記帳する: `python3 scripts/seo/record_changes.py --source structure --manifest <トップの変更の控え changes.json> --brief ~/マイドライブ/9_システム/scix-web解析/weekly/<日付>/brief.json --commit <マージの SHA>`（class は top-order と nav・check_days は 14 と 28。記帳するまで、第1日曜の構成レビューと週次がトップ3頁を触れる）→ ⑤`docs/seo-change-log.md` の確認日を、公開日から数えた14日後・28日後に書き直す → ⑥画面で /en と /zh の Sell・出售・「買主のリクエストを見る」の行き先を確かめる → ⑦sitemap の更新日・IndexNow（`python3 scripts/ping_indexnow.py / /en /zh`）・GSC の URL 検査（3つ）。

上の帯（`header.js` の `var nav`）は蓄電所マーケットの帯（`public/platform-nav.js`）と同じ並び・同じ札の言葉。2つのリポジトリで片方を直したらもう片方も手で写す（実行時に相手のサイトから定義を読む形は、片方が落ちると帯が欠けるので採らない）。

| 札 | scix.co.jp（日本語） | マーケット |
|---|---|---|
| 買いたい | 札＝マーケットの `/`・▾＝/transfer・/fund | `/` |
| 売りたい | 札＝マーケットの売りたいの入口（今は `/needs`）・▾＝/sell-form・/sourcing・/partners | `/needs`（今の sell） |
| ナレッジ | 引き出しのみ（/knowledge ほか今のまま） | `https://www.scix.co.jp/knowledge` |
| 市場リサーチ | 引き出しのみ（/report・/report/data・/market-data） | `https://www.scix.co.jp/report` |
| 会社案内 | /company | `https://www.scix.co.jp/company` |
| お問い合わせ | /contact | `https://www.scix.co.jp/contact` |
| ログイン・無料で登録 | `https://dealroom.scix.co.jp/login`・`/register` | 右端 |

英語は Buy（マーケットの `/en`）・Sell（`/en/needs`）・Knowledge・Market Research（/en/report・/en/report/data）・Company・Contact｜Log in・Sign up（マーケットの英語の頁）。中国語は 购买・出售（どちらもマーケットの英語の頁）・洞见・市场研究（英文）・公司介绍（英文）・联系我们｜登录・免费注册。
