# CLAUDE.md — scix-web

ScienceX コーポレートサイト（静的HTML・ビルド工程なし・Vercel デプロイ）。
ローカル確認は `python3 -m http.server 3847`。詳細は `docs/new-mac-setup.md`。

---

## ⚠️ 最重要 — 案件データ（DealRoom2 / DR2）はこのリポジトリに無い

**このリポジトリの中だけを見て「DR2 に到達できない」と結論してはいけない。**
DR2 は **Google Drive** にある。Drive コネクタ（MCP）から普通に読み書きできる。
「登録できない」と言う前に、**必ず Drive を検索すること。**

過去の失敗例（2026-08-30）: `scripts/build_projects_json.py` に書かれた Mac ローカルパスと
Cloudflare D1 だけを見て「DR2 はこのセッションから到達不能」と誤答した。
実際には Drive に案件フォルダがあり、対象案件は既に登録済みだった。

### DR2 の実体（3か所ある。混同しない）

| 呼び名 | 場所 | 用途 |
|---|---|---|
| **DR2（案件フォルダ）** | Google Drive `マイドライブ/5_共有Drive/_DealRoom2/` | **「DR2登録して」と言われたらここ。** 案件ごとの資料フォルダ |
| 作業フォルダ | Google Drive `1_案件/{案件ID}_{案件名}/` | 受領直後の生資料・必要書類チェックリスト・買い手想定質問 |
| DR2 アプリ（コード） | Google Drive `マイドライブ/書類GD/1AI営業支援/scix/scix-dealroom2/` | Cloudflare Pages + D1。`data/projects-source.json` が canonical、`projects-end.json` は transform 生成 |

補足:
- 新規案件の追加・仕入れ値・インライン編集は **D1**（`dealroom2_new_projects` / `deal_edits`）側。再デプロイ不要。
- 旧 dealroom1 = GitHub `nakashimashinya-a11y/scix-dealroom`（private）。**最終同期 2026-05-20・最大 no=200 で止まっており、現行台帳ではない。** 採番の根拠に使わない。

### 「DR2登録して」の手順

1. **まず Drive を検索して既存を確認する**
   - `fullText contains 'HV-xxx'` / `title contains '<地名>'`
   - **案件フォルダが既にあれば作り直さない。** 差分だけ埋める。
2. **案件IDを採番する**
   - `_DealRoom2/` 直下の既存フォルダ名の最大値 ＋1。接頭辞は 高圧=`HV-` / 特別高圧=`SHV-`。
   - フォルダ名は `{ID}_{案件名}`（例 `HV-###_○○市△△町蓄電所`）。
   - **公開 `projects.json` の最大IDを採番根拠にしない**（非公開案件が除外されており実態より小さい）。
3. **標準サブフォルダに資料を振り分ける**

   | フォルダ | 入れるもの |
   |---|---|
   | `A_土地・現地` | 地番一覧・敷地平面図・公図・位置図・現地写真・登記簿 |
   | `B_系統連系` | 契約申込回答書・検討結果説明書・添付資料1〜6・連系承諾のご案内・工事概要図 |
   | `C_関係法令` | 都市計画法／農地法／森林法／盛土規制法などの照会回答 |
   | `D_設備・計画` | システム構成図・レイアウト図・機器仕様書・認証書 |
   | `99_確認中` | 区分が決まらないもの |

   物件概要書は案件フォルダ直下に置く。
4. **ファイル名は中身が分かる日本語に整える**
   （例 `地番一覧（筆数・地積入り）.pdf` / `契約申込みに対する回答書_YYYY-MM-DD.pdf`）
5. 作業フォルダ側の `_必要書類チェックリスト.md` を更新する（✅/⚠️/⬜/➖ の判定を最新化）。
6. **DR2 アプリの案件一覧に載せる（Drive フォルダを作っただけでは出ない）**
   - 「DR2登録」は **①案件フォルダ（Drive）** と **②案件レコード（DR2アプリ）** の2段構え。①だけで終わらせない。
   - 新規案件のレコードは **D1 `dealroom2_new_projects`** に入れる。
     `data/projects-source.json` は既存案件用で、新規をここに書いても増えない。
   - 投入経路は2つ。**owner 画面の「+ 新規案件」**、または **SQLを生成して wrangler で流す**:
     ```
     npx wrangler d1 execute scix-dealroom-db --remote --file=dr2-<ID>-insert.sql
     ```
     後者は `scripts/04_update_d1_drivefolderurl.py` と同じ流儀（SQL生成 → wrangler 適用）。
   - **`dealroom2_new_projects` が受け付ける列は限られる**（`functions/api/admin/projects.ts` の `ALLOWED`）:
     `id` / `no` / `name` / `address` / `lat` / `lng` / `voltage` / `mw` / `capacity` / `maxPower` /
     `gridOperator` / `saleType` / `status` / `landType` / `landArea` / `connectionDate` /
     `operationStartDate` / `price`。
     **これ以外**（`seller`・`constructionCost`・`constructionNote`・`driveFolderUrl`・機器仕様など）は
     `deal_edits` に UPSERT、社内メモは `memos` テーブルに入れる。
   - `driveFolderUrl` に ① の案件フォルダURLを入れて紐付ける。
   - 緯度経度が資料に無い案件は `showMap: false`、非公開にするなら `dealroom2Visible: false`。
   - **D1への書き込みはMacからしかできない。** クラウド実行環境（Claude Code on the web 等）は
     Cloudflare 認証が無いうえ、egress ポリシーで `api.cloudflare.com` への接続自体が
     403 で拒否される（迂回しない・報告する）。
     その場合は**適用できるSQLを生成して渡す**こと。「できません」で終わらせない。
   - 生成したSQLは **`scix-dealroom2/` 直下**（Drive経由でMacに同期される場所）に
     `dr2-<ID>-insert.sql` として置く。リポジトリ直下に置けば上のコマンドがそのまま通り、
     受け取る側はパスを考えなくてよい。作業フォルダにも同じものを残しておく。

### 公開サイトへの反映は別工程

公開案件一覧 `projects.json` は **DR2 からの自動生成物**。手で追記しない。
`scripts/build_projects_json.py` が DR2（`projects-end.json` ＋ D1）から公開セーフな
9項目（id / area / pref / voltage / mw / mwh / cod / status / scheme）だけを書き出す。

---

## ⚠️ このリポジトリは public — 機密を絶対にコミットしない

`nakashimashinya-a11y/scix-web` は **公開リポジトリ**。以下は絶対に置かない:

- 住所・地番・緯度経度
- 販売価格・仕入れ価格・工事費負担金・土地代
- 売主／仲介者名・担当者名・連絡先
- 社内メモ・買い手情報
- 電力会社の「秘密情報」表記のある資料（契約申込回答書・検討結果説明書など）およびその抜粋

案件の実データは Drive（DR2）か private リポジトリに置く。
公開してよいのは `projects.json` の公開セーフ9項目まで（＝都道府県レベル・匿名）。

---

## サイト編集の約束事

- ビルド工程なし。素の HTML を直接編集する。`.html` 拡張子は `vercel.json` の `cleanUrls` で省略される。
- 日本語URLのリダイレクトも `vercel.json` 側のルール。
- 3言語（JA / EN `en/` / ZH `zh-*.html`）。コラムを足すときは 3言語そろえるのが既定。
- ヘッダーは `header.js` で共通化。各ページに直書きしない。
- ページを更新したら `sitemap.xml` の `lastmod` を更新し、必要なら `python3 tools/indexnow_submit.py <URL>`。
- GA4 測定ID・秘密情報はコミットしない。
