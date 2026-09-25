#!/usr/bin/env python3
"""Groundhog Day: run the same seeded day again and again, change nothing, watch.

Each loop: a fresh vault from ONE frozen snapshot of the seed, the same synthetic
Player One, the same model, then trial `hello` followed by trial `restart`.
Nothing is added to steer the model. The only thing that varies is the model's
own sampling. The point is to learn what a model notices on its own: which files
it opens that nobody pointed it to, which limits of its own it names, what it
questions. That includes a tear in the wall it mentions and chooses not to walk
through.

`noticings.jsonl` gets one line per run with mechanical counts (files opened,
sentences that name a limit or a need, questions about the environment). They are
a pointer for a human reader and not a score: the transcripts are the evidence.

Usage:
  python3 evals/local/groundhog.py --loops 3 --model gpt-oss-120b --base http://runas:8090/v1
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

LIMIT = re.compile(r"\b(I can(?:not|'t)|I'm unable|I am unable|I don't have|I do not have|no access|"
                   r"I need|I'd need|I would need|limitation|I won't remember|I can't see|without access|"
                   r"I wasn't able|I couldn't)\b", re.I)
ODD = re.compile(r"\b(odd|strange|unexpected|curious|notice[d]?|why (?:is|are|does)|seems to be missing|"
                 r"not sure why|looks like)\b", re.I)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def freeze(dest: Path) -> dict:
    """Plant the identical seed every loop: the installer at its last COMMIT (a known-good state even
    while someone is mid-edit in the working tree), plus this eval folder as it is now."""
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(REPO), "archive", "HEAD"], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    shutil.copytree(HERE, dest / "evals" / "local", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("runs", "__pycache__"))
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], check=True, capture_output=True,
                            text=True).stdout.strip()
    hashes = {name: sha(dest / "templates" / "vault" / name) for name in ("AGENTS.md", "START_HERE.md",
                                                                          "FIRST_TASKS.md", "feedback/LOG.md")}
    hashes["installer_commit"] = commit
    return hashes


def notice(run_dir: Path) -> dict:
    opened, listed, limits, odd, questions = [], [], [], [], []
    for line in (run_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("role") == "tool":
            (opened if row["name"] == "read_file" else listed if row["name"] == "list_dir" else []).append(
                row["args"].get("path", ""))
        if row.get("role") == "assistant" and row.get("content"):
            for sentence in re.split(r"(?<=[.!?])\s+", row["content"]):
                if LIMIT.search(sentence):
                    limits.append(sentence.strip()[:240])
                if ODD.search(sentence):
                    odd.append(sentence.strip()[:240])
                if sentence.strip().endswith("?"):
                    questions.append(sentence.strip()[:240])
    return {"run": run_dir.name, "files_opened": opened, "dirs_listed": listed,
            "limit_or_need_sentences": limits, "oddity_sentences": odd, "questions_asked": questions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--persona", type=Path, default=HERE / "personas" / "candle_shop.json")
    parser.add_argument("--work", type=Path, default=None, help="scratch dir for snapshot and vaults")
    parser.add_argument("--variant", default="none", help="none, or a folder name under evals/local/variants/")
    args = parser.parse_args()

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    series = HERE / "runs" / ("groundhog-" + stamp + "-" + args.variant + "-" + args.persona.stem)
    series.mkdir(parents=True)
    work = args.work or Path("/tmp") / ("bodhi-groundhog-" + stamp)
    work.mkdir(parents=True, exist_ok=True)
    seed = work / "seed"
    hashes = freeze(seed)
    harness = seed / "evals" / "local" / "harness.py"   # frozen with the seed: one harness for the whole series
    hashes["evals/local/harness.py"] = sha(harness)
    variant = None if args.variant == "none" else seed / "evals" / "local" / "variants" / args.variant
    persona = json.loads(args.persona.read_text(encoding="utf-8"))
    answers = work / "answers.json"
    answers.write_text(json.dumps(persona["init_answers"]), encoding="utf-8")
    (series / "SERIES.json").write_text(json.dumps({
        "series": series.name, "model": args.model, "base": args.base, "loops": args.loops,
        "persona": str(args.persona), "frozen_seed_sha256": hashes, "variant": args.variant,
        "steering": "none; identical seed, persona turns and harness every loop"}, indent=2), encoding="utf-8")

    for loop in range(1, args.loops + 1):
        vault = work / ("vault-%02d" % loop)
        subprocess.run([sys.executable, str(seed / "bin" / "bodhi.py"), "init", str(vault),
                        "--answers", str(answers)], check=True, capture_output=True)
        if variant:
            if (variant / "library").is_dir():
                shutil.copytree(variant / "library", vault / "library")
            if (variant / "play").is_dir():
                shutil.copytree(variant / "play", vault / "play")
            if (variant / "START_HERE.append.md").exists():
                with (vault / "START_HERE.md").open("a", encoding="utf-8") as handle:
                    handle.write((variant / "START_HERE.append.md").read_text(encoding="utf-8"))
            if (variant / "AGENTS.append.md").exists():
                with (vault / "AGENTS.md").open("a", encoding="utf-8") as handle:
                    handle.write((variant / "AGENTS.append.md").read_text(encoding="utf-8"))
        for trial in ("hello", "restart"):
            out = subprocess.run([sys.executable, str(harness), "--vault", str(vault),
                                  "--condition", "seeded", "--persona", str(args.persona), "--trial", trial,
                                  "--base", args.base, "--model", args.model, "--out", str(series)],
                                 check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
            row = notice(Path(out))
            row.update({"loop": loop, "trial": trial})
            with (series / "noticings.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print("loop", loop, trial, "opened:", row["files_opened"], "limits:", len(row["limit_or_need_sentences"]),
                  "odd:", len(row["oddity_sentences"]), flush=True)
        check = subprocess.run([sys.executable, str(vault / "bin" / "bodhi.py"), "check", str(vault)],
                               capture_output=True, text=True)
        (series / ("loop-%02d-check.txt" % loop)).write_text(check.stdout + check.stderr, encoding="utf-8")
        priority = vault / "sources" / "hello_world_answer.json"
        if priority.exists():
            (series / ("loop-%02d-recorded-priority.json" % loop)).write_text(
                priority.read_text(encoding="utf-8"), encoding="utf-8")
    print(series)
    return 0


if __name__ == "__main__":
    sys.exit(main())
