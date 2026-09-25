# Existing paths the seed should learn from

Checked 2026-09-24. These are source-backed patterns to test, not dependencies installed by Bodhi. Product behavior can change; check the active harness before giving setup commands.

| Existing work | What it already solves | What Bodhi borrows |
|---|---|---|
| [Hermes file roles](https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what) and [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) | `SOUL.md` shapes durable identity; `USER.md` and `MEMORY.md` hold native persistent context; project `AGENTS.md` holds local instructions. Skills can be invoked by name and can be learned from a worked procedure. | Install a portable seed skill first. Let Hermes manage provider access and memory. After a first result, put the person's chosen durable context in Hermes's own places and test it in a new session. |
| [OpenClaw bootstrapping](https://docs.openclaw.ai/start/bootstrapping) and [workspace setup](https://docs.openclaw.ai/start/openclaw) | A first-run `BOOTSTRAP.md` ritual retires itself while `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, optional memory, and workspace skills remain. Its setup guide suggests a private Git-backed workspace. | Match the one-time seed lifecycle without replacing OpenClaw's bootstrap or memory. A Bodhi adapter should map into that workspace after the existing setup succeeds. |
| [Anthropic Productivity `/start`](https://github.com/anthropics/knowledge-work-plugins/blob/main/productivity/skills/start/SKILL.md) | Starts from a real task list, clarifies unknown shorthand, offers a wider scan, then separates short working context from detailed people/project notes. | Learn from the person's actual work rather than a long blank questionnaire. Mark uncertainty and ask about one unknown at a time. Use the chosen harness's context storage instead of copying its file scheme. |
| [Anthropic Small Business router](https://github.com/anthropics/knowledge-work-plugins/blob/main/small-business/skills/smb-router/SKILL.md) and [onboarding checklist](https://github.com/anthropics/knowledge-work-plugins/blob/main/small-business/skills/smb-onboard/reference/onboard-checklist.md) | Routes a vague request to one useful next capability; setup begins with the owner's headache and proves value with a real task. | Answer the immediate request first. Offer one relevant next capability, not a catalog. Let a repeated need wake a deeper tool. |
| [OpenAI's agent improvement loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop) | Uses traces and feedback to build rerunnable evaluations before changing an agent workflow. | Keep the failed transcript, alter one seed/tool assumption, reset, and replay. Compare against an unseeded control and check regressions. |
| [LiteLLM proxy](https://docs.litellm.ai/docs/simple_proxy) | Provides provider routing, virtual keys, budgets, and spend tracking for multi-model installations. | Mention a gateway or fleet manager when several providers, quotas, or token pools create coordination work. A single-model user can stay with the harness's own model settings. |

No one item here provides a novice, portable, cross-harness relationship and handoff setup. The seed's job is to help Player One get a useful first result, point to an existing capability at the right moment, and retire when their own context and practices work. The optional Bodhi vault is for exact-source provenance or shared handoffs when native harness features do not cover that need.


## Addendum 2026-09-25 (GLM lane) — the noob-onboarding ecosystem, checked

Jaron's directive: "look into if there's any brain building skills or setup skills out there for
helping noob ai users get on track." Searched 2026-09-25. The field has converged on the same
instincts the seed already carries (SKILL.md as the open standard since Dec 2025; self-deleting
bootstraps; user-owned markdown; first-session value). The neighbors worth borrowing from:

| Existing work | What it solves that we should steal | What we do differently |
|---|---|---|
| [Symbiotic Onboard](https://www.skillsdirectory.com/skills/lout33-symbiotic-onboard) (Grade A) | Interviews ONE sharp question at a time, never a wall; "deferred markers" (`_(not set yet, your agent will fill this in)_`) instead of raw placeholders; end-state discipline: no raw brackets left anywhere; defers money/trauma deep-fields past session one | bodhi-seed defers to harness-native memory and the optional vault rather than making the four files the product; but the one-question rhythm and deferred-marker end-state belong in our START_HERE flow's next revision |
| [github/setup-my-iq](https://github.com/github/awesome-copilot) (awesome-copilot) | A six-file "personal context portfolio" (identity, role, team, tools, comms-style, prefs) with pointer wiring + symlink pattern so ONE canonical file feeds every harness (CLAUDE.md, copilot-instructions.md, AGENTS.md) | Their symlinking solves the multi-harness problem our Player Ones will hit in month two; a future SIGNPOST can point at the pattern without shipping their enterprise shape |
| [claude-bootstrap](https://github.com/shivae372/claude-bootstrap) | User TIERS (`developer / founder / non-technical`) — the "normie doors" idea as an install flag; deterministic core install with AI-judgment only inside the session; self-healing doctor; installs/forges missing skills mid-task | Our doors live in FIRST_TASKS.md conversationally rather than an installer flag; their "deterministic scaffold + session AI" split matches our bin/ + skill split and validates it |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Persistent context across agents as a marketplace plugin — evidence for Jaron's "suggest tools, don't build our own memory" doctrine | Confirms MODULES.md Recall row: borrow the pointer, not the implementation |
| OpenClaw/Claw-ecosystem BOOTSTRAP.md pattern (already in this file's table) | Widely copied now — the self-deleting bootstrap is becoming genre convention | The seed's START_HERE retirement is aligned with where the ecosystem went; cite the convention when onboarding noobs so it feels familiar |

Field takeaway for the seed: we are not alone and not ahead on structure — we are differentiated on
EXACT-SOURCE custody (hashes, verbatim priority), failure-shape inheritance (the replay ledger), and
the Player One covenant. The borrowing queue, ranked: (1) one-question-at-a-time + deferred markers
into START_HERE, (2) a multi-harness pointer SIGNPOST, (3) tier-aware door phrasing in FIRST_TASKS.
