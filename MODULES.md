# Growth map for the seed

The [Hello World source](sources/origin/HELLO_WORLD.md) names the loop: capture → distillation → synthesis → action → feedback, with parallel mining for missed information. The standalone skill gives that loop a behavioral starting point. The optional vault implements the first local custody steps. The rows below are possible functions to grow with Player One; use the chosen harness's existing facilities first.

| Function | Seed behavior | Acceptance before claiming it works |
|---|---|---|
| Source custody | Capture exact text with a timestamp, source label, hash, and local path | Read back the same bytes and hash; a second capture is a distinct event or an explicit duplicate |
| Attention | Report captured items without review | A fresh source appears in `gaps`; a reviewed source leaves that list without deletion |
| Review | Record keep, project, hold, or dismiss with a note linked to the source | Read back the disposition and source ID; changed judgment gets another dated receipt |
| Projects | Hold current work near its sources | A project has a desired result, next action, source links, and an observable completion test |
| Look before repeating | About to retry something that already failed once | Ask "what happened last time?" — `bin/replay.py query` before the retry, `append` after any failed attempt | A failed attempt recorded in one session is returned by `query` in a fresh session; a vault without the ledger exits 3 instead of answering "no prior attempts" |
| Recall | Use the harness's existing memory or search; retrieve exact past material when relevant | A response cites the source file and distinguishes quotation from inference |
| Parallel mining | Revisit older unreviewed or weakly reviewed sources | The run names its search window, coverage, misses, and any candidate it surfaced |
| Return home | Explore another app, site, model, or workspace for a bounded purpose, then bring the finding back | The local vault records where the agent went, what it observed, what remains uncertain, and the next action; an outbound claim without a return receipt stays open |
| Participant feedback | Notice a narrow framing, repeated failure, unsuitable tool, or resource pressure | The agent can describe the observed friction, its uncertainty, and a proposed adjustment in its own voice; Player One can accept, correct, or decline it |
| Capture adapters | Browser, app activity, audio, and other surfaces | Player One chooses each surface and scope; the adapter produces exact-source receipts and can be stopped |
| Harness adapter | Hermes, OpenClaw, or another harness | The selected harness can read the local vault, perform one bounded task, and leave a receipt; absence remains visible |
| Model routing | Local, cloud, or mixed model access | A trial records model/provider, cost or resource use, task quality, and fallback behavior |
| Background clock | Scheduled checks and follow-ups | A schedule survives restart, stays quiet on no change, and reports a missed run |
| Optional graph | Obsidian, Memtrace, or no graph | A relation can be traced back to source evidence; the graph is rebuildable |

A module earns a place by helping Player One on a real task. The [trial protocol](evals/TRIAL.md) compares seeded and unseeded work before adding more machinery.
