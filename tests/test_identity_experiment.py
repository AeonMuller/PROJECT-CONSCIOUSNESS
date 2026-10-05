"""Independent checks of I1 exports against the underlying persisted histories."""

import csv
import json
from pathlib import Path
import random
import shutil
import sqlite3
import tempfile
import unittest

from project_consciousness.contracts import LabError, digest
from project_consciousness.identity_experiment import CONDITIONS, run_experiment
from project_consciousness.identity_runtime import LifeRuntime
from project_consciousness.identity_state import DOMAINS
from project_consciousness.runtime import source_fingerprint


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class IdentityExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.out = cls.root / "pilot"
        before_rng = random.getstate()
        cls.result = run_experiment(cls.out, seeds="400:401")
        cls.global_rng_unchanged = before_rng == random.getstate()

    def assert_code(self, code, call):
        with self.assertRaises(LabError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def test_pilot_exports_complete_counts_protocol_and_one_source(self):
        result = self.result
        self.assertTrue(result["valid"], result)
        self.assertTrue(self.global_rng_unchanged)
        self.assertEqual([400], result["seeds"])
        self.assertEqual(7, result["identities"])
        self.assertEqual(177, result["events"])
        self.assertEqual(60, result["followup_choices"])
        self.assertEqual(300, result["score_rows"])
        self.assertEqual(0, result["failed_checks"])
        self.assertEqual([source_fingerprint()], result["source_hashes"])
        protocol = json.loads((self.out / "protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(digest(protocol), result["protocol_hash"])
        checks = json.loads((self.out / "checks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(checks), result["checks"])
        self.assertTrue(all(item["passed"] for item in checks))
        expected_checks = {"base_recompute", "parent_unchanged", "restarted_exact_state",
                           "restarted_functional_events", "frozen_maps_and_new_memories",
                           "neutral_initial_score", "aversion_initial_score_intervention",
                           "no_dream_no_new_simulations"}
        expected_checks.update(condition + "_recompute" for condition in CONDITIONS)
        expected_checks.update(condition + "_budget_and_no_pending" for condition in CONDITIONS)
        self.assertTrue(expected_checks <= {item["check"] for item in checks})
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        for key, value in summary.items():
            self.assertEqual(value, result[key])
        report = (self.out / "report.md").read_text(encoding="utf-8")
        self.assertIn("feedback sintético", report)
        self.assertIn("No se mide conciencia", report)
        self.assertIn("400:401", report)

    def test_all_histories_recompute_and_exports_match_recorded_outcomes(self):
        identities = self.out / "identities" / "400"
        rows = {row["condition"]: row for row in read_rows(self.out / "conditions.csv")}
        scores = read_rows(self.out / "scores.csv")
        self.assertEqual(set(CONDITIONS), set(rows))
        self.assertEqual(300, len(scores))
        with LifeRuntime.open(identities / "base") as base:
            origin = base.snapshot()
            self.assertTrue(base.verify("recompute")["valid"])
            self.assertEqual(27, len(base.events()))
            self.assertEqual(83, origin["budget_remaining"])
        for condition in CONDITIONS:
            with self.subTest(condition=condition), LifeRuntime.open(identities / condition) as runtime:
                verification = runtime.verify("recompute")
                self.assertTrue(verification["valid"], verification)
                self.assertEqual(25, verification["events"])
                state, events = runtime.snapshot(), runtime.events()
                self.assertEqual(52, state["revision"])
                self.assertEqual(68, state["budget_remaining"])
                self.assertIsNone(state["pending"])
                self.assertEqual(digest(origin), runtime.manifest["parent"]["state_hash"])
                choices = [event["result"]["decision"] for event in events if event["request"]["kind"] == "choose"]
                self.assertEqual(10, len(choices))
                for domain in DOMAINS:
                    measured = sum(choice["selected"]["domain"] == domain for choice in choices)
                    self.assertEqual(measured, int(rows[condition]["selected_" + domain]))
                self.assertEqual(15, int(rows[condition]["budget_consumed"]))
                self.assertAlmostEqual(float(rows[condition]["priority_l1_change"]),
                                       sum(abs(state["priorities"][d] - origin["priorities"][d]) for d in DOMAINS))
                new_memories = [memory for memory in state["memories"] if memory["revision"] > origin["revision"]]
                for kind in ("OBSERVED", "REPORTED", "INFERRED", "SIMULATED"):
                    self.assertEqual(sum(memory["source_kind"] == kind for memory in new_memories),
                                     int(rows[condition][kind]))
                for event in events:
                    if event["request"]["kind"] == "feedback":
                        self.assertTrue(event["request"]["source_uri"].startswith("fixture://i1/"))
                        self.assertIn("Synthetic", event["request"]["text"])
                if condition == "frozen":
                    for key in ("priorities", "aversions", "competence"):
                        self.assertEqual(origin[key], state[key])
                    self.assertGreater(len(new_memories), 0)
                if condition == "no-dream":
                    self.assertEqual(0, int(rows[condition]["SIMULATED"]))
                for step, decision in enumerate(choices):
                    exported = [row for row in scores if row["condition"] == condition and int(row["step"]) == step]
                    self.assertEqual(5, len(exported))
                    self.assertTrue(all(row["selected"] == decision["selected"]["id"] for row in exported))
                    self.assertAlmostEqual(1, sum(float(row["probability"]) for row in exported))

    def test_restart_matches_state_and_events_with_independent_lineage(self):
        identities = self.out / "identities" / "400"
        with LifeRuntime.open(identities / "updated") as updated, LifeRuntime.open(identities / "restarted") as restarted:
            self.assertNotEqual(updated.manifest["life_id"], restarted.manifest["life_id"])
            self.assertEqual(updated.snapshot(), restarted.snapshot())
            for first, second in zip(updated.events(), restarted.events(), strict=True):
                self.assertNotEqual(first["event_hash"], second["event_hash"])
                self.assertNotEqual(first["previous_hash"], second["previous_hash"])
                for key in ("revision", "request_id", "request", "result", "before_hash", "after_hash"):
                    self.assertEqual(first[key], second[key])
        summary = self.result["conditions"]["restarted"]
        self.assertEqual(0, summary["choices_different_from_updated"])
        self.assertEqual(0, summary["first_choices_different_from_updated"])

    def test_invalid_seed_ranges_and_existing_outputs_never_write(self):
        for index, invalid in enumerate((None, 400, [], "", "400", "400:400", "401:400", "-1:1",
                                         "0:101", "1:2:3", "x:2", f"0:{2**63 + 1}")):
            with self.subTest(seeds=invalid):
                output = self.root / f"invalid-{index}"
                self.assert_code("INVALID_INPUT", lambda: run_experiment(output, seeds=invalid))
                self.assertFalse(output.exists())
        before = (self.out / "summary.json").read_bytes()
        self.assert_code("OUTPUT_EXISTS", lambda: run_experiment(self.out, seeds="400:401"))
        self.assertEqual(before, (self.out / "summary.json").read_bytes())
        sentinel = self.root / "existing-file"
        sentinel.write_bytes(b"preserve")
        self.assert_code("OUTPUT_EXISTS", lambda: run_experiment(sentinel, seeds="400:401"))
        self.assertEqual(b"preserve", sentinel.read_bytes())

    def test_later_archive_tampering_is_detected_by_runtime(self):
        source = self.out / "identities" / "400" / "updated"
        target = self.root / "tampered-copy"
        shutil.copytree(source, target)
        with LifeRuntime.open(target) as runtime:
            self.assertTrue(runtime.verify("recompute")["valid"])
            runtime.apply({"kind": "question", "domain": "understand", "text": "What changed?", "references": []},
                          "post-pilot-check")
            db = sqlite3.connect(target / "identity.sqlite")
            try:
                db.execute("UPDATE events SET result_json='{}' WHERE revision=28")
                db.commit()
            finally:
                db.close()
            verification = runtime.verify("reconstruct")
            self.assertFalse(verification["valid"])
            self.assertTrue(verification["errors"])
            self.assert_code("STATE_INCONSISTENT", lambda: runtime.apply({"kind": "cycle"}, "reject-corrupt"))
            self.assert_code("STATE_INCONSISTENT", runtime.export_bundle)


if __name__ == "__main__":
    unittest.main()
