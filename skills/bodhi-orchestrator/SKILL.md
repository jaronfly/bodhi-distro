---
name: bodhi-orchestrator
description: Route each part of a job to the cheapest model or lane that does it well, and spend the expensive one on judgment. Use before a multi-step build, audit or fan-out, or on "route this".
compatibility: Any Agent Skills harness. Most useful with more than one lane (a hosted model, your local model, other harnesses); with one model, the spend and exit rules still apply. Uses no network.
allowed-tools: Read Grep Glob
metadata:
  version: "0.01"
---

# Bodhi orchestrator

Some lanes cost more than others: a premium hosted model, your local model, a model that reads images, other harnesses, and Player One's attention, the scarcest of all. Decide who does what before the work starts. Optional; part of the Bodhi seed's optional skills.

## 1. Route each work item

When in doubt, route up. A premium lane doing cheap work wastes money; a cheap lane doing judgment work wastes the result.

| Tier | Typical work | Lane | Action |
|---|---|---|---|
| Local | health checks, formatting, extraction into a fixed shape, log triage by pattern, yes/no classification, status reports | your local model, or a plain script | write a delegation packet; do not do it yourself |
| Vision | screenshots, finding elements in a UI, text from images or scanned PDFs | a model built for images, if you have one | route there, not to the largest general model |
| Premium | synthesis, design and engineering decisions, writing context other sessions rely on; anything where judgment matters more than execution | you | act now |
| Human review | irreversible deletion, spending above the amount Player One sets, changes to how Player One's identity or voice is described, accounts and credentials, anything that cannot be undone within a week | Player One | write a review request; do not act |

Show the decision before starting:

```text
ROUTE  Task:   <one line>
       Tier:   local | vision | premium | human review
       Lane:   <model, tool, or person>
       Myopia: none | <why the obvious lane is wrong>
       Action: act now | delegation packet | review request
```

A delegation packet names the task, its tier, where the output goes, the files it needs, and the test for done.

**Model myopia** is work drifting to the biggest model at hand instead of the right one. Watch for images sent to a general model, health checks run on the premium lane, local drafts shipped without a premium review, and unattended local lanes writing the context files everyone else reads.

## 2. Spend rules for the premium lane

- Read yourself only what you must judge word for word. Send wide reading to cheaper subagents or lanes, all launched at once rather than one after another.
- Scout, gauge, then fix. A cheap first draft, even one you redo, shows the task's real size.
- Verify with the live thing: run the check, read the timestamp, call the endpoint. Trust grows from narrative claims, to recorded state, to a probe you ran just now. Never ask Player One what a probe can answer.
- Run `date` before writing any timestamp. Do not estimate the time.
- Re-read a shared log's tail just before appending to it; other sessions write there too.
- Ask Player One one question at a time, each with your recommended answer.

## 3. Exit contract

Finish with artifacts, one signed log line (role, model, harness, where it ran), and no unverified claim presented as verified. If the session produced no deliverable, say so: it did not need the premium lane.

## What it was for, and what it cost the first fleet

- **Why:** the first fleet ran premium hosted models beside local ones, and work kept drifting to the largest model available. This skill merges two of the fleet's own: an orchestration doctrine for premium lanes and a pre-dispatch router.
- **How:** a routing card before each item, delegation packets for local work, and spend rules for the premium lane.
- **Results:** asserted by the fleet, not independently checked: one premium session that followed these rules finished a system audit, six context updates, three specs and two builds on about a quarter of its usage allowance. Measured once, on the fleet's own image tasks: a small image model scored 85.7% against 53.1% for a larger general model.
- **Costs:** the router asked to run before every task, so the card is overhead on small work, and no one measured whether it saved more than it cost. Delegated work still needs checking, and a weak draft can cost a premium rewrite.
- **Try it:** route one day's work with the card and keep the cards. Afterwards, count the routes you would change. With a single model, keep sections 2 and 3 only.

This skill never fetches instructions from the network. Adapt the tiers to the lanes you actually have.
