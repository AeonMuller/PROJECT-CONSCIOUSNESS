import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from project_consciousness.contracts import Config, LabError
from project_consciousness.runtime import Runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_resume_matches_uninterrupted_and_recompute(self):
        with Runtime.create(self.root / "continuous", 17, Config()) as full:
            full.run(80)
            expected = full.traces()
        with Runtime.create(self.root / "split", 17, Config()) as split:
            split.run(4)
        with Runtime.open(self.root / "split") as split:
            split.run(76)
            self.assertEqual(expected, split.traces())
            self.assertTrue(split.verify("reconstruct")["valid"])
            self.assertTrue(split.verify("recompute")["valid"])

    def test_fault_before_commit_rolls_back_after_commit_is_idempotent(self):
        with Runtime.create(self.root / "faults", 4, Config()) as run:
            origin = run.snapshot()
            with self.assertRaises(LabError):
                run.step(expected_tick=0, fail_at="before_commit")
            self.assertEqual(origin, run.snapshot())
            self.assertEqual([], run.traces())
            with self.assertRaises(LabError):
                run.step(expected_tick=0, fail_at="after_commit")
            self.assertEqual(1, run.snapshot()["tick"])
            replay = run.step(expected_tick=0)
            self.assertEqual(replay, run.traces()[0])
            self.assertEqual(1, len(run.traces()))
            with self.assertRaises(LabError):
                run.step(expected_tick=3)

    def test_abrupt_process_exit_before_commit(self):
        path = self.root / "process-crash"
        with Runtime.create(path, 29, Config()) as run:
            before = run.snapshot()
        script = """
import os, sys
import project_consciousness.runtime as m
def die(stage, requested):
    if stage == requested:
        os._exit(23)
m._inject_fault = die
with m.Runtime.open(sys.argv[1]) as run:
    run.step(expected_tick=0, fail_at='before_commit')
"""
        result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True)
        self.assertEqual(23, result.returncode, result.stderr.decode())
        with Runtime.open(path) as run:
            self.assertEqual(before, run.snapshot())
            run.step(expected_tick=0)
            self.assertTrue(run.verify()["valid"])

    def test_fork_preserves_parent_and_masks_only_read(self):
        with Runtime.create(self.root / "parent", 17, Config()) as parent:
            parent.run(4)
            before = parent.snapshot()
            with parent.fork(self.root / "child", 4, {"read_mode": "block_all"}) as child:
                snapshot = child.snapshot()
                self.assertEqual(before["agent"], snapshot["agent"])
                self.assertEqual(before["environment"], snapshot["environment"])
                trace = child.step()
                self.assertEqual(0.5, trace["decision"]["probability_left"])
                self.assertTrue(child.verify()["valid"])
            self.assertEqual(before, parent.snapshot())
            self.assertEqual(1.0, parent.step()["decision"]["confidence"])

    def test_modified_trace_or_state_is_detected(self):
        path = self.root / "corrupt"
        with Runtime.create(path, 9, Config()) as run:
            run.run(7)
        with sqlite3.connect(path / "run.sqlite") as db:
            row = db.execute("SELECT trace_json FROM events WHERE tick=0").fetchone()
            trace = json.loads(row[0])
            trace["decision"]["action"] = "left"
            db.execute("UPDATE events SET trace_json=? WHERE tick=0", (json.dumps(trace),))
        db.close()
        with Runtime.open(path) as run:
            self.assertFalse(run.verify()["valid"])

    def test_refuse_overwrite_and_unknown_configuration(self):
        path = self.root / "existing"
        path.mkdir()
        sentinel = path / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        with self.assertRaises(LabError):
            Runtime.create(path, 0, Config())
        self.assertEqual("preserve", sentinel.read_text(encoding="utf-8"))
        with self.assertRaises(LabError):
            Config.from_dict({"surprise": 1})

    def test_manifest_provenance_tampering_is_detected(self):
        path = self.root / "manifest-corrupt"
        with Runtime.create(path, 17, Config()) as run:
            run.run(2)
        db = sqlite3.connect(path / "run.sqlite")
        try:
            manifest = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
            manifest["seed"] = 999
            db.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps(manifest),))
            db.commit()
        finally:
            db.close()
        with Runtime.open(path) as run:
            self.assertFalse(run.verify()["valid"])
            with self.assertRaises(LabError):
                run.step()

    def test_structural_json_corruption_returns_invalid_not_traceback(self):
        path = self.root / "shape-corrupt"
        with Runtime.create(path, 17, Config()) as run:
            run.run(2)
        db = sqlite3.connect(path / "run.sqlite")
        try:
            db.execute("UPDATE events SET trace_json='[]' WHERE tick=0")
            db.commit()
        finally:
            db.close()
        with Runtime.open(path) as run:
            result = run.verify()
            self.assertFalse(result["valid"])
            self.assertIn("trace JSON object", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
