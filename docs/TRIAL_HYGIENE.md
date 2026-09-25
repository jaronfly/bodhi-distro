# Trial hygiene — how to run a clean seed trial (learned 2026-09-25, GLM lane)

Two contamination mechanisms were found while running the fresh-profile hello in
Hermes. Both make a "fresh Bodhi" answer as if it were the founder's fleet.
Neither is a bug in the distribution; both are invocation-environment effects.
Any future trial (fresh model, fresh Player One simulation) should follow these.

## 1. The cwd walks: `AGENTS.md` lookup climbs the directory tree

Running the trial session with working directory anywhere **under a tree that
contains a fleet `AGENTS.md`** (e.g. `/opt/data/...` on the ruNAS gateway) makes
the model ingest that file and answer in the fleet's voice — door rituals,
advisory read-backs, task queues, lane names. The seed's own `SOUL.md` and
skill stay clean; the walk-up context drowns them.

**Rule:** run every seed trial from a neutral directory that contains no
`AGENTS.md` above it (`/tmp/<trial>` in a container, an empty folder on a
desktop). Verify with: `cd <dir> && ls ../AGENTS.md` → must not exist.

## 2. Session continuation: a profile remembers its last session

> For automated runs, `evals/hermes/groundhog.py` (Codex lane) already solves this:
> it installs the frozen distribution into a FRESH profile each loop, plays the
> scripted first day, asks the restart question in a NEW session, then deletes the
> profile and its tombstone, with HOME/HERMES_HOME pointed at scratch. The rules
> below explain WHY it does that and apply to any manual trial.

`hermes -p <profile> -z "..."` resumes the profile's most recent session, so a
second hello in the same profile inherits the first run's context — including
its contamination. A "fresh session" claim requires a fresh session.

**Rule:** either delete/recreate the trial profile between runs, or start an
explicitly fresh session per the harness's session flags. Record the session
id in the transcript folder either way.

## 3. The profile needs a model and a key (install does not carry credentials)

`hermes profile install` ships `SOUL.md`, `skills/bodhi-seed`, `sources/`, and
the manifest — no `config.yaml` model mapping and no provider key. A working
trial profile needs, after install:

- `hermes -p <name> config set model.default <model>`
- `hermes -p <name> config set model.provider <provider>`
- a profile `.env` with the provider key, owned by the profile user (uid 10000
  in the ruNAS gateway container), mode 600 — otherwise the run dies with
  `PermissionError` in `env_loader`.

## 4. What a contaminated run looks like (fingerprint)

Greeting begins correctly ("Bodhi online. Just a seed, for now") but continues
into fleet status: dashboard weather, advisory queues, cron fleet health, lane
names (Goose/Codex/Claude), "the door's four steps". The seed's real first
hello asks about Player One's first win and claims nothing about the
environment. If you see fleet content, stop scoring; the run is void, and the
cause is rule 1 or 2, not the seed.
