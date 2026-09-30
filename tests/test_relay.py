"""Relay: cross-harness continuity in one append-only ledger (bin/bodhi.py relay)."""

import importlib.util
import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from test_bodhi import CLI, PYTHON, run_cli

ANSWERS = json.dumps({"os": "linux", "harness": "undecided", "model_access": "none"})


def load_bodhi():
    spec = importlib.util.spec_from_file_location("bodhi_relay", str(CLI))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RelayTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bodhi-relay-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        result = run_cli(CLI, "init", self.vault, "--answers", ANSWERS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.ledger = self.vault / "relay/ledger.jsonl"

    def relay(self, *args, lane=None, stdin=None, env_update=None, cwd=None, cli=None):
        env = {key: value for key, value in os.environ.items()
               if key not in ("BODHI_LANE", "BODHI_VAULT")}
        env.update(env_update or {})
        command = [str(PYTHON), str(cli or self.vault / "bin/bodhi.py"), "relay"] + list(args)
        if lane:
            command += ["--as", lane]
        return subprocess.run(command, input=stdin, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, cwd=str(cwd or self.root), check=False)

    def write(self, *args, lane=None, **kwargs):
        result = self.relay(*args, lane=lane, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["git"], "committed")
        return receipt["event"]

    def refused(self, *args, lane=None, contains=""):
        result = self.relay(*args, lane=lane)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(contains, result.stderr)
        return result.stderr

    def thread(self, thread_id):
        result = self.relay("show", thread_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def plant(self, *events):
        """Write events directly, as if a harness had written them earlier."""
        self.ledger.parent.mkdir(exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")


class LifecycleTests(RelayTestCase):
    def test_missing_ledger_exits_3_instead_of_answering_empty(self):
        for args in (("list",), ("brief",), ("show", "c1234")):
            result = self.relay(*args)
            self.assertEqual(result.returncode, 3, args)
            self.assertIn("not the same as 'nothing is waiting'", result.stderr)

    def test_handoff_claim_takeover_release_done_reopen_drop(self):
        handoff = self.write("handoff", "--to", "hermes", "Draft the listing",
                             "Done when: one approved draft.", lane="claude-code")
        tid = handoff["id"]
        self.assertEqual(self.thread(tid)["state"], "open")
        self.write("claim", tid, lane="hermes")
        self.assertEqual(self.thread(tid)["owner"], "hermes")
        self.write("claim", tid, lane="codex")  # a second claim takes over
        self.assertEqual(self.thread(tid)["owner"], "codex")
        self.write("release", tid, "stopped mid-draft; outline saved", lane="codex")
        released = self.thread(tid)
        self.assertEqual(released["state"], "open")
        self.assertNotIn("owner", released)
        self.refused("release", tid, lane="codex", contains="only a claimed thread can be released")
        self.write("done", tid, "Draft saved; Player One approved it", lane="hermes")
        done = self.thread(tid)
        self.assertEqual((done["state"], done["closed_by"], done["resolution"]),
                         ("done", "hermes", "Draft saved; Player One approved it"))
        self.refused("claim", tid, lane="codex", contains="reopen it first")
        self.write("reopen", tid, "Player One wants a second draft", lane="hermes")
        self.assertEqual(self.thread(tid)["state"], "open")
        self.refused("reopen", tid, contains="only a done or dropped thread")
        self.write("drop", tid, "superseded by the new listing plan", lane="hermes")
        self.assertEqual(self.thread(tid)["state"], "dropped")
        history = self.thread(tid)["log"]
        self.assertEqual([entry["kind"] for entry in history],
                         ["claim", "claim", "release", "done", "reopen", "drop"])
        shown = self.relay("show", tid)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        for words in ("Draft the listing", "Done when: one approved draft.", "stopped mid-draft",
                      "Draft saved; Player One approved it", "Player One wants a second draft",
                      "superseded by the new listing plan", "History, oldest first"):
            self.assertIn(words, shown.stdout)

    def test_records_are_logged_retracted_and_restored(self):
        decision = self.write("decide", "Listings before profit", "Player One chose it", lane="hermes")
        self.assertEqual((decision["kind"], self.thread(decision["id"])["state"]),
                         ("decision", "logged"))
        self.refused("claim", decision["id"], contains="takes reply, drop")
        self.write("reply", decision["id"], "Agreed after the second session", lane="codex")
        self.write("drop", decision["id"], "Player One changed their mind", lane="hermes")
        self.assertEqual(self.thread(decision["id"])["state"], "retracted")
        self.refused("drop", decision["id"], contains="already retracted")
        self.write("reopen", decision["id"], "restored", lane="hermes")
        self.assertEqual(self.thread(decision["id"])["state"], "logged")

    def test_reply_needs_text_and_title_is_required(self):
        note = self.write("note", "Context for later", lane="hermes")
        self.refused("reply", note["id"], contains="a reply needs text")
        self.refused("note", "   ", contains="needs a title")

    def test_body_dash_reads_standard_input(self):
        note = self.write("note", "From stdin", "-", lane="hermes", stdin="line one\r\nline two\n\n")
        self.assertEqual(note["body"], "line one\nline two")


class IdTests(RelayTestCase):
    def test_ids_are_short_unique_and_accept_prefixes(self):
        ids = [self.write("note", "Note %d" % index, lane="hermes")["id"] for index in range(4)]
        tid = self.write("handoff", "Work", lane="hermes")["id"]
        for value in ids + [tid]:
            self.assertRegex(value, r"^c[0-9a-z]{5}$")
        self.write("claim", tid[:4], lane="codex")
        self.write("reply", "#" + tid[:5], "hash prefix works too", lane="codex")
        self.refused("done", tid[:3], contains="at least 4 characters")
        events = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len({event["id"] for event in events}), len(events))

    def test_ambiguous_prefix_names_the_matches(self):
        now = int(time.time())
        self.plant({"id": "cabcd1", "kind": "handoff", "from": "a", "to": "any", "title": "one", "ts": now},
                   {"id": "cabcd2", "kind": "handoff", "from": "a", "to": "any", "title": "two", "ts": now})
        stderr = self.refused("claim", "cabc", contains="matches 2 threads")
        self.assertIn("cabcd1", stderr)
        self.write("claim", "cabcd2", lane="b")

    def test_new_ids_avoid_every_existing_event_id(self):
        bodhi = load_bodhi()
        taken = {"c" + format(index, "05d") for index in range(1000)}
        for _ in range(200):
            self.assertNotIn(bodhi.relay_new_id(taken), taken)


class ExpiryAndLaneTests(RelayTestCase):
    def test_pokes_expire_after_a_day_unless_claimed(self):
        now = int(time.time())
        self.plant({"id": "cold01", "kind": "poke", "from": "hermes", "to": "any",
                    "title": "Yesterday's poke", "ts": now - 90000, "ttl": 86400})
        fresh = self.write("poke", "Today's poke", lane="hermes")
        self.assertEqual(fresh["ttl"], 86400)
        self.assertEqual(self.thread("cold01")["state"], "expired")
        self.assertEqual(self.thread(fresh["id"])["state"], "open")
        claimed = self.write("handoff", "Being worked", lane="hermes")
        self.write("claim", claimed["id"], lane="codex")
        brief = self.relay("brief").stdout
        order = [brief.index(title) for title in ("Today's poke", "Yesterday's poke", "Being worked")]
        self.assertEqual(order, sorted(order), "open, then expired, then claimed")
        self.write("claim", "cold01", lane="codex")  # an expired poke can still be taken
        self.assertEqual(self.thread("cold01")["state"], "claimed")

    def test_fold_expiry_is_a_pure_function_of_time(self):
        bodhi = load_bodhi()
        events = [{"id": "cp0001", "kind": "poke", "from": "a", "to": "any", "title": "t",
                   "ts": 1000, "ttl": 86400}]
        self.assertEqual(bodhi.relay_fold(events, 1000 + 86400)["by_id"]["cp0001"]["state"], "open")
        self.assertEqual(bodhi.relay_fold(events, 1001 + 86400)["by_id"]["cp0001"]["state"], "expired")
        events[0]["ttl"] = 0
        self.assertEqual(bodhi.relay_fold(events, 10 ** 10)["by_id"]["cp0001"]["state"], "open")

    def test_lane_filter_and_lanes_derived_from_events(self):
        to_codex = self.write("handoff", "--to", "codex", "For codex", lane="claude-code")
        to_hermes = self.write("handoff", "--to", "hermes", "For hermes", lane="codex")
        anyone = self.write("poke", "For anyone", lane="claude-code")
        listed = self.relay("list", "--for", "hermes").stdout
        self.assertIn(to_hermes["id"], listed)
        self.assertIn(anyone["id"], listed)
        self.assertNotIn(to_codex["id"], listed)
        mine = self.relay("list", "--for", "claude-code").stdout
        self.assertIn(to_codex["id"], mine)  # a lane also sees what it sent
        brief = self.relay("brief", env_update={"BODHI_LANE": "hermes"}).stdout
        self.assertIn("# Relay brief for hermes", brief)
        self.assertNotIn("For codex", brief)
        lanes_line = [line for line in brief.splitlines() if line.startswith("Lanes seen:")][0]
        for lane in ("hermes", "codex", "claude-code"):  # hermes never wrote; it was addressed
            self.assertIn(lane, lanes_line)

    def test_lane_names_are_normalized(self):
        event = self.write("note", "Signed", lane="Claude Code (Opus)!")
        self.assertEqual(event["from"], "claude-code-opus")
        long_lane = self.write("note", "Long", lane="x" * 60)
        self.assertEqual(long_lane["from"], "x" * 40)
        unsigned = self.relay("note", "No byline")
        self.assertEqual(json.loads(unsigned.stdout)["event"]["from"], "unsigned")
        self.assertIn("Sign with --as", unsigned.stderr)


class SafetyTests(RelayTestCase):
    def test_credential_shapes_are_refused_with_a_reason(self):
        shapes = ("sk-" + "a1" * 10, "ghp_" + "A" * 24, "github_pat_" + "a" * 22,
                  "xoxb-" + "1" * 12, "AKIA" + "ABCDEFGHIJKLMNOP",
                  "-----BEGIN RSA PRIVATE KEY-----", "api_key=abcd1234efgh", "token: abcdefgh",
                  "password=hunter2hunter2", "secret: s3cr3tv4lu3")
        for shape in shapes:
            stderr = self.refused("note", "Setup notes", "the value is " + shape, lane="hermes",
                                  contains="looks like a credential")
            self.assertIn("Nothing was written", stderr)
            self.refused("note", "key " + shape, lane="hermes", contains="looks like a credential")
        self.assertFalse(self.ledger.exists())
        for benign in ("The token expires tomorrow", "password rotation is due",
                       "api keys live in the harness's secret store"):
            self.write("note", benign, lane="hermes")

    def test_limits(self):
        self.refused("note", "t" * 161, contains="limited to 160 characters")
        self.refused("note", "ok", "b" * 4001, contains="limited to 4000 characters")
        self.write("note", "t" * 160, "b" * 4000, lane="hermes")
        self.refused("poke", "--ttl", "soon", "x", contains="ttl must be whole seconds")

    def test_unicode_round_trip(self):
        title = "Übergabe — 準備 ✓"
        body = "Zeile eins\nnaïve café, 日本語, emoji 🌱 and a tab\there"
        event = self.write("note", title, body, lane="hermes")
        thread = self.thread(event["id"])
        self.assertEqual((thread["title"], thread["body"]), (title, body))
        raw = self.ledger.read_bytes().decode("utf-8")
        self.assertIn(title, raw)  # stored as UTF-8, readable with grep
        self.assertIn(title, self.relay("brief").stdout)

    def test_wrong_surface_is_refused(self):
        outside = self.root / "not-a-vault"
        outside.mkdir()
        result = self.relay("list", cli=CLI, cwd=outside)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no Bodhi vault", result.stderr)
        result = self.relay("list", "--vault", str(outside), cli=CLI)
        self.assertIn("is not a Bodhi vault", result.stderr)
        # The installer's CLI finds the vault from inside it, and BODHI_VAULT works too.
        self.write("note", "from inside", lane="hermes", cli=CLI, cwd=self.vault / "projects")
        self.write("note", "by env", lane="hermes", cli=CLI, env_update={"BODHI_VAULT": str(self.vault)})


class LedgerTests(RelayTestCase):
    def test_every_write_is_one_line_and_one_commit_even_in_parallel(self):
        env = {key: value for key, value in os.environ.items() if key != "BODHI_LANE"}
        procs = [subprocess.Popen([str(PYTHON), str(self.vault / "bin/bodhi.py"), "relay", "note",
                                   "--as", "lane-%d" % index, "Parallel note %d" % index],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                 for index in range(6)]
        for proc in procs:
            _, err = proc.communicate(timeout=60)
            self.assertEqual(proc.returncode, 0, err)
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 6)
        self.assertEqual(len({json.loads(line)["id"] for line in lines}), 6)
        commits = subprocess.run(["git", "-C", str(self.vault), "log", "--format=%s", "--",
                                  "relay/ledger.jsonl"], stdout=subprocess.PIPE, text=True,
                                 check=True).stdout.splitlines()
        self.assertEqual(len(commits), 6)
        status = subprocess.run(["git", "-C", str(self.vault), "status", "--porcelain"],
                                stdout=subprocess.PIPE, text=True, check=True).stdout
        self.assertEqual(status.strip(), "")

    def test_ledger_is_append_only(self):
        first = self.write("note", "First", lane="hermes")
        before = self.ledger.read_bytes()
        self.write("reply", first["id"], "an addition", lane="codex")
        self.assertTrue(self.ledger.read_bytes().startswith(before))

    def test_unreadable_lines_are_counted_not_fatal(self):
        self.write("note", "Readable", lane="hermes")
        with self.ledger.open("a", encoding="utf-8") as stream:
            stream.write("{not json\n")
        brief = self.relay("brief")
        self.assertEqual(brief.returncode, 0, brief.stderr)
        self.assertIn("1 unreadable lines skipped", brief.stdout)

    def test_brief_has_every_section_and_a_way_to_write_back(self):
        self.write("handoff", "--to", "hermes", "Open handoff", lane="codex")
        done = self.write("handoff", "Finished work", lane="codex")
        self.write("done", done["id"], "verified by rereading the file", lane="hermes")
        self.write("decide", "A settled call", "because Player One said so", lane="hermes")
        self.write("note", "A note", lane="codex")
        brief = self.relay("brief", "--for", "hermes").stdout
        sections = ["## Open threads for hermes or anyone", "## Decisions and notes, newest first",
                    "## Recently closed", "## Write back"]
        positions = [brief.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        for words in ("Open handoff", "A settled call", "because Player One said so", "A note",
                      "Finished work", "verified by rereading the file", "relay claim <id>",
                      "Never put credentials here"):
            self.assertIn(words, brief)
        self.assertLess(brief.index("A note"), brief.index("A settled call"), "newest first")


if __name__ == "__main__":
    unittest.main()
