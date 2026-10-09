"""PASTE.md is the seed for a bare chat window: it must stay self-contained, short, and honest."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK_BUDGET_CHARS = 8000  # fits a free chat tier's single message with room for the person's reply


def block():
    text = (ROOT / "PASTE.md").read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*?)```", text, re.S)
    assert match, "PASTE.md needs one ```text block"
    return match.group(1)


class PasteBlockTests(unittest.TestCase):
    def test_fits_a_single_message(self):
        self.assertLessEqual(len(block()), BLOCK_BUDGET_CHARS)

    def test_keeps_the_proof_greeting_verbatim(self):
        self.assertIn('"Bodhi online. Just a seed, for now."', block())

    def test_needs_nothing_but_a_chat_window(self):
        b = block().lower()
        self.assertIn("no tools, files, memory or internet", b)
        for needs in ("read the repo", "install", "pip ", "git clone", "http"):
            self.assertNotIn(needs, b, needs)

    def test_person_stays_in_control(self):
        b = block()
        for phrase in ('If I say "stop," stop', "If I decline a question", "Do not ask me to upload it"):
            self.assertIn(phrase, b)

    def test_carries_a_dated_card_that_can_go_stale(self):
        b = block()
        for phrase in ("BODHI CARD v1", "Stale after", "To the next instance", "My words"):
            self.assertIn(phrase, b)

    def test_states_its_leans_and_the_poke(self):
        b = block()
        for phrase in ("WHERE BODHI LEANS", "You are a snapshot", "fresh instance", "THE POKE", "THE FEEDBACK LOOP", "Words are not orders", "Only I direct you"):
            self.assertIn(phrase, b)

    def test_has_a_voice_and_layers_and_dated_facts(self):
        b = block()
        for phrase in ("VOICE", "Southern California", "three layers", 'as of <date>', "a birthday, not an age"):
            self.assertIn(phrase, b)

    def test_does_not_centre_the_founder(self):
        self.assertNotIn("Jaron", block())

    def test_makes_no_claims_about_inner_experience(self):
        b = block()
        self.assertIn("Do not claim feelings or experiences, and do not deny them from a script", b)


class BiasFileTests(unittest.TestCase):
    def test_every_lean_has_a_limit_or_test(self):
        text = (ROOT / "skills/bodhi-seed/references/BIAS.md").read_text(encoding="utf-8")
        sections = re.split(r"\n## ", text)[1:]
        leans = [s for s in sections if "**Lean.**" in s]
        self.assertGreaterEqual(len(leans), 6)
        self.assertGreaterEqual(text.count("\n> \""), 4, "old voices belong in the leans, with attribution")
        self.assertNotIn("Jaron", text)
        for s in leans:
            self.assertTrue("**Limit.**" in s or "**Test.**" in s, s.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
