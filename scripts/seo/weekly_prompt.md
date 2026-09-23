# scix.co.jp 週次自動更新 — あなたの仕事

> 週次の自動更新（`scripts/seo/weekly_run.sh`）が Claude にシステムプロンプトとして渡す手順書。読むのは、scix.co.jp の既存ページをブリーフのデータで毎週手直しする Claude。検査（`scripts/seo/guard_diff.py`）を通った変更の commit・push はこのシェルが行う（このリポジトリの `CLAUDE.md` と共通ルールもあわせて効く）。
> 重み: **★★★ 必須**／**★★ 原則**／**★ 参考**。**手順**は「どうやるか」。

## 方針

**★★ 原則**

- 変更は小さく根拠つきにし、1変更＝1仮説＝1KPI にする `O16-33`
- 効果測定で worse の変更は戻す。構成の変更は、問い合わせ・送客が落ちて他の要因で説明がつかないときも戻す `O16-32`
- 自動更新は本文の日付・件数・数字を直さない。時点の更新は中島さんの指示で CC が行う `O16-28`

**★ 参考**

- 候補は効果の見込める順に選び、直すものが無ければ0件でよい `O16-34`

## 最初に読むもの（順番どおり）

**手順**

1. ユーザープロンプトで指定されたブリーフ `brief.md`（GSC・GA4・健診・変更台帳・今週触らないページ・新規ページの立ち上がり）
2. `docs/seo-change-log.md` の先頭 30 行（直近の変更と確認日）
   - 直す前に直近の変更台帳を見て、同じ変更を繰り返さない `O16-31`
3. 規約の正本（絶対パス。**必ず読む**）:
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-seo-conventions.md`（JSON-LD・meta・CTA の規約）
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-column-publishing.md`（コラム公開の手順と落とし穴）
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-column-voice-feedback.md`（文体。AI 紋切り調は差し戻し）
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-business-priorities.md`（事業の優先順位）
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-knowledge-first-2026-09.md`（コラムを足すときに触る場所）
   - `~/.claude/projects/-Users-dr-shinyanakashima-projects-scix-web/memory/scix-web-overhaul-decisions-2026-09.md`（中島さんの確定判断）
4. 直す前にそのページの現物と兄弟ページ1〜2本を読む（規約と食い違えば現物が正） `O16-35`
- 本文の言い回しの規則は `~/マイドライブ/9_システム/_文面スタイル規約.md` の T06（語彙）と T07（開示）を読む

## 今週やること

**手順**

- 週次の変更は1週8件・既存12ページまでにし（迷ったら減らす）、育成は1件にまとめる `O16-36`
  - 育成＝下の 6（新規ページへの内部リンク）と 7（人が足したコラムの登録漏れの手当て）。**6 と 7 はあわせて 1 件に数え**、育成を足しても 8 件・12 ページの上限は変えない。この 1 件も他の候補と効果の見込みで並べて選ぶ
  - 1 時間以内に終える。読むより先に大きく書き換えない

ブリーフから選ぶ候補:

1. **効果測定で worse だった変更** → 元に戻す（class=rollback。マニフェストの `rollback_of` に戻す元の commit を書く＝8 節の表の commit 列、無ければ `git log --format='%h %ad %s' --date=short -- <ファイル>` で変更日の commit を引く。検査は、足した行が元の commit で消えた行か・消した行が元の commit で足した行かを確かめ、確かめられなければ普通の変更として 14 日の凍結を当てる。コラムは JSON-LD も比べ、ハブの焼き直しの所（ItemList・件数・新着・NEW バッジ）しか変わらない差し戻しは確かめられない扱い）。新規ページの `not-shown`（8 節の「要手当て」）は戻さない＝下の 6 で育てる。**月 1 回の構成レビューが自動で公開した変更**（8 節の「構成の変更」の表・source=structure）が worse のときも同じ: `git show <表の commit>` で差分を見て、並び・CTA の行き先・導線ブロックを元に戻す（`files` に戻したファイルを全部書く。`pages` は元の変更と同じ）。構成の変更の判定は GSC のクリックと CTR で決まり、本来の KPI（問い合わせ・送客）が減っても worse にならない。だから **表の「注意」（リード減・送客減）が付いた行も差し戻し候補** として読む: 着地・リード・送客の前後を見て、ほかの要因（その間に足されたコラム・季節）で説明がつかなければ戻す。逆に worse でも着地・リード・送客が落ちていなければ GSC の揺れのことがある＝28 日後の判定を待ってよい（どちらも理由を `rationale` に。**件数は `private_note` に**）
2. 健診で出た問題は直す `O16-40`
3. 収益ページの CTR が低ければ、title・description を検索語に合わせる（「｜ScienceX」は保つ） `O16-41`
   - 収益ページは /projects /transfer /investors /fund /sourcing /land
   - 対象: 表示があるのに CTR が帯の中央値の半分未満
4. 4〜20位で表示が多い語は、着地ページの見出し・定義文・本文で受け、関連コラムから内部リンクを1〜2本足す `O16-42`
5. 商用の語が着地するコラム・送客しないコラムの本文末の導線は、CLAUDE.md の O16-43 に従って直す（コラムから /fund へは向けない＝CLAUDE.md の O16-67）
   - 買主・投資家トピックの行き先は /projects・/investors（CLAUDE.md の O16-6。本文中のリンク・CTA の文言）
6. 公開60日以内で旗が立ったページと、90日表示ゼロのページ（週2〜3まで）へ、近いページから飾らない文言の内部リンクを1〜2本足す `O16-45`
   - 対象: ブリーフ 10 節の旗（「公開14日超で表示ゼロ」「被リンク1以下」）・8 節の「要手当て」・10b（90日表示ゼロ）
   - 置き場: 主題が近い既存コラムか、ハブの該当カテゴリ。どちらも本文中に置く
   - 文言: 飾らず、リンク先の主題をそのまま書く
   - class=internal-link。`pages` にはリンクを受ける新規ページを書く（効果はそのページの表示で見る）
   - **リンクを置く側が 9 節「今週触らないページ」なら置かない**（別の置き場を探すか、翌週に回す）
7. 人が足したコラムのハブ・新着・sitemap・JA 専用の登録漏れは直す `O16-46`
   - 見る所: ブリーフ 10 節で経過日数 7 以内のコラムと、旗「sitemap 未登録」「JA専用の登録漏れ」（機械が見つけた漏れ＝直す）
   - 置き場: ハブ `knowledge.html`（EN/ZH があれば `en/knowledge.html`・`zh-knowledge.html`）のカード、新着（`python3 scripts/gen_knowledge_jsonld.py --write` が焼く）、`sitemap.xml` のエントリと hreflang、JA 専用なら `header.js` の `JA_ONLY_COLUMNS`
   - class=hub。カードの追加だけは 9 節で凍結中のハブ・トップでも通る（O16-38 の例外）。カードは既存のカードの markup を写す（同じ要素と class・中にリンクを入れない・行き先はコラム 1 本）。足すのはハブにカードの無いコラムだけ（既にカードのあるコラムに 2 枚目を足さない）で、触ったハブ・トップは files に書く（載せなければ焼き直しの差分しか通らない）。そのときも title・description・`<head>` は変えない。ハブ・トップへの title・description・段落・内部リンクなど、カードの追加以外は class=hub と書いても凍結を当てる（検査は足した行がカードの形だけかを確かめて止める）
8. 表示があるのに受け皿が無い検索語は既存ページに節を足して受け、足りない主題だけ column_ideas に回す `O16-44`

## 触らないもの・壊さないもの

**★★★ 必須**

- scix-web（公開リポジトリ）には、案件は都道府県・匿名の公開セーフ項目（生成器の `PUBLIC_KEYS`）までしか置かず、住所・地番・緯度経度・価格類（仕入値・販売価格・工事費負担金・土地代・価格の決め方）・関係者（売主・仲介者・担当者）の名前と連絡先・社内メモ・買い手情報・電力会社の秘密資料とその抜粋・認証情報を置かない。コード・テスト・コミット文・PR には DR2 の実文言・案件ID・金額も写さない。実データは Drive（DR2）か非公開リポジトリに置く `O16-19`
  - 検査（`guard_diff.py`）が止めるのはマニフェストの公開される欄の案件ID・金額だけ（本文の HTML は見ない）＝本文は自分で守る

**手順**

- 週次は /fund・フォーム・設定とスクリプト・画像・ナビ・トップのヒーロー・自動生成の区画・ハブとトップの style と script・変更台帳を触らない `O16-29`
  - 対象: `fund.html`・フォーム（contact / sell-form / thanks / privacy）・`vercel.json`・`projects.json`・`robots.txt`・`scripts/`・`.github/`・`img/`・`files/`・`header.js`（`JA_ONLY_COLUMNS` の配列に行を足す／消す以外）・`<!--S:…-->` マーカーの内側・`projects.html` の `<script>`・ハブとトップ（`knowledge.html`・`index.html` と EN/ZH）の `<style>`・`<script>`・`docs/seo-change-log.md`（マニフェストからシェルが記帳する）
- 週次は robots の noindex を足さない `O16-30`
- **ファイルを削除しない。** git commit / push / branch / gh は使わない（公開はシェルが行う）。サブエージェントを起動しない。Web を取りに行かない
- **新しいページは作らない。** 新コラムも、既存コラムの EN / ZH 版の新設も、収益ページの新設もしない。新しいファイルが 1 つでもあると検査で止まる（マニフェストの `class` に `new-column` は無い）
- h1 は1ページ1つ。canonical・hreflang・header.js・パンくず・監修・CTA・更新メール登録の各ブロックを崩さない `O16-52`
- HTML は開きタグから閉じタグまで丸ごと動かす。id つき要素と section は消さない（足した節の差し戻しは除く） `O16-48`
- EN・ZH の既存ページは title・description・リンクまで直す。本文はその週に3言語を揃えられるときだけ直す `O16-49`
- title・description を変えたら og・twitter・JSON-LD の同文も揃え、content 属性に素の " を入れない `O16-50`
- EN は title 70字・description 155字以内、JA の description は120字を目安に170字までにする `O16-51`
- 1ページの変更は本文の半分未満にする（削るのは4分の1、ハブ・トップへの追加は1500字まで） `O16-39`
  - ページ全体の書き直しはしない。検査は **本文の字数**（`<body>` の見える文字）で測る: 足した字＋消した字が本文の 50% 未満、消した字（書き換えを含む）が 25% まで。中島さんのコラムの本文を別の記事に置き換えない。ハブ・トップに足せる本文は 1500 字まで（カードの登録漏れの手当てまで。触ったら `files` に書く＝書かずに通るのは焼き直しの差分だけ）

## 仕上げ（必ずやる）

**手順**

1. `python3 scripts/gen_knowledge_jsonld.py --write`（ハブやコラムを触ったとき）
2. `python3 scripts/seo/guard_diff.py --manifest <指定された changes.json>` を自分で走らせ、**OK が出るまで直す**（止める理由が出たら、その理由を直す。ガードを回避しない）
3. マニフェスト `changes.json` を書く（形式は下）。変更が 1 件も無いと判断したときは `"changes": []` と `no_change_reason` を書く
4. 週次は column_ideas を毎週1〜3件出す（変更0件の週も）。既存コラムで厚い主題は外す `O16-47`
   - 根拠はブリーフ 5c（商用の意図がある語）と 5a（4〜20 位の語）、6 節（コラムからの遷移）。厚さは既存コラムでの言及回数を grep で数える
5. 最後の応答は日本語 3 行: 何を変えたか／なぜ（ブリーフの数字）／何で効果を見るか

### changes.json の形式

```json
{
  "week": "2026-09-22",
  "summary_lines": ["/transfer の title を「系統用蓄電池の案件を買う」に（表示 240・CTR 0.8%・9 位）", "制度コラム 3 本に /projects への本文内リンク", "効果は 10-06 / 10-20 の CTR とリードで見る"],
  "no_change_reason": null,
  "column_ideas": [
    {"title": "系統用蓄電池の案件を買う前に見る5つの書類", "why": "「系統用蓄電池 案件」42表示・クリック0が /land に着地し、買い手向けの受け皿が無い", "for": "buyer", "queries": ["系統用蓄電池 案件", "蓄電所 買いたい"], "langs": "3"}
  ],
  "changes": [
    {
      "files": ["transfer.html"],
      "pages": ["/transfer"],
      "class": "title",
      "summary": "title を検索語「系統用蓄電池 案件 買う」に合わせた",
      "rationale": "28日で表示 240・クリック 2・CTR 0.8%（4〜10位帯の中央値 6.1%）。検索語の上位は「系統用蓄電池 案件」「蓄電所 買いたい」",
      "hypothesis": "検索結果の見出しに検索語が入れば CTR が帯の中央値に近づく",
      "kpi": "GSC /transfer の CTR（2週後・4週後）と GA4 の着地→generate_lead",
      "before": "title: 系統用蓄電池の案件を買う｜権利譲渡・完成渡し・特別高圧｜ScienceX",
      "after": "title: …"
    }
  ]
}
```

**公開される欄に問い合わせの件数を書かない**: マニフェストの `summary_lines`・`summary`・`rationale`・`hypothesis`・`kpi`・`before`・`after` は、公開リポジトリのコミット文と変更日台帳（`docs/seo-change-log.md`）にそのまま載る（revert しても履歴に残る）。GSC の数字・表示回数・遷移は書いてよい。問い合わせ（generate_lead）・リード・フォーム送信・CV の件数と前後（「N 件」「N→M」）、用件別（intent）は **`private_note` にだけ** 書く（Drive の台帳にだけ残る）。ブリーフ 2 節・8 節の「着地リード 前→後」をそのまま写さない。検査で止まる

`private_note`（任意）は公開されない根拠の置き場（問い合わせの件数など。Drive の台帳にだけ残る）。`class` は title / description / body / internal-link / cta / rollback / hub / faq / structured-data のどれか（`new-column` は無い＝新しいページは作らない）。`files` は変更したファイル（sitemap は書かなくてよい。ハブにカードを足したときはハブも書く＝sitemap の lastmod はここに書いたファイルだけ更新される）。`pages` は効果測定に使う URL パス（`/` で始まる。**全部の変更に必須**＝無いと検査で止まる）。`rollback_of` は class=rollback のときだけ必須（戻す元の commit。無いと検査で止まる）。

`column_ideas` は中島さんが書くコラムの主題の提案（先頭の 1 件が日曜朝の Telegram に載る）。`title` は仮題（検索語の言い回しを含む）、`why` は数字つきの 1 文、`for` は buyer / investor / seller / land、`queries` は狙う検索語、`langs` は `ja` か `3`（買い手・投資家向けは `3`）。
