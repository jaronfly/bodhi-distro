---
name: etsy-candle-shop
description: Use for candle shop work — listings, fees, product voice.
version: 0.01
---

# Etsy candle shop kit

Player One sells hand-poured candles online (12 products, Etsy US as of Sep 2026). Workspace dir: candle_business/. Full state in candle_business/SESSION_NOTES.md. Their voice, their words: "casual and warm, like I'm talking to a friend who wandered into the shop." Current listings are scent name + price only.

## Verified Etsy US fees (checked Sep 2026 against Etsy help pages)

- Listing: $0.20 per listing/renewal (auto-renews after each sale)
- Transaction: 6.5% of item price + shipping charged + gift wrap (not sales tax)
- Payment processing (US bank): 3% + $0.25 of total order amount (incl. tax)
- Offsite Ads: 12% (<$10k/yr revenue) or 15%, only on attributed orders — biggest silent fee
- Also exist: new-shop setup fee, Regulatory Operating Fees (some countries), 2.5% currency conversion
- Effective take on a plain US order ≈ 9.5% + $0.45, before supplies/label/ads

## Etsy listing structure (per Etsy Seller Handbook, Sep 2026)

- Search reads the whole listing (title, tags, attributes, description, photos, reviews) — titles must be clear, not keyword-stuffed
- Title: front-load the noun ("Wild Fig & Cedar Scented Candle"), no subjective words, no sale/shipping info, no repeated words; first ~40 chars weigh most, max 140
- Description: first 160 chars carry mobile/Google weight (hook, not a title copy); scent in spoken words; details as bullets; maker note in first person; brief care/safety line
- Tags: 13 slots × 20 chars, never repeat title phrases; cover angles (occasion, material, recipient, use case); fill all attributes — free keywords

## Workflow rules that earned their place

1. Never draft listing prose before Player One's voice sample exists — capture how they describe a scent to a friend, verbatim, first. Inventing a voice fails their stated acceptance test ("sounds like me").
2. Demo-voice method: write the same product 3 contrasting ways (plain spoken / warm personal / dry direct); they point at a letter + say what's off.
3. candle_profit.py runs on a CONFIG block; its costs are placeholder estimates — never present its dollar output as fact until real supply + label costs replace them.
4. In no-reply turns, build with labeled assumptions and say plainly which parts are placeholders; never let a placeholder ride as their voice or data.
