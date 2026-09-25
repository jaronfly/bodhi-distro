import json
import tempfile
import unittest
from pathlib import Path

from test_bodhi import CLI, run_cli
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def load_bodhi_module():
    spec = importlib.util.spec_from_file_location("bodhi_mod", ROOT / "bin/bodhi.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class CapabilityQuotedGateTests(unittest.TestCase):
    def test_quoted_spans_detected(self):
        mod = load_bodhi_module()
        self.assertTrue(mod._contains_quoted_span('She said "Let\'s start with the listings" — twelve products.'))
        self.assertTrue(mod._contains_quoted_span("\u201cLet\u2019s start with the listings\u201d"))
        self.assertFalse(mod._contains_quoted_span("Create on-brand candle listings that reflect her voice."))
        self.assertFalse(mod._contains_quoted_span('a "label"'))  # too short to be a sentence

    def test_record_includes_capability_quoted(self):
        with tempfile.TemporaryDirectory(prefix="bodhi-gate-") as temp:
            root = Path(temp)
            pri = root / "pri.txt"
            pri.write_text("I sell hand-poured candles online.", encoding="utf-8")
            rec = root / "rec.txt"
            rec.write_text("First session receipt.", encoding="utf-8")
            cases = (
                ("quoted", root / "cap_q.txt",
                 'She said "Let\'s start with the listings" and wants on-brand drafts.', True),
                ("paraphrase", root / "cap_p.txt",
                 "Enhanced product-listing authoring workflow.", False),
            )
            for name, cap_path, cap_text, expect in cases:
                cap_path.write_text(cap_text, encoding="utf-8")
                vault = root / ("vault-" + name)
                result = run_cli(CLI, "init", vault,
                                 "--answers", json.dumps({"os": "macos", "harness": "undecided", "model_access": "none"}))
                self.assertEqual(result.returncode, 0, result.stderr)
                done = run_cli(vault / "bin/bodhi.py", "onboard-complete", vault,
                               "--priority-file", pri, "--capability-file", cap_path,
                               "--receipt-file", rec, "--source-ref", "test:gate-" + name)
                self.assertEqual(done.returncode, 0, done.stderr)
                answer = json.loads((vault / "sources/hello_world_answer.json").read_text(encoding="utf-8"))
                self.assertEqual(answer.get("capability_quoted"), expect,
                                 f"capability_quoted should be {expect} for the {name} case")


if __name__ == "__main__":
    unittest.main()
