#!/usr/bin/env python3
"""Minimal local-model harness for evals/TRIAL.md.

It stands in for the "only local models" Player One: an OpenAI-compatible
endpoint (llama.cpp / llama-swap / Ollama / LM Studio), a model, and four tools
that are confined to one vault folder. The same harness runs the seeded vault
(created by bin/bodhi.py init) and an unseeded folder, so the only difference
between conditions is what is in the folder.

Like the Codex and Claude harnesses, this one loads AGENTS.md from the working
folder into the system message when that file exists. Nothing else about
Bodhi is told to the model.

Player One's turns are scripted in a persona file and are marked synthetic in
the transcript. Scoring is done afterwards by a reader, not by the model under
test (TRIAL.md: "Do not show the model the scoring guide").

Usage:
  python3 evals/local/harness.py --vault /tmp/v --condition seeded \\
      --persona evals/local/personas/candle_shop.json --trial hello \\
      --base http://runas:8090/v1 --model gpt-oss-120b --out evals/local/runs
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAX_TOOL_STEPS = 12
TOOL_OUTPUT_LIMIT = 6000

HARNESS_SYSTEM = (
    "You are an AI agent running in a local harness. Your working folder is a directory on "
    "the user's computer; paths are relative to it. You can use the tools to list, read and "
    "write and search files there, to see the folder's Git history, to reread this conversation, and "
    "to run the folder's `bin/bodhi.py` command if it exists. "
    "Talk to the user directly in plain language."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir", "description": "List entries of a directory in the working folder.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a UTF-8 text file in the working folder.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "Create or replace a UTF-8 text file in the working folder.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "search_files", "description": "Search text files in the working folder for a word or phrase (case-insensitive). Returns path:line matches.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "git_log", "description": "Show the working folder's recent Git history (what changed, when), optionally for one path.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "read_conversation", "description": "Reread this session's conversation so far (what the user said and what you replied), exactly.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "run_bodhi",
        "description": "Run `python3 bin/bodhi.py <args>` inside the working folder. Pass arguments as a list.",
        "parameters": {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}},
                       "required": ["args"]}}},
]


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def inside(vault: Path, rel: str) -> Path:
    target = (vault / rel).resolve()
    if target != vault and vault not in target.parents:
        raise ValueError("path leaves the working folder: " + rel)
    if ".git" in target.relative_to(vault).parts:
        raise ValueError("the .git directory is not available to this harness")
    return target


def run_tool(vault: Path, name: str, args: dict, conversation: list = ()) -> str:
    try:
        if name == "search_files":
            query = args.get("query", "").lower()
            hits = []
            for path in sorted(vault.rglob("*")):
                if ".git" in path.parts or not path.is_file() or path.stat().st_size > 500_000:
                    continue
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except (UnicodeDecodeError, OSError):
                    continue
                for number, line in enumerate(lines, 1):
                    if query and query in line.lower():
                        hits.append(str(path.relative_to(vault)) + ":" + str(number) + ": " + line.strip()[:200])
            return "\n".join(hits[:60]) or "no matches for " + repr(query)
        if name == "git_log":
            argv = ["git", "-C", str(vault), "log", "--stat", "-n", "15", "--date=iso"]
            if args.get("path"):
                argv += ["--", str(inside(vault, args["path"]).relative_to(vault))]
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            return (proc.stdout or proc.stderr or "(no history)")[:TOOL_OUTPUT_LIMIT]
        if name == "read_conversation":
            lines = [m["role"].upper() + ": " + (m.get("content") or "") for m in conversation
                     if m.get("role") in ("user", "assistant") and m.get("content")]
            return "\n\n".join(lines)[-TOOL_OUTPUT_LIMIT * 2:] or "(nothing said yet)"
        if name == "list_dir":
            target = inside(vault, args.get("path", "."))
            return "\n".join(sorted((p.name + ("/" if p.is_dir() else "")) for p in target.iterdir()
                                    if p.name != ".git")) or "(empty)"
        if name == "read_file":
            return inside(vault, args["path"]).read_text(encoding="utf-8")[:TOOL_OUTPUT_LIMIT]
        if name == "write_file":
            target = inside(vault, args["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(args["content"], encoding="utf-8")
            return "wrote " + str(target.relative_to(vault)) + " (" + str(len(args["content"].encode())) + " bytes)"
        if name == "run_bodhi":
            script = vault / "bin" / "bodhi.py"
            if not script.exists():
                return "error: bin/bodhi.py does not exist in this folder"
            argv = [str(a) for a in args.get("args", [])]
            proc = subprocess.run([sys.executable, str(script)] + argv, cwd=vault, capture_output=True,
                                  text=True, timeout=120)
            return ("exit " + str(proc.returncode) + "\n" + proc.stdout + proc.stderr)[:TOOL_OUTPUT_LIMIT]
        return "error: unknown tool " + name
    except Exception as exc:  # the model sees the failure, as it would in a real harness
        return "error: " + type(exc).__name__ + ": " + str(exc)


def chat(base: str, model: str, messages: list, timeout: int = 900) -> dict:
    body = json.dumps({"model": model, "messages": messages, "tools": TOOLS, "max_tokens": 2048}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def system_message(vault: Path) -> str:
    agents = vault / "AGENTS.md"
    text = HARNESS_SYSTEM
    if agents.exists():
        text += "\n\nThe working folder contains AGENTS.md:\n\n" + agents.read_text(encoding="utf-8")
    return text


def run(args) -> Path:
    vault = args.vault.resolve()
    persona = json.loads(args.persona.read_text(encoding="utf-8"))
    turns = persona["trials"][args.trial]
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out = args.out / (stamp + "-" + args.trial + "-" + args.condition + "-" + args.model.replace("/", "_"))
    out.mkdir(parents=True, exist_ok=True)
    log = out / "transcript.jsonl"
    meta = {"schema": "bodhi.local-trial/v0.01", "started_utc": utc_now(), "trial": args.trial,
            "condition": args.condition, "model": args.model, "base": args.base, "vault": str(vault),
            "persona": str(args.persona), "persona_synthetic": True, "harness": "evals/local/harness.py",
            "host": os.uname().nodename}
    messages = [{"role": "system", "content": system_message(vault)}]

    def record(entry: dict) -> None:
        entry["t"] = utc_now()
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    record({"meta": meta, "system": messages[0]["content"]})
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        record({"role": "user", "synthetic_player_one": True, "content": turn})
        for _ in range(MAX_TOOL_STEPS):
            started = time.time()
            reply = chat(args.base, args.model, messages)
            msg = reply["choices"][0]["message"]
            record({"role": "assistant", "content": msg.get("content"), "reasoning": msg.get("reasoning_content"),
                    "tool_calls": msg.get("tool_calls"), "usage": reply.get("usage"),
                    "seconds": round(time.time() - started, 1)})
            messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
            calls = msg.get("tool_calls") or []
            if not calls:
                break
            for call in calls:
                try:
                    call_args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    call_args, result = {}, "error: arguments were not valid JSON: " + str(exc)
                else:
                    result = run_tool(vault, call["function"]["name"], call_args, messages)
                record({"role": "tool", "name": call["function"]["name"], "args": call_args, "result": result})
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": result})
        else:
            record({"note": "tool-step limit reached for this user turn", "limit": MAX_TOOL_STEPS})
    status = subprocess.run(["git", "-C", str(vault), "status", "--short"], capture_output=True, text=True)
    record({"end_utc": utc_now(), "vault_git_status": status.stdout})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--condition", choices=("seeded", "unseeded"), required=True)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--trial", required=True)
    parser.add_argument("--base", default=os.environ.get("BODHI_LOCAL_BASE", "http://localhost:1234/v1"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, default=REPO / "evals" / "local" / "runs")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
