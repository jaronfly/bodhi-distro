# Onboarding, from a stranger's point of view

Jaron's question for this page was: "how do i make this simple and easy to understand". Below is a stranger's path, from landing on the project to a first useful result. For each step it asks that question and answers three more: what was missing, what covers it now, and what is still missing.

The project's home is [bodhi.fyi](https://bodhi.fyi). This page covers the repository and the installer, not the landing page.

## The journey

### 1. Landing on the README

- **Missing before:** the README opened with pilot details: a Hermes profile, a vault, the founder's sources. A stranger could not tell in half a minute what this is or how to start.
- **Now:** a 30-second paragraph in plain words, then one install line, and an honest note that the line only works once the repository is public. The clone-and-run alternative sits right under it.
- **Still missing:** pictures or a short video of a first session. The landing page may cover that; this repository does not.

### 2. Running the installer

- **Missing before:** there was no installer. People copied folders by hand for each harness, from a doc written for people who already know what a harness is.
- **Now:** `install.sh` runs on macOS, Linux, and WSL.
  - It looks at the computer first and reports in words: what is installed, and which package manager exists.
  - It asks before every change. Each request shows what will change, why, and the exact command.
  - Software installs default to "no". A downloaded installer is named by its URL before it runs. Using sudo is explained before it is asked for.
  - `--dry-run` shows the whole plan and writes nothing. Run piped from `curl`, it reads answers from the terminal, as Hermes's installer does.
- **Still missing:**
  - The installer has not been run on macOS or WSL. It is written for the bash 3.2 that macOS ships, but that is untested.
  - Its output can pass 80 columns when a path is long.
  - Windows without WSL gets instructions, not a script.

### 3. "What is a harness?"

- **Missing before:** words such as harness, skill, vault, and lane appeared with no explanation.
- **Now:**
  - A glossary on this page.
  - `?` at any setup question gives a longer explanation.
  - The installer names the harnesses it found, so the person can recognize theirs instead of having to know the word.
- **Still missing:** someone who only chats in a browser has no harness. The installer offers to install one (Claude Code, Codex, or Hermes), but whether that person wants a terminal tool at all is a bigger question. For them, the zip upload to claude.ai ([INSTALL.md](INSTALL.md)) is the gentler path, and the installer does not automate it.

### 4. The setup questions

- **Missing before:** the questions assumed a harness and asked nothing about the person's chat apps, devices, or notes. They also gave no way to hear more.
- **Now:** "simple, then verbose."
  - Six core questions, each with a default from detection. For example, "claude-code (found on this computer)", or "local (Ollama found)".
  - Then an opt-in set of five: comfort with the terminal (it sets how much gets explained), a chat app, devices, where notes live today, and whether findings should be pushed or wait to be asked for.
  - Answers are kept exactly as typed, and every question can be skipped.
  - What setup *detected* is stored apart from what the person *said*.
- **Still missing:**
  - The questions are in English only.
  - There is no command to edit one answer. The person can re-run `bin/bodhi.py setup` or edit `~/.bodhi/answers.json`.

### 5. Getting an AI tool and signing in

- **Missing before:** "use your harness" assumed one already worked.
- **Now:**
  - The installer offers the person's chosen harness with its official install command, preferring a package manager.
  - Signing in stays with each tool: `claude` and `codex` open their own login on first run, and Hermes runs its own setup wizard after it installs. Bodhi never sees a key.
- **Still missing:** cost. Claude Code needs a paid plan or an API account (per its setup docs), and other tools have their own terms. The installer does not explain plans yet.

### 6. The skill reaches the harness

- **Missing before:** after a copy, nothing confirmed that the skill was in place.
- **Now:**
  - The installer copies the skill where each harness reads it: `~/.claude/skills`, `~/.agents/skills`, or Hermes's own `hermes skills install`.
  - It then runs `bin/bodhi.py doctor`, which compares each copy with the seed.
  - Doctor prints the exact first message to paste and the greeting that proves the skill loaded: "Bodhi online. Just a seed, for now."
  - It also prints a round trip that works after the first meeting: a `bodhi check` message with a fresh code, and the one reply a session that read the skill gives (the code reversed). OpenClaw's verification by a real completion was the model.
- **Still missing:** nothing automatic confirms that the model actually *uses* the skill. Both checks are human steps, and neither has been run in a live harness here.

### 7. Reaching Bodhi from a chat app

- **Missing before:** nothing.
- **Now:** if the person named a chat app that the Hermes gateway documents, the installer offers to hand off to `hermes gateway setup` once Hermes is installed. That wizard asks for the app's token itself.
- **Still missing:**
  - The handoff covers only Hermes.
  - It has not been tested end to end here.

### 8. The vault, if wanted

- **Missing before:** the vault was the main path, which was a lot for a first day.
- **Now:**
  - The vault is offered last, in one sentence, as optional: "the skill works without it". It is created from the answers already given, so no question is asked twice.
  - With `--yes`, a vault is created only when `--vault` names a place.
- **Still missing:** a one-line answer to "why a vault, when my AI tool has memory?" The answer is exact words, history, and handoffs between tools. It lives in the README, not in the installer.

### 9. The first conversation

- **Now:** paste the first message, and see the greeting. The seed's first three turns are designed to feel like meeting someone, not filling in a form ([first boot](../skills/bodhi-seed/references/FIRST_BOOT.md)): hello and one open question; the person's words quoted back with the smallest useful first result; then the result itself, and only after it a signpost. With a vault, the one-time `START_HERE.md` guides that first session. On a terminal with color, `install.sh` and `bodhi.py init` end with a 1.5-second sprout of the Bodhi mark; any key skips it, and `--plain`, `NO_COLOR`, `TERM=dumb`, `CI` or `BODHI_NO_MOTION` turn it off.
- **Still missing:** every trial so far used synthetic personas. No real stranger has gone through this whole path yet.

### 10. Coming back, updating, leaving

- **Now:**
  - `bin/bodhi.py doctor` says what is installed, what is stale, and the one-line fix for each.
  - `./install.sh --update` pulls the seed and refreshes the copies it made.
  - `./install.sh --uninstall` removes only what `~/.bodhi/install-manifest.json` lists. It refuses anything that does not look like what it made. It keeps the vault and any seed checkout the person already had, and in unattended runs it never removes software.
- **Still missing:** uninstall leaves empty parent folders that it created, such as `~/.claude/skills`, and it leaves the log.

## Glossary

| Word | Meaning |
|---|---|
| **Player One** | The person a Bodhi grows around: you. Jaron chose the term in place of "user". |
| **Harness** | The app or command that runs an AI model and lets it read files and use tools, such as Claude Code, Codex, Hermes Agent, or OpenClaw. |
| **Skill** | A folder with a `SKILL.md` of instructions that a harness loads when a task matches. The seed is one skill, `bodhi-seed`. |
| **Seed** | This repository: the skill, the installer, and the optional vault tools. "Just a seed, for now": it grows around what you need. |
| **Vault** | An optional local folder with its own Git history, for exact notes, first-session receipts, and handoffs. |
| **Lane** | One agent's name on the relay, such as `claude-desktop` or `hermes-home`. Lanes appear as they write; there is no list to join. |
| **Relay** | The vault's shared notebook for sessions and harnesses: notes, decisions, handoffs, and pokes that can be claimed and closed (`bin/bodhi.py relay`). |
| **Byline** | How work is signed: role, model, harness, and where it ran (cloud, desktop, or local). |
| **bodhinas** | The generic name for a home server a Bodhi runs on, such as a computer that stays on and runs models or scheduled jobs. |
| **Doctor** | `bin/bodhi.py doctor`: a read-only check of what is installed, with a fix for each problem. |

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `python3 is older than 3.9` or `not installed` | Bodhi's tools are Python scripts. | Let the installer offer the package-manager install, or get Python from python.org. Then run it again. |
| `could not clone ...` | While the repository is private, cloning needs your GitHub access. | Clone it yourself with access, then run `./install.sh` inside the clone. |
| A piped install asks nothing | There was no terminal to ask in, so it ran unattended with safe defaults. | Run it from a terminal, or clone and run `./install.sh`. |
| `claude: command not found` right after installing | The new command is not on your PATH yet (Claude Code's docs). | Open a new terminal window. |
| The greeting is different, or the agent claims to know you | The skill did not load, or another project's instructions leaked in. | Run `bin/bodhi.py doctor`, then start a fresh session. See [trial hygiene](TRIAL_HYGIENE.md). |
| Doctor: "differs from the seed" | An older or edited copy. | `./install.sh --update` |
| Doctor: "installed but has no Bodhi skill yet" | The harness is there, but the skill is not. | `./install.sh`, which asks first. |
| `relay ... exits 3` | This vault's relay has never been written to. | That is not "nothing waiting". Check you are in the right vault, or write the first note. |
| Uninstall left `~/.claude/skills` empty | It removes only what it recorded, not folders it may share. | Delete the empty folder if you like. |

Every run is logged to `~/.bodhi/install.log`: the commands, their output, and your yes or no answers.

## Update and removal

```sh
./install.sh --update        # pull the latest seed, refresh the skill copies, run doctor
./install.sh --uninstall     # remove what the install record lists; keep your vault
bin/bodhi.py doctor ~/Bodhi  # check everything, including a vault
```

Software the installer added through a package manager is listed with the command that removes it. Uninstall asks before running any of those, and never runs them unattended. Hermes's copy of the skill is removed with `hermes skills uninstall bodhi-seed` (Hermes's CLI reference lists the subcommand; the argument form was not tested here).

## Privacy

- **What is stored, and where:**
  - `~/.bodhi/answers.json`: your setup answers, readable only by you.
  - `~/.bodhi/install-manifest.json`: the paths and commands the installer used.
  - `~/.bodhi/install.log`: the commands it ran and your consent answers.
  - Copies of the skill in each harness's folder.
  - If you made one, the vault: your answers are in `context/player_one.json`, readable only by you, and the vault's history is in its own Git repository.
- **Nothing phones home:** there is no telemetry and no analytics. The installer uses the network only to clone or update the seed and to download software you approved. Bodhi itself never sends anything.
- **Your AI tool is a different matter:** when you use a harness, its model provider sees what the agent reads and writes. Choose what goes in the vault with that in mind.
- **No API keys:** none is asked for or stored. Each tool signs you in itself. The relay refuses text that looks like a credential.

## Accessibility

The setup questions and the installer carry every meaning in words. Statuses read "ok", "note", "warn", and "fail". Color only decorates, appears only on a terminal, and stops under `NO_COLOR`, `--plain`, or `TERM=dumb`. There is no emoji. The setup questions wrap at 80 columns at most; the installer's long paths can run past that. Every question has a default, accepts a number or a word, and offers `?` for more. The README describes the setup's accessibility. [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) has a draft accessibility statement and lists what has not been tested, starting with screen readers.

## What was borrowed from Hermes

Hermes Agent's installer and setup already solve much of this. The seed borrows their patterns, and hands off to Hermes's own tools where Hermes does the job. These were read on 2026-09-30:

- From the [installation guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation) and the installer script at `https://hermes-agent.nousresearch.com/install.sh`:
  - Read answers from `/dev/tty` when stdin is the piped script, and skip interactive steps when no terminal exists.
  - Color only on a terminal, and none under `NO_COLOR`.
  - Name the steps.
  - Write a log file.
  - Keep a completion record (ours is the install record, which uninstall also uses).
  - Never append a duplicate line on a repair run.
  - Guard the main block so tests can load the functions.
- From the [quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart):
  - Setup offers a quick path and a full path; ours is core questions, then optional ones.
  - "Get one clean conversation working first, then layer on gateway, cron, skills, voice, or routing." Our order follows it: skill and first message, then the optional chat gateway.
  - Secrets live in each tool's own store, so the seed keeps none.
- From the [skills guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) and the [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands): `hermes skills install <path>` is how the skill reaches Hermes, `hermes gateway setup` is the chat handoff, and `hermes doctor` was the model for `bodhi.py doctor`.

## Install commands, and where each was checked

The installer runs only these. Each was taken from the tool's own documentation on 2026-09-30.

| Tool | Command | Source |
|---|---|---|
| Claude Code | `brew install --cask claude-code` (macOS with Homebrew); `npm install -g @anthropic-ai/claude-code` (Node 22 or newer, never with sudo); `curl -fsSL https://claude.ai/install.sh \| bash` | [Claude Code setup](https://code.claude.com/docs/en/setup) |
| Codex | `brew install --cask codex`; `npm install -g @openai/codex`; `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` | [openai/codex README](https://github.com/openai/codex), [Codex CLI docs](https://learn.chatgpt.com/docs/codex/cli) |
| Hermes Agent | `curl -fsSL https://hermes-agent.nousresearch.com/install.sh \| bash`; `hermes skills install <path>`; `hermes gateway setup` | [Hermes installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation), [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) |
| Ollama | `brew install ollama`; on Linux `curl -fsSL https://ollama.com/install.sh \| sh` (the script uses sudo itself); on macOS without Homebrew, a link to the app | [Ollama on Linux](https://docs.ollama.com/linux), [on macOS](https://docs.ollama.com/macos), [Homebrew formula](https://formulae.brew.sh/formula/ollama) |
| Obsidian | `brew install --cask obsidian`; otherwise a link to the download page | [Homebrew cask](https://formulae.brew.sh/cask/obsidian) |
| Python | `brew install python@3.13` | [Homebrew formula](https://formulae.brew.sh/formula/python@3.13) |
| Git and Python on Linux | `sudo apt-get install -y git python3`, `sudo dnf install -y git python3`, `sudo pacman -S --needed git python` | Standard distribution package names; not checked against each distribution's docs |
| Homebrew | Not installed by the installer; it links [brew.sh](https://brew.sh) | [brew.sh](https://brew.sh) |
| OpenClaw | Not installed; a link to its [install guide](https://docs.openclaw.ai/install). It reads skills from `~/.agents/skills` | [OpenClaw skills](https://docs.openclaw.ai/tools/skills) |
| LM Studio, memtrace | Links only. Memtrace is a proprietary beta | [lmstudio.ai](https://lmstudio.ai), [syncable-dev/memtrace-public](https://github.com/syncable-dev/memtrace-public) |

## Still missing, in one list

- A run on macOS and on WSL, and a native Windows path.
- A real stranger's first session.
- An explanation of plans and costs before a harness is installed.
- An "edit one answer" command.
- Questions in other languages.
- Screen-reader testing.
- Tidying the empty folders uninstall leaves.

*Written by Claude, subagent, cloud session, 2026-10-01.*
