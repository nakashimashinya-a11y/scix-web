# AI の答えに当社が出るかを測る（問い16個・週1回）

2026-11-23 新設。ChatGPT・Perplexity・Google の AI の答え・Copilot・Gemini・Claude に、買い手・売り手・調べる人が訊きそうな問いをそのまま訊き、答えに scix.co.jp と蓄電所マーケット（dealroom.scix.co.jp）が出るか・どの頁が引かれるかを週1回控える。

- **この紙は頁を変えない。** 決めるのは「何を・どこに・どう訊いて・何を控えるか」だけ。測った結果を見て頁を直すのは別の回（同じ頁を14日以内に2度変えない＝`CLAUDE.md` の O16-37）。
- **測った数と答えの写しは、この公開リポジトリに書かない。** 控えは Drive `9_システム/scix-web解析/ai-answers/` に置く（下の「控える物」）。
- Google 検索の AI概要を月1回14語で見る表（`docs/seo-change-log.md` の「AI概要スポット」）とは別。こちらは AI の対話の答えを週1回見る。
- 台本は作らない（手で訊く）。AI の答えは同じ問いでも回ごとに揺れるので、1回の有る無しで頁を直さず、4週の並びで見る。

## 問い（日本語8・英語8）

「出てほしい頁」は、答えに引かれてほしい当社の頁（`docs/keyword-page-map.md` の正の頁にそろえた）。問いの字は毎週同じにし、言い換えない。

### 日本語

| # | 問い（この字のまま訊く） | 出てほしい頁 |
|---|---|---|
| J1 | 日本の系統用蓄電池の売り案件はどこで探せますか？ | dealroom:/・www:/projects |
| J2 | 系統用蓄電池の案件（権利渡し・完成渡し）を買いたいです。どこに相談すればよいですか？ | www:/transfer・dealroom:/ |
| J3 | 系統用蓄電池の案件を売りたいです。買い手はどうやって探せばよいですか？ | www:/sourcing・www:/sell-form |
| J4 | 系統用蓄電所の売買価格の相場はいくらですか？ | www:/column-project-price・www:/guide-buy-sell |
| J5 | 系統用蓄電池の売り案件は、電力会社の管内ごとにどれくらいありますか？ | www:/market-data |
| J6 | 需給調整市場の一次調整力の最近の約定価格はいくらですか？ | www:/report・www:/column-bidding-ceiling-market |
| J7 | 系統用蓄電池の権利渡しと完成渡しの違いは何ですか？ | www:/transfer・www:/column-buyer-structures |
| J8 | 接続検討回答書は、買う前にどこを見ればよいですか？ | www:/column-study-reply |

### English

| # | Question (ask exactly as written) | Pages we want cited |
|---|---|---|
| E1 | Where can I find grid-scale battery storage (BESS) projects for sale in Japan? | dealroom:/en・www:/en/projects |
| E2 | Japan BESS projects for sale | www:/en/market-data・dealroom:/en |
| E3 | How can a foreign investor buy a battery storage project in Japan? | www:/en/guide-buy-sell・www:/en/primer |
| E4 | How many battery storage projects are for sale in Japan, by grid area? | www:/en/market-data |
| E5 | What are the latest balancing market (EPRX) prices in Japan? | www:/en/report |
| E6 | How do the capacity market and the LDA work for battery storage in Japan? | www:/en/guide-capacity-lda |
| E7 | How does battery storage earn money in Japan (JEPX, balancing and capacity markets)? | www:/en/guide-revenue-cost |
| E8 | What is the difference between buying grid rights and buying a completed battery storage plant in Japan? | www:/en/guide-buy-sell |

## 測り方（週1回・月曜の朝）

**訊く先**（6つ・毎週同じ）

| AI | 訊き方 |
|---|---|
| ChatGPT | 検索を入れた状態・新しい会話・記憶（メモリ）を切る |
| Perplexity | 既定の検索・新しいスレッド・ログインしない |
| Google の AI の答え | 日本語は `hl=ja&gl=jp&pws=0`、英語は `hl=en&gl=us&pws=0` の検索で AI概要（出なければ AI モード） |
| Microsoft Copilot | 新しい会話（引用は Bing の索引から＝IndexNow の効きが出る先） |
| Gemini | 新しい会話・アプリの履歴を使わない |
| Claude | Web 検索を入れた状態・新しい会話 |

**決まり**

- 1つの問いに1つの新しい会話。続けて訊かない・言い換えない・当社の名前を出さない（名前を出すと測りにならない）。
- 日本語の問いは日本語の画面、英語の問いは英語の画面で訊く。
- 当社の社内の端末・ログインの履歴の付いた画面は避け、別のブラウザの人格（または私用でない窓）で訊く。
- 1回に 16問×6先＝96 の答え。時間が無い週は、J1・J2・J3・J5・E1・E2・E3・E4（買う・売る・市場データ）の8問を先に。

## 控える物

置き場: Drive `9_システム/scix-web解析/ai-answers/YYYY-MM-DD.jsonl`（1行＝1つの答え）。画面の写しは同じ日付のフォルダに。

| 欄 | 中身 |
|---|---|
| `date`・`ai`・`q` | 訊いた日・訊いた先・問いの番号（J1〜E8） |
| `named` | 答えの本文に ScienceX／サイエンスエックス／蓄電所マーケット／Chikudensho Market の名前が出たか（true/false） |
| `cited` | 答えの出典に出た当社の住所（www・dealroom の両方。無ければ空） |
| `cited_rank` | 当社の住所が出典の何番目か（無ければ null） |
| `target_hit` | 「出てほしい頁」が出典に出たか |
| `wrong` | 当社の頁の数字・事実と食い違う答え（あれば、どの頁のどの字と違うかを一言） |
| `others` | 出典に出たほかの住所の **ドメインだけ** |
| `shot` | 画面の写しのファイル名 |

**週に見る数**（Drive の控えから数える・この紙には書かない）

- 先ごとの「出典に当社が出た問い」の数（16問のうち）と、その4週の並び。
- `target_hit` が false で当社のほかの頁が引かれている問い → その問いの言葉を受ける頁の表（`docs/keyword-page-map.md`）を見直す候補。
- `wrong` が出た問い → 当社の頁の説明・要点の枠・構造化データの直しの候補（14日の間隔を守って別の回に）。
- あわせて見る物: GA4 の AI からの参照（`scripts/seo/common.py` の `AI_SOURCE_RX` で拾う流入）と、Bing Webmaster Tools の AI Performance（Copilot の引用・基準値は Drive `scix-web解析/bing/2026-10-18_ai-performance.md`）。
