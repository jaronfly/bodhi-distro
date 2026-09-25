#!/usr/bin/env python3
"""replay — "what happened last time I tried this?" for a Bodhi vault.

Adopted into the seed (v0.01) from the original Brain's tools/attempt_replay.py, cut
down to what a new vault needs:

  append  record an attempt: situation, action, outcome, note
  query   find earlier attempts that look like the one you are about to make
  shapes  print the failure shapes inherited from the original swarm

The vault's ledger starts EMPTY, so its failures are this Player One's own. What
is inherited is only the list of shapes, whose descriptions are copied verbatim
from the original ledger's FAMILIES table. The ledger file is created by init
(or by the first `append`).

The one behaviour that must survive the cut: a missing ledger exits 3 and says
so. It never reports "no prior attempts". A tool that is absent must not answer
in the voice of a tool that looked and found nothing.

Usage:
  python3 bin/replay.py append . --situation "publish listing" --action "..." \
      --outcome failed --note "what the next attempt needs to know"
  python3 bin/replay.py query . "publish a listing to the shop"
  python3 bin/replay.py shapes
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

LEDGER = Path("memory") / "attempts.jsonl"
OUTCOMES = ("worked", "failed", "blocked")

# Verbatim "why" strings from the original Brain's tools/attempt_replay.py FAMILIES,
# ranked there by how often they recurred (wrong-surface: 17 attempts, 8 failed;
# empty-is-not-zero: 14 attempts, 8 failed, as of 2026-09-24).
INHERITED_SHAPES = {
    "wrong-surface": "Acted on the wrong machine, container, user or config file. The most expensive recurring mistake in this system.",
    "empty-is-not-zero": "A failed or absent command returned nothing, and nothing was read as zero. Absence of a tool is never evidence about the thing it would have measured.",
    "silent-no-op": "Something reported success while producing no forward motion. An exit code describes the wrapper, not the work.",
    "premature-closure": "Called it done before proving it. Done must mean proved.",
    "inherited-unverified": "Trusted another lane's, agent's or doc's claim without re-measuring it. Delegated findings are evidence, not canon.",
    "guard-too-loose": "An idempotence or safety guard matched something it did not mean, and the real work was skipped.",
}

WORD = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with", "is", "it", "my", "i"}


def tokens(text: str) -> set:
    return {w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 1}


def ledger_path(vault: Path) -> Path:
    return vault / LEDGER


def cmd_append(args) -> int:
    path = ledger_path(args.vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "situation": args.situation, "action": args.action, "outcome": args.outcome,
           "note": args.note, "evidence": args.evidence, "by": args.by}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "appended", "ledger": str(LEDGER), "outcome": args.outcome}))
    return 0


def cmd_query(args) -> int:
    path = ledger_path(args.vault)
    if not path.exists():
        print("error: no attempt ledger at " + str(LEDGER) + ". The ledger is not set up here; "
              "that does NOT mean there are no earlier attempts.", file=sys.stderr)
        return 3
    want = tokens(args.text)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    scored = []
    for row in rows:
        key = tokens(row.get("situation", ""))
        body = tokens(row.get("action", "") + " " + row.get("note", ""))
        if want:
            score = 3.0 * len(want & key) / len(want) + len(want & body) / len(want)
            if score > 0:
                scored.append((score, row))
    scored.sort(key=lambda pair: -pair[0])
    print(json.dumps({"ledger_rows": len(rows), "matches": [row for _, row in scored[:args.limit]]},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_shapes(_args) -> int:
    for name, why in INHERITED_SHAPES.items():
        print(name + ": " + why)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    append = sub.add_parser("append")
    append.add_argument("vault", type=Path)
    append.add_argument("--situation", required=True)
    append.add_argument("--action", required=True)
    append.add_argument("--outcome", choices=OUTCOMES, required=True)
    append.add_argument("--note", default="")
    append.add_argument("--evidence", default="")
    append.add_argument("--by", default="")
    query = sub.add_parser("query")
    query.add_argument("vault", type=Path)
    query.add_argument("text")
    query.add_argument("--limit", type=int, default=5)
    sub.add_parser("shapes")
    args = parser.parse_args()
    return {"append": cmd_append, "query": cmd_query, "shapes": cmd_shapes}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

# Adopted 2026-09-25 from proposals/claude/replay/replay.py (Claude lane).
# Logic unchanged: empty ledger exits 3; failures are this vault's own;
# only the six failure-shape descriptions are inherited.
