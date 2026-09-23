# CLAUDE.md — scix-web

> scix-web（scix.co.jp のコーポレートサイト・静的 HTML・Vercel で公開・**公開リポジトリ**）で作業する Claude Code が読む。サイトの中身と編集・公開の規則、公開案件一覧と DR2 登録の手順を置く。
> 公開リポジトリに置いてはいけないものは共通ルール（`~/.claude/CLAUDE.md`、写しは Drive `9_システム/_共通ルール.md`）の O16-19 が正本。安全の線引きなので、このファイルの「編集と公開」にも同じ中身を置く（O01-28）。
> 重み: **★★★ 必須**／**★★ 原則**／**★ 参考**。**手順**は「どうやるか」。行末の番号で指して直す。

## サイトの中身

**★★★ 必須**

- サイトに事実・数字を作らず、手数料の率、売買の手付率・日数・価格レンジ、IRR・利回りを新たに書かない。数字は既存ページか公表資料（官公庁・OCCTO・JEPX 等）から出典つきで転記する `O16-8`
- 問い合わせへの自動返信と、NDA 前の資料の自動送付・NDA 雛形の自動添付は作らない `O16-9`
- /fund は案内と取次ぎに留め、出資の勧誘・申込受付を書かない `O16-14`
- /grid-storage に案件固有の数値（IRR・分配・案件リスト・スキーム図）を置かない `O16-16`
- 資産運用会社（AM）を私募取扱いの登録業者と書かない `O16-17`
- サイトにファンドの IRR・募集額・1口金額・組入案件名を出さず、AM の社名は出さずに「投資顧問会社」と書く。 `O16-66`

**★★ 原則**

- サイト改善の目的は検索のヒットと問い合わせを増やすこと。迷ったら問い合わせにつながるほうを先にする `O16-4`
- 読者は 買い手 ≧ 投資家 ＞ 売り手・地主 の順に優先する `O16-5`
- 買い手の入口は NDA 不要の /projects にする（NDA を求める CTA を第一ボタンにしない） `O16-6`
- 立場は「案件を仕入れて、売る会社」で全ページ揃え、「中立」「neutral」「independent」を自称せず、「メーカー・EPCと資本関係がない」と事実で書く `O16-10`
- LDA（長期脱炭素電源オークション）落札案件の売却・名義変更は、記事も導線も主題の提案も作らない（対象外と書く1文は除く） `O16-13`
- /fund を noindex にも sitemap 除外にもせず、提案もしない（中島さんが明示で決める） `O16-15`
- コラムから /fund へ導線を張らない `O16-67`
- サイトの文章は AI の紋切り調にしない。既存コラム2〜3本を読み、です・ます＋短い断言・場面から入る声に合わせる `O16-54`

**★ 参考**

- /investors は残し（301 しない）、zh.html の収益モデルの数字は触らない `O16-11`
- 買い手・投資家が主題のコラムは3言語で出し、日本の制度・税務・土地の実務の話は JA 専用にする。英語・中文のページには証券化（GK-TK）を載せない `O16-53`
  - JA 専用は `header.js` の `JA_ONLY_COLUMNS` に登録し、sitemap は hreflang ja 1本。JA 先行で出して後から EN/ZH を足したら `JA_ONLY_COLUMNS` から外す
- 一度やめた施策（gBizINFO への登録・Microsoft Clarity の導入）は再提案しない `O16-59`

## 編集と公開

**★★★ 必須**

- scix-web（公開リポジトリ）には、案件は都道府県・匿名の公開セーフ項目（生成器の `PUBLIC_KEYS`）までしか置かず、住所・地番・緯度経度・価格類（仕入値・販売価格・工事費負担金・土地代・価格の決め方）・関係者（売主・仲介者・担当者）の名前と連絡先・社内メモ・買い手情報・電力会社の秘密資料とその抜粋・認証情報を置かない。コード・テスト・コミット文・PR には DR2 の実文言・案件ID・金額も写さない。実データは Drive（DR2）か非公開リポジトリに置く `O16-19`
**★★ 原則**

- ログイン・DB・API・添付が要る機能は scix-web に作らず、DR2 か cockpit に置く `O17-33`

**★ 参考**

- 作業セッションで直した scix-web は main へ直接 push せず、PR を出してマージまで通し、反映の可否を毎回訊かない（O02-5） `O17-30`
- ナビの組み替えは、手の変更も含めて90日に1回までにする `O16-26`

**手順**

- ビルド工程を持ち込まず、素の HTML を直接直す（`.html` 拡張子は `vercel.json` の `cleanUrls` で省略される）
- リダイレクトは日本語URLも含めて `vercel.json` の規則に書く
- ローカル確認は `python3 -m http.server 3847`。詳細は `docs/new-mac-setup.md`。
- ヘッダーは header.js の共通部品を使い、各ページに直書きしない `O16-55`
- ナビは上段に項目を増やさず既存の引き出しに入れ（ファンドは「買う」の中）、ラベルは行き先の title・h1 と揃える `O16-27`
- 画像はリポジトリの img/ に置き、外部サイト（Wix など）に直リンクしない `O16-56`
- 手で既存ページを変えたら sitemap の lastmod を直し、変更台帳に記帳し、公開後に検索エンジンへ通知する `O16-57`
  - sitemap の lastmod は変更したページだけ手で更新する
  - 通知は `python3 scripts/ping_indexnow.py /path1 /path2`（Bing 等。Google は GSC の URL 検査から手動で）
  - 記帳のしかたは `docs/seo-automation.md`（公開の変更日台帳は `docs/seo-change-log.md`）
  - PR で足した新規ページは翌朝、変更台帳に自動で載る（`scripts/seo/register_new_pages.py`＝手で記帳しなくてよい）

## 週次の自動更新と変更の間隔

仕組み・止め方・戻し方は `docs/seo-automation.md`。台帳は Drive `9_システム/scix-web解析/`。

**★★ 原則**

- 自動更新は新しいページを作らない（新コラム・既存コラムの EN/ZH 版・収益ページも） `O16-3`
- 自動更新は週1回、構成の見直しは月1回にし、頻度を上げない `O16-24`
- 自動更新と構成の見直しは、検査を通れば承認なしで公開する。ナビ（header.js）を含む回だけ PR に出す `O16-25`

**手順**

- 同じページを14日以内に2度変えない `O16-37`
- 「今週触らないページ」は週次も人も触らない（ハブのカード追加と sitemap は除く） `O16-38`
- 自動のコミットは `auto(seo):`（週次）と `auto(structure):`（構成）。差し戻しはそのコミットを `git revert` し、すぐ上の `chore(seo-log):`（sitemap の lastmod と変更日台帳の記帳）は revert しない

## 公開案件一覧（projects.json）

**★★★ 必須**

- 公開サイトの案件一覧には公開セーフ項目（生成器の `PUBLIC_KEYS`＝下の手順の一覧。都道府県レベル・匿名）だけを出し、名称・住所（地番）・緯度経度・価格・売主・社内メモは出さない `O07-20`

**手順**

- 公開サイトの案件一覧（projects.json）はDR2からの自動生成に任せ、手で追記しない `O07-46`
  - 生成は `scripts/build_projects_json.py`、同期（再生成→変化があれば main へ直接 commit/push）は `scripts/sync_projects_json.sh`。ふだんは毎朝 launchd が回す
  - 生成器は DR2（D1 `dealroom2_new_projects` ＋ `deal_edits`）から公開セーフな項目だけを書き出す: id / area / pref / voltage / mw / mwh / status / scheme ／ 連系の見込み（cod・codYm・leadMonths・leadBasis・live）／ firstSeen・updatedAt。項目を足すときは `PUBLIC_KEYS`（生成器）・`.github/workflows/projects-freshness.yml` の allowed・この一覧の3か所をそろえる
  - 同期は案件の出入りだけでなく項目の変更も公開する
  - トップの件数は `scripts/inject_stats.py` が同時に焼き直す（`index.html`・`projects.html` の `<!--S:…-->` マーカーの中。手で直さない）
- 連系の見込みは DR2 の運転開始予定日と月数から作り、connectionDate（回答日）は使わない `O16-21`
- DR2 の自由記述（運転開始予定・負担金の欄）はサイトにそのまま出さず、年月・整数・列挙値だけにする `O16-20`
- 公開項目や連系見込みの文言を変えるときは、対になる箇所（生成器と検査・静的一覧と JS）を同時に直す `O16-23`
  - 生成器（`scripts/build_projects_json.py`）の `PUBLIC_KEYS` と `.github/workflows/projects-freshness.yml` の allowed、静的一覧の `scripts/inject_stats.py` と `projects.html` の JS

## DR2 登録（案件データはこのリポジトリに無い）

DR2 登録の規則の正本は Drive `マイドライブ/5_共有Drive/_DealRoom2/_DR2登録ルール (1).md`（書類番号の表もここ）。

DR2 の置き場は3か所ある。混同しない（同じ名前のフォルダが `_DealRoom2` と `1_案件` の両方にあるのは正常）。

| 呼び名 | 場所 | 用途 |
|---|---|---|
| 案件フォルダ（棚） | Drive `マイドライブ/5_共有Drive/_DealRoom2/{ID}_{案件名}/` | 「DR2登録して」と言われたらここ。案件ごとの買い手向け資料フォルダ |
| 作業フォルダ | Drive `マイドライブ/1_案件/{案件ID}_{案件名}/` | 受領直後の生資料・必要書類チェックリスト・買い手想定質問 |
| DR2 アプリ（コード） | Drive `マイドライブ/9_システム/1AI営業支援/scix/scix-dealroom2/` | Cloudflare Pages ＋ D1（新規案件のレコードは D1）。既存案件の正本は `data/projects-source.json`。`projects-end.json` は transform の生成物なので手で直さない `O17-35` |

**手順**

- 「DR2に届かない・見つからない」と言う前に、Drive の `_DealRoom2` を検索し、`1_案件` の作業フォルダも検索する（「登録できない」と言う前も同じ）。このリポジトリやコードのローカルパス・D1 だけを見て到達できないと結論しない（Drive はコネクタ〔MCP〕で読み書きできる。クラウド実行でも同じで、Mac に限られるのは D1 への書き込みだけ） `O07-8`
- 「DR2登録して」と言われたら:
  1. まず Drive を検索して既存を確認する（`_DealRoom2` の棚と `1_案件` の作業フォルダの両方。`fullText contains 'HV-xxx'` / `title contains '<地名>'`）。**案件フォルダが既にあれば作り直さない。** 差分だけ埋める `O07-9`
  2. 手で採番せず `~/.openclaw/workspace/bin/dr2_register.py add` を使えば `MAX(no)+1` を自動採番し、重複ガード・販売価格の自動計算・undo付きジャーナルまで面倒を見る（価格ルールの中身はこの公開リポジトリに書かない。スクリプトの docstring を見ること）。採番の線引き:
     - D1 `SELECT MAX(no) FROM dealroom2_new_projects` と `_DealRoom2/` 直下のフォルダ名の最大値、**両方を見て大きい方 ＋1**。どちらか片方だけを見ると既存IDを踏む（D1レコードだけ先に作られ、Driveフォルダが未作成の案件がある）
     - 公開 `projects.json` の最大IDを採番根拠にしない（非公開案件が除外されており実態より小さい）
     - 旧 dealroom1（GitHub `nakashimashinya-a11y/scix-dealroom`・private）は現行台帳ではない。採番の根拠に使わない
     - 接頭辞は 高圧=`HV-`／特別高圧=`SHV-`。`_DealRoom2` 直下に作る案件フォルダの名前は `{ID}_{案件名}`（例 `HV-###_○○市△△町蓄電所`）
  3. 資料を `_DealRoom2` の案件フォルダの次の標準サブフォルダに振り分ける（`1_案件` の作業フォルダの仕分けとは別）。物件概要書は案件フォルダ直下に置く。

     | フォルダ | 入れるもの |
     |---|---|
     | `A_土地・現地` | 地番一覧・敷地平面図・公図・位置図・現地写真・登記簿 |
     | `B_系統連系` | 契約申込回答書・検討結果説明書・添付資料1〜6・連系承諾のご案内・工事概要図 |
     | `C_関係法令` | 都市計画法／農地法／森林法／盛土規制法などの照会回答 |
     | `D_設備・計画` | システム構成図・レイアウト図・機器仕様書・認証書 |
     | `99_確認中` | 区分が決まらないもの |

     棚に置くファイルの名前には書類番号を必ず頭に付け、`{番号}_{案件短縮名}_{内容}.拡張子`（例 `A-3_○○_土地全部事項証明書.pdf`）にする。番号の頭文字は置くサブフォルダと合わせ、合わない書類は先に正しいサブフォルダへ移す。**番号が無いと DR2 アプリの必要書類チェックが永久に付かない**（日本語だけの名前は何個置いてもゼロ件と出る）。番号表は正本の「4. 書類番号」（共通ルール O07-19）。

  4. 公開まで通す — `bash ~/マイドライブ/9_システム/1AI営業支援/scix/scix-dealroom2/scripts/dr2_publish.sh`（毎朝 launchd が自動実行するので急がなければ不要。git push では反映されない）
  5. 作業フォルダ（`マイドライブ/1_案件/{案件ID}_{案件名}/`）の `_必要書類チェックリスト.md` を更新する（✅/⚠️/⬜/➖ の判定を最新化）。
  6. DR2 アプリの案件一覧に載せる（Drive フォルダを作っただけでは出ない）。「DR2登録」は ①案件フォルダ（Drive）と ②案件レコード（DR2アプリ）の2段構え。**①だけで終わらせない** `O07-11`
     - 新規案件のレコードは D1 `dealroom2_new_projects` に入れる。`data/projects-source.json` は既存案件用で、新規をここに書いても増えない
     - 仕入れ値と既存案件の手直し（インライン編集）も D1 側に入れる（既存案件への上書きは `deal_edits`）。再デプロイは要らない。既存案件の表示を直すときは 1AI営業支援/scix/scix-dealroom2/CLAUDE.md の O17-34 に従う
     - `dr2_register.py add`（上の2）を使わないときの投入経路は2つだけ: owner 画面の「+ 新規案件」か、SQL を生成して wrangler で流す（`scix-dealroom2/` 直下で `npx wrangler d1 execute scix-dealroom-db --remote --file=dr2-<ID>-insert.sql`。`scripts/04_update_d1_drivefolderurl.py` と同じ流儀）。無人（フック・cron・エージェント）で流すときは `npx wrangler` でなくラッパー wr（`~/.config/scix-cockpit/wr d1 execute …`）を通す（共通ルール O17-7）
     - `dealroom2_new_projects` が受け付ける列は限られる（`functions/api/admin/projects.ts` の `ALLOWED`）: `id` / `no` / `name` / `address` / `lat` / `lng` / `voltage` / `mw` / `capacity` / `maxPower` / `gridOperator` / `saleType` / `status` / `landType` / `landArea` / `connectionDate` / `operationStartDate` / `price`。数値として入れるのは `lat` / `lng` / `mw` / `capacity` / `maxPower`（と採番の整数 `no`）だけで、残りは `price` も含めて文字列（SQL を生成して渡すときも同じ）。**書く前に `ALLOWED` を見る。** これ以外（`seller`・`constructionCost`・`constructionNote`・`driveFolderUrl`・機器仕様など）は `deal_edits` に UPSERT、社内メモは `memos` テーブルに入れる
     - `deal_edits` はホワイトリスト制。`functions/api/projects.ts` の `OVERLAY_STRING_FIELDS` / `OVERLAY_NUMERIC_FIELDS` に無いフィールド名で入れてもエラーにならず画面に出ないだけ（行はDBに残るので気づけない）。**書く前に必ずこの2配列を見る**（蓄電池は `battery` ではなく `equipmentBattery`、PCSは `equipmentPcs`） `O17-12`
     - **D1への書き込みはMacからしかできない。** クラウド実行環境（Claude Code on the web 等）では拒否される＝迂回しない・報告する。その場合は**適用できるSQLを生成して渡す**。「できません」で終わらせない `O07-35`
     - 生成したSQLは `scix-dealroom2/` 直下（`~/マイドライブ/9_システム/1AI営業支援/scix/scix-dealroom2/`＝Drive経由でMacに同期される場所）に `dr2-<ID>-insert.sql` として置く。作業フォルダにも同じものを残しておく
  7. `driveFolderUrl` に `_DealRoom2` の案件フォルダURLを入れて紐付ける（`1_案件` の作業フォルダは指さない）。
     - 緯度経度が資料に無い案件は `deal_edits` の `showMap` を `'off'` にする（`'off'` のときだけ非表示。`false`・`true` を入れても変わらない）。非公開（`dealroom2Visible` を `'off'`）にするのは共通ルール O07-2 の3つの場合だけ
