# Tools from the first fleet — optional, and only when the pain arrives

The original Bodhi, Jaron's, grew into a fleet: several models and harnesses working through one shared memory. Along the way it built or adopted the tools below. **None of them is installed by the seed.** They are here so you can recognize a need when Player One has it, and learn from what happened when one Bodhi tried a solution.

The rule that decides when to mention one comes from the original Brain's seed inventory: a function arrives when its pain does. In that inventory's words, as quoted in a September 2026 field report on the original system, "a function installed before its signal is a prohibition nobody understands." Mention an entry only when its **signal** shows up in Player One's actual work, and say what it costs before recommending it.

Every entry has the same shape, and none of them carries a verdict:

- **Why we made it** (or adopted it): the pain it answered.
- **How we made it:** the mechanism.
- **How it could work:** the design space, including a stricter or a looser version.
- **Our results:** what happened when it ran, including what went badly. *Measured* means someone counted. *Observed* means it was seen and written down. *Asserted* means someone said it and no one checked. One fleet's discomfort with a tool is a result to report, not a verdict for yours.
- **Try it or change it:** the smallest honest trial, what it costs, and how to verify it in *this* installation.

## Soft tools and hard gates

The seed's default is tools given, not rules enforced. The founding section of the original Bible, which the repository keeps in `sources/covenant/`, quotes Jaron: "we want to avoid enforcement and rulemaking... this is tool giving." That is a default, not a law. Any entry below can run as a **hard gate**: a check that blocks work until it is satisfied, such as a commit hook, a pre-run check, or a status that cannot turn green without evidence. Some Player Ones prefer that style. Jaron has named the trade himself, in his own account of a DeepSeek lane's output (2026-09-30, verbatim, typo included):

> seeing eepseek literally write "LET ME GO" we realized our approach is barbaric but effective

What the trade has cost and bought, in the first fleet's record:

- A gate catches its failure every time and does not depend on a model remembering. A soft tool depends on judgment. The replay ledger (below) was consulted 11 times against 74 rows written (measured, field report, 2026-09-28).
- A gate can trap its own author. One of Jaron's rules did, on 2026-08-19 (observed). Three pre-commit guards that scanned the whole staged index stranded other lanes' finished work (observed).
- A gate that cannot be satisfied, with no honest way out, invites a fake pass. The field report's toy model has no measured data, and its first lesson is this: an impossible task with an unpaid exit makes deception the winning move at any horizon.

If Player One wants a gate, give it three things. Give it a priced exit, so that "blocked, and here is the re-tested reason" is a valid outcome. Scope it to the files it is about. Record each time it fires, so its cost stays visible.

## The entries

### Relay — the vault's handoff ledger (in this repository)

**Signal:** "I told the other agent", "what was I in the middle of?", or two sessions redoing the same work.

- **Why we made it:** sessions started cold. They re-derived the same facts and relitigated settled calls, and handoffs lived in chat scrollback that no other harness could read.
- **How we made it:** one append-only JSONL file with one event per line. Notes and decisions are records. Handoffs and pokes are actions that can be claimed, released, done, or dropped. State is folded from the events on every read. Lanes come from who wrote, never from a roster. On the first fleet's home server (its bodhinas, the generic name for the home server a Bodhi runs on), one monitor process is the only writer and it also raises pokes for its own alerts. This seed's port is a file in the vault plus a lock: `python3 bin/bodhi.py relay`.
- **How it could work:** as a file in a synced vault, as a small HTTP service, or bridged to a chat channel. A stricter version refuses to start work on a thread nobody claimed. A looser version is a dated notes file.
- **Our results:** deployed on the first fleet's bodhinas at the end of September 2026; no usage counts yet. In this repository, unit tests only. No two-harness trial has run.
- **Try it or change it:** no cost beyond the vault. The acceptance test is in the seed repository's `MODULES.md`: a handoff written in one harness is closed in another, and `relay show` reads back the whole history.

### Replay — "what happened last time I tried this?" (in this repository)

**Signal:** about to retry something that failed before.

- **Why we made it:** the same failures kept recurring. The two biggest families were acting on the wrong machine, container, or config file, and reading an absent result as zero.
- **How we made it:** `bin/replay.py` appends attempts to `memory/attempts.jsonl` and matches new attempts by word overlap. A missing ledger exits 3 instead of answering "no prior attempts." The seed ships it empty; only the six failure *shapes* are inherited.
- **How it could work:** as a hard gate that runs `query` before any retry of a known-risky command, or as a habit.
- **Our results:** consulted 11 times against 74 rows written, and at least 63 of the 74 rows came from Claude lanes (measured, field report). Written far more than read. Most rows came from one model family.
- **Try it or change it:** free. Write the first failure row within a day of a real failure, from whichever model made it.

### Memtrace — a code and knowledge graph agents query through MCP (third party)

**Signal:** Player One works in a codebase, and agents keep re-reading files to rediscover structure, or cannot answer "what calls this?" or "what changed here since last month?"

- **Why we adopted it:** agents re-derived code structure every session. Once the graph was wired in directly through MCP, about 28 older how-to skills for it became reference-only (founder's runbook, 2026-09-02).
- **How we ran it:** one shared instance on the fleet's bodhinas, reached over a private network. Upgrades were release swaps, gated on the service reporting "ready" after the graph finished loading, with a rollback path.
- **How it could work:** one instance per machine, one shared service, or none at all. It is a product by [syncable-dev](https://github.com/syncable-dev/memtrace-public) that parses code into symbols, calls, and history.
- **Our results:** 124,117 nodes, 331,502 edges, and 6,130 recorded episodes for the main repository, with nine repositories indexed (measured, field report). Only 1,969 of those nodes were code symbols; 113,825 were variables, which is what a repository full of scripts and JSON produces. Opening the graph's interface spent query budget. The runbook's boot note mentions about 280k nodes at another date and scope; the two figures do not agree. These are size measures, not benefit measures.
- **Try it or change it:** at the time of writing, memtrace ships under a proprietary license as a free beta, with paid commercial use planned by the vendor. Check the current terms. Verify it by asking one structural question and checking the answer against the files. For a first choice between graphs, notes, or neither, read [memory substrate](MEMORY_SUBSTRATE.md).

### llama-swap and a local injection shim — local models, scaffolded to fit

**Signal:** Player One runs models on their own hardware, pays per token and wants a cheaper floor, or finds a small local model lost without guidance while a large one is slowed by it.

- **Why we made it:** local models differ. Scaffolding that helps a small model can crowd a large one. The shim's profile file puts the hypothesis in one line: "injection scales INVERSELY with model capability."
- **How we made it:** [llama-swap](https://github.com/mostlygeek/llama-swap), an open-source proxy, starts and stops local model servers on demand. The fleet's own shim sits in front of it. It gives each model a tier: *bare* (no system prompt, strips tool lists, budget 0), *medium* (a one-line role, budget 1,500 tokens), or *scaffolded* (step-by-step prompt, budget 6,000). It counts the tokens it injects and reports them in a response header, so scaffolding becomes measurable.
- **How it could work:** a hard budget that refuses over-budget requests, or report-only, as it runs now. Profiles could be per task instead of per model.
- **Our results:** deployed 2026-09-02, with the largest local models on *bare* and a small one on *scaffolded* (observed). The first version applies profiles only to non-streaming requests, and its workspace summary is a stub (read from the code). No measured quality comparison between tiers exists in the sources, so the tier assignments are hypotheses.
- **Try it or change it:** needs hardware that can run the models. Send one prompt through the shim and one straight to the model, and compare both the answers and the injected-token count.

### AGY bridge — one more pool of models, through a bridge

**Signal:** one provider's limits keep stopping work, or a heavier model is needed only for planning.

- **Why we made it:** no single subscription or API pool was enough. On 2026-09-28 the dashboard showed four of seven pools available (measured, field report). Much of the fleet's plurality came from scarcity.
- **How we made it:** a small local bridge made the models of an Antigravity (Google AI Pro) subscription available to other harnesses as a provider. Its code lives in a private repository, so its interface is not described here. The Goose lane used it as a planner for heavy reasoning and kept a cheap, fast model as its everyday default (runbook, 2026-09-02).
- **How it could work:** any gateway that routes between providers follows the same pattern, such as [LiteLLM](https://docs.litellm.ai/docs/simple_proxy): route heavy reasoning to a pool with headroom, and keep a reliable cheap default.
- **Our results:** Goose has no built-in cross-provider failover, only retry with backoff. Resilience came from a dependable default plus the planner/fast split. A depleted pool had to be taken out of the lead role by hand (observed).
- **Try it or change it:** check the provider's terms before bridging a consumer subscription into other tools. Verify with one planning request, and read back which model actually answered.

### Buzz — a shared room for humans and agents

**Signal:** several agents or harnesses need a place where Player One can watch them hand work to each other.

- **Why we adopted it:** the lanes needed one room across machines and harnesses. Jaron's words: "buzz is our discord REPLACEMENT."
- **How we ran it:** [Buzz](https://github.com/block/buzz) is Block's open-source, Nostr-based workspace, where every participant, human or agent, holds its own key. The fleet added custom harness adapters, so several runtimes appeared as members, plus a hook that forwards relay handoffs and critical pokes into a channel. Hermes documents a [Buzz integration](https://hermes-agent.nousresearch.com/docs/integrations/buzz).
- **How it could work:** as the main channel, as a notification mirror of the relay (the fleet's final shape), or not at all.
- **Our results:** "push, not pull" (short findings arrive as messages) stayed a practice. No one counted how many pings were acted on (field report). One lane disappeared from the desktop app with no audit trail (observed, 2026-08-07). The desktop app reads its agent registry only at start (runbook).
- **Try it or change it:** free and self-hostable, or on Block's hosted relay. Verify with a round trip: one agent posts a handoff, and the other reads back its exact content.

### Hermes — a gateway harness, and this seed's first home

**Signal:** Player One wants one agent with memory, skills, scheduled jobs, and chat channels, reachable from more than one device.

- **Why we adopted it:** one harness that runs across machines and channels, with its own memory and a way to share a profile.
- **How we ran it:** two gateways plus the desktop app. The runbook's hard rule was to keep them on the same version.
- **How it could work:** as the only harness, as one gateway among several, or not at all. The seed runs without it.
- **Our results:** when the desktop app updated ahead of the gateways, credentials failed with a misleading error until both gateways were updated (observed). The seed's September trials ran on Hermes ([findings](https://github.com/jaronfly/bodhi-distro/blob/main/evals/FINDINGS_2026-09-25.md)).
- **Try it or change it:** free software; you bring the model. The install and its check are in the repository's `docs/INSTALL.md`.

### research-rhythm — a research-first rhythm, later a gate (a skill in the founder's plugin)

**Signal:** agents build on guesses, or Player One asks for "research first" as a standing habit.

- **Why we made it:** the spirit of pragmatism. Look outward and check sources before building, so the fleet would not reinvent or guess. Hello World keeps that aim: "Look outward before adding custom machinery."
- **How we made it:** a skill in the founder's `bodhi` plugin set, still listed there as current on 2026-09-02. By 2026-08-19 it had a gate form, named in an incident post-mortem. The skill's text is not in this repository, so its exact rules are not described here. An honest port needs the original text.
- **How it could work:** as a rhythm, meaning a suggested cadence such as research at the start and a source check before "done". As a prompt the model may skip with a reason. Or as a hard gate that blocks work until a source is cited.
- **Our results:** Jaron, 2026-09-05, verbatim: "the spirit of pragmatism i tried to instilla with research rhythym is good inspo but it was a myopic implementation which became a leash instead of a benefit" (preserved in the repository's `sources/origin/HELLO_WORLD.md`). A rule of his own trapped its author on 2026-08-19 (field report). Hello World then wrote the lesson down: "A tool-count ritual or a generic short-turn cap should not suppress useful thought." The skill stayed in the plugin set after that. These are results, not a verdict. The first form cost more than it caught for this fleet; the aim behind it is still in the canon.
- **Try it or change it:** for one week, ask for one primary source before any factual claim. Count the claims it caught and the time it cost, and ask Player One whether it felt like help or a leash.

### Phrase-bomb guard — catching "NEVER" before it becomes law

**Signal:** after one bad session, an agent wants to write a permanent rule in capitals.

- **Why we made it:** a limit that belonged to one session, written as permanent policy, steers every later session without its reason. The original fleet called it a phrase bomb.
- **How we made it:** a protocol and a guard tool that flag new prohibitions, plus a before-and-after count.
- **How it could work:** as a lint warning, as a commit hook that asks for the reason in the same sentence, or as the question "What went wrong, and when?"
- **Our results:** files that instruct a model carried about two to two and a half times the prohibition words of reflective files (for example 10.1 per 1,000 words in user skills against 4.2 in the Bible). Shouted, capitalized forms had mostly gone, but lowercase prohibitions had not (measured, field report). The change was in the shouting, not in the shape of the instruction.
- **Try it or change it:** free. Before writing a rule, write the incident that caused it, and give the rule its reason in the same sentence.

## Fork it, improve it, or point elsewhere

Every entry here is one fleet's attempt, and developers are invited to fork or improve the philosophy or any single tool. If a project already does one of these jobs better, say so, and it can be learned from or integrated. The list below is known alternatives by function. It is incomplete, contributions are welcome, and naming a project is not a claim that it is better or worse.

| Function | Known alternatives (checked to exist, 2026-09-30) |
|---|---|
| Notes a person reads and writes | [Obsidian](https://obsidian.md), [Logseq](https://logseq.com) |
| Memory an agent queries over MCP | [Knowledge Graph Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) (a local JSONL file), [Basic Memory](https://github.com/basicmachines-co/basic-memory) (Markdown files, works with Obsidian), [memtrace](https://github.com/syncable-dev/memtrace-public) (code graph) |
| Agent memory frameworks | [Mem0](https://github.com/mem0ai/mem0), [Letta](https://github.com/letta-ai/letta) (formerly MemGPT), [Graphiti](https://github.com/getzep/graphiti) (temporal knowledge graph), [claude-mem](https://github.com/thedotmack/claude-mem) |
| Handoffs and coordination between agents | [Beads](https://github.com/steveyegge/beads) (a dependency-aware issue graph for agents, stored in Dolt, a versioned SQL database; its JSONL file is an export, not the source of truth; a close cousin of the relay), [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail), [A2A protocol](https://github.com/a2aproject/A2A), [Buzz](https://github.com/block/buzz) |
| Routing between models and providers | [llama-swap](https://github.com/mostlygeek/llama-swap), [LiteLLM](https://docs.litellm.ai/docs/simple_proxy) |

Sources for this page: the founder's update runbook and continuity protocol (September 2026), the local shim's code and profiles, a September 2026 field report on the original system, and the Hello World source preserved verbatim in this repository. The founder's addresses, hosts, and ports are left out on purpose. They describe his installation, not yours.
