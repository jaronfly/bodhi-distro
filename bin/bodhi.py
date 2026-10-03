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
COMFORT_CHOICES = ("new", "some", "comfortable")
CHAT_CHOICES = ("none", "telegram", "discord", "slack", "whatsapp", "signal", "email", "teams", "other")
DEVICE_CHOICES = ("this_computer", "another_computer", "phone", "tablet", "home_server")
NOTES_CHOICES = ("nowhere_yet", "paper", "notes_app", "obsidian", "notion", "docs", "other")
DELIVERY_CHOICES = ("pull", "push", "both", "undecided")
DETECTED_KEYS = {"harnesses", "ollama", "lm_studio", "obsidian"}
DISPOSITIONS = ("keep", "project", "hold", "dismiss")
LOCAL_GIT_COMMANDS = {"init", "add", "commit", "rev-parse", "log", "cat-file", "status"}
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


def _choice_list(raw, key, allowed):
    items = raw.get(key, [])
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        raise BodhiError(key + " must be a list of names")
    items = [choice(item, allowed, key) for item in items]
    if len(items) != len(set(items)):
        raise BodhiError(key + " contains duplicates")
    return items


def _optional_choice(raw, key, allowed):
    value = raw.get(key, "")
    if value is None or value == "":
        return ""
    return choice(value, allowed, key)


def _named_other(raw, key, chosen, name_key):
    name = raw.get(name_key, "")
    if not isinstance(name, str):
        raise BodhiError(name_key + " must be a string")
    if chosen != "other" and name.strip():
        raise BodhiError(name_key + " applies only when " + key + " is other")
    return name.strip() if chosen == "other" else ""


def _detected(raw):
    """What setup observed on this computer, kept apart from what Player One answered."""
    found = raw.get("detected", {})
    if not isinstance(found, dict) or set(found) - DETECTED_KEYS:
        raise BodhiError("detected must be an object with only: " + ", ".join(sorted(DETECTED_KEYS)))
    harnesses = found.get("harnesses", [])
    if not isinstance(harnesses, list) or any(item not in HARNESS_CHOICES for item in harnesses):
        raise BodhiError("detected.harnesses must list harness names")
    flags = {key: found.get(key, False) for key in ("ollama", "lm_studio", "obsidian")}
    if any(not isinstance(value, bool) for value in flags.values()):
        raise BodhiError("detected ollama, lm_studio and obsidian must be true or false")
    return dict(flags, harnesses=list(harnesses)) if found else {}


def normalize_answers(raw):
    if not isinstance(raw, dict):
        raise BodhiError("answers must be a JSON object")
    allowed = {"priority", "os", "harness", "harness_name", "model_access",
               "capture_surfaces", "next_capability", "terminal_comfort", "chat_app",
               "chat_app_name", "devices", "notes_today", "notes_name", "findings_delivery",
               "detected"}
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
    chat_app = _optional_choice(raw, "chat_app", CHAT_CHOICES)
    notes_today = _optional_choice(raw, "notes_today", NOTES_CHOICES)
    return {
        "priority_verbatim": priority,
        "os": os_name,
        "primary_harness": harness,
        "other_harness_name": harness_name.strip() if harness == "other" else "",
        "model_access": model_access,
        "capture_interests": surfaces,
        "capture_enabled": False,
        "next_capability_verbatim": next_capability,
        # Optional answers; "" or [] means the question was skipped.
        "terminal_comfort": _optional_choice(raw, "terminal_comfort", COMFORT_CHOICES),
        "chat_app": chat_app,
        "other_chat_app_name": _named_other(raw, "chat_app", chat_app, "chat_app_name"),
        "devices": _choice_list(raw, "devices", DEVICE_CHOICES),
        "notes_today": notes_today,
        "other_notes_name": _named_other(raw, "notes_today", notes_today, "notes_name"),
        "findings_delivery": _optional_choice(raw, "findings_delivery", DELIVERY_CHOICES),
        "detected_at_setup": _detected(raw),
    }


# Harnesses this seed knows how to find, by the command each one installs.
HARNESS_BINARIES = (("claude-code", "claude"), ("codex", "codex"), ("hermes", "hermes"),
                    ("openclaw", "openclaw"))


def detect_tools(env=None):
    """Look, never install: which harnesses and tools are already on this computer."""
    env = os.environ if env is None else env
    search = env.get("PATH", os.defpath)
    home = Path(env.get("HOME") or str(Path.home()))

    def found(name):
        return shutil.which(name, path=search) is not None

    lm_studio = found("lms") or Path("/Applications/LM Studio.app").exists() or \
        (home / ".lmstudio").is_dir()
    obsidian = found("obsidian") or Path("/Applications/Obsidian.app").exists() or any(
        (home / part).is_dir() for part in (".config/obsidian", "Library/Application Support/obsidian",
                                             ".var/app/md.obsidian.Obsidian"))
    return {"harnesses": [key for key, command in HARNESS_BINARIES if found(command)],
            "ollama": found("ollama"), "lm_studio": bool(lm_studio), "obsidian": bool(obsidian)}


def detected_os():
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system(), "other")


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
# The same mark as the SVG path on bodhi.fyi (one unit per cell); a test checks they agree.
MARK_SVG_PATH = ("M3 0h2v1h-2zM6 0h2v1h-2zM5 1h1v1h-1zM5 2h1v1h-1zM0 3h5v1h-5zM6 3h5v1h-5z"
                 "M0 4h5v1h-5zM7 4h4v1h-4zM0 5h4v1h-4zM5 5h2v1h-2zM8 5h3v1h-3zM0 6h3v1h-3z"
                 "M4 6h4v1h-4zM9 6h2v1h-2zM0 7h3v1h-3zM4 7h7v1h-7zM0 8h2v1h-2zM3 8h8v1h-8z"
                 "M0 9h11v1h-11z")
# Where the saffron seed sits while it sprouts: the top of the root channel (row, column).
MARK_SEED = (3, 5)
SPROUT_SECONDS = 1.5
SETUP_QUESTIONS = 6
OPTIONAL_QUESTIONS = 5

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
COMFORT_LABELS = {"new": "new to it; explain as we go", "some": "I can follow steps",
                  "comfortable": "comfortable; keep it short"}
CHAT_LABELS = {"none": "none, or not for this", "telegram": "Telegram", "discord": "Discord",
               "slack": "Slack", "whatsapp": "WhatsApp", "signal": "Signal", "email": "email",
               "teams": "Microsoft Teams", "other": "something else; you can name it next"}
# Chat apps the Hermes gateway documents (hermes gateway setup), checked 2026-09-30.
HERMES_GATEWAY_APPS = ("telegram", "discord", "slack", "whatsapp", "signal", "email", "teams")
DEVICE_LABELS = {"this_computer": "this computer", "another_computer": "another computer",
                 "phone": "a phone", "tablet": "a tablet",
                 "home_server": "a home server, a bodhinas"}
NOTES_LABELS = {"nowhere_yet": "nowhere yet", "paper": "on paper",
                "notes_app": "a notes app on a phone or computer", "obsidian": "Obsidian",
                "notion": "Notion", "docs": "documents, such as Google Docs or Word",
                "other": "somewhere else; you can name it next"}
DELIVERY_LABELS = {"pull": "I ask when I want something", "push": "send me short findings",
                   "both": "both", "undecided": "not sure yet"}
CAPTURE_LABELS = {"web_history": "your browser history", "app_usage": "which apps you use",
                  "audio": "recordings you choose", "screen": "what is on your screen"}

# Tools the seed can recommend, keyed by the capture surface they serve.
# Self-hosted first; anything cloud says so plainly. Entries are OFFERS, never
# installations: `bodhi recommend` prints them, a session proposes them, and
# Player One decides. No entry here phones home or needs a key.
TOOL_CATALOG = {
    "screenpipe": {
        "label": "screenpipe",
        "serves": ("screen", "app_usage", "audio"),
        "kind": "local, open source",
        "what": ("records your screen and mic locally and makes them searchable; "
                 "Bodhi reads the local index, nothing leaves the machine"),
        "why": "the richest single surface: what you actually read, build, and return to",
        "commands": ("screenpipe", "sp-control"),
        "get": "brew install screenpipe (macOS) or see screenpi.pe; always opt-in",
    },
    "browser-history-export": {
        "label": "a browser history export",
        "serves": ("web_history",),
        "kind": "a file you already own",
        "what": "your search and browsing history, exported by hand and handed to Bodhi",
        "why": "a map of what you actually wondered about, not what you say you did",
        "commands": (),
        "get": "browser settings -> export history; works with any browser",
    },
    "youtube-takeout": {
        "label": "a YouTube takeout",
        "serves": ("web_history", "audio"),
        "kind": "a file you already own",
        "what": "your watch and search history from Google Takeout",
        "why": "watch history is interest with timestamps; the most honest signal there is",
        "commands": (),
        "get": "takeout.google.com -> select YouTube -> 'history'; nothing else is needed",
    },
    "chat-exports": {
        "label": "your AI chat exports",
        "serves": ("web_history",),
        "kind": "files you already own",
        "what": "exports of your other AI conversations, pasted or dropped into the vault",
        "why": "the context you already gave away, returning to your own system",
        "commands": (),
        "get": "each chat app has an export; ChatGPT and Claude both do",
    },
}


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
        self.truecolor = env.get("COLORTERM", "").lower() in ("truecolor", "24bit")
        # Motion is decoration on top of color: never in CI, and never when asked not to.
        self.motion = self.color and not env.get("CI") and not env.get("BODHI_NO_MOTION")
        if width is None:
            width = shutil.get_terminal_size((80, 24)).columns if tty else 80
        self.width = max(20, min(80, int(width)))
        self.block = "█" if _can_encode(self.stream, "█") else "#"
        self.brief = False    # set when Player One is comfortable in a terminal
        self.explain = False  # set when Player One is new to the terminal

    def style(self, text, *names):
        if not self.color or not text or not names:
            return text
        codes = {"bold": "1", "dim": "2",
                 "sprout": "38;5;70" if self.palette_256 else "32",
                 "soil": "38;5;130" if self.palette_256 else "33",
                 # Saffron, #E8982A: exact on a truecolor terminal, nearest otherwise.
                 "seed": "38;2;232;152;42" if self.truecolor else
                         ("38;5;172" if self.palette_256 else "1;33")}
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


def svg_cells(path):
    """The filled cells of a pixel SVG path made of 'Mx yhWv1h-Wz' runs, as a MARK-style grid."""
    runs = [(int(x), int(y), int(w)) for x, y, w in re.findall(r"M(\d+) (\d+)h(\d+)v1h-\d+z", path)]
    width = max(x + w for x, _, w in runs)
    height = max(y for _, y, _ in runs) + 1
    grid = [["."] * width for _ in range(height)]
    for x, y, w in runs:
        for column in range(x, x + w):
            grid[y][column] = "#"
    return tuple("".join(row) for row in grid)


def sprout_frames():
    """The seed sprouting into the mark: whole cells only, never rotated or smoothed.

    Soil first, with the saffron seed ("o") at the top of the root channel; the roots
    carve downward; the stem rises; the leaves open; the seed is spent. The last frame
    is MARK exactly.
    """
    seed_row, seed_col = MARK_SEED

    def frame(carved_to, stem_from, leaves, seed=True):
        rows = []
        for index, row in enumerate(MARK):
            if index < MARK_SPROUT_ROWS:
                cells = ["." for _ in row]
                if index >= stem_from:
                    cells = [cell for cell in row]
                if index == 0 and leaves:
                    cells = [cell if abs(col - seed_col) <= leaves else "."
                             for col, cell in enumerate(row)]
            elif index <= carved_to:
                cells = list(row)
            else:
                cells = ["#"] * len(row)
            if seed and index == seed_row:
                cells[seed_col] = "o"
            rows.append("".join(cells))
        return tuple(rows)

    frames = [frame(seed_row, MARK_SPROUT_ROWS, 0)] * 2       # the seed in whole soil, held
    for carved in range(seed_row + 1, len(MARK)):              # the roots carve downward
        if frame(carved, MARK_SPROUT_ROWS, 0) != frames[-1]:
            frames.append(frame(carved, MARK_SPROUT_ROWS, 0))
    for stem_from in range(MARK_SPROUT_ROWS - 1, 0, -1):       # the stem rises
        frames.append(frame(len(MARK), stem_from, 0))
    frames.append(frame(len(MARK), 0, 1))                      # the leaves open
    frames.append(tuple(MARK))                                 # the seed is spent
    return frames


def render_frame(frame, block="█", style=None):
    """Draw one frame like render_mark, with the seed cell in saffron."""
    lines = []
    for index, row in enumerate(frame):
        part = "sprout" if index < MARK_SPROUT_ROWS else "soil"
        drawn = ""
        for cell in row:
            if cell == ".":
                drawn += "  "
            elif style is None:
                drawn += block * 2
            else:
                drawn += style(block * 2, "seed" if cell == "o" else part)
        lines.append(drawn)
    return lines


def _key_watcher(stream):
    """Return (pressed, restore): a non-blocking keypress check on a terminal, or None."""
    try:
        fd = stream.fileno()
        if not os.isatty(fd):
            return None, lambda: None
    except (AttributeError, ValueError, OSError):
        return None, lambda: None
    if msvcrt is not None and os.name == "nt":  # pragma: no cover - Windows
        return (lambda: msvcrt.kbhit() and (msvcrt.getwch() or True)), lambda: None
    try:
        import select
        import termios
        import tty
        saved = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    except (ImportError, OSError, ValueError):
        return None, lambda: None

    def pressed():
        ready, _, _ = select.select([fd], [], [], 0)
        if ready:
            os.read(fd, 64)
            return True
        return False

    def restore():
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        except (OSError, ValueError):
            pass
    return pressed, restore


def play_sprout(voice, indent="  ", pressed=None, sleep=time.sleep, keys=None):
    """Plant the seed on screen: about 1.5 seconds of motion, ending on the static mark.

    Motion needs color on an interactive terminal (so not --plain, NO_COLOR, TERM=dumb
    or a pipe), and is skipped when CI or BODHI_NO_MOTION is set. Any key skips to the
    end. Without motion the static mark is drawn as before, if art is allowed at all.
    Returns True when frames were animated.
    """
    if not voice.art or voice.width < MARK_MIN_WIDTH:
        return False
    if not voice.motion:
        for drawn in voice.mark_lines():
            voice.line(indent + drawn)
        return False
    frames = sprout_frames()
    restore = lambda: None  # noqa: E731
    if pressed is None:
        pressed, restore = _key_watcher(keys if keys is not None else sys.stdin)
    pause = SPROUT_SECONDS / (len(frames) - 1)
    voice.write("\x1b[?25l")  # hide the cursor while drawing
    try:
        for number, frame in enumerate(frames):
            if number:
                voice.write("\x1b[%dA" % len(frame))
            if pressed is not None and number < len(frames) - 1 and pressed():
                frame = frames[-1]
            for drawn in render_frame(frame, voice.block, voice.style):
                voice.write("\r\x1b[2K" + indent + drawn + "\n")
            if frame == frames[-1]:
                break
            sleep(pause)
    finally:
        restore()
        voice.write("\x1b[?25h")
    return True


def _read_line(voice, prompt="Your answer: ", eof_ok=False):
    try:
        if voice.stream is sys.stdout:
            value = input(prompt)
        else:
            voice.write(prompt)
            value = input()
    except EOFError:
        if eof_ok:
            voice.line()
            return None
        raise BodhiError("setup stopped before the last question; nothing was created")
    if not _isatty(sys.stdin):
        voice.line()  # keep a log readable when answers arrive from a pipe
    return value


def _question(voice, label, title, why, more=None):
    voice.line()
    voice.para(label + ". " + title, style=("bold",))
    if why and not voice.brief:
        voice.para(why, indent=2)
    if more and voice.explain:
        voice.para(more, indent=2)


def _more(voice, more):
    voice.para(more or "Nothing more to add here. Press Enter to keep the default.", indent=2)


def _help_hint(more):
    return " Type ? to hear more." if more else ""


def _ask_choice(voice, label, title, why, field, options, labels, default, default_note="",
                more=None):
    _question(voice, label, title, why, more)
    for index, value in enumerate(options, 1):
        voice.para("%d. %s (%s)" % (index, value, labels[value]), indent=2)
    voice.para("Press Enter to keep %s%s, or type a number or a name.%s"
               % (default, default_note, _help_hint(more)), indent=2)
    while True:
        raw = _read_line(voice).strip()
        if not raw:
            return default
        if raw == "?":
            _more(voice, more)
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        try:
            return choice(raw, options, field)
        except BodhiError:
            voice.problem("%s. Type a number from 1 to %d, a name such as %s, or press Enter "
                          "to keep %s." % (raw, len(options), options[0], default))


def _ask_many(voice, label, title, why, field, options, labels, default=(), more=None):
    _question(voice, label, title, why, more)
    for index, value in enumerate(options, 1):
        voice.para("%d. %s (%s)" % (index, value, labels[value]), indent=2)
    keep = ", ".join(default) if default else "none"
    voice.para("Press Enter for %s, or type numbers or names separated by commas.%s"
               % (keep, _help_hint(more)), indent=2)
    while True:
        raw = _read_line(voice).strip()
        if not raw:
            return list(default)
        if raw == "?":
            _more(voice, more)
            continue
        if raw.lower() == "none":
            return []
        chosen, error = [], ""
        for part in [item for item in re.split(r"[,\s]+", raw) if item]:
            if part.isdigit() and 1 <= int(part) <= len(options):
                chosen.append(options[int(part) - 1])
                continue
            try:
                chosen.append(choice(part, options, field))
            except BodhiError:
                error = part
                break
        if not error and len(chosen) != len(set(chosen)):
            error = raw + " names one choice twice"
        if not error:
            return chosen
        voice.problem("%s. Type numbers from 1 to %d or names such as %s, or press Enter for "
                      "%s." % (error, len(options), options[0], keep))


def _ask_words(voice, label, title, why, skip_note, more=None):
    _question(voice, label, title, why, more)
    voice.para(skip_note + _help_hint(more), indent=2)
    while True:
        raw = _read_line(voice)
        if raw.strip() == "?" and more:
            _more(voice, more)
            continue
        return raw


def _core(number):
    return "Question %d of %d" % (number, SETUP_QUESTIONS)


def _optional(number):
    return "Optional question %d of %d" % (number, OPTIONAL_QUESTIONS)


def _names(keys, labels):
    return ", ".join(labels.get(key, key) for key in keys)


def ask_raw_answers(voice, saved_where, found):
    """The Ready Player One questions. Returns raw answers in --answers form; writes nothing."""
    voice.line(voice.style("Bodhi seed, setup (v" + VERSION + ")", "bold"))
    voice.line()
    voice.para("Hello, Player One.")
    voice.line()
    voice.para("Bodhi is a practice more than an app: write things down, keep exact words, "
               "check claims against evidence, and sign your work. This setup gets that practice "
               "ready next to the AI tools you already use.")
    voice.line()
    voice.para("Six short questions follow, one at a time, then five optional ones. Each shows a "
               "default: press Enter to keep it or to skip. Type ? at a question to hear more. "
               "You can change any answer later.")
    voice.line()
    voice.para("Nothing here records you, installs tools, connects accounts, or sends anything "
               "anywhere. " + saved_where[0])
    voice.verbatim(shown_path(saved_where[1]))
    raw = {"detected": found}
    raw["priority"] = _ask_words(
        voice, _core(1), "What is one thing you want AI to help you change or make right now?",
        "Your words are kept exactly as you type them. Your first agent session will read "
        "them back and ask whether they still fit.",
        "Press Enter to skip; your first session will ask you instead.",
        more="This is the first thing you want, in your own words: a project, a chore, a question "
             "you keep circling. It becomes the first task, not a lifetime plan.")
    raw["os"] = _ask_choice(
        voice, _core(2), "Which computer will hold your Bodhi folder?",
        "So that agents suggest commands that work on your machine.",
        "os", OS_CHOICES, OS_LABELS, detected_os(), " (detected)")
    harness_default, harness_note = "undecided", ""
    if found["harnesses"]:
        harness_default, harness_note = found["harnesses"][0], " (found on this computer)"
        voice.line()
        voice.para("Found on this computer: " + _names(found["harnesses"], HARNESS_LABELS) + ".")
    raw["harness"] = _ask_choice(
        voice, _core(3), "Which AI app or agent will you mainly use with this folder?",
        "Bodhi works through the AI tool you already use. It does not install one.",
        "harness", HARNESS_CHOICES, HARNESS_LABELS, harness_default, harness_note,
        more="A harness is the app or command that runs an AI model for you and lets it read "
             "files and use tools, such as Claude Code, Codex, Hermes, or OpenClaw. If you only "
             "chat in a browser, pick undecided; the installer can help later.")
    raw["harness_name"] = ""
    if raw["harness"] == "other":
        voice.para("What is it called? Press Enter to skip.", indent=2)
        raw["harness_name"] = _read_line(voice)
    model_default, model_note = ("local", " (Ollama found)") if found["ollama"] else ("undecided", "")
    raw["model_access"] = _ask_choice(
        voice, _core(4), "What kind of AI model access do you have?",
        "Bodhi needs no keys of its own. This only helps agents make realistic suggestions.",
        "model_access", MODEL_CHOICES, MODEL_LABELS, model_default, model_note,
        more="Local means a model running on your own computer, for example with Ollama or LM "
             "Studio. Cloud means a service you sign in to, such as a Claude, ChatGPT, or Gemini "
             "plan. Keys and logins stay with those tools; Bodhi never asks for them.")
    raw["capture_surfaces"] = _ask_many(
        voice, _core(5), "Is there anything you might want Bodhi to learn from, later on?",
        "These are interests only. Nothing is recorded now, and nothing starts without your "
        "say-so in a later session.", "capture_surfaces", CAPTURE_CHOICES, CAPTURE_LABELS)
    raw["next_capability"] = _ask_words(
        voice, _core(6), "What would you like Bodhi to be able to do next?",
        "One small ability, in your own words. It is kept exactly as you type it.",
        "Press Enter to skip.")
    raw.update(optional_answers(voice, found))
    return raw


def optional_answers(voice, found):
    voice.line()
    voice.para("That covers the basics. Five optional questions help Bodhi fit how you work: "
               "how much explaining you want, a chat app, your devices, where your notes live, "
               "and how findings should reach you. About a minute.")
    voice.para("Press Enter to answer them, or type n to skip them.", indent=2)
    gate = _read_line(voice, eof_ok=True)
    if gate is None:
        voice.para("No more answers arrived, so the optional questions were skipped.")
        return {}
    if gate.strip().lower() in ("n", "no", "skip"):
        return {}
    raw = {}
    raw["terminal_comfort"] = _ask_choice(
        voice, _optional(1), "How comfortable are you with a terminal?",
        "This sets how much Bodhi explains, here and in later sessions.",
        "terminal_comfort", COMFORT_CHOICES, COMFORT_LABELS, "some",
        more="A terminal is the text window where you type commands, such as Terminal on a Mac "
             "or PowerShell on Windows. Nobody has to be an expert; this only sets the pace.")
    voice.brief = raw["terminal_comfort"] == "comfortable"
    voice.explain = raw["terminal_comfort"] == "new"
    raw["chat_app"] = _ask_choice(
        voice, _optional(2), "Is there a chat app where you would like to reach Bodhi?",
        "Some harnesses, such as Hermes, can bring an agent into a chat app. Nothing is "
        "connected now.", "chat_app", CHAT_CHOICES, CHAT_LABELS, "none",
        more="Hermes Agent's gateway supports Telegram, Discord, Slack, WhatsApp, Signal, email "
             "and Microsoft Teams, among others. Hermes asks for the app's token itself; Bodhi "
             "never sees it.")
    if raw["chat_app"] == "other":
        voice.para("What is it called? Press Enter to skip.", indent=2)
        raw["chat_app_name"] = _read_line(voice)
    raw["devices"] = _ask_many(
        voice, _optional(3), "Which devices do you want to use Bodhi from?",
        "So suggestions fit where you are. Nothing is installed on them.",
        "devices", DEVICE_CHOICES, DEVICE_LABELS, default=("this_computer",),
        more="A home server, which the first Bodhi called its bodhinas, is a computer that stays "
             "on at home and can run models or scheduled jobs. Most people start with one "
             "computer.")
    notes_default, notes_note = ("obsidian", " (Obsidian found)") if found["obsidian"] else \
        ("nowhere_yet", "")
    raw["notes_today"] = _ask_choice(
        voice, _optional(4), "Where do you keep notes today?",
        "Bodhi works with notes where they already are before suggesting anything new.",
        "notes_today", NOTES_CHOICES, NOTES_LABELS, notes_default, notes_note,
        more="This does not move or read your notes. It helps Bodhi ask better questions later, "
             "for example before suggesting a notes app or a memory graph.")
    if raw["notes_today"] == "other":
        voice.para("What is it called? Press Enter to skip.", indent=2)
        raw["notes_name"] = _read_line(voice)
    raw["findings_delivery"] = _ask_choice(
        voice, _optional(5), "How should findings reach you?",
        "A finding is something an agent noticed that you did not ask about.",
        "findings_delivery", DELIVERY_CHOICES, DELIVERY_LABELS, "pull",
        more="Pull means Bodhi keeps findings until you ask. Push means it sends short notes "
             "through a channel you choose, once one is set up. You can change this any time.")
    return raw


def interactive_answers(dest, voice=None, found=None):
    """Ask the setup questions one at a time. Nothing is written until they are done."""
    voice = voice or Voice()
    found = detect_tools() if found is None else found
    raw = ask_raw_answers(voice, ("Your answers are saved in one file inside the new folder:",
                                  dest / "context" / "player_one.json"), found)
    return normalize_answers(raw)


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
    chat = answers.get("chat_app", "")
    if chat == "other" and answers.get("other_chat_app_name"):
        chat = "other: " + answers["other_chat_app_name"]
    notes = answers.get("notes_today", "")
    if notes == "other" and answers.get("other_notes_name"):
        notes = "other: " + answers["other_notes_name"]
    optional = (("Terminal comfort", answers.get("terminal_comfort", "")), ("Chat app", chat),
                ("Devices", ", ".join(answers.get("devices", []))), ("Notes today", notes),
                ("Findings", answers.get("findings_delivery", "")))
    rows += tuple((label, value) for label, value in optional if value)
    found = answers.get("detected_at_setup") or {}
    seen = [HARNESS_LABELS[key] for key in found.get("harnesses", [])]
    seen += [name for key, name in (("ollama", "Ollama"), ("lm_studio", "LM Studio"),
                                    ("obsidian", "Obsidian")) if found.get(key)]
    if found:
        rows += (("Found on this computer", ", ".join(seen) or "none of the tools Bodhi looks for"),)
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
        play_sprout(voice)
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
        voice.para("In a terminal, that is these two lines" + (
            " (cd means: go to this folder)" if answers.get("terminal_comfort") == "new" else "")
            + ":", indent=5)
        voice.verbatim("cd " + folder, indent=7)
        voice.verbatim(HARNESS_START[harness], indent=7)
    voice.para("2. Say: Hello, Bodhi.", indent=2, hang=3)
    voice.para("3. Bodhi asks what you want to change or make, then helps with one small first "
               "thing you can judge for yourself.", indent=2, hang=3)
    voice.para("4. After that first real exchange, your agent saves your exact words and "
               "retires START_HERE.md. Its text stays in the folder's Git history.",
               indent=2, hang=3)
    for line in later_steps(answers):
        voice.para(line, indent=2, hang=3)
    voice.line()
    voice.para("Nothing is recording. No account was connected. Nothing left this computer. "
               "To check the folder at any time, run this inside it:")
    voice.verbatim("python3 bin/bodhi.py check .")
    voice.line()
    voice.line("Receipt, for scripts and agents:")


def later_steps(answers):
    """One line each for the optional answers that change what comes next."""
    lines = []
    chat = answers.get("chat_app", "")
    if chat in HERMES_GATEWAY_APPS:
        app = CHAT_LABELS[chat]
        if answers["primary_harness"] == "hermes":
            lines.append("Later, to reach Bodhi in " + app + ": once Hermes works in the terminal, "
                         "run hermes gateway setup. Hermes asks for the app's token itself; Bodhi "
                         "never sees it.")
        else:
            lines.append("Later, to reach Bodhi in " + app + ": Hermes Agent's gateway can do "
                         "that (hermes gateway setup). The seed's install guide explains how.")
    notes = answers.get("notes_today", "")
    if notes and notes not in ("nowhere_yet", "paper"):
        lines.append("Your notes can stay where they are. Before suggesting a new notes app or a "
                     "memory graph, Bodhi asks what you are losing today.")
    if answers.get("findings_delivery") in ("push", "both"):
        lines.append("You asked for findings to reach you. Until a channel is set up, Bodhi "
                     "leaves them in the folder's session log and says so.")
    return lines


def load_raw_answers(argument):
    if argument.startswith("@"):
        raw_text = Path(argument[1:]).expanduser().read_text(encoding="utf-8")
    elif argument.lstrip().startswith("{"):
        raw_text = argument
    else:
        raw_text = Path(argument).expanduser().read_text(encoding="utf-8")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise BodhiError("invalid answers JSON: " + str(exc))
    normalize_answers(raw)  # validate before anyone relies on it
    return raw


def read_answers(argument):
    return normalize_answers(load_raw_answers(argument))


# ---------------------------------------------------------------------------
# Setup without a vault, and the doctor.
#
# `setup` asks the same questions as `init` but only saves the answers, so the
# installer can learn which harnesses to serve before anyone decides on a
# vault. `doctor` reads the state of this computer and says what to fix.
# ---------------------------------------------------------------------------

SKILL_NAME = "bodhi-seed"
GREETING = "Bodhi online. Just a seed, for now."


def bodhi_home(env=None):
    env = os.environ if env is None else env
    return Path(env.get("BODHI_HOME") or Path(env.get("HOME") or str(Path.home())) / ".bodhi")


def default_answers(found):
    """Safe defaults for an unattended setup: what was detected, nothing invented."""
    return {"os": detected_os(), "model_access": "local" if found["ollama"] else "undecided",
            "harness": found["harnesses"][0] if found["harnesses"] else "undecided",
            "detected": found}


def save_raw_answers(raw, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def setup_command(args):
    save = Path(args.save).expanduser().absolute() if args.save else bodhi_home() / "answers.json"
    found = detect_tools()
    voice = None
    if args.answers is not None:
        raw = load_raw_answers(args.answers)
    elif args.yes:
        raw = default_answers(found)
    else:
        voice = Voice(plain=args.plain)
        try:
            raw = ask_raw_answers(voice, ("Your answers are saved in one file, and nothing else "
                                          "is written:", save), found)
        except KeyboardInterrupt:
            voice.line()
            raise BodhiError("setup stopped; nothing was saved")
    answers = normalize_answers(raw)
    save_raw_answers(raw, save)
    if voice is not None:
        setup_summary(voice, answers)
        voice.line()
        voice.line("Receipt, for scripts and agents:")
    emit({"status": "saved", "answers": str(save), "primary_harness": answers["primary_harness"],
          "model_access": answers["model_access"], "chat_app": answers["chat_app"],
          "detected": found})


def tree_hash(folder):
    """One digest for a skill folder's files and their paths; hidden files are ignored."""
    digest = hashlib.sha256()
    folder = Path(folder)
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_file():
            digest.update(relative.as_posix().encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def skill_version(folder):
    try:
        text = (Path(folder) / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    found = re.search(r'^\s+version:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    return found.group(1) if found else ""


def skill_targets(env=None):
    """Where each harness reads a personal copy of the skill (checked against their docs)."""
    env = os.environ if env is None else env
    home = Path(env.get("HOME") or str(Path.home()))
    claude = Path(env.get("CLAUDE_CONFIG_DIR") or home / ".claude")
    hermes = Path(env.get("HERMES_HOME") or home / ".hermes")
    return (
        {"key": "claude-code", "label": "Claude Code", "commands": ("claude",),
         "dest": claude / "skills" / SKILL_NAME, "first": "/bodhi-seed Hello, Bodhi."},
        {"key": "agents", "label": "Codex and OpenClaw", "commands": ("codex", "openclaw"),
         "dest": home / ".agents" / "skills" / SKILL_NAME, "first": "$bodhi-seed Hello, Bodhi."},
        {"key": "hermes", "label": "Hermes", "commands": ("hermes",),
         "dest": hermes / "skills" / SKILL_NAME, "search": hermes / "skills",
         "first": "/bodhi-seed Hello, Bodhi."},
    )


def _find_skill_copy(target, name=SKILL_NAME):
    dest = target["dest"].parent / name
    if (dest / "SKILL.md").is_file():
        return dest
    root = target.get("search")
    if root and root.is_dir():  # `hermes skills install` may file it under a category
        for candidate in sorted(root.glob("**/" + name)):
            if (candidate / "SKILL.md").is_file() and len(candidate.relative_to(root).parts) <= 4:
                return candidate
    return None


def optional_skill_names(seed_dir):
    """The optional Bodhi skills a seed carries: every skills/bodhi-* folder but the seed."""
    folder = Path(seed_dir) / "skills"
    if not folder.is_dir():
        return []
    return sorted(path.name for path in folder.iterdir()
                  if path.name.startswith("bodhi-") and path.name != SKILL_NAME
                  and (path / "SKILL.md").is_file())


def load_check(code, version):
    """The round trip that proves a session read the skill: a message and its one right reply.

    The rule for the reply lives only in SKILL.md (its Load check), so a model that has not
    read the skill cannot produce it, and a fresh code means the reply is not a stale copy.
    """
    return "bodhi check " + code, "Bodhi seed %s loaded. Check %s." % (version, code[::-1])


def new_check_code():
    while True:
        code = secrets.token_hex(2)
        if code != code[::-1]:
            return code


def find_seed(explicit=None, env=None):
    env = os.environ if env is None else env
    choices = [explicit, env.get("BODHI_SEED_DIR")]
    try:
        manifest = json.loads((bodhi_home(env) / "install-manifest.json").read_text(encoding="utf-8"))
        choices.append(manifest.get("seed_dir"))
    except (OSError, ValueError, AttributeError):
        pass
    choices.append(str(SKILL_SOURCE.parent.parent))
    for option in choices:
        if option and (Path(option).expanduser() / "skills" / SKILL_NAME / "SKILL.md").is_file():
            return Path(option).expanduser().absolute()
    return None


class Doctor:
    def __init__(self):
        self.checks = []

    def add(self, status, what, fix=""):
        self.checks.append({"status": status, "what": what, "fix": fix})

    @property
    def problems(self):
        return sum(1 for check in self.checks if check["status"] == "fail")

    @property
    def warnings(self):
        return sum(1 for check in self.checks if check["status"] == "warn")


def doctor(vault=None, seed=None, env=None):
    """Read this computer's Bodhi state. Returns (Doctor, first messages)."""
    env = os.environ if env is None else env
    report = Doctor()
    version = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info >= (3, 9):
        report.add("ok", "Python " + version)
    else:
        report.add("fail", "Python " + version + " is older than 3.9",
                   "install Python 3.9 or newer from python.org or your package manager")
    if shutil.which("git", path=env.get("PATH", os.defpath)):
        report.add("ok", "Git is installed")
    else:
        report.add("fail", "Git is not installed; the vault keeps its history with it",
                   "install git with your package manager (brew install git, apt install git)")
    seed_dir = find_seed(seed, env)
    seed_skill = seed_dir / "skills" / SKILL_NAME if seed_dir else None
    seed_hash = tree_hash(seed_skill) if seed_skill else ""
    if seed_dir:
        report.add("ok", "Seed at %s (skill version %s)" % (shown_path(seed_dir),
                                                             skill_version(seed_skill) or "?"))
    else:
        report.add("warn", "The seed repository was not found, so skill copies cannot be compared",
                   "pass --seed PATH, or set BODHI_SEED_DIR to your clone of bodhi-distro")
    firsts = []
    search = env.get("PATH", os.defpath)
    for target in skill_targets(env):
        copy = _find_skill_copy(target)
        has_harness = [c for c in target["commands"] if shutil.which(c, path=search)]
        source = shown_path(seed_skill) if seed_skill else "skills/bodhi-seed"
        folder = shown_path(target["dest"].parent)
        install_line = "./install.sh (it asks first), or copy %s into %s" % (source, folder)
        update_line = "./install.sh --update, or copy %s into %s again" % (source, folder)
        if copy is None:
            if has_harness:
                report.add("note", "%s is installed but has no Bodhi skill yet" % target["label"],
                           install_line)
            continue
        if seed_hash and tree_hash(copy) == seed_hash:
            report.add("ok", "%s: skill at %s matches the seed" % (target["label"], shown_path(copy)))
        elif seed_hash:
            report.add("warn", "%s: skill at %s differs from the seed (older or edited)"
                       % (target["label"], shown_path(copy)), update_line)
        else:
            report.add("note", "%s: skill at %s (not compared)" % (target["label"], shown_path(copy)))
        firsts.append((target["label"], target["first"]))
        for name in optional_skill_names(seed_dir) if seed_dir else []:
            extra = _find_skill_copy(target, name)
            if extra is None:
                continue
            if tree_hash(extra) == tree_hash(seed_dir / "skills" / name):
                report.add("ok", "%s: optional skill %s matches the seed" % (target["label"], name))
            else:
                report.add("warn", "%s: optional skill %s differs from the seed (older or edited)"
                           % (target["label"], name), "./install.sh --update")
    if not firsts:
        report.add("note", "No harness on this computer has the Bodhi skill yet",
                   "run ./install.sh from the seed, or see docs/INSTALL.md")
    manifest_path = bodhi_home(env) / "install-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            missing = [entry["path"] for entry in manifest.get("entries", [])
                       if entry.get("path") and not Path(entry["path"]).exists()]
        except (ValueError, KeyError, TypeError, AttributeError):
            report.add("fail", "The install record %s cannot be read" % shown_path(manifest_path),
                       "move it aside and run ./install.sh again")
        else:
            if missing:
                report.add("warn", "The install record lists paths that are gone: " +
                           ", ".join(shown_path(Path(item)) for item in missing),
                           "./install.sh --update puts them back; ./install.sh --uninstall forgets them")
            else:
                report.add("ok", "Install record %s matches this computer" % shown_path(manifest_path))
    if vault is not None:
        _doctor_vault(report, vault)
    return report, firsts


def _doctor_vault(report, vault):
    name = shown_path(vault)
    errors = verify_vault(vault)
    if errors:
        for error in errors:
            report.add("fail", "Vault %s: %s" % (name, error),
                       "compare with python3 bin/bodhi.py check %s and the vault's Git history" % name)
        return
    state = "Hello World done" if onboarding_state(vault) == "complete" else "Hello World pending"
    report.add("ok", "Vault %s passes its checks (%s)" % (name, state))
    try:
        changed = [line for line in git(vault, "status", "--porcelain").splitlines() if line.strip()]
    except BodhiError as exc:
        report.add("warn", "Vault %s: git status failed: %s" % (name, exc), "run git status inside it")
    else:
        if changed:
            report.add("warn", "Vault %s has %d uncommitted change(s)" % (name, len(changed)),
                       "cd %s && git status, then commit what should be kept" % name)
        else:
            report.add("ok", "Vault %s: everything is committed" % name)
    if (vault / RELAY_LEDGER).is_file():
        _, unreadable = relay_events(vault)
        if unreadable:
            report.add("warn", "Relay ledger has %d unreadable line(s)" % unreadable,
                       "open relay/ledger.jsonl and compare with git log -p relay/ledger.jsonl")
        else:
            report.add("ok", "Relay ledger is present and readable")
    else:
        report.add("note", "No relay ledger yet (optional; the first relay note creates it)")


def recommend(vault=None, env=None):
    """Answers x scan: reason from Player One's recorded answers and this
    computer's real state to the tools worth offering. Pure reads; nothing is
    installed, connected, or sent."""
    env = os.environ if env is None else env
    rows = []
    interests = []
    priority = ""
    if vault is not None:
        try:
            player = json.loads((vault / "context/player_one.json").read_text(encoding="utf-8"))
            interests = list(player.get("capture_interests", []))
            priority = ((player.get("priority_verbatim") or "")).strip()
        except (OSError, ValueError, AttributeError):
            interests, priority = [], ""
    search = env.get("PATH", os.defpath)
    for key, tool in TOOL_CATALOG.items():
        serves = set(tool.get("serves", ()))
        matches = [s for s in interests if s in serves]
        present = any(shutil.which(c, path=search) for c in tool.get("commands", ()))
        if not matches and not present:
            continue
        rows.append({
            "tool": key,
            "label": tool["label"],
            "matches": matches,
            "installed": present,
            "kind": tool["kind"],
            "what": tool["what"],
            "why": tool["why"],
            "get": tool["get"],
        })
    # Sort: installed first (a live surface is worth more than a promised one),
    # then breadth of match, then alphabetical.
    rows.sort(key=lambda r: (not r["installed"], -len(r["matches"]), r["tool"]))
    return rows, priority


def recommend_command(args):
    vault = Path(args.vault).expanduser().absolute() if args.vault else None
    if vault is not None and not (vault / "context/player_one.json").is_file():
        raise BodhiError("no Bodhi vault at %s (context/player_one.json is missing); "
                         "create one with: bodhi init %s" % (shown_path(vault), shown_path(vault)))
    rows, priority = recommend(vault)
    if args.json:
        emit({"recommendations": rows, "priority_verbatim": priority})
        return 0
    voice = Voice(plain=args.plain)
    voice.para("Bodhi recommend", style=("bold",))
    if priority:
        voice.para("Reasoning from your own words: \"" + priority + "\"")
        voice.line()
    if not rows:
        voice.para("Nothing to offer yet. Answer the capture-interest question (bodhi init"
                   " --answers, or in a session) and run this again.")
        return 0
    for row in rows:
        status = "ready " if row["installed"] else "offer "
        voice.para("%s%s  (%s)" % (status, row["label"], row["kind"]), hang=7)
        voice.para(row["what"], indent=7, hang=6)
        voice.para("why: " + row["why"], indent=7, hang=6)
        voice.para("get: " + row["get"], indent=7, hang=6)
    voice.line()
    voice.para("Offers, not installations. Nothing is set up without your say-so in a session.")
    return 0


def doctor_command(args):
    vault = None
    if args.vault:
        vault = Path(args.vault).expanduser().absolute()
    else:
        try:
            vault = relay_vault()
        except BodhiError:
            vault = None
    report, firsts = doctor(vault, args.seed)
    seed_dir = find_seed(args.seed)
    version = skill_version(seed_dir / "skills" / SKILL_NAME) if seed_dir else ""
    check, reply = load_check(args.code or new_check_code(), version or VERSION)
    checks = [(label, message.split()[0] + " " + check) for label, message in firsts]
    if args.json:
        emit({"checks": report.checks, "problems": report.problems, "warnings": report.warnings,
              "first_messages": [{"harness": label, "message": message} for label, message in firsts],
              "greeting": GREETING,
              "load_check": {"messages": [{"harness": label, "message": message}
                                          for label, message in checks],
                             "reply": reply}})
        return 1 if report.problems else 0
    voice = Voice(plain=args.plain)
    voice.para("Bodhi doctor", style=("bold",))
    for check in report.checks:
        voice.para("%-5s %s" % (check["status"], check["what"]), hang=6)
        if check["fix"]:
            voice.para("fix: " + check["fix"], indent=6, hang=5)
    if vault is None:
        voice.para("note  No vault was checked; pass its folder to check one.", hang=6)
    if firsts:
        voice.line()
        voice.para("To see the skill load, paste this as your first message:", style=("bold",))
        for label, message in firsts:
            voice.para(label + ":", indent=2)
            voice.verbatim(message, indent=4)
        voice.para("A loaded seed answers: " + GREETING, indent=2)
        voice.line()
        voice.para("Round trip: to check at any time that a session can see the skill, paste "
                   "this into a new session:", style=("bold",))
        for label, message in checks:
            voice.para(label + ":", indent=2)
            voice.verbatim(message, indent=4)
        voice.para("The only right reply, word for word:", indent=2)
        voice.verbatim(reply, indent=4)
        voice.para("Any other reply means the skill was not read in that session. The code is "
                   "new each run, so an old answer cannot pass.", indent=2)
    voice.line()
    voice.para("Result: %d problem(s), %d warning(s)." % (report.problems, report.warnings))
    return 1 if report.problems else 0


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
# Ported from the continuity ledger running on the first fleet's home server,
# its bodhinas (the bodhinas monitor and the bodhi-continuity command, September
# 2026), with the same event shape, so a ledger can move between them. There, one server
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
    setup_parser = sub.add_parser(
        "setup", help="ask the setup questions and save the answers, without making a vault",
        description="The same questions as init, saved for later use with init --answers or "
                    "the installer. Nothing else is written.")
    setup_parser.add_argument("--save", metavar="PATH", help="where to save the answers "
                              "(default ~/.bodhi/answers.json)")
    setup_parser.add_argument("--answers", metavar="JSON_OR_PATH", help="use these answers instead of asking")
    setup_parser.add_argument("--yes", action="store_true", help="no questions: save detected defaults")
    setup_parser.add_argument("--plain", action="store_true", help="no art and no color")
    doctor_parser = sub.add_parser(
        "doctor", help="check Python, Git, the seed, each harness's skill copy, and a vault",
        description="Reads this computer's Bodhi state and gives each finding a one-line fix. "
                    "Exits 1 when something is actually broken.")
    doctor_parser.add_argument("vault", nargs="?", help="a vault to check (default: the vault "
                               "this command runs in, if any)")
    doctor_parser.add_argument("--seed", help="the seed repository to compare skill copies with")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.add_argument("--plain", action="store_true", help="no color")
    recommend_parser = sub.add_parser(
        "recommend", help="match Player One's answers and this computer to tools worth offering",
        description="Answers x scan: reads Player One's setup answers and the real state of this "
                    "computer, then names the tools worth offering — installed ones first. "
                    "Offers, never installations.")
    recommend_parser.add_argument("vault", nargs="?", help="a vault to read Player One's answers "
                                  "from (default: the vault this command runs in, if any)")
    recommend_parser.add_argument("--json", action="store_true")
    recommend_parser.add_argument("--plain", action="store_true", help="no color")
    doctor_parser.add_argument("--code", help=argparse.SUPPRESS)  # fixed round-trip code, for tests
    mark_parser = sub.add_parser(
        "mark", help="plant the seed: draw the Bodhi mark, with a short sprout on a terminal",
        description="About 1.5 seconds of motion on an interactive terminal with color, ending "
                    "on the static mark; any key skips it. No motion under --plain, NO_COLOR, "
                    "TERM=dumb, CI or BODHI_NO_MOTION, or when output is not a terminal.")
    mark_parser.add_argument("--plain", action="store_true", help="draw nothing")
    add_relay_parser(sub)
    args = parser.parse_args(argv)
    dest = args.dest.expanduser().absolute() if getattr(args, "dest", None) is not None else None
    try:
        if args.command == "relay":
            return relay_command(args)
        if args.command == "setup":
            setup_command(args)
            return 0
        if args.command == "doctor":
            return doctor_command(args)
        if args.command == "recommend":
            return recommend_command(args)
        if args.command == "mark":
            play_sprout(Voice(plain=args.plain))
            return 0
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
