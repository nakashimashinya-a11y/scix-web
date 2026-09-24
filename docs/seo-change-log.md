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
| 2026-09-22 | /column-jcstar | title「JC-STAR★1の義務化はいつから — 蓄電池は接続契約申込みが基準」・description 130字（IPA登録345件・2026年9月）。「決まったこと／まだ決まっていないこと」「JC-STAR適合製品の現状」を2026-09-22時点に（ガイドラインは令和6年12月1日版のまま未公布・IPA 9/15版345件・起点は契約申込みの受付＝指針第88条）。JSON-LD description は据え置き（PR#84）。診断: 28日の減少は順位落ちが主（jc-star 蓄電池 4.8→6.9位・着地が levels へ）＝title だけでは戻らない | #95 | 3か月（06-22〜09-18）表示20,282・クリック663・CTR3.3%・5.8位／28日（08-22〜09-18）表示4,498・クリック92・CTR2.0%・6.2位（前28日 152クリック）。「jc-star 義務化」3か月 285表示・14クリック・5.8位（28日 82・2・6.3位）／「jc-star 蓄電池」3か月 604・27・3.6位（28日 30・0・6.9位）／「jcstar 蓄電池」3か月 148・8・4.2位（28日 41・2・5.3位） | マージ+14日／+28日 | KPI: 3語の順位とクリック、ページのクリックが28日で120以上に戻るか。裸の「jcstar」の CTR は KPI にしない |
| 2026-09-22 | /column-lda | title「長期脱炭素電源オークション（LDA）とは — 蓄電池の落札率と第3回の結果」・description 118字を meta/og/twitter/JSON-LD で同文に（旧 og・twitter・JSON-LD は「徹底解説」入りの58字）。h2「第3回（2025年度応札）の結果 — 2026年5月13日公表」を追加（OCCTO 約定結果: 蓄電池19件・1,251MW・落札率46%。第1・2回との比較のみ） | #95 | 3か月（06-22〜09-18）表示5,326・クリック77・CTR1.4%・6.2位／28日 表示1,743・クリック21・6.8位。「長期脱炭素電源オークションとは」3か月 39表示・0クリック・19.5位（28日 36・0・20.3位）／「ldaとは」49・0・8.6位／「lda」3か月 222・0・8.0位（KPI外） | マージ+14日／+28日 | KPI: 「長期脱炭素電源オークションとは」「長期脱炭素電源オークション 蓄電池」の順位（20位台→10位以内）とクリック（0→）。「lda」は KPI にしない |
| 2026-09-20 | /en/column-construction-cost /en/column-price-cap /en/column-investment-tax | 表示ゼロ・被リンクの少ない EN 新規3ページへ、主題の近い EN コラム4本から本文中のリンクを1〜2本ずつ足した（自動・internal-link。根拠: ブリーフ8節の要手当て /en/column-construction-cost（公開39日・28日表示0・EN内の被リンク1本＝ハブのみ）と /en/column-price-cap（公開33日・28日表示0）、10節の旗つき /en/column-investment-tax（公開20日・表示187・クリック0・被リンク1本）。リンク元はいずれも9節の凍結外で、建設費→キャッシュフロー・補助金、上限価格→収益・キャッシュフロー、即時償却→税制と主題が直接つながる） | auto 2026-09-20 #1 | /en/column-construction-cost 表示なし／/en/column-price-cap 表示なし／/en/column-investment-tax クリック0・表示187・CTR0.0%・10.3位 | 2026-10-04 / 2026-10-18 | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: GSC の /en/column-construction-cost・/en/column-price-cap の表示（14日後・28日後に0から動くか）と /en/column-investment-tax のクリック |
| 2026-09-20 | /en/column-revenue | title・description を検索語の言い回し「revenue stacking」に合わせた（自動・title。根拠: 28日で「batterij revenue stack」146表示・クリック0・18.5位、「battery storage revenue stacking」43表示・クリック0・31.5位が当たっているのに、title は「3 Battery Revenue Sources」で stacking という語を含んでいなかった） | auto 2026-09-20 #2 | /en/column-revenue クリック8・表示1592・CTR0.5%・14.3位 | 2026-10-04 / 2026-10-18 | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: GSC /en/column-revenue の CTR と「revenue stacking」系の語のクリック（2週後・4週後）、GA4 の着地→generate_lead |
| 2026-09-20 | /en/column-cashflow | title・description を検索語の言い回し「battery storage project IRR」に合わせた（自動・title。根拠: 28日で「battery storage project irr comparison」90表示・クリック0・18.7位がこのページに当たっているが、title は「Battery Business 20-Year Cash Flow」で storage も project も入っていなかった） | auto 2026-09-20 #3 | /en/column-cashflow クリック2・表示237・CTR0.8%・12.0位 | 2026-10-04 / 2026-10-18 | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: GSC /en/column-cashflow の CTR と「battery storage project irr」系の語のクリック（2週後・4週後） |
| 2026-09-20 | /en/column-balancing-market | title・description に battery を入れ、検索語「balancing market battery」を受けた（自動・title。根拠: 28日で表示317・クリック3・CTR0.9%・6.1位（4-10位帯の中央値2.1%の半分未満）。「balancing market battery」44表示・クリック0・10.7位。title は「Japan's Balancing Market — 5 Products & Composite Bidding」で battery を含んでいなかった） | auto 2026-09-20 #4 | /en/column-balancing-market クリック3・表示317・CTR0.9%・6.1位 | 2026-10-04 / 2026-10-18 | 台帳 `9_システム/scix-web解析/ledger` が自動計測。KPI: GSC /en/column-balancing-market の CTR（2週後・4週後）と「balancing market battery」のクリック |
| 2026-09-17 | 更新メール登録（`header.js` 注入・`knowledge.html`／`index.html` の置き場・`privacy.html`・`scripts/newsletter_draft.py`）＋ DR2 `/api/newsletter` | **「週1本の更新をメールで受け取る」**（中島「つくって。入力はなるべく簡単に」）。入力はメールアドレスだけ（お名前は任意）。JAページのみ: ハブ（立場別の下・書き手の上）、トップのナレッジ帯、全コラムの末尾（関連記事の下・フッターの上）。受け口は scix-dealroom2 の `/api/newsletter`（D1 `newsletter_subscribers`・中島宛通知・本人への自動返信なし）。翌朝 07:20 の `blastmail_sync.py` がブラストメールへ登録（解除者は入れない・scix.co.jp 宛は除外）。配信は従来どおりブラストメールから「全登録者」宛＝本文の下書きは `python3 scripts/newsletter_draft.py`。GA4 `newsletter_signup`（placement=column/top/knowledge-top/knowledge-bottom） | #87 | コラム着地の83%が離脱・受け皿ゼロ（GA4 経路 09-17） | 2026-10-15 | GA4 `newsletter_signup` の件数と placement 別、D1 の登録数、ブラストメール登録者の増分。placement 別で置き場を減らすか判断 |
| 2026-09-17 | ヘッダー（`header.js`）・トップ（`index.html`）・ナレッジハブ（`knowledge.html`）・コラム48本のパンくず・`company.html`・sitemap | **ナレッジを目玉に据え直す**。①ナビの先頭を「ナレッジ▾」（2列: テーマで読む=全記事／収益・市場／税制・制度・規制／売買の実務／土地・用地／技術・安全・運用、はじめての方=入門Q&A／そもそも連載／しくみ）にし「学ぶ▾」を廃止（買う▾／売る▾／会社案内／お問い合わせ／金ボタンは据え置き）。②トップのヒーロー直下にナレッジ帯（新着3・よく読まれている5・立場別入口4）。③ハブを再設計: 検索窓（`?q=`・GA4 `knowledge_search`）、立場別「まず読む4本」×3（各々 /projects・/sourcing・/land・/investors へ）、新着／定番、カテゴリ見出しを h2 化＋導入文、書き手ブロック、CTAを /contact 1本→案件一覧＋売る・土地・投資の4方向。「準備中（SMR・e-fuel）」の空箱は撤去。title「系統用蓄電池のナレッジ｜制度・市場・税制・用地・売買の解説 全67記事」。④コラム48本の可視パンくず・BreadcrumbList にカテゴリ層（/knowledge#cat-…）を追加（そもそも連載19本は連載パンくずのまま）。⑤WebSite に SearchAction。⑥sitemap は `/`・`/knowledge` の lastmod のみ（⚠️コラム54本と company.html はパンくず・id だけの変更＝lastmod を触っていない。`sync_sitemap_lastmod.py --write` を次の本文更新より前に走らせると 54本が 09-17 に化けるので走らせない）。⑦言語切替を地球アイコン＋枠付きピル（現在の言語は白地）に、スマホはドロワー最上段へ（中島「地味すぎてわからない」） | #86 | GA4 90日（06-18〜09-15）: `/knowledge` は表示回数2,354で全ページ2位・1人4.2回、着地670セッション（222人＝1人3回・新規118＝リピーターの入口）、KE 2。経路（28日）: トップ606→次は /knowledge 103・/company 91・/projects 64；/column-jcstar 374→/knowledge 13が1位で /projects は上位5に無し。GSC 90日 `/knowledge`: クリック23・表示1,786・CTR1.3%・10.4位（ブランド語以外ほぼ無し）。リード内訳は Drive `9_システム/scix-web改造提案_20260904/SEO計測基準値_20260905.md` 側（公開リポジトリには書かない） | 2026-10-01 / 2026-12-16 | 10-01: GA4 nav_click の nav_group=knowledge の比率、`/knowledge` の表示回数と「/knowledge→/projects・/sourcing・/land・/investors」の遷移が増えたか（経路データ探索・始点 /knowledge）、`knowledge_search` の語。12-16: GSC で `/knowledge` のブランド以外の表示・順位、「系統用蓄電池」「需給調整市場」「容量市場 蓄電池 収益」の順位。※#85 の nav_group 値 learn は knowledge に変わった（10-01 の比較は 09-17 以降の knowledge を learn 相当として読む） |
| 2026-09-17 | ヘッダー（全ページ共通 `header.js`）・トップ見出し1箇所 | ナビを16の行き先→「買う▾／売る▾／学ぶ▾／会社案内／お問い合わせ／金ボタン」に再編。ホームはロゴへ、言語切替はナビ内の小さな文字へ、スマホは折りたたみ3つ、境界1060→900px。静的な内部リンク（フッター）は不変。トップの見出し「買う以外のご用件」→「1棟を買う以外のご用件」、sitemap は `/` の lastmod のみ更新 | #85 | `/` クリック449・表示1,376・CTR32.6%・3.4位。ヘッダーのクリック計測は無かった（GA4 `nav_click`／`nav_open` を今回から収集。カスタムディメンション nav_group / open_by / link_text / link_url / page_lang を09-17登録） | 2026-10-01 | GA4 で nav_group 別のクリック分布（値は buy／sell／learn／top／cta／lang／logo、nav_open は drawer も。open_by は hover／click／keyboard）と、`/projects` `/contact` への遷移が増えたかを見る。検索面は「/」の CTR・順位が下がっていないこと |
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
| 2026-09-17 | URL 送信 | `/` を手動送信（ヘッダー再編 #85。IndexNow でも `/`＋日本語88本を送信済み） |
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
| 2026-09-17 | / | リクエスト済み（#86 公開後の再リクエスト。トースト確認） |
| 2026-09-17 | /knowledge | リクエスト済み（ナレッジ再設計 #86。「URL は Google に登録されています」→再リクエスト、トースト「インデックス登録をリクエスト済み」を確認） |
| 2026-09-17 | / | リクエスト済み（ヘッダー再編 #85。ライブテストは「URL は Google に登録できます」、Googlebot（スマートフォン）のレンダリング結果に新ヘッダーを確認） |
| 2026-09-05 | /projects /transfer /sourcing /fund /column-financing /knowledge | リクエスト済み（いずれも登録済みページの再クロール依頼） |
| 2026-09-05 | /column-subsidies | リクエスト済み。06-10 クロール以降「クロール済み・インデックス未登録」だった。P2 で壊れた JS 文字列を直したので、登録されるかを 2026-09-19 に確認 |
| 2026-09-05 | /column-trading | リクエスト済み（新設・Google 未認識だった。サイトマップの再読込も待ち） |
| 2026-09-05 | /en/column-trading・/zh-column-trading | リクエスト済み（新設・Google 未認識）。IndexNow も送信済み（/column-trading /en/knowledge /zh-knowledge /zh を含む） |

IndexNow（Bing 等）は `python3 scripts/ping_indexnow.py /path…` で送る。 09-17（#86 公開後）送信済み: `/`・`/knowledge`・`/company`・コラム54本（カテゴリパンくずを足した48本＋深掘り子6本）＝57 URL・HTTP 200。09-17 送信済み: `/` と日本語ページ88本（ヘッダー再編 #85 でレンダリング後のナビ文言が変わったページ。EN/ZH は不変なので送っていない）。いずれも HTTP 200。09-05 送信済み: /projects /transfer /sourcing /fund /grid-storage /knowledge /investors /partners /column-trading ほか変更ページ。
