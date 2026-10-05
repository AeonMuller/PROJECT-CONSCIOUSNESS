"""Causal and boundary checks for the operational capability predictor."""

import random
import unittest

from project_consciousness.capability import initial_model, model_bytes, model_estimates, update_model, validate_model
from project_consciousness.capability_agent import advance_agent, initial_agent, record_result
from project_consciousness.contracts import Config, LabError, canonical, clone, digest
from project_consciousness.memory import observation_record


def config(**overrides):
    return Config(policy_mode="capability", **overrides)


def observation(episode=0, phase="choice", value=None):
    return {"episode": episode, "phase": phase, "value": value}


class FixedRng:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.value


def outcome(decision, episode=0, decision_correct=True, execution_success=True):
    tool = decision["tool"]
    if tool is None:
        return {"terminal": False, "success": None, "reward": 0.0, "episode": episode,
                "decision_correct": None, "execution_success": None, "tool": None, "cost": 0.0}
    cost = 0.05 if tool == "fast" else 0.2
    success = decision_correct and execution_success
    return {"terminal": True, "success": success, "reward": float(success) - cost, "episode": episode,
            "decision_correct": decision_correct, "execution_success": execution_success, "tool": tool, "cost": cost}


class CapabilityModelTests(unittest.TestCase):
    def test_prior_and_layouts_are_equivalent_and_copied(self):
        self_model, generic = initial_model(), initial_model("generic")
        self.assertEqual(model_estimates(self_model), [0.5, 0.5])
        self.assertEqual(model_estimates(generic), [0.5, 0.5])
        view = model_estimates(generic)
        view[0] = 0
        self.assertEqual(model_estimates(generic), [0.5, 0.5])
        self.assertEqual(model_bytes(self_model), len(canonical(self_model).encode("utf-8")))

    def test_feedback_changes_only_used_tool_and_preserves_input(self):
        for backend in ("self", "generic"):
            model = initial_model(backend)
            before = clone(model)
            learned = update_model(model, "safe", True, 2, 0, 0.2, "a" * 64)
            self.assertEqual(model_estimates(learned), [0.5, 0.6])
            self.assertEqual(model, before)
            self.assertEqual(learned["updates"], 1)
            self.assertEqual(learned["last_update"], {"tick": 2, "episode": 0, "input_hash": "a" * 64})
            failed = update_model(learned, "fast", False, 5, 1, 0.2, "b" * 64)
            self.assertEqual(model_estimates(failed), [0.4, 0.6])

    def test_repeated_observations_revise_execution_forecast(self):
        model = initial_model()
        for episode in range(20):
            model = update_model(model, "fast", True, episode * 3 + 2, episode, 0.2, digest(episode))
        self.assertGreater(model_estimates(model)[0], 0.99)
        for episode in range(20, 40):
            model = update_model(model, "fast", False, episode * 3 + 2, episode, 0.2, digest(episode))
        self.assertLess(model_estimates(model)[0], 0.02)
        self.assertEqual(model_estimates(model)[1], 0.5)

    def test_malformed_models_and_future_lineage_are_rejected(self):
        trained = update_model(initial_model(), "fast", True, 2, 0, 0.2, "a" * 64)
        bad = [None, {}, {**initial_model(), "backend": []},
               {**initial_model(), "probabilities": [0.5, 0.5]},
               {**initial_model(), "probabilities": {"fast": True, "safe": 0.5}},
               {**initial_model(), "probabilities": {"fast": float("nan"), "safe": 0.5}},
               {**initial_model(), "updates": True},
               {**initial_model(), "probabilities": {"fast": 0.6, "safe": 0.5}},
               {**trained, "last_update": None},
               {**trained, "last_update": {"tick": 2, "episode": 0, "input_hash": "bad"}}]
        for model in bad:
            with self.subTest(model=model), self.assertRaises(LabError):
                validate_model(model)
        with self.assertRaises(LabError):
            validate_model(trained, 1)
        with self.assertRaises(LabError):
            initial_model([])

    def test_update_rejects_malformed_or_reused_feedback(self):
        args = {"tool": "fast", "execution_success": True, "tick": 2, "episode": 0, "rate": 0.2, "input_hash": "a" * 64}
        for patch in ({"tool": []}, {"execution_success": 1}, {"rate": 0}, {"rate": True},
                      {"rate": float("inf")}, {"tick": True}, {"episode": -1}, {"input_hash": "a"}):
            with self.subTest(patch=patch), self.assertRaises(LabError):
                update_model(initial_model(), **{**args, **patch})
        trained = update_model(initial_model(), **args)
        for patch in ({}, {"tick": 3}, {"tick": 1, "episode": 1}):
            with self.subTest(patch=patch), self.assertRaises(LabError):
                update_model(trained, **{**args, **patch})


class CapabilityAgentTests(unittest.TestCase):
    def cue_state(self, cfg=None, cue=0, episode=0, tick=0, model=None):
        cfg = cfg or config()
        state = initial_agent(cfg)
        if model is not None:
            state["capability"] = model
        obs = observation(episode, "cue", cue)
        state, decision = advance_agent(state, obs, tick, cfg, FixedRng(0.1))
        return record_result(state, obs, decision, outcome(decision, episode), tick, cfg)

    def test_wait_does_not_predict_or_update_model_or_consume_randomness(self):
        cfg, rng = config(), FixedRng(0.1)
        state, decision = advance_agent(initial_agent(cfg), observation(phase="cue", value=1), 0, cfg, rng)
        self.assertEqual(set(decision), {"action", "intended_action", "tool", "probability_left", "probability_fast", "confidence", "memory_ids", "encoded_ids", "records_scanned", "memory_bytes", "predicted_target_left", "predicted_execution_success", "predicted_success", "capability_view", "expected_utilities", "model_version", "model_hash", "model_bytes"})
        for field in ("intended_action", "tool", "probability_left", "probability_fast", "confidence", "predicted_target_left", "predicted_execution_success", "predicted_success", "capability_view", "expected_utilities"):
            self.assertIsNone(decision[field])
        post = record_result(state, observation(phase="cue", value=1), decision, outcome(decision), 0, cfg)
        self.assertEqual(post["capability"], initial_model())
        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["encoded_ids"], ["observation:0"])
        self.assertEqual(rng.calls, 0)

    def test_side_is_grounded_in_memory_and_one_rng_draw_selects_tool(self):
        for cue, side in ((0, "left"), (1, "right")):
            rng, cfg = FixedRng(0.2), config()
            state, decision = advance_agent(self.cue_state(cue=cue), observation(), 2, cfg, rng)
            self.assertEqual(decision["action"], side + ":fast")
            self.assertEqual(decision["tool"], "fast")
            self.assertEqual(decision["probability_fast"], 0.95)
            self.assertEqual(decision["predicted_success"], 0.5)
            self.assertEqual(decision["memory_ids"], ["observation:0"])
            self.assertEqual(rng.calls, 1)
            self.assertEqual(set(state), {"records", "capability"})

    def test_capability_estimates_causally_change_tool_distribution(self):
        cfg = config()
        model = update_model(initial_model(), "safe", True, 2, 0, 1, "a" * 64)
        state = self.cue_state(cfg, episode=1, tick=3, model=model)
        _, decision = advance_agent(state, observation(1), 5, cfg, FixedRng(0.2))
        self.assertEqual(decision["tool"], "safe")
        self.assertEqual(decision["probability_fast"], 0.05)
        self.assertEqual(decision["capability_view"], [0.5, 1.0])
        self.assertEqual(decision["expected_utilities"], [0.45, 0.8])
        _, blocked = advance_agent(state, observation(1), 5, config(capability_read_mode="blocked"), FixedRng(0.2))
        self.assertEqual(blocked["tool"], "fast")
        self.assertEqual(blocked["capability_view"], [0.5, 0.5])
        self.assertEqual(blocked["predicted_execution_success"], 0.5)
        _, sham = advance_agent(state, observation(1), 5, config(capability_read_mode="sham"), FixedRng(0.2))
        self.assertEqual(sham, decision)

    def test_feedback_is_execution_not_global_success(self):
        cfg = config(write_enabled=False)
        state, decision = advance_agent(initial_agent(cfg), observation(), 2, cfg, FixedRng(0.8))
        self.assertEqual(decision["predicted_target_left"], 0.5)
        feedback = outcome(decision, decision_correct=False, execution_success=True)
        self.assertFalse(feedback["success"])
        learned = record_result(state, observation(), decision, feedback, 2, cfg)
        self.assertEqual(model_estimates(learned["capability"]), [0.6, 0.5])
        self.assertEqual(learned["records"], [])
        failed = record_result(state, observation(), decision, outcome(decision, execution_success=False), 2, cfg)
        self.assertEqual(model_estimates(failed["capability"]), [0.4, 0.5])

    def test_predictions_are_locked_before_feedback_and_inputs_unchanged(self):
        cfg = config()
        original = self.cue_state()
        before = clone(original)
        state, decision = advance_agent(original, observation(), 2, cfg, FixedRng(0.2))
        locked = clone(decision)
        feedback = outcome(decision)
        learned = record_result(state, observation(), decision, feedback, 2, cfg)
        self.assertEqual(decision, locked)
        self.assertEqual(decision["predicted_execution_success"], 0.5)
        self.assertEqual(model_estimates(learned["capability"]), [0.6, 0.5])
        self.assertEqual(original, before)
        self.assertEqual(state, before)
        learned["records"][-1]["result"]["success"] = False
        self.assertTrue(feedback["success"])

    def test_frozen_model_is_identical_while_records_continue(self):
        cfg = config(capability_learning_enabled=False)
        state, decision = advance_agent(self.cue_state(cfg), observation(), 2, cfg, FixedRng(0.2))
        learned = record_result(state, observation(), decision, outcome(decision), 2, cfg)
        self.assertEqual(learned["capability"], state["capability"])
        self.assertEqual(len(learned["records"]), len(state["records"]) + 1)

    def test_blocked_capability_reader_keeps_writer_active(self):
        cfg = config(capability_read_mode="blocked")
        model = update_model(initial_model(), "fast", True, 2, 0, 1, "a" * 64)
        state = self.cue_state(cfg, episode=1, tick=3, model=model)
        state, decision = advance_agent(state, observation(1), 5, cfg, FixedRng(0.2))
        self.assertEqual(decision["capability_view"], [0.5, 0.5])
        learned = record_result(state, observation(1), decision, outcome(decision, 1, execution_success=False), 5, cfg)
        self.assertEqual(model_estimates(learned["capability"]), [0.8, 0.5])
        self.assertEqual(learned["capability"]["updates"], 2)

    def test_generic_backend_has_identical_functional_behavior(self):
        states = [initial_agent(config(capability_backend=backend)) for backend in ("self", "generic")]
        rngs = [random.Random(42), random.Random(42)]
        ignored = {"model_hash", "model_bytes"}
        for tick in range(30):
            episode, phase_index = divmod(tick, 3)
            obs = observation(episode, ("cue", "distractor", "choice")[phase_index], None if phase_index == 2 else episode % 2)
            decisions = []
            for index, backend in enumerate(("self", "generic")):
                cfg = config(capability_backend=backend)
                states[index], dec = advance_agent(states[index], obs, tick, cfg, rngs[index])
                states[index] = record_result(states[index], obs, dec, outcome(dec, episode, execution_success=episode % 3 != 0), tick, cfg)
                decisions.append({key: value for key, value in dec.items() if key not in ignored})
            self.assertEqual(decisions[0], decisions[1])
            self.assertEqual(states[0]["records"], states[1]["records"])
            self.assertEqual(model_estimates(states[0]["capability"]), model_estimates(states[1]["capability"]))

    def test_eviction_and_provenance_prevent_hidden_cue_cache(self):
        for cfg in (config(capacity=1), config(read_mode="block_all"), config(agent_mode="reactive")):
            state = self.cue_state(cfg)
            rng = FixedRng(0.8)
            _, decision = advance_agent(state, observation(), 2, cfg, rng)
            self.assertEqual(decision["probability_left"], 0.5)
            self.assertEqual(decision["predicted_success"], 0.25)
            self.assertEqual(decision["memory_ids"], [])
            self.assertEqual(rng.calls, 2)
        for patch in ({"source_kind": "SIMULATED"}, {"episode": 1}, {"origin_agent_id": "other"}):
            state = initial_agent(config())
            state["records"] = [{**observation_record(observation(phase="cue", value=0), 0), **patch}]
            _, decision = advance_agent(state, observation(), 2, config(), FixedRng(0.8))
            self.assertEqual(decision["memory_ids"], [])

    def test_ties_and_exploration_are_explicit_distributions(self):
        for epsilon, expected in ((0.0, 1.0), (0.2, 0.9), (1.0, 0.5)):
            cfg = config(capability_exploration=epsilon)
            _, decision = advance_agent(self.cue_state(cfg), observation(), 2, cfg, FixedRng(0.1))
            self.assertEqual(decision["probability_fast"], expected)
        cfg = config(fast_cost=0.2, safe_cost=0.2)
        _, decision = advance_agent(self.cue_state(cfg), observation(), 2, cfg, FixedRng(0.8))
        self.assertEqual(decision["probability_fast"], 0.5)
        self.assertEqual(decision["tool"], "safe")

    def test_corrupted_decisions_or_feedback_are_rejected_before_updates(self):
        cfg = config()
        state, decision = advance_agent(self.cue_state(), observation(), 2, cfg, FixedRng(0.2))
        feedback = outcome(decision)
        bad_decisions = [{**decision, **patch} for patch in (
            {"predicted_execution_success": 0.9}, {"predicted_success": True}, {"model_hash": "a" * 64},
            {"memory_ids": []}, {"model_version": 1}, {"records_scanned": -1},
            {"memory_bytes": 0}, {"tool": "safe"}, {"action": "right:fast"},
            {"capability_view": [0.9, 0.5]}, {"expected_utilities": []}, {"encoded_ids": ["observation:0"]},
            {"model_bytes": float("nan")}, {"extra": None})]
        for bad in bad_decisions:
            with self.subTest(bad=bad), self.assertRaises(LabError):
                record_result(state, observation(), bad, feedback, 2, cfg)
        for patch in ({"episode": 1}, {"success": False}, {"execution_success": 1}, {"terminal": False},
                      {"tool": "safe"}, {"cost": 0}, {"reward": float("inf")}, {"secret": 0.95}):
            with self.subTest(patch=patch), self.assertRaises(LabError):
                record_result(state, observation(), decision, {**feedback, **patch}, 2, cfg)
        self.assertEqual(state["capability"], initial_model())

    def test_feedback_cannot_contradict_an_observed_fixed_rule_cue(self):
        cfg = config()
        for cue in (0, 1):
            with self.subTest(cue=cue):
                state, decision = advance_agent(self.cue_state(cue=cue), observation(), 2, cfg, FixedRng(0.2))
                contradictory = outcome(decision, decision_correct=False, execution_success=True)
                self.assertFalse(contradictory["success"])
                self.assertEqual(contradictory["reward"], -contradictory["cost"])
                with self.assertRaises(LabError) as caught:
                    record_result(state, observation(), decision, contradictory, 2, cfg)
                self.assertEqual(caught.exception.code, "STATE_INCONSISTENT")
                self.assertEqual(state["capability"], initial_model())

    def test_state_shape_backend_and_post_feedback_reuse_rejected(self):
        cfg = config()
        for state in ({**initial_agent(cfg), "cached_cue": 0}, initial_agent(config(capability_backend="generic"))):
            with self.assertRaises(LabError):
                advance_agent(state, observation(), 2, cfg, FixedRng(0.1))
        state, decision = advance_agent(self.cue_state(), observation(), 2, cfg, FixedRng(0.1))
        post = record_result(state, observation(), decision, outcome(decision), 2, cfg)
        with self.assertRaises(LabError):
            record_result(post, observation(), decision, outcome(decision), 2, cfg)


if __name__ == "__main__":
    unittest.main()
