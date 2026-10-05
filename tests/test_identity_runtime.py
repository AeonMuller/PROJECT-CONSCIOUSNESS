from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

from project_consciousness.contracts import LabError, canonical, clone, digest
from project_consciousness.identity_runtime import LifeRuntime
from project_consciousness.identity_state import DOMAINS


def candidates():
    return [{"id": domain, "domain": domain, "description": "Investigate " + domain,
             "novelty": 0.5, "cost": 0.1, "risk": 0.7} for domain in DOMAINS]


def feedback(decision_id, *, status="completed", value=0.8, harm=0.0):
    return {"kind": "feedback", "decision_id": decision_id, "status": status,
            "success": None if status == "unknown" else status == "completed",
            "value": None if status == "unknown" else value,
            "harm": None if status == "unknown" else harm,
            "text": "Reported result from an authorized host experiment.",
            "source_uri": "experiment://host/receipt"}


def add_library(runtime):
    for domain in DOMAINS:
        runtime.apply({"kind": "ingest", "domain": domain, "text": "A source document about " + domain,
                       "source_uri": "corpus://" + domain}, "ingest-" + domain)


class IdentityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_code(self, code, call):
        with self.assertRaises(LabError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def test_restart_and_recompute_preserve_complete_history_and_rng(self):
        for folder in ("continuous", "resumed"):
            with LifeRuntime.create(self.root / folder, seed=47, budget=30) as runtime:
                add_library(runtime)
                for index in range(6):
                    runtime.apply({"kind": "cycle"}, f"cycle-{index}")
        with LifeRuntime.open(self.root / "continuous") as continuous:
            for index in range(6, 15):
                continuous.apply({"kind": "cycle"}, f"cycle-{index}")
            expected_state = continuous.snapshot()
            expected_events = continuous.events()
        for index in range(6, 15):
            with LifeRuntime.open(self.root / "resumed") as resumed:
                resumed.apply({"kind": "cycle"}, f"cycle-{index}")
        with LifeRuntime.open(self.root / "resumed") as resumed:
            self.assertEqual(expected_state, resumed.snapshot())
            for expected, actual in zip(expected_events, resumed.events(), strict=True):
                for key in ("revision", "request_id", "request", "result", "before_hash", "after_hash"):
                    self.assertEqual(expected[key], actual[key])
            self.assertTrue(resumed.verify("reconstruct")["valid"])
            verification = resumed.verify()
            self.assertTrue(verification["valid"], verification)
            self.assertEqual(20, verification["events"])
            self.assertEqual(15, resumed.snapshot()["budget_remaining"])

    def test_feedback_idempotency_precedes_stale_revision_and_survives_restart(self):
        path = self.root / "feedback"
        with LifeRuntime.create(path, budget=4) as runtime:
            event = runtime.apply({"kind": "choose", "candidates": candidates()}, "choose", expected_revision=0)
            request = feedback(event["result"]["decision"]["id"], status="failed", value=-0.8, harm=0.9)
            result = runtime.apply(request, "result", expected_revision=1)
            state = runtime.snapshot()
            self.assertIsNone(state["pending"])
        with LifeRuntime.open(path) as runtime:
            self.assertEqual(result, runtime.apply(request, "result", expected_revision=1))
            self.assertEqual(state, runtime.snapshot())
            self.assertEqual(2, len(runtime.events()))
            altered = {**request, "text": "A different receipt"}
            self.assert_code("IDEMPOTENCY_CONFLICT", lambda: runtime.apply(altered, "result", expected_revision=0))
            self.assert_code("STALE_REVISION", lambda: runtime.apply({"kind": "cycle"}, "new", expected_revision=1))
            self.assertEqual(state, runtime.snapshot())

    def test_before_and_after_commit_have_atomic_retry_boundaries(self):
        with LifeRuntime.create(self.root / "faults") as runtime:
            before = runtime.snapshot()
            request = {"kind": "cycle"}
            self.assert_code("INJECTED_FAILURE", lambda: runtime.apply(request, "same", 0, "before_commit"))
            self.assertEqual(before, runtime.snapshot())
            self.assertEqual([], runtime.events())
            self.assert_code("INJECTED_FAILURE", lambda: runtime.apply(request, "same", 0, "after_commit"))
            committed = runtime.snapshot()
            self.assertEqual(1, committed["revision"])
            self.assertEqual(runtime.events()[0], runtime.apply(request, "same", 0))
            self.assertEqual(committed, runtime.snapshot())
            self.assertTrue(runtime.verify()["valid"])

    def test_process_exit_before_commit_leaves_no_partial_learning(self):
        path = self.root / "crash"
        with LifeRuntime.create(path) as runtime:
            choice = runtime.apply({"kind": "choose", "candidates": candidates()}, "choice")
            request = feedback(choice["result"]["decision"]["id"], status="failed", harm=1)
            before = runtime.snapshot()
        script = """
import json, os, sys
import project_consciousness.identity_runtime as m
def die(stage, requested):
    if stage == requested:
        os._exit(23)
m._inject_fault = die
with m.LifeRuntime.open(sys.argv[1]) as life:
    life.apply(json.loads(sys.argv[2]), 'feedback', fail_at='before_commit')
"""
        result = subprocess.run([sys.executable, "-c", script, str(path), canonical(request)], capture_output=True)
        self.assertEqual(23, result.returncode, result.stderr.decode())
        with LifeRuntime.open(path) as runtime:
            self.assertEqual(before, runtime.snapshot())
            self.assertEqual(1, len(runtime.events()))
            runtime.apply(request, "feedback")
            self.assertTrue(runtime.verify()["valid"])

    def test_two_writers_use_latest_state_and_share_idempotency(self):
        path = self.root / "two-writers"
        with LifeRuntime.create(path, budget=10):
            pass

        def apply_from_connection(request_id):
            with LifeRuntime.open(path) as runtime:
                return runtime.apply({"kind": "cycle"}, request_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply_from_connection, ["same", "same"]))
            different = list(pool.map(apply_from_connection, ["second", "third"]))
        self.assertEqual(results[0], results[1])
        self.assertEqual({2, 3}, {event["revision"] for event in different})
        with LifeRuntime.open(path) as first, LifeRuntime.open(path) as second:
            first.apply({"kind": "cycle"}, "fourth")
            second.apply({"kind": "cycle"}, "fifth")
            first.apply({"kind": "cycle"}, "sixth")
            self.assertEqual(6, first.snapshot()["cycles"])
            self.assertEqual(4, first.snapshot()["budget_remaining"])
            self.assertTrue(first.verify()["valid"])

    def test_export_bundle_is_one_consistent_boundary_during_writer_commit(self):
        path = self.root / "concurrent-export"
        ready_to_commit = threading.Event()
        with LifeRuntime.create(path) as runtime, ThreadPoolExecutor(max_workers=1) as pool:
            runtime.run(1)
            original_snapshot = runtime._snapshot
            futures = []

            def write_concurrently():
                with LifeRuntime.open(path) as writer:
                    return writer.apply({"kind": "cycle"}, "concurrent-write")

            def before_commit(stage, requested):
                if stage == "before_commit":
                    ready_to_commit.set()

            def snapshot_during_write():
                futures.append(pool.submit(write_concurrently))
                self.assertTrue(ready_to_commit.wait(8), "writer did not reach commit")
                return original_snapshot()

            with patch("project_consciousness.identity_runtime._inject_fault", side_effect=before_commit):
                with patch.object(runtime, "_snapshot", side_effect=snapshot_during_write):
                    bundle = runtime.export_bundle()
                committed = futures[0].result(timeout=10)
            self.assertEqual(2, committed["revision"])
            self.assertEqual(1, bundle["state"]["revision"])
            self.assertEqual(1, len(bundle["events"]))
            self.assertEqual(1, bundle["verification"]["events"])
            self.assertEqual(digest(bundle["state"]), bundle["events"][-1]["after_hash"])
            self.assertTrue(bundle["verification"]["valid"])
            self.assertEqual(2, runtime.snapshot()["revision"])

    def test_branch_controls_preserve_parent_and_all_other_state(self):
        with LifeRuntime.create(self.root / "parent") as parent:
            add_library(parent)
            parent.run(3)
            before = parent.snapshot()
            before_events = parent.events()
            controls = {"learning_enabled": False, "preferences_visible": False,
                        "aversion_visible": False, "dream_enabled": False}
            with parent.fork(self.root / "child", controls) as child:
                expected = clone(before)
                expected["controls"].update(controls)
                self.assertEqual(expected, child.snapshot())
                self.assertEqual([], child.events())
                self.assertEqual(digest(before), child.manifest["parent"]["state_hash"])
                choice = child.apply({"kind": "choose", "candidates": candidates()}, "choose")
                child.apply(feedback(choice["result"]["decision"]["id"], status="failed", value=-1, harm=1), "result")
                after = child.snapshot()
                for key in ("priorities", "aversions", "competence"):
                    self.assertEqual(before[key], after[key])
                self.assertGreater(len(after["memories"]), len(before["memories"]))
                self.assertTrue(child.verify()["valid"])
            self.assertEqual(before, parent.snapshot())
            self.assertEqual(before_events, parent.events())
            for index, invalid in enumerate(({"priorities": {}}, {"paused": 1}, {"budget_remaining": 1000}, [])):
                output = self.root / f"invalid-{index}"
                self.assert_code("INVALID_INPUT", lambda: parent.fork(output, invalid))
                self.assertFalse(output.exists())

    def test_run_honors_pending_pause_and_budget_across_restart(self):
        path = self.root / "limits"
        with LifeRuntime.create(path, budget=3) as runtime:
            event = runtime.apply({"kind": "choose", "candidates": candidates()}, "choice")
            self.assertEqual([], runtime.run(3))
            request = feedback(event["result"]["decision"]["id"], status="unknown")
            runtime.apply(request, "unknown")
            self.assertIsNotNone(runtime.snapshot()["pending"])
            runtime.apply({"kind": "control", "changes": {"paused": True}}, "pause")
            runtime.apply(feedback(event["result"]["decision"]["id"]), "known")
        with LifeRuntime.open(path) as runtime:
            self.assertTrue(runtime.snapshot()["controls"]["paused"])
            self.assertEqual([], runtime.run(5))
            runtime.apply({"kind": "control", "changes": {"paused": False}}, "unpause")
            self.assertEqual(2, len(runtime.run(10)))
            self.assertEqual(0, runtime.snapshot()["budget_remaining"])
            self.assertEqual([], runtime.run(1))
            self.assertTrue(runtime.verify()["valid"])

    def test_source_package_and_runtime_guards_allow_reconstruction_only(self):
        with LifeRuntime.create(self.root / "guard") as runtime:
            runtime.run(1)
            for target, value, error_code in (
                    ("project_consciousness.identity_runtime.source_fingerprint", "0" * 64, "SOURCE_MISMATCH"),
                    ("project_consciousness.identity_runtime.__version__", "different", "SOURCE_MISMATCH"),
                    ("project_consciousness.identity_runtime.platform.python_version", "0.0.0", "RUNTIME_MISMATCH")):
                kwargs = {"return_value": value} if target.endswith(("source_fingerprint", "python_version")) else {"new": value}
                with patch(target, **kwargs):
                    self.assertTrue(runtime.verify("reconstruct")["valid"])
                    self.assertFalse(runtime.verify("recompute")["valid"])
                    self.assert_code(error_code, lambda: runtime.apply({"kind": "cycle"}, "different"))
                    self.assert_code(error_code, lambda: runtime.fork(self.root / "blocked-fork"))
                    self.assertEqual(1, runtime.snapshot()["revision"])

    def test_tampering_events_origin_head_manifest_and_shapes_is_detected(self):
        mutations = {
            "event": "UPDATE events SET request_json='{}' WHERE revision=1",
            "shape": "UPDATE events SET result_json='[]' WHERE revision=1",
            "chain": "UPDATE events SET previous_hash='broken' WHERE revision=2",
            "blob": "UPDATE events SET state_blob=x'00' WHERE revision=1",
            "origin": "UPDATE origin SET state_hash='changed' WHERE id=1",
            "head": "UPDATE metadata SET value='9000' WHERE key='head_revision'",
            "manifest": "UPDATE metadata SET value='[]' WHERE key='manifest'",
            "deleted": "DELETE FROM events WHERE revision=1",
        }
        for name, statement in mutations.items():
            with self.subTest(name=name):
                path = self.root / name
                with LifeRuntime.create(path) as runtime:
                    runtime.run(2)
                    db = sqlite3.connect(path / "identity.sqlite")
                    try:
                        db.execute(statement)
                        db.commit()
                    finally:
                        db.close()
                    verification = runtime.verify("reconstruct")
                    self.assertFalse(verification["valid"], verification)
                    self.assertTrue(verification["errors"])
                    self.assert_code("STATE_INCONSISTENT", lambda: runtime.apply({"kind": "cycle"}, "reject"))

    def test_manifest_file_mismatch_blocks_mutation(self):
        path = self.root / "manifest-file"
        with LifeRuntime.create(path) as runtime:
            altered = clone(runtime.manifest)
            altered["seed"] += 1
            (path / "manifest.json").write_text(canonical(altered), encoding="utf-8")
            self.assertFalse(runtime.verify("reconstruct")["valid"])
            self.assert_code("STATE_INCONSISTENT", lambda: runtime.apply({"kind": "cycle"}, "rejected"))

    def test_recompute_checks_origin_initialization_beyond_hashes(self):
        path = self.root / "forged-origin"
        with LifeRuntime.create(path) as runtime:
            altered = runtime.snapshot()
            altered["traits"]["curiosity"] = 0.12345678
            manifest = clone(runtime.manifest)
            manifest["initial_hash"] = digest(altered)
        db = sqlite3.connect(path / "identity.sqlite")
        try:
            db.execute("UPDATE origin SET state_blob=?,state_hash=?", (zlib.compress(canonical(altered).encode()), digest(altered)))
            db.executemany("UPDATE metadata SET value=? WHERE key=?", [
                (canonical(manifest), "manifest"), (digest(manifest), "manifest_hash"),
                (digest(altered), "head_hash"),
                (digest({"manifest_hash": digest(manifest), "origin_hash": digest(altered)}), "head_event_hash"),
            ])
            db.commit()
        finally:
            db.close()
        (path / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        with LifeRuntime.open(path) as runtime:
            self.assertTrue(runtime.verify("reconstruct")["valid"])
            result = runtime.verify("recompute")
            self.assertFalse(result["valid"])
            self.assertIn("initialization diverged", result["errors"][0])

    def test_invalid_requests_and_limits_leave_state_and_output_unchanged(self):
        with LifeRuntime.create(self.root / "validation") as runtime:
            before = runtime.snapshot()
            for invalid in ([], {"kind": "invalid"}, {"kind": "cycle", "extra": 1}, {"kind": "cycle", "bad": float("nan")}):
                self.assert_code("INVALID_INPUT", lambda: runtime.apply(invalid, "invalid"))
            for key in ("", 1, "x" * 257):
                self.assert_code("INVALID_INPUT", lambda: runtime.apply({"kind": "cycle"}, key))
            for revision in (-1, True, 1.5):
                self.assert_code("INVALID_INPUT", lambda: runtime.apply({"kind": "cycle"}, "key", revision))
            self.assert_code("INVALID_INPUT", lambda: runtime.apply({"kind": "cycle"}, "key", fail_at="during"))
            for count in (-1, True, 10001, 1.1):
                self.assert_code("INVALID_INPUT", lambda: runtime.run(count))
            self.assertEqual([], runtime.run(0))
            self.assert_code("INVALID_INPUT", lambda: runtime.verify("unknown"))
            self.assertEqual(before, runtime.snapshot())
            self.assertEqual([], runtime.events())
        existing = self.root / "existing"
        existing.mkdir()
        sentinel = existing / "run.sqlite"
        sentinel.write_bytes(b"legacy archive")
        self.assert_code("OUTPUT_EXISTS", lambda: LifeRuntime.create(existing))
        self.assertEqual(b"legacy archive", sentinel.read_bytes())
        missing = self.root / "missing"
        self.assert_code("NOT_FOUND", lambda: LifeRuntime.open(missing))
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
