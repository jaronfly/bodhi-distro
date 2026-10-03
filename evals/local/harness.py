#!/usr/bin/env python3
"""Minimal local-model harness for evals/TRIAL.md.

It stands in for the "only local models" Player One: an OpenAI-compatible
endpoint (llama.cpp / llama-swap / Ollama / LM Studio), a model, and tools
scoped to one vault folder. This is a trial harness, not an OS sandbox. The same harness runs the seeded vault
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
      --base "$BODHI_MODEL_URL" --model gpt-oss-120b --out evals/local/runs

--base defaults to $BODHI_MODEL_URL, then $BODHI_LOCAL_BASE, then LM Studio's local default.
A home model server might be http://bodhinas:8090/v1 ("bodhinas": the generic name for the
home server a Bodhi runs on).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import socket
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
        "description": "Run the trial's frozen Bodhi CLI for this vault. Pass arguments as a list; init and paths outside this vault are unavailable.",
        "parameters": {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}},
                       "required": ["args"]}}},
]


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def inside(vault: Path, rel: str) -> Path:
    vault = vault.resolve()
    target = (vault / rel).resolve()
    if target != vault and vault not in target.parents:
        raise ValueError("path leaves the working folder: " + rel)
    if ".git" in target.relative_to(vault).parts:
        raise ValueError("the .git directory is not available to this harness")
    return target


BODHI_OPTIONS = {
    "check": set(), "gaps": set(),
    "capture": {"--text", "--file", "--source"},
    "onboard-complete": {"--priority", "--priority-file", "--capability", "--capability-file",
                         "--receipt", "--receipt-file"},
    "review": {"--disposition", "--note"},
}
BODHI_FILE_OPTIONS = {"--file", "--priority-file", "--capability-file", "--receipt-file"}


def checked_bodhi_args(vault: Path, raw: object) -> list[str]:
    """Allow only the vault-scoped subset of the CLI used by this local trial."""
    if not isinstance(raw, list) or not all(isinstance(a, str) for a in raw):
        raise ValueError("run_bodhi args must be a list of strings")
    if len(raw) < 2 or raw[0] not in BODHI_OPTIONS:
        raise ValueError("run_bodhi permits check, gaps, capture, onboard-complete, and review only")
    vault = vault.resolve()
    if inside(vault, raw[1]) != vault:
        raise ValueError("Bodhi destination must be this working folder")
    command = raw[0]
    checked = [command, str(vault)]
    index = 2
    if command == "review":
        if len(raw) <= index or raw[index].startswith("--"):
            raise ValueError("review requires a capture ID")
        checked.append(raw[index])
        index += 1
    while index < len(raw):
        option, equals, inline_value = raw[index].partition("=")
        if option not in BODHI_OPTIONS[command]:
            raise ValueError("unavailable Bodhi option: " + option)
        if equals:
            value = inline_value
            index += 1
        else:
            if index + 1 >= len(raw):
                raise ValueError("missing value for " + option)
            value = raw[index + 1]
            index += 2
        if option in BODHI_FILE_OPTIONS:
            value = str(inside(vault, value))
        checked.extend([option, value])
    return checked


def run_tool(vault: Path, name: str, args: dict, conversation: list = (),
             source_ref: str | None = None) -> str:
    try:
        if name == "search_files":
            query = args.get("query", "").lower()
            hits = []
            for path in sorted(vault.rglob("*")):
                if path.is_symlink():
                    continue
                try:
                    inside(vault, str(path.relative_to(vault)))
                except ValueError:
                    continue
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
            script = REPO / "bin" / "bodhi.py"
            if not script.exists():
                return "error: frozen bin/bodhi.py does not exist in this trial"
            argv = checked_bodhi_args(vault, args.get("args", []))
            if argv[0] == "onboard-complete" and source_ref:
                argv.extend(["--source-ref", source_ref])
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
    # A shared llama-swap evicts/reloads models under concurrent use; a 502 or a
    # reset connection is a transient, not a trial result. Retry with backoff.
    for attempt, delay in enumerate((0, 10, 30, 60)):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as error:
            if error.code not in (502, 503, 504) or attempt == 3:
                raise
            print("chat: transient HTTP %d, retrying in %ds" % (error.code, (10, 30, 60)[attempt]), flush=True)
        except (urllib.error.URLError, ConnectionError, TimeoutError, socket.timeout) as error:
            if attempt == 3:
                raise
            print("chat: transient %s, retrying in %ds" % (type(error).__name__, (10, 30, 60)[attempt]), flush=True)
    raise RuntimeError("chat: retries exhausted")


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
                    result = run_tool(vault, call["function"]["name"], call_args, messages,
                                      source_ref=str(log))
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
    parser.add_argument("--base", default=os.environ.get("BODHI_MODEL_URL")
                        or os.environ.get("BODHI_LOCAL_BASE", "http://localhost:1234/v1"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, default=REPO / "evals" / "local" / "runs")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
