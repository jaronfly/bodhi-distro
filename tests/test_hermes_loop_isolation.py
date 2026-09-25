import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hermes_loop", ROOT / "evals/hermes/hermes_loop.py")
hermes_loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hermes_loop)


class HermesLoopIsolationTests(unittest.TestCase):
    def test_freeze_records_the_exact_installer_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            commit = hermes_loop.freeze(Path(temp) / "seed", "HEAD")
            expected = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                      capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(commit, expected)
            self.assertTrue((Path(temp) / "seed/distribution.yaml").is_file())
            with self.assertRaisesRegex(RuntimeError, "seed ref does not resolve"):
                hermes_loop.freeze(Path(temp) / "bad-seed", "no-such-bodhi-ref")

    def test_trial_env_keeps_only_selected_key_and_runtime_settings(self):
        with patch.dict(os.environ, {"BODHI_UNRELATED_SECRET": "do-not-pass",
                                  "PATH": "/usr/bin", "HOME": "/real-home"}, clear=True):
            env = hermes_loop.trial_env(Path("/scratch"), Path("/scratch/hermes"),
                                        {"BODHI_SELECTED_KEY": "selected"})
        self.assertEqual(env["HOME"], "/scratch")
        self.assertEqual(env["HERMES_HOME"], "/scratch/hermes")
        self.assertEqual(env["BODHI_SELECTED_KEY"], "selected")
        self.assertNotIn("BODHI_UNRELATED_SECRET", env)

    def test_missing_provider_key_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(hermes_loop, "LIVE_HERMES_ROOT", Path(temp)):
                with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(RuntimeError, "provider key is not available"):
                        hermes_loop.provider_env("BODHI_TRIAL_TEST_KEY_NOT_REAL")


if __name__ == "__main__":
    unittest.main()
