"""The Ready Player One setup session: words carry meaning; color and art only decorate."""

import importlib.util
import io
import json
import os
import re
import select
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_bodhi import CLI, PYTHON, run_cli

ROOT = Path(__file__).resolve().parents[1]
SGR = re.compile(r"\x1b\[[0-9;]*m")  # color and bold escapes
CSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")  # every control sequence, cursor moves included
BLOCK = "█"
# Six core answers, then "n" at the optional-questions prompt. (A pipe that ends after
# six answers also skips them; a terminal waits, so the pty tests need the "n".)
FULL_ANSWERS = "\nmacos\nhermes\ncloud\n\n\nn\n"


def load_bodhi():
    spec = importlib.util.spec_from_file_location("bodhi_setup", str(CLI))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTerminal(io.StringIO):
    encoding = "utf-8"

    def isatty(self):
        return True


def run_init(vault, input_text, *extra, env_update=None, drop=()):
    env = dict(os.environ)
    for name in drop:
        env.pop(name, None)
    env.update(env_update or {})
    return subprocess.run([str(PYTHON), str(CLI), "init", str(vault)] + list(extra),
                          input=input_text, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, check=False)


def human_lines(stdout):
    """Every line a person reads, minus the final JSON receipt and verbatim paths/commands."""
    lines = stdout.splitlines()
    json.loads(lines[-1])  # the receipt stays machine-readable
    keep = []
    for line in lines[:-1]:
        text = line.strip()
        if text.startswith(("/", "~", '"', "cd ", "python3 ")) or re.match(r"^[A-Za-z]:\\", text):
            continue
        keep.append(line)
    return keep


class SetupOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-setup-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_plain_mode_is_words_only_and_fits_80_columns(self):
        vault = self.root / "vault"
        result = run_init(vault, FULL_ANSWERS, "--plain", env_update={"TERM": "xterm-256color"},
                          drop=("NO_COLOR",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(SGR.search(result.stdout), "plain mode must not emit color")
        self.assertNotIn(BLOCK, result.stdout, "plain mode must not draw the mark")
        for number in range(1, 7):
            self.assertIn("Question %d of 6." % number, result.stdout)
        for words in ("Hello, Player One.", "Press Enter", "What happens next",
                      "Your seed is planted", "Nothing is recording", "Hello, Bodhi."):
            self.assertIn(words, result.stdout)
        for line in human_lines(result.stdout):
            self.assertLessEqual(len(line), 80, line)
        receipt = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(receipt["status"], "pending_hello_world")
        self.assertFalse(receipt["capture_enabled"])

    def test_piped_output_has_no_color_or_art_even_without_plain(self):
        result = run_init(self.root / "vault", FULL_ANSWERS,
                          env_update={"TERM": "xterm-256color"}, drop=("NO_COLOR", "BODHI_PLAIN"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(SGR.search(result.stdout))
        self.assertNotIn(BLOCK, result.stdout)
        self.assertIn("Question 6 of 6.", result.stdout)

    def test_numbers_retries_and_exact_words(self):
        vault = self.root / "vault"
        answers = "My words stay exactly  \n9\n2\n5\nZed agent\n1\n1, 1\n1,4\n\n"
        result = run_init(vault, answers, "--plain")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("Not recognized"), 2, result.stderr)
        player = json.loads((vault / "context/player_one.json").read_text(encoding="utf-8"))
        self.assertEqual(player["priority_verbatim"], "My words stay exactly  ")
        self.assertEqual(player["os"], "windows")
        self.assertEqual(player["primary_harness"], "other")
        self.assertEqual(player["other_harness_name"], "Zed agent")
        self.assertEqual(player["model_access"], "local")
        self.assertEqual(player["capture_interests"], ["web_history", "screen"])
        self.assertFalse(player["capture_enabled"])
        self.assertIn("in Zed agent", result.stdout)

    def test_named_harness_gets_a_documented_start_command(self):
        vault = self.root / "vault"
        result = run_init(vault, "\nlinux\nclaude code\n\n\n\n", "--plain")
        self.assertEqual(result.returncode, 0, result.stderr)
        player = json.loads((vault / "context/player_one.json").read_text(encoding="utf-8"))
        self.assertEqual(player["primary_harness"], "claude-code")
        self.assertIn("in Claude Code", result.stdout)
        self.assertRegex(result.stdout, r"(?m)^ +claude$")

    def test_stopping_early_creates_nothing(self):
        vault = self.root / "vault"
        result = run_init(vault, "\nmacos\n", "--plain")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nothing was created", result.stderr)
        self.assertFalse(vault.exists())

    def test_answers_mode_still_prints_only_the_json_receipt(self):
        result = run_cli(CLI, "init", self.root / "vault", "--answers",
                         json.dumps({"os": "linux", "harness": "codex", "model_access": "none"}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pending_hello_world")


class VoiceTests(unittest.TestCase):
    def voice(self, env, plain=False, stream=None):
        return load_bodhi().Voice(stream or FakeTerminal(), plain=plain, env=env, width=80)

    def test_color_needs_a_terminal_and_no_no_color(self):
        voice = self.voice({"TERM": "xterm-256color"})
        self.assertTrue(voice.color)
        self.assertTrue(voice.art)

    def test_no_color_removes_color_but_keeps_words(self):
        voice = self.voice({"TERM": "xterm-256color", "NO_COLOR": "1"})
        self.assertFalse(voice.color)
        self.assertTrue(voice.art)
        self.assertEqual(voice.style("Hello", "bold"), "Hello")

    def test_empty_no_color_is_unset_per_the_convention(self):
        self.assertTrue(self.voice({"TERM": "xterm", "NO_COLOR": ""}).color)

    def test_plain_and_dumb_terminals_get_neither(self):
        for voice in (self.voice({"TERM": "xterm"}, plain=True),
                      self.voice({"TERM": "xterm", "BODHI_PLAIN": "1"}),
                      self.voice({"TERM": "dumb"})):
            self.assertFalse(voice.color)
            self.assertFalse(voice.art)

    def test_non_tty_gets_neither(self):
        voice = self.voice({"TERM": "xterm-256color"}, stream=io.StringIO())
        self.assertFalse(voice.color)
        self.assertFalse(voice.art)

    def test_wrapping_never_exceeds_the_width(self):
        stream = FakeTerminal()
        voice = load_bodhi().Voice(stream, env={"TERM": "xterm"}, width=40)
        voice.para("word " * 40, indent=2, hang=3)
        for line in stream.getvalue().splitlines():
            self.assertLessEqual(len(SGR.sub("", line)), 40)


class MarkTests(unittest.TestCase):
    SPEC = ("...##.##...", ".....#.....", ".....#.....", "#####.#####", "#####..####",
            "####.##.###", "###.####.##", "###.#######", "##.########", "###########")

    def test_mark_is_the_brand_mark(self):
        self.assertEqual(load_bodhi().MARK, self.SPEC)

    def test_every_cell_is_whole_and_square(self):
        lines = load_bodhi().render_mark("#")
        self.assertEqual(len(lines), 10)
        for row, drawn in zip(self.SPEC, lines):
            self.assertEqual(len(drawn), 22)
            for index, cell in enumerate(row):
                self.assertEqual(drawn[2 * index:2 * index + 2], "##" if cell == "#" else "  ")


class MotionTests(unittest.TestCase):
    """The seed-sprout animation: when it plays, when it must not, and how it ends."""

    MOTION_ENV = {"TERM": "xterm-256color"}

    def voice(self, env=None, plain=False, stream=None):
        return load_bodhi().Voice(stream or FakeTerminal(), plain=plain,
                                  env=dict(self.MOTION_ENV, **(env or {})), width=80)

    def test_motion_needs_color_on_a_terminal_and_no_opt_out(self):
        self.assertTrue(self.voice().motion)
        cases = {"--plain": self.voice(plain=True), "NO_COLOR": self.voice({"NO_COLOR": "1"}),
                 "TERM=dumb": self.voice({"TERM": "dumb"}), "BODHI_PLAIN": self.voice({"BODHI_PLAIN": "1"}),
                 "not a TTY": self.voice(stream=io.StringIO()), "CI": self.voice({"CI": "true"}),
                 "BODHI_NO_MOTION": self.voice({"BODHI_NO_MOTION": "1"})}
        for why, voice in cases.items():
            self.assertFalse(voice.motion, why)

    def play(self, voice, pressed=lambda: False):
        sleeps = []
        played = load_bodhi().play_sprout(voice, pressed=pressed, sleep=sleeps.append)
        return played, sleeps, voice.stream.getvalue()

    def last_mark(self, output):
        lines = CSI.sub("", output).replace("\r", "").splitlines()
        return [line[2:] for line in lines if BLOCK in line][-10:]

    def test_animation_lasts_about_a_second_and_a_half_and_ends_on_the_static_mark(self):
        bodhi = load_bodhi()
        played, sleeps, output = self.play(self.voice())
        self.assertTrue(played)
        self.assertAlmostEqual(sum(sleeps), 1.5, delta=0.2)
        self.assertEqual(self.last_mark(output), bodhi.render_mark(BLOCK))
        self.assertIn("38;5;172", output, "the saffron seed appears")
        self.assertTrue(output.endswith("\x1b[?25h"), "the cursor comes back")

    def test_any_key_skips_to_the_end(self):
        presses = iter([False, False, True])
        played, sleeps, output = self.play(self.voice(), pressed=lambda: next(presses, True))
        self.assertTrue(played)
        self.assertEqual(len(sleeps), 2)
        self.assertEqual(self.last_mark(output), load_bodhi().render_mark(BLOCK))

    def test_without_motion_the_static_mark_is_drawn_once(self):
        played, sleeps, output = self.play(self.voice({"CI": "1"}))
        self.assertFalse(played)
        self.assertEqual(sleeps, [])
        self.assertNotIn("\x1b[10A", output)
        self.assertEqual(self.last_mark(output), load_bodhi().render_mark(BLOCK))
        played, _, output = self.play(self.voice(plain=True))
        self.assertEqual((played, output), (False, ""), "plain draws nothing")

    def test_frames_are_whole_cells_with_one_seed(self):
        bodhi = load_bodhi()
        frames = bodhi.sprout_frames()
        self.assertEqual(frames[-1], bodhi.MARK)
        for frame in frames:
            self.assertEqual([len(row) for row in frame], [11] * 10)
            self.assertTrue(set("".join(frame)) <= {"#", ".", "o"})
        for frame in frames[:-1]:
            self.assertEqual("".join(frame).count("o"), 1)
            row, column = bodhi.MARK_SEED
            self.assertEqual(frame[row][column], "o")

    def test_mark_is_the_svg_path_from_the_brand(self):
        bodhi = load_bodhi()
        self.assertEqual(bodhi.svg_cells(bodhi.MARK_SVG_PATH), bodhi.MARK)

    def test_mark_command_draws_nothing_into_a_pipe(self):
        result = run_cli(CLI, "mark")
        self.assertEqual((result.returncode, result.stdout), (0, ""))


@unittest.skipUnless(os.name == "posix", "needs a POSIX pseudo-terminal")
class TerminalTests(unittest.TestCase):
    """Run init on a real pseudo-terminal, where color and the mark are allowed."""

    def run_on_tty(self, vault, *extra, env_update=None):
        import pty
        env = {key: value for key, value in os.environ.items()
               if key not in ("NO_COLOR", "BODHI_PLAIN", "COLUMNS", "CI", "BODHI_NO_MOTION")}
        env.update({"TERM": "xterm-256color", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"})
        env.update(env_update or {})
        pid, fd = pty.fork()
        if pid == 0:  # child
            try:
                os.execve(str(PYTHON), [str(PYTHON), str(CLI), "init", str(vault)] + list(extra), env)
            finally:
                os._exit(127)
        # A real terminal has a size; a fresh pty is 0x0 until one is set, and
        # the CLI draws no art below MARK_MIN_WIDTH columns.
        import fcntl
        import struct
        import termios as termios_module
        fcntl.ioctl(fd, termios_module.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        os.write(fd, FULL_ANSWERS.encode())
        output = b""
        while True:
            ready, _, _ = select.select([fd], [], [], 20)
            if not ready:  # the child is waiting for input it will never get: fail, don't hang
                os.kill(pid, 9)
                os.waitpid(pid, 0)
                os.close(fd)
                self.fail("init waited for more input:\n" + output.decode("utf-8", "replace")[-800:])
            try:
                chunk = os.read(fd, 4096)
            except OSError:  # the child closed the terminal
                break
            if not chunk:
                break
            output += chunk
        _, status = os.waitpid(pid, 0)
        os.close(fd)
        self.assertEqual(os.WEXITSTATUS(status), 0, output.decode("utf-8", "replace"))
        return output.decode("utf-8", "replace").replace("\r\n", "\n")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-tty-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_terminal_gets_color_and_the_whole_mark(self):
        output = self.run_on_tty(self.root / "vault", env_update={"BODHI_NO_MOTION": "1"})
        self.assertIsNotNone(SGR.search(output))
        plain_output = SGR.sub("", output)
        expected = [line for line in load_bodhi().render_mark(BLOCK)]
        drawn = [line[2:] for line in plain_output.splitlines() if BLOCK in line]
        self.assertEqual(drawn, expected)
        self.assertIn("Your seed is planted", plain_output)

    def test_terminal_plays_the_sprout_and_ends_on_the_static_mark(self):
        output = self.run_on_tty(self.root / "vault")
        self.assertIn("\x1b[10A", output, "frames redraw in place")
        drawn = [line[2:] for line in CSI.sub("", output).replace("\r", "").splitlines()
                 if BLOCK in line]
        self.assertEqual(drawn[-10:], load_bodhi().render_mark(BLOCK))
        self.assertIn("Your seed is planted", output)

    def test_ci_on_a_terminal_draws_the_static_mark_without_motion(self):
        output = self.run_on_tty(self.root / "vault", env_update={"CI": "true"})
        self.assertNotIn("\x1b[10A", output)
        self.assertIn(BLOCK, output)

    def test_no_color_on_a_terminal_keeps_the_mark_without_color(self):
        output = self.run_on_tty(self.root / "vault", env_update={"NO_COLOR": "1"})
        self.assertIsNone(SGR.search(output))
        self.assertIn(BLOCK, output)

    def test_plain_on_a_terminal_has_neither(self):
        output = self.run_on_tty(self.root / "vault", "--plain")
        self.assertIsNone(SGR.search(output))
        self.assertNotIn(BLOCK, output)
        self.assertIn("Question 1 of 6.", output)


if __name__ == "__main__":
    unittest.main()


class AgnosticQuestionTests(unittest.TestCase):
    """The optional questions, detection, ? help, and setup without a vault."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-agnostic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def path_with(self, *names):
        for name in names:
            stub = self.bin / name
            stub.write_text("#!/bin/sh\n", encoding="utf-8")
            stub.chmod(0o755)
        return str(self.bin) + ":/usr/bin:/bin"

    def test_optional_questions_are_saved_and_help_explains_more(self):
        vault = self.root / "vault"
        lines = ["", "linux", "?", "hermes", "cloud", "", "",   # core six, with one ? for help
                 "",                                             # yes to the optional questions
                 "1", "?", "telegram", "1,phone,5", "notion", "push"]
        result = run_init(vault, "\n".join(lines) + "\n", "--plain",
                          env_update={"PATH": self.path_with()})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A harness is the app or command", result.stdout)
        self.assertIn("Telegram, Discord, Slack, WhatsApp, Signal", result.stdout)
        player = json.loads((vault / "context/player_one.json").read_text(encoding="utf-8"))
        self.assertEqual(player["terminal_comfort"], "new")
        self.assertEqual(player["chat_app"], "telegram")
        self.assertEqual(player["devices"], ["this_computer", "phone", "home_server"])
        self.assertEqual(player["notes_today"], "notion")
        self.assertEqual(player["findings_delivery"], "push")
        self.assertIn("hermes gateway setup", result.stdout)
        self.assertIn("Optional question 5 of 5.", result.stdout)

    def test_detected_tools_become_defaults_and_are_kept_apart(self):
        vault = self.root / "vault"
        result = run_init(vault, "\n\n\n\n\n\nn\n", "--plain",
                          env_update={"PATH": self.path_with("claude", "codex", "ollama")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Found on this computer: Claude Code, Codex.", result.stdout)
        player = json.loads((vault / "context/player_one.json").read_text(encoding="utf-8"))
        self.assertEqual(player["primary_harness"], "claude-code")
        self.assertEqual(player["model_access"], "local")
        self.assertEqual(player["detected_at_setup"]["harnesses"], ["claude-code", "codex"])
        self.assertTrue(player["detected_at_setup"]["ollama"])
        self.assertEqual(player["chat_app"], "", "skipped questions stay empty, not guessed")

    def test_setup_saves_answers_that_init_reuses(self):
        saved = self.root / "answers.json"
        result = subprocess.run([str(PYTHON), str(CLI), "setup", "--save", str(saved), "--plain"],
                                input="Write a short film  \nlinux\n2\n3\n\nshare drafts\nn\n",
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, PATH=self.path_with()), check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1])["status"], "saved")
        self.assertFalse((self.root / "vault").exists())
        raw = json.loads(saved.read_text(encoding="utf-8"))
        self.assertEqual(raw["priority"], "Write a short film  ")
        self.assertEqual(oct(saved.stat().st_mode & 0o777), "0o600")
        made = run_cli(CLI, "init", self.root / "vault", "--answers", saved)
        self.assertEqual(made.returncode, 0, made.stderr)
        player = json.loads((self.root / "vault/context/player_one.json").read_text(encoding="utf-8"))
        self.assertEqual(player["priority_verbatim"], "Write a short film  ")
        self.assertEqual(player["primary_harness"], "openclaw")

    def test_answers_json_new_fields_are_optional_and_validated(self):
        base = {"os": "linux", "harness": "undecided", "model_access": "none"}
        ok = dict(base, chat_app="other", chat_app_name="Matrix", devices=["phone"],
                  notes_today="paper", findings_delivery="both", terminal_comfort="some")
        self.assertEqual(run_cli(CLI, "init", self.root / "a", "--answers", json.dumps(ok)).returncode, 0)
        for bad in (dict(base, chat_app="carrier-pigeon"), dict(base, devices=["phone", "phone"]),
                    dict(base, chat_app="slack", chat_app_name="Slack"), dict(base, mood="happy"),
                    dict(base, detected={"harnesses": ["notepad"]})):
            refused = run_cli(CLI, "init", self.root / "b", "--answers", json.dumps(bad))
            self.assertNotEqual(refused.returncode, 0, bad)
            self.assertFalse((self.root / "b").exists())
