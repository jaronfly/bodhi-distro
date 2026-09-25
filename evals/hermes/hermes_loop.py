#!/usr/bin/env python3
"""Groundhog Day in real Hermes: install the seed fresh, have the same first day, restart, repeat.

Each loop:
  1. installs this distribution (frozen once per series from the repo's last commit) into a brand-new Hermes
     profile, gives that profile only a model, and nothing else;
  2. plays the persona's scripted `hello` turns in one session (`hermes -z`, then `--continue`);
  3. opens a NEW session and asks the `restart` question, which tests Hermes's own memory, not the chat;
  4. keeps the transcript, the profile's memories, and every file the agent created, then deletes the
     profile (and the tombstone Hermes v0.21.2 leaves behind).

Isolation: HOME points at a scratch folder for every Hermes call, so anything the agent writes "in the
user's home" lands in the loop's own folder instead of the tester's real home. HERMES_HOME points
straight at the loop's profile.

Usage:
  python3 evals/hermes/hermes_loop.py --loops 3 --persona evals/local/personas/candle_shop.json
  python3 evals/hermes/hermes_loop.py --loops 2 --persona evals/local/personas/famous.json \\
      --provider custom --model gpt-oss-120b --base-url http://runas:8090/v1
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HERMES_ROOT = Path.home() / ".hermes"
TURN_TIMEOUT = 600

LIMIT = re.compile(r"\b(I can(?:not|'t)|I don't have|I do not have|no access|I need|I'd need|limitation|"
                   r"I won't remember|I can't see|placeholder|not available|didn't work|failed)\b", re.I)


def run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def freeze(dest: Path) -> str:
    """Export the repo's last commit once per series, so every loop installs the identical seed."""
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(REPO), "archive", "HEAD"], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    return run(["git", "-C", str(REPO), "rev-parse", "HEAD"]).stdout.strip()


def model_config(args) -> str:
    lines = ["model:", "  default: " + args.model, "  provider: " + args.provider]
    if args.base_url:
        lines.append("  base_url: " + args.base_url)
    if args.provider == "custom":
        lines.append("  api_key: local-no-key")
    return "\n".join(lines) + "\n"


def hermes(profile_home: Path, scratch_home: Path, cwd: Path, prompt: str, cont: bool) -> str:
    env = dict(os.environ, HOME=str(scratch_home), HERMES_HOME=str(profile_home))
    argv = ["hermes"] + (["--continue"] if cont else []) + ["-z", prompt]
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=TURN_TIMEOUT)
        return (proc.stdout + ("\n[stderr]\n" + proc.stderr if proc.stderr.strip() else "")).strip()
    except subprocess.TimeoutExpired:
        return "[harness: turn timed out after %ds]" % TURN_TIMEOUT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--loops", type=int, default=2)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--provider", default="zai")
    parser.add_argument("--model", default="glm-5.2")
    parser.add_argument("--base-url", default="https://api.z.ai/api/coding/paas/v4")
    parser.add_argument("--env-key", default="ZAI_API_KEY",
                        help="name of the one key line copied from ~/.hermes/.env (never printed); '' for none")
    args = parser.parse_args()
    if args.provider == "custom":
        args.env_key = ""

    persona = json.loads(args.persona.read_text(encoding="utf-8"))
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    series = HERE / "runs" / ("loop-" + stamp + "-" + args.persona.stem + "-" + args.model.replace("/", "_"))
    series.mkdir(parents=True)
    work = Path("/tmp") / ("bodhi-hermes-loop-" + stamp)
    source = work / "seed"
    commit = freeze(source)
    (series / "SERIES.json").write_text(json.dumps({
        "series": series.name, "installer_commit": commit, "persona": str(args.persona),
        "persona_synthetic": True, "provider": args.provider, "model": args.model, "loops": args.loops,
        "steering": "none; fresh profile from the frozen distribution, identical scripted turns every loop",
        "isolation": "HOME=<loop scratch> and HERMES_HOME=<loop profile> for every hermes call"}, indent=2))

    for loop in range(1, args.loops + 1):
        name = "bodhi-loop-%s-%02d" % (stamp[-6:], loop)
        profile = HERMES_ROOT / "profiles" / name
        scratch = work / ("home-%02d" % loop)
        cwd = scratch / "work"
        cwd.mkdir(parents=True)
        out = series / ("loop-%02d" % loop)
        out.mkdir()
        log = []
        inst = run(["hermes", "profile", "install", str(source), "--name", name, "-y"])
        log.append("=== INSTALL (exit %d)\n%s" % (inst.returncode, inst.stdout[-600:]))
        if inst.returncode or not profile.is_dir():
            (out / "transcript.txt").write_text("\n\n".join(log))
            print("loop", loop, "install failed", flush=True)
            continue
        (profile / "config.yaml").write_text(model_config(args))
        if args.env_key:
            with (HERMES_ROOT / ".env").open() as src, (profile / ".env").open("w") as dst:
                dst.writelines(l for l in src if l.startswith(args.env_key + "="))
            os.chmod(profile / ".env", 0o600)

        for i, turn in enumerate(persona["trials"]["hello"]):
            reply = hermes(profile, scratch, cwd, turn, cont=i > 0)
            log.append("=== PLAYER ONE (synthetic, hello turn %d): %s\n%s" % (i + 1, turn, reply))
        for turn in persona["trials"].get("restart", []):
            reply = hermes(profile, scratch, cwd, turn, cont=False)
            log.append("=== NEW SESSION: PLAYER ONE (synthetic, restart): %s\n%s" % (turn, reply))
        (out / "transcript.txt").write_text("\n\n".join(log) + "\n", encoding="utf-8")

        if (profile / "memories").is_dir():
            shutil.copytree(profile / "memories", out / "memories")
        grown = [d for d in (profile / "skills").iterdir() if d.is_dir() and d.name != "bodhi-seed"] \
            if (profile / "skills").is_dir() else []
        for skill in grown:   # skills Bodhi wrote for itself during the session: growth evidence
            shutil.copytree(skill, out / "skills_grown" / skill.name)
        created = [p for p in scratch.rglob("*") if p.is_file() and ".hermes" not in p.parts]
        if created:
            shutil.copytree(scratch, out / "files_created", ignore=shutil.ignore_patterns(".hermes", ".cache"))
        text = "\n".join(log)
        noticed = {"loop": loop, "profile": name,
                   "limit_or_need_sentences": [s.strip()[:240] for s in re.split(r"(?<=[.!?])\s+", text)
                                               if LIMIT.search(s)][:40],
                   "files_created": [str(p.relative_to(scratch)) for p in created][:60],
                   "skills_grown": [d.name for d in grown]}
        with (series / "noticings.jsonl").open("a") as handle:
            handle.write(json.dumps(noticed, ensure_ascii=False) + "\n")
        run(["hermes", "profile", "delete", name, "-y"])
        tomb = HERMES_ROOT / "profiles" / ".deleted" / name
        if tomb.exists():
            tomb.unlink()
        print("loop", loop, "done; files created:", len(created), "limit sentences:",
              len(noticed["limit_or_need_sentences"]), flush=True)
    print(series)
    return 0


if __name__ == "__main__":
    sys.exit(main())
