---
name: etsy-candle-shop
description: "Use for the candle shop — listings, fees, orders, admin."
version: 0.01
---

# Etsy candle shop (Player One)

Shop facts live in candle-business/NEXT_UP.md in the workspace (current task,
open questions, assumptions). Products: 12 hand-poured candles.

## Listing workflow
1. Inputs before writing: scent list (or shop URL / current titles), shared
   specs (wax, vessel, burn time, wick), and a 2-4 sentence VOICE SAMPLE from
   Player One describing a scent unpolished. No drafting without a voice
   sample; check every draft against it.
2. Fill one copy of candle-business/listings/TEMPLATE.md per product:
   title, opening 2-3 keyword-natural sentences, scent-in-their-words,
   spec bullets, care/safety, shipping, mini FAQ, 13 tags.
3. Offer one demo listing first and let reactions to a near-miss tune the
   voice before batch-writing all 12.

## Verified facts (Sept 2026 — re-verify if months stale)
- Etsy US fees per sale: $0.20 listing (re-charged each unit sold), 6.5%
  transaction on item+shipping charged, 3% + $0.25 processing on order total.
  Typical order: ~10-11% in fees. Offsite Ads: 15% (12% over $10k/365d).
- Under $10k trailing-365-day sales, Offsite Ads is optional and can be
  turned off: Shop Manager > Settings > Offsite Ads.
- Etsy title guidance (2026): plain and clear, state the noun once, no
  subjective descriptors, no sale/free-shipping phrasing.
- Tags: 13 slots, 20 chars each; multi-word long-tail phrases; don't repeat
  a word across tags; strongest tags should also appear in the title.
- No health claims in descriptions: avoid calming, relaxing, aromatherapy,
  stress relief, therapeutic. Describe scent + moment instead.

## Profit kit
candle-business/profit.py — estimate mode (products.csv volumes) and actual
mode (orders.csv; convert Etsy's order-history CSV export into it). Fee
rates in config.csv.
