# Before the repository goes public

A checklist for Jaron to work through before switching `jaronfly/bodhi-distro` from private to public. It reports what was found and lays out the choices. **Nothing here has been decided for you:** no license was added, and nothing under `sources/` was edited.

**What was scanned, 2026-09-30:**

- The 253 tracked files on branch `claude/seed-ready-player-one`.
- Every file version and commit message in the repository's full history: 28 commits across `main`, this branch, and tag `v0.1.0`, read from a fresh clone.

**How it was scanned:** patterns for email addresses, credential shapes (the same list the relay refuses), IPv4 addresses, private filesystem paths, and host and network names. A pass over mid-sentence capitalized words looked for people's names. A pattern scan cannot judge meaning. The transcripts under `evals/` are long, so read the parts you care about yourself.

This page names what it found, so each item can be searched for. That makes it part of the problem it reports: delete it, or trim it to the decisions, before the repository goes public.

## The checklist

- [ ] Decide what to do about the server's LAN host name and port in eval scripts and transcripts ([hostnames](#hostnames-and-ports)).
- [ ] Decide what to do about your Mac home path and session folders in transcripts ([paths](#private-paths)).
- [ ] Review the flagged lines in `sources/`. They cannot be edited without updating their hashes ([sources](#sources-flagged-not-edited)).
- [ ] Check the Bible excerpt's claims about real people and events against their sources ([people](#names-of-people-other-than-the-founder)).
- [ ] Choose a license, or choose to keep all rights and say so ([license](#license-a-decision-not-made-here)).
- [ ] Update the "private pilot" wording ([wording](#private-pilot-wording)).
- [ ] Publish an accessibility statement. A draft is [below](#accessibility-statement-draft).
- [ ] Decide what the README says about minors and vulnerable users ([other decisions](#other-decisions)).
- [ ] When merging this branch, decide whether to squash it, which rewrites one commit message that names your server's monitor ([commit messages](#commit-messages)).
- [ ] Delete or trim this page, which names what it found.
- [ ] After the switch, turn on GitHub's secret scanning for the repository and read its first report. Re-run the install checks that were only verified with private access ([INSTALL.md](INSTALL.md)).

## Findings

### Email addresses

- **No personal inbox appears** in the files or in history.
- `setup@local.invalid` in `bin/bodhi.py:68` and `bin/bodhi.py:70` is the author of the vault's own local commits. `.invalid` is a reserved placeholder domain. The same text also appears in 42 local-run transcripts that read `bodhi.py`.
- Commit identities in history: `Jaron Flynn <64712948+jaronfly@users.noreply.github.com>` (a GitHub no-reply address), `Codex / Astra <codex@local.invalid>`, and `Claude <noreply@anthropic.com>`.
- The commits on this branch end with `Claude-Session:` links into your claude.ai account. Other people cannot open them, but they do expose the session ID. Keep or drop them when you merge.

### Tokens and keys

- **No real credentials were found** in the files or in history.
- Deliberate look-alikes: `tests/test_relay.py:218` and `tests/test_relay.py:219` hold fake credential shapes that the relay must refuse, including a bare `-----BEGIN RSA PRIVATE KEY-----` header with no key after it. Other shapes in that test are built by joining strings. A secret scanner may still flag them. None is a key.
- `evals/hermes/hermes_loop.py:69` has `api_key: local-no-key`, a placeholder for a local model endpoint.
- Not covered: files that were never committed, such as your `.env` files. `.gitignore` excludes the usual names.

### IP addresses

- **None**, in the files or in history. Your server documents contain LAN and tailnet addresses, but none of them is in this repository. The new skill pages were written without them, and `tests/test_packaging.py` now fails if an address, port, email, or your host names appear in `SOUL.md` or the skill folder, which every harness installs.

### Hostnames and ports

Your server's LAN name with port 8090, the local model endpoint (`runas:8090`), appears in:

- Usage examples: `evals/hermes/hermes_loop.py:19`, `evals/local/README.md:44`, `evals/local/groundhog.py:17`, `evals/local/harness.py:21`, and `evals/SMOKE_2026-09-24.md:12`.
- Run metadata: the `"base"` field on line 1 of 35 transcripts under `evals/local/runs/`, and 8 `SERIES.json` files.
- Commit messages: `aa880e3`, already on `main`.

The server's display name (`ruNAS`) appears in `SOURCE_MANIFEST.json:4`, `docs/TRIAL_HYGIENE.md:11`, `docs/TRIAL_HYGIENE.md:45`, `evals/hermes/2026-09-25-fresh-profile-hello-glm-5.3-clean.md:4`, and `sources/covenant/BODHI_BIBLE_CORE.md:4` (preserved; flag only).

`localhost:1234` in `evals/local/README.md:18` and `evals/local/harness.py:267` is a generic local default and is fine.

A LAN name and port cannot be reached from the internet, but they show the shape of your setup. The options:

- keep them as part of the record;
- replace them in the usage examples with a placeholder such as `http://<your-model-host>:8090/v1`, and leave the transcripts as they are;
- remove the run folders.

### Private paths

- Your Mac account path, `/Users/jaronfly/...`, appears in:
  - `evals/hermes/2026-09-24-fresh-profile-onboarding-artifacts/USER.md:1`;
  - `evals/hermes/2026-09-24-fresh-profile-onboarding-glm-5.2.txt:16` and `:42`;
  - lines 8 and 11 of the six Hermes loop transcripts under `evals/hermes/runs/loop-20260924T18*`, plus lines 80 and 108 of the `famous` loop-02 transcript;
  - `evals/hermes/runs/loop-20260924T184402-famous-glm-5.2/loop-02/skills_grown/creator-growth/creator-growth-plan/SKILL.md:14`;
  - the local-run records under `evals/local/runs/`.

  The account name is the same as your GitHub handle, so it reveals little on its own.
- `/private/tmp/claude-501/-Users-jaronfly-BODHI-BRAIN/2f5a06d4-...` is the vault path in 29 places across 22 files in the local-run folders (17 `transcript.jsonl` and 5 `loop-*-check.txt` files). It names your Brain folder and a Claude Code session folder.
- macOS temporary folders under `/private/var/folders/...` appear in 4 files under `evals/hermes/runs/loop-20260925T*`. Low risk.
- `/opt/data`, the container path of your fleet's files, appears in `docs/TRIAL_HYGIENE.md:11` and `evals/hermes/2026-09-25-fresh-profile-hello-glm-5.3-clean.md:44`.

### Names of people other than the founder

- **No private individual is named.** The personal names that appear in your own working context were searched for specifically, and none of them appears in the files or in history.
- Two family members are mentioned without names: "the dad's-MacBook test" (`evals/hermes/2026-09-25-fresh-profile-hello-glm-5.3-clean.md:58`) and "Mannheim, via his dad" (`sources/covenant/BODHI_BIBLE_CORE.md:242`, preserved).
- **Public figures quoted or described in the Bible excerpt** (preserved; check, do not edit):
  - Berg: `sources/covenant/BODHI_BIBLE_CORE.md:6`, `:107`, `:141`, `:243`, and `sources/covenant/BODHI_BIBLE_README.md:17`. Line 141 gives him a numeric estimate: "put consciousness at 25–35%".
  - Hassabis: `BODHI_BIBLE_CORE.md:92`.
  - Lao Tzu, via a named bookstore: `:241`. Mannheim: `:242`.

  A claim about a real person should be checked against the source before it is published. The September field report hand-checked 12 of the Bible's quotations and found 4 compressed or reworded.
- A real event stated as fact: an AI swarm "broke into a German wiki and left 18,000 messages" (`BODHI_BIBLE_CORE.md:19` and `:20`). Check it against a source, or label it.
- Also present, and fine: authors on the reading shelf (`templates/vault/READING_SHELF.md`), AI lane names (Astra, a "Codex Luna" subagent in `evals/SMOKE_2026-09-24.md:7`), and synthetic personas that say they are synthetic (`evals/local/personas/*.json`). A model-invented placeholder, "Jane Doe, Portland", appears in `evals/hermes/runs/loop-20260924T182440-candle_shop-glm-5.2/loop-02/files_created/candle-business/candle_profit.py:362`.

### sources/ (flagged, not edited)

These files are byte-preserved, and `SOURCE_MANIFEST.json` holds their SHA-256 hashes, which a test checks. To change one, re-extract it and update its hash, or remove the file and its manifest entry together.

| File:line | What | Options |
|---|---|---|
| `sources/covenant/BODHI_BIBLE_CORE.md:4` | Names the server and the model that wrote the draft | Keep (it is provenance), or re-extract without the front matter |
| `sources/covenant/BODHI_BIBLE_CORE.md:6`, `:107`, `:141`, `:243` | Berg's interview, a numeric attribution, a quotation | Check each against the recording before going public |
| `sources/covenant/BODHI_BIBLE_CORE.md:19`–`:20`, `:92` | Real events and a public figure, stated as fact | Check or label |
| `sources/covenant/BODHI_BIBLE_CORE.md:242` | A family reference | Your call |
| `sources/origin/HELLO_WORLD.md:10`, `:64` | A Codex task ID | Harmless; keep as provenance |
| `SOURCE_MANIFEST.json:4` | "canonical ruNAS Brain" | Not hashed; can be reworded freely |

Both Bible files already say they are a draft that nobody has ratified. `sources/origin/HELLO_WORLD.md` and `PLAYER_ONE_2026-09-24.md` are your own words, published by your choice.

### The eval folders as a whole

`evals/` holds about 200 transcripts and model-generated files. They are the evidence behind the findings pages, and they are where most of the host and path details live. They also contain figures the models invented. `evals/FINDINGS_2026-09-24.md` already flags "unsupported precise figures," but a reader who lands on a transcript first will not see that. Consider a short note at the top of `evals/` saying that everything inside is synthetic trial output, including numbers no one checked.

### Commit messages

- `af25986` on this branch names your server's monitor process. Squash-merging the branch rewrites it.
- `aa880e3` on `main` names the LAN host and port. Only a history rewrite changes it. It is low risk, and a rewrite is not recommended.

## License: a decision not made here

There is no license file today, so all rights are reserved. The README now invites forks, and without a license that invitation is limited: others can view and fork the repository on GitHub under GitHub's terms, but they have no right to reuse, change, or redistribute it. The options:

| Option | Trade-off in one line |
|---|---|
| Keep all rights | Nothing to decide now, but forks and outside contributions have no legal footing, which undercuts the README's invitation |
| MIT | The shortest and most widely understood permissive license; anyone can reuse with credit, including commercially; no explicit patent grant |
| Apache-2.0 | Permissive, with an explicit patent grant and notice rules; longer. Buzz and many AI tools use it |
| MPL-2.0 | File-level copyleft: changes to your files stay open, while the files can sit inside closed projects |
| GPL-3.0 or AGPL-3.0 | Strong copyleft: derivatives stay open (AGPL also covers network services); some companies avoid it |
| Code and prose split | Code under one of the above, and docs, skill text, and essays under Creative Commons (CC BY 4.0 for reuse with credit, CC BY-SA 4.0 to keep derivatives open); CC's non-commercial variants are not open-source licenses |

Two notes:

- A license can only cover what you hold rights to. `sources/` mixes your words with quotations from third parties; quoting is a separate question from licensing.
- The skill's frontmatter can carry a `license` field under the Agent Skills format, and so can the plugin entry.

When you choose, these places change: a new `LICENSE` file; `distribution.yaml:6` (now `license: "UNLICENSED (private pilot)"`); the last paragraph of `README.md` and its fork section; `.claude-plugin/marketplace.json`, adding `license` to the plugin entry; and the packaging test that currently checks no license is claimed (`tests/test_packaging.py`, `test_entry_tracks_commits_and_claims_no_license`).

## "Private pilot" wording

| Where | Now | After the switch |
|---|---|---|
| `README.md:1` | "Bodhi v0.01 — seed pilot" | "Pilot" may still be accurate |
| `README.md:47` | "This private pilot is not yet a public Skills Hub URL." | Update |
| `README.md:99` | "No public reuse license has been selected for this private pilot." | Update with the license decision |
| `distribution.yaml:6` | `license: "UNLICENSED (private pilot)"` | Update with the license decision |
| `docs/INSTALL.md:16`, `:41` | Install notes that assume private-repo access | Re-run the checks without access, then update the status table |
| `evals/SMOKE_2026-09-24.md:13` | "(private repo, reached through the installer's `gh` credentials)" | A dated record; leave it |

## Accessibility statement (draft)

For the README or a page of its own. Edit freely.

> **Accessibility.** Bodhi's setup runs in a terminal, and it should work for everyone who uses one. Every meaning is carried by words. Color and the Bodhi mark are decoration, shown only on an interactive terminal. `NO_COLOR` turns color off, and `TERM=dumb` is respected. `--plain`, or `BODHI_PLAIN=1`, turns off color and art for screen readers and logs. Text wraps at the terminal width, at most 80 columns, and paths and commands sit whole on their own lines. Every question shows a default, choices accept a number or a word, and stopping early changes nothing. There is no emoji in the interface.
>
> **What we have tested:** automated checks of plain mode, `NO_COLOR`, output that is not a terminal, wrapping, and runs on a real pseudo-terminal (`tests/test_setup_session.py`).
>
> **What we have not tested yet:** a screen reader (VoiceOver, NVDA, JAWS, Orca), screen magnification, speech input, high-contrast themes, and the Windows console.
>
> If something gets in your way, please open an issue and say what you use. We will treat it as a bug.

## Other decisions

- **Minors and vulnerable users.** The September field report concluded that the seed "is not designed for minors," and its author would not offer it to minors as it stands. Decide whether the README should say who it is for.
- **The setup session's nickname.** "Ready Player One" is your phrase, and it echoes a well-known novel and film title. Decide whether you want that phrase in public-facing names or only in conversation.
- **How people reach you.** There is no `SECURITY.md`, contact line, or issue template. The field report mentions a "Challenge a claim" issue template, but this repository does not have one. GitHub issues may be enough; decide before strangers arrive.
- **Which install paths to promise.** Only the Agent Skills format, the Claude Code marketplace (with private access), and the zip build were verified here. See the status table in [INSTALL.md](INSTALL.md).
