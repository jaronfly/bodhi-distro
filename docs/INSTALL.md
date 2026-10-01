# Install the Bodhi seed

Bodhi is a practice, not an app. What installs is one small skill folder, [`skills/bodhi-seed/`](../skills/bodhi-seed/SKILL.md): a `SKILL.md` and two reference files. It gives an AI tool you already use a first conversation with Player One and a set of working habits. No path below installs a model, a background service, a key, a scheduler, or any capture. The founder's source material (`sources/`), the trials (`evals/`), and the vault tools (`bin/`) are never part of an installed skill.

The project's home is [bodhi.fyi](https://bodhi.fyi).

## The one-command installer

`install.sh` does the steps below for you. It looks first, asks before each change, and records what it did:

```sh
curl -fsSL https://raw.githubusercontent.com/jaronfly/bodhi-distro/main/install.sh | bash   # once the repository is public
git clone https://github.com/jaronfly/bodhi-distro.git && cd bodhi-distro && ./install.sh   # works now, with access
```

Useful options: `--dry-run` prints the plan and writes nothing. `--yes` runs unattended with safe defaults: it never uses sudo, runs a downloaded installer, or installs software unless `--allow-sudo`, `--allow-remote-scripts` or `--install LIST` say so. `--update` and `--uninstall` do what they say; uninstall removes only what `~/.bodhi/install-manifest.json` lists and keeps your vault. It runs on macOS, Linux and WSL. It was tested here on Linux with stub package managers and harnesses (`tests/test_install_sh.py`) and run for real on this Linux box. It has **not** been run on macOS or WSL yet.

**Windows.** Install [WSL](https://learn.microsoft.com/windows/wsl/install), open its Ubuntu terminal, and run the installer there. Without WSL, follow the per-harness steps below by hand. Claude Code's personal skills folder, `~/.claude/skills`, is `.claude\skills` inside your Windows user folder. No PowerShell installer is offered, because none could be tested here.

The optional local vault is separate: `python3 bin/bodhi.py init ~/Bodhi` (see the [README](../README.md#optional-exact-source-vault)). It works with any harness that reads a folder's `AGENTS.md`.

Each section ends with **Check it actually loaded**. Do that step. An install command that prints "success" tells you about the installer, not about whether your AI can see the skill.

## Status, honestly

Checked on 2026-09-30 against each harness's own documentation. "Verified" means the step was run here and its output read back; "untested" means it follows the documentation but was not run.

| Where | How | Status |
|---|---|---|
| Any Agent Skills tool | the folder follows the [open format](https://agentskills.io/specification) | **Verified**: `skills-ref validate skills/bodhi-seed` passes (the reference validator from agentskills/agentskills) |
| Claude Code | plugin from this repo's marketplace | **Verified up to the loader**, with Claude Code 2.1.285 and a scratch config: `claude plugin validate .` passed; `claude plugin marketplace add jaronfly/bodhi-distro#claude/seed-ready-player-one` cloned the repo with access to it while private; `claude plugin install bodhi@bodhi-distro` succeeded; `claude plugin details bodhi` listed `Skills (1) bodhi-seed`; the plugin cache held only `SKILL.md` and `references/`. **Untested**: the `/plugin` slash-command form inside a session, the form without `#branch` (works once this is on `main`), install without private-repo access, and whether Claude uses the skill in a live session |
| Claude Code | copy into `~/.claude/skills/` | **Untested** here |
| claude.ai and Claude Desktop | upload a zip | **Zip verified**: `python3 bin/package_skill.py` builds it; unzipped, it is byte-identical to the folder and passes `skills-ref`. **Upload untested** (no browser here) |
| Codex | copy into `~/.agents/skills/` | **Untested** (Codex is not installed here) |
| Other harnesses that read `AGENTS.md` | copy the folder into the project, add one line to `AGENTS.md` | **Untested** |
| Hermes | profile distribution (`distribution.yaml`) | Exercised in the September trials ([findings](../evals/FINDINGS_2026-09-25.md)) with Hermes v0.21; not re-run for this change. The skill's frontmatter moved `version` under `metadata:`, which Hermes documents as optional |

If you run an untested path, please report what happened (an issue, or a note in your own vault) so this table can change.

## Claude Code: install as a plugin

Inside a Claude Code session:

```text
/plugin marketplace add jaronfly/bodhi-distro
/plugin install bodhi@bodhi-distro
```

Or from a terminal:

```sh
claude plugin marketplace add jaronfly/bodhi-distro
claude plugin install bodhi@bodhi-distro
```

While the repository is private, adding the marketplace needs Git access to it. To try a branch before it is merged, add `#branch-name` after the repository name.

The plugin is named `bodhi`, and its one skill runs as **`/bodhi:bodhi-seed`**. Plugin skills carry the plugin's name as a prefix. Start with:

```text
/bodhi:bodhi-seed Hello, Bodhi.
```

What it installs: only `skills/bodhi-seed/`. The marketplace entry pins no version, so each commit is a new version. Marketplaces outside Anthropic's own do not auto-update by default. To pull a newer seed:

```sh
claude plugin marketplace update bodhi-distro
claude plugin update bodhi@bodhi-distro
```

To remove it: `claude plugin uninstall bodhi@bodhi-distro`, then `claude plugin marketplace remove bodhi-distro`.

**Check it actually loaded.**

1. `claude plugin list` shows `bodhi@bodhi-distro` with `Status: enabled`.
2. `claude plugin details bodhi` shows `Skills (1)  bodhi-seed` under `Component inventory`.
3. In a new session, type `/bodhi:bodhi-seed Hello, Bodhi.` A loaded seed opens with **"Bodhi online. Just a seed, for now."** It then asks what you want AI to help change or make. If it greets you some other way, or claims to already know you, the skill did not load. Check step 2 again and start a fresh session.

## Claude Code: copy the skill folder

For a personal install without a marketplace:

```sh
mkdir -p ~/.claude/skills
cp -R skills/bodhi-seed ~/.claude/skills/
```

The skill then runs as `/bodhi-seed`, with no prefix. Claude Code watches this folder, so a new session is not strictly needed. Claude Code does not read `.agents/skills/`, so the copy the vault keeps there is not seen by Claude Code. The vault's `AGENTS.md` is read, from Claude Code v2.1.277 on, when the folder has no `CLAUDE.md`.

**Check it actually loaded.** Run `/skills` in a session and look for `bodhi-seed`. Then say `/bodhi-seed Hello, Bodhi.` and expect "Bodhi online. Just a seed, for now."

## claude.ai and Claude Desktop: upload a zip

Build the zip from a clone of this repository (Python 3.9 or newer, nothing to install):

```sh
python3 bin/package_skill.py
```

It checks the skill against the Agent Skills format, then writes `dist/bodhi-seed.zip`. The zip holds the `bodhi-seed/` folder as its top level, which is the shape claude.ai expects. It prints the zip's SHA-256, so you can confirm the file you upload is the one you built. The zip is never committed to this repository; build it yourself from source you have read.

Then, in claude.ai or the desktop app, open **Customize > Skills**, add a skill, and choose `dist/bodhi-seed.zip`. Custom skills need code execution turned on. Which plans include skills can change, so check Claude's help center for yours.

In chat, the skill has no access to a local vault on your computer. It works without one.

**Check it actually loaded.** Turn the skill on in **Customize > Skills**. Start a new chat and say "Hello, Bodhi." Anthropic's guidance is to review Claude's thinking and confirm it loads the skill. A loaded seed opens with "Bodhi online. Just a seed, for now."

## Codex

Codex reads skills from `~/.agents/skills/` for you, and from `.agents/skills/` in a repository, walking from the working directory up to the repository root.

```sh
mkdir -p ~/.agents/skills
cp -R skills/bodhi-seed ~/.agents/skills/
```

Invoke it with `$bodhi-seed Hello, Bodhi.`, or pick it from `/skills`. If it does not appear, restart Codex.

The vault already works this way. `init` puts the skill at `<vault>/.agents/skills/bodhi-seed/` and an `AGENTS.md` at the vault's root. Codex reads `AGENTS.md` from the Git root down to the working directory, so `cd ~/Bodhi && codex` should see both.

**Check it actually loaded.**

1. `/skills` lists `bodhi-seed`.
2. For the vault's `AGENTS.md`, the Codex documentation suggests `codex --ask-for-approval never "Summarize the current instructions."` from inside the vault. It should mention Player One and `START_HERE.md`.
3. `$bodhi-seed Hello, Bodhi.` opens with "Bodhi online. Just a seed, for now."

## Other harnesses that read AGENTS.md

Many coding agents read a project's `AGENTS.md` but have no skill system. Copy the folder into the project and point to it:

```sh
mkdir -p .agents/skills
cp -R /path/to/bodhi-distro/skills/bodhi-seed .agents/skills/
```

Then add this line to the project's `AGENTS.md`:

```text
For work with Player One, read and follow .agents/skills/bodhi-seed/SKILL.md and the reference files it links.
```

**Check it actually loaded.** Ask: "What does the Bodhi seed tell you to say first, and which file says so?" A harness that read the file answers with "Bodhi online. Just a seed, for now." and names `.agents/skills/bodhi-seed/SKILL.md`. A model can claim to have read a file it has not, so the quote matters more than the claim.

## Hermes

Hermes is where the seed started, and it has its own one-command install: a [profile distribution](https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions). See the [README](../README.md#one-command-with-hermes) for the commands. It installs `SOUL.md` and the `bodhi-seed` skill and nothing else (`distribution.yaml`). To add only the skill to an existing Hermes profile, copy the folder into that profile's skills directory, as the README shows.

**Check it actually loaded.** `hermes skills list --source local` lists `bodhi-seed`. In a new session, `/bodhi-seed Hello, Bodhi.` opens with "Bodhi online. Just a seed, for now." If the greeting drifts into another installation's projects or status, see [trial hygiene](TRIAL_HYGIENE.md). Usually a parent folder's `AGENTS.md` or a resumed session leaked in.

## Any other tool that follows the Agent Skills format

Copy `skills/bodhi-seed/` wherever that tool reads skills. To check the folder yourself, use either tool:

```sh
python3 bin/package_skill.py --check        # standard library only
skills-ref validate skills/bodhi-seed      # the reference validator, if installed
```

Then run the same greeting check. A skill that validates is well-formed. Only the greeting check shows that your AI can see it.
