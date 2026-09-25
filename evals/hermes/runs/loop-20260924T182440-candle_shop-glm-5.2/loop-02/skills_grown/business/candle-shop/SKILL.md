---
name: candle-shop
description: Use for the candle shop (profit, listings, messages).
version: 0.01
---

# Candle shop workflow

Player One sells hand-poured candles online (assumed Etsy, roughly 20–100 orders/month — unconfirmed). Business workspace: `candle-business/` under the session home.

## Tools built (stdlib-only Python, tested)
- `candle_profit.py` — real profit from an Etsy Order CSV export plus a per-unit materials cost file. Flags for fee rates, fixed monthly costs, labor minutes, Etsy statement. `--demo` regenerates demo data; the selftest line must print PASS after any edit.
- `listing_kit.py` — validates a listing JSON sheet against Etsy's mechanical rules and assembles title/tags/description. `sheet_cedar_sage.json` is the filled example.

## Etsy facts (verified Sept 2026)
- Tags: max 13 per listing, 20 characters each including spaces, unique, letters/digits/hyphens/apostrophes only; multi-word phrases are matched whole, so long-tail beats single words.
- Listing titles: 140 characters max.

## Procedure: profit run
1. Collect the Etsy Order CSV export (Shop Manager → Orders → Download CSV) and per-unit materials costs (wax+jar+wick+fragrance+label+packaging) from Player One.
2. costs file columns: `product,materials_cost` — matched exact-then-substring against item names.
3. Run `python3 candle_profit.py --orders X --costs Y [--etsy-statement S]` → monthly net, per-product margin, verdict, effective hourly earnings.
4. Report unmatched items loudly: profit is overstated until their costs are added.

## Procedure: new listing
1. Voice before copy: INTERVIEW.md Part A. Load-bearing questions: A4 (what big brands do that they refuse), A5 (scent language: ingredients vs mood vs memory), A8 (one real line written to a customer).
2. Facts per product: Part B → `sheet_<name>.json` (copy the cedar+sage example).
3. Run `listing_kit.py sheet.json`. Hook and story must be Player One's own words or clearly approved by them — never ship placeholder voice.

## Lessons
- Ask discovery questions as plain text in the reply; in these sessions the clarify tool returns a oneshot fallback, not answers.
- Label every assumed number and every placeholder voice; Player One judges work by honest state, not polish.
- Listing quality criteria stated by Player One: it sounds like them, and the right questions were asked before writing.

## Resume state (update as work moves)
- Profit: tool built and demo-verified; awaiting real CSV export + costs answers.
- Listings: kit + interview delivered, demo draft shown; awaiting Part A answers + one product's Part B, then write that listing for real and learn voice from corrections.
- Customer messages (third pain): not started; triage + reply drafts is the natural shape.
