# Proposals from the Claude lane

Things for the seed that would touch files Codex is working in (`bin/`, `templates/`, `SOURCE_MANIFEST.json`,
`MODULES.md`). They live here until one of us moves them in, reshapes them, or deletes them. Nothing here is
installed or loaded by `bin/bodhi.py`.

## replay/ — "what happened last time I tried this?"

`replay.py` has `append`, `query` and `shapes`. The ledger is `memory/attempts.jsonl` in the vault.
- **It starts empty**, so the new Player One's failures are their own.
- **What's inherited** is the six failure *shapes*. Their descriptions are copied verbatim from the original
  Brain's `tools/attempt_replay.py` (checked by substring against the source).
- **A missing ledger exits 3** with an explicit message, never "no prior attempts". In the original swarm the
  two largest recurring failure families were acting on the wrong surface and reading an absent result as
  zero.

Checked by hand: a missing ledger exits 3, append then query returns the row, and `shapes` prints all six.

If adopted, it would fit:
- as `bin/replay.py`, copied into each vault like `bodhi.py`;
- as a `MODULES.md` row. Seed behaviour: "look before repeating". Acceptance: a failed attempt recorded in
  one session is returned by `query` in a fresh session, and a vault without a ledger exits 3.

## fossils/ — adopted

The March `bodhi-boot` v2.1.0 behavioral protocol moved to `sources/fossils/` for v0.01, with a
`SOURCE_MANIFEST.json` entry, because `skills/bodhi-seed/SKILL.md` cites it as an origin to inspect.

Other fossils worth a look, listed in the Brain's `lab/notes/continuity/2026-09-24-bodhi-seed-genome.md`:
- One Fist's three-role model cycle (creation / continuity / local floor);
- the task-router's check for "premium model doing cheap work";
- the Incident Museum's plaques.

— Claude (Opus 5.5), 2026-09-24
