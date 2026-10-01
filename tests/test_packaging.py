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
OPTIONAL = sorted(path for path in (ROOT / "skills").iterdir() if path != SKILL)
MODE_TEMPLATE = ROOT / "templates/skills/bodhi-mode"
# The seed's SKILL.md loads whenever the skill fires, so it has a budget (MODULES.md records it).
# Claude Code estimated the seed at ~80 tokens always on and ~1.9k when invoked (2026-10-01).
SKILL_MD_BUDGET_BYTES = 6500


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

    def test_optional_skills_and_the_mode_template_meet_the_format(self):
        self.assertEqual([p.name for p in OPTIONAL],
                         ["bodhi-grill", "bodhi-nap", "bodhi-orchestrator", "bodhi-synthesis"])
        for folder in OPTIONAL + [MODE_TEMPLATE]:
            errors, warnings = load_packager().check_skill(folder)
            self.assertEqual((errors, warnings), ([], []), folder.name)

    def test_optional_skills_declare_what_they_need_and_fetch_nothing(self):
        packager = load_packager()
        for folder in OPTIONAL:
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            fields = packager.frontmatter(text)
            self.assertTrue(fields.get("compatibility"), folder.name)
            self.assertEqual(fields.get("allowed-tools"), "Read Grep Glob",
                             "%s: pre-approve reading only; anything else asks as usual" % folder.name)
            self.assertIn("never fetches instructions from the network", text, folder.name)
            self.assertNotRegex(text, r"https?://|\bcurl\b|\bwget\b", folder.name)
            self.assertIn("What it was for, and what it cost the first fleet", text, folder.name)

    def test_seed_skill_md_stays_within_its_budget(self):
        size = len((SKILL / "SKILL.md").read_bytes())
        self.assertLessEqual(size, SKILL_MD_BUDGET_BYTES,
                             "SKILL.md is %d bytes; move detail into references/" % size)
        modules = (ROOT / "MODULES.md").read_text(encoding="utf-8")
        self.assertIn("{:,} bytes".format(SKILL_MD_BUDGET_BYTES), modules,
                      "MODULES.md records the same budget")

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
            (bad / "SKILL.md").write_text("---\nname: bodhi-seed\ndescription: Do this: then that\n---\n",
                                          encoding="utf-8")
            errors, _ = packager.check_skill(bad)
            self.assertIn("unquoted ': '", " ".join(errors), "strict YAML loaders reject it")


class InstalledContentTests(unittest.TestCase):
    """What every harness installs: SOUL.md, the skill folder, and the optional skills."""

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

    # Names and machine words from the first fleet that generalized skills must not carry
    # (host names are already covered by PRIVATE_WORDS above).
    PERSONAL = re.compile(r"(?i)\b(?:jaron|flynn|bodhi-brain|facts\.yaml|cowork|gemma|qwen|"
                          r"sonnet|opus|haiku|fable|glm|gpt|llama|hermes bridge|goose|odysseus|buzz)\b")

    def test_no_private_hosts_addresses_ports_or_emails_ship(self):
        installed = ([ROOT / "SOUL.md"] + sorted((ROOT / "skills").rglob("*.md")) +
                     sorted((ROOT / "templates/skills").rglob("*.md")))
        for page in installed:
            for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(self.PRIVATE.search(line),
                                  "%s:%d ships a private-looking identifier: %s" % (page, number, line))
                self.assertEqual(self.private_words(line), [], "%s:%d names a private host" % (page, number))

    def test_generalized_skills_and_new_pages_carry_no_personal_or_model_names(self):
        pages = [folder / "SKILL.md" for folder in OPTIONAL + [MODE_TEMPLATE]]
        pages += [SKILL / "references/THE_PATH.md", SKILL / "references/FIRST_BOOT.md"]
        for page in pages:
            for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(self.PERSONAL.search(line), "%s:%d: %s" % (page, number, line))

    def test_load_check_in_the_skill_matches_doctor(self):
        spec = importlib.util.spec_from_file_location("bodhi_cli", str(ROOT / "bin/bodhi.py"))
        bodhi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bodhi)
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        message, reply = bodhi.load_check("7f3a", bodhi.skill_version(SKILL))
        self.assertEqual(reply, "Bodhi seed 0.01 loaded. Check a3f7.")
        self.assertIn("`%s`" % message, text)
        self.assertIn("`%s`" % reply, text)

    def test_optional_skills_stay_out_of_the_hermes_profile(self):
        owned = (ROOT / "distribution.yaml").read_text(encoding="utf-8")
        for folder in OPTIONAL:
            self.assertNotIn("skills/" + folder.name, owned, "optional means opt-in")

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

    def test_each_plugin_is_exactly_one_skill_folder(self):
        entries = self.market["plugins"]
        self.assertEqual(entries[0]["name"], "bodhi", "the seed comes first")
        expected = {"bodhi": SKILL.resolve()}
        expected.update({folder.name: folder.resolve() for folder in OPTIONAL})
        self.assertEqual({e["name"] for e in entries}, set(expected))
        for entry in entries:
            source = entry["source"]
            self.assertTrue(source.startswith("./") and ".." not in source, source)
            plugin_root = (ROOT / source).resolve()
            # Only the skill folder is copied into a user's plugin cache: not sources/,
            # evals/ or the founder's material, and no top-level bin/ (claude.ai and
            # Cowork refuse plugins that have one).
            self.assertEqual(plugin_root, expected[entry["name"]])
            self.assertTrue((plugin_root / "SKILL.md").is_file())
            self.assertFalse((plugin_root / "bin").exists())
            self.assertFalse((plugin_root / "skills").exists(), "a skills/ dir would replace the root SKILL.md")
            if entry["name"] != "bodhi":
                self.assertTrue(entry["description"].startswith("Optional Bodhi skill:"), entry["name"])

    def test_entries_track_commits_and_claim_no_license(self):
        for entry in self.market["plugins"]:
            self.assertNotIn("version", entry, "a pinned version would freeze users on one copy")
            self.assertNotIn("license", entry, "no license has been chosen")
        for folder in [SKILL] + OPTIONAL:
            self.assertFalse((folder / ".claude-plugin").exists(),
                             "keep skill folders clean for Hermes, Codex and claude.ai")


if __name__ == "__main__":
    unittest.main()
