---
slug: guide-siting-risk
lang: en
title: Battery Storage Noise and Siting Risk in Japan | ScienceX
h1: Noise, Hazard and Siting Risk for Grid-Scale Battery Storage in Japan
description: Battery storage in Japan: night-time noise, flood risk (EAL), DC-side O&M gaps, insurance and site checks before buying.
columns: en/column-four-labels, en/column-noise, en/column-hazard-eal, en/column-om, en/column-bess-insurance, en/column-buyer-check
published: 2026-11-22
modified: 2026-11-23
---

## @tldr

- The usual sources of trouble at a storage site are cooling-fan and PCS noise that does not stop at night, flood and landslide hazard, the gap over who fixes the DC side when the plant stops, and how the insurance is built.
- O&M is a design matter before COD, not something to think about afterwards, and noise measures that cost several million yen at the design stage jump to a different order of magnitude when retrofitted after operation.
- The way to check is on paper: a night-time noise prediction, inundation depths by probability, the as-built documentation for communications, and the evidence trail you will be asked for after an incident. A seller's explanations are claims, not facts, until they are on third-party paper.

## Start with the map — size, siting and tax can't be chosen separately

For one and the same battery, four separate laws — the Electricity Business Act, the Local Tax Act, the depreciation rules, and the City Planning Act with the Agricultural Land Act — each attach their own label, each for a different purpose.

The labels pull in different directions, so size, siting and tax have to be set together, as a single triangle, not one at a time. The column lays out the whole map for a ~2 MW / 8 MWh unit; the chapters below take the site-level risks one by one.

more: Read more → [Grid-Scale Battery Storage in Japan: The Full Picture of Regulation, Tax & Siting](/en/column-four-labels)

## Noise — the night-time standard is what gets missed

Battery cells themselves make no noise. The sound comes from the cooling systems that keep the cells at temperature, and from the fans inside the PCS. At 1 m, a PCS cooling fan at full speed runs 70–80 dB, a battery-container cooling system 72–75 dB, and transformer hum 65–75 dB; at large sites with dozens of containers, the combined level rises well above any single unit. With homes within 50 m, the level is one that triggers complaints.

Grid-scale batteries run 24 hours, and "shut down at night" effectively isn't an option. Meanwhile, the cooling systems are highly likely to qualify as "blowers" under the Noise Regulation Act Enforcement Order, and daytime standards of 45–70 dB tighten to 40–65 dB at night.

There are four measures to weigh at the design stage: low-noise equipment, layout, sound barriers, and operating-hour control (a last resort, because of the revenue impact). Boundary levels can be predicted with an ISO 9613-2 simulation, from several hundred thousand yen depending on scale. And the biggest reason noise problems escalate is insufficient explanation — hold briefings, set up a contact point, and monitor after start-up.

more: Read more → [Noise Risk at Battery Storage Facilities — the night-time standard](/en/column-noise)

## Hazard — measure Expected Annual Loss, not the color on the map

A flood hazard map is a life-safety (evacuation) map under the Flood Control Act; what it draws is the worst case at an annual exceedance probability of 1/1000 or less. Use its colors as a yes/no filter and you don't remove risk, you just trade it for another one, such as hillside sites with landslide risk and earthwork.

Since December 2022, MLIT has been rolling out multi-stage inundation maps that show the same land's depth from 1/10 up to the maximum assumed scale. Combined with the Flood Control Economic Survey Manual, a location hazard becomes an Expected Annual Loss (EAL) in yen. In a model calculation we built ourselves (HV 2 MW / 8 MWh, ¥400M depreciable asset, illustrative probability bands for a riverside site), the EAL comes to about ¥16M a year; raising the equipment foundation by 1 m nearly halves it, to about ¥7.2M a year.

Two zones stay out however you quantify them: the building-collapse inundation zone and the Special Landslide Hazard Zone. When a candidate address arrives, check those two first on the Overlay Hazard Map; if it falls inside, stop there.

more: Read more → [Hazard-map colors can't choose a battery-storage site — Expected Annual Loss (EAL)](/en/column-hazard-eal)

## When the plant stops, who fixes it — the O&M gap

Storage operation is often described as a three-party job: aggregator, licensed chief engineer and OEM. But the aggregator faces the market on the assumption the equipment is running, the chief engineer guards the receiving/transforming (AC) side, and the OEM looks only as far as its own devices. When something goes wrong on the DC side (EMS, PCS, BESS, BMS), no one is assigned to be the first to triage it and begin recovery. The law places safety supervision of the DC side on the chief engineer, but there is no provision that names who actually fixes the devices.

Communications are the most exposed. A "comms fault" on the EMS means different instructions depending on whether the router or the fiber line went down, and if the as-built documentation was never handed over, no one can fix it at the moment of failure.

A stop costs more than lost trading. In the capacity market, maintenance filed in advance as a planned outage counts at parity, while a sudden unplanned outage counts at 5x (excluding normal nights and holidays). O&M is a design matter before COD; in practice, start assembling it roughly six months before interconnection.

more: Read more → [When the storage stops, who fixes it?](/en/column-om)

## Insurance — six layers, and keep the evidence

The "movables + business interruption" package used for solar does not transfer: movables comprehensive insurance excludes generation facilities of 500 kW or more in each carrier's wording. For the operating phase, build cover in six layers — property, machinery, business interruption, liability, cyber and theft.

Set the insured value on a replacement-cost basis, not market value. If it falls short, proportional indemnity cuts the payout: in the column's example, ¥300M of cover against a ¥600M replacement cost pays only ¥100M on a ¥200M partial loss.

The other pressure point is timing. In the Kagoshima case (Isa, March 27, 2024), the payout was reported as still unpaid more than a year after the event, although fire insurance was in place. From day one of operation, keep at least three years of BMS and EMS logs, operation history and maintenance records in cloud storage. On the hazard side, tsunami is a standard exclusion on the earthquake side, not "flood," and earthquake-triggered liquefaction falls on the same excluded side; filling the gap requires an earthquake-risk endorsement.

more: Read more → [BESS Insurance Design — The Six Insurance Layers Owners Must Arrange During Operation](/en/column-bess-insurance)

## Before you buy, check on site — neighbors, noise, delivery, ground

This is the domain most often missed in desk-based document checks and most bitterly disputed after purchase.

For community consent, open up "we've briefed them": when, to whom, what was explained, with invitations, attendance records, minutes and consent forms — and whose consent it is. For noise, a cutoff like "◯ m from a home and I can buy it" doesn't work. Look instead at three things: a predictive calculation against the night-time standard, whether the mitigation is folded into design and cost, and evidence of resident briefing and adjacent landowners' consent. The walk-away line is a night-time exceedance that mitigation can't resolve.

Check the delivery route too (containers and transformers of tens of tons on 16-m-class trailers), the ground and hazards, and dated site photos. Only when coordinates, parcel number, photo and actual conditions all match can you talk about "that land."

more: Read more → [The Technical Checks Before You Buy a Grid-Scale Battery Storage Facility](/en/column-buyer-check)

## @next

- **If you are buying** — projects that hold a connection study response are for sale on Chikudensho Market, open to view without registration: project name, prefecture and city, scale, voltage, how to buy, procedural stage, expected start of operation and photos. For each project we write up and hand over the distance to occupied buildings and the expected noise at the site boundary.
  → [See projects on Chikudensho Market](https://dealroom.scix.co.jp/en)
- **If you are selling** — we either buy the project ourselves or introduce you to a buyer. We take projects that hold a connection study response, rights with interconnection approval, and operating storage plants. We do not buy or lease land alone.
  → [Request a free sale assessment](/en/contact)

## @faq

### How loud is a grid-scale battery storage site?

At 1 m, a PCS cooling fan at full speed runs 70–80 dB, a battery-container cooling system 72–75 dB, and transformer hum 65–75 dB; with dozens of containers the combined level rises further. Night-time standards are 40–65 dB, and with homes within 50 m the level is one that triggers complaints. (→ /en/column-noise)

### How do you prevent noise trouble at a battery storage site?

Weigh four measures at the design stage — low-noise equipment, layout, sound barriers and operating-hour control — and check the boundary level with a simulation. Measures that cost several million yen at the design stage jump to a different order of magnitude when retrofitted. Since insufficient explanation is the biggest reason disputes escalate, hold briefings, set up a contact point and monitor after start-up. (→ /en/column-noise)

### Can a site inside a flood hazard area still be used?

Color alone doesn't decide it. Read inundation depths by probability from the multi-stage maps and compare the EAL with the cost of raising the site and the insurance terms. The building-collapse inundation zone and the Special Landslide Hazard Zone, however, are a veto. (→ /en/column-hazard-eal)

### What insurance does a battery storage plant need?

Not the solar "movables + BI" package — movables cover excludes generation facilities of 500 kW or more. Build six layers (property, machinery, BI, liability, cyber, theft) through a broker with battery storage experience, with the insured value on a replacement-cost basis. (→ /en/column-bess-insurance)
