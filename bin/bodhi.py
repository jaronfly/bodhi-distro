#!/usr/bin/env python3
"""Local, standard-library onboarding and evidence loop for Bodhi v0.01."""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:  # POSIX file locking; Windows uses msvcrt instead.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None


VERSION = "0.01"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "vault"
SKILL_SOURCE = Path(__file__).resolve().parent.parent / "skills" / "bodhi-seed"
OS_CHOICES = ("macos", "windows", "linux", "other")
HARNESS_CHOICES = ("hermes", "openclaw", "claude-code", "codex", "other", "undecided")
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
    harness_aliases = {"claude code": "claude-code", "claudecode": "claude-code",
                       "claude_code": "claude-code", "open claw": "openclaw"}
    if field == "os":
        normalized = aliases.get(normalized, normalized)
    if field == "harness":
        normalized = harness_aliases.get(normalized, normalized)
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


# ---------------------------------------------------------------------------
# Ready Player One: the guided first run of `init`.
#
# Plain words carry every meaning. Color and the mark are decoration: they
# appear only on an interactive terminal, color is dropped under NO_COLOR or
# TERM=dumb, and --plain (or BODHI_PLAIN=1) drops both for screen readers and
# logs. Lines wrap at the terminal width, never wider than 80 columns.
# ---------------------------------------------------------------------------

# The Bodhi mark, 11 cells wide and 10 tall. The top three rows are the sprout;
# the bottom seven are soil with carved roots. Brand rule: whole cells only,
# never smoothed, rotated, or stretched. A terminal cell is about twice as tall
# as it is wide, so each cell is drawn two characters wide to stay square.
MARK = ("...##.##...", ".....#.....", ".....#.....", "#####.#####", "#####..####",
        "####.##.###", "###.####.##", "###.#######", "##.########", "###########")
MARK_SPROUT_ROWS = 3
MARK_MIN_WIDTH = 26
SETUP_QUESTIONS = 6

HARNESS_LABELS = {"hermes": "Hermes Agent", "openclaw": "OpenClaw", "claude-code": "Claude Code",
                  "codex": "Codex", "other": "something else; you can name it next",
                  "undecided": "decide later"}
# Only start commands checked against each harness's own documentation (2026-09-30):
# both read a folder's AGENTS.md when started inside it. See docs/INSTALL.md.
HARNESS_START = {"claude-code": "claude", "codex": "codex"}
MODEL_LABELS = {"local": "a model that runs on this computer",
                "cloud": "a hosted service you sign in to", "both": "local and hosted",
                "none": "none yet", "undecided": "not sure"}
OS_LABELS = {"macos": "a Mac", "windows": "Windows", "linux": "Linux", "other": "something else"}
CAPTURE_LABELS = {"web_history": "your browser history", "app_usage": "which apps you use",
                  "audio": "recordings you choose", "screen": "what is on your screen"}


def _isatty(stream):
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _can_encode(stream, text):
    try:
        text.encode(getattr(stream, "encoding", None) or "ascii")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _ansi_supported(env):
    if os.name != "nt":
        return True
    # Older Windows consoles print escape codes literally; newer hosts announce themselves.
    return any(env.get(name) for name in ("WT_SESSION", "TERM_PROGRAM", "ANSICON", "TERM"))


class Voice:
    """How setup speaks. Every meaning is in words; color and art only decorate."""

    def __init__(self, stream=None, plain=False, env=None, width=None):
        self.stream = sys.stdout if stream is None else stream
        env = os.environ if env is None else env
        tty = _isatty(self.stream)
        dumb = env.get("TERM", "") == "dumb"
        self.plain = bool(plain) or bool(env.get("BODHI_PLAIN"))
        self.art = tty and not self.plain and not dumb
        # https://no-color.org: any nonempty NO_COLOR value turns color off.
        self.color = self.art and not env.get("NO_COLOR") and _ansi_supported(env)
        self.palette_256 = "256color" in env.get("TERM", "") or bool(env.get("COLORTERM"))
        if width is None:
            width = shutil.get_terminal_size((80, 24)).columns if tty else 80
        self.width = max(20, min(80, int(width)))
        self.block = "█" if _can_encode(self.stream, "█") else "#"

    def style(self, text, *names):
        if not self.color or not text or not names:
            return text
        codes = {"bold": "1", "dim": "2",
                 "sprout": "38;5;70" if self.palette_256 else "32",
                 "soil": "38;5;130" if self.palette_256 else "33"}
        return "\x1b[" + ";".join(codes[name] for name in names) + "m" + text + "\x1b[0m"

    def write(self, text):
        self.stream.write(text)
        self.stream.flush()

    def line(self, text=""):
        self.write(text + "\n")

    def para(self, text, indent=0, style=(), hang=0):
        wrapped = textwrap.wrap(text, width=self.width, initial_indent=" " * indent,
                                subsequent_indent=" " * (indent + hang), break_long_words=False,
                                break_on_hyphens=False) or [""]
        for item in wrapped:
            self.line(self.style(item, *style))

    def verbatim(self, text, indent=2):
        """A path or command on its own line, never wrapped, so it can be copied whole."""
        self.line(" " * indent + text)

    def problem(self, text):
        # Written in words ("Not recognized") so the message does not rely on color.
        print("Not recognized: " + text, file=sys.stderr)

    def mark_lines(self):
        return render_mark(self.block, self.style)


def render_mark(block="█", style=None):
    """Draw MARK in whole cells, two characters per cell so each cell stays square."""
    lines = []
    for index, row in enumerate(MARK):
        drawn = "".join(block * 2 if cell == "#" else "  " for cell in row)
        if style is not None:
            drawn = style(drawn, "sprout" if index < MARK_SPROUT_ROWS else "soil")
        lines.append(drawn)
    return lines


def _read_line(voice, prompt="Your answer: "):
    try:
        if voice.stream is sys.stdout:
            value = input(prompt)
        else:
            voice.write(prompt)
            value = input()
    except EOFError:
        raise BodhiError("setup stopped before the last question; nothing was created")
    if not _isatty(sys.stdin):
        voice.line()  # keep a log readable when answers arrive from a pipe
    return value


def _question(voice, number, title, why):
    voice.line()
    voice.para("Question %d of %d. %s" % (number, SETUP_QUESTIONS, title), style=("bold",))
    voice.para(why, indent=2)


def _ask_choice(voice, number, title, why, field, options, labels, default, default_note=""):
    _question(voice, number, title, why)
    for index, value in enumerate(options, 1):
        voice.para("%d. %s (%s)" % (index, value, labels[value]), indent=2)
    voice.para("Press Enter to keep %s%s, or type a number or a name." % (default, default_note),
               indent=2)
    while True:
        raw = _read_line(voice).strip()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        try:
            return choice(raw, options, field)
        except BodhiError:
            voice.problem("%s. Type a number from 1 to %d, a name such as %s, or press Enter "
                          "to keep %s." % (raw, len(options), options[0], default))


def _ask_capture(voice, number):
    _question(voice, number, "Is there anything you might want Bodhi to learn from, later on?",
              "These are interests only. Nothing is recorded now, and nothing starts "
              "without your say-so in a later session.")
    for index, value in enumerate(CAPTURE_CHOICES, 1):
        voice.para("%d. %s (%s)" % (index, value, CAPTURE_LABELS[value]), indent=2)
    voice.para("Press Enter for none, or type numbers or names separated by commas.", indent=2)
    while True:
        raw = _read_line(voice).strip()
        if not raw or raw.lower() == "none":
            return []
        chosen, error = [], ""
        for part in [item for item in re.split(r"[,\s]+", raw) if item]:
            if part.isdigit() and 1 <= int(part) <= len(CAPTURE_CHOICES):
                chosen.append(CAPTURE_CHOICES[int(part) - 1])
                continue
            try:
                chosen.append(choice(part, CAPTURE_CHOICES, "capture_surfaces"))
            except BodhiError:
                error = part
                break
        if not error and len(chosen) != len(set(chosen)):
            error = raw + " names one choice twice"
        if not error:
            return chosen
        voice.problem("%s. Type numbers from 1 to %d or names such as web_history, or press "
                      "Enter for none." % (error, len(CAPTURE_CHOICES)))


def _ask_words(voice, number, title, why, skip_note):
    _question(voice, number, title, why)
    voice.para(skip_note, indent=2)
    return _read_line(voice)


def interactive_answers(dest, voice=None):
    """Ask the six setup questions one at a time. Nothing is written until they are done."""
    voice = voice or Voice()
    voice.line(voice.style("Bodhi seed, setup (v" + VERSION + ")", "bold"))
    voice.line()
    voice.para("Hello, Player One.")
    voice.line()
    voice.para("Bodhi is a practice more than an app: write things down, keep exact words, "
               "check claims against evidence, and sign your work. This setup makes a folder "
               "where that practice can live, next to the AI tools you already use.")
    voice.line()
    voice.para("Six short questions follow, one at a time. Each one shows a default: press "
               "Enter to keep it or to skip. You can change any answer later.")
    voice.line()
    voice.para("Nothing here records you, installs tools, connects accounts, or sends anything "
               "anywhere. Your answers are saved in one file inside the new folder:")
    voice.verbatim(shown_path(dest / "context" / "player_one.json"))
    priority = _ask_words(
        voice, 1, "What is one thing you want AI to help you change or make right now?",
        "Your words are kept exactly as you type them. Your first agent session will read "
        "them back and ask whether they still fit.",
        "Press Enter to skip; your first session will ask you instead.")
    detected = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(
        platform.system(), "other")
    os_name = _ask_choice(
        voice, 2, "Which computer will hold your Bodhi folder?",
        "So that agents suggest commands that work on your machine.",
        "os", OS_CHOICES, OS_LABELS, detected, " (detected)")
    harness = _ask_choice(
        voice, 3, "Which AI app or agent will you mainly use with this folder?",
        "Bodhi works through the AI tool you already use. It does not install one.",
        "harness", HARNESS_CHOICES, HARNESS_LABELS, "undecided")
    harness_name = ""
    if harness == "other":
        voice.para("What is it called? Press Enter to skip.", indent=2)
        harness_name = _read_line(voice)
    model_access = _ask_choice(
        voice, 4, "What kind of AI model access do you have?",
        "Bodhi needs no keys of its own. This only helps agents make realistic suggestions.",
        "model_access", MODEL_CHOICES, MODEL_LABELS, "undecided")
    surfaces = _ask_capture(voice, 5)
    next_capability = _ask_words(
        voice, 6, "What would you like Bodhi to be able to do next?",
        "One small ability, in your own words. It is kept exactly as you type it.",
        "Press Enter to skip.")
    return normalize_answers({"priority": priority, "os": os_name, "harness": harness,
                              "harness_name": harness_name, "model_access": model_access,
                              "capture_surfaces": surfaces,
                              "next_capability": next_capability})


def _said(value, empty):
    return '"' + value + '"' if value.strip() else empty


def setup_summary(voice, answers):
    harness = answers["primary_harness"]
    if harness == "other" and answers["other_harness_name"]:
        harness = "other: " + answers["other_harness_name"]
    voice.line()
    voice.para("Here is what was saved.", style=("bold",))
    rows = (("Priority", _said(answers["priority_verbatim"], "none yet; your first session will ask")),
            ("Computer", answers["os"]),
            ("AI app or agent", harness),
            ("Model access", answers["model_access"]),
            ("Capture interests", ", ".join(answers["capture_interests"]) or "none"),
            ("Recording", "off; nothing records"),
            ("Next ability", _said(answers["next_capability_verbatim"], "none yet")))
    for label, value in rows:
        voice.para(label + ": " + value, indent=2)


def shown_path(path):
    """A path as a person would type it: ~/Bodhi where that works, quoted if it has spaces."""
    path = Path(path)
    text = str(path)
    if os.name != "nt":
        try:
            relative = path.relative_to(Path.home())
            text = "~" if str(relative) == "." else "~/" + relative.as_posix()
        except (ValueError, RuntimeError, KeyError):
            pass
    if any(char.isspace() for char in text):
        text = '"' + str(path) + '"'
    return text


def what_happens_next(voice, dest, answers):
    harness = answers["primary_harness"]
    name = HARNESS_LABELS.get(harness) if harness not in ("other", "undecided") else None
    if harness == "other" and answers["other_harness_name"].strip():
        name = answers["other_harness_name"].strip()
    folder = shown_path(dest)
    voice.line()
    if voice.art and voice.width >= MARK_MIN_WIDTH:
        for drawn in voice.mark_lines():
            voice.line("  " + drawn)
        voice.line()
    voice.para("Your seed is planted. Its folder is:", style=("bold",))
    voice.verbatim(folder)
    voice.line()
    voice.para("What happens next", style=("bold",))
    if name:
        voice.para("1. Open that folder in " + name + " as its working folder.", indent=2, hang=3)
    else:
        voice.para("1. Open that folder as the working folder in the AI app or agent you "
                   "choose. It needs to be able to read the files there.", indent=2, hang=3)
    if harness in HARNESS_START:
        voice.para("In a terminal, that is these two lines:", indent=5)
        voice.verbatim("cd " + folder, indent=7)
        voice.verbatim(HARNESS_START[harness], indent=7)
    voice.para("2. Say: Hello, Bodhi.", indent=2, hang=3)
    voice.para("3. Bodhi asks what you want to change or make, then helps with one small first "
               "thing you can judge for yourself.", indent=2, hang=3)
    voice.para("4. After that first real exchange, your agent saves your exact words and "
               "retires START_HERE.md. Its text stays in the folder's Git history.",
               indent=2, hang=3)
    voice.line()
    voice.para("Nothing is recording. No account was connected. Nothing left this computer. "
               "To check the folder at any time, run this inside it:")
    voice.verbatim("python3 bin/bodhi.py check .")
    voice.line()
    voice.line("Receipt, for scripts and agents:")


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
    return {"status": "pending_hello_world", "vault": str(dest), "version": VERSION,
            "capture_enabled": False}


def _contains_quoted_span(text):
    """True if text contains a quoted span of >= 8 chars in any common quote style.

    A soft structural signal: the onboarding instructions ask for the player's
    exact words in quotation marks. A paraphrase usually arrives unquoted, and
    this makes that visible in the recorded evidence instead of silent.
    """
    pairs = [('"', '"'), ("\u201c", "\u201d"), ("'", "'"), ("\u2018", "\u2019")]
    for opener, closer in pairs:
        first = text.find(opener)
        if first == -1:
            continue
        second = text.find(closer, first + len(opener))
        if second != -1 and (second - first) >= 9:
            return True
    return False


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
              "capability_verbatim": capability,
              "capability_quoted": _contains_quoted_span(capability)}
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


# ---------------------------------------------------------------------------
# Relay: what one session leaves for the next, across harnesses.
#
# Ported from the continuity ledger running on the founder's server (the
# runas-monitor ledger and its bodhi-continuity command, September 2026), with
# the same event shape, so a ledger can move between them. There, one server
# process is the only writer; here, the vault's file is the shared surface and
# a lock serializes writers on one machine.
#
# One append-only JSONL file, one event per line, never rewritten. Thread state
# is folded from the events on every read, so the file is its own audit trail.
#
#   starters     note | decision      records  -- state "logged"
#                handoff | poke       actions  -- open -> claimed -> done | dropped
#   transitions  claim | release | done | drop | reopen | reply  (each carries re=<id>)
#
# Lanes (who is writing) are derived from the events, never from a roster: a
# new harness appears the first time it writes or is addressed.
# ---------------------------------------------------------------------------

RELAY_LEDGER = "relay/ledger.jsonl"
RELAY_STARTERS = {"note": "record", "decision": "record", "handoff": "action", "poke": "action"}
RELAY_TRANSITIONS = ("claim", "release", "done", "drop", "reopen", "reply")
RELAY_POKE_TTL = 86400
RELAY_MAX_TTL = 2592000
RELAY_MAX_TITLE = 160
RELAY_MAX_BODY = 4000
RELAY_ID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"
# The ledger is plain text in the vault and in its Git history. Refuse the
# obvious credential shapes at the door rather than trusting every lane to remember.
RELAY_SECRET = re.compile(r"""
    \bsk-[A-Za-z0-9_-]{16,} | \bghp_[A-Za-z0-9]{20,} | \bgithub_pat_[A-Za-z0-9_]{20,}
  | \bxox[abprs]-[A-Za-z0-9-]{10,} | \bAKIA[0-9A-Z]{16}\b | -----BEGIN[A-Z ]*PRIVATE[ ]KEY-----
  | \b(?:api[_-]?key|token|secret|passw(?:or)?d)\s*[:=]\s*["']?[^\s"']{8,}
""", re.IGNORECASE | re.VERBOSE)
RELAY_WRITE_BACK = """\
python3 bin/bodhi.py relay claim <id>                      # before you start on a thread
python3 bin/bodhi.py relay done <id> "what you verified"   # or: drop <id> "why not"
python3 bin/bodhi.py relay release <id> "where it stands"  # stopping before it is done
python3 bin/bodhi.py relay note "title" ["body"]           # what the next session should know
python3 bin/bodhi.py relay decide "title" "why"            # a settled call, so nobody relitigates it
python3 bin/bodhi.py relay handoff --to <lane|any> "title" "what done looks like\""""


class RelayMissing(BodhiError):
    """No ledger yet. Reported as exit 3, never as an empty answer."""


def relay_lane(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")[:40]


def relay_line(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()


def relay_text(value):
    if not isinstance(value, str):
        return ""
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", value)
    return value.lstrip("\n").rstrip()


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def relay_vault(explicit=None):
    """Find the vault: --vault, then BODHI_VAULT, then this CLI's own vault, then the cwd upward."""
    def is_vault(path):
        return (path / "context" / "player_one.json").is_file() and (path / "AGENTS.md").is_file()
    chosen = explicit or os.environ.get("BODHI_VAULT")
    if chosen:
        path = Path(chosen).expanduser().absolute()
        if not is_vault(path):
            raise BodhiError(str(path) + " is not a Bodhi vault (no context/player_one.json and "
                             "AGENTS.md); pass the vault folder with --vault")
        return path
    home = Path(__file__).resolve().parent.parent
    if is_vault(home):
        return home
    here = Path.cwd().absolute()
    for path in (here,) + tuple(here.parents):
        if is_vault(path):
            return path
    raise BodhiError("no Bodhi vault here or above " + str(here) + "; run this inside a vault, "
                     "pass --vault PATH, or set BODHI_VAULT")


def relay_events(vault):
    """Return (events, unreadable_line_count). A missing ledger is RelayMissing, not []."""
    path = vault / RELAY_LEDGER
    if not path.is_file():
        raise RelayMissing(
            "no relay ledger at " + str(path) + ". Nothing has been written to this vault's relay "
            "yet, or this is not the vault the other session used. That is not the same as "
            "'nothing is waiting'. Start one with: python3 bin/bodhi.py relay note \"title\"")
    events, unreadable = [], 0
    for raw in path.read_bytes().splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            unreadable += 1
            continue
        if isinstance(event, dict) and isinstance(event.get("id"), str) and isinstance(event.get("kind"), str):
            events.append(event)
        else:
            unreadable += 1
    return events, unreadable


def relay_fold(events, now):
    """Replay events into threads. Same rules the server's ledger uses."""
    by_id, threads, lanes, ids = {}, [], {}, set()

    def lane(name):
        return lanes.setdefault(name, {"id": name, "events": 0, "last_seen": 0,
                                       "opened": 0, "closed": 0})

    for event in events:
        kind, ts, sender = event.get("kind"), _as_int(event.get("ts")), event.get("from")
        ids.add(event["id"])
        if isinstance(sender, str) and sender:
            seen = lane(sender)
            seen["events"] += 1
            seen["last_seen"] = max(seen["last_seen"], ts)
        if kind in RELAY_STARTERS:
            if event["id"] in by_id:
                continue
            thread = {key: event[key] for key in ("id", "kind", "from", "to", "title", "body",
                                                  "ts", "ttl", "tags", "meta")
                      if event.get(key) is not None}
            thread.update({"class": RELAY_STARTERS[kind], "updated": ts, "log": [],
                           "state": "open" if RELAY_STARTERS[kind] == "action" else "logged"})
            by_id[event["id"]] = thread
            threads.append(thread)
            if sender in lanes:
                lanes[sender]["opened"] += 1
            addressed = event.get("to") or "any"
            if addressed != "any":
                lane(addressed)
            continue
        if kind not in RELAY_TRANSITIONS:
            continue
        thread = by_id.get(event.get("re") or "")
        if thread is None:
            continue
        thread["log"].append({key: event[key] for key in ("id", "kind", "from", "ts", "body")
                              if event.get(key) is not None})
        thread["updated"] = max(thread["updated"], ts)
        state = thread["state"]
        if thread["class"] == "action":
            if kind == "claim" and state in ("open", "claimed"):
                thread.update({"state": "claimed", "owner": sender, "claimed_at": ts})
            elif kind == "release" and state == "claimed":
                # A session that stops mid-work hands the thread back rather than
                # leaving it claimed by a lane that is no longer there.
                thread["state"] = "open"
                for key in ("owner", "claimed_at"):
                    thread.pop(key, None)
            elif kind in ("done", "drop") and state in ("open", "claimed"):
                thread.update({"state": "done" if kind == "done" else "dropped",
                               "closed_by": sender, "closed_at": ts})
                if event.get("body") is not None:
                    thread["resolution"] = event["body"]
                if sender in lanes:
                    lanes[sender]["closed"] += 1
            elif kind == "reopen" and state in ("done", "dropped"):
                thread["state"] = "open"
                for key in ("owner", "claimed_at", "closed_by", "closed_at", "resolution"):
                    thread.pop(key, None)
        elif kind == "drop" and state == "logged":
            thread.update({"state": "retracted", "closed_by": sender, "closed_at": ts})
        elif kind == "reopen" and state == "retracted":
            thread["state"] = "logged"
            for key in ("closed_by", "closed_at"):
                thread.pop(key, None)
    for thread in threads:
        ttl = _as_int(thread.get("ttl"))
        if thread["class"] == "action" and thread["state"] == "open" and ttl > 0 \
                and _as_int(thread.get("ts")) + ttl < now:
            thread["state"] = "expired"
    return {"threads": threads, "by_id": by_id, "lanes": lanes, "ids": ids}


def relay_resolve(ref, by_id):
    ref = relay_line(ref)
    if ref.startswith("#"):
        ref = ref[1:]
    ref = ref.lower()[:40]
    if not ref:
        raise BodhiError("a thread id is required; run `python3 bin/bodhi.py relay list --all` to see them")
    if ref in by_id:
        return ref
    matches = sorted(tid for tid in by_id if tid.startswith(ref)) if len(ref) >= 4 else []
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise BodhiError("'" + ref + "' matches " + str(len(matches)) + " threads (" +
                         ", ".join(matches) + "); type more of the id")
    if len(ref) < 4:
        raise BodhiError("no thread '" + ref + "'; a short id needs at least 4 characters "
                         "(ids look like c4k2q9). Run relay list --all to see them")
    raise BodhiError("no thread '" + ref + "' in this vault's relay; run relay list --all to see them")


def relay_transition_error(thread, kind):
    state, tid = thread["state"], thread["id"]
    if kind == "reply":
        return ""
    if thread["class"] == "action":
        if kind in ("claim", "done", "drop") and state in ("open", "claimed", "expired"):
            return ""
        if kind == "reopen" and state in ("done", "dropped"):
            return ""
        if kind == "release" and state == "claimed":
            return ""
        if kind == "reopen":
            return "thread %s is %s; only a done or dropped thread can be reopened" % (tid, state)
        if kind == "release":
            return ("thread %s is %s; only a claimed thread can be released. Claim it first, "
                    "or leave it %s" % (tid, state, state))
        return "thread %s is %s; reopen it first: relay reopen %s \"why\"" % (tid, state, tid)
    if kind == "drop" and state == "logged":
        return ""
    if kind == "reopen" and state == "retracted":
        return ""
    if kind == "drop":
        return "thread %s is already retracted; relay reopen %s restores it" % (tid, tid)
    return ("thread %s is a %s (%s); a note or decision takes reply, drop (to retract it) or "
            "reopen (to restore it), not %s" % (tid, thread["kind"], state, kind))


def relay_new_id(taken):
    for length in (5,) * 100 + (8,) * 100:
        candidate = "c" + "".join(secrets.choice(RELAY_ID_CHARS) for _ in range(length))
        if candidate not in taken:
            return candidate
    raise BodhiError("could not find an unused relay id")


def relay_build(request, fold, now):
    """Validate one request against the current fold. Returns the event to append."""
    kind = relay_line(request.get("kind")).lower()
    if kind == "decide":
        kind = "decision"
    if kind not in RELAY_STARTERS and kind not in RELAY_TRANSITIONS:
        raise BodhiError("kind must be one of: note decision handoff poke claim release done "
                         "drop reopen reply")
    title, body = relay_line(request.get("title")), relay_text(request.get("body"))
    if len(title) > RELAY_MAX_TITLE:
        raise BodhiError("a title is limited to %d characters (this one has %d); put the rest in "
                         "the body" % (RELAY_MAX_TITLE, len(title)))
    if len(body) > RELAY_MAX_BODY:
        raise BodhiError("a body is limited to %d characters (this one has %d); save the long "
                         "text as a file in the vault and name its path" % (RELAY_MAX_BODY, len(body)))
    if RELAY_SECRET.search(title) or RELAY_SECRET.search(body):
        raise BodhiError("refused: that looks like a credential. The relay is plain text in the "
                         "vault and its Git history. Keep keys in your harness's secret store and "
                         "refer to them by name. Nothing was written")
    event = {"kind": kind, "ts": int(now), "from": relay_lane(request.get("from")) or "unsigned"}
    if kind in RELAY_STARTERS:
        if not title:
            raise BodhiError("a " + kind + " needs a title")
        event["title"] = title
        if body:
            event["body"] = body
        event["to"] = relay_lane(request.get("to")) or "any"
        ttl = request.get("ttl")
        if ttl is not None and str(ttl) != "":
            if not re.fullmatch(r"\d+", str(ttl)) or int(ttl) > RELAY_MAX_TTL:
                raise BodhiError("ttl must be whole seconds from 0 to %d (30 days); 0 never "
                                 "expires" % RELAY_MAX_TTL)
            event["ttl"] = int(ttl)
        elif kind == "poke":
            event["ttl"] = RELAY_POKE_TTL
    else:
        target = relay_resolve(request.get("re"), fold["by_id"])
        why = relay_transition_error(fold["by_id"][target], kind)
        if why:
            raise BodhiError(why)
        if not body and title:
            body = title
        if kind == "reply" and not body:
            raise BodhiError("a reply needs text: relay reply " + target + " \"text\"")
        event["re"] = target
        if body:
            event["body"] = body
    event["id"] = relay_new_id(fold["ids"])
    return event


@contextlib.contextmanager
def relay_lock(vault):
    """Serialize writers on this machine: read, validate and append happen under one lock.

    The lock file lives inside .git so it never shows as an untracked change; a vault
    without a .git directory falls back to relay/.lock, which the template ignores.
    """
    lock_path = vault / ".git" / "bodhi-relay.lock"
    if not lock_path.parent.is_dir():
        lock_path = vault / "relay" / ".lock"
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif msvcrt is not None:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
            elif msvcrt is not None:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)


def relay_write(vault, request, now=None):
    now = time.time() if now is None else now
    (vault / "relay").mkdir(exist_ok=True)
    ledger = vault / RELAY_LEDGER
    with relay_lock(vault):
        events, _ = relay_events(vault) if ledger.is_file() else ([], 0)
        event = relay_build(request, relay_fold(events, now), now)
        append_jsonl(ledger, event)
        try:
            git(vault, "add", "--", RELAY_LEDGER)
            git(vault, "commit", "-q", "--only", "-m", "Bodhi relay: %s %s from %s" %
                (event["kind"], event["id"], event["from"]), "--", RELAY_LEDGER)
            committed = "committed"
        except BodhiError as exc:
            # The ledger line is the record; a failed commit is reported, not hidden.
            committed = "not committed: " + str(exc)
    return event, committed


def _age(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "%dm ago" % (seconds // 60)
    if seconds < 172800:
        return "%dh ago" % (seconds // 3600)
    return "%dd ago" % (seconds // 86400)


def _utc(ts):
    return datetime.fromtimestamp(_as_int(ts), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _oneline(text, limit):
    text = re.sub(r"\s*\n\s*", " / ", text or "")
    return text if len(text) <= limit else text[:limit - 3] + "..."


def relay_for_lane(thread, lane):
    if not lane:
        return True
    return (thread.get("to") or "any") == "any" or lane in (thread.get("to"), thread.get("from"),
                                                           thread.get("owner"))


def relay_summary(fold, lane):
    """Everything a reader needs, ranked for attention: open, then expired, then claimed."""
    visible = [thread for thread in fold["threads"] if relay_for_lane(thread, lane)]
    rank = {"open": 0, "expired": 1, "claimed": 2}

    def severity(thread):
        meta = thread.get("meta") if isinstance(thread.get("meta"), dict) else {}
        return {"critical": 2, "warning": 1}.get(meta.get("severity"), 0)

    # Timestamps are whole seconds; within one second, later in the ledger counts as newer.
    order = {thread["id"]: index for index, thread in enumerate(fold["threads"])}
    active = sorted((t for t in visible if t["state"] in rank),
                    key=lambda t: (rank[t["state"]], -severity(t), -t["updated"], -order[t["id"]]))
    closed = sorted((t for t in visible if t["state"] in ("done", "dropped")),
                    key=lambda t: (-_as_int(t.get("closed_at")), -order[t["id"]]))
    records = sorted((t for t in visible if t["class"] == "record" and t["state"] == "logged"),
                     key=lambda t: (-_as_int(t.get("ts")), -order[t["id"]]))
    retracted = [t for t in visible if t["state"] == "retracted"]
    return {"active": active, "closed": closed, "records": records, "retracted": retracted}


def relay_list_lines(summary, now, show_all):
    threads = summary["active"] + (summary["closed"] + summary["records"] + summary["retracted"]
                                   if show_all else [])
    lines = []
    for thread in threads:
        state = thread["state"]
        if state == "claimed" and thread.get("owner"):
            state += ":" + thread["owner"]
        route = "%s -> %s" % (thread.get("from", "?"), thread.get("to", "any"))
        lines.append("%-7s %-8s %-18s %-24s %8s  %s" % (
            thread["id"], thread["kind"], state, route,
            _age(now - thread["updated"]).replace(" ago", ""), thread.get("title", "")))
    return lines


def relay_show_text(thread, now):
    head = "%s  %s  %s" % (thread["id"], thread["kind"], thread["state"].upper())
    if thread["state"] == "claimed" and thread.get("owner"):
        head += " by " + thread["owner"]
    elif thread.get("closed_by"):
        head += " by " + thread["closed_by"]
    lines = [head, thread.get("title", ""),
             "%s -> %s, %s (%s)" % (thread.get("from", "?"), thread.get("to", "any"),
                                    _utc(thread.get("ts")), _age(now - _as_int(thread.get("ts"))))]
    if thread.get("ttl") and thread["class"] == "action":
        lines.append("expires %s unless claimed" % _utc(_as_int(thread["ts"]) + _as_int(thread["ttl"])))
    if thread.get("body"):
        lines += ["", thread["body"]]
    if thread["log"]:
        lines.append("")
        lines.append("History, oldest first:")
        for entry in thread["log"]:
            lines.append(("  %-8s %-16s %s  %s" % (entry["kind"], entry.get("from", "?"),
                                                   _utc(entry.get("ts")), entry.get("body", ""))).rstrip())
    return "\n".join(lines)


def _thread_brief(thread, now):
    state = thread["state"].upper()
    if thread["state"] == "claimed" and thread.get("owner"):
        state += " by " + thread["owner"]
    line = "- `%s` %s %s -> %s, %s, %s: %s" % (
        thread["id"], thread["kind"], thread.get("from", "?"), thread.get("to", "any"),
        _age(now - _as_int(thread.get("ts"))), state, thread.get("title", ""))
    if thread.get("body"):
        line += "\n  " + _oneline(thread["body"], 240)
    replies = [entry for entry in thread["log"] if entry["kind"] == "reply"]
    if replies:
        latest = replies[-1]
        line += "\n  latest reply (%s, %s): %s" % (latest.get("from", "?"),
                                                   _age(now - _as_int(latest.get("ts"))),
                                                   _oneline(latest.get("body", ""), 160))
    return line


def relay_brief(vault, events, unreadable, fold, lane, now):
    summary = relay_summary(fold, lane)
    lanes = sorted(fold["lanes"].values(), key=lambda item: (-item["last_seen"], item["id"]))
    out = ["# Relay brief " + ("for " + lane if lane else "for every lane"), ""]
    ledger_note = "%s, %d events" % (RELAY_LEDGER, len(events))
    if unreadable:
        ledger_note += ", %d unreadable lines skipped" % unreadable
    out.append("Vault `%s`; ledger %s." % (vault, ledger_note))
    out.append("Lanes seen: " + (", ".join(item["id"] for item in lanes) or "none yet") +
               " (from who wrote and who was addressed; there is no roster).")
    out += ["", "## Open threads" + (" for " + lane + " or anyone" if lane else "")]
    active = summary["active"]
    out += [_thread_brief(thread, now) for thread in active[:15]] or ["- none open"]
    if len(active) > 15:
        out.append("- ...and %d more: relay list%s" % (len(active) - 15,
                                                         " --for " + lane if lane else ""))
    out += ["", "## Decisions and notes, newest first"]
    records = summary["records"][:8]
    out += ["- `%s` %s, %s, %s: %s%s" % (t["id"], t["kind"], t.get("from", "?"),
                                          _utc(t.get("ts"))[:10], t.get("title", ""),
                                          "\n  " + _oneline(t["body"], 240) if t.get("body") else "")
            for t in records] or ["- none recorded yet"]
    if summary["closed"]:
        out += ["", "## Recently closed"]
        out += ["- `%s` %s %s by %s, %s: %s%s" % (
            t["id"], t["kind"], t["state"], t.get("closed_by", "?"),
            _age(now - _as_int(t.get("closed_at"))), t.get("title", ""),
            " -- " + _oneline(t["resolution"], 200) if t.get("resolution") else "")
            for t in summary["closed"][:5]]
    out += ["", "## Write back", "```", RELAY_WRITE_BACK, "```",
            "Sign with --as <lane> or BODHI_LANE. Ids accept any unique prefix of 4+ characters. "
            "Never put credentials here: the ledger is plain text in the vault's Git history."]
    return "\n".join(out) + "\n"


def _say(text):
    """Print text even on a console that cannot encode every character."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(encoding, "replace").decode(encoding))


def _relay_body(value):
    if value == "-":
        return sys.stdin.read()
    return value or ""


def relay_command(args):
    vault = relay_vault(args.vault)
    who = relay_lane(args.as_lane or os.environ.get("BODHI_LANE", ""))
    now = time.time()
    command = args.relay_command
    if command in ("note", "decide", "decision", "handoff", "poke"):
        request = {"kind": "decision" if command == "decide" else command, "from": who,
                   "title": args.title, "body": _relay_body(args.body),
                   "to": getattr(args, "to", None) or "any", "ttl": getattr(args, "ttl", None)}
    elif command in RELAY_TRANSITIONS:
        if command == "reply" and not args.text:
            raise BodhiError("a reply needs text: relay reply <id> \"text\"")
        request = {"kind": command, "from": who, "re": args.id, "body": _relay_body(args.text)}
    else:
        events, unreadable = relay_events(vault)
        fold = relay_fold(events, now)
        if command == "list":
            lane = relay_lane(args.for_lane or "")
            summary = relay_summary(fold, lane)
            if args.json:
                emit(summary if args.all else {"active": summary["active"]})
                return 0
            lines = relay_list_lines(summary, now, args.all)
            for line in lines:
                _say(line)
            if not lines:
                print("relay: nothing open" + (" for " + lane + " or anyone" if lane else "") +
                      " in " + str(vault / RELAY_LEDGER), file=sys.stderr)
            if unreadable:
                print("relay: %d unreadable ledger lines skipped" % unreadable, file=sys.stderr)
            return 0
        if command == "show":
            thread = fold["by_id"][relay_resolve(args.id, fold["by_id"])]
            if args.json:
                emit(thread)
            else:
                _say(relay_show_text(thread, now))
            return 0
        lane = relay_lane(args.for_lane or "") or who
        _say(relay_brief(vault, events, unreadable, fold, lane, now).rstrip("\n"))
        return 0
    event, committed = relay_write(vault, request, now)
    emit({"event": event, "ledger": RELAY_LEDGER, "vault": str(vault), "git": committed})
    target = (" on " + event["re"]) if event.get("re") else (
        " -> " + event["to"] if event.get("to", "any") != "any" else "")
    print("relay: %s %s%s as %s" % (event["kind"], event["id"], target, event["from"]), file=sys.stderr)
    if event["from"] == "unsigned":
        print("relay: written as 'unsigned'. Sign with --as <lane> or BODHI_LANE so the next "
              "reader knows who wrote it.", file=sys.stderr)
    return 0


def add_relay_parser(sub):
    relay = sub.add_parser(
        "relay", help="leave notes, decisions, handoffs and pokes for other sessions and harnesses",
        description="An append-only ledger in the vault (relay/ledger.jsonl) that any harness "
                    "with a shell can read and write. Ids accept any unique prefix of 4+ "
                    "characters. A body of - is read from standard input.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", help="the vault folder (default: BODHI_VAULT, this CLI's vault, "
                                        "or the nearest vault at or above the current folder)")
    common.add_argument("--as", dest="as_lane", help="your lane name (default: BODHI_LANE)")
    actions = relay.add_subparsers(dest="relay_command", required=True)
    for name, help_text in (("note", "context the next session needs"),
                            ("decide", "a settled call and why, so nobody relitigates it"),
                            ("handoff", "work for a lane or anyone, with what done looks like"),
                            ("poke", "look at this soon; expires after a day unless claimed")):
        starter = actions.add_parser(name, parents=[common], help=help_text)
        if name in ("handoff", "poke"):
            starter.add_argument("--to", default="any", help="lane to address (default any)")
            starter.add_argument("--ttl", help="seconds until an unclaimed thread reads as expired")
        starter.add_argument("title")
        starter.add_argument("body", nargs="?", default="")
    for name, help_text in (("claim", "take a thread before you start on it"),
                            ("release", "stopping before it is done: hand it back as open"),
                            ("done", "close it with what you verified"),
                            ("drop", "close it without doing it, or retract a note or decision"),
                            ("reopen", "open a closed thread, or restore a retracted record"),
                            ("reply", "add to a thread without changing its state")):
        move = actions.add_parser(name, parents=[common], help=help_text)
        move.add_argument("id")
        move.add_argument("text", nargs="?", default="")
    listing = actions.add_parser("list", parents=[common], help="open threads, one per line")
    listing.add_argument("--for", dest="for_lane", help="only threads for this lane or anyone")
    listing.add_argument("--all", action="store_true", help="also closed threads, notes and decisions")
    listing.add_argument("--json", action="store_true")
    show = actions.add_parser("show", parents=[common], help="one thread and its whole history")
    show.add_argument("id")
    show.add_argument("--json", action="store_true")
    brief = actions.add_parser("brief", parents=[common],
                               help="markdown for the start of a session: what is waiting, what was decided")
    brief.add_argument("--for", dest="for_lane", help="lane to brief (default: --as or BODHI_LANE)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bodhi v0.01 local vault")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser(
        "init", help="create a local Git vault for Player One",
        description="A guided first run: six short questions, one at a time, each with a "
                    "default. Color and the Bodhi mark appear only on an interactive terminal; "
                    "NO_COLOR turns color off, and --plain or BODHI_PLAIN=1 turns off both.")
    init_parser.add_argument("dest", type=Path)
    init_parser.add_argument("--answers", metavar="JSON_OR_PATH", help="JSON object or JSON file path; skips prompts")
    init_parser.add_argument("--plain", action="store_true",
                             help="no art and no color: plain text for screen readers and logs")
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
    add_relay_parser(sub)
    args = parser.parse_args(argv)
    dest = args.dest.expanduser().absolute() if getattr(args, "dest", None) is not None else None
    try:
        if args.command == "relay":
            return relay_command(args)
        if args.command == "init":
            nonempty_target(dest)
            if args.answers is not None:
                emit(init_vault(dest, read_answers(args.answers)))
            else:
                voice = Voice(plain=args.plain)
                try:
                    answers = interactive_answers(dest, voice)
                except KeyboardInterrupt:
                    voice.line()
                    raise BodhiError("setup stopped; nothing was created")
                result = init_vault(dest, answers)
                setup_summary(voice, answers)
                what_happens_next(voice, dest, answers)
                emit(result)
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
    except RelayMissing as exc:
        # Absent is not empty: exit 3, the same way replay reports a missing ledger.
        print("Bodhi: " + str(exc), file=sys.stderr)
        return 3
    except (BodhiError, OSError, EOFError, KeyboardInterrupt) as exc:
        print("Bodhi: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
