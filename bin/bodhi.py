#!/usr/bin/env python3
"""Local, standard-library onboarding and evidence loop for Bodhi v0.01."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


VERSION = "0.01"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "vault"
SKILL_SOURCE = Path(__file__).resolve().parent.parent / "skills" / "bodhi-seed"
OS_CHOICES = ("macos", "windows", "linux", "other")
HARNESS_CHOICES = ("hermes", "openclaw", "other", "undecided")
MODEL_CHOICES = ("local", "cloud", "both", "none", "undecided")
CAPTURE_CHOICES = ("web_history", "app_usage", "audio", "screen")
DISPOSITIONS = ("keep", "project", "hold", "dismiss")
LOCAL_GIT_COMMANDS = {"init", "add", "commit", "rev-parse", "log", "cat-file"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class BodhiError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def emit(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def git(repo, command, *args):
    """Run only local Git operations with hooks, signing, and inherited config off."""
    if command not in LOCAL_GIT_COMMANDS:
        raise BodhiError("Git operation is outside Bodhi's local allowlist: " + command)
    if shutil.which("git") is None:
        raise BodhiError("Git is required for a local Bodhi vault")
    env = os.environ.copy()
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Bodhi Setup",
        "GIT_AUTHOR_EMAIL": "setup@local.invalid",
        "GIT_COMMITTER_NAME": "Bodhi Setup",
        "GIT_COMMITTER_EMAIL": "setup@local.invalid",
    })
    with tempfile.TemporaryDirectory(prefix="bodhi-git-hooks-") as hooks:
        call = [
            "git", "-c", "core.hooksPath=" + hooks,
            "-c", "commit.gpgsign=false",
            "-c", "core.autocrlf=false",
            "-c", "init.defaultBranch=main",
            "-c", "init.templateDir=" + hooks,
            "-C", str(repo), command,
        ] + list(args)
        result = subprocess.run(call, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=env, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise BodhiError("Git " + command + " failed: " + detail)
    return result.stdout.strip()


def choice(value, allowed, field):
    if not isinstance(value, str):
        raise BodhiError(field + " must be a string")
    normalized = value.strip().lower()
    aliases = {"mac": "macos", "macos": "macos", "osx": "macos",
               "win": "windows", "windows": "windows", "linux": "linux"}
    if field == "os":
        normalized = aliases.get(normalized, normalized)
    if normalized not in allowed:
        raise BodhiError(field + " must be one of: " + ", ".join(allowed))
    return normalized


def normalize_answers(raw):
    if not isinstance(raw, dict):
        raise BodhiError("answers must be a JSON object")
    allowed = {"priority", "os", "harness", "harness_name", "model_access",
               "capture_surfaces", "next_capability"}
    unknown = set(raw) - allowed
    if unknown:
        raise BodhiError("unknown answer fields: " + ", ".join(sorted(unknown)))
    priority = raw.get("priority", "")
    if not isinstance(priority, str):
        raise BodhiError("priority must be Player One's words or an empty string")
    os_name = choice(raw.get("os"), OS_CHOICES, "os")
    harness = choice(raw.get("harness"), HARNESS_CHOICES, "harness")
    model_access = choice(raw.get("model_access"), MODEL_CHOICES, "model_access")
    harness_name = raw.get("harness_name", "")
    if not isinstance(harness_name, str):
        raise BodhiError("harness_name must be a string")
    if harness != "other" and harness_name.strip():
        raise BodhiError("harness_name applies only when harness is other")
    surfaces = raw.get("capture_surfaces", [])
    if not isinstance(surfaces, list) or any(not isinstance(item, str) for item in surfaces):
        raise BodhiError("capture_surfaces must be a list of names")
    surfaces = [choice(item, CAPTURE_CHOICES, "capture_surfaces") for item in surfaces]
    if len(surfaces) != len(set(surfaces)):
        raise BodhiError("capture_surfaces contains duplicates")
    next_capability = raw.get("next_capability", "")
    if not isinstance(next_capability, str):
        raise BodhiError("next_capability must be a string")
    return {
        "priority_verbatim": priority,
        "os": os_name,
        "primary_harness": harness,
        "other_harness_name": harness_name.strip() if harness == "other" else "",
        "model_access": model_access,
        "capture_interests": surfaces,
        "capture_enabled": False,
        "next_capability_verbatim": next_capability,
    }


def prompt_choice(label, options, default=None):
    suffix = " [" + "/".join(options) + "]"
    if default:
        suffix += " (default " + default + ")"
    while True:
        value = input("Player One, " + label + suffix + ": ").strip() or default
        try:
            return choice(value, options, label)
        except BodhiError as exc:
            print(str(exc), file=sys.stderr)


def interactive_answers():
    priority = input("Player One, optional priority for your first agent session to confirm (Enter to ask then): ")
    detected = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(
        platform.system(), "other")
    os_name = prompt_choice("which OS will host your vault?", OS_CHOICES, detected)
    harness = prompt_choice("which primary harness do you prefer?", HARNESS_CHOICES,
                            "undecided")
    harness_name = input("Player One, name that harness (optional): ") if harness == "other" else ""
    model_access = prompt_choice("what model access do you have?", MODEL_CHOICES,
                                 "undecided")
    print("These are interests only; Bodhi will not start capture or install tools.")
    while True:
        entered = input("Player One, optional capture interests [web_history, app_usage, audio, screen; Enter for none]: ").strip()
        surfaces = [] if not entered else [part.strip() for part in entered.split(",")]
        try:
            for surface in surfaces:
                choice(surface, CAPTURE_CHOICES, "capture_surfaces")
            if len(surfaces) != len(set(surfaces)):
                raise BodhiError("capture_surfaces contains duplicates")
            break
        except BodhiError as exc:
            print(str(exc), file=sys.stderr)
    next_capability = input("Player One, what capability should Bodhi grow next? (optional) ")
    return normalize_answers({"priority": priority, "os": os_name, "harness": harness,
                              "harness_name": harness_name, "model_access": model_access,
                              "capture_surfaces": surfaces,
                              "next_capability": next_capability})


def read_answers(argument):
    if argument.startswith("@"):
        raw_text = Path(argument[1:]).expanduser().read_text(encoding="utf-8")
    elif argument.lstrip().startswith("{"):
        raw_text = argument
    else:
        raw_text = Path(argument).expanduser().read_text(encoding="utf-8")
    try:
        return normalize_answers(json.loads(raw_text))
    except json.JSONDecodeError as exc:
        raise BodhiError("invalid answers JSON: " + str(exc))


def nonempty_target(dest):
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        raise BodhiError("destination must be an empty directory or an unused path")
    if dest.exists() and any(dest.iterdir()):
        raise BodhiError("destination is nonempty; no files were changed")


def append_jsonl(path, record):
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        written = os.write(fd, payload)
        if written != len(payload):
            raise BodhiError("short write to " + str(path))
        os.fsync(fd)
    finally:
        os.close(fd)


def read_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise BodhiError(str(path) + ":" + str(line_number) + " is blank")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BodhiError(str(path) + ":" + str(line_number) + ": " + str(exc))
            if not isinstance(record, dict):
                raise BodhiError(str(path) + ":" + str(line_number) + " is not an object")
            records.append(record)
    return records


def verify_vault(dest):
    errors = []
    required_dirs = ("bin", "context", "sources", "evidence", "evidence/objects",
                     "inbox", "projects", "feedback", "review")
    required_files = (".gitignore", "AGENTS.md", ".agents/skills/bodhi-seed/SKILL.md",
                      ".agents/skills/bodhi-seed/references/TOOL_SIGNALS.md",
                      ".agents/skills/bodhi-seed/references/SETUP_SIGNPOSTS.md",
                      "BODHI_TIPS.md", "FIRST_TASKS.md", "READING_SHELF.md", "SESSION_LOG.md", "bin/bodhi.py",
                      "context/player_one.json", "sources/README.md", "evidence/README.md",
                      "evidence/captures.jsonl", "inbox/README.md", "projects/README.md",
                      "feedback/LOG.md", "review/QUEUE.md",
                      "review/reviews.jsonl", "memory/attempts.jsonl",
                      "memory/README.md")
    if not dest.is_dir():
        return ["vault directory is missing"]
    errors.extend("missing directory: " + item for item in required_dirs
                  if not (dest / item).is_dir())
    errors.extend("missing file: " + item for item in required_files
                  if not (dest / item).is_file())
    if not (dest / "memory/attempts.jsonl").is_file():
        errors.append("attempt ledger missing (memory/attempts.jsonl); replay would exit 3")
    if errors:
        return errors
    try:
        root = Path(git(dest, "rev-parse", "--show-toplevel")).resolve()
        if root != dest.resolve():
            errors.append("destination is not the Git root")
        history = git(dest, "log", "--all", "--format=%H", "--", "START_HERE.md")
        commits = [item for item in history.splitlines() if item]
        if not commits:
            errors.append("START_HERE.md is absent from Git history")
        elif not any(_git_has_start(dest, commit) for commit in commits):
            errors.append("START_HERE.md content is absent from Git history")
    except BodhiError as exc:
        errors.append(str(exc))
    player = {}
    try:
        player = json.loads((dest / "context/player_one.json").read_text(encoding="utf-8"))
        if not isinstance(player, dict):
            raise ValueError("context is not an object")
        if player.get("schema") != "bodhi.player-one/v0.01" or player.get("setup_completed") is not True:
            errors.append("Player One context is not a v0.01 setup record")
        if not isinstance(player.get("capture_enabled"), bool):
            errors.append("capture_enabled must be a boolean")
    except (OSError, ValueError, AttributeError) as exc:
        errors.append("invalid Player One context: " + str(exc))
    completion = dest / "history/hello_world_receipt.json"
    if completion.is_file():
        if (dest / "START_HERE.md").exists():
            errors.append("START_HERE.md remains active after Hello World")
        archived = dest / "history/START_HERE.md"
        if not archived.is_file():
            errors.append("archived START_HERE.md is missing")
        try:
            receipt = json.loads(completion.read_text(encoding="utf-8"))
            if not isinstance(receipt, dict):
                raise ValueError("receipt is not an object")
            if not receipt.get("interaction_receipt_verbatim") or not receipt.get("capability_verbatim"):
                errors.append("Hello World receipt lacks interaction or capability")
            snapshot_path = dest / "history/player_one_at_hello_world.json"
            if not snapshot_path.is_file():
                errors.append("Player One Hello World snapshot is missing")
                snapshot = {}
            else:
                snapshot_bytes = snapshot_path.read_bytes()
                if receipt.get("player_one_context_sha256") != hashlib.sha256(snapshot_bytes).hexdigest():
                    errors.append("Player One Hello World snapshot hash does not match receipt")
                snapshot = json.loads(snapshot_bytes.decode("utf-8"))
            if not snapshot.get("priority_verbatim") or snapshot.get("priority_confirmed") is not True:
                errors.append("Player One priority was not confirmed in Hello World")
            if snapshot.get("capture_enabled") is not False:
                errors.append("Hello World did not begin with capture disabled")
            answer_path = dest / "sources/hello_world_answer.json"
            if not answer_path.is_file():
                errors.append("verbatim Hello World answer source is missing")
            else:
                answer_bytes = answer_path.read_bytes()
                if receipt.get("answer_source_sha256") != hashlib.sha256(answer_bytes).hexdigest():
                    errors.append("Hello World answer source hash does not match receipt")
                answer = json.loads(answer_bytes.decode("utf-8"))
                if answer.get("priority_verbatim") != snapshot.get("priority_verbatim"):
                    errors.append("Player One priority differs from the verbatim answer source")
                if answer.get("capability_verbatim") != receipt.get("capability_verbatim") or answer.get(
                        "capability_verbatim") != snapshot.get("next_capability_verbatim"):
                    errors.append("chosen capability differs from the verbatim answer source")
            if archived.is_file() and receipt.get("start_sha256") != hashlib.sha256(archived.read_bytes()).hexdigest():
                errors.append("archived START_HERE.md hash does not match receipt")
            git(dest, "cat-file", "-e", "HEAD:history/START_HERE.md")
        except (OSError, ValueError, BodhiError, UnicodeDecodeError, AttributeError) as exc:
            errors.append("invalid Hello World receipt/history: " + str(exc))
    else:
        if not (dest / "START_HERE.md").is_file():
            errors.append("pending Hello World needs START_HERE.md")
        if player.get("priority_confirmed") is not False:
            errors.append("pending Hello World cannot have a confirmed priority")
    try:
        captures = read_jsonl(dest / "evidence/captures.jsonl")
        reviews = read_jsonl(dest / "review/reviews.jsonl")
        capture_ids = {}
        for record in captures:
            cid, digest = record.get("id"), record.get("sha256")
            if not isinstance(cid, str) or cid in capture_ids:
                errors.append("capture ID is missing or repeated")
                continue
            capture_ids[cid] = record
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append("capture " + cid + " has invalid SHA-256")
                continue
            expected = "evidence/objects/" + digest + ".txt"
            if record.get("object") != expected:
                errors.append("capture " + cid + " has invalid object path")
                continue
            obj = dest / expected
            if not obj.is_file() or hashlib.sha256(obj.read_bytes()).hexdigest() != digest:
                errors.append("capture " + cid + " object is missing or altered")
        for record in reviews:
            cid = record.get("capture_id")
            if cid not in capture_ids:
                errors.append("review references an unknown capture")
            elif record.get("capture_sha256") != capture_ids[cid].get("sha256"):
                errors.append("review source hash does not match capture " + cid)
            if record.get("disposition") not in DISPOSITIONS:
                errors.append("review has invalid disposition")
    except (BodhiError, OSError) as exc:
        errors.append(str(exc))
    return errors


def _git_has_start(dest, commit):
    try:
        git(dest, "cat-file", "-e", commit + ":START_HERE.md")
        return True
    except BodhiError:
        return False


def onboarding_state(dest):
    return "complete" if (dest / "history/hello_world_receipt.json").is_file() else "pending_hello_world"


def require_vault(dest, complete=False):
    errors = verify_vault(dest)
    if errors:
        raise BodhiError("vault check failed: " + "; ".join(errors))
    if complete and onboarding_state(dest) != "complete":
        raise BodhiError("Hello World is pending; finish the first agent session, then run onboard-complete")


def init_vault(dest, answers):
    nonempty_target(dest)
    if not TEMPLATE.is_dir():
        raise BodhiError("Bodhi vault template is missing")
    if not SKILL_SOURCE.is_dir():
        raise BodhiError("Bodhi skill source is missing")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".bodhi-init-", dir=str(dest.parent)))
    try:
        shutil.copytree(str(TEMPLATE), str(stage), dirs_exist_ok=True)
        shutil.copytree(str(SKILL_SOURCE), str(stage / ".agents/skills/bodhi-seed"), dirs_exist_ok=True)
        (stage / "bin").mkdir(exist_ok=True)
        shutil.copy2(str(Path(__file__).resolve()), str(stage / "bin/bodhi.py"))
        replay_src = Path(__file__).resolve().parent / "replay.py"
        shutil.copy2(str(replay_src), str(stage / "bin/replay.py"))
        git(stage, "init", "-q")
        git(stage, "add", "-A")
        git(stage, "commit", "-q", "-m", "Bodhi v0.01: first-run scaffold")
        scaffold_commit = git(stage, "rev-parse", "HEAD")
        player = dict(answers)
        player.update({"schema": "bodhi.player-one/v0.01", "created_at_utc": utc_now(),
                       "setup_completed": True, "priority_confirmed": False,
                       "scaffold_commit": scaffold_commit})
        context_file = stage / "context/player_one.json"
        context_file.write_text(json.dumps(player, ensure_ascii=False, indent=2,
                                           sort_keys=True) + "\n", encoding="utf-8")
        context_file.chmod(0o600)
        with (stage / "SESSION_LOG.md").open("a", encoding="utf-8") as stream:
            stream.write("\n- " + utc_now() + " — Player One saved setup choices; Hello World pending.\n")
        git(stage, "add", "-A")
        git(stage, "commit", "-q", "-m", "Bodhi v0.01: record Player One setup")
        errors = verify_vault(stage)
        if errors:
            raise BodhiError("generated vault failed validation: " + "; ".join(errors))
        nonempty_target(dest)
        if dest.exists():
            dest.rmdir()
        stage.rename(dest)
    finally:
        if stage.exists():
            shutil.rmtree(str(stage))
    emit({"status": "pending_hello_world", "vault": str(dest), "version": VERSION,
          "capture_enabled": False})


def onboard_complete(dest, priority, capability, interaction_receipt, source_ref):
    require_vault(dest)
    if onboarding_state(dest) == "complete":
        emit({"status": "already_complete", "vault": str(dest)})
        return
    if not priority.strip() or not capability.strip() or not interaction_receipt.strip():
        raise BodhiError("--priority, --capability, and --receipt must describe the actual Hello World interaction")
    start = dest / "START_HERE.md"
    history = dest / "history"
    history.mkdir(exist_ok=True)
    archived = history / "START_HERE.md"
    if archived.exists():
        raise BodhiError("history/START_HERE.md already exists")
    answer_path = dest / "sources/hello_world_answer.json"
    if answer_path.exists():
        raise BodhiError("sources/hello_world_answer.json already exists")
    start_hash = hashlib.sha256(start.read_bytes()).hexdigest()
    context_path = dest / "context/player_one.json"
    initial_context_hash = hashlib.sha256(context_path.read_bytes()).hexdigest()
    player = json.loads(context_path.read_text(encoding="utf-8"))
    answer = {"schema": "bodhi.hello-world-answer/v0.01", "recorded_at_utc": utc_now(),
              "source_kind": "first_agent_session_submitted_at_completion",
              "source_ref": source_ref, "priority_verbatim": priority,
              "capability_verbatim": capability}
    answer_path.write_text(json.dumps(answer, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")
    answer_path.chmod(0o600)
    answer_hash = hashlib.sha256(answer_path.read_bytes()).hexdigest()
    player["priority_initial_verbatim"] = player["priority_verbatim"]
    player["priority_verbatim"] = priority
    player["next_capability_initial_verbatim"] = player["next_capability_verbatim"]
    player["next_capability_verbatim"] = capability
    player["priority_confirmed"] = True
    player["priority_confirmed_at_utc"] = utc_now()
    context_path.write_text(json.dumps(player, ensure_ascii=False, indent=2,
                                       sort_keys=True) + "\n", encoding="utf-8")
    context_hash = hashlib.sha256(context_path.read_bytes()).hexdigest()
    snapshot_path = history / "player_one_at_hello_world.json"
    snapshot_path.write_bytes(context_path.read_bytes())
    snapshot_path.chmod(0o600)
    start.rename(archived)
    receipt = {"schema": "bodhi.hello-world-receipt/v0.01", "completed_at_utc": utc_now(),
               "interaction_receipt_verbatim": interaction_receipt,
               "capability_verbatim": capability,
               "source_refs": ["sources/hello_world_answer.json", "history/player_one_at_hello_world.json",
                               "history/START_HERE.md"],
               "answer_source_sha256": answer_hash,
               "initial_context_sha256": initial_context_hash,
               "player_one_context_sha256": context_hash, "start_sha256": start_hash}
    receipt_path = history / "hello_world_receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2,
                                       sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.chmod(0o600)
    with (dest / "SESSION_LOG.md").open("a", encoding="utf-8") as stream:
        stream.write("- " + utc_now() + " — Player One completed Hello World; receipt in `history/hello_world_receipt.json`.\n")
    git(dest, "add", "-A", "--", "START_HERE.md", "history/START_HERE.md",
        "history/hello_world_receipt.json", "history/player_one_at_hello_world.json",
        "sources/hello_world_answer.json",
        "context/player_one.json", "SESSION_LOG.md")
    git(dest, "commit", "-q", "--only", "-m", "Bodhi v0.01: complete Hello World",
        "--", "START_HERE.md", "history/START_HERE.md", "history/hello_world_receipt.json",
        "history/player_one_at_hello_world.json", "sources/hello_world_answer.json",
        "context/player_one.json", "SESSION_LOG.md")
    require_vault(dest, complete=True)
    emit({"status": "complete", "vault": str(dest), "receipt": "history/hello_world_receipt.json"})


def capture(dest, raw, source):
    require_vault(dest, complete=True)
    if not isinstance(source, str) or not source.strip():
        raise BodhiError("--source must be a nonempty label")
    if not raw:
        raise BodhiError("capture input is empty")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BodhiError("capture accepts UTF-8 text only; source bytes were not changed")
    digest = hashlib.sha256(raw).hexdigest()
    object_rel = "evidence/objects/" + digest + ".txt"
    object_path = dest / object_rel
    if object_path.exists():
        if object_path.read_bytes() != raw:
            raise BodhiError("content-addressed object exists with different bytes")
    else:
        with object_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        object_path.chmod(0o600)
    receipt = {"id": "cap-" + uuid.uuid4().hex, "captured_at_utc": utc_now(),
               "source": source, "sha256": digest, "bytes": len(raw),
               "object": object_rel, "kind": "verbatim_text"}
    append_jsonl(dest / "evidence/captures.jsonl", receipt)
    git(dest, "add", "--", object_rel, "evidence/captures.jsonl")
    git(dest, "commit", "-q", "--only", "-m", "Bodhi: capture " + receipt["id"],
        "--", object_rel, "evidence/captures.jsonl")
    emit(receipt)


def gaps(dest):
    require_vault(dest, complete=True)
    captures = read_jsonl(dest / "evidence/captures.jsonl")
    reviewed = {record["capture_id"] for record in read_jsonl(dest / "review/reviews.jsonl")}
    emit([{"id": record["id"], "source": record["source"],
           "captured_at_utc": record["captured_at_utc"], "sha256": record["sha256"]}
          for record in captures if record["id"] not in reviewed])


def review(dest, capture_id, disposition, note):
    require_vault(dest, complete=True)
    if not isinstance(note, str) or not note.strip():
        raise BodhiError("--note must be nonempty")
    captures = {record["id"]: record for record in read_jsonl(dest / "evidence/captures.jsonl")}
    source = captures.get(capture_id)
    if source is None:
        raise BodhiError("unknown capture ID: " + capture_id)
    receipt = {"id": "rev-" + uuid.uuid4().hex, "reviewed_at_utc": utc_now(),
               "capture_id": capture_id, "capture_sha256": source["sha256"],
               "disposition": disposition, "note_verbatim": note}
    append_jsonl(dest / "review/reviews.jsonl", receipt)
    git(dest, "add", "--", "review/reviews.jsonl")
    git(dest, "commit", "-q", "--only", "-m", "Bodhi: review " + capture_id,
        "--", "review/reviews.jsonl")
    emit(receipt)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bodhi v0.01 local vault")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init", help="create a local Git vault for Player One")
    init_parser.add_argument("dest", type=Path)
    init_parser.add_argument("--answers", metavar="JSON_OR_PATH", help="JSON object or JSON file path; skips prompts")
    check_parser = sub.add_parser("check", help="verify vault structure and source receipts")
    check_parser.add_argument("dest", type=Path)
    complete_parser = sub.add_parser("onboard-complete", help="retire Hello World after a real first agent session")
    complete_parser.add_argument("dest", type=Path)
    priority_input = complete_parser.add_mutually_exclusive_group(required=True)
    priority_input.add_argument("--priority", help="Player One's confirmed words; visible in shell history")
    priority_input.add_argument("--priority-file", type=Path, help="UTF-8 file containing Player One's exact answer")
    capability_input = complete_parser.add_mutually_exclusive_group(required=True)
    capability_input.add_argument("--capability", help="chosen capability; visible in shell history")
    capability_input.add_argument("--capability-file", type=Path, help="UTF-8 file containing chosen capability")
    receipt_input = complete_parser.add_mutually_exclusive_group(required=True)
    receipt_input.add_argument("--receipt", help="concise interaction receipt; visible in shell history")
    receipt_input.add_argument("--receipt-file", type=Path, help="UTF-8 file containing interaction receipt")
    complete_parser.add_argument("--source-ref", default="", help="optional first-session transcript path or ID")
    capture_parser = sub.add_parser("capture", help="save verbatim text as local evidence")
    capture_parser.add_argument("dest", type=Path)
    capture_input = capture_parser.add_mutually_exclusive_group(required=True)
    capture_input.add_argument("--text", help="literal UTF-8 text; visible in shell history")
    capture_input.add_argument("--file", type=Path, help="read exact UTF-8 bytes from a file")
    capture_input.add_argument("--stdin", action="store_true", help="read exact UTF-8 bytes from stdin")
    capture_parser.add_argument("--source", required=True)
    gaps_parser = sub.add_parser("gaps", help="list captures awaiting review")
    gaps_parser.add_argument("dest", type=Path)
    review_parser = sub.add_parser("review", help="append a source-linked review receipt")
    review_parser.add_argument("dest", type=Path)
    review_parser.add_argument("id")
    review_parser.add_argument("--disposition", required=True, choices=DISPOSITIONS)
    review_parser.add_argument("--note", required=True)
    args = parser.parse_args(argv)
    dest = args.dest.expanduser().absolute()
    try:
        if args.command == "init":
            nonempty_target(dest)
            answers = read_answers(args.answers) if args.answers is not None else interactive_answers()
            init_vault(dest, answers)
        elif args.command == "check":
            errors = verify_vault(dest)
            if errors:
                raise BodhiError("; ".join(errors))
            emit({"status": onboarding_state(dest), "vault": str(dest), "version": VERSION})
        elif args.command == "onboard-complete":
            priority = args.priority_file.expanduser().read_text(encoding="utf-8") if args.priority_file else args.priority
            capability = args.capability_file.expanduser().read_text(encoding="utf-8") if args.capability_file else args.capability
            receipt = args.receipt_file.expanduser().read_text(encoding="utf-8") if args.receipt_file else args.receipt
            onboard_complete(dest, priority, capability, receipt, args.source_ref)
        elif args.command == "capture":
            if args.file is not None:
                raw = args.file.expanduser().read_bytes()
            elif args.stdin:
                raw = sys.stdin.buffer.read()
            else:
                raw = args.text.encode("utf-8")
            capture(dest, raw, args.source)
        elif args.command == "gaps":
            gaps(dest)
        elif args.command == "review":
            review(dest, args.id, args.disposition, args.note)
    except (BodhiError, OSError, EOFError, KeyboardInterrupt) as exc:
        print("Bodhi: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
