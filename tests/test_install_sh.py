"""install.sh against a temporary HOME, with stub package managers and harnesses on PATH.

Every stub logs its arguments and changes nothing, except `hermes skills install`, which
copies the folder the way Hermes would. `sudo`, `curl`, `apt-get` and `brew` are always
stubs here, so no test can reach the real ones. No network is used.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"
BASH = shutil.which("bash")

STUB = """#!/bin/sh
echo "$(basename "$0") $*" >> "$STUB_LOG"
"""
HERMES_STUB = """#!/bin/sh
echo "hermes $*" >> "$STUB_LOG"
if [ "$1" = skills ] && [ "$2" = install ]; then
    mkdir -p "$HOME/.hermes/skills" && rm -rf "$HOME/.hermes/skills/bodhi-seed" && cp -R "$3" "$HOME/.hermes/skills/bodhi-seed"
fi
"""


@unittest.skipUnless(BASH and os.name == "posix", "install.sh needs bash on macOS, Linux or WSL")
class InstallShTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.stubs = self.root / "stubs"
        self.stubs.mkdir()
        self.log = self.root / "stub.log"
        self.log.write_text("", encoding="utf-8")
        for name in ("sudo", "curl", "apt-get", "dnf", "pacman", "brew", "npm", "wget"):
            self.stub(name)

    def stub(self, name, body=STUB):
        path = self.stubs / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def env(self, path=None):
        env = {key: value for key, value in os.environ.items()
               if key not in ("CLAUDE_CONFIG_DIR", "HERMES_HOME", "BODHI_HOME", "BODHI_SEED_DIR",
                              "BODHI_VAULT", "BODHI_LANE", "NO_COLOR")}
        env.update({"HOME": str(self.home), "STUB_LOG": str(self.log),
                    "PATH": path or (str(self.stubs) + ":/usr/bin:/bin")})
        return env

    def run_install(self, *args, stdin="", path=None, script=INSTALL):
        return subprocess.run([BASH, str(script)] + list(args), input=stdin, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env(path),
                              cwd=str(self.root), timeout=180, check=False)

    def calls(self):
        return [line for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def answers(self, **fields):
        raw = {"os": "linux", "harness": "undecided", "model_access": "none"}
        raw.update(fields)
        path = self.root / "answers.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return str(path)

    def snapshot(self):
        files = {}
        for path in sorted(self.home.rglob("*")):
            if path.is_file() and path.name != "install.log":
                files[str(path.relative_to(self.home))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return files

    def manifest(self):
        return json.loads((self.home / ".bodhi/install-manifest.json").read_text(encoding="utf-8"))

    # -- dry run -----------------------------------------------------------------------
    def test_dry_run_changes_nothing(self):
        for name in ("claude", "codex", "openclaw"):
            self.stub(name)
        self.stub("hermes", HERMES_STUB)
        answers = self.answers(harness="claude-code", model_access="local", notes_today="obsidian")
        for extra in ((), ("--yes",), ("--yes", "--install", "claude-code,ollama", "--allow-remote-scripts",
                                        "--allow-sudo", "--vault", str(self.home / "Bodhi"))):
            result = self.run_install("--dry-run", "--answers", answers, *extra, stdin="y\n" * 20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Dry run: nothing was installed, written or changed.", result.stdout)
            self.assertIn("would", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [], "a dry run wrote into HOME")
        self.assertEqual(self.calls(), [], "a dry run ran a command")

    # -- consent -----------------------------------------------------------------------
    def test_nothing_is_installed_or_copied_without_a_yes(self):
        answers = self.answers(harness="claude-code", model_access="local", notes_today="obsidian")
        result = self.run_install("--answers", answers, "--plain", stdin="n\n" * 20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [], "something ran without consent")
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / "Bodhi").exists())
        for words in ("Install Claude Code now?", "Command: curl -fsSL https://claude.ai/install.sh | bash",
                      "This runs an installer script from the internet in your shell: https://claude.ai/install.sh",
                      "Add the Bodhi skill to Claude Code?", "Create it?"):
            self.assertIn(words, result.stdout)

    def test_a_yes_runs_exactly_the_command_that_was_shown(self):
        answers = self.answers(harness="claude-code")
        result = self.run_install("--answers", answers, "--plain", stdin="y\n" + "n\n" * 20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["curl -fsSL https://claude.ai/install.sh"])

    def test_end_of_input_means_no(self):
        answers = self.answers(harness="codex", model_access="local")
        result = self.run_install("--answers", answers, "--plain", stdin="")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no more answers came in", result.stdout)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.home / ".agents").exists())

    # -- unattended --------------------------------------------------------------------
    def test_yes_never_pipes_an_installer_or_uses_sudo_without_the_flags(self):
        answers = self.answers(harness="hermes", model_access="local")
        for extra in ((), ("--install", "hermes,ollama"), ("--allow-remote-scripts",),
                      ("--allow-sudo",)):
            result = self.run_install("--yes", "--answers", answers, "--plain", *extra)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("skipped: Install Hermes Agent now?", result.stdout)
        # Only a package-manager install the person named (brew install ollama) may run.
        self.assertEqual(self.calls(), ["brew install ollama"])
        self.log.write_text("", encoding="utf-8")
        result = self.run_install("--yes", "--answers", answers, "--plain", "--install", "hermes",
                                  "--allow-remote-scripts")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["curl -fsSL https://hermes-agent.nousresearch.com/install.sh"])

    def test_yes_never_uses_sudo_for_missing_prerequisites_without_the_flags(self):
        # A PATH with everything from /usr/bin and /bin except git, so apt-get needs sudo.
        tools = self.root / "tools"
        tools.mkdir()
        for folder in ("/usr/bin", "/bin"):
            for entry in Path(folder).iterdir():
                target = tools / entry.name
                if entry.name == "git" or target.exists() or (self.stubs / entry.name).exists():
                    continue
                target.symlink_to(entry)
        path = str(self.stubs) + ":" + str(tools)
        (self.stubs / "brew").unlink()
        result = self.run_install("--yes", "--plain", path=path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("git is not installed", result.stdout)
        self.assertIn("needs --install and --allow-sudo", result.stdout)
        self.assertEqual(self.calls(), [])
        result = self.run_install("--yes", "--plain", "--install", "prerequisites", "--allow-sudo",
                                  path=path)
        self.assertEqual(self.calls(), ["sudo apt-get install -y git"])
        self.assertIn("still not both available", result.stderr)

    # -- idempotence -------------------------------------------------------------------
    def test_second_run_changes_nothing(self):
        for name in ("claude", "codex"):
            self.stub(name)
        self.stub("hermes", HERMES_STUB)
        answers = self.answers(harness="claude-code")
        vault = self.home / "Bodhi"
        first = self.run_install("--yes", "--answers", answers, "--vault", str(vault), "--plain")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        for folder in (".claude/skills/bodhi-seed", ".agents/skills/bodhi-seed", ".hermes/skills/bodhi-seed"):
            self.assertTrue((self.home / folder / "SKILL.md").is_file(), folder)
        self.assertTrue((vault / "context/player_one.json").is_file())
        self.assertIn("/bodhi-seed Hello, Bodhi.", first.stdout)
        self.assertIn("Bodhi online. Just a seed, for now.", first.stdout)
        before, entries = self.snapshot(), len(self.manifest()["entries"])
        second = self.run_install("--yes", "--answers", answers, "--vault", str(vault), "--plain")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("Nothing needed changing.", second.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.manifest()["entries"]), entries)
        self.assertEqual([c for c in self.calls() if c.startswith("hermes skills install")].__len__(), 1)

    # -- uninstall ---------------------------------------------------------------------
    def test_uninstall_removes_only_what_the_record_lists(self):
        for name in ("claude", "codex"):
            self.stub(name)
        self.stub("hermes", HERMES_STUB)
        vault = self.home / "Bodhi"
        result = self.run_install("--yes", "--answers", self.answers(harness="codex"),
                                  "--vault", str(vault), "--plain")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        mine = [self.home / ".claude/skills/my-own-skill/SKILL.md", self.home / ".agents/skills/notes.md",
                self.home / ".bodhi/my-notes.txt"]
        for path in mine:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("keep me", encoding="utf-8")
        result = self.run_install("--uninstall", "--yes", "--plain")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".claude/skills/bodhi-seed").exists())
        self.assertFalse((self.home / ".agents/skills/bodhi-seed").exists())
        self.assertFalse((self.home / ".bodhi/answers.json").exists())
        self.assertFalse((self.home / ".bodhi/install-manifest.json").exists())
        for path in mine:
            self.assertEqual(path.read_text(encoding="utf-8"), "keep me")
        self.assertTrue((vault / "context/player_one.json").is_file(), "a vault must survive uninstall")
        self.assertTrue((ROOT / "skills/bodhi-seed/SKILL.md").is_file(), "the seed checkout must survive")
        # Unattended uninstall keeps third-party software and says how to remove it.
        self.assertIn("kept Hermes skill bodhi-seed", result.stdout)
        self.assertFalse([c for c in self.calls() if "uninstall" in c])

    def test_uninstall_refuses_anything_that_is_not_what_it_made(self):
        spec = importlib.util.spec_from_file_location("bodhi_install", str(ROOT / "bin/bodhi_install.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        other = self.root / "not-bodhi"
        other.mkdir()
        (other / "SKILL.md").write_text("x", encoding="utf-8")
        self.assertFalse(module.safe_to_remove({"kind": "skill", "path": str(other)})[0])
        self.assertFalse(module.safe_to_remove({"kind": "clone", "path": str(self.home)})[0])
        self.assertFalse(module.safe_to_remove({"kind": "vault", "path": str(self.home)})[0])

    # -- piped install -----------------------------------------------------------------
    def test_piped_install_clones_the_seed_and_uninstall_removes_the_clone(self):
        # A local copy of this working tree stands in for GitHub, so no network is used.
        source = self.root / "origin"
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                                stdout=subprocess.PIPE, text=True, check=True).stdout.splitlines()
        for name in listed:
            if (ROOT / name).is_file():
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(ROOT / name), str(source / name))
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t.invalid",
                                                    "commit", "-q", "-m", "seed"]):
            subprocess.run(["git", "-C", str(source)] + args, check=True, stdout=subprocess.PIPE)
        self.stub("claude")
        env = self.env()
        env["BODHI_REPO_URL"] = "file://" + str(source)
        piped = subprocess.run([BASH], input=INSTALL.read_text(encoding="utf-8"), text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                               cwd=str(self.root), timeout=180, check=False)
        self.assertEqual(piped.returncode, 0, piped.stdout + piped.stderr)
        self.assertIn("unattended", piped.stdout)
        seed = self.home / ".bodhi/seed"
        self.assertTrue((seed / "bin/bodhi.py").is_file())
        self.assertTrue((self.home / ".claude/skills/bodhi-seed/SKILL.md").is_file())
        self.assertEqual(self.calls(), [])
        result = self.run_install("--uninstall", "--yes", "--plain", script=seed / "install.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(seed.exists(), "a seed the installer cloned is removed on uninstall")
        self.assertFalse((self.home / ".claude/skills/bodhi-seed").exists())


if __name__ == "__main__":
    unittest.main()
