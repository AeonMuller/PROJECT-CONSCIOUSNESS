"""Behavioral controls for the causal-memory mechanism, independent of runtime."""

import random
import unittest

from project_consciousness.agent import advance_agent, initial_agent, record_result
from project_consciousness.contracts import Config, LabError, canonical, clone
from project_consciousness.memory import (
    append_record, observation_record, retrieve_episodic, retrieve_history,
    validate_records,
)


def observation(episode=0, phase="cue", value=0):
    return {"episode": episode, "phase": phase, "value": value}


class FixedRng:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.value


class MemoryAgentTests(unittest.TestCase):
    def episode_state(self, config=Config(), cue=0):
        state = initial_agent()
        for tick in range(4):
            obs = observation(phase="cue" if tick == 0 else "distractor", value=cue if tick == 0 else tick % 2)
            state, decision = advance_agent(state, obs, tick, config, random.Random(10))
            state = record_result(state, obs, decision, {"episode": 0, "done": False, "success": None}, tick, config)
        return state

    def choose(self, state, config=Config(), episode=0, rng=None, tick=4):
        return advance_agent(state, observation(episode, "choice", None), tick, config, rng or FixedRng(0.8))

    def test_recorded_cue_controls_choice_without_consuming_randomness(self):
        for cue, action, probability in ((0, "left", 1.0), (1, "right", 0.0)):
            with self.subTest(cue=cue):
                rng = FixedRng(0.2)
                _, decision = self.choose(self.episode_state(cue=cue), rng=rng)
                self.assertEqual(decision["action"], action)
                self.assertEqual(decision["probability_left"], probability)
                self.assertEqual(decision["confidence"], 1.0)
                self.assertEqual(decision["memory_ids"], ["observation:0"])
                self.assertEqual(rng.calls, 0)

    def test_decision_has_exact_contract_and_wait_no_confidence(self):
        state, decision = advance_agent(initial_agent(), observation(), 0, Config(), FixedRng(0.1))
        self.assertEqual(set(decision), {"action", "probability_left", "confidence", "memory_ids", "encoded_ids", "records_scanned", "memory_bytes"})
        self.assertEqual(decision["action"], "wait")
        self.assertIsNone(decision["probability_left"])
        self.assertIsNone(decision["confidence"])
        self.assertEqual(decision["encoded_ids"], ["observation:0"])
        self.assertEqual(set(state), {"records"})

    def test_read_masks_and_sham_have_predicted_distinct_effects(self):
        state = self.episode_state()
        for mode in ("intact", "sham", "mask_irrelevant", "mask_relevant", "block_all"):
            with self.subTest(mode=mode):
                next_state, decision = self.choose(state, Config(read_mode=mode))
                self.assertEqual(next_state, state)
                expected = 0.5 if mode in ("mask_relevant", "block_all") else 1.0
                self.assertEqual(decision["probability_left"], expected)
                self.assertEqual(decision["records_scanned"], {"intact": 8, "sham": 8, "mask_irrelevant": 7, "mask_relevant": 7, "block_all": 0}[mode])

    def test_read_block_keeps_encoding_and_restored_reader_can_use_it(self):
        state = self.episode_state(Config(read_mode="block_all"))
        self.assertEqual(len(state["records"]), 8)
        _, blocked = self.choose(state, Config(read_mode="block_all"))
        _, restored = self.choose(state)
        self.assertEqual(blocked["memory_ids"], [])
        self.assertEqual(restored["action"], "left")

    def test_write_block_preserves_preexisting_reads_and_writes_nothing(self):
        config = Config(write_enabled=False)
        self.assertEqual(self.episode_state(config), {"records": []})
        state = self.episode_state()
        _, decision = self.choose(state, config)
        self.assertEqual(decision["action"], "left")
        obs = observation(phase="choice", value=None)
        self.assertEqual(record_result(state, obs, decision, {"episode": 0, "success": True}, 4, config), state)

    def test_reactive_ignores_supplied_memory_and_never_encodes(self):
        config = Config(agent_mode="reactive")
        self.assertEqual(self.episode_state(config), {"records": []})
        state = self.episode_state()
        result, decision = self.choose(state, config)
        self.assertEqual(result, state)
        self.assertEqual(decision["probability_left"], 0.5)
        self.assertEqual(decision["memory_ids"], [])
        self.assertEqual(decision["records_scanned"], 0)

    def test_policy_fallback_is_explicit_half_and_threshold_is_fixed(self):
        for random_value, action in ((0.0, "left"), (0.499999, "left"), (0.5, "right"), (0.999999, "right")):
            rng = FixedRng(random_value)
            _, decision = self.choose(initial_agent(), rng=rng)
            self.assertEqual(decision["action"], action)
            self.assertEqual(decision["probability_left"], 0.5)
            self.assertEqual(decision["confidence"], 0.5)
            self.assertEqual(rng.calls, 1)

    def test_own_episode_and_observed_provenance_required(self):
        original = observation_record(observation(), 0)
        variants = ({"source_kind": "SIMULATED"}, {"source_kind": "INFERRED"},
                    {"source_kind": "REPORTED"}, {"source_kind": "INTERVENED"},
                    {"origin_agent_id": "agent-other"}, {"episode": 1})
        for updates in variants:
            with self.subTest(updates=updates):
                record = {**original, **updates}
                for mode in ("episodic", "history"):
                    _, decision = self.choose({"records": [record]}, Config(agent_mode=mode))
                    self.assertEqual(decision["memory_ids"], [])
                    self.assertEqual(decision["probability_left"], 0.5)

    def test_memory_ids_include_only_accepted_source(self):
        good = observation_record(observation(), 0)
        simulated = {**observation_record(observation(value=1), 1), "source_kind": "SIMULATED"}
        _, decision = self.choose({"records": [good, simulated]})
        self.assertEqual(decision["action"], "left")
        self.assertEqual(decision["memory_ids"], [good["record_id"]])

    def test_no_inputs_or_return_values_share_mutable_state(self):
        state = self.episode_state()
        original = clone(state)
        obs = observation(phase="distractor", value={"sample": [1, 2]})
        original_obs = clone(obs)
        next_state, decision = advance_agent(state, obs, 4, Config(), FixedRng(0.1))
        outcome = {"episode": 0, "nested": [5]}
        result = record_result(next_state, obs, decision, outcome, 4, Config())
        result["records"][-1]["result"]["nested"].append(7)
        next_state["records"][-1]["value"]["sample"].append(3)
        self.assertEqual(state, original)
        self.assertEqual(obs, original_obs)
        self.assertEqual(outcome["nested"], [5])

    def test_finite_capacity_evicts_cue_without_a_hidden_cache(self):
        state = self.episode_state(Config(capacity=6))
        self.assertEqual(len(state["records"]), 6)
        self.assertNotIn("cue", [record["kind"] for record in state["records"]])
        _, decision = self.choose(state, Config(capacity=6))
        self.assertEqual(decision["probability_left"], 0.5)

    def test_history_parity_across_conditions_capacities_and_cues(self):
        for capacity in (1, 6, 8, 64):
            for cue in (0, 1):
                state = self.episode_state(Config(capacity=capacity), cue)
                for read_mode in ("intact", "sham", "block_all", "mask_relevant", "mask_irrelevant"):
                    _, episodic = self.choose(state, Config(capacity=capacity, read_mode=read_mode))
                    _, history = self.choose(state, Config(capacity=capacity, read_mode=read_mode, agent_mode="history"))
                    self.assertEqual(episodic, history)

    def test_memory_cost_is_serialized_records_utf8_bytes(self):
        state = self.episode_state()
        _, decision = self.choose(state)
        self.assertEqual(decision["memory_bytes"], len(canonical(state["records"]).encode("utf-8")))

    def test_outcome_is_observed_linked_once_and_conflict_is_rejected(self):
        obs = observation()
        state, decision = advance_agent(initial_agent(), obs, 0, Config(), FixedRng(0.1))
        outcome = {"episode": 0, "done": False}
        first = record_result(state, obs, decision, outcome, 0, Config())
        second = record_result(first, obs, decision, outcome, 0, Config())
        self.assertEqual(first, second)
        self.assertEqual(first["records"][-1]["source_id"], "action:0")
        self.assertEqual(first["records"][-1]["source_kind"], "OBSERVED")
        with self.assertRaises(LabError) as caught:
            record_result(first, obs, decision, {"episode": 0, "done": True}, 0, Config())
        self.assertEqual(caught.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_invalid_record_boundaries_fail_loudly(self):
        good = observation_record(observation(), 0)
        cases = ([good, good], [{**good, "source_kind": "MADE_UP"}],
                 [{**good, "tick": 9, "source_id": "observation:9"}],
                 [{**good, "source_id": "observation:3"}],
                 [{**good, "origin_agent_id": ""}])
        for records in cases:
            with self.subTest(records=records), self.assertRaises(LabError):
                validate_records(records, 4)
        oversized = observation_record(observation(phase="distractor", value="x" * 4096), 0)
        with self.assertRaises(LabError) as caught:
            append_record([], oversized, 64, 0)
        self.assertEqual(caught.exception.code, "BUDGET_EXHAUSTED")

    def test_future_records_are_rejected_by_both_readers(self):
        record = observation_record(observation(), 5)
        for reader in (retrieve_episodic, retrieve_history):
            with self.assertRaises(LabError) as caught:
                reader([record], 0, 4, "intact")
            self.assertEqual(caught.exception.code, "INVALID_PROVENANCE")

    def test_invalid_shapes_produce_boundary_errors(self):
        good = observation_record(observation(), 0)
        for updates in ({"source_kind": []}, {"kind": []}, {"record_id": "renamed-observation"}):
            with self.subTest(updates=updates), self.assertRaises(LabError):
                validate_records([{**good, **updates}], 0)
        with self.assertRaises(LabError):
            advance_agent(initial_agent(), observation(phase=[]), 0, Config(), FixedRng(0.1))

    def test_public_observation_and_state_reject_hidden_fields(self):
        for obs in ({**observation(), "hidden_target": 0}, observation(phase="choice", value=0)):
            with self.assertRaises(LabError):
                advance_agent(initial_agent(), obs, 0, Config(), FixedRng(0.1))
        with self.assertRaises(LabError):
            advance_agent({"records": [], "cached_cue": 0}, observation(), 0, Config(), FixedRng(0.1))


if __name__ == "__main__":
    unittest.main()
