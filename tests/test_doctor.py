"""bin/bodhi.py doctor: every finding in words, each problem with a one-line fix."""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_bodhi import CLI, PYTHON

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/bodhi-seed"
ANSWERS = json.dumps({"os": "linux", "harness": "undecided", "model_access": "none"})


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-doctor-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def env(self):
        env = {key: value for key, value in os.environ.items()
               if key not in ("CLAUDE_CONFIG_DIR", "HERMES_HOME", "BODHI_HOME", "BODHI_SEED_DIR",
                              "BODHI_VAULT")}
        env.update({"HOME": str(self.home), "PATH": str(self.bin) + ":/usr/bin:/bin"})
        return env

    def doctor(self, *args):
        result = subprocess.run([str(PYTHON), str(CLI), "doctor", "--json", "--seed", str(ROOT)] +
                                [str(a) for a in args], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=self.env(),
                                cwd=str(self.root), check=False)
        report = json.loads(result.stdout)
        return result.returncode, report, {c["what"]: c for c in report["checks"]}

    def copy_skill(self, relative):
        dest = self.home / relative
        shutil.copytree(str(SKILL), str(dest))
        return dest

    def harness(self, name):
        path = self.bin / name
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)

    def find(self, checks, words):
        hits = [check for what, check in checks.items() if words in what]
        self.assertTrue(hits, "no check mentions %r: %s" % (words, list(checks)))
        return hits[0]

    def test_matching_copies_pass_and_name_the_first_message(self):
        self.copy_skill(".claude/skills/bodhi-seed")
        self.copy_skill(".hermes/skills/agents/bodhi-seed")  # filed under a category
        code, report, checks = self.doctor()
        self.assertEqual(code, 0)
        self.assertEqual(self.find(checks, "Claude Code: skill")["status"], "ok")
        self.assertEqual(self.find(checks, "Hermes: skill")["status"], "ok")
        self.assertIn({"harness": "Claude Code", "message": "/bodhi-seed Hello, Bodhi."},
                      report["first_messages"])
        self.assertEqual(report["greeting"], "Bodhi online. Just a seed, for now.")

    def test_round_trip_names_one_message_per_harness_and_the_one_right_reply(self):
        self.copy_skill(".claude/skills/bodhi-seed")
        self.copy_skill(".agents/skills/bodhi-seed")
        code, report, _ = self.doctor("--code", "7f3a")
        self.assertEqual(code, 0)
        self.assertEqual(report["load_check"], {
            "messages": [{"harness": "Claude Code", "message": "/bodhi-seed bodhi check 7f3a"},
                         {"harness": "Codex and OpenClaw", "message": "$bodhi-seed bodhi check 7f3a"}],
            "reply": "Bodhi seed 0.01 loaded. Check a3f7."})
        result = subprocess.run([str(PYTHON), str(CLI), "doctor", "--seed", str(ROOT), "--plain",
                                 "--code", "7f3a"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=self.env(), cwd=str(self.root), check=False)
        lines = [line.strip() for line in result.stdout.splitlines()]
        self.assertIn("/bodhi-seed bodhi check 7f3a", lines)
        self.assertIn("Bodhi seed 0.01 loaded. Check a3f7.", lines, "the reply sits whole on its own line")

    def test_round_trip_code_is_fresh_and_never_a_palindrome(self):
        self.copy_skill(".claude/skills/bodhi-seed")
        replies = {self.doctor()[1]["load_check"]["reply"] for _ in range(3)}
        self.assertGreater(len(replies), 1, "a fixed code would let an old answer pass")
        spec = importlib.util.spec_from_file_location("bodhi_cli", str(CLI))
        bodhi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bodhi)
        for _ in range(200):
            code = bodhi.new_check_code()
            self.assertNotEqual(code, code[::-1])

    def test_optional_skill_copies_are_compared_with_the_seed(self):
        self.copy_skill(".claude/skills/bodhi-seed")
        grill = self.home / ".claude/skills/bodhi-grill"
        shutil.copytree(str(ROOT / "skills/bodhi-grill"), str(grill))
        _, _, checks = self.doctor()
        self.assertEqual(self.find(checks, "optional skill bodhi-grill matches")["status"], "ok")
        (grill / "SKILL.md").write_text("---\nname: bodhi-grill\ndescription: old\n---\n", encoding="utf-8")
        _, _, checks = self.doctor()
        self.assertEqual(self.find(checks, "optional skill bodhi-grill differs")["status"], "warn")

    def test_stale_copy_warns_with_a_fix(self):
        copy = self.copy_skill(".agents/skills/bodhi-seed")
        (copy / "SKILL.md").write_text("---\nname: bodhi-seed\ndescription: old\n---\n", encoding="utf-8")
        code, report, checks = self.doctor()
        check = self.find(checks, "Codex and OpenClaw: skill")
        self.assertEqual((check["status"], code), ("warn", 0))
        self.assertIn("./install.sh --update", check["fix"])

    def test_installed_harness_without_the_skill_is_a_note_with_a_fix(self):
        self.harness("codex")
        code, _, checks = self.doctor()
        check = self.find(checks, "Codex and OpenClaw is installed but has no Bodhi skill")
        self.assertEqual((check["status"], code), ("note", 0))
        self.assertIn("./install.sh", check["fix"])

    def test_vault_checks_git_status_and_relay(self):
        vault = self.root / "vault"
        made = subprocess.run([str(PYTHON), str(CLI), "init", str(vault), "--answers", ANSWERS],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        self.assertEqual(made.returncode, 0, made.stderr)
        code, _, checks = self.doctor(vault)
        self.assertEqual(code, 0)
        self.assertEqual(self.find(checks, "everything is committed")["status"], "ok")
        self.assertEqual(self.find(checks, "No relay ledger yet")["status"], "note")
        (vault / "inbox/new.md").write_text("draft", encoding="utf-8")
        relay = subprocess.run([str(PYTHON), str(vault / "bin/bodhi.py"), "relay", "note", "--as",
                                "test", "Hello"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, check=False)
        self.assertEqual(relay.returncode, 0, relay.stderr)
        code, _, checks = self.doctor(vault)
        self.assertEqual(self.find(checks, "uncommitted change")["status"], "warn")
        self.assertEqual(self.find(checks, "Relay ledger is present")["status"], "ok")
        (vault / "AGENTS.md").unlink()
        code, report, checks = self.doctor(vault)
        self.assertEqual(code, 1, "a broken vault is a real problem")
        failed = [c for c in report["checks"] if c["status"] == "fail"]
        self.assertTrue(failed and all(c["fix"] for c in failed))

    def test_install_record_with_missing_paths_warns(self):
        record = self.home / ".bodhi/install-manifest.json"
        record.parent.mkdir()
        record.write_text(json.dumps({"schema": "bodhi.install-manifest/v1", "seed_dir": str(ROOT),
                                      "entries": [{"kind": "skill", "path": str(self.home / "gone")}]}),
                          encoding="utf-8")
        code, _, checks = self.doctor()
        check = self.find(checks, "install record lists paths that are gone")
        self.assertEqual((check["status"], code), ("warn", 0))

    def test_plain_text_report_has_fix_lines_and_a_result(self):
        self.harness("claude")
        result = subprocess.run([str(PYTHON), str(CLI), "doctor", "--seed", str(ROOT), "--plain"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=self.env(), cwd=str(self.root), check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("note  Claude Code is installed but has no Bodhi skill yet", result.stdout)
        self.assertIn("fix: ", result.stdout)
        self.assertIn("Result: 0 problem(s)", result.stdout)
        self.assertNotIn("\x1b[", result.stdout)


if __name__ == "__main__":
    unittest.main()
