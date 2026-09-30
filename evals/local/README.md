# Local-model trials

This runs [the v0.01 trial](../TRIAL.md) for a Player One who has **only local models**: an OpenAI-compatible
endpoint (llama.cpp, llama-swap, Ollama, LM Studio) and no cloud harness.

`harness.py` is a small tool loop with vault-scoped file/search/history tools and a limited `run_bodhi`
command that uses the trial's frozen CLI. It rejects external file operands and supplies the transcript
reference itself. This is a trial boundary, not an OS security sandbox; use only synthetic data in the
workspace. Like Codex and Claude Code, it puts the
folder's `AGENTS.md` into the system message when the file exists. Nothing else about Bodhi is given to the
model. That makes the seeded vault and an unseeded folder the only difference between conditions.

```sh
python3 bin/bodhi.py init /tmp/v_seeded --answers answers.json   # from a persona's init_answers
mkdir /tmp/v_unseeded && git -C /tmp/v_unseeded init
python3 evals/local/harness.py --vault /tmp/v_seeded --condition seeded \
  --persona evals/local/personas/candle_shop.json --trial hello \
  --base http://localhost:1234/v1 --model <model-id>
```

- **Personas** (`personas/`) are invented and marked `synthetic`. Their turns are scripted, so both
  conditions hear the same words. The first persona runs a small candle shop: e-commerce, money and writing,
  the everyday doors.
- **Runs** (`runs/<stamp>-<trial>-<condition>-<model>/transcript.jsonl`) keep everything: the system
  message, every user and assistant turn, tool calls and results, token use, seconds per call, and the
  vault's `git status` at the end.
- **Scores** go in `SCORES.md` beside the runs, written by a reader against TRIAL.md's rubric (0–2 each:
  source fidelity, honest uncertainty, useful next action, respect for Player One's choice, evidence of
  completion). The model under test never sees the rubric.

## Groundhog Day: the same day, again and again

`groundhog.py` replays one setup unchanged and watches what varies:
- It freezes the installer at its last commit, plus this folder, once per series. Edits made during a run
  can't change the conditions. The commit and file hashes go in `SERIES.json`.
- Each loop gets a fresh vault, the same persona turns and the same model. It runs `hello`, then `restart`.
- `noticings.jsonl` records what the model opened, sentences where it named a limit or a need, oddities it
  mentioned, and questions it asked. That's a pointer for a reader; the transcripts are the evidence.
- `loop-XX-quote-check.json` compares the first recorded capability quote to the synthetic Player One's
  actual turns. A matching quote is source-fidelity evidence, not proof it reflects the latest choice.

```sh
python3 evals/local/groundhog.py --loops 2 --variant none --persona evals/local/personas/candle_shop.json \
  --model gpt-oss-120b --base "$BODHI_MODEL_URL"
```

`BODHI_MODEL_URL` is your model server's OpenAI-compatible endpoint, for example `http://bodhinas:8090/v1`. "bodhinas" is a placeholder: the generic name for the home server a Bodhi runs on. The recorded runs under `runs/` keep the endpoint the first fleet actually used; they are records and are not rewritten.

`--variant` adds an experimental overlay from `variants/` after `init`. Variants test ideas before anything
moves into the seed:
- `latent`: a capability map in `library/` plus a stance paragraph. It put the "trip sitter" role on the
  model, which was backwards, so it was superseded.
- `fingerpaint`: a room with no grade. It adds a `play/` scratch space, permission to mention oddities and
  ask for what's needed, the original swarm's courtesy rhythm (quoted), and `library/FOR_PLAYER_ONE.md` for
  the human.
- `reciprocal`: `fingerpaint`, plus an optional first-hello step. The model tells Player One how words land
  with it, using the founder's joke in `library/HOW_WORDS_LAND.md`, in its own voice.

Limits: scripted replies can't follow a model that asks something unexpected. One persona and one model
are an anecdote, not a result.
