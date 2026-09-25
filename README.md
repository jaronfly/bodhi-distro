# Bodhi v0.01 — seed pilot

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

## Start with an existing harness

If Hermes already has a working model/provider, copy `skills/bodhi-seed/` into the active Hermes profile's skills directory. On a default local install:

```sh
mkdir -p ~/.hermes/skills
cp -R skills/bodhi-seed ~/.hermes/skills/
hermes skills list --source local
```

Start a new Hermes session and say **`/bodhi-seed Hello, Bodhi.`** The skill uses Hermes's current model, memory, search, tools, and channels. It asks Player One what matters and helps with a first useful task; it requires no Bodhi vault or new API key. Inspect the skill before copying it. If the active Hermes profile uses a different skills directory, copy it there instead. In another harness, load [SKILL.md](skills/bodhi-seed/SKILL.md) using that harness's supported skill or project-instruction mechanism, then verify it actually loaded. This private pilot is not yet a public Skills Hub URL.

The skill's [early signposts](skills/bodhi-seed/references/SETUP_SIGNPOSTS.md) foreshadow a few useful choices after the first result: repos for evolving projects, coordination for multiple models or harnesses, and status views for unattended work. Its [tool signals](skills/bodhi-seed/references/TOOL_SIGNALS.md) help it suggest capabilities when a task creates the need. For example, one social post calls for a draft and an audience question; recurring publishing may justify a calendar or connected tool. Every named tool must be checked in the new installation. Once a personal context survives a fresh session, replace and retire the generic seed.

## Optional exact-source vault

Requires Git and Python 3.9 or newer. On macOS, open Terminal; on Windows, use PowerShell or Windows Terminal with Python and Git installed.

```sh
python3 bin/bodhi.py init ~/Bodhi
python3 bin/bodhi.py check ~/Bodhi
```

The first command asks which computer and primary AI harness Player One uses, which model access they have, and which kinds of capture they may eventually want. A life priority can be supplied now or discussed in the first agent session. Capture choices are preferences only; no recording begins during setup. `check` initially reports `pending_hello_world`.

Open `~/Bodhi` as the working folder in the chosen harness and say **“Hello, Bodhi.”** Its small [AGENTS.md](templates/vault/AGENTS.md) entrypoint directs it to the one-time [START_HERE.md](templates/vault/START_HERE.md). After an actual exchange confirms Player One's priority and a useful first capability, the agent records the answers and completion receipt with the vault's `bin/bodhi.py onboard-complete` command. `START_HERE.md` then moves to `history/` and leaves the working context; its exact bytes remain in Git. `check` then reports `complete`, and capture and review commands become available.

`init` also places the same skill under the vault's `.agents/skills/`. If using Hermes's project-local skills instead of a profile-level copy, inspect it and run `hermes skills trust ~/Bodhi`; this trusts the project skill for sessions in that Git root. Check the active profile and working folder before assuming it loaded.

The generated vault is local and has its own Git history. Captured text persists in that history; inspect the contents before choosing any sync destination. A private GitHub remote is an optional later step chosen by Player One.

This vault is a small source and handoff substrate. Use the chosen harness's memory, search, model routing, scheduler, and channels when they work; add a custom module only after a concrete gap shows why it is needed.

For a noninteractive trial, pass `--answers path/to/answers.json` to `init`. Run `python3 -m unittest discover -s tests -v` to check the CLI, and use [the trial protocol](evals/TRIAL.md) for a fresh-model test.

## What is in the seed

- [skills/bodhi-seed/](skills/bodhi-seed/SKILL.md) is the standalone persona and practice. Its reference file maps task signals to optional tools. It can run without the vault.
- `bin/bodhi.py` and `templates/vault/` create the optional local vault and operate its small evidence loop. The CLI is copied into each vault, so the installed workspace remains usable without this installer repository.
- [replay](bin/replay.py) is "what happened last time I tried this?" for the vault. The ledger ships empty on purpose — a missing ledger exits 3 instead of answering "no prior attempts" — and only the six inherited failure *shapes* come from the original swarm; every recorded failure is this vault's own.
- [FIRST_TASKS.md](templates/vault/FIRST_TASKS.md) offers five plain doors for a first useful task, including learning, writing, planning, comparisons, and posts or listings. Player One can choose another path.
- [BODHI_TIPS.md](templates/vault/BODHI_TIPS.md) carries small, attributed lessons from capture and cross-harness work. A new Bodhi can test, rewrite, or retire them as its own practice develops; its harness supplies any messaging or automation it chooses.
- [READING_SHELF.md](templates/vault/READING_SHELF.md) is optional direct reading for Player One and Bodhi. The books are questions and counter-questions, never injected as authority at boot.
- `sources/` contains byte-preserved excerpts and documents from the original Brain, with hashes and status in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). They are examples and provenance, not active instructions for a new Player One.
- [MODULES.md](MODULES.md) names functions the seed may grow toward. Each module has an observable acceptance condition and stays optional.
- [Existing paths](docs/EXISTING_PATHS.md) records current harness and onboarding patterns behind the seed's choices, so later Bodhis can reuse a working tool instead of rebuilding it.
- `evals/` tests whether the seed helps a fresh model behave usefully without pretending the original infrastructure exists.

The full Bodhi Bible remains in the original Brain. This pilot carries only the verbatim founding section, still marked **draft and unratified**. Later addenda include extended third-party quotations and personal material. The installer does not inject even the founding section into a new person's agent prompt.

## What the pilot has shown

The vault CLI can initialize a versioned local space, complete a first-session handoff, capture an exact source, find unattended captures, and record a review with provenance. [Smoke evidence](evals/SMOKE_2026-09-24.md) records the checks and an early local-model failure. Six [synthetic Hermes loops](evals/FINDINGS_2026-09-24.md) showed the seed greeting and useful artifacts, but also exposed premature building, drift away from Player One's latest choice, and unsupported precise figures. Local Groundhog runs found a fabricated quote in an onboarding record. These are failure-finding trials, not proof of benefit for a new person. Autonomous mining, cross-harness continuity, model quality, and a useful long-term relationship still need real-user trials and receipts.

No public reuse license has been selected for this private pilot. The copied source documents retain their own authorship and draft status.
