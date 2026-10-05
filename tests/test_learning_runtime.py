from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from project_consciousness.agent import advance_agent
from project_consciousness.contracts import Config, LabError, TaskConfig, digest
from project_consciousness.runtime import Runtime


class LearningRuntimeTests(unittest.TestCase):
    def test_restart_on_both_sides_of_reversal_preserves_all_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(policy_mode="learned", delay=1)
            task = TaskConfig(kind="reversal-v1", reversal_episode=15)
            with Runtime.create(root / "continuous", 17, config, task) as continuous:
                expected = continuous.run(120)
                state = continuous.snapshot()
            previous = 0
            for checkpoint in (2, 44, 46, 80, 120):
                run = Runtime.create(root / "resumed", 17, config, task) if previous == 0 else Runtime.open(root / "resumed")
                with run:
                    run.run(checkpoint - previous)
                previous = checkpoint
            with Runtime.open(root / "resumed") as resumed:
                self.assertEqual(resumed.snapshot(), state)
                self.assertEqual(resumed.traces(), expected)
                self.assertTrue(resumed.verify("recompute")["valid"])
                self.assertEqual(state["agent"]["learner"]["updates"], 40)

    def test_frozen_writer_preserves_model_but_allows_memory_and_same_first_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Runtime.create(root / "parent", 17, Config(policy_mode="learned"),
                                TaskConfig(kind="reversal-v1", reversal_episode=10)) as parent:
                parent.run(50)
                origin = parent.snapshot()
                with parent.fork(root / "adaptive") as adaptive, parent.fork(root / "frozen", overrides={"learning_enabled": False}) as frozen:
                    initial = frozen.snapshot()
                    self.assertEqual(initial["agent"], origin["agent"])
                    self.assertEqual(initial["environment"], origin["environment"])
                    self.assertEqual(initial["rng"], origin["rng"])
                    active_traces, frozen_traces = adaptive.run(50), frozen.run(50)
                    self.assertEqual(active_traces[4]["decision"], frozen_traces[4]["decision"])
                    self.assertEqual(frozen.snapshot()["agent"]["learner"], origin["agent"]["learner"])
                    self.assertNotEqual(frozen.snapshot()["agent"]["records"], origin["agent"]["records"])
                    self.assertNotEqual(adaptive.snapshot()["agent"]["learner"], origin["agent"]["learner"])
                    self.assertTrue(all(trace["post_model_hash"] == digest(origin["agent"]["learner"]) for trace in frozen_traces))
                    self.assertTrue(frozen.verify()["valid"])
                self.assertEqual(parent.snapshot(), origin)
                for override in ({"learning_rate": .5}, {"reversal_episode": 3}, {"policy_mode": "fixed"}):
                    with self.assertRaises(LabError):
                        parent.fork(root / "invalid", overrides=override)

    def test_learning_update_and_feedback_commit_atomically_and_retries_do_not_relearn(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run"
            with Runtime.create(path, 17, Config(policy_mode="learned"), TaskConfig(kind="reversal-v1")) as run:
                run.run(4)
                before = run.snapshot()
                with self.assertRaises(LabError):
                    run.step(expected_tick=4, fail_at="before_commit")
                self.assertEqual(run.snapshot(), before)
            with Runtime.open(path) as run:
                committed = run.step(expected_tick=4)
                self.assertEqual(run.snapshot()["agent"]["learner"]["updates"], 1)
                self.assertEqual(run.step(expected_tick=4), committed)
                run.run(4)
                with self.assertRaises(LabError):
                    run.step(expected_tick=9, fail_at="after_commit")
            with Runtime.open(path) as run:
                run.step(expected_tick=9)
                self.assertEqual(run.snapshot()["agent"]["learner"]["updates"], 2)
                self.assertTrue(run.verify()["valid"])

    def test_runtime_does_not_pass_private_rule_or_schedule_to_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("project_consciousness.runtime.advance_agent", wraps=advance_agent) as spy:
                with Runtime.create(Path(directory) / "run", 17, Config(policy_mode="learned"),
                                    TaskConfig(kind="reversal-v1", reversal_episode=2)) as run:
                    run.run(20)
            for call in spy.call_args_list:
                state, observation, tick, config, rng = call.args
                self.assertEqual(set(observation), {"episode", "phase", "value"})
                self.assertFalse({"target", "reversal_episode", "initial_mapping", "task"} & set(config.to_dict()))
                self.assertEqual(set(state), {"records", "learner"})


if __name__ == "__main__":
    unittest.main()
