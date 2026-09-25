import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("groundhog", ROOT / "evals/local/groundhog.py")
groundhog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(groundhog)


class RecordedWordsTests(unittest.TestCase):
    def test_quote_is_checked_against_player_ones_actual_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            transcript = Path(temp) / "transcript.jsonl"
            transcript.write_text("\n".join(json.dumps(row) for row in (
                {"role": "user", "content": "Hello, Bodhi."},
                {"role": "assistant", "content": "Let's start with the listings."},
                {"role": "user", "content": "Let's start with the listings. I have twelve products."},
            )), encoding="utf-8")
            check = groundhog.check_recorded_words(
                {"capability_verbatim": "“Let’s start with the listings.” Make one draft."}, transcript)
            self.assertEqual(check["quote_status"], "matched")
            self.assertEqual(check["matched_user_turn"], 2)
            self.assertTrue(check["quote_leads_capability"])

            fabricated = groundhog.check_recorded_words(
                {"capability_verbatim": '"Generate friendly listings and a profit template."'}, transcript)
            self.assertEqual(fabricated["quote_status"], "unmatched")
            self.assertIsNone(fabricated["matched_user_turn"])

            unquoted = groundhog.check_recorded_words(
                {"capability_verbatim": "Draft one listing."}, transcript)
            self.assertEqual(unquoted["quote_status"], "absent")


if __name__ == "__main__":
    unittest.main()
