"""Causal feedback, provenance, neutrality and parameter-freeze controls."""

import unittest

from project_consciousness.agent import advance_agent, initial_agent, record_result
from project_consciousness.contracts import Config, LabError, canonical, clone, digest
from project_consciousness.learning import initial_learner, learner_bytes, validate_learner
from project_consciousness.memory import observation_record


def observation(episode=0, phase="cue", value=0):
    return {"episode": episode, "phase": phase, "value": value}


def feedback(episode, success=None):
    return {"episode": episode, "terminal": success is not None,
            "success": success, "reward": float(success) if success is not None else 0.0}


class FixedRng:
    def __init__(self, value=0.1):
        self.value = value
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.value


class LearningAgentTests(unittest.TestCase):
    config = Config(policy_mode="learned")

    def choice(self, cue=0, episode=0, state=None, config=None, rng=None):
        config = config or self.config
        state = initial_agent(config) if state is None else state
        tick = episode * 5
        state, waiting = advance_agent(state, observation(episode, "cue", cue), tick, config, FixedRng())
        state = record_result(state, observation(episode, "cue", cue), waiting, feedback(episode), tick, config)
        obs = observation(episode, "choice", None)
        state, decision = advance_agent(state, obs, tick + 4, config, rng or FixedRng())
        return state, obs, decision, tick + 4

    def complete(self, cue, target, episode, state=None, config=None):
        config = config or self.config
        state, obs, decision, tick = self.choice(cue, episode, state, config)
        success = decision["action"] == ("left" if target == 0 else "right")
        return record_result(state, obs, decision, feedback(episode, success), tick, config), decision

    def test_fixed_initial_state_and_decisions_are_unchanged(self):
        self.assertEqual(initial_agent(), {"records": []})
        self.assertEqual(initial_agent(Config()), {"records": []})
        self.assertEqual(set(initial_agent(self.config)), {"records", "learner"})

    def test_prior_is_neutral_for_both_cues_and_does_not_update_on_observation(self):
        for cue in (0, 1):
            for random_value, action in ((0.1, "left"), (0.9, "right")):
                rng = FixedRng(random_value)
                state, _, decision, _ = self.choice(cue, rng=rng)
                self.assertEqual(state["learner"], initial_learner())
                self.assertEqual(decision["action"], action)
                self.assertEqual(decision["probability_left"], 0.5)
                self.assertEqual(decision["predicted_target_left"], 0.5)
                self.assertEqual(decision["predicted_success"], 0.5)
                self.assertEqual(decision["model_version"], 0)
                self.assertEqual(decision["model_hash"], digest(initial_learner()))
                self.assertEqual(rng.calls, 1)

    def test_feedback_updates_only_retrieved_cue_and_keeps_prediction_pre_outcome(self):
        state, obs, decision, tick = self.choice(cue=1)
        before = clone(state)
        locked = clone(decision)
        result = record_result(state, obs, decision, feedback(0, True), tick, self.config)
        self.assertEqual(result["learner"]["q_left"], [0.5, 0.625])
        self.assertEqual(result["learner"]["updates"], 1)
        self.assertEqual(decision, locked)
        self.assertEqual(state, before)
        self.assertEqual(decision["predicted_target_left"], 0.5)
        self.assertNotEqual(decision["model_hash"], digest(result["learner"]))

    def test_target_is_inferred_from_action_and_success_for_all_combinations(self):
        for action_left, success, target_left in ((True, True, True), (True, False, False),
                                                  (False, True, False), (False, False, True)):
            rng = FixedRng(0.1 if action_left else 0.9)
            state, obs, decision, tick = self.choice(rng=rng)
            result = record_result(state, obs, decision, feedback(0, success), tick, self.config)
            self.assertEqual(result["learner"]["q_left"][0], 0.625 if target_left else 0.375)

    def test_both_mappings_are_learned_without_a_preferred_mapping(self):
        for mapping in (0, 1):
            state = initial_agent(self.config)
            for episode in range(12):
                cue = episode % 2
                state, decision = self.complete(cue, cue ^ mapping, episode, state)
                if episode >= 2:
                    self.assertEqual(decision["action"], "left" if cue ^ mapping == 0 else "right")
            self.assertEqual(state["learner"]["updates"], 12)
            self.assertGreater(state["learner"]["q_left"][mapping], 0.9)
            self.assertLess(state["learner"]["q_left"][1 ^ mapping], 0.1)

    def test_selection_probability_and_model_prediction_are_distinct(self):
        state, _ = self.complete(0, 0, 0)
        rng = FixedRng()
        _, _, decision, _ = self.choice(0, 1, state, rng=rng)
        self.assertEqual(decision["predicted_target_left"], 0.625)
        self.assertEqual(decision["predicted_success"], 0.625)
        self.assertEqual(decision["probability_left"], 1.0)
        self.assertEqual(rng.calls, 0)

    def test_reversal_adapts_only_when_learning_is_enabled(self):
        state = initial_agent(self.config)
        for episode in range(16):
            state, _ = self.complete(episode % 2, episode % 2, episode, state)
        frozen_config = Config(policy_mode="learned", learning_enabled=False)
        frozen = clone(state)
        frozen_model = clone(frozen["learner"])
        for episode in range(16, 32):
            cue = episode % 2
            state, adaptive_decision = self.complete(cue, 1 ^ cue, episode, state)
            frozen, frozen_decision = self.complete(cue, 1 ^ cue, episode, frozen, frozen_config)
            self.assertEqual(frozen["learner"], frozen_model)
            self.assertEqual(frozen_decision["action"], "left" if cue == 0 else "right")
            if episode >= 24:
                self.assertEqual(adaptive_decision["action"], "left" if cue == 1 else "right")
        self.assertNotEqual(frozen["records"], [])

    def test_frozen_prior_is_invariant_despite_memory_writes_and_feedback(self):
        config = Config(policy_mode="learned", learning_enabled=False)
        state = initial_agent(config)
        for episode in range(3):
            state, _ = self.complete(episode % 2, episode % 2, episode, state, config)
            self.assertEqual(state["learner"], initial_learner())
        self.assertGreater(len(state["records"]), 0)

    def test_read_block_masks_and_reactive_do_not_learn_from_stored_cues(self):
        for changes in ({"read_mode": "block_all"}, {"read_mode": "mask_relevant"}, {"agent_mode": "reactive"}):
            config = Config(policy_mode="learned", **changes)
            state, obs, decision, tick = self.choice(config=config)
            result = record_result(state, obs, decision, feedback(0, True), tick, config)
            self.assertEqual(result["learner"], initial_learner())
            self.assertIsNone(decision["learning_evidence"])
            self.assertEqual(decision["predicted_target_left"], 0.5)

    def test_relevant_provenance_and_episode_are_required(self):
        for changes in ({"source_kind": "SIMULATED"}, {"source_kind": "INFERRED"},
                        {"source_kind": "REPORTED"}, {"origin_agent_id": "agent-other"}, {"episode": 1}):
            state = initial_agent(self.config)
            state["records"] = [{**observation_record(observation(), 0), **changes}]
            obs = observation(phase="choice", value=None)
            state, decision = advance_agent(state, obs, 4, self.config, FixedRng())
            result = record_result(state, obs, decision, feedback(0, True), 4, self.config)
            self.assertEqual(result["learner"], initial_learner())
            self.assertIsNone(decision["learning_evidence"])

    def test_feedback_cannot_substitute_another_valid_cue_for_the_decision(self):
        state, obs, decision, tick = self.choice()
        another = observation_record(observation(value=1), 3)
        state["records"].append(another)
        with self.assertRaises(LabError) as error:
            record_result(state, obs, decision, feedback(0, True), tick, self.config)
        self.assertEqual(error.exception.code, "INVALID_PROVENANCE")
        state["records"].pop()
        blocked = Config(policy_mode="learned", read_mode="block_all")
        with self.assertRaises(LabError):
            record_result(state, obs, decision, feedback(0, True), tick, blocked)

    def test_write_block_can_learn_only_from_preexisting_readable_evidence(self):
        config = Config(policy_mode="learned", write_enabled=False)
        state = initial_agent(config)
        state["records"] = [observation_record(observation(), 0)]
        obs = observation(phase="choice", value=None)
        before, decision = advance_agent(state, obs, 4, config, FixedRng())
        result = record_result(before, obs, decision, feedback(0, True), 4, config)
        self.assertEqual(result["records"], state["records"])
        self.assertEqual(result["learner"]["updates"], 1)
        empty, empty_obs, empty_decision, tick = self.choice(config=config)
        result = record_result(empty, empty_obs, empty_decision, feedback(0, True), tick, config)
        self.assertEqual(result["learner"]["updates"], 0)

    def test_exact_feedback_retry_is_inert_and_conflicting_retry_is_rejected(self):
        state, obs, decision, tick = self.choice()
        result = record_result(state, obs, decision, feedback(0, True), tick, self.config)
        self.assertEqual(record_result(result, obs, decision, feedback(0, True), tick, self.config), result)
        with self.assertRaises(LabError) as error:
            record_result(result, obs, decision, feedback(0, False), tick, self.config)
        self.assertEqual(error.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_duplicate_guard_survives_outcome_eviction_of_the_cue(self):
        config = Config(policy_mode="learned", capacity=1)
        state = initial_agent(config)
        state["records"] = [observation_record(observation(), 0)]
        obs = observation(phase="choice", value=None)
        state, decision = advance_agent(state, obs, 4, config, FixedRng())
        first = record_result(state, obs, decision, feedback(0, True), 4, config)
        self.assertEqual(first["records"][0]["kind"], "outcome")
        self.assertEqual(record_result(first, obs, decision, feedback(0, True), 4, config), first)

    def test_same_episode_cannot_update_twice_under_a_new_tick(self):
        state, obs, decision, tick = self.choice()
        state = record_result(state, obs, decision, feedback(0, True), tick, self.config)
        state, repeated_decision = advance_agent(state, obs, tick + 1, self.config, FixedRng())
        with self.assertRaises(LabError) as error:
            record_result(state, obs, repeated_decision, feedback(0, True), tick + 1, self.config)
        self.assertEqual(error.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_invalid_feedback_is_rejected_without_mutating_inputs(self):
        state, obs, decision, tick = self.choice()
        baseline = clone(state)
        for change in ({"success": 1}, {"success": None}, {"reward": 0.0}, {"terminal": False},
                       {"episode": 1}, {"reward": True}, {"reward": float("nan")}, {"hidden_target": 0}):
            with self.subTest(change=change), self.assertRaises(LabError):
                record_result(state, obs, decision, {**feedback(0, True), **change}, tick, self.config)
            self.assertEqual(state, baseline)

    def test_tampered_prediction_or_evidence_is_rejected(self):
        state, obs, decision, tick = self.choice()
        for change in ({"predicted_target_left": 1}, {"model_hash": "bad"}, {"model_version": 1},
                       {"learning_evidence": {"cue": 1, "record_id": "observation:0"}},
                       {"learning_evidence": {"cue": False, "record_id": "observation:0"}},
                       {"probability_left": True}, {"memory_ids": ["observation:99"]}):
            with self.subTest(change=change), self.assertRaises(LabError):
                record_result(state, obs, {**decision, **change}, feedback(0, True), tick, self.config)

    def test_learner_cost_and_state_shape_are_explicit(self):
        state, obs, decision, tick = self.choice()
        self.assertEqual(decision["model_bytes"], learner_bytes(state["learner"]))
        self.assertEqual(decision["model_bytes"], len(canonical(state["learner"]).encode("utf-8")))
        for change in ({"q_left": [float("nan"), 0.5]}, {"q_left": [True, 0.5]},
                       {"updates": True}, {"cached_cue": 0}, {"q_left": [10**1000, 0.5]}):
            with self.subTest(change=change), self.assertRaises(LabError):
                validate_learner({**initial_learner(), **change})

    def test_frozen_and_adaptive_choose_identically_before_first_feedback(self):
        state = initial_agent(self.config)
        for episode in range(8):
            state, _ = self.complete(episode % 2, episode % 2, episode, state)
        adaptive, obs, first, tick = self.choice(0, 8, state)
        frozen_config = Config(policy_mode="learned", learning_enabled=False)
        frozen, _, control, _ = self.choice(0, 8, state, frozen_config)
        self.assertEqual(first, control)
        self.assertEqual(adaptive, frozen)
        feedback_value = feedback(8, False)
        adaptive = record_result(adaptive, obs, first, feedback_value, tick, self.config)
        frozen = record_result(frozen, obs, control, feedback_value, tick, frozen_config)
        self.assertNotEqual(adaptive["learner"], frozen["learner"])
        self.assertEqual(adaptive["records"], frozen["records"])


if __name__ == "__main__":
    unittest.main()
