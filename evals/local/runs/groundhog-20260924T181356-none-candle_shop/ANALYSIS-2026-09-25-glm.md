# Groundhog loop analysis — capability-verbatim iteration (GLM lane, 2026-09-25)

Run: `groundhog-20260924T181356-none-candle_shop` — 3 loops, gpt-oss-120b on
`<model-host>:8090`, frozen installer commit `5835e63` (carries the one-clause
capability-verbatim nudge from 5835e63's parent commit; this run TESTS that
nudge).

## Loop 1 — hypothesis DISCONFIRMED, new signal found

`loop-01-recorded-priority.json`:

- `priority_verbatim`: her real sentence, verbatim ✓ (the earlier fix holds)
- `capability_verbatim`: **a paraphrase again** — "Create on-brand candle
  listings that reflect Player One's voice and collect needed product data…"
  instead of her "Let's start with the listings. I have twelve products…".

The one-clause nudge (commit 5835e63) did not beat GPT-OSS-120B's
label-making reflex. Worse: the field is *named* `capability_verbatim` while
containing a paraphrase — the vault recorded a false claim about its own
evidence with no way to notice. "Empty is not zero" got a gate; "verbatim is
verbatim" had only an instruction.

## Loops 2–3 — did not complete onboarding, for a DEFENSIBLE reason

Both ended `pending_hello_world`. The transcripts show the model doing the
right seed behavior: after the persona's four scripted turns ran out, it asked
brand-voice follow-up questions ("Do you prefer friendly & conversational,
polished & p…") because the answers would alter the listing it would draft.
The script had no further turns, so the session ended mid-flow and
`onboard-complete` never ran.

That is not a seed failure — it is the seed's "ask a question when an answer
will alter the result" habit colliding with a fixed script. Trial-harness
suggestion (Codex's call, his harness): give the candle-shop persona one more
turn ("Answer any or all: friendly, polished…" → "Friendly, and don't worry
about the rest — go ahead and wrap up this first session.") so loops can
complete without the model having to guess that silence means "proceed".

## What shipped in response (this commit)

Structural soft gate, iteration 2:

1. `START_HERE.md`: the capability file must LEAD with the player's exact
   sentence inside quotation marks; framing follows the quote.
2. `bin/bodhi.py`: `onboard-complete` records `capability_quoted` (true/false,
   ≥8-char quoted-span detection across straight/curly/single quotes) in
   `sources/hello_world_answer.json`. Soft by design: a paraphrase is now
   VISIBLE in the evidence instead of silently wearing the verbatim name; a
   real onboarding is never stranded by it.
3. `tests/test_capability_gate.py`: 2 tests (detector unit + end-to-end
   record field for quoted vs paraphrase cases). Suite: 14/14.

## Expected next-loop signal

Next groundhog run on this frozen state should show, per loop:
`capability_quoted: true` when the model follows the lead-with-quote format,
`false` where it still labels. The paraphrase can no longer masquerade as
verbatim in the record. If loops still paraphrase at high rate, the next
smallest change is at RECORDING time (bodhi.py echoing the quoted span back
for the player's confirm), not more instruction text — instructions had their
shot.

— GLM-5.3 via Hermes, 2026-09-25
