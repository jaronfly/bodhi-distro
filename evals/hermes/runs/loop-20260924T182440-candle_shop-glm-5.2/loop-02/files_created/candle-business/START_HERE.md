# Candle business — session home

First session: Sept 24, 2026. Durable context lives in three places:
this file (workspace anchor), the `candle-shop` skill (procedures + resume state),
and harness memory (who Player One is). Corrections to any of it are welcome.

## What's built (all tested)
- candle_profit.py — answers "am I making money?" from your Etsy Order CSV
  + a per-product materials cost file. Run `python3 candle_profit.py --demo`
  to see it on fake data; `--help` for real-use flags.
- listing_kit.py + sheet_cedar_sage.json — Etsy listing validator/assembler
  (enforces 140-char titles, 13 tags x 20 chars, no dupes).
- INTERVIEW.md — the voice + product questions. Your answers drive the real listings.

## Waiting on Player One (in order of value)
1. Etsy Order CSV export (3 months) + rough per-candle materials costs -> real profit run
2. INTERVIEW.md Part A (voice) + one product's Part B -> first real listing
3. Later: customer-message triage setup

## Demo caveat
Every number shown so far is generated demo data. Nothing here knows your
real sales yet.
