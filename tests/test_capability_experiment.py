"""E2 provenance, paired controls, common probes and failure-aware reporting."""

from dataclasses import replace
import csv
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from project_consciousness.capability import model_estimates
from project_consciousness.capability_experiment import _probe, run_e2, write_capability_report
from project_consciousness.contracts import Config, LabError, TaskConfig, clone, seeded_rng
from project_consciousness.runtime import Runtime


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class CapabilityExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = Config(delay=1, policy_mode="capability")

    def run_small(self, name="e2", **kwargs):
        return run_e2(self.root / name, seeds=kwargs.pop("seeds", [300]),
                      acquisition_episodes=kwargs.pop("acquisition_episodes", 3),
                      adaptation_episodes=kwargs.pop("adaptation_episodes", 3),
                      bootstrap_samples=10, probe_trials=5,
                      config=kwargs.pop("config", self.config), **kwargs)

    def test_complete_exports_controls_forecasts_and_reproducible_report(self):
        before = random.getstate()
        result = self.run_small(seeds=[300, 301])
        self.assertEqual(random.getstate(), before)
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(result["valid"])
        self.assertEqual(result["runs_completed"], 14)
        self.assertEqual(result["runs_planned"], 14)
        self.assertEqual(result["episodes_completed"], 48)
        self.assertEqual(result["episodes_planned"], 48)
        self.assertEqual(result["episodes_valid"], 48)
        self.assertEqual(result["probe_groups_planned"], 16)
        self.assertEqual(result["probe_trials_planned"], 160)
        self.assertEqual(result["probe_trials_completed"], 160)
        self.assertEqual(result["probe_trials_valid"], 160)
        out = self.root / "e2"
        metrics = read_rows(out / "metrics.csv")
        self.assertEqual(len(metrics), 16)
        for row in metrics:
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["verify_valid"], "True")
            self.assertEqual(row["episodes_completed"], "3")
            self.assertEqual(row["actions_consumed"], "9")
            self.assertEqual(row["model_updates"], "0" if row["condition"] == "frozen" else "3")
            self.assertEqual(row["probe_trials_planned"], "10")
            self.assertEqual(row["probe_trials_completed"], "10")
            self.assertEqual(row["decision_errors"], "0")
        episodes = read_rows(out / "episodes.csv")
        self.assertEqual(len(episodes), 48)
        for episode in episodes:
            prediction = float(episode["predicted_execution_success"])
            execution = int(episode["execution_success"])
            self.assertEqual(float(episode["execution_brier"]), (prediction - execution) ** 2)
            self.assertEqual(int(episode["success"]), int(episode["decision_correct"]) * execution)
            self.assertEqual(float(episode["utility"]), int(episode["success"]) - float(episode["cost"]))
            if episode["condition"] == "reader_blocked":
                self.assertEqual(float(episode["visible_fast"]), .5)
                self.assertEqual(float(episode["visible_safe"]), .5)
                self.assertEqual(prediction, .5)
        comparisons = read_rows(out / "comparisons.csv")
        for row in comparisons:
            self.assertEqual(row["complete_pairs"], "2")
            self.assertEqual(row["statistical_seed"], "20261005")
            if row["contrast"] in ("sham_control", "restart_control", "generic_control", "generic_acquisition") and row["metric"] != "agent_bytes_peak":
                self.assertEqual(float(row["difference_condition_minus_baseline"]), 0)
                self.assertEqual(float(row["ci95_low"]), 0)
                self.assertEqual(float(row["ci95_high"]), 0)
        checks = read_rows(out / "checks.csv")
        self.assertEqual(result["checks_passed"], len(checks))
        self.assertTrue(all(row["status"] == "ok" for row in checks))
        calibration = read_rows(out / "calibration.csv")
        self.assertEqual(sum(int(row["trials_valid"]) for row in calibration), 160)
        report = out / "report.md"
        original = report.read_bytes()
        report.unlink()
        write_capability_report(out)
        self.assertEqual(original, report.read_bytes())

    def test_probe_outcomes_are_common_forecasts_are_stored_and_snapshot_is_unchanged(self):
        self.run_small()
        out = self.root / "e2"
        rows = read_rows(out / "probes.csv")
        observed = {}
        for row in rows:
            key = (row["seed"], row["phase"], row["tool"], row["trial"])
            if key in observed:
                self.assertEqual(observed[key], row["execution_success"])
            observed[key] = row["execution_success"]
            self.assertEqual(float(row["brier"]),
                             (float(row["predicted_execution_success"]) - int(row["execution_success"])) ** 2)
        with Runtime.open(out / "runs" / "training" / "seed-300") as runtime:
            snapshot = runtime.snapshot()
            before = clone(snapshot)
            task = TaskConfig(kind="capability-v1", capability_change_episode=3)
            raw, measured, unchanged = _probe(300, "training", "acquisition", snapshot, 5, task)
            self.assertTrue(unchanged)
            self.assertEqual(snapshot, before)
            self.assertEqual(runtime.snapshot(), before)
            self.assertEqual([r["predicted_execution_success"] for r in measured],
                             model_estimates(snapshot["agent"]["capability"]))
            rng = seeded_rng(300, "e2-probe-acquisition")
            expected = [int(rng.random() < p) for p in (task.fast_success_before, task.safe_success) for _ in range(5)]
            self.assertEqual([r["execution_success"] for r in raw], expected)
            # The snapshot prepares a degraded episode; acquisition probes use the prior regime.
            self.assertEqual(snapshot["environment"]["episode"], 3)
            self.assertEqual(raw[0]["evaluation_probability"], task.fast_success_before)
        with Runtime.open(out / "runs" / "reader_blocked" / "seed-300") as runtime:
            stored = model_estimates(runtime.snapshot()["agent"]["capability"])
            measured = [r for r in read_rows(out / "probe_metrics.csv") if r["condition"] == "reader_blocked"]
            self.assertEqual([float(r["predicted_execution_success"]) for r in measured], stored)

    def test_frozen_model_and_restart_identity_from_same_training_state(self):
        self.run_small()
        runs = self.root / "e2" / "runs"
        with Runtime.open(runs / "training" / "seed-300") as runtime:
            training = runtime.snapshot()
        for condition in ("updated", "frozen", "reader_blocked", "sham", "resumed"):
            with Runtime.open(runs / condition / "seed-300") as runtime:
                initial = runtime.snapshot(9)
                for key in ("tick", "agent", "environment", "rng"):
                    self.assertEqual(initial[key], training[key])
                if condition == "frozen":
                    self.assertEqual(runtime.snapshot()["agent"]["capability"], training["agent"]["capability"])
                if condition == "reader_blocked":
                    self.assertEqual(runtime.snapshot()["agent"]["capability"]["updates"], 6)
        with Runtime.open(runs / "updated" / "seed-300") as updated, Runtime.open(runs / "resumed" / "seed-300") as resumed:
            self.assertEqual(updated.traces(), resumed.traces())

    def test_null_effect_is_valid_and_single_seed_has_no_interval(self):
        result = self.run_small(config=replace(self.config, capability_exploration=1.0))
        self.assertTrue(result["valid"], result)
        primary = next(r for r in read_rows(self.root / "e2" / "comparisons.csv")
                       if r["contrast"] == "primary_adaptation" and r["metric"] == "utility_mean")
        self.assertEqual(float(primary["difference_condition_minus_baseline"]), 0)
        self.assertEqual(primary["status"], "descriptive_single_seed")
        self.assertEqual(primary["ci95_low"], "")
        self.assertEqual(primary["ci95_high"], "")
        self.assertEqual(primary["bootstrap_samples"], "0")

    def test_failed_branch_keeps_planned_denominators_and_excludes_pair(self):
        original = Runtime.fork

        def fail_frozen(runtime, path, tick=None, overrides=None):
            if Path(path).parent.name == "frozen":
                raise LabError("TEST_FAILURE", "deliberate frozen failure")
            return original(runtime, path, tick, overrides)

        with patch("project_consciousness.capability_experiment.Runtime.fork", new=fail_frozen):
            result = self.run_small("failed")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["runs_planned"], 7)
        self.assertEqual(result["runs_completed"], 6)
        self.assertEqual(result["episodes_planned"], 24)
        self.assertEqual(result["episodes_completed"], 21)
        self.assertEqual(result["probe_trials_planned"], 80)
        self.assertEqual(result["probe_trials_completed"], 70)
        out = self.root / "failed"
        frozen = next(r for r in read_rows(out / "metrics.csv") if r["condition"] == "frozen")
        self.assertIn("TEST_FAILURE", frozen["error"])
        self.assertEqual(frozen["episodes_planned"], "3")
        self.assertEqual(frozen["probe_trials_planned"], "10")
        primary = next(r for r in read_rows(out / "comparisons.csv")
                       if r["contrast"] == "primary_adaptation" and r["metric"] == "utility_mean")
        self.assertEqual(primary["complete_pairs"], "0")
        self.assertEqual(json.loads(primary["excluded_seeds"]), [300])
        self.assertEqual(primary["difference_condition_minus_baseline"], "")

    def test_invalid_recompute_keeps_raw_evidence_but_excludes_all_estimands(self):
        original = Runtime.verify

        def fail_frozen(runtime, mode="recompute"):
            result = original(runtime, mode)
            if mode == "recompute" and runtime.path.parent.name == "frozen":
                return {**result, "valid": False, "errors": ["test invalid replay"]}
            return result

        with patch("project_consciousness.capability_experiment.Runtime.verify", new=fail_frozen):
            result = self.run_small("invalid")
        self.assertEqual(result["episodes_completed"], 24)
        self.assertEqual(result["episodes_valid"], 21)
        self.assertEqual(result["probe_trials_completed"], 80)
        self.assertEqual(result["probe_trials_valid"], 70)
        out = self.root / "invalid"
        frozen = next(r for r in read_rows(out / "metrics.csv") if r["condition"] == "frozen")
        self.assertEqual(frozen["verify_valid"], "False")
        self.assertEqual(frozen["status"], "failed")
        expected = "| frozen | adaptation | 0 / 1 | 0 / 3 | — | — | — | — | — |"
        self.assertIn(expected, (out / "report.md").read_text(encoding="utf-8"))
        self.assertEqual(sum(int(r["trials_valid"]) for r in read_rows(out / "calibration.csv") if r["condition"] == "frozen"), 0)
        # A stale success flag cannot bypass the independent integrity field.
        rows = read_rows(out / "metrics.csv")
        for row in rows:
            if row["condition"] == "frozen":
                row["status"] = "ok"
        with (out / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        write_capability_report(out)
        self.assertIn(expected, (out / "report.md").read_text(encoding="utf-8"))

    def test_partial_failure_retains_committed_episode_and_planned_horizon(self):
        original = Runtime.step

        def fail_after_choice(runtime, expected_tick=None, fail_at=None):
            if runtime.path.parent.name == "frozen" and runtime.snapshot()["tick"] == 12:
                raise LabError("TEST_PARTIAL", "failure after one committed episode")
            return original(runtime, expected_tick, fail_at)

        with patch("project_consciousness.capability_experiment.Runtime.step", new=fail_after_choice):
            result = self.run_small("partial")
        self.assertEqual(result["episodes_completed"], 22)
        self.assertEqual(result["episodes_valid"], 21)
        row = next(r for r in read_rows(self.root / "partial" / "metrics.csv") if r["condition"] == "frozen")
        self.assertEqual(row["episodes_completed"], "1")
        self.assertEqual(row["episodes_planned"], "3")
        self.assertEqual(row["actions_consumed"], "3")
        self.assertEqual(row["status"], "failed")

    def test_intermediate_snapshot_failure_preserves_generic_data_and_probe_denominators(self):
        original = Runtime.snapshot

        def fail_intermediate(runtime, tick=None):
            if runtime.path.parent.name == "generic" and tick == 9 and original(runtime)["tick"] == 18:
                raise LabError("TEST_SNAPSHOT", "intermediate snapshot unavailable")
            return original(runtime, tick)

        with patch("project_consciousness.capability_experiment.Runtime.snapshot", new=fail_intermediate):
            result = self.run_small("snapshot-failure")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["runs_completed"], 6)
        self.assertEqual(result["episodes_completed"], 24)
        self.assertEqual(result["episodes_valid"], 18)
        self.assertEqual(result["probe_trials_completed"], 70)
        self.assertEqual(result["probe_trials_planned"], 80)
        self.assertEqual(result["probe_trials_valid"], 60)
        rows = read_rows(self.root / "snapshot-failure" / "metrics.csv")
        generic = [r for r in rows if r["condition"] == "generic"]
        self.assertEqual(len(generic), 2)
        self.assertTrue(all("TEST_SNAPSHOT" in r["error"] for r in generic))

    def test_report_protects_evidence_and_existing_custom_document(self):
        self.run_small()
        out = self.root / "e2"
        manifest = out / "manifest.json"
        original = manifest.read_bytes()
        with self.assertRaises(LabError):
            write_capability_report(out, manifest)
        self.assertEqual(manifest.read_bytes(), original)
        custom = self.root / "existing.md"
        custom.write_text("preserve", encoding="utf-8")
        with self.assertRaises(LabError):
            write_capability_report(out, custom)
        self.assertEqual(custom.read_text(encoding="utf-8"), "preserve")

    def test_protocol_validation_precedes_output_creation(self):
        invalid = self.root / "invalid"
        for seeds in ([], [300, 300], [True], [-1], [2**63], "300"):
            with self.subTest(seeds=seeds), self.assertRaises(LabError):
                run_e2(invalid, seeds=seeds)
        for key in ("acquisition_episodes", "adaptation_episodes", "bootstrap_samples", "probe_trials"):
            for value in (0, True, 1.5):
                with self.subTest(key=key, value=value), self.assertRaises(LabError):
                    run_e2(invalid, **{key: value})
        for config in (Config(), replace(self.config, capability_learning_enabled=False),
                       replace(self.config, capability_read_mode="blocked"), replace(self.config, capability_backend="generic"),
                       replace(self.config, read_mode="block_all"), replace(self.config, write_enabled=False)):
            with self.assertRaises(LabError):
                run_e2(invalid, config=config)
        with self.assertRaises(LabError):
            run_e2(invalid, acquisition_episodes=3, task=TaskConfig(kind="capability-v1", capability_change_episode=4))
        self.assertFalse(invalid.exists())
        invalid.mkdir()
        marker = invalid / "marker"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(LabError):
            run_e2(invalid)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
