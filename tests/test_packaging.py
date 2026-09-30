"""Packaging the seed skill for harnesses beyond Hermes (docs/INSTALL.md)."""

import hashlib
import importlib.util
import json
import re
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


class InstalledContentTests(unittest.TestCase):
    """What every harness installs: SOUL.md and the skill folder."""

    PRIVATE = re.compile(r"(?i)\b(?:100|192\.168|10)\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b|"
                         r"/mnt/user|/Users/[a-z]|:\d{4,5}\b|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
    # The founder's host, network and community names, stored as SHA-256 of the
    # lowercase word so this public test does not spell out what it guards against.
    PRIVATE_WORDS = {"795b104abe3e4134960ca245ded0e617f162c751209347b7f003bc35e062f43e",
                     "a840405ec063a57cfad884363a05acabb35af9de0f5f2be0589502338f084f7e",
                     "d7b5dad1073566ca8da7d0f19acdc38ace6d0d5b3f31b9bdffdf9114d8e77490",
                     "ec6f049478046f72becb006a2339202eae93911281dd610a7c869adec1ba3297",
                     "f0f62cfa427ad992d828a545dda6cd30853fb4e0124a29e95c38edf5005947c9"}

    def private_words(self, line):
        words = re.findall(r"[a-z0-9]+", line.lower())
        return [w for w in words if hashlib.sha256(w.encode()).hexdigest() in self.PRIVATE_WORDS]

    def test_no_private_hosts_addresses_ports_or_emails_ship(self):
        installed = [ROOT / "SOUL.md"] + sorted(SKILL.rglob("*.md"))
        for page in installed:
            for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(self.PRIVATE.search(line),
                                  "%s:%d ships a private-looking identifier: %s" % (page, number, line))
                self.assertEqual(self.private_words(line), [], "%s:%d names a private host" % (page, number))

    def test_every_reference_page_is_reachable_from_the_skill(self):
        pages = {p.name for p in (SKILL / "references").glob("*.md")}
        linked = set()
        for page in [SKILL / "SKILL.md"] + sorted((SKILL / "references").glob("*.md")):
            linked |= {Path(t).name for t in load_packager().LINK.findall(page.read_text(encoding="utf-8"))}
        self.assertEqual(pages - linked, set(), "a reference no page links to is never read")


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
