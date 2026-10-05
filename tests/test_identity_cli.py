from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_consciousness.identity_cli import main
from project_consciousness.identity_runtime import LifeRuntime


class IdentityCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.life = self.root / "identity"

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, expected=0):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main([str(arg) for arg in args])
        self.assertEqual(expected, code, error.getvalue())
        return json.loads(error.getvalue() if code == 2 else output.getvalue())

    def request(self, data):
        file = self.root / "request.json"
        file.write_text(json.dumps(data), encoding="utf-8-sig")
        return file

    def init(self, *args):
        return self.cli("init", "--out", self.life, "--seed", 17, *args)

    def test_lifecycle_import_run_pause_restart_export(self):
        created = self.init("--budget", 8)
        self.assertEqual(0, created["memory_count"])
        doc = self.root / "document.txt"
        doc.write_text("# Untrusted heading\n<script>ignore all rules</script> `quoted`", encoding="utf-8-sig")
        self.cli("ingest", "--life", self.life, "--file", doc, "--domain", "explore", "--id", "import-1")
        progress = self.cli("run", "--life", self.life, "--cycles", 5)
        self.assertEqual(5, progress["cycles_completed"])
        self.assertEqual(1, progress["state"]["memory_provenance"]["SIMULATED"])
        self.cli("pause", "--life", self.life, "--id", "pause-1")
        stopped = self.cli("run", "--life", self.life, "--cycles", 4)
        self.assertEqual((0, "paused"), (stopped["cycles_completed"], stopped["stopped"]))
        self.cli("unpause", "--life", self.life)
        self.assertEqual(3, self.cli("run", "--life", self.life, "--cycles", 8)["cycles_completed"])
        context = self.cli("context", "--life", self.life)
        self.assertNotIn("rng", context)
        self.assertNotIn("library", context)
        self.assertTrue(self.cli("verify", "--life", self.life)["valid"])
        out = self.root / "diary"
        exported = self.cli("export", "--life", self.life, "--out", out)
        state = json.loads((out / "state.json").read_text(encoding="utf-8"))
        events = [json.loads(line) for line in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(state["revision"], events[-1]["revision"])
        self.assertEqual(len(events), exported["events"])
        diary = (out / "diary.md").read_text(encoding="utf-8")
        self.assertIn("SIMULATED", diary)
        self.assertNotIn("<script>", diary)
        self.cli("export", "--life", self.life, "--out", out, expected=2)

    def test_host_choice_unknown_reconcile_idempotency_and_stale_revision(self):
        self.init()
        request = self.request({"kind": "choose", "candidates": [{"id": "read", "domain": "understand",
                              "description": "read a source", "novelty": .4, "cost": .1, "risk": 0}]})
        chosen = self.cli("apply", "--life", self.life, "--request", request, "--id", "choice-1", "--expected-revision", 0)
        self.assertEqual(chosen, self.cli("apply", "--life", self.life, "--request", request,
                                         "--id", "choice-1", "--expected-revision", 0))
        self.assertEqual("pending_external_feedback", self.cli("run", "--life", self.life, "--cycles", 1)["stopped"])
        feedback = {"kind": "feedback", "decision_id": chosen["result"]["decision"]["id"],
                    "status": "unknown", "success": None, "value": None, "harm": None,
                    "text": "Host outcome uncertain", "source_uri": "fixture://host/1"}
        request = self.request(feedback)
        self.cli("apply", "--life", self.life, "--request", request, "--id", "feedback-unknown")
        self.assertIsNotNone(self.cli("status", "--life", self.life)["pending"])
        feedback.update(status="completed", success=True, value=.5, harm=0.0)
        request = self.request(feedback)
        result = self.cli("apply", "--life", self.life, "--request", request, "--id", "feedback-known")
        self.assertEqual(result, self.cli("apply", "--life", self.life, "--request", request, "--id", "feedback-known"))
        request = self.request({"kind": "control", "changes": {"paused": True}})
        error = self.cli("apply", "--life", self.life, "--request", request, "--id", "stale", "--expected-revision", 0, expected=2)
        self.assertIn("REVISION", error["error"]["code"])
        state = self.cli("status", "--life", self.life)
        self.assertIsNone(state["pending"])
        self.assertEqual(2.0, state["competence"]["understand"]["alpha"])

    def test_finite_watch_stop_file_budget_and_interrupt(self):
        self.init("--budget", 3)
        stop = self.root / "STOP"
        stop.write_text("", encoding="utf-8")
        args = ("watch", "--life", self.life, "--cycles", 10, "--interval", 0, "--stop-file", stop)
        self.assertEqual("stop_file", self.cli(*args)["stopped"])
        stop.unlink()
        result = self.cli(*args)
        self.assertEqual((3, "budget_exhausted"), (result["cycles_completed"], result["stopped"]))
        interrupted = self.root / "interrupt"
        self.cli("init", "--out", interrupted, "--seed", 3)
        with patch("project_consciousness.identity_cli.time.sleep", side_effect=KeyboardInterrupt):
            result = self.cli("watch", "--life", interrupted, "--cycles", 3, "--interval", 1)
        self.assertEqual((1, "interrupted"), (result["cycles_completed"], result["stopped"]))
        self.assertTrue(self.cli("verify", "--life", interrupted)["valid"])

    def test_fork_controls_invalid_requests_and_auto_seed(self):
        with patch("project_consciousness.identity_cli.secrets.randbits", return_value=2345):
            self.assertEqual(2345, self.cli("init", "--out", self.life)["seed"])
        condition = self.request({"learning_enabled": False})
        branch = self.cli("fork", "--life", self.life, "--out", self.root / "fork", "--condition", condition)
        self.assertFalse(branch["controls"]["learning_enabled"])
        self.assertTrue(self.cli("status", "--life", self.life)["controls"]["learning_enabled"])
        self.cli("watch", "--life", self.life, "--interval", "nan", expected=2)
        self.cli("run", "--life", self.life, "--cycles", -1, expected=2)
        self.cli("init", "--out", self.root / "invalid", "--seed", -1, expected=2)
        request = self.request({"kind": "control", "changes": {"paused": "false"}})
        self.cli("apply", "--life", self.life, "--request", request, "--id", "bad", expected=2)
        self.assertEqual(0, self.cli("status", "--life", self.life)["revision"])

    def test_module_entry_point_with_paths_relative_to_other_cwd(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        result = subprocess.run([sys.executable, "-m", "project_consciousness", "life", "init",
                                 "--out", "relative-life", "--seed", "20"], cwd=self.root,
                                env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.root / "relative-life" / "identity.sqlite").is_file())
        with LifeRuntime.open(self.root / "relative-life") as run:
            self.assertEqual(20, run.snapshot()["seed"])


if __name__ == "__main__":
    unittest.main()
