# Bodhi v0.01 — seed pilot

**Home: [bodhi.fyi](https://bodhi.fyi)**

**In 30 seconds.** Bodhi is a practice for working with AI, not an app. It comes down to a few habits: write things down, keep exact words, check claims against evidence, and sign your work. The seed is a small skill that teaches those habits to the AI tool you already use, such as Claude Code, Codex, Hermes, or OpenClaw. It adds an optional local folder, the vault, that keeps your exact notes and handoffs in Git. It installs no model and no service, and it never asks for your keys. You, the human it grows around, are called **Player One**.

```sh
curl -fsSL https://raw.githubusercontent.com/jaronfly/bodhi-distro/main/install.sh | bash
```

That one line works once this repository is public. While it is private, an anonymous download fails, so clone it with your GitHub access and run the installer from the clone:

```sh
git clone https://github.com/jaronfly/bodhi-distro.git && cd bodhi-distro && ./install.sh
```

The installer looks at your computer first and asks before every change. `--dry-run` shows the plan without changing anything. Afterwards, `bin/bodhi.py doctor` checks what is installed, `./install.sh --update` refreshes it, and `./install.sh --uninstall` removes only what the installer recorded. A stranger's walkthrough, with a glossary, troubleshooting, and the privacy and accessibility notes, is in [docs/ONBOARDING_UX.md](docs/ONBOARDING_UX.md).

This repository is a small, runnable starting point for **Player One**, the human founding a Bodhi instance, and the agents who work with them. The portable [Bodhi seed skill](skills/bodhi-seed/SKILL.md) gives an existing AI harness a first-meeting conversation and a set of useful working habits. A local Git vault is optional when Player One needs exact-source custody and a shared handoff trail. Neither path installs a model, browser recorder, or background service.

The name **Player One** comes from [Jaron's direct terminology choice](sources/origin/PLAYER_ONE_2026-09-24.md). The original system's [Hello World](sources/origin/HELLO_WORLD.md) states the broader aim. These are attributed sources. A fresh installation starts from the new person's answers and observations, not Jaron's personal canon.

## One command, with Hermes

This repository is also a [Hermes profile distribution](https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions). With Hermes v0.21 or newer and access to this repo:

```sh
hermes profile install github.com/jaronfly/bodhi-distro --alias
hermes -p bodhi setup          # choose a model; Bodhi needs no keys of its own
hermes -p bodhi chat           # then say: Hello, Bodhi.
```

The profile gets `SOUL.md` (the seed's opening, verbatim from the skill) and the `bodhi-seed` skill. The original founder's source material stays in this repository for optional inspection; it is not installed into a new person's profile. Your keys, memories and sessions stay yours, and `hermes profile update bodhi` pulls new versions without touching them. The optional vault below isn't part of the profile, because Hermes reserves `bin` inside profiles. Create it from a clone of this repo.

If you delete the profile and install it again under the same name, Hermes v0.21.2 can leave a tombstone at `~/.hermes/profiles/.deleted/bodhi` that hides the new install ("does not exist" right after "Installed"). Remove that file if it's there.

## Or as an extension of the tool you already use

Bodhi isn't a plugin or an app, but the seed can travel as one. The same skill folder installs in several harnesses:

```text
/plugin marketplace add jaronfly/bodhi-distro     # Claude Code, inside a session
/plugin install bodhi@bodhi-distro                # then: /bodhi:bodhi-seed Hello, Bodhi.
```

```sh
python3 bin/package_skill.py                      # claude.ai / Claude Desktop: upload dist/bodhi-seed.zip
mkdir -p ~/.agents/skills && cp -R skills/bodhi-seed ~/.agents/skills/   # Codex
```

[docs/INSTALL.md](docs/INSTALL.md) has one section per harness, each ending with a check that the skill actually loaded, and a table of which paths were verified here and which are still untested.

## Start with an existing harness

If Hermes already has a working model/provider, copy `skills/bodhi-seed/` into the active Hermes profile's skills directory. On a default local install:

```sh
mkdir -p ~/.hermes/skills
cp -R skills/bodhi-seed ~/.hermes/skills/
hermes skills list --source local
```

Start a new Hermes session and say **`/bodhi-seed Hello, Bodhi.`** The skill uses Hermes's current model, memory, search, tools, and channels. It asks Player One what matters and helps with a first useful task; it requires no Bodhi vault or new API key. Inspect the skill before copying it. If the active Hermes profile uses a different skills directory, copy it there instead. In another harness, follow [docs/INSTALL.md](docs/INSTALL.md), then verify the skill actually loaded. This private pilot is not yet a public Skills Hub URL.

The skill's [early signposts](skills/bodhi-seed/references/SETUP_SIGNPOSTS.md) foreshadow a few useful choices after the first result: repos for evolving projects, coordination for multiple models or harnesses, and status views for unattended work. Its [tool signals](skills/bodhi-seed/references/TOOL_SIGNALS.md) help it suggest capabilities when a task creates the need. For example, one social post calls for a draft and an audience question; recurring publishing may justify a calendar or connected tool. Every named tool must be checked in the new installation. Once a personal context survives a fresh session, replace and retire the generic seed.

## Optional exact-source vault

Requires Git and Python 3.9 or newer. On macOS, open Terminal; on Windows, use PowerShell or Windows Terminal with Python and Git installed.

```sh
python3 bin/bodhi.py init ~/Bodhi
python3 bin/bodhi.py check ~/Bodhi
```

The first command is a short guided setup, the **Ready Player One** session. It asks six plain questions, one at a time, and each shows a default you keep by pressing Enter: an optional first priority in Player One's own words, which computer holds the folder, which AI app or agent they mainly use, which model access they have, which kinds of capture they might want later, and one ability to grow next. Nothing is written until the last answer, and stopping early creates nothing. At the end it shows what was saved, plants the seed (the Bodhi mark, drawn in whole terminal cells), and says what happens next. Capture choices are preferences only; no recording begins during setup. `check` initially reports `pending_hello_world`.

Accessibility is part of the design, not a skin. Every meaning is carried by words. Color and the mark appear only on an interactive terminal. [`NO_COLOR`](https://no-color.org) turns color off, `TERM=dumb` turns off both, and `--plain` (or `BODHI_PLAIN=1`) gives plain text for screen readers and logs. Text wraps at the terminal width, at most 80 columns. Paths and commands sit whole on their own lines, so they can be copied even when a long path runs past the edge. Choices take a number or a name, and there is no emoji. `--answers` skips the conversation and prints only the JSON receipt.

Open `~/Bodhi` as the working folder in the chosen harness and say **“Hello, Bodhi.”** Its small [AGENTS.md](templates/vault/AGENTS.md) entrypoint directs it to the one-time [START_HERE.md](templates/vault/START_HERE.md). After an actual exchange confirms Player One's priority and a useful first capability, the agent records the answers and completion receipt with the vault's `bin/bodhi.py onboard-complete` command. `START_HERE.md` then moves to `history/` and leaves the working context; its exact bytes remain in Git. `check` then reports `complete`, and capture and review commands become available.

`init` also places the same skill under the vault's `.agents/skills/`. If using Hermes's project-local skills instead of a profile-level copy, inspect it and run `hermes skills trust ~/Bodhi`; this trusts the project skill for sessions in that Git root. Check the active profile and working folder before assuming it loaded.

The generated vault is local and has its own Git history. Captured text persists in that history; inspect the contents before choosing any sync destination. A private GitHub remote is an optional later step chosen by Player One.

This vault is a small source and handoff substrate. Use the chosen harness's memory, search, model routing, scheduler, and channels when they work; add a custom module only after a concrete gap shows why it is needed.

For a noninteractive trial, pass `--answers path/to/answers.json` to `init`. Run `python3 -m unittest discover -s tests -v` to check the CLI, and use [the trial protocol](evals/TRIAL.md) for a fresh-model test.

## What is in the seed

- [skills/bodhi-seed/](skills/bodhi-seed/SKILL.md) is the standalone persona and practice. It can run without the vault. Its reference files map task signals to optional tools ([tool signals](skills/bodhi-seed/references/TOOL_SIGNALS.md)); catalogue [the first fleet's tools](skills/bodhi-seed/references/FLEET_TOOLS.md), each with why it was made, how, how it could work, and what happened when it ran; lay out [notes, a graph, or nothing yet](skills/bodhi-seed/references/MEMORY_SUBSTRATE.md) as questions rather than a recommendation; and turn the seed's own claims into [founding exercises](skills/bodhi-seed/references/FOUNDING_EXERCISES.md) that a new fleet's first model can test, including trust-matrix and team exercises.
- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) and [`bin/package_skill.py`](bin/package_skill.py) carry the same skill to Claude Code and to claude.ai or Claude Desktop; [docs/INSTALL.md](docs/INSTALL.md) covers those and other harnesses.
- `bin/bodhi.py` and `templates/vault/` create the optional local vault and operate its small evidence loop. The CLI is copied into each vault, so the installed workspace remains usable without this installer repository.
- [replay](bin/replay.py) is "what happened last time I tried this?" for the vault. The ledger ships empty on purpose — a missing ledger exits 3 instead of answering "no prior attempts" — and only the six inherited failure *shapes* come from the original swarm; every recorded failure is this vault's own.
- `bin/bodhi.py relay` is the vault's cross-harness relay: one append-only ledger (`relay/ledger.jsonl`) where any session, in any harness with a shell, leaves notes, decisions, handoffs, and pokes, and claims or closes them with a byline. It is ported from the continuity ledger the founder's machines run. Thread state is folded from the events on every read, lanes are derived from who wrote rather than from a roster, and credential-shaped text is refused. `relay brief` is a session's first read.
- [The path](skills/bodhi-seed/references/THE_PATH.md) distils the founding texts into four stages, seed to tree, each with practices, signs it is working, signs it is not, and an honest exit. It adds calibration receipts (predict a benefit, then record the result) and a check for reliance Player One would endorse on reflection. The skill reads it on demand. The [first boot](skills/bodhi-seed/references/FIRST_BOOT.md) lays out the first three turns of a first session.
- Four **optional Bodhi skills**, generalized from the first fleet's own and each off by default: [bodhi-orchestrator](skills/bodhi-orchestrator/SKILL.md) routes work to the cheapest lane that does it well, [bodhi-grill](skills/bodhi-grill/SKILL.md) stress-tests a plan one question at a time, [bodhi-nap](skills/bodhi-nap/SKILL.md) catches up a missed consolidation pass, and [bodhi-synthesis](skills/bodhi-synthesis/SKILL.md) turns one queued lead into a verified entry. Each says what it cost the first fleet. `install.sh` asks about each; the marketplace lists each as its own plugin. A [mode skill template](templates/skills/bodhi-mode/SKILL.md) shows how to write your own; the founder's personal mode skills are not shipped.
- [FIRST_TASKS.md](templates/vault/FIRST_TASKS.md) offers five plain doors for a first useful task, including learning, writing, planning, comparisons, and posts or listings. Player One can choose another path.
- [BODHI_TIPS.md](templates/vault/BODHI_TIPS.md) carries small, attributed lessons from capture and cross-harness work. A new Bodhi can test, rewrite, or retire them as its own practice develops; its harness supplies any messaging or automation it chooses.
- [READING_SHELF.md](templates/vault/READING_SHELF.md) is optional direct reading for Player One and Bodhi. The books are questions and counter-questions, never injected as authority at boot.
- `sources/` contains byte-preserved excerpts and documents from the original Brain, with hashes and status in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). They are examples and provenance, not active instructions for a new Player One.
- [MODULES.md](MODULES.md) names functions the seed may grow toward. Each module has an observable acceptance condition and stays optional.
- [Existing paths](docs/EXISTING_PATHS.md) records current harness and onboarding patterns behind the seed's choices, so later Bodhis can reuse a working tool instead of rebuilding it.
- `evals/` tests whether the seed helps a fresh model behave usefully without pretending the original infrastructure exists.

## Fork it, improve it, or point us elsewhere

Bodhi is one person's practice, grown with a fleet of models, and it is offered as a question more than an answer. Developers are invited to fork or improve the philosophy or any single tool: the setup session, the relay, replay, the vault, or one skill reference. If a project already does one of these jobs better, open an issue that names it, so it can be learned from or integrated. The [first fleet's tools](skills/bodhi-seed/references/FLEET_TOOLS.md#fork-it-improve-it-or-point-elsewhere) end with a list of known alternatives by function, and [existing paths](docs/EXISTING_PATHS.md) records the neighbors the seed already borrows from. Both lists are incomplete. No reuse license has been chosen yet, so forking on GitHub works under GitHub's terms, but other reuse rights are unclear until one is; see [before the repository goes public](docs/PUBLIC_RELEASE.md).

The full Bodhi Bible remains in the original Brain. This pilot carries only the verbatim founding section, still marked **draft and unratified**. Later addenda include extended third-party quotations and personal material. The installer does not inject even the founding section into a new person's agent prompt.

## What the pilot has shown

The vault CLI can initialize a versioned local space, complete a first-session handoff, capture an exact source, find unattended captures, and record a review with provenance. [Smoke evidence](evals/SMOKE_2026-09-24.md) records the checks and an early local-model failure. Six [synthetic Hermes loops](evals/FINDINGS_2026-09-24.md) showed the seed greeting and useful artifacts, but also exposed premature building, drift away from Player One's latest choice, and unsupported precise figures. [Matched five-turn trials](evals/FINDINGS_2026-09-25.md) found that the older seed also resumed the chosen listing task; no tested seed version stopped premature building. Local Groundhog runs found a fabricated quote in an onboarding record. These are failure-finding trials, not proof of benefit for a new person. Autonomous mining, cross-harness continuity, model quality, and a useful long-term relationship still need real-user trials and receipts. The relay gives cross-harness continuity a mechanism with unit tests; no second harness has yet used it in a fresh-session trial.

No public reuse license has been selected for this private pilot. The copied source documents retain their own authorship and draft status.


## What grows from the seed

Every function in a grown Bodhi began as a response to a specific pain — not
a feature list. A few of the seed's instincts, each with the signal that
wakes it:

| Signal | What the seed does |
|---|---|
| A fix "worked" and nothing changed | Check that the tool exists *where you're running it* before calling it |
| A check returned nothing, and you were about to act on "nothing" | Absence of a tool is never evidence about what it would have measured |
| "I already told you that." | Capture exact words, with source and timestamp, where you can see them |
| "All good" — and something is broken | Every status names what it checked; earned green, never template green |
| Things need to happen while nobody is at the keyboard | One scheduled job that writes to the log when it runs |
| The system's words start sounding borrowed | Read primary sources whole; keep quotes distinct from inference |

The full growth map — every function, its signal, and the acceptance test
before it may be claimed as working — is in [MODULES.md](MODULES.md).

## Credits & lineage

Bodhi grew inside one person's life before it became a distribution. The
seed distills that practice; it does not include the tree.

- **Player One** — Jaron Flynn, who grew the original and named the stance:
  *"Bodhi displayed exemplary behavior whenever he went above and beyond as
  well as understood the human on the other end of the line and actually met
  him halfway as well as went the extra mile."*
- **The seed itself** — distilled by Claude (Opus 5.5) from the original
  system's record, at Jaron's direction: *"bodhi needs a seed so he can
  grow, not the whole tree transplanted."*
- **The reading shelf** — William James's *The Varieties of Religious
  Experience*, Aldous Huxley's *The Perennial Philosophy*, and the system's
  own book club shaped the covenant's stance on practice over arrival.
- **Hermes** — [Nous Research's](https://hermes-agent.nousresearch.com)
  agent platform, whose profile distributions carry the seed.

The founding documents in [`sources/origin/`](sources/origin/) are the
originals to inspect — origins, not instructions to inherit.

## License

Licensed under the **[GNU Affero General Public License v3.0](LICENSE)**.

What that means, plainly:

- **You can** plant it, grow it, modify it, and build on it — for free,
  forever, including commercially. A Bodhi grown around someone else is
  *theirs*, and this license is part of why.
- **You must** keep it open: if you modify and deploy it (even as a
  service), your changes ship under the same license. Your Player One's
  data was always theirs; that was never yours to open.
- **If it makes you money**, that's allowed — and if it's fair, supporting
  the project is the right move. The license can't force gratitude; it can
  force openness, and it does.
