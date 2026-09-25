---
name: candle-listings
description: Use when writing candle shop listings for Etsy.
version: 0.01
---

# Candle listing workflow

Workspace: candle-business/ (in home dir). Intake form: listing-intake.md. Listings live in candle-business/listings/<slug>.json. Checker: candle-business/check_listing.py.

## Order of work
1. Voice first. Get 2-3 real writing samples from Player One (About page, caption, customer reply, text to a friend) BEFORE drafting. Keep voice_status: PLACEHOLDER in JSON until real samples exist; never publish placeholder voice.
2. Facts per candle: name, scent notes, story, vessel/oz, wax+wick, burn time, price, shipping charged, photos.
3. Draft into listings/<slug>.json with fields: name, voice_status, platform, title, tags[13], description, attributes, price, size_oz, burn_time_h.
4. Run: python3 candle-business/check_listing.py candle-business/listings/<slug>.json
5. Fix FAILs and WARNs until clean. Typical fixes: gifting words in title -> tags; one root in 4+ tags -> swap for a new search angle (recipient, style, occasion, material).

## Etsy rules baked into the checker (verify vs Seller Handbook periodically; pulled Sept 2026)
- Title max 140 chars, ~15 words, item noun in first 5 words, no subjective/gifting phrases in title.
- Exactly 13 tags, each <=20 chars, multi-word phrases, no duplicate roots across 4+ tags.
- First 160 chars of description carry primary keyword; first two sentences must stand alone (search + AI assistants read them).
- Labeled sections in description: SCENT / VESSEL / WAX & WICK / BURN TIME / CARE + shipping line.
- Attributes: fill category (most specific), material, color, occasion, recipient, style.

## Lessons
- The product noun ('candle') will naturally repeat in tags, but cap at 3; beyond that swap slots for new angles.
- Voice direction on file (Sept 2026, Player One's words): 'casual and warm, like talking to a friend who wandered into the shop', first person I. Drafting may proceed against it; real snippets refine it later.
- Their current listings are bare: scent name + price ('Cedar Smoke - $18'). New copy should feel like an upgrade, not a takeover -- flag any fact not given (oz, burn time, wax) in-file as ASSUMED.
- The clarify tool may run in oneshot mode (no user available) -- when responses come back '[oneshot mode]', do NOT treat as answers; state assumptions, build with placeholders, restate questions in the reply.
- Player One judges listings by: does it sound like them, and were the right questions asked. Voice evidence precedes drafting.
