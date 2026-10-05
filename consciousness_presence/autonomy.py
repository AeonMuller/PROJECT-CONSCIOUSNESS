"""Transactional coordinator for bounded idle activity and visible delivery receipts.

The coordinator grants reservations, not host tool permissions. Exact scheduler
prompt matching is an adapter convention, not authentication of the caller.
"""

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

from .store import PresenceError


DEFAULTS = {"enabled": False, "idle_seconds": 1800, "max_activities_per_day": 3,
            "max_messages_per_day": 2, "message_cooldown_seconds": 14400,
            "max_activity_seconds": 600, "max_steps_per_wake": 4}
BOUNDS = {"idle_seconds": (0, 86400 * 30), "max_activities_per_day": (0, 100),
          "max_messages_per_day": (0, 20), "message_cooldown_seconds": (0, 86400 * 30),
          "max_activity_seconds": (1, 3600), "max_steps_per_wake": (1, 4)}


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise PresenceError("Value must contain finite JSON data") from error


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise PresenceError(name + " must be a nonempty string without NUL")
    return value


def _time(value):
    value = time.time() if value is None else value
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise PresenceError("now must be a finite nonnegative Unix timestamp")
    return float(value)


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def wake_id_for(session_id, turn_id):
    return "wake-" + _hash([session_id, turn_id])


def _result(value):
    required = {"status", "kind", "summary", "source_ids", "question"}
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - {"notification"}:
        raise PresenceError("result requires status, kind, summary, source_ids and question; notification is optional")
    result = json.loads(_json(value))
    if result["status"] not in ("completed", "skipped", "failed", "uncertain"):
        raise PresenceError("Invalid result status")
    if result["kind"] not in ("research", "dream", "reflect", "rest"):
        raise PresenceError("Invalid activity kind")
    _text(result["summary"], "summary")
    if not isinstance(result["source_ids"], list):
        raise PresenceError("source_ids must be a list")
    for source in result["source_ids"]:
        _text(source, "source_id")
    result["source_ids"] = sorted(set(result["source_ids"]))
    if result["status"] == "completed" and result["kind"] != "rest" and not result["source_ids"]:
        raise PresenceError("Completed non-rest activity requires source IDs")
    if result["question"] is not None:
        _text(result["question"], "question")
    notification = result.get("notification")
    if notification is not None:
        if not isinstance(notification, dict) or set(notification) != {"text", "source_ids"}:
            raise PresenceError("notification requires text and source_ids")
        _text(notification["text"], "notification text")
        if not isinstance(notification["source_ids"], list) or not notification["source_ids"]:
            raise PresenceError("notification requires source IDs")
        for source in notification["source_ids"]:
            _text(source, "notification source_id")
        notification["source_ids"] = sorted(set(notification["source_ids"]))
        if not set(notification["source_ids"]) <= set(result["source_ids"]):
            raise PresenceError("Notification sources must belong to the result")
    return result


class AutonomyStore:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.home / "autonomy.sqlite3", timeout=30, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS turns (
                session_id TEXT NOT NULL, turn_id TEXT NOT NULL, origin TEXT NOT NULL,
                opened_at REAL NOT NULL, closed_at REAL, close_reason TEXT, wake_id TEXT,
                PRIMARY KEY(session_id, turn_id));
            CREATE TABLE IF NOT EXISTS observed (id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS wakes (id TEXT PRIMARY KEY, created_at REAL NOT NULL,
                status TEXT NOT NULL, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, wake_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL, reserved_at REAL, delivered_at REAL, value TEXT NOT NULL);
        """)
        with self._write():
            if self._get("settings") is None:
                self._set("settings", DEFAULTS)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.connection.close()

    @contextmanager
    def _write(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def _get(self, key):
        row = self.connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def _set(self, key, value):
        self.connection.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, _json(value)))

    def configure(self, changes):
        if not isinstance(changes, dict) or not changes or changes.keys() - DEFAULTS.keys():
            raise PresenceError("changes must contain known autonomy settings")
        for key, value in changes.items():
            if key == "enabled":
                if type(value) is not bool:
                    raise PresenceError("enabled must be boolean")
            elif type(value) is not int or not BOUNDS[key][0] <= value <= BOUNDS[key][1]:
                raise PresenceError(f"{key} must be an integer in {BOUNDS[key]}")
        with self._write():
            settings = {**self._get("settings"), **changes}
            self._set("settings", settings)
        return settings

    def register_prompt(self, prompt):
        _text(prompt, "prompt")
        receipt = {"sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "length": len(prompt)}
        with self._write():
            self._set("scheduled_prompt", receipt)
        return receipt

    def _turns(self, origin=None):
        sql = "SELECT * FROM turns WHERE closed_at IS NULL"
        args = ()
        if origin:
            sql += " AND origin=?"
            args = (origin,)
        return [dict(row) for row in self.connection.execute(sql + " ORDER BY opened_at, session_id, turn_id", args)]

    def _close(self, session_id, turn_id, reason, now):
        row = self.connection.execute("SELECT * FROM turns WHERE session_id=? AND turn_id=?", (session_id, turn_id)).fetchone()
        if not row:
            return None
        if row["closed_at"] is None:
            self.connection.execute("UPDATE turns SET closed_at=?, close_reason=? WHERE session_id=? AND turn_id=?",
                                    (now, reason, session_id, turn_id))
            if row["origin"] == "human":
                self._set("last_human_activity", now)
        return dict(row)

    def _uncertain_deliveries(self, session_id, turn_id, reason):
        for row in self.connection.execute("SELECT value FROM messages WHERE status='reserved'").fetchall():
            message = json.loads(row[0])
            if message.get("session_id") == session_id and message.get("turn_id") == turn_id:
                message.update(status="uncertain", uncertainty=reason)
                self._save_message(message)

    def observe_event(self, payload, now=None):
        now = _time(now)
        if not isinstance(payload, dict):
            raise PresenceError("Hook payload must be an object")
        event = payload.get("hook_event_name")
        if event not in ("SessionStart", "UserPromptSubmit", "Stop", "Interrupt", "SessionEnd"):
            return {"origin": "system", "event": event, "ignored": True}
        session = _text(payload.get("session_id"), "session_id")
        turn = payload.get("turn_id") or ""
        if not isinstance(turn, str):
            raise PresenceError("turn_id must be a string")
        if event in ("UserPromptSubmit", "Stop"):
            _text(turn, "turn_id")
        prompt = payload.get("prompt")
        if event == "UserPromptSubmit":
            _text(prompt, "prompt")
        event_id = _hash([session, turn, event])
        digest = _hash(prompt if event == "UserPromptSubmit" else [session, turn, event])
        with self._write():
            previous = self.connection.execute("SELECT digest, result FROM observed WHERE id=?", (event_id,)).fetchone()
            if previous and previous[0] != digest:
                raise PresenceError("Hook identity reused with a different prompt", "IDEMPOTENCY_CONFLICT")
            known = self.connection.execute("SELECT origin, wake_id FROM turns WHERE session_id=? AND turn_id=?", (session, turn)).fetchone()
            origin = known[0] if known else "system"
            scheduled_id = known[1] if known else None
            if event == "UserPromptSubmit" and not previous:
                registered = self._get("scheduled_prompt")
                origin = "scheduled" if registered and hashlib.sha256(prompt.encode("utf-8")).hexdigest() == registered["sha256"] else "human"
                scheduled_id = wake_id_for(session, turn) if origin == "scheduled" else None
            if not previous:
                if self._get("first_hook_at") is None and (event == "SessionStart" or origin == "human"):
                    self._set("first_hook_at", now)
                if event == "UserPromptSubmit":
                    self.connection.execute("INSERT INTO turns VALUES (?, ?, ?, ?, NULL, NULL, ?)", (session, turn, origin, now, scheduled_id))
                    if origin == "human":
                        self._set("last_human_activity", now)
            # SessionEnd/Interrupt may have no turn ID and recur after resume.
            # Closure itself is idempotent, so a repeated event still closes new
            # active turns without moving the clock for already closed turns.
            if event in ("Stop", "Interrupt", "SessionEnd"):
                targets = self._turns() if event == "SessionEnd" or not turn else [{"session_id": session, "turn_id": turn}]
                for target in targets:
                    if target["session_id"] == session:
                        self._close(session, target["turn_id"], event, now)
                        if event != "Stop":
                            self._uncertain_deliveries(session, target["turn_id"], event)
            acknowledgment = None
            if event == "Stop" and origin == "scheduled":
                text = payload.get("last_assistant_message")
                for row in self.connection.execute("SELECT value FROM messages WHERE status IN ('reserved','uncertain')").fetchall():
                    message = json.loads(row[0])
                    if message.get("session_id") == session and message.get("turn_id") == turn:
                        if isinstance(text, str) and message["text"] in text:
                            self._deliver(message, {"event": "Stop", "session_id": session, "turn_id": turn,
                                                  "visible_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}, now)
                            acknowledgment = message["id"]
                        else:
                            self._uncertain_deliveries(session, turn, "Stop did not confirm the exact saved message")
            result = {"origin": origin, "event": event, "session_id": session, "turn_id": turn,
                      "duplicate": bool(previous), "wake_id": scheduled_id, "acknowledged_message_id": acknowledgment}
            if not previous:
                self.connection.execute("INSERT INTO observed VALUES (?, ?, ?)", (event_id, digest, _json(result)))
        return result

    def _save_wake(self, wake):
        self.connection.execute("INSERT OR REPLACE INTO wakes VALUES (?, ?, ?, ?)",
                                (wake["id"], wake["created_at"], wake["status"], _json(wake)))

    def get_wake(self, wake_id):
        _text(wake_id, "wake_id")
        row = self.connection.execute("SELECT value FROM wakes WHERE id=?", (wake_id,)).fetchone()
        if row is None:
            raise PresenceError("Unknown wake_id", "NOT_FOUND")
        return json.loads(row[0])

    def _expire(self, now):
        for row in self.connection.execute("SELECT value FROM wakes WHERE status='running'").fetchall():
            wake = json.loads(row[0])
            if now >= wake["deadline"]:
                wake["status"] = "uncertain"
                wake["uncertainty"] = "Activity lease expired; reconcile before another wake"
                self._save_wake(wake)

    def _gate(self, now):
        settings = self._get("settings")
        if not settings["enabled"]:
            return "disabled"
        baseline = self._get("first_hook_at")
        if baseline is None:
            return "hooks_unobserved"
        if self._turns("human"):
            return "human_turn_active"
        last_human = self._get("last_human_activity")
        baseline = max(baseline, last_human if last_human is not None else baseline)
        if now < baseline or now - baseline < settings["idle_seconds"]:
            return "not_idle"
        return None

    def _checkpoint(self, wake_id, now):
        self._expire(now)
        wake = self.get_wake(wake_id)
        reason = self._gate(now)
        if not reason and now < wake["created_at"]:
            reason = "clock_regressed"
        if not reason and wake["status"] != "running":
            reason = "wake_" + wake["status"]
        if not reason and not any(turn["wake_id"] == wake_id for turn in self._turns("scheduled")):
            reason = "scheduled_turn_closed"
        return {"allowed": reason is None, "reason": reason or "allowed", "wake": wake}

    def begin(self, wake_id, core_state, now=None):
        _text(wake_id, "wake_id")
        now = _time(now)
        with self._write():
            self._expire(now)
            existing = self.connection.execute("SELECT 1 FROM wakes WHERE id=?", (wake_id,)).fetchone()
            if existing:
                return {**self._checkpoint(wake_id, now), "replayed": True}
            reason = self._gate(now)
            scheduled = next((turn for turn in self._turns("scheduled") if turn["wake_id"] == wake_id), None)
            if not reason and scheduled is None:
                reason = "scheduled_turn_missing"
            blocking = self.connection.execute("SELECT status FROM wakes WHERE status IN ('running','uncertain') LIMIT 1").fetchone()
            if not reason and blocking:
                reason = "wake_" + blocking[0]
            if not reason and self.connection.execute("SELECT 1 FROM messages WHERE status IN ('reserved','uncertain') LIMIT 1").fetchone():
                reason = "delivery_unacknowledged"
            if not isinstance(core_state, dict) or not isinstance(core_state.get("controls"), dict):
                reason = reason or "invalid_core_state"
            elif type(core_state.get("budget_remaining")) is not int or core_state["budget_remaining"] < 1:
                reason = reason or "core_budget_exhausted"
            elif core_state["controls"].get("paused") is not False:
                reason = reason or "core_paused"
            elif core_state.get("pending", "missing") is not None:
                reason = reason or "core_pending"
            settings = self._get("settings")
            day = int(now // 86400) * 86400
            count = self.connection.execute("SELECT COUNT(*) FROM wakes WHERE created_at>=? AND created_at<?", (day, day + 86400)).fetchone()[0]
            if not reason and count >= settings["max_activities_per_day"]:
                reason = "daily_activity_limit"
            if reason:
                return {"allowed": False, "reason": reason, "replayed": False, "wake": None}
            wake = {"id": wake_id, "session_id": scheduled["session_id"], "turn_id": scheduled["turn_id"],
                    "created_at": now, "deadline": now + settings["max_activity_seconds"], "status": "running",
                    "request": None, "progress": {}, "steps": [], "result": None, "history": []}
            self._save_wake(wake)
            return {"allowed": True, "reason": "allowed", "replayed": False, "wake": wake}

    def checkpoint(self, wake_id, now=None):
        now = _time(now)
        with self._write():
            return self._checkpoint(wake_id, now)

    def authorize_step(self, wake_id, step_id, now=None):
        _text(step_id, "step_id")
        now = _time(now)
        with self._write():
            checked = self._checkpoint(wake_id, now)
            if not checked["allowed"]:
                return checked
            wake = checked["wake"]
            if any(step["id"] == step_id for step in wake["steps"]):
                return {"allowed": False, "reason": "already_reserved", "wake": wake}
            if len(wake["steps"]) >= self._get("settings")["max_steps_per_wake"]:
                return {"allowed": False, "reason": "step_limit", "wake": wake}
            wake["steps"].append({"id": step_id, "reserved_at": now})
            self._save_wake(wake)
            return {"allowed": True, "reason": "allowed", "wake": wake, "step_id": step_id}

    def reserve_request(self, wake_id, request):
        if not isinstance(request, dict) or not request:
            raise PresenceError("request must be a nonempty object")
        request = json.loads(_json(request))
        with self._write():
            wake = self.get_wake(wake_id)
            if wake["request"] is not None:
                if wake["request"] != request:
                    raise PresenceError("Wake request changed", "IDEMPOTENCY_CONFLICT")
                return {"created": False, "request": wake["request"]}
            if wake["status"] != "running":
                raise PresenceError("Cannot reserve a request for a nonrunning wake")
            wake["request"] = request
            self._save_wake(wake)
        return {"created": True, "request": request}

    def save_progress(self, wake_id, key, value):
        _text(key, "key")
        value = json.loads(_json(value))
        with self._write():
            wake = self.get_wake(wake_id)
            if key in wake["progress"]:
                if wake["progress"][key] != value:
                    raise PresenceError("Progress receipt changed", "IDEMPOTENCY_CONFLICT")
                return {"created": False, "key": key, "value": value}
            wake["progress"][key] = value
            self._save_wake(wake)
        return {"created": True, "key": key, "value": value}

    def _save_message(self, message):
        self.connection.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                                (message["id"], message["wake_id"], message["status"], message.get("reserved_at"),
                                 message.get("delivered_at"), _json(message)))

    def _finish(self, wake, result, now, operation):
        kind = (wake["request"] or {}).get("kind")
        if kind is not None and kind != result["kind"]:
            raise PresenceError("Result kind differs from the reserved activity")
        wake.update(status=result["status"], result=result, finished_at=now)
        wake["history"].append({"operation": operation, "result": result, "at": now})
        self._save_wake(wake)
        notification = result.get("notification")
        if notification:
            existing = self.connection.execute("SELECT value FROM messages WHERE wake_id=?", (wake["id"],)).fetchone()
            if existing:
                saved = json.loads(existing[0])
                if any(saved[key] != notification[key] for key in ("text", "source_ids")):
                    raise PresenceError("A wake's saved notification cannot be replaced", "IDEMPOTENCY_CONFLICT")
            else:
                self._save_message({"id": "message-" + _hash(wake["id"]), "wake_id": wake["id"],
                                    **notification, "status": "pending", "created_at": now,
                                    "session_id": None, "turn_id": None})
        return wake

    def finish(self, wake_id, result, now=None):
        result = _result(result)
        now = _time(now)
        with self._write():
            self._expire(now)
        with self._write():
            wake = self.get_wake(wake_id)
            if wake["result"] is not None:
                first = next((item for item in wake["history"] if item["operation"] == "finish"), None)
                if first and first["result"] == result:
                    return wake
                raise PresenceError("Final wake result changed; use reconcile for uncertain outcomes", "IDEMPOTENCY_CONFLICT")
            if wake["status"] == "uncertain" and result["status"] != "uncertain":
                raise PresenceError("Expired wake requires explicit reconciliation", "RECONCILIATION_REQUIRED")
            return self._finish(wake, result, now, "finish")

    def reconcile(self, wake_id, result, now=None):
        result = _result(result)
        now = _time(now)
        if result["status"] == "uncertain" or not result["source_ids"]:
            raise PresenceError("Reconciliation requires evidence and a resolved status")
        with self._write():
            self._expire(now)
        with self._write():
            wake = self.get_wake(wake_id)
            if wake["status"] != "uncertain":
                if any(item["operation"] == "reconcile" and item["result"] == result for item in wake["history"]):
                    return wake
                raise PresenceError("Only an uncertain wake can be reconciled")
            return self._finish(wake, result, now, "reconcile")

    def outbox(self, now=None, session_id=None, turn_id=None):
        now = _time(now)
        if (session_id is None) != (turn_id is None):
            raise PresenceError("Delivery requires both session_id and turn_id")
        with self._write():
            if self._gate(now):
                return None
            if self.connection.execute("SELECT 1 FROM messages WHERE status IN ('reserved','uncertain') LIMIT 1").fetchone():
                return None
            turns = self._turns("scheduled")
            if session_id is not None:
                turns = [turn for turn in turns if turn["session_id"] == session_id and turn["turn_id"] == turn_id]
            if not turns:
                return None
            settings = self._get("settings")
            day = int(now // 86400) * 86400
            # A delayed acknowledgment can cross midnight. Count both potentially
            # sent reservations and confirmed deliveries on the current UTC day.
            count = self.connection.execute("SELECT COUNT(*) FROM messages WHERE (reserved_at>=? AND reserved_at<?) "
                                            "OR (delivered_at>=? AND delivered_at<?)",
                                            (day, day + 86400, day, day + 86400)).fetchone()[0]
            if count >= settings["max_messages_per_day"]:
                return None
            last = self.connection.execute("SELECT MAX(COALESCE(delivered_at,reserved_at)) FROM messages").fetchone()[0]
            if last is not None and now - last < settings["message_cooldown_seconds"]:
                return None
            row = self.connection.execute("SELECT value FROM messages WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return None
            message = json.loads(row[0])
            message.update(status="reserved", reserved_at=now, session_id=turns[-1]["session_id"], turn_id=turns[-1]["turn_id"])
            self._save_message(message)
            return message

    def _deliver(self, message, receipt, now):
        if message["status"] == "delivered":
            if message["receipt"] != receipt:
                raise PresenceError("Delivery receipt changed", "IDEMPOTENCY_CONFLICT")
            return message
        if message["status"] not in ("reserved", "uncertain"):
            raise PresenceError("Message has not been reserved for delivery")
        if now < message["reserved_at"]:
            raise PresenceError("Delivery acknowledgment predates its reservation")
        message.update(status="delivered", delivered_at=now, receipt=receipt)
        self._save_message(message)
        return message

    def delivered(self, message_id, receipt, now=None):
        _text(message_id, "message_id")
        if not isinstance(receipt, dict) or not receipt:
            raise PresenceError("Delivery receipt must be a nonempty object")
        receipt = json.loads(_json(receipt))
        now = _time(now)
        with self._write():
            row = self.connection.execute("SELECT value FROM messages WHERE id=?", (message_id,)).fetchone()
            if row is None:
                raise PresenceError("Unknown message_id", "NOT_FOUND")
            return self._deliver(json.loads(row[0]), receipt, now)

    def close_turn(self, session_id, turn_id, reason, now=None):
        for name, value in (("session_id", session_id), ("turn_id", turn_id), ("reason", reason)):
            _text(value, name)
        now = _time(now)
        with self._write():
            turn = self._close(session_id, turn_id, reason, now)
            if turn is None:
                raise PresenceError("Unknown turn", "NOT_FOUND")
            self._uncertain_deliveries(session_id, turn_id, reason)
            return dict(self.connection.execute("SELECT * FROM turns WHERE session_id=? AND turn_id=?", (session_id, turn_id)).fetchone())

    def status(self):
        return {"settings": self._get("settings"), "scheduled_prompt": self._get("scheduled_prompt"),
                "first_hook_at": self._get("first_hook_at"), "last_human_activity": self._get("last_human_activity"),
                "open_turns": self._turns(), "scheduled_turns": self._turns("scheduled"),
                "wakes": [json.loads(row[0]) for row in self.connection.execute("SELECT value FROM wakes ORDER BY created_at")],
                "deliveries": [json.loads(row[0]) for row in self.connection.execute("SELECT value FROM messages ORDER BY rowid")]}
