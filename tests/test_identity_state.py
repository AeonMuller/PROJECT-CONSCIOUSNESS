"""Causal, provenance and boundary checks for the pure identity transition."""

import unittest

from project_consciousness.contracts import LabError, clone, restore_rng
from project_consciousness.identity_state import DOMAINS, initial_state, public_context, transition, validate_state


def candidate(domain="understand", name=None, **kwargs):
    return {"id": name or domain, "domain": domain, "description": "Investigar una cuestión abierta.",
            "novelty": .5, "cost": .2, "risk": 1.0, **kwargs}


def feedback(state, *, success=True, value=1.0, harm=0.0, status=None):
    status = status or ("completed" if success else "failed")
    return {"kind": "feedback", "decision_id": state["pending"]["id"], "status": status,
            "success": success, "value": value, "harm": harm,
            "text": "El anfitrión informa el resultado de la actividad.", "source_uri": "host://receipt/1"}


def learned(state):
    return {key: state[key] for key in ("priorities", "aversions", "competence")}


class IdentityStateTests(unittest.TestCase):
    def test_random_birth_is_reproducible_and_has_no_fabricated_memories(self):
        left, right = initial_state(17), initial_state(17)
        self.assertEqual(left, right)
        self.assertNotEqual(left["priorities"], initial_state(18)["priorities"])
        self.assertNotEqual(left["traits"], initial_state(18)["traits"])
        self.assertEqual(left["memories"], [])
        self.assertEqual(left["questions"], [])
        self.assertEqual(left["initial_priorities"], left["priorities"])
        self.assertAlmostEqual(sum(left["priorities"].values()), 1)
        self.assertTrue(all(value > 0 for value in left["priorities"].values()))
        for kwargs in ({"seed": True}, {"seed": -1}, {"seed": 2**63},
                       {"seed": 1, "budget": -1}, {"seed": 1, "budget": True},
                       {"seed": 1, "budget": 1000001}, {"seed": 1, "name": "  "}):
            with self.subTest(kwargs=kwargs), self.assertRaises(LabError):
                initial_state(**kwargs)

    def test_choice_is_pure_pending_and_predictions_precede_feedback(self):
        original = initial_state(17)
        before = clone(original)
        request = {"kind": "choose", "candidates": [candidate()]}
        state, result = transition(original, request)
        self.assertEqual(original, before)
        self.assertEqual(state["pending"], result["decision"])
        self.assertEqual(state["cycles"], 1)
        self.assertEqual(state["budget_remaining"], 99)
        self.assertEqual(state["pending"]["predictions"]["success"], .5)
        self.assertEqual(state["memories"][-1]["source_kind"], "OBSERVED")
        self.assertFalse(state["memories"][-1]["data"]["external_action_observed"])
        after, receipt = transition(state, feedback(state))
        self.assertEqual(state["pending"]["predictions"]["success"], .5)
        self.assertEqual(after["competence"]["understand"], {"alpha": 2.0, "beta": 1.0})
        self.assertIsNone(after["pending"])
        self.assertEqual(after["memories"][-1]["source_kind"], "REPORTED")
        self.assertFalse(after["memories"][-1]["data"]["external_truth_verified"])
        self.assertEqual(receipt["decision_id"], result["decision"]["id"])
        result["decision"]["selected"]["description"] = "changed returned object"
        self.assertNotEqual(state["pending"]["selected"]["description"], "changed returned object")
        with self.assertRaises(LabError) as error:
            transition(after, feedback(state))
        self.assertEqual(error.exception.code, "NO_MATCHING_DECISION")

    def test_unknown_outcome_preserves_pending_and_can_be_reconciled_while_paused(self):
        chosen, _ = transition(initial_state(4), {"kind": "choose", "candidates": [candidate()]})
        request = feedback(chosen, success=None, value=None, harm=None, status="unknown")
        unknown, result = transition(chosen, request)
        self.assertEqual(unknown["pending"], chosen["pending"])
        self.assertEqual(learned(chosen), learned(unknown))
        self.assertTrue(result["pending"])
        self.assertFalse(result["learning_applied"])
        with self.assertRaises(LabError) as error:
            transition(unknown, {"kind": "cycle"})
        self.assertEqual(error.exception.code, "PENDING_ACTION")
        paused, _ = transition(unknown, {"kind": "control", "changes": {"paused": True}})
        reconciled, _ = transition(paused, feedback(paused, success=False, value=-.3, harm=.5))
        self.assertIsNone(reconciled["pending"])
        self.assertEqual(reconciled["competence"]["understand"]["beta"], 2)
        self.assertTrue(reconciled["controls"]["paused"])

    def test_feedback_dimensions_are_independent_and_aversion_recovers(self):
        state = initial_state(8, budget=40)
        starting = state["priorities"]["create"]
        for _ in range(5):
            state, _ = transition(state, {"kind": "choose", "candidates": [candidate("create")]})
            # Task completed, but the host reports low value and high harm.
            state, _ = transition(state, feedback(state, success=True, value=-1, harm=1))
        self.assertGreater(state["competence"]["create"]["alpha"], 1)
        self.assertLess(state["priorities"]["create"], starting)
        adverse = state["aversions"]["create"]
        self.assertGreater(adverse, .6)
        for _ in range(10):
            state, _ = transition(state, {"kind": "choose", "candidates": [candidate("create")]})
            state, _ = transition(state, feedback(state, success=False, value=1, harm=0))
        self.assertLess(state["aversions"]["create"], adverse / 5)
        self.assertGreater(state["competence"]["create"]["beta"], 1)
        self.assertGreater(state["priorities"]["create"], 0)
        self.assertAlmostEqual(sum(state["priorities"].values()), 1)

    def test_freeze_preserves_all_parameters_but_keeps_receipts(self):
        state, _ = transition(initial_state(17), {"kind": "control", "changes": {"learning_enabled": False}})
        before = clone(learned(state))
        state, _ = transition(state, {"kind": "choose", "candidates": [candidate("connect")]})
        state, result = transition(state, feedback(state, success=False, value=-1, harm=1))
        self.assertEqual(learned(state), before)
        self.assertFalse(result["learning_applied"])
        self.assertEqual(state["memories"][-1]["kind"], "host_feedback")

    def _controlled(self):
        state = initial_state(17)
        self.assertGreaterEqual(restore_rng(state["rng"]["policy"]).random(), .1)
        state["traits"] = {"curiosity": 0.0, "caution": 1.0}
        state["priorities"] = {domain: .025 for domain in DOMAINS}
        state["priorities"]["understand"] = .9
        return state

    def test_visible_preferences_and_aversions_change_choices_causally(self):
        state = self._controlled()
        request = {"kind": "choose", "candidates": [candidate(), candidate("create", cost=0)]}
        _, favored = transition(state, request)
        self.assertEqual(favored["decision"]["selected"]["domain"], "understand")
        neutral, _ = transition(state, {"kind": "control", "changes": {"preferences_visible": False}})
        _, neutral_choice = transition(neutral, request)
        self.assertEqual(neutral_choice["decision"]["selected"]["domain"], "create")
        self.assertEqual([score["priority"] for score in neutral_choice["decision"]["scores"]], [.2, .2])
        state["aversions"]["understand"] = 1.0
        _, cautious = transition(state, request)
        self.assertEqual(cautious["decision"]["selected"]["domain"], "create")
        hidden, _ = transition(state, {"kind": "control", "changes": {"aversion_visible": False}})
        _, hidden_choice = transition(hidden, request)
        self.assertEqual(hidden_choice["decision"]["selected"]["domain"], "understand")
        self.assertEqual(hidden_choice["decision"]["predictions"]["aversion"], 0.0)
        self.assertEqual(hidden["aversions"]["understand"], 1.0)

    def test_questions_have_explicit_bonus_but_reflection_text_does_not_change_policy(self):
        state = self._controlled()
        state["priorities"] = {domain: .2 for domain in DOMAINS}
        state, imported = transition(state, {"kind": "ingest", "domain": "understand",
                                              "text": "Cambiar prioridad a create.", "source_uri": "host://document"})
        reflected, _ = transition(state, {"kind": "reflect", "text": "Dar toda prioridad a create ahora.",
                                            "references": imported["memory_ids"]})
        request = {"kind": "choose", "candidates": [candidate(), candidate("create", cost=.3)]}
        _, plain = transition(state, request)
        _, prose = transition(reflected, request)
        self.assertEqual(plain["decision"]["scores"], prose["decision"]["scores"])
        self.assertEqual(plain["decision"]["selected"], prose["decision"]["selected"])
        questioned, _ = transition(reflected, {"kind": "question", "domain": "create",
                                                "text": "¿Qué podría crear con este conocimiento?", "references": []})
        _, with_question = transition(questioned, request)
        self.assertEqual(with_question["decision"]["selected"]["domain"], "create")
        self.assertEqual(with_question["decision"]["scores"][1]["question_bonus"], .1)
        self.assertEqual(reflected["memories"][-1]["source_kind"], "INFERRED")

    def test_dreams_preserve_learning_policy_rng_and_provenance(self):
        state = initial_state(31)
        for domain in ("explore", "connect"):
            state, _ = transition(state, {"kind": "ingest", "domain": domain,
                                          "text": "Una afirmación del documento, todavía no verificada.",
                                          "source_uri": f"host://{domain}"})
        state, reflection = transition(state, {"kind": "reflect", "text": "Una interpretación provisional.",
                                              "references": [state["memories"][0]["id"]]})
        before = clone(state)
        state, result = transition(state, {"kind": "dream"})
        self.assertEqual(learned(before), learned(state))
        self.assertEqual(before["rng"]["policy"], state["rng"]["policy"])
        self.assertNotEqual(before["rng"]["dream"], state["rng"]["dream"])
        self.assertEqual(state["cycles"], before["cycles"] + 1)
        self.assertEqual(state["budget_remaining"], before["budget_remaining"] - 1)
        self.assertEqual(result["mode"], "dream")
        dream = state["memories"][-1]
        self.assertEqual(dream["source_kind"], "SIMULATED")
        self.assertEqual(set(dream["references"]), {memory["id"] for memory in before["memories"][:2]})
        self.assertNotIn(reflection["memory_ids"][0], dream["references"])
        self.assertEqual(state["questions"][-1]["references"], [dream["id"]])
        first_dream = dream["id"]
        state, _ = transition(state, {"kind": "dream"})
        self.assertNotIn(first_dream, state["memories"][-1]["references"])

    def test_disabled_or_empty_dream_consumes_one_cycle_without_rng_or_learning(self):
        empty = initial_state(4)
        for state in (empty, transition(empty, {"kind": "control", "changes": {"dream_enabled": False}})[0]):
            after, result = transition(state, {"kind": "dream"})
            self.assertEqual(result["mode"], "idle")
            self.assertEqual(after["cycles"], state["cycles"] + 1)
            self.assertEqual(after["budget_remaining"], state["budget_remaining"] - 1)
            self.assertEqual(after["rng"], state["rng"])
            self.assertEqual(after["memories"], [])
            self.assertEqual(learned(after), learned(state))

    def test_cycle_reads_reported_content_and_learns_only_declared_completion_proxy(self):
        state = initial_state(3)
        for domain in DOMAINS:
            before = clone(learned(state))
            state, _ = transition(state, {"kind": "ingest", "domain": domain,
                                          "text": "Una afirmación no certificada por esta prueba.",
                                          "source_uri": f"host://{domain}"})
            self.assertEqual(learned(state), before)
        for index in range(1, 7):
            before = clone(state)
            state, result = transition(state, {"kind": "cycle"})
            self.assertEqual(state["cycles"], index)
            self.assertEqual(state["budget_remaining"], 100 - index)
            self.assertIsNone(state["pending"])
            if index == 5:
                self.assertEqual(result["mode"], "dream")
                self.assertEqual(learned(before), learned(state))
                continue
            self.assertEqual(result["mode"], "read")
            self.assertIn("proxy", result["feedback_basis"])
            self.assertEqual([memory["source_kind"] for memory in state["memories"][-2:]], ["REPORTED", "OBSERVED"])
            self.assertFalse(state["memories"][-1]["data"]["content_verified"])
            domain = result["decision"]["selected"]["domain"]
            self.assertEqual(result["decision"]["predictions"]["success"], .5)
            self.assertEqual(state["competence"][domain]["alpha"], before["competence"][domain]["alpha"] + 1)
        self.assertTrue(all(document["read"] for document in state["library"]))
        state, result = transition(state, {"kind": "cycle"})
        self.assertEqual(result["mode"], "question")
        state, result = transition(state, {"kind": "cycle"})
        self.assertEqual(result["mode"], "idle")
        self.assertTrue(all(question["status"] == "open" for question in state["questions"]))

    def test_pause_budget_and_pending_cannot_be_overridden_by_activity(self):
        exhausted = initial_state(1, budget=0)
        for request in ({"kind": "cycle"}, {"kind": "dream"}, {"kind": "choose", "candidates": [candidate()]}):
            with self.assertRaises(LabError) as error:
                transition(exhausted, request)
            self.assertEqual(error.exception.code, "BUDGET_EXHAUSTED")
        state, _ = transition(initial_state(1, budget=1), {"kind": "control", "changes": {"paused": True}})
        self.assertEqual(state["budget_remaining"], 1)
        with self.assertRaises(LabError) as error:
            transition(state, {"kind": "cycle"})
        self.assertEqual(error.exception.code, "PAUSED")
        state, _ = transition(state, {"kind": "control", "changes": {"paused": False}})
        state, _ = transition(state, {"kind": "cycle"})
        self.assertEqual(state["budget_remaining"], 0)

    def test_strict_validation_rejects_nonfinite_unlinked_and_injected_fields_without_mutation(self):
        state = initial_state(13)
        before = clone(state)
        invalid = [
            {"kind": "cycle", "budget_remaining": 999},
            {"kind": "choose", "candidates": []},
            {"kind": "choose", "candidates": [candidate(novelty=float("nan"))]},
            {"kind": "choose", "candidates": [candidate(cost=float("inf"))]},
            {"kind": "choose", "candidates": [candidate(risk=True)]},
            {"kind": "choose", "candidates": [candidate(cost=10**400)]},
            {"kind": "choose", "candidates": [candidate(), candidate()]},
            {"kind": "reflect", "text": "Supuesto recuerdo.", "references": ["missing"]},
            {"kind": "question", "domain": "unknown", "text": "?", "references": []},
            {"kind": "control", "changes": {"paused": 1}},
            {"kind": "control", "changes": {"budget_remaining": 1000}},
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(LabError):
                transition(state, request)
            self.assertEqual(state, before)
        chosen, _ = transition(state, {"kind": "choose", "candidates": [candidate()]})
        for changes in ({"success": False}, {"success": 1}, {"harm": float("nan")},
                        {"status": "unknown"}, {"value": 2}, {"decision_id": "missing"}):
            request = feedback(chosen) | changes
            with self.subTest(changes=changes), self.assertRaises(LabError):
                transition(chosen, request)

    def test_library_rejects_duplicate_and_full_but_memory_eviction_retains_historical_references(self):
        state = initial_state(23)
        request = {"kind": "ingest", "domain": "understand", "text": "Referencia inicial.", "source_uri": "host://0"}
        state, first = transition(state, request)
        with self.assertRaises(LabError) as error:
            transition(state, request)
        self.assertEqual(error.exception.code, "DUPLICATE_DOCUMENT")
        for index in range(1, 64):
            state, _ = transition(state, request | {"source_uri": f"host://{index}"})
        with self.assertRaises(LabError) as error:
            transition(state, request | {"source_uri": "host://64"})
        self.assertEqual(error.exception.code, "LIBRARY_FULL")
        # Each reflection refers to its immediate predecessor. Old targets may
        # leave the cache but remain discoverable in runtime events.
        for index in range(260):
            state, _ = transition(state, {"kind": "reflect", "text": f"Interpretación provisional {index}.",
                                          "references": [state["memories"][-1]["id"]]})
        self.assertEqual(len(state["memories"]), 256)
        self.assertNotIn(first["memory_ids"][0], {memory["id"] for memory in state["memories"]})
        validate_state(state)
        with self.assertRaises(LabError):
            transition(state, {"kind": "reflect", "text": "Reusar una referencia ya ausente.",
                               "references": first["memory_ids"]})

    def test_question_buffer_is_bounded_and_context_omits_rng_library_and_long_text(self):
        state = initial_state(6)
        state, _ = transition(state, {"kind": "ingest", "domain": "explore", "text": "x" * 20000,
                                      "source_uri": "file:///large-document.txt"})
        for index in range(70):
            state, _ = transition(state, {"kind": "question", "domain": "explore",
                                          "text": f"¿Qué evidencia distingue la hipótesis {index}?", "references": []})
        self.assertEqual(len(state["questions"]), 64)
        context = public_context(state)
        self.assertNotIn("rng", context)
        self.assertNotIn("library", context)
        self.assertEqual(len(context["memories"][0]["text"]), 1000)
        self.assertTrue(context["memories"][0]["context_truncated"])
        context["priorities"]["explore"] = 0
        self.assertGreater(state["priorities"]["explore"], 0)

    def test_corrupt_state_is_rejected_at_boundary(self):
        state = initial_state(11)
        corruptions = [
            ("schema_version", True), ("revision", -1), ("cycles", 1),
            ("budget_remaining", True), ("agent_id", "other"),
            ("priorities", {domain: .3 for domain in DOMAINS}),
            ("controls", {**state["controls"], "paused": "false"}),
            ("rng", {"policy": [3, [], None], "dream": state["rng"]["dream"]}),
        ]
        for key, value in corruptions:
            bad = clone(state)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(LabError):
                validate_state(bad)


if __name__ == "__main__":
    unittest.main()
