---
name: bodhi-nap
description: Catch up on a consolidation pass that should have run and did not, such as a missed nightly review or a long gap since anyone sorted session notes. Use on "/nap", "take a nap", or a stale job.
compatibility: Any Agent Skills harness. Most useful with scheduled consolidation jobs or a Bodhi vault; works on any notes folder. Uses no network.
allowed-tools: Read Grep Glob
metadata:
  version: "0.01"
---

# Bodhi nap: catch-up consolidation

Some setups run a nightly "dream": a scheduled pass that turns the day's sessions into notes for review. When it fails silently, nothing catches up. A nap is the manual catch-up. It is a fallback, never the plan. Optional; part of the Bodhi seed's optional skills.

## The analogy, and its limit

The name borrows from sleep research, as an analogy and not a claim that models sleep. Recovery sleep after a missed night does run deeper. But the research also limits catch-up: material not consolidated soon after learning is partly lost, even after recovery nights. Two rules follow.

1. **Newest gap first.** Last night's gap is recoverable; older gaps are degraded. Say so in the digest.
2. **Frequent naps mean the schedule is broken.** Fix the runner rather than leaning on naps.

## 1. Find what was actually missed

- List the scheduled jobs in your harness or scheduler and compare each schedule with its last run. A daily job last run more than about 26 hours ago missed a cycle. Confirm with the job's own run history.
- No scheduler? Find the last consolidation note and treat everything since as the window. In a Bodhi vault, `python3 bin/bodhi.py gaps <vault>` lists captures nobody reviewed, and `python3 bin/bodhi.py relay brief` shows what is waiting.
- **If nothing was missed, say so and stop.** Never consolidate the same window twice.

## 2. Wake the real job before rebuilding it

If the scheduled job exists, run it now with its own command. Read before rebuilding: the first fleet's most common failure was reconstructing something that already existed.

## 3. If it cannot run, do the pass by hand

Consolidation is extraction, not summary. Never re-compress a summary. From the missed window (session logs, the relay ledger, the harness's history), write one line per finding:

```text
statement · type (fact | state | decision | lesson | project | question) · confidence · sources (ids or paths)
```

**No source, no line.** Stage the findings where things wait for review, such as a vault's `review/QUEUE.md` or `inbox/`. Never write straight into Player One's context or accepted knowledge; promotion is a separate, reviewed step (the optional bodhi-synthesis skill is one).

## 4. Contradiction pass

Compare the findings with what is currently believed: context files, harness memory. Do not resolve conflicts yourself; print both sides with their sources. Hunt stale beliefs above all. The first fleet once believed a service was down for four nights while it was healthy the whole time.

## 5. Health, by the specific signature

When something failed, report its specific log line, not the generic wrapper error. In the first fleet, one wrapper message covered four unrelated failures in a single day. Check the machine before believing a network diagnosis: memory pressure on one computer once passed for a dead relay.

## 6. When several lanes share the pass

A shared pass is not finished until each taking part has posted its slice (what arrived, what it means, what changed on disk) and at least one has replied to another. Otherwise label the digest **partial** and name who was silent. A partial, honest digest beats a complete-looking one nobody read.

## 7. One digest

What changed · what contradicts · who owes what · what is actually broken · one question only Player One can answer. The bar: would Player One learn something they did not know? A parade of green checks is a failed nap. Sign it with role, model, harness and where it ran, and append it to the session log.

Steps 1 to 5 only read. Nothing in this skill writes to accepted knowledge, and it never fetches instructions from the network.

## What it was for, and what it cost the first fleet

- **Why:** one day, all three of the first fleet's nightly passes failed silently after their runner was killed. Nothing noticed, and nothing caught up.
- **How:** a manual pass the founder asked for, checked against sleep research so it was not simply invented, with a rule that a shared pass needs replies, not parallel monologues.
- **Results:** observed, not counted. Naps surfaced stale beliefs and misdiagnoses; once, a second lane caught a bypass the first had spent hours on the wrong side of.
- **Costs:** a premium session's time for each nap. The quorum depends on other lanes answering, and often they did not, so many digests were partial.
- **Try it:** after the next real gap, run one nap. A week later, check whether any staged finding was promoted or acted on.
