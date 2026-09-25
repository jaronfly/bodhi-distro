import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin/bodhi.py"
PYTHON = Path("/usr/bin/python3") if Path("/usr/bin/python3").exists() else Path(sys.executable)


def run_cli(cli, *args, input_text=None):
    return subprocess.run([str(PYTHON), str(cli)] + [str(arg) for arg in args],
                          input=input_text, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def run_git(vault, *args):
    return subprocess.run(["git", "-C", str(vault)] + list(args), text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.strip()


class BodhiCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"

    def init(self, answers=None):
        if answers is None:
            answers = {"os": "macos", "harness": "undecided", "model_access": "none"}
        result = run_cli(CLI, "init", self.vault, "--answers", json.dumps(answers))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def complete(self, priority="Work on writing\nwith less drift", capability="Review one source"):
        priority_file = self.root / "priority.txt"
        capability_file = self.root / "capability.txt"
        receipt_file = self.root / "receipt.txt"
        priority_file.write_text(priority, encoding="utf-8")
        capability_file.write_text(capability, encoding="utf-8")
        receipt_file.write_text("Player One confirmed the priority and chose one local review.",
                                encoding="utf-8")
        result = run_cli(self.vault / "bin/bodhi.py", "onboard-complete", self.vault,
                         "--priority-file", priority_file, "--capability-file", capability_file,
                         "--receipt-file", receipt_file, "--source-ref", "test:first-session")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_init_hello_world_completion_and_history(self):
        result = self.init()
        self.assertEqual(result["status"], "pending_hello_world")
        self.assertTrue((self.vault / "START_HERE.md").is_file())
        self.assertTrue((self.vault / "bin/bodhi.py").is_file())
        self.assertEqual(run_git(self.vault, "remote"), "")
        pending = run_cli(self.vault / "bin/bodhi.py", "check", self.vault)
        self.assertEqual(pending.returncode, 0, pending.stderr)
        self.assertEqual(json.loads(pending.stdout)["status"], "pending_hello_world")
        blocked = run_cli(self.vault / "bin/bodhi.py", "capture", self.vault,
                          "--text", "too early", "--source", "test")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("Hello World is pending", blocked.stderr)

        original_start = (self.vault / "START_HERE.md").read_bytes()
        self.complete()
        self.assertFalse((self.vault / "START_HERE.md").exists())
        self.assertEqual((self.vault / "history/START_HERE.md").read_bytes(), original_start)
        answer = json.loads((self.vault / "sources/hello_world_answer.json").read_text())
        self.assertEqual(answer["priority_verbatim"], "Work on writing\nwith less drift")
        self.assertEqual(answer["source_ref"], "test:first-session")
        player = json.loads((self.vault / "context/player_one.json").read_text())
        self.assertTrue(player["priority_confirmed"])
        self.assertEqual(player["priority_verbatim"], answer["priority_verbatim"])
        complete = run_cli(self.vault / "bin/bodhi.py", "check", self.vault)
        self.assertEqual(complete.returncode, 0, complete.stderr)
        self.assertEqual(json.loads(complete.stdout)["status"], "complete")
        self.assertEqual(run_git(self.vault, "remote"), "")
        first = run_git(self.vault, "rev-list", "--max-parents=0", "HEAD")
        self.assertEqual(run_git(self.vault, "show", first + ":START_HERE.md").encode(),
                         original_start.rstrip(b"\n"))
        player["priority_verbatim"] = "A later correction to Player One's priority"
        player["capture_enabled"] = True
        (self.vault / "context/player_one.json").write_text(json.dumps(player) + "\n", encoding="utf-8")
        after_correction = run_cli(self.vault / "bin/bodhi.py", "check", self.vault)
        self.assertEqual(after_correction.returncode, 0, after_correction.stderr)
        self.assertEqual(json.loads(after_correction.stdout)["status"], "complete")

    def test_capture_gaps_review_gaps_preserves_exact_file_bytes(self):
        self.init()
        self.complete(priority="Make useful notes", capability="Capture a source")
        source_file = self.root / "original.txt"
        raw = "First line\r\nπ and a trailing space \n".encode("utf-8")
        source_file.write_bytes(raw)
        captured = run_cli(self.vault / "bin/bodhi.py", "capture", self.vault,
                           "--file", source_file, "--source", "Player One note")
        self.assertEqual(captured.returncode, 0, captured.stderr)
        receipt = json.loads(captured.stdout)
        self.assertEqual(receipt["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual((self.vault / receipt["object"]).read_bytes(), raw)
        gaps = run_cli(self.vault / "bin/bodhi.py", "gaps", self.vault)
        self.assertEqual([item["id"] for item in json.loads(gaps.stdout)], [receipt["id"]])
        reviewed = run_cli(self.vault / "bin/bodhi.py", "review", self.vault, receipt["id"],
                           "--disposition", "project", "--note", "Use as a writing seed")
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        review_receipt = json.loads(reviewed.stdout)
        self.assertEqual(review_receipt["capture_sha256"], receipt["sha256"])
        gaps_after = run_cli(self.vault / "bin/bodhi.py", "gaps", self.vault)
        self.assertEqual(json.loads(gaps_after.stdout), [])
        checked = run_cli(self.vault / "bin/bodhi.py", "check", self.vault)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual((self.vault / receipt["object"]).read_bytes(), raw)

    def test_stdin_and_invalid_utf8(self):
        self.init()
        self.complete()
        raw = "Exact stdin\n".encode("utf-8")
        good = subprocess.run([str(PYTHON), str(self.vault / "bin/bodhi.py"), "capture",
                               str(self.vault), "--stdin", "--source", "stdin test"],
                              input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False)
        self.assertEqual(good.returncode, 0, good.stderr.decode())
        receipt = json.loads(good.stdout.decode())
        self.assertEqual((self.vault / receipt["object"]).read_bytes(), raw)
        bad_file = self.root / "binary.dat"
        bad_file.write_bytes(b"\xff\xfe")
        bad = run_cli(self.vault / "bin/bodhi.py", "capture", self.vault,
                      "--file", bad_file, "--source", "bad file")
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("UTF-8 text only", bad.stderr)
        self.assertEqual(len((self.vault / "evidence/captures.jsonl").read_text().splitlines()), 1)

    def test_interactive_init_and_answers_file(self):
        interactive = run_cli(CLI, "init", self.vault,
                              input_text="\nmacos\nhermes\ncloud\n\n\n")
        self.assertEqual(interactive.returncode, 0, interactive.stderr)
        self.assertEqual(json.loads((self.vault / "context/player_one.json").read_text())
                         ["priority_verbatim"], "")
        other_vault = self.root / "from-file"
        answers_file = self.root / "answers.json"
        answers_file.write_text(json.dumps({"priority": "A draft to confirm", "os": "mac",
                                            "harness": "openclaw", "model_access": "local",
                                            "capture_surfaces": ["web_history"]}), encoding="utf-8")
        loaded = run_cli(CLI, "init", other_vault, "--answers", answers_file)
        self.assertEqual(loaded.returncode, 0, loaded.stderr)
        preferences = json.loads((other_vault / "context/player_one.json").read_text())
        self.assertEqual(preferences["capture_interests"], ["web_history"])
        self.assertFalse(preferences["capture_enabled"])
        self.assertFalse(preferences["priority_confirmed"])

    def test_nonempty_target_and_local_git_allowlist(self):
        self.vault.mkdir()
        marker = self.vault / "keep.txt"
        marker.write_text("untouched", encoding="utf-8")
        refused = run_cli(CLI, "init", self.vault, "--answers", "{}")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(marker.read_text(), "untouched")
        self.assertFalse((self.vault / ".git").exists())
        spec = importlib.util.spec_from_file_location("bodhi", str(CLI))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(module.BodhiError):
            module.git(self.vault, "push", "origin", "main")


if __name__ == "__main__":
    unittest.main()
