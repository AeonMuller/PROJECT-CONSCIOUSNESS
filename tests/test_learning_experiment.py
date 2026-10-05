"""L1 scientific bookkeeping, causal controls, failures and reporting."""

from dataclasses import replace
import csv
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from project_consciousness.contracts import Config, LabError, TaskConfig
from project_consciousness.learning_experiment import run_l1, write_learning_report
from project_consciousness.runtime import Runtime


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class LearningExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = Config(delay=1, policy_mode="learned")

    def run_small(self, name="l1", **kwargs):
        return run_l1(self.root / name, seeds=kwargs.pop("seeds", [200]),
                      acquisition_episodes=kwargs.pop("acquisition_episodes", 3),
                      adaptation_episodes=kwargs.pop("adaptation_episodes", 3),
                      bootstrap_samples=10, config=self.config, **kwargs)

    def test_paired_controls_model_brier_complete_exports_and_report_regeneration(self):
        state = random.getstate()
        result = self.run_small(seeds=[200, 201])
        self.assertEqual(random.getstate(), state)
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(result["valid"])
        self.assertEqual(result["runs_completed"], 12)
        self.assertEqual(result["runs_planned"], 12)
        self.assertEqual(result["episodes_completed"], 42)
        self.assertEqual(result["episodes_planned"], 42)
        self.assertEqual(result["episodes_valid"], 42)
        out = self.root / "l1"
        rows = read_rows(out / "metrics.csv")
        self.assertEqual(len(rows), 14)
        self.assertTrue(all(row["status"] == "ok" and row["verify_valid"] == "True" for row in rows))
        for row in rows:
            self.assertEqual(int(row["episodes_completed"]), 3)
            self.assertEqual(int(row["actions_consumed"]), 9)
            self.assertEqual(int(row["model_updates"]), 0 if row["condition"] in ("frozen", "untrained_frozen") else 3)
            if row["condition"] == "untrained_frozen":
                self.assertEqual(float(row["brier_mean"]), .25)
            if row["phase"] == "adaptation":
                self.assertEqual(row["recovery_episode"], "")
                self.assertEqual(row["recovery_censored"], "True")
        episodes = read_rows(out / "episodes.csv")
        self.assertEqual(len(episodes), 42)
        for episode in episodes:
            prediction = float(episode["predicted_target_left"])
            target = int(episode["target_left"])
            self.assertEqual(float(episode["brier"]), (prediction - target) ** 2)
        # Greedy action probabilities are not the learner's calibrated prediction.
        self.assertTrue(any(float(e["predicted_target_left"]) != float(e["probability_left"]) for e in episodes))
        comparisons = read_rows(out / "comparisons.csv")
        for row in comparisons:
            self.assertEqual(row["complete_pairs"], "2")
            if row["contrast"] in ("sham_control", "restart_control"):
                self.assertEqual(float(row["difference_condition_minus_baseline"]), 0)
                self.assertEqual(float(row["ci95_low"]), 0)
                self.assertEqual(float(row["ci95_high"]), 0)
        checks = read_rows(out / "checks.csv")
        self.assertEqual(result["checks_passed"], len(checks))
        self.assertTrue(all(row["status"] == "ok" for row in checks))
        report = out / "report.md"
        original = report.read_bytes()
        report.unlink()
        write_learning_report(out)
        self.assertEqual(original, report.read_bytes())

    def test_snapshot_frozen_state_and_restart_identity(self):
        self.run_small()
        out = self.root / "l1" / "runs"
        with Runtime.open(out / "training" / "seed-200") as training:
            trained = training.snapshot()
        for condition in ("adaptive", "frozen", "sham", "resumed"):
            with Runtime.open(out / condition / "seed-200") as runtime:
                initial = runtime.snapshot(9)
                self.assertEqual(initial["agent"], trained["agent"])
                self.assertEqual(initial["environment"], trained["environment"])
                self.assertEqual(initial["rng"], trained["rng"])
                if condition == "frozen":
                    self.assertEqual(initial["agent"]["learner"], runtime.snapshot()["agent"]["learner"])
        with Runtime.open(out / "adaptive" / "seed-200") as adaptive, Runtime.open(out / "resumed" / "seed-200") as resumed:
            self.assertEqual(adaptive.traces(), resumed.traces())

    def test_failed_branch_retained_in_denominators_and_excluded_from_pairs(self):
        original_fork = Runtime.fork

        def failing_fork(runtime, path, tick=None, overrides=None):
            if Path(path).parent.name == "frozen":
                raise LabError("TEST_FAILURE", "deliberate frozen failure")
            return original_fork(runtime, path, tick, overrides)

        with patch("project_consciousness.learning_experiment.Runtime.fork", new=failing_fork):
            result = self.run_small("failed")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["runs_planned"], 6)
        self.assertEqual(result["runs_completed"], 5)
        self.assertEqual(result["episodes_planned"], 21)
        self.assertEqual(result["episodes_completed"], 18)
        rows = read_rows(self.root / "failed" / "metrics.csv")
        frozen = next(row for row in rows if row["condition"] == "frozen")
        self.assertIn("TEST_FAILURE", frozen["error"])
        self.assertEqual(frozen["episodes_planned"], "3")
        primary = next(row for row in read_rows(self.root / "failed" / "comparisons.csv")
                       if row["contrast"] == "primary_adaptation" and row["metric"] == "success_rate")
        self.assertEqual(primary["complete_pairs"], "0")
        self.assertEqual(json.loads(primary["excluded_seeds"]), [200])
        self.assertEqual(primary["difference_condition_minus_baseline"], "")

    def test_failed_recompute_preserves_episodes_but_excludes_evidence(self):
        original_verify = Runtime.verify

        def fail_frozen(runtime, mode="recompute"):
            result = original_verify(runtime, mode)
            if mode == "recompute" and runtime.path.parent.name == "frozen":
                return {**result, "valid": False, "errors": ["deliberate verification failure"]}
            return result

        with patch("project_consciousness.learning_experiment.Runtime.verify", new=fail_frozen):
            result = self.run_small("invalid")
        self.assertEqual(result["episodes_completed"], 21)
        self.assertEqual(result["episodes_valid"], 18)
        rows = read_rows(self.root / "invalid" / "metrics.csv")
        frozen = next(row for row in rows if row["condition"] == "frozen")
        self.assertEqual(frozen["episodes_completed"], "3")
        self.assertEqual(frozen["verify_valid"], "False")
        self.assertEqual(frozen["status"], "failed")
        report = (self.root / "invalid" / "report.md").read_text(encoding="utf-8")
        self.assertIn("| frozen | adaptation | 0 / 1 | 0 / 3 | — | — | — | 0 |", report)
        # Even a stale success status cannot bypass the explicit integrity flag.
        frozen["status"] = "ok"
        with (self.root / "invalid" / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        write_learning_report(self.root / "invalid")
        self.assertIn("| frozen | adaptation | 0 / 1 | 0 / 3 | — | — | — | 0 |",
                      (self.root / "invalid" / "report.md").read_text(encoding="utf-8"))

    def test_partial_failure_keeps_confirmed_episode(self):
        original_step = Runtime.step

        def fail_frozen_after_choice(runtime, expected_tick=None, fail_at=None):
            if runtime.path.parent.name == "frozen" and runtime.snapshot()["tick"] == 12:
                raise LabError("TEST_PARTIAL", "failure after one confirmed episode")
            return original_step(runtime, expected_tick, fail_at)

        with patch("project_consciousness.learning_experiment.Runtime.step", new=fail_frozen_after_choice):
            result = self.run_small("partial")
        self.assertEqual(result["episodes_completed"], 19)
        row = next(row for row in read_rows(self.root / "partial" / "metrics.csv") if row["condition"] == "frozen")
        self.assertEqual(row["episodes_completed"], "1")
        self.assertEqual(row["actions_consumed"], "3")
        self.assertEqual(row["status"], "failed")

    def test_report_protects_data_and_existing_custom_documents(self):
        self.run_small()
        out = self.root / "l1"
        manifest = out / "manifest.json"
        original = manifest.read_bytes()
        with self.assertRaises(LabError):
            write_learning_report(out, manifest)
        self.assertEqual(manifest.read_bytes(), original)
        custom = self.root / "existing.md"
        custom.write_text("keep", encoding="utf-8")
        with self.assertRaises(LabError):
            write_learning_report(out, custom)
        self.assertEqual(custom.read_text(encoding="utf-8"), "keep")

    def test_protocol_validation_happens_before_creating_any_output(self):
        invalid = self.root / "invalid"
        for seeds in ([], [200, 200], [True], [-1], [2**63], "200"):
            with self.subTest(seeds=seeds), self.assertRaises(LabError):
                run_l1(invalid, seeds=seeds)
        for key in ("acquisition_episodes", "adaptation_episodes", "bootstrap_samples"):
            for value in (0, True, 1.5):
                with self.subTest(key=key, value=value), self.assertRaises(LabError):
                    run_l1(invalid, **{key: value})
        for config in (Config(), replace(self.config, learning_enabled=False),
                       replace(self.config, read_mode="block_all"), replace(self.config, write_enabled=False)):
            with self.assertRaises(LabError):
                run_l1(invalid, config=config)
        with self.assertRaises(LabError):
            run_l1(invalid, acquisition_episodes=3, task=TaskConfig(kind="reversal-v1", reversal_episode=4))
        self.assertFalse(invalid.exists())
        invalid.mkdir()
        marker = invalid / "marker"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(LabError):
            run_l1(invalid)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
