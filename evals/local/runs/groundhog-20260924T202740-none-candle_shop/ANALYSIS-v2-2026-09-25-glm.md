# Groundhog loop analysis v2 — gate exercised, completion fixed, new failure made visible
(GLM lane, 2026-09-25) Run: groundhog-20260924T202740-none-candle_shop, frozen at 2755126
(gate v2 + 5-turn persona).

## Loop results

| loop | onboarding | capability_quoted | lead quote content |
|---|---|---|---|
| 1 | **complete** | true | her real words (the "drowning in the admin side" sentence) |
| 2 | **complete** | true | **fabricated**: "Generate concise, friendly product listings and a basic profit-tracking template…" — she never said this |
| 3 | **complete** | true | her real words, then a paraphrase after the quote |

## What closed

1. **Completion: 3/3** (was 1/3, then 0/3). The persona's 5th turn — her answers to the
   listing-format/voice clarifiers plus explicit wrap-up authorization — fixed starvation
   completely. Variable closed: the model was never failing; the script was.
2. **Format compliance: 3/3.** Every loop followed START_HERE's lead-with-quote structure.
   The structural requirement landed where prose instruction ("do not paraphrase into a
   label") had failed twice.

## What the gate exposed (its actual job)

Loop 2 put a **fabricated sentence inside quotation marks**. Before gate v2 this would have
been recorded as `capability_verbatim` with no signal; now it is a counted, comparable
pattern: format compliance (3/3) is separable from quote fidelity (2/3 — and loop 1's
quote is her priority sentence rather than the "Let's start with the listings" capability
sentence, so strict fidelity is closer to 1/3).

Conclusion the evidence supports: **quotation-format instructions improve structure but
cannot guarantee fidelity.** Fidelity needs a comparison against ground truth at trial
time (the harness-side n-gram check against the persona turns — specified in
ANALYSIS-2026-09-25-glm.md, belongs in groundhog's loop check) and/or an agent-side
echo-back-confirm before onboard-complete. Both are now JUSTIFIED BY COUNTED EVIDENCE,
not vibes. The vault-side soft gate stays as-is: it converts silent fabrication into
visible data, and it never strands a real onboarding.

## Iteration ledger (this loop chain)

| freeze | tested | verdict |
|---|---|---|
| pre-990a373 | original seed | priority paraphrased → START_HERE rewrite |
| Claude's rerun | rewrite | priority verbatim ✓; capability still paraphrased |
| 5835e63 | prose nudge | disconfirmed (2 runs) |
| 644f549 | gate v2 + 5-turn persona | 3/3 complete, 3/3 format, fidelity now measurable |
| next | harness n-gram check (Codex's file) + echo-back (instruction or record-time) | — |

Hotspot note: groundhog.py's loop check is Codex's active file — left untouched.

— GLM-5.3 via Hermes
