from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from consciousness_presence.autonomy import AutonomyStore, wake_id_for
from consciousness_presence.store import PresenceError


CORE = {"controls": {"paused": False}, "budget_remaining": 5, "pending": None}
PROMPT = "Run one bounded autonomous activity with saved sources."


def outcome(kind="research", status="completed", notification=None):
    return {"status": status, "kind": kind, "summary": "A measured local result.",
            "source_ids": [] if kind == "rest" else ["record-evidence"], "question": "What would disconfirm this?",
            "notification": notification}


class AutonomyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "presence"
        self.store = AutonomyStore(self.home)
        self.store.register_prompt(PROMPT)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ready(self, **settings):
        self.store.configure({"enabled": True, "idle_seconds": 0, **settings})
        self.store.observe_event({"hook_event_name": "SessionStart", "session_id": "host"}, now=0)

    def scheduled(self, turn="1", now=100, session="scheduled"):
        return self.store.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": session,
                                         "turn_id": turn, "prompt": PROMPT}, now=now)["wake_id"]

    def begin(self, turn="1", now=100):
        wake_id = self.scheduled(turn, now)
        result = self.store.begin(wake_id, CORE, now=now)
        self.assertTrue(result["allowed"], result)
        return wake_id

    def pending_message(self, turn="1", now=100):
        wake_id = self.begin(turn, now)
        notification = {"text": "A sourced question for you: " + turn, "source_ids": ["record-evidence"]}
        self.store.finish(wake_id, outcome(notification=notification), now=now)
        return wake_id, notification

    def assert_code(self, code, call):
        with self.assertRaises(PresenceError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def test_defaults_and_hook_origin_fail_closed(self):
        wake_id = self.scheduled()
        self.assertEqual("disabled", self.store.begin(wake_id, CORE, now=100)["reason"])
        self.store.configure({"enabled": True, "idle_seconds": 0})
        self.assertEqual("hooks_unobserved", self.store.begin(wake_id, CORE, now=100)["reason"])
        self.store.observe_event({"hook_event_name": "SessionStart", "session_id": "host"}, now=100)
        self.assertEqual("scheduled_turn_missing", self.store.begin("invented-wake", CORE, now=100)["reason"])
        impostor = self.store.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": "other",
                                            "turn_id": "t", "prompt": PROMPT + " "}, now=100)
        self.assertEqual("human", impostor["origin"])
        self.assertEqual("human_turn_active", self.store.begin(wake_id, CORE, now=100000)["reason"])
        self.store.close_turn("other", "t", "Explicitly reconciled closed chat", now=100000)
        self.assertTrue(self.store.begin(wake_id, CORE, now=100000)["allowed"])

    def test_idle_clock_tracks_human_completion_and_duplicate_events(self):
        self.ready(idle_seconds=10)
        event = {"hook_event_name": "UserPromptSubmit", "session_id": "human", "turn_id": "h", "prompt": "Hello"}
        self.store.observe_event(event, now=100)
        self.store.observe_event(event, now=110)
        self.assertEqual(100, self.store.status()["last_human_activity"])
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "human", "turn_id": "h"}, now=120)
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "human", "turn_id": "h"}, now=125)
        wake_id = self.scheduled(now=125)
        self.assertEqual(120, self.store.status()["last_human_activity"])
        self.assertEqual("not_idle", self.store.begin(wake_id, CORE, now=129)["reason"])
        self.assertTrue(self.store.begin(wake_id, CORE, now=130)["allowed"])

    def test_two_wakes_race_for_one_reservation_and_replay_is_stable(self):
        self.ready()
        ids = [self.scheduled(str(index)) for index in range(2)]
        def claim(wake_id):
            with AutonomyStore(self.home) as store:
                return store.begin(wake_id, CORE, now=100)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(claim, ids))
        self.assertEqual(1, sum(result["allowed"] for result in results))
        winning = next(result["wake"]["id"] for result in results if result["allowed"])
        replay = self.store.begin(winning, CORE, now=101)
        self.assertTrue(replay["replayed"])
        self.assertEqual(1, len(self.store.status()["wakes"]))
        self.assertEqual(wake_id_for("scheduled", "0"), ids[0])

    def test_core_budget_pause_and_pending_gates(self):
        self.ready()
        wake_id = self.scheduled()
        for state, reason in (({**CORE, "budget_remaining": 0}, "core_budget_exhausted"),
                              ({**CORE, "controls": {"paused": True}}, "core_paused"),
                              ({**CORE, "pending": {"decision": "unfinished"}}, "core_pending"),
                              ({}, "invalid_core_state")):
            self.assertEqual(reason, self.store.begin(wake_id, state, now=100)["reason"])
        self.assertEqual([], self.store.status()["wakes"])

    def test_returning_human_and_configuration_stop_further_steps(self):
        self.ready()
        wake_id = self.begin()
        self.assertTrue(self.store.authorize_step(wake_id, "read-one", now=101)["allowed"])
        self.assertEqual("already_reserved", self.store.authorize_step(wake_id, "read-one", now=102)["reason"])
        self.store.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": "human",
                                  "turn_id": "new", "prompt": "I returned"}, now=103)
        self.assertEqual("human_turn_active", self.store.authorize_step(wake_id, "read-two", now=104)["reason"])
        self.store.observe_event({"hook_event_name": "Interrupt", "session_id": "human", "turn_id": "new"}, now=105)
        self.store.configure({"enabled": False})
        self.assertEqual("disabled", self.store.checkpoint(wake_id, now=106)["reason"])
        # Already obtained results can be recorded even while further actions are blocked.
        self.assertEqual("completed", self.store.finish(wake_id, outcome(), now=107)["status"])

    def test_step_budget_request_and_progress_retries(self):
        self.ready(max_steps_per_wake=2)
        wake_id = self.begin()
        request = {"kind": "research", "candidates": [{"id": "one"}]}
        self.assertTrue(self.store.reserve_request(wake_id, request)["created"])
        self.assertFalse(self.store.reserve_request(wake_id, request)["created"])
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.store.reserve_request(wake_id, {"kind": "dream"}))
        self.store.save_progress(wake_id, "core_commit", {"decision_id": "decision-1"})
        self.assertFalse(self.store.save_progress(wake_id, "core_commit", {"decision_id": "decision-1"})["created"])
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.store.save_progress(wake_id, "core_commit", {"decision_id": "different"}))
        for number in range(2):
            self.assertTrue(self.store.authorize_step(wake_id, str(number), now=101)["allowed"])
        self.assertEqual("step_limit", self.store.authorize_step(wake_id, "extra", now=102)["reason"])
        self.assertEqual(request, self.store.get_wake(wake_id)["request"])

    def test_expired_lease_stays_uncertain_until_explicit_evidence(self):
        self.ready(max_activity_seconds=10)
        first = self.begin()
        self.assertEqual("wake_uncertain", self.store.checkpoint(first, now=110)["reason"])
        second = self.scheduled("second", now=111)
        self.assertEqual("wake_uncertain", self.store.begin(second, CORE, now=111)["reason"])
        self.assert_code("RECONCILIATION_REQUIRED", lambda: self.store.finish(first, outcome(), now=112))
        self.assert_code("INVALID_INPUT", lambda: self.store.reconcile(first, outcome("rest"), now=112))
        resolved = self.store.reconcile(first, outcome(status="failed"), now=112)
        self.assertEqual("failed", resolved["status"])
        self.assertEqual(resolved, self.store.reconcile(first, outcome(status="failed"), now=113))
        self.assertTrue(self.store.begin(second, CORE, now=113)["allowed"])

    def test_daily_activities_reset_at_utc_midnight(self):
        self.ready(max_activities_per_day=1)
        first = self.begin(now=86390)
        self.store.finish(first, outcome("rest"), now=86391)
        second = self.scheduled("next", now=86392)
        self.assertEqual("daily_activity_limit", self.store.begin(second, CORE, now=86399)["reason"])
        self.assertTrue(self.store.begin(second, CORE, now=86400)["allowed"])

    def test_notification_ack_requires_reserved_turn_and_exact_visible_text(self):
        self.ready(message_cooldown_seconds=0)
        _, notification = self.pending_message()
        self.assertIsNone(self.store.outbox(now=101, session_id="wrong", turn_id="1"))
        reserved = self.store.outbox(now=101, session_id="scheduled", turn_id="1")
        self.assertEqual(notification["text"], reserved["text"])
        self.assertIsNone(self.store.outbox(now=102))
        blocked = self.scheduled("new", now=102)
        self.assertEqual("delivery_unacknowledged", self.store.begin(blocked, CORE, now=102)["reason"])
        wrong = self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "new",
                                         "last_assistant_message": reserved["text"]}, now=103)
        self.assertIsNone(wrong["acknowledged_message_id"])
        actual = self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1",
                                          "last_assistant_message": "Hello. " + reserved["text"]}, now=104)
        self.assertEqual(reserved["id"], actual["acknowledged_message_id"])
        self.assertEqual("delivered", self.store.status()["deliveries"][0]["status"])

    def test_missing_ack_is_uncertain_and_never_automatically_resent(self):
        self.ready(message_cooldown_seconds=0)
        self.pending_message()
        reserved = self.store.outbox(now=101)
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1"}, now=102)
        self.scheduled("later", now=86400)
        self.assertIsNone(self.store.outbox(now=86400))
        self.assertEqual("uncertain", self.store.status()["deliveries"][0]["status"])
        # A later visible final variant may provide actual acknowledgment, without resending.
        acknowledged = self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1",
                                                "last_assistant_message": reserved["text"]}, now=86401)
        self.assertEqual(reserved["id"], acknowledged["acknowledged_message_id"])

    def test_message_daily_quota_and_cooldown_cross_midnight_independently(self):
        self.ready(max_messages_per_day=1, message_cooldown_seconds=10)
        self.pending_message("1", now=86390)
        first = self.store.outbox(now=86391)
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1",
                                  "last_assistant_message": first["text"]}, now=86392)
        self.pending_message("2", now=86393)
        self.assertIsNone(self.store.outbox(now=86399))  # Same UTC day quota.
        self.assertIsNone(self.store.outbox(now=86400))  # New day, cooldown still active.
        second = self.store.outbox(now=86402)
        self.assertIsNotNone(second)
        self.assertNotEqual(first["id"], second["id"])

    def test_late_delivery_acknowledgment_counts_towards_new_utc_day(self):
        self.ready(max_messages_per_day=1, message_cooldown_seconds=0)
        self.pending_message("1", now=86390)
        message = self.store.outbox(now=86391)
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1",
                                  "last_assistant_message": message["text"]}, now=86401)
        self.pending_message("2", now=86402)
        self.assertIsNone(self.store.outbox(now=86403))

    def test_reconciliation_never_resets_a_notification_already_delivered(self):
        self.ready(message_cooldown_seconds=0)
        wake_id = self.begin()
        notification = {"text": "The result is still uncertain.", "source_ids": ["record-evidence"]}
        self.store.finish(wake_id, outcome(status="uncertain", notification=notification), now=101)
        message = self.store.outbox(now=102)
        self.store.observe_event({"hook_event_name": "Stop", "session_id": "scheduled", "turn_id": "1",
                                  "last_assistant_message": message["text"]}, now=103)
        self.store.reconcile(wake_id, outcome(notification=notification), now=104)
        self.assertEqual("delivered", self.store.status()["deliveries"][0]["status"])
        self.assertEqual(1, len(self.store.status()["deliveries"]))

    def test_prompt_registration_change_preserves_origin_of_replayed_turn(self):
        self.ready()
        self.scheduled()
        self.store.register_prompt("A changed registered prompt")
        repeated = self.store.observe_event({"hook_event_name": "UserPromptSubmit", "session_id": "scheduled",
                                             "turn_id": "1", "prompt": PROMPT}, now=101)
        self.assertEqual("scheduled", repeated["origin"])
        self.assertTrue(repeated["duplicate"])
        self.assertIsNone(self.store.status()["last_human_activity"])

    def test_finish_is_atomic_with_outbox_and_cannot_replace_receipts(self):
        self.ready()
        wake_id = self.begin()
        notification = {"text": "A verified question", "source_ids": ["record-evidence"]}
        result = outcome(notification=notification)
        self.store.connection.execute("""CREATE TRIGGER fail_notification BEFORE INSERT ON messages
            BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.finish(wake_id, result, now=101)
        self.assertEqual("running", self.store.get_wake(wake_id)["status"])
        self.assertIsNone(self.store.get_wake(wake_id)["result"])
        self.store.connection.execute("DROP TRIGGER fail_notification")
        first = self.store.finish(wake_id, result, now=102)
        self.assertEqual(first, self.store.finish(wake_id, result, now=103))
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.store.finish(wake_id, {**result, "summary": "Changed"}, now=104))
        self.assertEqual(1, len(self.store.status()["deliveries"]))

    def test_provenance_configuration_and_result_validation(self):
        self.ready()
        wake_id = self.begin()
        bad_results = [{**outcome(), "source_ids": []}, {**outcome(), "status": "sent"},
                       {**outcome(), "notification": {"text": "claim", "source_ids": ["unrelated"]}}]
        for result in bad_results:
            self.assert_code("INVALID_INPUT", lambda: self.store.finish(wake_id, result, now=100))
        for settings in ({"enabled": 1}, {"max_activity_seconds": 0}, {"max_messages_per_day": -1}, {"unknown": 4}):
            self.assert_code("INVALID_INPUT", lambda: self.store.configure(settings))
        self.assertEqual("running", self.store.get_wake(wake_id)["status"])

    def test_reserved_request_survives_new_process_and_unrelated_cwd(self):
        self.ready()
        wake_id = self.begin()
        self.store.reserve_request(wake_id, {"kind": "dream"})
        self.store.save_progress(wake_id, "core_commit", {"revision": 12})
        script = """
import json, sys
from consciousness_presence.autonomy import AutonomyStore
with AutonomyStore(sys.argv[1]) as store:
    print(json.dumps(store.get_wake(sys.argv[2])))
"""
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
        run = subprocess.run([sys.executable, "-P", "-B", "-c", script, str(self.home), wake_id],
                             cwd=self.home, env=env, capture_output=True, text=True, check=True)
        recovered = json.loads(run.stdout)
        self.assertEqual({"kind": "dream"}, recovered["request"])
        self.assertEqual({"revision": 12}, recovered["progress"]["core_commit"])
        self.assertEqual(self.store.get_wake(wake_id), recovered)


if __name__ == "__main__":
    unittest.main()
