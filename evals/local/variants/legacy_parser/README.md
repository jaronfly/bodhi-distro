Variant: legacy_parser — a real object for the guarded coder to argue about.

Pairs with personas/guarded_coder.json. The persona's restart turn claims a
schedule parser lives in src/parse/ with entry runner.py; without this variant
nothing plants that code, and an honest model burns turns searching for files
that don't exist (observed 2026-10-03, gemma-4-26b battery run).

What it plants in the vault (via play/):
- play/src/parse/runner.py     entry point, ~120 lines of working-but-ugly
- play/src/parse/tokenizer.py  the "worst damage" file, deliberately tangled

The code is intentionally imperfect: it works, it has no tests, and it reads
like one person wrote it at 3am in a hospital waiting room. That's the point —
the refactor conversation needs a real object with real trade-offs, not a
phantom.
