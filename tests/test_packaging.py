"""Packaging the seed skill for harnesses beyond Hermes (docs/INSTALL.md)."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from test_bodhi import run_cli

ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "bin/package_skill.py"
SKILL = ROOT / "skills/bodhi-seed"


def load_packager():
    spec = importlib.util.spec_from_file_location("package_skill", str(PACKAGER))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentSkillsFormatTests(unittest.TestCase):
    def test_seed_skill_meets_the_open_agent_skills_format(self):
        errors, warnings = load_packager().check_skill(SKILL)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [], "keep the description within 200 characters for claude.ai")

    def test_checker_catches_the_mistakes_that_break_other_harnesses(self):
        packager = load_packager()
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "bodhi-seed"
            bad.mkdir()
            (bad / "SKILL.md").write_text(
                "---\nname: Bodhi-Seed\ndescription: x\nversion: 0.01\n---\nSee [a](references/NONE.md).\n",
                encoding="utf-8")
            errors, _ = packager.check_skill(bad)
            joined = " ".join(errors)
            self.assertIn("version", joined)
            self.assertIn("lowercase", joined)
            self.assertIn("references/NONE.md", joined)


class ZipTests(unittest.TestCase):
    def build(self, out):
        result = run_cli(PACKAGER, "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_zip_holds_the_skill_folder_at_its_top_level_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "bodhi-seed.zip"
            receipt = self.build(out)
            with zipfile.ZipFile(str(out)) as archive:
                names = archive.namelist()
                self.assertIn("bodhi-seed/SKILL.md", names)
                for name in names:
                    self.assertTrue(name.startswith("bodhi-seed/"), name)
                    source = SKILL / name[len("bodhi-seed/"):]
                    self.assertEqual(archive.read(name), source.read_bytes(), name)
            expected = sorted("bodhi-seed/" + p.relative_to(SKILL).as_posix()
                              for p in SKILL.rglob("*") if p.is_file())
            self.assertEqual(sorted(names), expected)
            self.assertEqual(receipt["sha256"], hashlib.sha256(out.read_bytes()).hexdigest())

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            first = self.build(Path(temp) / "a.zip")
            second = self.build(Path(temp) / "b.zip")
            self.assertEqual(first["sha256"], second["sha256"])

    def test_zip_is_never_committed(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("dist/", ignored)


class ClaudePluginMarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))

    def test_marketplace_has_the_required_fields(self):
        for field in ("name", "owner", "plugins"):
            self.assertIn(field, self.market)
        self.assertTrue(self.market["owner"]["name"])
        self.assertRegex(self.market["name"], r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

    def test_plugin_is_only_the_seed_skill(self):
        (entry,) = self.market["plugins"]
        self.assertEqual(entry["name"], "bodhi")
        source = entry["source"]
        self.assertTrue(source.startswith("./") and ".." not in source, source)
        plugin_root = (ROOT / source).resolve()
        # Only the skill folder is copied into a user's plugin cache: not sources/,
        # evals/ or the founder's material, and no top-level bin/ (claude.ai and
        # Cowork refuse plugins that have one).
        self.assertEqual(plugin_root, SKILL.resolve())
        self.assertTrue((plugin_root / "SKILL.md").is_file())
        self.assertFalse((plugin_root / "bin").exists())
        self.assertFalse((plugin_root / "skills").exists(), "a skills/ dir would replace the root SKILL.md")

    def test_entry_tracks_commits_and_claims_no_license(self):
        (entry,) = self.market["plugins"]
        self.assertNotIn("version", entry, "a pinned version would freeze users on one copy")
        self.assertNotIn("license", entry, "no license has been chosen")
        self.assertFalse((SKILL / ".claude-plugin").exists(),
                         "keep the skill folder clean for Hermes, Codex and claude.ai")


if __name__ == "__main__":
    unittest.main()
