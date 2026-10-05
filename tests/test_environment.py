"""Contract tests for the hidden delayed-cue environment."""

import copy
import random
import unittest

from project_consciousness.contracts import Config, LabError
from project_consciousness.environment import initial_environment, observe, transition


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(delay=3)
        self.rng = random.Random(42)
        self.env = initial_environment(self.config, self.rng)

    def test_episode_schedule_and_outcomes(self):
        env = self.env
        self.assertEqual(observe(env, self.config), {"episode": 0, "phase": "cue", "value": env["target"]})
        rng_after_initial = self.rng.getstate()
        for step in range(self.config.delay + 1):
            env, outcome = transition(env, "wait", self.config, self.rng)
            self.assertEqual(outcome, {"terminal": False, "success": None, "reward": 0.0, "episode": 0})
            if step < self.config.delay:
                self.assertEqual(observe(env, self.config), {"episode": 0, "phase": "distractor", "value": env["distractors"][step]})
        self.assertEqual(self.rng.getstate(), rng_after_initial)
        self.assertEqual(observe(env, self.config), {"episode": 0, "phase": "choice", "value": None})
        action = "left" if env["target"] == 0 else "right"
        next_env, outcome = transition(env, action, self.config, self.rng)
        self.assertEqual(outcome, {"terminal": True, "success": True, "reward": 1.0, "episode": 0})
        self.assertEqual(next_env["episode"], 1)
        self.assertEqual(next_env["step"], 0)

    def test_wrong_choice_has_zero_reward(self):
        env = {**self.env, "step": self.config.delay + 1}
        action = "right" if env["target"] == 0 else "left"
        _, outcome = transition(env, action, self.config, self.rng)
        self.assertEqual(outcome, {"terminal": True, "success": False, "reward": 0.0, "episode": 0})

    def test_public_observation_does_not_leak_private_state(self):
        env = {**self.env, "step": self.config.delay + 1}
        alternate = {**env, "target": 1 - env["target"], "distractors": [1 - n for n in env["distractors"]]}
        self.assertEqual(observe(env, self.config), observe(alternate, self.config))
        for step in range(self.config.delay + 2):
            self.assertEqual(set(observe({**env, "step": step}, self.config)), {"episode", "phase", "value"})
        # A distractor exposes only its own value, not a hidden target or future distractor.
        current = {**env, "step": 1}
        future_changed = {**current, "target": 1 - current["target"], "distractors": list(current["distractors"])}
        future_changed["distractors"][-1] = 1 - future_changed["distractors"][-1]
        self.assertEqual(observe(current, self.config), observe(future_changed, self.config))

    def test_inputs_and_returned_states_do_not_alias(self):
        before = copy.deepcopy(self.env)
        public = observe(self.env, self.config)
        public["value"] = "changed"
        next_env, _ = transition(self.env, "wait", self.config, self.rng)
        self.assertEqual(self.env, before)
        next_env["distractors"][0] = 1 - next_env["distractors"][0]
        self.assertEqual(self.env, before)
        choice_env = {**self.env, "step": self.config.delay + 1}
        before_choice = copy.deepcopy(choice_env)
        transition(choice_env, "left", self.config, self.rng)
        self.assertEqual(choice_env, before_choice)

    def test_actions_do_not_change_future_world_randomness(self):
        left_rng = random.Random(7)
        right_rng = random.Random(7)
        left_env = initial_environment(self.config, left_rng)
        right_env = initial_environment(self.config, right_rng)
        for episode in range(20):
            self.assertEqual(left_env, right_env)
            self.assertEqual(left_env["episode"], episode)
            for _ in range(self.config.delay + 1):
                left_env, _ = transition(left_env, "wait", self.config, left_rng)
                right_env, _ = transition(right_env, "wait", self.config, right_rng)
            left_env, _ = transition(left_env, "left", self.config, left_rng)
            right_env, _ = transition(right_env, "right", self.config, right_rng)
            self.assertEqual(left_rng.getstate(), right_rng.getstate())
        self.assertEqual(left_env, right_env)

    def test_seeded_determinism(self):
        def run():
            rng = random.Random(1729)
            env = initial_environment(self.config, rng)
            trace = []
            for _ in range(30):
                observation = observe(env, self.config)
                action = "left" if observation["phase"] == "choice" else "wait"
                env, outcome = transition(env, action, self.config, rng)
                trace.append((observation, env, outcome))
            return trace, rng.getstate()
        self.assertEqual(run(), run())

    def test_delay_limits(self):
        for delay in (1, 100):
            with self.subTest(delay=delay):
                config = Config(delay=delay)
                env = initial_environment(config, self.rng)
                self.assertEqual(len(env["distractors"]), delay)
                for _ in range(delay + 1):
                    env, _ = transition(env, "wait", config, self.rng)
                self.assertEqual(observe(env, config)["phase"], "choice")
                next_env, _ = transition(env, "left", config, self.rng)
                self.assertEqual(next_env["episode"], 1)

    def test_malformed_states_raise_lab_error(self):
        invalid = [None, [], {}, {**self.env, "extra": 1}]
        for field, values in {
            "episode": [-1, True, 1.5, "0"],
            "step": [-1, self.config.delay + 2, True, 1.5, "0"],
            "target": [-1, 2, True, 0.0, "0"],
            "distractors": [None, (), [0], [0, 1, True], [0, 1, 2], [0, 1, 0.0]],
        }.items():
            invalid.extend({**self.env, field: value} for value in values)
        for env in invalid:
            with self.subTest(env=env):
                before_rng = self.rng.getstate()
                with self.assertRaises(LabError):
                    observe(env, self.config)
                with self.assertRaises(LabError):
                    transition(env, "wait", self.config, self.rng)
                self.assertEqual(self.rng.getstate(), before_rng)

    def test_illegal_actions_raise_lab_error_without_mutation(self):
        for step, actions in [(0, ["left", "right", "bad", None, False, 1, {}]), (4, ["wait", "bad", None, True, [], 0])]:
            for action in actions:
                with self.subTest(step=step, action=action):
                    env = {**self.env, "step": step}
                    before_env = copy.deepcopy(env)
                    before_rng = self.rng.getstate()
                    with self.assertRaises(LabError) as error:
                        transition(env, action, self.config, self.rng)
                    self.assertEqual(error.exception.code, "INVALID_ACTION")
                    self.assertEqual(env, before_env)
                    self.assertEqual(self.rng.getstate(), before_rng)

    def test_invalid_config_and_rng_raise_lab_error(self):
        for config in (None, {}, 3):
            with self.subTest(config=config):
                with self.assertRaises(LabError):
                    initial_environment(config, self.rng)
                with self.assertRaises(LabError):
                    observe(self.env, config)
                with self.assertRaises(LabError):
                    transition(self.env, "wait", config, self.rng)
        for rng in (None, {}, 3):
            with self.subTest(rng=rng):
                with self.assertRaises(LabError):
                    initial_environment(self.config, rng)
                with self.assertRaises(LabError):
                    transition(self.env, "wait", self.config, rng)


if __name__ == "__main__":
    unittest.main()
