# SEO 変更日台帳（docs/seo-change-log.md）

検索向けに title・description・CTA・構造を変えた日と、変更前の基準値を残す台帳。
**目的は「2週間後に GSC で CTR・順位を比べ、下がった title は戻す」こと。** 効果の主張は書かない。

- 基準値の出典: GSC（sc-domain:scix.co.jp）検索パフォーマンス 2026-06-03〜09-02 の3か月（順位は表示加重平均）。
  「28日」と書いたものは GA4 p532483329 の 2026-08-08〜09-04。
- 確認のしかた: GSC → 検索結果 → ページで絞る → 期間「過去28日」を「前の期間と比較」。順位は日次でぶれるので CTR を主に見る。
- リード数（generate_lead の intent 別）はこの公開リポジトリに書かない。基準値は Drive `9_システム/scix-web改造提案_20260904/` に置く。
- AI概要のスポットは月1回、同じ14語を Chrome（`hl=ja gl=jp pws=0`）で見て下の表に列を足す。

## 変更（新しいものを上に）

| 変更日 | ページ | 変更 | PR | 変更前の基準（GSC 3か月） | 確認日 | 結果 |
|---|---|---|---|---|---|---|
| 2026-09-06 | meta description 34ページ | Bing 指摘「description が短い」を実測で検証して範囲を確定。**JA 17・ZH 8 は自サイトの中央値（122/120字）より短かったので 118〜134字へ**。**EN 9 は逆に長すぎた（最長740字）ので 144〜155字へ**（サイト規約 英meta≤155字）。日本語を英語基準で水増しはしない。og/twitter も同文だったものは追随、JSON-LD Article の長い description は AI 検索の材料なので据置。検証で既存説明文の**事実誤り3件**も判明し訂正（land-value の5基準／options の3択／grid-rules で上限額を示す主体） | #84 | JA min 81→108・ZH min 88→105・EN max 740→155 | 2026-09-19 | |
| 2026-09-06 | 英語ページ 40本の title | Bing 指摘「title が70文字超（高）」に対応。EN 47本のうち71〜164字だった40本を70字以内に（主題語を前半に・h1/description/本文は不変・og:title/twitter:title/JSON-LD headline が title と同文だったものだけ追随）。/en の og:title の「Science X Inc.」も title に揃えた | #83 | Bing 3か月: EN ページの表示は少数（上位25語に EN 語なし）。Google: EN 64クリック/3か月 | 2026-10-05 | |
| 2026-09-05 | /sourcing（本文増補）・「中立」の自称を除去（JA/EN/ZH 28ファイル） | /sourcing の本文を約1,000字→約3,300字（何を仕入れるか・出口2つ・最初に見る書類・順番・止まる型・用意するもの。title/description/h1 は不変）。サイト全体で当社を「中立」「neutral」「independent」と呼ぶ文を「メーカー・EPCと資本関係がない」「仕入れて売る側」の事実表現に置換（判断⑥） | #82 | 「系統用蓄電所 物件 売りたい」45表示・21.2位（/land 33・/sourcing 10）／「系統用蓄電池 買取」61表示・16.0位（/sourcing 31）／「系統用蓄電池 売買 仲介」19表示・29.9位 | 2026-09-19 / 2026-10-05 | |
| 2026-09-05 | /en/column-trading・/zh-column-trading（COLUMN 46 の EN/ZH）・/zh FAQ | COLUMN 46 を3言語に（JA_ONLY 解除・hreflang 3本・sitemap・索引カード EN/ZH）。zh トップ FAQ「海外の外国人も買えるか」に外為法の1文 | #80 | 「蓄電所 売買」EN/ZH 語は GSC で表示なし（EN 64クリック/3か月・投資家ページ着地 0） | 2026-10-05 | |
| 2026-09-05 | 制度コラム12本（aggregator-fee / area-data / auction / balancing-market / biz / capacity-market / day-ahead / eprx / lda / merchant / nonfirm / revenue） | 末尾CTAブロック内のリンクを3本→2本（主 /projects・副 /investors。説明文中のフォームリンクを外し PR#46 の確定形に戻す） | #79 | 28日: 上位4コラム＋/knowledge 1,646セッションでキーイベント0 | 2026-09-19 | |
| 2026-09-05 | /column-trading（COLUMN 46 新設・JA先行） | 「蓄電所の売買はどう進むか」約4,200字 | #78 | 「蓄電所 売買」scix 圏外・AI概要あり（09-05 SERP） | 2026-10-05 | |
| 2026-09-05 | 制度コラム12本 | CTA 主 /contact→/projects・副 /grid-storage→/investors（h3 は記事ごと） | #77 | 同上（28日 KE0）。内部被リンク /projects 13→25・/investors 2→14 | 2026-09-19 | |
| 2026-09-05 | /column-eprx | title を「EPRXとは」に分割 | #77 | 「eprx」表示4,114・クリック15・CTR0.4%・5.5位（/column-eprx 774/9・/column-area-data 2,123/4・/column-balancing-market 1,458/1＝3本で票割れ） | 2026-09-19 | |
| 2026-09-05 | /column-balancing-market | title を「需給調整市場とは」に、定義文と h2「一次調整力とは」を追加、eprx／area-data と相互リンク | #77 | 「需給調整市場」表示230・17.8位（本ページ166）／「一次調整力」表示193・10.4位／「需給調整市場 複合商品」表示111・クリック38・CTR34.2%・1.8位 | 2026-09-19 | |
| 2026-09-05 | /column-area-data | title を「需給調整市場の取引実績」に、「このデータの引用について」ブロック | #77 | 「需給調整市場 取引実績」表示325・クリック4・CTR1.2%・4.5位 | 2026-09-19 | |
| 2026-09-05 | /investors | title「系統用蓄電池への投資｜法人が1棟で持つ・ファンドで持つ」、本文を約3,300字に増補、監修ブロック、被リンク 2→6ページ | #76 #77 | 「系統用蓄電池 投資」表示46・クリック0・44.3位（当たり先 /fund）／「系統用蓄電所 投資」33・33.2位／「蓄電池 利回り」11・46.5位／「需給調整市場 蓄電池 投資」57・25.5位。/investors の非ブランド表示 1 | 2026-09-19 / 2026-10-05 | |
| 2026-09-05 | /projects | title「系統用蓄電池の案件一覧・物件情報（NDA不要）」、案件127件を静的HTMLに焼き込み（本番HTMLの「県」2→127）、pid付き /contact リンクに nofollow | #76 | 非ブランド表示 4。GSC「代替ページ（適切な canonical タグあり）」55件は /contact?intent=buyer&pid= | 2026-09-19 | |
| 2026-09-05 | /transfer | title「系統用蓄電池の案件を買う｜権利譲渡・完成渡し・特別高圧」、買い方の正本に改稿 | #76 #77 | 非ブランド表示 24。「系統用蓄電池 売買 仲介」で当たるのは /sourcing（19表示・29.9位） | 2026-09-19 | |
| 2026-09-05 | /sourcing | title「系統用蓄電池の案件を売りたい方へ｜売買・買取・仲介」、h1「当社が仕入れるか、買い手につなぎます」 | #76 | 「系統用蓄電池 売買 仲介」19表示・29.9位（09-05 当日SERP 3位）／「系統用蓄電池 買取」61表示・16.0位（/sourcing 31）／「系統用蓄電所 物件 売りたい」45表示・21.2位（/land 33・/sourcing 10） | 2026-09-19 | |
| 2026-09-05 | /fund | description を商社の立場に、「接続申込の 0.3%」 | #76 | 「系統用蓄電池ファンド」表示29・クリック2・9.1位／「系統用蓄電池 ファンド」37・1・8.1位 | 2026-09-19 | |
| 2026-09-05 | /grid-storage・/knowledge | description を商社の立場に、接尾辞「｜ScienceX」統一 | #76 | 「系統用蓄電池」32表示・15.3位（13ページに分散） | 2026-09-19 | |
| 2026-09-05 | /column-tax | title に「一括償却」を追加 | #76 | 「系統用蓄電池 即時償却」表示255・クリック28・CTR11.0%・2.3位／「系統用蓄電池 一括償却」182・16・8.8%・2.6位／「蓄電池 一括償却」182・13・7.1%・5.5位 | 2026-09-19 | |
| 2026-09-05 | /column-buyer-structures | title に「投資案件」「完成渡し」、description から価格レンジを除去 | #76 | 「系統用蓄電池 完成渡し」で当たるのは /qa（6位） | 2026-09-19 | |
| 2026-09-05 | /column-cashflow | description から IRR% を除去 | #76 | 「蓄電池 利回り」表示11・0クリック・46.5位 | 2026-09-19 | |
| 2026-09-05 | 全ページ Organization JSON-LD・/company | @id・legalName・法人番号・sameAs(gBizINFO)・founder 肩書。/company に同一法人の1文と「引用・取材について」 | #77 | 被リンク 外部16件（全部コラムの参考文献型） | 2026-10-05 | |
| 2026-09-05 | 404 の発生源と 301 | column-subsidies の JS 文字列 `'/5）。…'` を全角スラッシュに、vercel.json に 301×21、sitemap `/` に zh-CN、overview.html 削除 | #76 | GSC 404 23URL（旧Wixパス・壊れたURL）・インデックス未登録 101 | 2026-09-19 | |

## KPI の基準値（変更前・2026-09-05）

| 指標 | 基準値 | 90日後の目標 | 出典 |
|---|---|---|---|
| 収益ページの非ブランド表示（3か月） | /transfer 24・/projects 4・/investors 1 | 各50 | GSC |
| 投資判断4語の順位 | 系統用蓄電池 投資 44.3／系統用蓄電所 投資 33.2／蓄電池 利回り 46.5／需給調整市場 蓄電池 投資 25.5（クリック0・表示計147） | 4語とも20位以内 | GSC |
| 本番 /projects の HTML に「県」 | 2 → 127（09-05 達成） | 毎朝の同期が止まらない（`.github/workflows/projects-freshness.yml` が監視） | curl |
| 外部被リンク | 16件・ドメイン少数（参考文献型） | gBizINFO 登録＋引用元3社への更新通知 | GSC リンク |
| インデックス未登録 | 101（代替canonical 55・404 23・クロール済み未登録 8・検出未登録 5・リダイレクト 10） | 404→0・代替canonical は nofollow で自然減 | GSC ページ 08-28 |

## Bing（Bing Webmaster Tools）— 基準値と操作記録

| 日 | 項目 | 値・結果 |
|---|---|---|
| 2026-09-06 | 3か月の検索パフォーマンス（06-05〜09-03） | クリック 1.6K・表示 43.2K・CTR 3.81%。上位語は jc-star／jcstar／eprx 系（表示の大半）、ブランド語（サイエンスエックス・sciencex）約90クリック。買い手・売り手・投資家の語は上位25に無し。日次クリックは6月の30台→8〜9月は20前後に減少 |
| 2026-09-06 | IndexNow | 過去16時間で51 URL 受理・累計1.9K。送信元は自サイトの ping_indexnow.py |
| 2026-09-06 | URL 送信 | 09-05以降に変えた146ページを手動送信（1日の枠10,000） |
| 2026-09-06 | サイトマップ | sitemap.xml を再送信（前回クロール 09-04・153 URL・エラー0）。EN/ZH の column-trading を含む再読込待ち |
| 2026-09-06 | Recommendations | 高: title が70文字超 5ページ（/en /en/column-area-data /en/column-bess-insurance /en/column-equipment /en/market-entry-guide）。実測では EN 47ページ中40が70超（JA/ZH は0）→ EN title を全面的に70字以内へ（別PR）。中: meta description が短い 22ページ（一覧は Recommendations から開けず。サイトスキャンの結果で特定） |
| 2026-09-06 | サイトスキャン結果 | 75ページ・エラー1・警告0。唯一のエラーは `/files/scix-nda-template.docx` が robots.txt でブロック＝**意図どおり**（NDA雛形を検索結果に出さない）。技術的な問題は無し |
| 2026-09-06 | Bing の表示回数の読み方（注意） | 表示 43.2K の大半は eprx 3.5K・jc-star 3.0K・jcstar 1.9K など**他組織の名称を探すナビゲーショナル検索**。順位5〜8位でも CTR 0.37〜0.43%＝探し物が当社ではない。表示の多さを需要と読まない。6月 約900表示/日 → 9月 約450表示/日 に半減しているが、減っているのはこの層。買い手・売り手・投資家の語は Bing でも上位25に無し |
| 2026-09-06 | AI Performance（Copilot 等の引用・3か月） | 引用 14.1K 回・引用ページ 平均13/日。引用を集める問い: jc-star制度（2.3K・シェア11.6%）・jcstar制度 748・eprxとは 712（シェア68%）・電力需給調整力取引所 351（41%）・需給調整市場 複合商品とは 305（45%）・フルマーチャント 189／とは 170（36%）・蓄電所 騒音 124・トーリング契約 106・系統用蓄電所 設置までの流れ 90。買い手・売り手・投資家の問いは上位25に無し＝AI 引用も制度解説に偏る |
| 2026-09-06 | AI Performance 引用ページ（3か月・61ページ） | column-jcstar 5.0K・column-balancing-market 1.8K・column-eprx 1.3K・column-noise 970・column-merchant 601・column-jcstar-levels 590・column-tax 392・column-grid-rules 353・column-area-data 342・column-development 190・column-lda 183・column-long-term-contract 179・column-capacity-market 176。/projects /transfer /investors /sourcing は上位25に無し（column-transfer 66）→ 90日後にここが増えるかを見る |
| 2026-09-06 | サイトスキャン | 「scix-web 2026-09-06」を200ページ上限で開始（キュー登録）。結果で meta description の短いページと他の指摘を確定 |

## AI概要スポット（14語・月1回）

Chrome（Googleログイン済み・`hl=ja&gl=jp&pws=0&num=10`）で見た、scix.co.jp の順位と AI概要の有無。

| # | クエリ | 2026-09-05 順位（該当URL） | AI概要 | 次回 |
|---|---|---|---|---|
| 1 | 系統用蓄電池 投資 | 圏外 | 有 | |
| 2 | 系統用蓄電池 案件 | 圏外 | 有 | |
| 3 | 蓄電所 売買 | 圏外 | 有 | |
| 4 | 系統用蓄電池 売買 仲介 | 3位（/sourcing） | 有 | |
| 5 | 蓄電所 権利譲渡 | 1位（/column-transfer） | 有 | |
| 6 | 系統用蓄電池 利回り | 圏外 | 有 | |
| 7 | 系統用蓄電池 ファンド | 圏外 | 有 | |
| 8 | 蓄電池 即時償却 | 1位（/column-tax） | 有 | |
| 9 | 系統用蓄電池 買取 | 3位（/column-land-buyback） | 有 | |
| 10 | 系統用蓄電池 完成渡し | 6位（/qa） | 有 | |
| 11 | 系統用蓄電池 | 圏外 | 有 | |
| 12 | 蓄電所 投資 事業会社 | 圏外 | 有 | |
| 13 | 特別高圧 蓄電池 案件 | 圏外 | 有 | |
| 14 | 系統用蓄電池 とは | 圏外 | 有 | |

## 手動インデックス登録リクエスト（GSC URL検査）

| 日 | URL | 結果 |
|---|---|---|
| 2026-09-05 | /projects /transfer /sourcing /fund /column-financing /knowledge | リクエスト済み（いずれも登録済みページの再クロール依頼） |
| 2026-09-05 | /column-subsidies | リクエスト済み。06-10 クロール以降「クロール済み・インデックス未登録」だった。P2 で壊れた JS 文字列を直したので、登録されるかを 2026-09-19 に確認 |
| 2026-09-05 | /column-trading | リクエスト済み（新設・Google 未認識だった。サイトマップの再読込も待ち） |
| 2026-09-05 | /en/column-trading・/zh-column-trading | リクエスト済み（新設・Google 未認識）。IndexNow も送信済み（/column-trading /en/knowledge /zh-knowledge /zh を含む） |

IndexNow（Bing 等）は `python3 scripts/ping_indexnow.py /path…` で送る。09-05 送信済み: /projects /transfer /sourcing /fund /grid-storage /knowledge /investors /partners /column-trading ほか変更ページ。
