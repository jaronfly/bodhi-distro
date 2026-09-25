import json
import tempfile
import unittest
from pathlib import Path

from test_bodhi import CLI, run_cli

REPLAY = Path(__file__).resolve().parents[1] / "bin/replay.py"


class ReplayLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-replay-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"

    def _init_vault(self):
        result = run_cli(CLI, "init", self.vault,
                         "--answers", json.dumps({"os": "macos", "harness": "undecided", "model_access": "none"}))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_init_ships_empty_ledger(self):
        self._init_vault()
        ledger = self.vault / "memory/attempts.jsonl"
        self.assertTrue(ledger.is_file(), "init must stage the empty ledger")
        self.assertEqual(ledger.read_text(encoding="utf-8").strip(), "")
        self.assertTrue((self.vault / "memory/README.md").is_file())

    def test_check_flags_missing_ledger(self):
        self._init_vault()
        (self.vault / "memory/attempts.jsonl").unlink()
        result = run_cli(self.vault / "bin/bodhi.py", "check", self.vault)
        self.assertNotEqual(result.returncode, 0, "missing ledger must fail check")
        self.assertIn("replay would exit 3", result.stdout + result.stderr)

    def test_missing_ledger_exits_3_and_never_says_no_prior_attempts(self):
        self._init_vault()
        (self.vault / "memory/attempts.jsonl").unlink()
        result = run_cli(REPLAY, "query", self.vault, "publish listing")
        self.assertEqual(result.returncode, 3)
        self.assertNotIn("no prior attempts", result.stderr)
        self.assertIn("not set up", result.stderr)

    def test_append_then_query_in_vault_cli(self):
        self._init_vault()
        result = run_cli(self.vault / "bin/replay.py", "append", self.vault,
                         "--situation", "publish listing to shop",
                         "--action", "ran uploader",
                         "--outcome", "failed",
                         "--note", "shop token was for the wrong store")
        self.assertEqual(result.returncode, 0, result.stderr)
        again = run_cli(self.vault / "bin/replay.py", "query", self.vault, "publish listing")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("wrong store", again.stdout)

    def test_shapes_lists_six(self):
        result = run_cli(REPLAY, "shapes")
        self.assertEqual(result.returncode, 0, result.stderr)
        for shape in ("wrong-surface", "empty-is-not-zero", "silent-no-op",
                      "premature-closure", "inherited-unverified", "guard-too-loose"):
            self.assertIn(shape, result.stdout)


if __name__ == "__main__":
    unittest.main()
