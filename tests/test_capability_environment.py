from dataclasses import replace
import random
import unittest

from project_consciousness.contracts import Config, LabError, TaskConfig, clone
from project_consciousness.environment import initial_environment, observe, transition


class CapabilityEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(policy_mode="capability", delay=1)
        self.task = TaskConfig(kind="capability-v1", capability_change_episode=2,
                               fast_success_before=1.0, fast_success_after=0.0, safe_success=1.0)

    def test_decision_and_execution_are_distinct_and_costs_always_apply(self):
        rng = random.Random(3)
        env = initial_environment(self.config, rng, self.task)
        env.update(step=2, target=0)
        for action, correct, executes, success in (("left:fast", True, True, True),
                                                  ("right:safe", False, True, False)):
            _, result = transition(env, action, self.config, rng)
            self.assertEqual((result["decision_correct"], result["execution_success"], result["success"]),
                             (correct, executes, success))
            self.assertEqual(result["reward"], float(success) - result["cost"])
        env["episode"] = 2
        _, failed = transition(env, "left:fast", self.config, rng)
        self.assertTrue(failed["decision_correct"])
        self.assertFalse(failed["execution_success"])
        self.assertFalse(failed["success"])
        self.assertEqual(failed["reward"], -self.config.fast_cost)

    def test_change_boundary_and_public_observations_have_no_capability_signal(self):
        rng = random.Random(4)
        env = initial_environment(self.config, rng, self.task)
        before = clone(env)
        alternate = clone(env)
        alternate["execution_draws"] = [.99, .99]
        alternate["capability_task"]["fast_success_before"] = .3
        for step in range(3):
            self.assertEqual(observe({**env, "step": step}, self.config), observe({**alternate, "step": step}, self.config))
            self.assertEqual(set(observe({**env, "step": step}, self.config)), {"episode", "phase", "value"})
        next_env, feedback = transition(env, "wait", self.config, rng)
        self.assertEqual(set(feedback), {"terminal", "success", "reward", "episode", "decision_correct", "execution_success", "tool", "cost"})
        self.assertIsNone(feedback["execution_success"])
        next_env["execution_draws"][0] = .9
        next_env["capability_task"]["fast_success_after"] = .9
        self.assertEqual(env, before)
        for episode in range(5):
            choice = {**env, "episode": episode, "step": 2}
            side = "left" if choice["target"] == 0 else "right"
            _, feedback = transition(choice, side + ":fast", self.config, rng)
            self.assertEqual(feedback["execution_success"], episode < 2)

    def test_unused_tool_noise_is_sampled_and_future_world_independent_of_actions(self):
        rngs = [random.Random(5), random.Random(5)]
        worlds = [initial_environment(self.config, rng, self.task) for rng in rngs]
        for _ in range(30):
            self.assertEqual(worlds[0], worlds[1])
            for i in (0, 1):
                phase = observe(worlds[i], self.config)["phase"]
                worlds[i], _ = transition(worlds[i], ("left:fast", "right:safe")[i] if phase == "choice" else "wait", self.config, rngs[i])
            self.assertEqual(rngs[0].getstate(), rngs[1].getstate())

    def test_invalid_probabilities_actions_and_private_states_fail_before_rng_changes(self):
        for changes in ({"fast_success_before": True}, {"safe_success": 1.01}, {"fast_success_after": float("nan")},
                        {"capability_change_episode": 0}, {"capability_change_episode": False}):
            with self.subTest(changes=changes), self.assertRaises(LabError):
                replace(self.task, **changes)
        for changes in ({"capability_backend": []}, {"capability_read_mode": "x"}, {"capability_learning_enabled": 1},
                        {"capability_learning_rate": 0}, {"capability_exploration": float("inf")}, {"safe_cost": -1},
                        {"fast_cost": 10**400}):
            with self.subTest(changes=changes), self.assertRaises(LabError):
                replace(self.config, **changes)
        rng = random.Random(1)
        env = initial_environment(self.config, rng, self.task)
        before = rng.getstate()
        for action in ("left", "left:unknown", "right:safe", None, {}):
            with self.subTest(action=action), self.assertRaises(LabError):
                transition(env, action, self.config, rng)
            self.assertEqual(rng.getstate(), before)
        for draws in ([0, 1], [True, .5], [float("nan"), .5], [.5]):
            with self.subTest(draws=draws), self.assertRaises(LabError):
                observe({**env, "execution_draws": draws}, self.config)
        self.assertFalse({"fast_success_before", "fast_success_after", "safe_success", "capability_change_episode"} & set(self.config.to_dict()))


if __name__ == "__main__":
    unittest.main()
