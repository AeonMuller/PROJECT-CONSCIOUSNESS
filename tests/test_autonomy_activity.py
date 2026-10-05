"""Coordinator/core boundary tests, including lost responses after committed effects."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from consciousness_presence import activity
from consciousness_presence.autonomy import AutonomyStore, wake_id_for
from consciousness_presence.core import read_core
from consciousness_presence.store import PresenceStore, PresenceError
from project_consciousness.identity_runtime import LifeRuntime


ROOT = Path(__file__).resolve().parents[1]


class AutonomyActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "presence"
        self.life = self.root / "life"
        with LifeRuntime.create(self.life, name="Test", budget=3) as runtime:
            runtime.apply({"kind": "ingest", "domain": "explore", "text": "Observed document used for a scenario.",
                           "source_uri": "test:document"}, "fixture-document")
            self.before = runtime.snapshot()
            self.binding = {"project": str(ROOT), "life": str(self.life), "python": sys.executable,
                            "skill": str(ROOT / "skills" / "project-consciousness"),
                            "life_id": runtime.manifest["life_id"], "agent_id": self.before["agent_id"]}
        with PresenceStore(self.home) as store:
            store.bind(self.binding)
            record = store.record("evidence", "one", "memory", "A fixture check passed.", "test:check", provenance="OBSERVED")
            self.source = record["id"]
        self.wake_id = self.scheduled_turn("one")
        self.request = {"kind": "research", "candidates": [
            {"id": "repo", "domain": "explore", "description": "Read the repository specification",
             "novelty": .5, "cost": .1, "risk": .1},
            {"id": "web", "domain": "understand", "description": "Read a public primary source",
             "novelty": .4, "cost": .2, "risk": .1}]}

    def scheduled_turn(self, turn):
        with AutonomyStore(self.home) as coordinator:
            coordinator.configure({"enabled": True, "idle_seconds": 0})
            coordinator.register_prompt("Exact scheduled task")
            coordinator.observe_event({"hook_event_name": "SessionStart", "session_id": "scheduled"})
            coordinator.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": "scheduled",
                                       "turn_id": turn, "prompt": "Exact scheduled task"})
        return wake_id_for("scheduled", turn)

    def completion(self, **updates):
        return {"status": "completed", "summary": "A bounded check completed", "source_ids": [self.source],
                "question": "Will this result hold under a changed condition?",
                "notification": {"text": "I checked the hypothesis and found a testable next question.", "source_ids": [self.source]},
                "feedback": {"success": True, "value": .2, "harm": 0, "text": "The bounded fixture check passed.",
                             "source_uri": "test:check"}, **updates}

    def test_research_retries_keep_one_decision_and_one_feedback(self):
        started = activity.start(self.home, self.wake_id, self.request)
        self.assertTrue(started["allowed"])
        after_start = read_core(self.binding)["state"]
        replay = activity.start(self.home, self.wake_id, self.request)
        self.assertFalse(replay["allowed"])
        self.assertEqual("replayed", replay["reason"])
        target = str(ROOT / "README.md")
        self.assertTrue(activity.check(self.home, self.wake_id, "read-1", "repo", target)["allowed"])
        self.assertFalse(activity.check(self.home, self.wake_id, "read-1", "repo", target)["allowed"])
        activity.complete(self.home, self.wake_id, self.completion())
        after = read_core(self.binding)["state"]
        activity.complete(self.home, self.wake_id, self.completion())
        self.assertEqual(after, read_core(self.binding)["state"])
        self.assertEqual(self.before["budget_remaining"] - 1, after["budget_remaining"])
        self.assertNotEqual(after_start["priorities"], after["priorities"])
        self.assertIsNone(after["pending"])
        with AutonomyStore(self.home) as coordinator:
            message = coordinator.outbox(session_id="scheduled", turn_id="one")
            self.assertEqual(self.completion()["notification"]["text"], message["text"])
            coordinator.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "one",
                                       "last_assistant_message": message["text"]})
            self.assertEqual("delivered", coordinator.status()["deliveries"][0]["status"])

    def test_lost_start_response_recovers_committed_core_without_second_credit(self):
        original = activity.apply_core
        def lose_response(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("simulated lost response after commit")
        with patch.object(activity, "apply_core", side_effect=lose_response):
            with self.assertRaises(OSError):
                activity.start(self.home, self.wake_id, self.request)
        committed = read_core(self.binding)["state"]
        result = activity.start(self.home, self.wake_id, self.request)
        self.assertTrue(result["allowed"])
        self.assertEqual(committed, read_core(self.binding)["state"])

    def test_lost_feedback_response_recovers_without_double_learning(self):
        activity.start(self.home, self.wake_id, self.request)
        original = activity.apply_core
        def lose_response(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("lost feedback response")
        with patch.object(activity, "apply_core", side_effect=lose_response):
            with self.assertRaises(OSError):
                activity.complete(self.home, self.wake_id, self.completion())
        committed = read_core(self.binding)["state"]
        activity.complete(self.home, self.wake_id, self.completion())
        after = read_core(self.binding)["state"]
        for key in ("priorities", "aversions", "competence", "rng", "budget_remaining"):
            self.assertEqual(committed[key], after[key])

    def test_returning_human_stops_new_tools_but_completed_outcome_can_be_recorded(self):
        activity.start(self.home, self.wake_id, self.request)
        with AutonomyStore(self.home) as coordinator:
            coordinator.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": "human-chat",
                                       "turn_id": "hi", "prompt": "I'm back"})
        self.assertFalse(activity.check(self.home, self.wake_id, "read", "repo", str(ROOT / "README.md"))["allowed"])
        activity.complete(self.home, self.wake_id, self.completion())
        self.assertIsNone(read_core(self.binding)["state"]["pending"])

    def test_dream_preserves_preferences_and_records_simulated_result(self):
        started = activity.start(self.home, self.wake_id, {"kind": "dream"})
        self.assertTrue(started["allowed"])
        request = self.completion(source_ids=started["source_ids"], notification=None)
        del request["feedback"]
        activity.complete(self.home, self.wake_id, request)
        after = read_core(self.binding)["state"]
        for key in ("priorities", "aversions", "competence"):
            self.assertEqual(self.before[key], after[key])
        with PresenceStore(self.home) as store:
            self.assertEqual("SIMULATED", store.recent(1)[0]["provenance"])

    def test_unknown_result_reconciles_without_resampling_or_inventing_success(self):
        activity.start(self.home, self.wake_id, self.request)
        unknown = self.completion(status="uncertain", notification=None,
                                  feedback={"success": None, "value": None, "harm": None,
                                            "text": "Result unavailable", "source_uri": "test:uncertain"})
        activity.complete(self.home, self.wake_id, unknown)
        pending = read_core(self.binding)["state"]
        self.assertIsNotNone(pending["pending"])
        self.assertEqual(self.before["priorities"], pending["priorities"])
        activity.complete(self.home, self.wake_id, self.completion(), reconcile=True)
        self.assertIsNone(read_core(self.binding)["state"]["pending"])

    def test_scope_and_changed_retry_are_rejected(self):
        activity.start(self.home, self.wake_id, self.request)
        for kind, target in (("repo", str(self.root)), ("web", "http://127.0.0.1/"),
                             ("web", "http://127.1/"), ("web", "http://0x7f.0.0.1/"),
                             ("web", "http://localhost.localdomain/"),
                             ("web", "https://user:password@example.com/"), ("web", "file:///secret")):
            with self.assertRaises(PresenceError):
                activity.check(self.home, self.wake_id, "bad", kind, target)
        with self.assertRaises(PresenceError):
            activity.start(self.home, self.wake_id, {"kind": "dream"})

    def test_expired_lost_start_can_recover_existing_receipt_for_reconciliation(self):
        original = activity.apply_core
        def lost(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("lost after commit")
        with patch.object(activity, "apply_core", side_effect=lost):
            with self.assertRaises(OSError):
                activity.start(self.home, self.wake_id, self.request)
        with AutonomyStore(self.home) as coordinator:
            deadline = coordinator.get_wake(self.wake_id)["deadline"]
            self.assertFalse(coordinator.checkpoint(self.wake_id, now=deadline + 1)["allowed"])
        activity.complete(self.home, self.wake_id, self.completion(), reconcile=True)
        self.assertIsNone(read_core(self.binding)["state"]["pending"])

    def test_reconcile_completed_dream_is_rejected_before_any_core_mutation(self):
        started = activity.start(self.home, self.wake_id, {"kind": "dream"})
        request = self.completion(source_ids=started["source_ids"], notification=None)
        del request["feedback"]
        activity.complete(self.home, self.wake_id, request)
        before = read_core(self.binding)["state"]
        with self.assertRaises(PresenceError):
            activity.complete(self.home, self.wake_id, request, reconcile=True)
        self.assertEqual(before, read_core(self.binding)["state"])

    def test_nul_completion_is_rejected_without_poisoning_the_retry_receipt(self):
        activity.start(self.home, self.wake_id, self.request)
        before = read_core(self.binding)["state"]
        with self.assertRaises(PresenceError):
            activity.complete(self.home, self.wake_id, self.completion(summary="invalid\x00summary"))
        self.assertEqual(before, read_core(self.binding)["state"])
        activity.complete(self.home, self.wake_id, self.completion())

    def test_expired_lost_feedback_is_reconciled_without_second_learning_update(self):
        activity.start(self.home, self.wake_id, self.request)
        original = activity.apply_core
        def lost(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("lost")
        with patch.object(activity, "apply_core", side_effect=lost):
            with self.assertRaises(OSError):
                activity.complete(self.home, self.wake_id, self.completion())
        committed = read_core(self.binding)["state"]
        with AutonomyStore(self.home) as coordinator:
            coordinator.checkpoint(self.wake_id, now=coordinator.get_wake(self.wake_id)["deadline"] + 1)
        activity.complete(self.home, self.wake_id, self.completion(), reconcile=True)
        after = read_core(self.binding)["state"]
        for key in ("priorities", "aversions", "competence", "rng", "budget_remaining"):
            self.assertEqual(committed[key], after[key])


if __name__ == "__main__":
    unittest.main()
