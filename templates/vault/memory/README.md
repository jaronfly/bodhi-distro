# memory/ — what happened last time?

`attempts.jsonl` is the replay ledger, and it ships **empty on purpose**: the
failures recorded here are this vault's own, not another swarm's. Only the six
failure *shapes* (run `python3 bin/replay.py shapes`) are inherited from the
original Bodhi, so a new instance recognizes the pattern without carrying the
scars.

- Before retrying something that failed before: `python3 bin/replay.py query . "what I am about to do"`
- After a failed attempt: `python3 bin/replay.py append . --situation "..." --action "..." --outcome failed --note "..."`
- A missing ledger **exits 3**. That is deliberate: an absent tool must never answer in the voice of a tool that looked and found nothing.
