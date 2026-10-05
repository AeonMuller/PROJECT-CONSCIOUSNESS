import random
import unittest

from project_consciousness.contracts import Config, LabError, TaskConfig
from project_consciousness.environment import initial_environment, observe, transition


class ReversalEnvironmentTests(unittest.TestCase):
    def test_opposite_rules_share_observations_and_reverse_on_exact_boundary(self):
        config = Config(delay=1)
        rngs = [random.Random(7), random.Random(7)]
        worlds = [initial_environment(config, rngs[mapping], TaskConfig(
            kind="reversal-v1", reversal_episode=3, initial_mapping=mapping)) for mapping in (0, 1)]
        for episode in range(7):
            cue = observe(worlds[0], config)["value"]
            for mapping, world in enumerate(worlds):
                self.assertEqual(world["target"], cue ^ mapping ^ int(episode >= 3))
            for _ in range(3):
                observations = [observe(world, config) for world in worlds]
                self.assertEqual(observations[0], observations[1])
                self.assertEqual(set(observations[0]), {"episode", "phase", "value"})
                action = "left" if observations[0]["phase"] == "choice" else "wait"
                outcomes = []
                for i in (0, 1):
                    worlds[i], outcome = transition(worlds[i], action, config, rngs[i])
                    outcomes.append(outcome)
                if action == "left":
                    self.assertNotEqual(outcomes[0]["success"], outcomes[1]["success"])
                self.assertEqual(rngs[0].getstate(), rngs[1].getstate())

    def test_actions_cannot_change_reversal_schedule_or_future_randomness(self):
        config = Config()
        rngs = [random.Random(9), random.Random(9)]
        task = TaskConfig(kind="reversal-v1", reversal_episode=4)
        worlds = [initial_environment(config, rng, task) for rng in rngs]
        for _ in range(60):
            self.assertEqual(worlds[0], worlds[1])
            for i in (0, 1):
                choice = observe(worlds[i], config)["phase"] == "choice"
                worlds[i], _ = transition(worlds[i], ("left", "right")[i] if choice else "wait", config, rngs[i])
            self.assertEqual(rngs[0].getstate(), rngs[1].getstate())

    def test_task_settings_are_not_agent_config_and_invalid_values_fail(self):
        self.assertFalse({"kind", "reversal_episode", "initial_mapping"} & set(Config().to_dict()))
        invalid_tasks = [{"kind": "unknown"}, {"kind": []},
                         {"kind": "reversal-v1", "reversal_episode": True},
                         {"kind": "reversal-v1", "reversal_episode": 0},
                         {"kind": "reversal-v1", "initial_mapping": True},
                         {"kind": "reversal-v1", "initial_mapping": 2},
                         {"initial_mapping": 0}]
        for data in invalid_tasks:
            with self.subTest(data=data), self.assertRaises(LabError):
                TaskConfig.from_dict(data)
        for data in ({"policy_mode": "x"}, {"learning_enabled": 1}, {"learning_rate": True},
                     {"learning_rate": 0}, {"learning_rate": 1.1}, {"learning_rate": float("nan")},
                     {"learning_rate": float("inf")}, {"learning_rate": 10**400}, {"reversal_episode": 40}):
            with self.subTest(data=data), self.assertRaises(LabError):
                Config.from_dict(data)

    def test_private_mapping_is_sampled_reproducibly_and_bad_state_rejected(self):
        config = Config()
        task = TaskConfig(kind="reversal-v1")
        worlds = [initial_environment(config, random.Random(seed), task) for seed in range(10)]
        self.assertEqual({world["initial_mapping"] for world in worlds}, {0, 1})
        self.assertEqual(worlds, [initial_environment(config, random.Random(seed), task) for seed in range(10)])
        for changes in ({"target": 1-worlds[0]["target"]}, {"cue": True}, {"initial_mapping": None}):
            with self.assertRaises(LabError):
                observe({**worlds[0], **changes}, config)


if __name__ == "__main__":
    unittest.main()
