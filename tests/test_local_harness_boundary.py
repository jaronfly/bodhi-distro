import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from test_bodhi import CLI, run_cli


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("local_harness", ROOT / "evals/local/harness.py")
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class LocalHarnessBoundaryTests(unittest.TestCase):
    def test_run_bodhi_cannot_import_or_read_outside_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            result = run_cli(CLI, "init", vault,
                             "--answers", '{"os":"macos","harness":"undecided","model_access":"none"}')
            self.assertEqual(result.returncode, 0, result.stderr)
            outside = root / "private.txt"
            outside.write_text("PRIVATE-OUTSIDE-SENTINEL", encoding="utf-8")
            for args in (
                ["capture", str(vault), "--file", str(outside), "--source", "test"],
                ["capture", str(vault), "--file=" + str(outside), "--source", "test"],
                ["onboard-complete", str(vault), "--priority-file", str(outside),
                 "--capability", "Review one note", "--receipt", "First session"],
                ["init", str(root / "another-vault")],
                ["check", str(root)],
                ["onboard-complete", str(vault), "--priority", "Write listings",
                 "--capability", "Draft one listing", "--receipt", "First session",
                 "--source-ref", str(outside)],
            ):
                response = harness.run_tool(vault, "run_bodhi", {"args": args})
                self.assertTrue(response.startswith("error:"), response)
            self.assertFalse((root / "another-vault").exists())
            self.assertEqual((vault / "evidence/captures.jsonl").read_text(encoding="utf-8").strip(), "")

            local = vault / "safe.txt"
            local.write_text("inside", encoding="utf-8")
            response = harness.run_tool(vault, "run_bodhi", {
                "args": ["onboard-complete", str(vault), "--priority", "Write better listings",
                         "--capability", '"Write better listings" one at a time.',
                         "--receipt", "Player One chose the first listing."]},
                source_ref="test:actual-trial-transcript")
            self.assertIn("exit 0", response)
            answer = json.loads((vault / "sources/hello_world_answer.json").read_text(encoding="utf-8"))
            self.assertEqual(answer["source_ref"], "test:actual-trial-transcript")
            response = harness.run_tool(vault, "run_bodhi", {
                "args": ["capture", str(vault), "--file", str(local), "--source", "test"]})
            self.assertIn("exit 0", response)
            self.assertNotIn("PRIVATE-OUTSIDE-SENTINEL", response)

    def test_search_skips_symlink_to_outside_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            vault.mkdir()
            outside = root / "private.txt"
            outside.write_text("PRIVATE-OUTSIDE-SENTINEL", encoding="utf-8")
            (vault / "shortcut.txt").symlink_to(outside)
            result = harness.run_tool(vault, "search_files", {"query": "PRIVATE-OUTSIDE-SENTINEL"})
            self.assertEqual(result, "no matches for 'private-outside-sentinel'")


if __name__ == "__main__":
    unittest.main()
