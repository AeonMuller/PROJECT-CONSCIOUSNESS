import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from project_consciousness.__main__ import main
from project_consciousness.contracts import Config, LabError, TaskConfig, digest
from project_consciousness.runtime import Runtime


class CapabilityRuntimeTests(unittest.TestCase):
    def test_restart_before_and_after_degradation_preserves_full_state_and_traces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(policy_mode="capability", delay=1)
            task = TaskConfig(kind="capability-v1", capability_change_episode=20)
            with Runtime.create(root / "continuous", 17, config, task) as run:
                expected = run.run(180)
                final = run.snapshot()
            previous = 0
            for checkpoint in (2, 59, 61, 120, 180):
                current = Runtime.create(root / "resumed", 17, config, task) if previous == 0 else Runtime.open(root / "resumed")
                with current:
                    current.run(checkpoint - previous)
                previous = checkpoint
            with Runtime.open(root / "resumed") as run:
                self.assertEqual(run.snapshot(), final)
                self.assertEqual(run.traces(), expected)
                self.assertEqual(final["agent"]["capability"]["updates"], 60)
                self.assertTrue(run.verify()["valid"])

    def test_forks_freeze_model_or_block_consumer_without_mutating_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Runtime.create(root / "parent", 17, Config(policy_mode="capability", delay=1),
                                TaskConfig(kind="capability-v1", capability_change_episode=20)) as parent:
                parent.run(60)
                before = parent.snapshot()
                traces = {}
                for condition, overrides in (("updated", {}), ("frozen", {"capability_learning_enabled": False}),
                                              ("blocked", {"capability_read_mode": "blocked"})):
                    with parent.fork(root / condition, overrides=overrides) as branch:
                        initial = branch.snapshot()
                        for key in ("agent", "environment", "rng", "tick"):
                            self.assertEqual(initial[key], before[key])
                        traces[condition] = branch.run(30)
                        if condition == "frozen":
                            self.assertEqual(branch.snapshot()["agent"]["capability"], before["agent"]["capability"])
                            self.assertNotEqual(branch.snapshot()["agent"]["records"], before["agent"]["records"])
                            self.assertTrue(all(t["post_capability_hash"] == digest(before["agent"]["capability"]) for t in traces[condition]))
                        if condition == "blocked":
                            self.assertEqual(branch.snapshot()["agent"]["capability"]["updates"], 30)
                            self.assertTrue(all(t["decision"]["capability_view"] == [.5, .5] for t in traces[condition] if t["outcome"]["terminal"]))
                        self.assertTrue(branch.verify()["valid"])
                self.assertEqual(traces["updated"][2]["decision"], traces["frozen"][2]["decision"])
                self.assertEqual(parent.snapshot(), before)

    def test_capability_feedback_is_atomic_and_committed_retry_does_not_update_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run"
            with Runtime.create(path, 17, Config(policy_mode="capability", delay=1), TaskConfig(kind="capability-v1")) as run:
                run.run(2)
                before = run.snapshot()
                with self.assertRaises(LabError):
                    run.step(expected_tick=2, fail_at="before_commit")
                self.assertEqual(run.snapshot(), before)
                with self.assertRaises(LabError):
                    run.step(expected_tick=2, fail_at="after_commit")
            with Runtime.open(path) as run:
                result = run.step(expected_tick=2)
                self.assertEqual(result["post_capability_version"], 1)
                self.assertEqual(run.snapshot()["agent"]["capability"]["updates"], 1)
                self.assertTrue(run.verify()["valid"])

    def test_incompatible_tasks_and_illegal_interventions_fail_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for config, task in ((Config(policy_mode="capability"), TaskConfig()),
                                 (Config(), TaskConfig(kind="capability-v1"))):
                with self.assertRaises(LabError):
                    Runtime.create(root / "absent", 17, config, task)
                self.assertFalse((root / "absent").exists())
            with Runtime.create(root / "fixed") as run:
                for override in ({"capability_learning_enabled": False}, {"capability_read_mode": "blocked"}):
                    with self.assertRaises(LabError):
                        run.fork(root / "absent", overrides=override)
                    self.assertFalse((root / "absent").exists())
            with Runtime.create(root / "cap", 17, Config(policy_mode="capability"), TaskConfig(kind="capability-v1")) as run:
                for override in ({"fast_cost": .9}, {"capability_backend": "generic"}, {"capability_read_mode": "bad"}, {"learning_enabled": False}):
                    with self.assertRaises(LabError):
                        run.fork(root / "absent", overrides=override)
                    self.assertFalse((root / "absent").exists())


class CapabilityCLITests(unittest.TestCase):
    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(map(str, args)))
        return code, json.loads(output.getvalue() or error.getvalue())

    def test_run_resume_frozen_status_and_explicit_execution_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "run.toml"
            config.write_text('[agent]\npolicy_mode="capability"\ndelay=1\n[task]\nkind="capability-v1"\ncapability_change_episode=3\n', encoding="utf-8")
            freeze = root / "freeze.toml"
            freeze.write_text('capability_learning_enabled=false\n', encoding="utf-8")
            code, result = self.invoke("run", "--config", config, "--ticks", 9, "--out", root / "run")
            self.assertEqual(code, 0, result)
            self.assertIn("mean_utility", result)
            self.assertEqual(result["decision_accuracy"], 1)
            self.assertEqual(sum(result["tool_counts"].values()), 3)
            _, before = self.invoke("status", "--run", root / "run")
            code, result = self.invoke("fork", "--run", root / "run", "--condition", freeze, "--out", root / "frozen")
            self.assertEqual(code, 0, result)
            code, result = self.invoke("resume", "--run", root / "frozen", "--ticks", 9)
            self.assertEqual(code, 0, result)
            _, after = self.invoke("status", "--run", root / "frozen")
            self.assertEqual(before["capability"], after["capability"])
            code, result = self.invoke("replay", "--run", root / "frozen", "--verify")
            self.assertEqual(code, 0, result)

    def test_e2_cli_and_report_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "experiment.toml"
            config.write_text('[experiment]\nprotocol="E2"\nacquisition_episodes=3\nadaptation_episodes=4\nbootstrap_samples=10\nprobe_trials=5\n', encoding="utf-8")
            destination = root / "experiment"
            code, result = self.invoke("experiment", "--protocol", config, "--seeds", "900:902", "--out", destination)
            self.assertEqual(code, 0, result)
            self.assertEqual(result["status"], "completed")
            report = destination / "report.md"
            before = report.read_bytes()
            code, result = self.invoke("report", "--experiment", destination)
            self.assertEqual(code, 0, result)
            self.assertEqual(before, report.read_bytes())


if __name__ == "__main__":
    unittest.main()
