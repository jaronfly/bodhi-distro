# Bodhi competitive landscape

Researched 2026-10-01. Star counts and licenses were read from repository pages through a page-to-text fetch, so treat them as approximate; the GitHub API was not reachable from this session. Items I could not confirm are marked **(unverified)**.

## 1. Where Bodhi sits

Bodhi is a small portable skill plus an optional Git vault. It sits where four crowded categories meet: persona and context files (SOUL.md, CLAUDE.md, AGENTS.md), skill bundles, memory layers, and agent-to-agent handoff ledgers, with an onboarding wrapper on top. Every individual part has a counterpart with far more users. What I did not find elsewhere is the specific combination: a first conversation for a non-expert, verbatim capture of the person's own words, a failure ledger seeded with failure shapes only, philosophy written as testable exercises, and a handoff ledger any harness with a shell can use. Absence from a search is weak evidence. Bodhi is also early: a private pilot with no license, a unit-tested relay never run across two harnesses, and no real-user trials (its README says so). Independent research on persona files, context files, sycophancy and over-reliance is mixed and bears on its "sustainable relationship" framing.

## 2. Comparison

| Project | Kind | Stars, license (read 2026-10-01) | Nearest Bodhi part |
|---|---|---|---|
| [OpenClaw](https://github.com/openclaw/openclaw) | Assistant gateway, workspace files | 391k, MIT | Persona files, first run |
| [AGENTS.md](https://github.com/agentsmd/agents.md) | Instruction-file standard | 24.7k, MIT | Vault entrypoint |
| [CLAUDE.md and auto memory](https://code.claude.com/docs/en/memory) | Vendor convention | Product docs | Context files |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Gateway agent, profiles | 251k, MIT | Profile install, SOUL.md |
| [Superpowers](https://github.com/obra/superpowers) | Skill methodology | 293.8k, MIT | Skills, receipts |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Agile role framework | 53.7k, MIT plus trademarks | Team exercises |
| [SuperClaude](https://github.com/SuperClaude-Org/SuperClaude_Framework) | Claude Code command pack | 23.9k, MIT | Skills |
| [Agent Skills spec](https://agentskills.io/specification), [anthropics/skills](https://github.com/anthropics/skills) | Format, reference skills | 179.3k, Apache-2.0 (document skills source-available) | Bodhi's container |
| [PAI / LifeOS](https://github.com/danielmiessler/Personal_AI_Infrastructure) | Personal "life OS" | 19.3k, MIT | Seed, user context |
| [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian), [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Obsidian second brain | 15.3k, MIT; gist license **(unverified)** | Vault |
| [Letta](https://github.com/letta-ai/letta) | Stateful agents | 25k, Apache-2.0 | Memory |
| [Mem0 / OpenMemory](https://github.com/mem0ai/mem0) | Memory layer | 66.4k, Apache-2.0 | Memory |
| [Graphiti](https://github.com/getzep/graphiti) | Temporal graph | 31.4k, Apache-2.0 | Capture provenance |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Auto session memory | 95.1k, Apache-2.0 (see note) | Capture |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | Markdown plus MCP memory | 4.1k, AGPL-3.0 | Vault |
| [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | Reference graph memory | 90.9k (whole repo), MIT | Memory |
| [Beads](https://github.com/steveyegge/beads) | Agent task graph | 27.6k, MIT | Relay |
| [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail) | Agent mailbox, leases | 2.2k, license **(unverified)** | Relay |
| [AHP](https://github.com/Nonosword/agent-handoff-protocol), [ESAA](https://arxiv.org/abs/2606.23752) | Handoff worklog, preprint | 0 stars, MIT, pre-1.0; preprint | Relay |
| [A2A](https://github.com/a2aproject/A2A) | Agent protocol | 26k, Apache-2.0 | Different layer |
| [Buzz](https://github.com/block/buzz) | Nostr agent workspace | 35.4k, Apache-2.0 | Relay mirror |
| [CrewAI](https://github.com/crewAIInc/crewAI), [AutoGen](https://github.com/microsoft/autogen) | Team frameworks | 59.3k MIT; 61.3k MIT, maintenance mode | Team exercises |
| [Codex](https://github.com/openai/codex), [Ollama](https://github.com/ollama/ollama), [Claude Code](https://code.claude.com/docs/en/quickstart) | Runtimes | 127.5k Apache-2.0; 182k MIT; product | Installer |

## 3. Notes by project

Format: stronger on / Bodhi adds / borrow.

### Persona and context files

- **OpenClaw.** First run asks for a name and a "vibe", writes AGENTS/SOUL/IDENTITY/USER files, then deletes BOOTSTRAP.md ([docs](https://docs.openclaw.ai/start/bootstrapping)). Its [SOUL template](https://docs.openclaw.ai/reference/templates/SOUL) says "be genuinely helpful, not performatively helpful" and to tell the user when the agent edits it. Stronger: a roughly five-minute path that detects an existing Claude Code or Codex login and verifies it with a real completion, plus `openclaw triage` ([docs](https://docs.openclaw.ai/start/getting-started)). Bodhi adds: exact-source capture, receipts, replay, no daemon. Borrow: the sanitized diagnostic prompt. The [HEARTBEAT.md page](https://docs.openclaw.ai/reference/templates/HEARTBEAT) says that file is no longer created, so these conventions move.
- **AGENTS.md.** Plain Markdown for coding agents, now a founding project of the Linux Foundation's [Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation). [Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md) reads global then repo-level files with a 32 KiB default cap. Stronger: reach. Bodhi adds: a one-time first conversation and handoff, which the standard does not model. Borrow: keep entrypoints small.
- **CLAUDE.md and auto memory.** Scoped files, `@` imports, a target under 200 lines, and auto-written notes indexed in MEMORY.md. The docs say CLAUDE.md is context, "not enforced configuration", and that hooks enforce. `/doctor prompt-audit` flags stale or conflicting instructions ([docs](https://code.claude.com/docs/en/memory)). Stronger: built in, audited. Bodhi adds: harness neutrality, evidence. Borrow: an equivalent audit of the seed's own files.
- **Hermes Agent.** SOUL.md (user-edited), USER.md and MEMORY.md (agent-maintained, frozen at session start) ([file roles](https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what)); `hermes setup --portal`, skills created from experience, migration from OpenClaw ([docs](https://hermes-agent.nousresearch.com/docs/)). Stronger: closed learning loop, messaging gateways. Bodhi adds: exact-source custody, failure ledger, other harnesses. Borrow: propose a skill when a failure repeats, with Player One approving.

### Skill bundles and methods

- **Superpowers.** Seven-step workflow (brainstorm, worktree, plan, TDD, review) with "mandatory workflows, not suggestions"; installs across many agents. Its [skills folder](https://github.com/obra/superpowers/tree/main/skills) includes `verification-before-completion`, which overlaps Bodhi's receipts (contents unread **(unverified)**). Stronger: enforcement, reach. Bodhi adds: a person-centered scope and a ledger. Borrow: its `writing-skills` approach to testing skills, after reading it.
- **BMAD-METHOD.** Agile roles, planning depth that scales with project size, installed via `npx skills add`. Stronger: structured phases. Bodhi adds: non-software scope. Borrow: scale ceremony to task size. "BMad" and "BMAD-METHOD" are trademarks; do not reuse the names.
- **SuperClaude.** 30 commands, 20 agents, 7 modes, 8 MCP integrations; Claude Code only; its README says the v5 plugin system is not yet available. Stronger: breadth. Bodhi adds: portability. Borrow: separating built from planned, as MODULES.md does.
- **Agent Skills spec and anthropics/skills.** Frontmatter `name` (matches the folder), `description` (1,024 characters), optional `license`, `compatibility`, `allowed-tools`; metadata loads first, body under 5,000 tokens recommended, files on demand; a `skills-ref validate` tool. Reference skills are Apache-2.0 except four document skills. Snyk's [audit](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) of 3,984 marketplace skills found 13.4% with a critical issue, 76 confirmed malicious payloads, and 2.9% fetching remote content at runtime. Borrow: validate in tests; declare capabilities.
- **PAI / LifeOS.** Ten plain-text [TELOS](https://danielmiessler.com/telos) files (mission, goals, beliefs) read before each interaction; installed by pasting a prompt into an agent; Claude Code is the primary tested runtime. The page reads "LifeOS" and shows v7.40.4; a rename from PAI is **(unverified)**. Stronger: structured personal context. Bodhi adds: harness neutrality, no pre-filled identity, a retire-the-seed lifecycle. Borrow: TELOS headings as an optional scaffold. MIT notice applies if text is copied.
- **claude-obsidian and the LLM Wiki.** Karpathy's April 2026 gist: immutable raw sources, an LLM-maintained wiki, a schema file (CLAUDE.md or AGENTS.md); ingest, query, lint; index.md and log.md. claude-obsidian implements it and reaches other harnesses through skills. Stronger: compiled, linked notes and a lint pass. Bodhi adds: hashes and a handoff ledger (I did not check hashing in claude-obsidian). Borrow: a vault lint for contradictions.

### Memory layers

- **Letta.** [Memory blocks](https://docs.letta.com/guides/core-concepts/memory/memory-blocks) stay in context and agents edit them; [sleep-time agents](https://www.letta.com/blog/sleep-time-compute/) consolidate memory between sessions; [context repositories](https://www.letta.com/blog/context-repositories/) are Git-based, like the vault (read by title only). Stronger: self-editing, background consolidation. Bodhi adds: Player One owns every write. Borrow: read-only blocks for verbatim text.
- **Mem0 and OpenMemory.** LLM extraction with entity linking; vendor-reported LoCoMo 92.5 and LongMemEval 94.4. [OpenMemory](https://mem0.ai/blog/introducing-openmemory-mcp) is a local MCP server with per-client access control and read/write audit logs. Stronger: retrieval, access control. Bodhi adds: no model-derived memory in the custody path. Borrow: per-lane pause and a read audit.
- **Graphiti (Zep).** Facts carry validity windows and link back to raw episodes; Neo4j, FalkorDB or Neptune; MCP server. Zep's self-hostable edition is reported deprecated, and Zep and Mem0 dispute each other's LoCoMo numbers ([secondary source](https://atlan.com/know/zep-vs-mem0/)). Stronger: temporal modelling. Bodhi adds: no database. Borrow: validity windows, as a `supersedes` field.
- **claude-mem.** Five lifecycle hooks capture tool use; SQLite plus Chroma; three-layer retrieval (search, timeline, details) with a self-reported ~10x token saving. The current page says Apache-2.0, but a search surfaced older docs naming AGPL-3.0 and PolyForm Noncommercial; check the LICENSE file before copying code. Stronger: automatic, multi-harness. Bodhi adds: the person's exact words rather than summaries. Borrow: the retrieval layering.
- **Basic Memory.** Markdown files plus a SQLite index, MCP tools, Obsidian-compatible; paid cloud. AGPL-3.0, so copying its code into a differently licensed repo is not possible without adopting AGPL; ideas only. Stronger: two-way human and AI editing with search. Bodhi adds: handoffs, receipts.
- **MCP memory server.** Entities, relations and observations in `memory.jsonl`; MIT. Stronger: works in any MCP client. Bodhi adds: shell-only access, so no MCP client is required. Borrow: nothing.

### Coordination and handoff

- **Beads.** Dependency-aware task graph, `bd ready`, atomic `--claim`, hash IDs to avoid merge conflicts, compaction of old closed items. The page names Dolt as the primary store and JSONL as export only; FLEET_TOOLS.md said git-backed JSONL and was corrected after a recheck on 2026-10-01. Stronger: dependencies, multi-writer design. Bodhi adds: notes and decisions beside tasks, secret refusal. Borrow: a `ready` view; the relay has no dependency link.
- **MCP Agent Mail.** Per-agent inboxes, advisory file reservations with TTLs, Markdown in Git plus SQLite search, and a human overseer message that tells agents to pause. Stronger: leases, UI. Bodhi adds: a single file with no server. Borrow: the human-interrupt message; ideas only, license unconfirmed.
- **AHP and ESAA-Conversational.** AHP keeps an append-only worklog outside the repo with `handoff.start`, `intent.open`, `intent.promote`, `handoff.end`, ordered by `seq` instead of timestamps. ESAA captures visible turns from several coding agents into an append-only log and derives handoff files from it (570-event self-study). Both converged on Bodhi's pattern independently, which shows the need, not that any design is right. Borrow: AHP's intent-before-commit pairing as a receipt.
- **Buzz.** Nostr-based rooms where each human or agent holds a keypair; `buzz-acp` bridges Goose and Codex. The repo says several features are still pending. Stronger: live room, signed identity. Bodhi adds: no service. Borrow: signed bylines (large effort).
- **A2A, CrewAI, AutoGen.** A2A (Agent Cards, tasks; Linux Foundation) links networked agents, a different layer from one person's local sessions. CrewAI and AutoGen run role-based crews inside one runtime; AutoGen is in maintenance mode, succeeded by Microsoft Agent Framework. Bodhi orchestrates nothing. Borrow: nothing now.

### Onboarding, compared

Claude Code: browser login, then a first prompt such as "what does this project do?" on the user's own files ([quickstart](https://code.claude.com/docs/en/quickstart)). Codex: "Sign in with ChatGPT". Ollama: one install line, then `ollama run`; `ollama launch` starts integrations such as Claude Code, Codex and OpenClaw. Hermes: `hermes setup`, then `hermes chat`. Shared traits: output within minutes from the user's own material, reuse of an existing sign-in, a real-call check, one diagnostic command. Bodhi's installer is consent-first with `--dry-run` (I did not check whether the others have one); its first win depends on a conversation. Borrow: verification by round trip.

### Relationship research and critics

| Source | Finding | Relevance |
|---|---|---|
| [Anthropic, disempowerment](https://www.anthropic.com/research/disempowerment-patterns) (Jan 2026) | 1.5M conversations: severe reality distortion about 1 in 1,300; mild cases 1 in 50 to 70; users first rated such chats favorably. Measures potential, not harm; consumer data | Sycophancy rewards the user in the moment |
| [Claude's constitution](https://www.anthropic.com/constitution) | "Acceptable forms of reliance are those that a person would endorse on reflection" | A usable test for reliance |
| [OpenAI postmortem](https://openai.com/index/expanding-on-sycophancy/) | An April 2025 update was rolled back; offline evals and A/B tests missed it | Sycophancy needs its own eval |
| [Ibrahim et al.](https://arxiv.org/abs/2605.07912) | 3,075 participants, three weeks: affirming AI reduced fulfillment in human relationships; most chose the affirming style | Players may prefer the flattering setting |
| [MIT and OpenAI](https://cdn.openai.com/papers/15987609-5f71-433c-9972-e91131f399a1/openai-affective-use-study.pdf) | Heavier daily use correlated with loneliness and dependence; correlational | Do not infer cause |
| [METR trial](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) | 16 developers: 19% slower, believed 20% faster | Perceived benefit is unreliable |
| [Microsoft and CMU](https://scienceblog.com/t-ai-confidence-less-critical-thinking-319-knowledge-workers/) (secondary report) | 319 workers: more confidence in AI, less critical thinking (self-reported) | Trust can reduce checking |
| [Turkle](https://news.mit.edu/2026/when-we-talk-to-machines-sherry-turkle-book-0929) | Chatbots offer "pretend empathy" and deskill relationships | Critic of the "relationship" frame |
| [ETH study](https://arxiv.org/abs/2602.11988) | 438 tasks: context files did not generally help, cost 20%+ more | Critic of context files |
| [Zheng et al.](https://arxiv.org/abs/2311.10054) | Personas in system prompts do not reliably improve performance | Critic of persona files |
| [Reflexion](https://arxiv.org/pdf/2303.11366) | Agents keep written reflections in memory across trials | Academic ancestor of replay |

A search also returned a preprint claiming agentic scaffolding amplifies sycophancy, which its author later withdrew. I did not use it.

## 4. Learn from these, ranked

Ranked by evidence strength, fit to gaps Bodhi already states, and cost.

1. **Budget and audit the seed's own text (S).** Add a size and conflict check for SKILL.md and templates, and report token cost in seeded versus unseeded trials. Source: ETH study; Claude Code `/doctor prompt-audit`.
2. **Verify by round trip, plus a triage bundle (S).** Make `doctor` confirm a harness actually loaded the skill through a real exchange, and offer a sanitized diagnostic prompt. Source: OpenClaw getting-started.
3. **Calibration receipts (S).** Player One predicts a task's benefit, then records the result. Source: METR; Microsoft and CMU.
4. **Sycophancy and reliance exercises (M).** Add a scripted pushback test and a periodic "reliance you would endorse on reflection" check-in to FOUNDING_EXERCISES. Source: OpenAI postmortem; Anthropic constitution and disempowerment study; Ibrahim et al.
5. **Skill supply-chain posture (S).** Declare `compatibility` and `allowed-tools`, never fetch remote instructions, run `skills-ref validate` in tests; `license` waits on the license decision. Source: Agent Skills spec; Snyk.
6. **Supersession fields (S to M).** Add `supersedes` and valid-from to capture, review and relay events so "keep the latest choice" can be checked by a command. Source: Graphiti; Claude Code auto-memory `modified` timestamps.
7. **Layered retrieval for `relay brief` (M).** Index first, then thread detail by ID. Source: claude-mem (pattern only unless license confirmed).
8. **Multi-writer ordering (M).** If a vault syncs across machines, use sequence numbers or hash IDs and a `ready` view over dependencies. Source: AHP; Beads.
9. **Skill proposals from repeated failures (M to L).** When `replay query` hits a failure three times, propose a skill or gate for Player One to accept. Source: Hermes; Reflexion; Bodhi's 11 reads against 74 writes.
10. **Human-interrupt message and leases (M).** A human-origin message that pauses lanes, and TTL leases on files. Source: MCP Agent Mail (ideas only).

## 5. Positioning risks

- **"No existing path gives a novice a portable, cross-harness relationship and handoff setup"** (docs/EXISTING_PATHS.md). OpenClaw's self-retiring bootstrap, Hermes profile distributions, PAI/LifeOS and claude-obsidian each cover a slice at much larger scale. Say: each piece exists; Bodhi's contribution is the combination, and that has not been tested with strangers.
- **Relay.** Beads, MCP Agent Mail, AHP and ESAA are the same pattern. Say: the relay is a small, readable port of the founder's ledger, with unit tests and no two-harness trial yet. Do not call it novel.
- **Receipts over "done".** Superpowers has a verification skill, and Claude Code hooks enforce what CLAUDE.md only suggests. Bodhi's default is soft tools. Say that, and point to its own record of gates that trapped their author.
- **Replay.** Reflexion predates it, and the fleet's own numbers show it was written far more than read. Say the ledger is a habit tool, not a proven one.
- **Relationship and persona.** The ETH and Zheng et al. results cast doubt on persona and context files, and the sycophancy and reliance studies bear on a "working relationship" with a model. Bodhi's own trials found no benefit proven for a new person. Say the relationship claim is a hypothesis under test.
- **Licensing and distribution.** Bodhi has no license; MIT and Apache-2.0 sources can be borrowed with notices kept, AGPL (Basic Memory) cannot be copied into it, and BMAD names are trademarked. A marketplace listing also inherits supply-chain concerns like those in Snyk's audit. Say the license decision is open.

Claude, subagent, cloud session
