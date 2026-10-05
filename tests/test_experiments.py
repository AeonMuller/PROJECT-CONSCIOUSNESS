"""Integration tests for causal contrasts, failures and reproducible reporting."""

import csv
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from project_consciousness.contracts import Config, LabError
from project_consciousness.__main__ import main
from project_consciousness.experiments import CONDITIONS, run_e0, run_e1, write_report
from project_consciousness.runtime import Runtime


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_e0_real_reopen_matches_continuous_and_report_regenerates(self):
        result = run_e0(self.root / "e0", ticks=12, config=Config(delay=1))
        self.assertTrue(result["valid"])
        self.assertEqual(result["runs_completed"], 2)
        self.assertGreater(len(result["checkpoints"]), 1)
        report = Path(result["report_path"])
        original = report.read_text(encoding="utf-8")
        report.unlink()
        regenerated = write_report(self.root / "e0")
        self.assertEqual(regenerated.read_text(encoding="utf-8"), original)
        with Runtime.open(self.root / "e0" / "runs" / "resumed") as runtime:
            self.assertEqual(runtime.snapshot()["tick"], 12)
            self.assertTrue(runtime.verify()["valid"])

    def test_e1_controls_brier_local_causality_and_paired_bootstrap(self):
        global_rng = random.getstate()
        out = self.root / "e1"
        result = run_e1(out, seeds=[100, 101], episodes=3, config=Config(delay=1), bootstrap_samples=30)
        self.assertEqual(random.getstate(), global_rng)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["runs_completed"], 16)
        self.assertEqual(result["branches_completed"], 10)
        rows = read_rows(out / "metrics.csv")
        self.assertEqual({row["condition"] for row in rows}, set(CONDITIONS))
        for row in rows:
            self.assertEqual(row["status"], "ok", row)
            self.assertEqual(int(row["actions_consumed"]), 9)
            self.assertEqual(int(row["episodes_completed"]), 3)
            self.assertEqual(int(row["records_capacity"]), 64)
            if row["condition"] in ("intact", "sham", "mask_irrelevant", "history"):
                self.assertEqual(float(row["success_rate"]), 1.0)
                self.assertEqual(float(row["brier_mean"]), 0.0)
            else:
                self.assertEqual(float(row["brier_mean"]), 0.25)
        causal = read_rows(out / "causal_contrasts.csv")
        for row in causal:
            self.assertEqual(row["same_pre_state"], "True")
            self.assertEqual(row["same_observation"], "True")
            expected = 0.5 if row["condition"] in ("block_read", "mask_relevant") else 0.0
            self.assertEqual(float(row["total_variation"]), expected)
        comparisons = read_rows(out / "comparisons.csv")
        history = next(row for row in comparisons if row["condition"] == "history" and row["metric"] == "success_rate")
        self.assertEqual(float(history["difference_condition_minus_baseline"]), 0.0)
        self.assertEqual(float(history["ci95_low"]), 0.0)
        self.assertEqual(float(history["ci95_high"]), 0.0)
        before = (out / "report.md").read_bytes()
        write_report(out)
        self.assertEqual((out / "report.md").read_bytes(), before)

    def test_failed_condition_remains_in_denominators_and_pair_exclusions(self):
        original_create = Runtime.create

        def failing_create(path, seed, config):
            if Path(path).parent.name == "block_read":
                raise LabError("TEST_FAILURE", "deliberate failed trajectory")
            return original_create(path, seed, config)

        out = self.root / "failed"
        with patch("project_consciousness.experiments.Runtime.create", side_effect=failing_create):
            result = run_e1(out, seeds=[100], episodes=1, config=Config(delay=1), bootstrap_samples=10)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["runs_planned"], 8)
        self.assertEqual(result["runs_completed"], 7)
        self.assertEqual(result["episodes_planned"], 8)
        self.assertEqual(result["episodes_completed"], 7)
        row = next(row for row in read_rows(out / "metrics.csv") if row["condition"] == "block_read")
        self.assertEqual(row["status"], "failed")
        self.assertIn("TEST_FAILURE", row["error"])
        self.assertEqual(int(row["episodes_planned"]), 1)
        self.assertEqual(int(row["episodes_completed"]), 0)
        comparison = next(row for row in read_rows(out / "comparisons.csv") if row["condition"] == "block_read")
        self.assertEqual(comparison["status"], "incomplete")
        self.assertEqual(int(comparison["complete_pairs"]), 0)
        self.assertEqual(json.loads(comparison["excluded_seeds"]), [100])
        self.assertEqual(comparison["ci95_low"], "")

    def test_failure_after_committed_work_preserves_partial_actions(self):
        original_open = Runtime.open
        failed_once = False

        def fail_first_reopen(path):
            nonlocal failed_once
            if Path(path).name == "resumed" and not failed_once:
                failed_once = True
                raise LabError("TEST_REOPEN", "deliberate reopen failure")
            return original_open(path)

        out = self.root / "partial"
        with patch("project_consciousness.experiments.Runtime.open", side_effect=fail_first_reopen):
            result = run_e0(out, ticks=6, config=Config(delay=1))
        self.assertFalse(result["valid"])
        row = next(row for row in read_rows(out / "metrics.csv") if row["condition"] == "resumed")
        self.assertEqual(row["status"], "failed")
        self.assertEqual(int(row["ticks_completed"]), 1)
        self.assertEqual(int(row["ticks_planned"]), 6)

    def test_failed_verification_retains_raw_success_but_excludes_functional_evidence(self):
        original_verify = Runtime.verify

        def fail_intact_recompute(runtime, mode="recompute"):
            result = original_verify(runtime, mode)
            if mode == "recompute" and runtime.path.parent.name == "intact":
                return {**result, "valid": False, "errors": ["deliberate verification failure"]}
            return result

        out = self.root / "invalid-evidence"
        with patch("project_consciousness.experiments.Runtime.verify", new=fail_intact_recompute):
            result = run_e1(out, seeds=[100], episodes=1, config=Config(delay=1), bootstrap_samples=10)
        self.assertEqual(result["status"], "incomplete")
        rows = read_rows(out / "metrics.csv")
        intact = next(row for row in rows if row["condition"] == "intact")
        self.assertEqual(intact["status"], "failed")
        self.assertEqual(intact["verify_valid"], "False")
        self.assertEqual(intact["successes"], "1")
        self.assertEqual(float(intact["brier_mean"]), 0.0)
        report = (out / "report.md").read_text(encoding="utf-8")
        self.assertIn("| intact | 0 / 1 | 0 / 1 | — | 0 | 0 |", report)
        self.assertIn("no constituyen evidencia funcional", report)
        # A stale success status must never override a failed verification flag.
        intact["status"] = "ok"
        with (out / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        write_report(out)
        self.assertIn("| intact | 0 / 1 | 0 / 1 | — | 0 | 0 |", (out / "report.md").read_text(encoding="utf-8"))

    def test_report_output_cannot_overwrite_data_or_existing_custom_document(self):
        out = self.root / "protected"
        run_e0(out, ticks=2, config=Config(delay=1))
        manifest = out / "manifest.json"
        original_manifest = manifest.read_bytes()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["report", "--experiment", str(out), "--out", str(manifest)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["error"]["code"], "INVALID_INPUT")
        self.assertEqual(manifest.read_bytes(), original_manifest)
        custom = self.root / "custom.md"
        custom.write_text("existing user document", encoding="utf-8")
        with self.assertRaises(LabError) as context:
            write_report(out, custom)
        self.assertEqual(context.exception.code, "OUTPUT_EXISTS")
        self.assertEqual(custom.read_text(encoding="utf-8"), "existing user document")
        alternative = self.root / "new-report.md"
        self.assertEqual(write_report(out, alternative), alternative)
        self.assertEqual(alternative.read_bytes(), (out / "report.md").read_bytes())
        write_report(out, out / "report.md")  # Explicit native destination remains regenerable.

    def test_invalid_inputs_and_existing_directory_are_not_overwritten(self):
        occupied = self.root / "occupied"
        occupied.mkdir()
        marker = occupied / "marker"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(LabError):
            run_e0(occupied, ticks=2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        invalid = self.root / "invalid"
        for seeds in ([], [100, 100], [True], [-1], [2**63]):
            with self.subTest(seeds=seeds), self.assertRaises(LabError):
                run_e1(invalid, seeds=seeds)
        with self.assertRaises(LabError):
            run_e1(invalid, config=Config(agent_mode="reactive"))
        with self.assertRaises(LabError):
            run_e1(invalid, episodes=0)
        self.assertFalse(invalid.exists())


if __name__ == "__main__":
    unittest.main()
