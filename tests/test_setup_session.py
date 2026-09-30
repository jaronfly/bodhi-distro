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
BLOCK = "█"
FULL_ANSWERS = "\nmacos\nhermes\ncloud\n\n\n"


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


@unittest.skipUnless(os.name == "posix", "needs a POSIX pseudo-terminal")
class TerminalTests(unittest.TestCase):
    """Run init on a real pseudo-terminal, where color and the mark are allowed."""

    def run_on_tty(self, vault, *extra, env_update=None):
        import pty
        env = {key: value for key, value in os.environ.items()
               if key not in ("NO_COLOR", "BODHI_PLAIN", "COLUMNS")}
        env.update({"TERM": "xterm-256color", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"})
        env.update(env_update or {})
        pid, fd = pty.fork()
        if pid == 0:  # child
            try:
                os.execve(str(PYTHON), [str(PYTHON), str(CLI), "init", str(vault)] + list(extra), env)
            finally:
                os._exit(127)
        os.write(fd, FULL_ANSWERS.encode())
        output = b""
        while True:
            ready, _, _ = select.select([fd], [], [], 20)
            if not ready:
                break
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
        output = self.run_on_tty(self.root / "vault")
        self.assertIsNotNone(SGR.search(output))
        plain_output = SGR.sub("", output)
        expected = [line for line in load_bodhi().render_mark(BLOCK)]
        drawn = [line[2:] for line in plain_output.splitlines() if BLOCK in line]
        self.assertEqual(drawn, expected)
        self.assertIn("Your seed is planted", plain_output)

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
