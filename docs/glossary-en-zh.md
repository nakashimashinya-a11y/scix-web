# 英語・中国語の頁の用語の対応表（docs/glossary-en-zh.md）

英語（`en/`）と中国語（`zh-*.html`・`zh.html`）の頁を訳す・直すときの正。日本語の頁が原文で、訳はその今の版に合わせる。
英語の呼び方は、公的な機関（OCCTO・EPRX・JEPX・経済産業省／資源エネルギー庁・一般送配電事業者の英語の頁）で確かめた物を先にし、確かめられなかった物は「公的な英語名は未確認」と書いた。

## 訳の決まり

1. **日本語に無い主張・助言・会社名・利回り・実績・日付・数を足さない。** 段を足すのは、日本語にあって訳に無い段だけ。
2. **警告を安心の言い方に変えない。** 日本語が「つまずく」「未確定」「座礁資産になりうる」と言う所は、訳でも同じ向きで言う。
3. **数は日本語の表示どおり。** 桁（5,000万円＝¥50 million、数億〜数十億円＝several hundred million to several billion yen、兆＝trillion／万亿）、「未満」と「以下」、「超」と「以上」を取り違えない。
   - 未満 → EN: below / less than ／ ZH: 不足・低于
   - 以下 → EN: or less / or below / up to ／ ZH: 以下
   - 超 → EN: more than / over / exceeding ／ ZH: 超过
   - 以上 → EN: or more / at least ／ ZH: 以上
4. **会社の説明は日本語と同じにする。** 当社は系統用蓄電池の案件の売買を行う会社（売り手からは買い取るか買い手に紹介し、買い手には販売する）で、建設は請け負わず、運用（operate）もしない。買い手に出すのは接続検討の回答が出た案件。言い方は読む人の側から（CLAUDE.md の O16-10）: 買い手には EN: for sale / sell ／ ZH: 在售・销售、売り手には EN: buy / acquire ／ ZH: 收购、会社そのものは EN: buys and sells ／ ZH: 买卖。EN の resell・buy and resell、ZH の 买断后转售・采购并出售 は使わない。
5. 英語・中国語の頁に証券化（GK-TK）の話を新しく足さない（今ある文は日本語に合わせる）。
6. 中国語は簡体字・中国大陆の業界の言い方で書き、日本の制度名は頁の本文の初出に「中文（日本語の原語）」の形で原語を添える（title・description には添えない）。日本語の漢字をそのまま流用しない（下の「使わない語」）。

## 対応表

| 日本語 | 英語 | 英語の根拠 | 中国語 |
|---|---|---|---|
| 長期脱炭素電源オークション | Long-Term Decarbonized Power Source Auction (LDA) | 経済産業省の英語資料は "long-term decarbonized power source auction"（OCCTO の英語の頁は "long-term decarbonized capacity auction"）。略称 LDA はこのサイトの呼び方（公的な略称は未確認） | 长期脱碳电源拍卖（長期脱炭素電源オークション，LDA） |
| 容量市場 | capacity market | OCCTO の英語の頁 | 容量市场 |
| 需給調整市場 | balancing market（初出は supply and demand balancing market） | EPRX の英語の頁 "supply and demand balancing market" | 辅助服务市场（需給調整市場） |
| 電力需給調整力取引所（EPRX） | Electric Power Reserve Exchange (EPRX) | EPRX の英語の頁（about） | 电力供需调整力交易所（EPRX） |
| 一次調整力 | Primary Reserve (FCR) | EPRX の英語名は "Primary balancing capacity"（FCR）。このサイトは Reserve の呼び方にそろえ、初出に略号を添える | 一次调频（一次調整力，FCR） |
| 二次調整力① | Secondary Reserve 1 (S-FRR) | EPRX "Secondary balancing capacity (1)" | 二次调频①（二次調整力①） |
| 二次調整力② | Secondary Reserve 2 (FRR) | EPRX "Secondary balancing capacity (2)" | 二次调频②（二次調整力②） |
| 三次調整力① | Tertiary Reserve 1 (RR) | EPRX "Tertiary balancing capacity (1)" | 三次备用①（三次調整力①） |
| 三次調整力② | Tertiary Reserve 2 (RR-FIT) | EPRX "Tertiary balancing capacity (2)" | 三次备用②（三次調整力②） |
| 複合商品 | combined product | 公的な英語名は未確認 | 复合产品 |
| オフライン枠 | offline category | 公的な英語名は未確認 | 离线类别（オフライン枠） |
| 調達（需給調整市場で調整力を買うこと） | procurement | — | 采购（「调度」は給電指令の意味なので使わない） |
| 落札率 | award rate | — | 中标率 |
| 第N回（入札・会合） | Round N（会合は the Nth meeting） | — | 第N次 |
| 日本卸電力取引所（JEPX） | Japan Electric Power Exchange (JEPX) | JEPX | 日本电力交易所（JEPX） |
| 電力広域的運営推進機関（OCCTO） | Organization for Cross-regional Coordination of Transmission Operators, Japan (OCCTO) | OCCTO の英語の事業計画 | 电力广域运营推进机构（OCCTO） |
| 資源エネルギー庁 | Agency for Natural Resources and Energy (ANRE) | — | 资源能源厅 |
| 一般送配電事業者 | general transmission and distribution company（略して T&D company。TSO は略号として可） | OCCTO "general transmission and distribution companies" | 一般输配电企业（一般送配電事業者） |
| 事業者・申込者（接続を申し込む側） | developer / applicant（送配電と同じ operator を使わない） | — | 开发企业／申请人 |
| 接続検討 | connection study（OCCTO の規程では interconnection study） | OCCTO Operational Rules "interconnection study" | 接入系统研究（接続検討） |
| 接続検討の回答（回答書） | connection study response | — | 接入系统研究答复 |
| 系統連系・連系 | grid connection / interconnection | — | 并网 |
| 系統（電力系統） | grid | — | 电网 |
| 系統用蓄電池 | grid-scale battery storage (grid-scale BESS) | 公的な英語名は未確認 | 电网侧储能（系統用蓄電池） |
| 工事費負担金 | construction cost contribution | 公的な英語名は未確認 | 并网工程费分摊（工事費負担金） |
| 特別高圧 | extra-high voltage (EHV) | 一般送配電事業者（東京電力）の英語の頁 "extra-high-voltage (EHV)" | 特别高压（日本的电压分类，非中国 800kV 级的 UHV） |
| 高圧 | high voltage (HV) | 同上 | 高压（日本的电压分类） |
| 低圧 | low voltage (LV) | 同上 | 低压 |
| 名義変更（申込者の地位を買主へ移す） | transfer of applicant status (assignment of contractual status) | — | 申请人地位转让（名義変更） |
| 権利渡し／完成渡し | sale of development rights / sale on completion | — | 权利转让／竣工后转让 |
| 蓄電所マーケット | Chikudensho Market（初出は our marketplace for grid-scale BESS projects を添える） | 当社のサービス名 | 蓄电所市场（Chikudensho Market） |
| 管区・エリア「中国」 | Chugoku | — | 中国地区（日本本州西部） |
| 1兆8,506億円 | ¥1.8506 trillion（表示どおり。丸めない） | — | 1.8506万亿日元 |

## 中国語で使わない語（日本語の漢字の流用・誤訳）

| 使わない | 使う |
|---|---|
| 接续（接続） | 接入 |
| 接续研讨・接续检讨・接続検讨・接入检讨 | 接入系统研究 |
| 接续供给（接続供給） | 输配电服务 |
| 业者・事业者 | 企业（発電事業者＝发电企业、小売電気事業者＝售电企业） |
| 特高压（中国では 800kV 以上の UHV） | 特别高压 |
| 未满 | 不足・低于 |
| 检讨 | 研究・评估 |
| 调度（調達の意味で） | 采购 |
| 实绩 | 实际数据・结果・业绩 |
| 工程费负担金・工程负担金・并网分摊金 | 并网工程费分摊 |
| 需给调整市场・供需调节市场 | 辅助服务市场 |
| 电力辅助服务交易所 | 电力供需调整力交易所 |
| 第N回 | 第N次 |

## 英語で使わない語

| 使わない | 使う |
|---|---|
| Long-Duration (Decarbonized) Auction・Long-term Decarbonization Auction などの揺れ | Long-Term Decarbonized Power Source Auction (LDA) |
| connection review | connection study |
| special-high voltage | extra-high voltage (EHV) |
| Electric Power Reserve eXchange | Electric Power Reserve Exchange |
| operators（申込者を指すとき） | developers / applicants |
| connection charges（工事費負担金を指すとき） | construction cost contribution |
| Name Change Application | transfer of applicant status |
