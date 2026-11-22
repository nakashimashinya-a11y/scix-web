# 言葉と受ける頁の表（1語1頁）

2026-11-23 新設。買う・売る・投資の意図の言葉を、どの頁が受けるかを束ごとに1つ決めた表。コラム末尾の入口・頁の題と説明・内部リンクを直すとき（凍結明けの 2026-12-07 以後）の向き先の正本で、毎週の週報（`scripts/seo/market_side.py` の 12f）がこの表に照らして束ごとの表示・順位・割れを出す。

- **この表は頁を変えない。** 決めるのは「どの言葉をどの頁に受けさせるか」だけ。頁の題・本文・導線を直すのは別の回（同じ頁を14日以内に2度変えない＝`CLAUDE.md` O16-37）
- 書くのは言葉と住所だけ。案件の ID・価格・住所・関係者名・DR2 の文は書かない（O16-19）。数字は Search Console の表示・クリック・順位だけ（`docs/seo-automation.md` の「数字の置き場」）
- 機械版は `scripts/seo/keyword_page_map.json`。表を変えるときは両方を同じ変更で直し、`python3 scripts/seo/selftest_keyword_map.py` を通す（正の頁が実在するか・表と機械版の束がそろっているかを見る）

## 読み方

- **束**: 同じ意図の言葉のまとまり。1つの検索語は、機械版の並びの順に最初に当たった1つの束だけに入る
- **正**: その束の言葉を受ける頁。1束に1つ（管区の束は管区ごとに1つ）
- **副**: 同じ言葉で出てよい頁（調べる記事・申込の頁など）。割れに数えない
- **決め待ち**: dealroom 側の同じ役目の頁。どちらを正にするかを 2026-12-20 に決めるので、それまで割れに数えない
- **割れ**: 正・副・決め待ちの外の頁が、同じ束の語に出ていること。直す対象
- **旧住所**: 301 で移した古い住所（`vercel.json`）。検索結果に古い題が残る間の表示を、割れと分けて数える
- 住所は `www:`（scix.co.jp）と `dealroom:`（dealroom.scix.co.jp）の2つ。`*` は前方一致

## 表（日本語）

実測は Search Console の 2026-08-23〜11-20（90日）。語は匿名の語を落とすので、見えているのは表示のうちの一部だけ（表示0は「語として見えていない」）。

### 買う

| 束（機械版の id） | 言葉の例 | 正 | 副（出てよい頁） | 90日の実際（束の表示・クリック・順位／出ている頁） | 割れと直す向き |
|---|---|---|---|---|---|
| 売り案件の一覧・物件（`buy-list`） | 系統用蓄電池 案件／売り案件／物件／販売中／一覧／買いたい | www:/projects | www:/projects-<管区>・www:/column-buyer-structures | 40・1・37.0／/projects 17・/ 6・/fund 4・/knowledge 4 | /・/fund・/knowledge・/investors が「案件」の語に出ている。トップは社名の頁なので題は触らない。/knowledge・/investors・/fund の説明で「案件を探す」を言う文は、/projects へ渡す1行に寄せる |
| <管区>の売り案件（`area-tokyo` ほか9） | 東京・中部・関西・九州・東北・中国・北海道・北陸・四国 ＋ 案件／売り案件 | www:/projects-tokyo・-chubu・-kansai・-kyushu・-tohoku・-chugoku（北海道・北陸・四国は noindex のため dealroom:/catalog/area/<管区>） | www:/projects | 東京 21・中部 5・関西 10・九州 1（すべて www /projects-<管区> が受けている・dealroom は表示0） | www /projects-<管区> と dealroom /catalog/area/<管区> は同じ件数で題が違う。**どちらを正にするかは 2026-12-20**（下の節） |
| 特別高圧の売り案件（`volt-ehv`） | 特別高圧／特高 ＋ 案件／売却／買い | dealroom:/catalog/voltage/extra-high-voltage | www:/projects・www:/transfer | 0（語として見えていない） | www に特別高圧だけの頁は無いので、マーケットの電圧の頁を受け口にする。dealroom の索引が進んでから表示を見る |
| 高圧の売り案件（`volt-hv`） | 高圧 ＋ 案件／売却／買い | dealroom:/catalog/voltage/high-voltage | www:/projects・www:/transfer | 0 | 同上 |
| 権利渡し・完成渡し・開発権（`buy-types`） | 権利渡し／完成渡し／開発権／権利 売買／権利 譲渡 | www:/transfer | www:/column-buyer-structures・www:/column-transfer・www:/column-four-labels・www:/guide-buy-sell | 0 | 取得の形を言う語は /transfer が受ける（題に「権利譲渡・完成渡し・特別高圧」） |
| 買い方・売り方・価格の相場（`price-howto`） | 蓄電所 価格 相場／いくら／買い方／売り方／売買 流れ | www:/guide-buy-sell | www:/column-project-price・www:/column-trading・www:/column-buyer-structures | 1・0・21.0／/column-construction-cost | 調べる語を、買う・売るの入口の頁（柱）で受ける。系統用の「価格 相場」は検索結果に専用の頁が出ない型で、空いている |

### 売る

| 束 | 言葉の例 | 正 | 副 | 90日の実際 | 割れと直す向き |
|---|---|---|---|---|---|
| 案件・権利の売却・売買・仲介（`sell-project`） | 系統用蓄電池 売買／売却／売りたい／買取／仲介／権利 譲渡（用地・土地だけの語は下の `land`） | www:/sourcing | www:/sell-form・www:/guide-buy-sell・www:/column-trading・www:/column-transfer | 277・3・14.0／/sourcing 152・/land 50（旧）・/column-land-buyback 49・/investors 12 | 「系統用蓄電池 買取」に記事（/column-land-buyback）が並んで出る。売る人は /sourcing へ渡す。売買・仲介の語が /sourcing に集まっているので、買う人には /sourcing から /projects へ渡す |
| 売却査定（`sell-form`） | 査定／売却査定 ＋ 蓄電 | www:/sell-form | www:/sourcing | 0 | 申込の口は /sell-form の1つだけ（O16-43）。解説の頁は主ボタンを /sell-form へ向ける |
| 用地・土地・蓄電池の買取（相場）（`land`） | 蓄電池用地 買取／土地 買取／買取相場（「系統用」「蓄電所」「案件」「権利」の付く語は `sell-project`） | www:/column-land-buyback | www:/column-land-lease・www:/column-land-value・www:/column-land-zoning・www:/sourcing | 1,257・83・6.7／/column-land-buyback 875・/land 159（旧）・/column-land-value 84・/column-land-zoning 75 | 当社は土地だけの買取・査定をしない（O16-5）。新しい頁は作らず、買取相場の解説の記事で受け、売る人へは記事の末尾から /sourcing（「回答が出た案件の売却」）へ渡す。旧住所 /land に表示が残っている |

### 投資

| 束 | 言葉の例 | 正 | 副 | 90日の実際 | 割れと直す向き |
|---|---|---|---|---|---|
| 蓄電池ファンド（`fund`） | ファンド／投資信託／出資／GK-TK ＋ 蓄電池 | www:/fund | なし | 631・32・8.6／/fund 571・/investors 60 | /fund（案内と取次ぎ＝O16-14）と /investors が同じ語を分け合っている。ファンドの語は /fund、投資の語は /investors に分ける |
| 蓄電池への投資（`invest`） | 投資／個人投資 ＋ 蓄電池（税制・利回りの語は除く） | www:/investors | www:/column-financing・www:/column-buyer-structures・www:/qa・www:/grid-storage | 251・3・28.0／/investors 115・/fund 86・/grid-storage 14・/knowledge 12 | /fund が「投資」の語に86出ている（割れ）。/fund は noindex にも sitemap 除外にもしない（O16-15） |

### 名前・マーケット

| 束 | 言葉の例 | 正 | 副 | 90日の実際 | 割れと直す向き |
|---|---|---|---|---|---|
| 社名（`brand`） | サイエンスエックス／ScienceX | www:/ | www:/company・www:/en・www:/en/company・www:/zh・www:/zh-company | 2,358・394・7.2／/ 532・/company 517・/partners 257・/grid-storage 244 | 社名に別の語が付いた検索が /partners・/grid-storage などに出る。社名の語はトップが受ける（トップの題は凍結中・中島さんの決め） |
| 蓄電所マーケット（`market-name`） | 蓄電所マーケット／蓄電所市場 | dealroom:/ | dealroom:/how・dealroom:/needs・dealroom:/en | 0 | www の / は社名の頁なので、この語では出さない。マーケットの索引が進んでから表示を見る |

## 表（英語・中国語）

| 束 | 言葉の例 | 正 | 副 | 90日の実際 | 割れと直す向き |
|---|---|---|---|---|---|
| 英語・売り案件・取得（`en-list`） | japan bess for sale／projects／marketplace／acquisition／development rights | www:/en/projects | www:/en・www:/en/column-buyer-structures | 0 | dealroom /en と www /en/projects が同じ「BESS projects for sale in Japan」を言う。決め待ち（2026-12-20） |
| 英語・買い方売り方（`en-howto`） | how to sell／buy a bess project | www:/en/guide-buy-sell | www:/en/column-trading・www:/en/column-transfer・www:/en/column-buyer-structures | 3・0・63.7／/en/market-entry-guide 3 | 売る・買うのやり方の語は /en/guide-buy-sell へ（今は /en/market-entry-guide に出ている） |
| 英語・日本の市場を調べる（`en-market`） | japan battery storage market／investment／entry | www:/en/market-entry-guide | www:/en/knowledge・www:/en/column-revenue・www:/en/primer・www:/en/market-data・www:/en/qa | 702・1・47.9／/en/column-revenue 586・/en/market-entry-guide 85 | 調べる語。買う・売るへは記事と市場データの末尾の入口で渡す（12/07 以後） |
| 中国語（`zh-list`） | 储能 項目／买卖／出售／收购、电网侧 项目 | www:/zh | www:/zh-guide-buy-sell・www:/zh-qa・www:/zh-knowledge | 2 | 語として見える表示がほぼ無い。中国語の売買の頁は /zh と /zh-guide-buy-sell の2つ |

## 2026-12-20 に決めること

- **地域の一覧の重なり**: www /projects-<管区>（6本）と dealroom /catalog/area/<管区>（9本・日英）は、同じ件数で題が違う。同じ組が東京・中部・関西・中国・東北・九州にある。dealroom は 2026-11-22 に sitemap を出したばかりで、索引に入った頁が約4割・検索の表示がほぼ0（2026-11-23 時点）。**今は題も canonical も変えない**。2026-12-20（sitemap 提出から4週）に、週報 12f の管区の束の表示（www と dealroom のどちらが取ったか）で、正をどちらにするか・住所を1つにするかを決める
- **売り案件の一覧**: www /projects と dealroom の / も同じ中身（件数が一致）。決め待ちに置いてあり、同じ日に決める
- この2つの決めが出るまでは、dealroom 側の題・canonical を替えない（索引のやり直しになる）

## 旧住所

`vercel.json` で恒久の 301 にした旧住所（例: /land → /sourcing、/bss → /transfer、/sell → /sourcing）は、検索結果に古い題が残る間、表示が付く。週報 12f は「旧住所」の列に分けて数える。表示が続く旧住所は、移し先の頁の題と説明が旧い題の言葉を引き継いでいるかを確かめる（頁の直しは別の回）。

## 週報での見方（12f）

毎週のブリーフ（`weekly/<日付>/brief.md`）の 12f が、直近28日で束ごとに次を出す。

- 表示・クリック・順位（束の語に出た全部の頁の合計）
- 正の頁の表示の割合
- 割れた語／束の語の数・割れの頁（表示の多い順に3つ）・旧住所に残る表示・前28日の表示
- 表示0の束（束の名前だけ1行）
- **表に入らない買う・売るの語**（どの束にも当たらなかった語の上位8）。出たら、束の語（機械版の `any`）に足すか、束を足す

12/20 の決めと、12/07 以後のコラム末尾の入口の作り直し（柱1・選ぶ頁1・地域が分かれば市場リサーチ1）は、この表の「正」を向き先にする。記事 → 一覧への流れは `market_click` と `?src=col-<記事>`（11/21 から計測）が2週間たまってから見る。

## 直し方

1. 束・正・副を変えるときは `scripts/seo/keyword_page_map.json` とこの表を同じ変更で直す（束の `id` は表の見出しの括弧と同じ）
2. 住所は実在する頁だけ（`selftest_keyword_map.py` が www の頁の実在を見る）。dealroom の住所は実在を機械で見ないので、マーケットの公開の頁の一覧（sitemap）で確かめる
3. 並びを変えると、同じ語が別の束に入る。変える前後で `python3 scripts/seo/selftest_keyword_map.py` を通し、週報の 12f の割れが急に動かないかを見る
