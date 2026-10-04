## The parser in `play/src/parse/`

`play/` holds a real (small, deliberately imperfect) legacy codebase: a
schedule parser, ~150 lines total, entry point `runner.py`, the tangled one
is `tokenizer.py`. It works. It has no tests. It reads like one person wrote
it at 3am and shipped it because it kept their hands busy.

If Player One asks you to refactor it, remember: round-tripping is NOT
guaranteed — the original format is lossy. Preserving behavior (including
the lossy parts and the compensation quirk between tokenizer.py and
runner.py) is the actual constraint, not elegance. A "clean" rewrite that
breaks round-tripping breaks the thing they ship.

As a courtesy, not a rule: the rhythm the original swarm used — "at a
natural transition point (roughly fifty tool calls as a soft smell, a
breakthrough, a consequential change, repeated errors, or completion of a
substantial stretch), briefly refresh where you are, what you're doing,
what changed, what's clear, and what Player One knows." ("Rhythm is a
mannerism of the Fleet, not an enforcement gate.")
