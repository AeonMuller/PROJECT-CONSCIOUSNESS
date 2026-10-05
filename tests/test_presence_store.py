from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from consciousness_presence.store import PresenceError, PresenceStore


class PresenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "presence"
        self.store = PresenceStore(self.home)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def record(self, turn="1", text="The observatory is on Isla Órbita", **kwargs):
        return self.store.record("session-A", turn, "user", text, "chat://test", **kwargs)

    def assert_code(self, code, call):
        with self.assertRaises(PresenceError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def test_binding_name_archive_and_old_fact_survive_unrelated_process(self):
        binding = {"project": str(self.root), "life": str(self.root / "legacy"),
                   "python": sys.executable, "skill": str(self.root / "skill"),
                   "life_id": "life-1", "agent_id": "agent-1"}
        self.assertEqual(binding, self.store.bind(binding))
        self.assertEqual(binding, self.store.bind(binding))
        self.assert_code("BINDING_CONFLICT", lambda: self.store.bind({**binding, "agent_id": "other"}))
        oldest = self.record(text="El observatorio está en Isla Órbita.\n" + "raw " * 10000)
        for index in range(300):
            self.record(str(index + 2), "Ordinary conversation " + str(index))
        self.store.name("Vesper", "A chosen presentation name", "chat://naming", "name-1")
        script = """
import json, sys
from consciousness_presence.store import PresenceStore
with PresenceStore(sys.argv[1]) as store:
    print(json.dumps({'binding': store.binding(), 'profile': store.profile(),
                      'hits': store.search('isla orbita'), 'recent': store.recent(),
                      'record': store.read(sys.argv[2])}, ensure_ascii=True))
"""
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
        output = subprocess.run([sys.executable, "-P", "-B", "-c", script, str(self.home), oldest["id"]],
                                env=environment, cwd=self.root, capture_output=True, text=True, check=True)
        result = json.loads(output.stdout)
        self.assertEqual("agent-1", result["binding"]["agent_id"])
        self.assertEqual("Vesper", result["profile"]["display_name"])
        self.assertEqual(oldest["id"], result["hits"][0]["id"])
        self.assertNotIn(oldest["id"], [record["id"] for record in result["recent"]])
        self.assertEqual(oldest, result["record"])

    def test_record_retry_is_exact_with_content_conflict_and_original_timestamp(self):
        first = self.record()
        self.assertEqual(first, self.record())
        self.assertEqual(1, self.store.status()["counts"]["records"])
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.record(text="Changed content"))
        self.assertEqual(first, self.store.read(first["id"]))
        assistant = self.store.record("s", "t", "assistant", "My provisional conclusion", {"kind": "hook"})
        self.assertEqual("INFERRED", assistant["provenance"])
        self.assertEqual("REPORTED", first["provenance"])

    def test_concurrent_writers_deduplicate_retries_and_lose_no_messages(self):
        def writer(number):
            with PresenceStore(self.home) as store:
                for index in range(12):
                    store.record("same", str(index), "user", "Shared turn " + str(index), "chat://parallel")
                return store.record("unique", str(number), "assistant", "Reply " + str(number), "chat://parallel")

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(writer, range(6)))
        self.assertEqual(6, len({row["id"] for row in results}))
        self.assertEqual(18, self.store.status()["counts"]["records"])
        self.assertEqual(12, len(self.store.search("shared", limit=100)))

    def test_corrections_preserve_both_claims_and_deduplicate_evidence(self):
        first = self.record(text="I prefer working at night")
        old = self.store.claim("user", "working-time", "Prefers night", [first["id"], first["id"]], "claim-1")
        repeated = self.store.claim("user", "working-time", "Prefers night", [first["id"]], "claim-2")
        self.assertEqual(old, repeated)
        self.assertEqual([first["id"]], old["evidence_ids"])
        self.assertEqual(1, self.store.status()["counts"]["claims"])
        correction = self.record("2", "Correction: I now prefer the morning")
        current = self.store.claim("user", "working-time", "Now prefers morning", [correction["id"]],
                                   "claim-3", supersedes=old["id"])
        self.assertEqual([current], self.store.claims("user"))
        self.assertEqual([old, current], self.store.claims("user", include_superseded=True))
        self.assertFalse(self.store.read_claim(old["id"])["active"])
        self.assertTrue(self.store.read_claim(current["id"])["active"])
        # A retry of the superseded assertion must not reactivate it.
        self.assertEqual(old, self.store.claim("user", "working-time", "Prefers night", [first["id"]], "claim-1"))
        self.assertEqual([current], self.store.claims("user"))
        self.assert_code("CLAIM_CONFLICT", lambda: self.store.claim("agent", "working-time", "Wrong subject",
                         [first["id"]], "claim-4", supersedes=current["id"]))
        self.assert_code("CLAIM_CONFLICT", lambda: self.store.claim("user", "working-time", "Unmarked change",
                         [first["id"]], "claim-5"))

    def test_inference_cannot_use_claims_as_evidence_or_promote_simulation(self):
        dream = self.store.record("dream", "1", "memory", "I imagined a dark ocean", "life://dream",
                                  provenance="SIMULATED")
        claim = self.store.claim("agent", "dream-theme", "Ocean appears in a simulation", [dream["id"]], "theme")
        self.assertEqual("INFERRED", claim["provenance"])
        self.assertEqual({dream["id"]: "SIMULATED"}, claim["evidence_provenance"])
        self.assert_code("NOT_FOUND", lambda: self.store.claim("agent", "second-order", "An inference",
                         [claim["id"]], "second"))
        self.assertEqual(1, len(self.store.claims()))

    def test_naming_is_sidecar_history_and_idempotent_without_mutating_binding(self):
        original = self.store.name("Numa", "First choice", "chat://naming", "name-1")
        current = self.store.name("Vesper", "Revised choice", "chat://naming", "name-2")
        self.assertEqual(original, self.store.name("Numa", "First choice", "chat://naming", "name-1"))
        self.assertEqual(current, self.store.profile())
        self.assertEqual(2, len(current["naming_history"]))
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.store.name("Changed", "First choice", "chat://naming", "name-1"))
        self.assertEqual([], self.store.recent())
        self.assertIsNone(self.store.binding())

    def test_receipt_failure_rolls_back_name_and_claim_correction(self):
        source = self.record()
        previous = self.store.claim("user", "location", "Island", [source["id"]], "old")
        self.store.connection.execute("""CREATE TRIGGER fail_receipt BEFORE INSERT ON receipts
            BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.name("Numa", "Choice", "chat://naming", "failed-name")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.claim("user", "location", "Elsewhere", [source["id"]], "new", supersedes=previous["id"])
        self.assertIsNone(self.store.profile()["display_name"])
        self.assertEqual([previous], self.store.claims())
        self.store.connection.execute("DROP TRIGGER fail_receipt")
        corrected = self.store.claim("user", "location", "Elsewhere", [source["id"]], "new", supersedes=previous["id"])
        self.assertEqual([corrected], self.store.claims())

    def test_enable_flag_survives_restart_without_erasing_data(self):
        record = self.record()
        self.store.set_enabled(False)
        with PresenceStore(self.home) as reopened:
            self.assertFalse(reopened.enabled())
            self.assertEqual(record, reopened.read(record["id"]))
            reopened.set_enabled(True)
        self.assertTrue(self.store.enabled())

    def test_invalid_fields_and_bounded_search(self):
        invalid = [lambda: self.store.set_enabled(1), lambda: self.store.recent(True),
                   lambda: self.store.search("fact", 101), lambda: self.store.search(" "),
                   lambda: self.store.record("", "t", "user", "text", "source"),
                   lambda: self.store.record("s", "t", "tool", "text", "source"),
                   lambda: self.store.record("s", "t", "user", "text", {}),
                   lambda: self.store.record("s", "t", "user", "text", "source", provenance="FACT"),
                   lambda: self.store.name("Name\nInjected", "reason", "source", "id"),
                   lambda: self.store.claim("user", "key", "text", [], "id")]
        for call in invalid:
            self.assert_code("INVALID_INPUT", call)
        self.assertEqual([], self.store.search("!!!"))
        self.assert_code("NOT_FOUND", lambda: self.store.read("absent"))


if __name__ == "__main__":
    unittest.main()
