---
slug: guide-balancing-market
lang: en
title: EPRX and Japan's Balancing Market: A Guide | ScienceX
h1: EPRX and Japan's balancing market — a guide
h1_sub: Products, trading results, the price cap and saturation on one page
description: EPRX and Japan's balancing market on one page: 5 products, area results, the ¥10 cap, the fixed-cost adder, saturation.
columns: en/column-balancing-market, en/column-eprx, en/column-area-data, en/column-day-ahead, en/column-price-cap, en/column-bidding-ceiling-market, en/column-bidding-ceiling, en/column-bidding-ceiling-law, en/column-bidding-ceiling-calc, en/column-bidding-ceiling-monitoring, en/column-balancing-saturation, en/column-balancing-saturation-volume, en/column-balancing-saturation-supply, en/column-balancing-saturation-floor, en/column-aggregator-fee, en/column-aggregators, en/column-aggregators-roster, en/column-aggregators-volume, en/column-aggregators-pricing, en/column-aggregators-switching, en/column-aggregators-overseas
published: 2026-11-22
modified: 2026-11-24
---

## @lead

The balancing market is one of the main sources of income for a battery in Japan. This page walks through the key points of our 21 columns on this market, in the order readers usually ask. Figures keep each column's data window (which data, from when). The evidence and sources are in each column.

## @tldr

- The balancing market is where the general transmission and distribution companies buy balancing capacity (ΔkW) to keep frequency stable. It is run by EPRX (Electric Power Reserve Exchange). For batteries, the fast products, Primary Reserve and Secondary Reserve 1, are the most advantageous.
- From transactions on March 13, 2026, trading moved to day-ahead, 30-minute slots, and the cap for Primary, Secondary 1 and the composite product fell from ¥19.51 to ¥15; from delivery on September 1, 2026 it is ¥10.00 (per ΔkW·30 min).
- In September, the first month under the ¥10 cap, primary offline averaged ¥5.81 nationally. Only Tohoku (¥9.51) and Tokyo (¥8.58) stayed just under the cap, and in August the batteries-only frame was still half open (shortfall rate 53%).

## @top

Grid-scale battery projects in Japan that hold a connection study response are for sale on Chikudensho Market, open to view without registration.
→ [See projects on Chikudensho Market](https://dealroom.scix.co.jp/en)

## What the balancing market and EPRX are

The balancing market trades balancing capacity, not electrical energy itself. The buyers are the general transmission and distribution companies (TSOs); the sellers are generation companies and battery operators. Sellers are paid for "standing by ready to operate at any time, at a specified output, during specified time periods." Because batteries can change their output in milliseconds, they have a structural advantage in this market.

The market is run by EPRX, the Electric Power Reserve Exchange, a general incorporated association. It took on this role in line with the start of trading for all balancing market products in April 2024. EPRX is a separate entity and a separate market from JEPX (Japan Electric Power Exchange). A battery faces three markets: JEPX trades electrical energy (kWh), EPRX trades balancing capacity (ΔkW = standby), and the Capacity Market run by OCCTO secures future supply capability (kW). How the three are combined (stacked) decides a battery's business viability.

more: Read more: [Japan's Balancing Market — 5 products and composite bidding](/en/column-balancing-market) / [What is EPRX](/en/column-eprx) / [The 3 revenue sources of batteries](/en/column-revenue)

## The five products, and Primary Reserve where batteries are strongest

There are five products: Primary Reserve, Secondary Reserve 1, Secondary Reserve 2, Tertiary Reserve 1 and Tertiary Reserve 2. They differ by how quickly they respond and how long they sustain: Primary within 10 seconds, Secondary 1 and 2 within 5 minutes, Tertiary 1 within 15 minutes, Tertiary 2 within 60 minutes. Primary through Tertiary 1 can be entered with a single bid as the composite product; only Tertiary 2 trades in an independent market.

Primary Reserve has two ways to take part: Online, connected by a dedicated line, and Offline, with no dedicated line and the response record submitted afterwards. Under EPRX trading rules, Offline is open to batteries of 1 MW or more but less than 10 MW (or aggregated batteries under 1 MW); batteries of 10 MW or more must use Online for Primary Reserve. All products from Secondary Reserve onward require Online connection.

In the FY2025 first half, Primary Reserve awards ran at 9.6–13.5 yen for batteries and 2.1–3.4 yen for thermal (per ΔkW·30 min, monthly range). The gap in response speed shows up directly as a gap in price.

more: Read more: [The 5 balancing market products — Online, Offline and composite](/en/column-balancing-market)

## Reading the trading results — 9 areas × 5 products

EPRX publishes its trading results, so you can check which product cleared, in which area and at what price (EPRX trading results: https://www.eprx.or.jp/information/results.php ). We organize them by 9 power areas and 5 products, using the first complete quarter after the move to day-ahead trading, April–June 2026 (preliminary figures), as the main data.

- Primary Online: the national shortage rate is 28.3% (59.2% in FY2025 under the old system). Tohoku (60.9%) and Tokyo (46.2%) stay high; Chugoku (3.7%) and Kyushu (4.9%) are nearly fulfilled; Shikoku and Hokkaido are in oversupply.
- Primary Offline: the national shortage rate is 67.9% (96.6% in FY2025). Batteries take 98.9% of awarded volume, and the average awarded price is about 12 yen per ΔkW·30 min.
- Secondary 1: Kansai (86.8%), Tohoku (53.0%) and Hokuriku (50.2%) are short; Hokkaido, Chubu, Chugoku and Kyushu are in oversupply.
- Secondary 2, Tertiary 1 and Tertiary 2: nearly fully supplied.

The shortage rate is (solicited volume − awarded volume) / solicited volume. It does not mean blackout risk: TSOs secure what the market does not supply through bilateral contracts with thermal and pumped-hydro plants and similar means. Read together with Capacity Market prices (FY2028 clearing), Tohoku and Tokyo are the most advantaged on both fronts.

more: Read more: [Balancing market results by area — 9 areas × 5 products](/en/column-area-data) (figures, CSVs and how to credit them: [Citation & Press Guide](/en/press))

## What changed in 2026 — day-ahead trading and the price cap

From transactions on March 13, 2026, Primary through Tertiary 1 moved from weekly products to day-ahead trading, in which the next day is bid at 14:00 the day before. The trading unit went from 3-hour blocks to 30-minute slots, and every product's duration was unified at 30 minutes. At the same time, the cap for Primary, Secondary 1 and the composite product fell from ¥19.51 to ¥15, and procurement volume for Primary and Secondary 1 went from 3σ to 1σ.

The cap then fell to ¥10.00 from delivery on September 1, 2026 (EPRX announcement, July 30, 2026). Secondary 2 and Tertiary 1 stay at ¥7.21; Tertiary 2 has never had a cap. The next step, ¥7.21, applies "if no improvement in competitive conditions is observed in the market."

What matters in operation is the daily split with JEPX. Only volume bid into the JEPX spot market and left unsold can be offered into the balancing market, so every day an operator decides, for each of the next day's 48 slots, whether to sell on JEPX or stand by in the balancing market. Because a battery cannot offer into the market while it is charging, how many of the 48 slots it can put on the market directly determines its revenue.

more: Read more: [The balancing market's shift to day-ahead trading](/en/column-day-ahead) / [The 5 products (FY2026 policy changes)](/en/column-balancing-market) / [The ceiling drops by five yen](/en/column-price-cap)

## What the ¥10 cap changed — the estimate, and September in practice

From EPRX's awarded-results CSVs (delivery 2026/3/14–8/18, 158 days), our central estimate is that the ¥10 cap removes −8.6% of ΔkW fees across the four capped products, about ¥30 billion a year (range −3 to −18%). The largest cut by product is −22% for primary offline, where batteries hold a 99% share; the largest area × product cell is Tohoku × primary offline at −32%. A bid above the cap can still clear, but it is clipped down to ¥10 at settlement.

The market did not wait for September 1. The share of primary-offline volume pinned at ¥15 collapsed from 83% in April to 10% in August, and the national average awarded price in August, ¥9.80, was already under the new ceiling before it applied.

In September 2026 (1–29 September, preliminary figures), primary offline averaged ¥5.81 nationally, down from ¥11.07 in April–August. Tohoku at ¥9.51 and Tokyo at ¥8.58 stayed just under the cap; the other seven areas fell to the ¥1–3 range. What split them was the award rate — the share of bids that were awarded: Tohoku 95.6%, Tokyo 85.1%. Where almost every bid gets through, the price leans towards the cap.

more: Read more: [The ceiling drops by five yen](/en/column-price-cap) / [September under the ¥10 cap: primary offline at ¥5.81](/en/column-bidding-ceiling-market)

## The second ceiling — the fixed-cost adder

Below the ¥10 cap is a second ceiling whose height differs from operator to operator: Section III.2 of the Balancing Market Guideline (revised 13 March 2026), "ΔkW price ≤ lost profit (opportunity cost) of the resource concerned + fixed-cost adder, etc." The adder is either Type A, ¥0.33 and open to anyone, or Type B, a calculated amount that can be used only while fixed costs have not yet been recovered: a year's fixed costs minus revenue from other markets, divided by the volume you can bid in a year. Even a plant that is not in the capacity market deducts what it would have earned there.

Put in only published figures, a 2 MW / 8 MWh plant in Tokyo gets an adder of ¥1.411 in year 1 of operation, ¥0.959 in year 2 and ¥0.33 in year 18. A battery can bid into most slots of the day, so the divisor is large and the adder comes out small. This ceiling concerns almost only batteries.

The text says "desirable", not obligatory. But the same revision added that unfairly earning profits through unreasonably high bids can be subject to a business improvement order. The Type B consultation with the EGC secretariat (5 cases in FY2024, 34 in FY2025 as of 17 October 2025) has ended; from FY2026 operators calculate the adder themselves and keep the basis. At the June 2026 expert committee, operators that had won at high prices were asked to revise their calculations — a request, not a sanction. The formula is reviewed every year: the next recommendation is due in December 2026 and the amendment in March 2027.

more: Read more: [The second ceiling](/en/column-bidding-ceiling) / [The fixed-cost adder, read from the text](/en/column-bidding-ceiling-law) / [Setting the adder from published figures](/en/column-bidding-ceiling-calc) / [Who has watched ΔkW prices, and how](/en/column-bidding-ceiling-monitoring)

## Are batteries saturated?

We re-read the published data of EPRX and JEPX and the government councils' primary materials and counted. The answer: the small seat has begun to fill, and the room is still wide.

- Procurement volume did not fall to one third. FY2026 over FY2025, required volume is 0.55, the procurement volume put to the market is 0.62, and the largest product, the combined product, is 0.97. What halved is the batteries' own seat, primary offline (0.45, about 500 MW per slot nationwide). Half of the reason for the fall is that the TSOs locked up 266 × 10,000 kW of pumped storage outside the market.
- The shortfall rate of the batteries-only frame (primary offline) went from 67.9% in April–June to 53% in August. Awarded battery volume rose about 1.8-fold in four months, but only Tokyo is 80% full; Kansai, Chugoku and Hokkaido are still largely open. In the online seats batteries compete with thermal and pumped storage on the same bids, holding 9% of the combined product and 23% of primary online.
- What arrives is part of what is applied for: contract applications are about 3,527 × 10,000 kW (end of March 2026). On the developers' own plans it is 631 × 10,000 kW in FY2030 — short even of the vessel formed by primary, secondary 1 and the combined product (680 × 10,000 kW).
- The price floor is not "thermal's ¥3" but what a battery could earn on JEPX: ¥6–8 in the 8 evening slots depending on the area, in the ¥1 range averaged across 48 slots. Kyushu cleared at ¥4.9 in August with the cap still at ¥15.

more: Read more: [Are batteries saturated?](/en/column-balancing-saturation) / [What the 1σ change actually cut](/en/column-balancing-saturation-volume) / [When and where batteries arrive](/en/column-balancing-saturation-supply) / [Where is the floor below ¥7.21?](/en/column-balancing-saturation-floor)

## Taking part — trading membership and the aggregator

To bid in the balancing market, you register as an EPRX trading member and conclude a generation sales contract with a general transmission and distribution company to join a balancing group. The party that concludes the generation sales contract and the trading member need not be the same: the owner can be the trading member while an aggregator handles operations, or an aggregator can take part collectively as the trading member. A company taking part as an aggregator files a notification for a Specified Wholesale Supply business under the Electricity Business Act (it is not a licence or registration); 187 had filed as of 30 October 2026 (COLUMN 53).

After the move to day-ahead trading, the allocation across 48 slots depends on the aggregator's algorithms, and the same facility can yield different annual revenue. Fee rates alone do not compare: with the same rate, a gross or a net calculation base changes what the owner keeps. Before signing, check five points — the calculation base in writing, the scope of the fee (balancing market only, or JEPX arbitrage and capacity market income too), who bears imbalance penalties, contract duration and termination, and whether the aggregator can disclose the past 12 months of performance (revenue per MW, award rate, utilization rate).

more: Read more: [What is EPRX (steps to participate)](/en/column-eprx) / [Aggregator fees: gross vs net](/en/column-aggregator-fee) / [Counting the aggregators](/en/column-aggregators)

## @next

- Buying: projects that hold a connection study response are for sale on [Chikudensho Market](https://dealroom.scix.co.jp/en), open to view without registration. Project-specific information not covered in our articles is available after free registration.
- Selling a project that holds a connection study response: we either buy the project ourselves or introduce you to a buyer. → [Contact us](/en/contact)
- Read the revenue side: [The 3 revenue sources of batteries](/en/column-revenue) / [Revenue by area](/en/column-regional-revenue) / [The capacity market main auction](/en/column-capacity-market)
- Terms: [Glossary](/en/glossary) / all columns: [Knowledge](/en/knowledge)

## @faq

### What is EPRX?
EPRX is the Electric Power Reserve Exchange, a general incorporated association that runs Japan's balancing market. It took on this role in line with the start of trading for all balancing market products in April 2024. JEPX trades electrical energy (kWh); EPRX trades balancing capacity (ΔkW = standby). They are separate entities and separate markets.

### Where can I see the balancing market trading results?
EPRX publishes them on its website (https://www.eprx.or.jp/information/results.php ), showing which product cleared, in which area and at what price. We organize them by 9 areas × 5 products, with April–June 2026 (preliminary) as the main data: [Balancing market results by area](/en/column-area-data).

### What products does the balancing market have?
Five: Primary Reserve, Secondary Reserve 1, Secondary Reserve 2, Tertiary Reserve 1 and Tertiary Reserve 2. Primary through Tertiary 1 can be entered with one bid as the composite product; Tertiary 2 trades in an independent market. The faster the response, the better the fit for batteries.

### What is the balancing market price cap?
From delivery on September 1, 2026, the cap for primary reserve (including the offline quota), secondary reserve 1 and the composite product is ¥10.00 per ΔkW·30 min (¥15 for delivery from 14 March to 31 August 2026, ¥19.51 before that). Secondary 2 and tertiary 1 stay at ¥7.21; tertiary 2 has no cap. A bid above the cap can still clear but is clipped to ¥10 at settlement.

### Are batteries saturated in Japan's balancing market?
On our count, the small seat has begun to fill and the room is still wide. The batteries-only frame (primary offline) still had a 53% shortfall rate in August 2026. In September, though, primary offline averaged ¥5.81, and outside Tohoku and Tokyo competition, not the cap, set the price.
