"""One bounded LLM-host activity, with stable receipts across the v0.4 bridge."""

import ipaddress
import math
from pathlib import Path
from urllib.parse import urlsplit

from .autonomy import AutonomyStore
from .core import apply_core, import_memories, read_core, lookup_core_receipt
from .store import PresenceStore, PresenceError


def _binding(home):
    with PresenceStore(home) as presence:
        binding = presence.binding()
        if not binding or not presence.enabled():
            raise PresenceError("Presence is not bound and enabled", "PRESENCE_DISABLED")
        if not (Path(binding["skill"]) / "SKILL.md").is_file():
            raise PresenceError("The installed skill is unavailable", "SKILL_MISSING")
        return binding


def _text(value, label, maximum=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise PresenceError(f"{label} must contain 1..{maximum} characters")
    return value


def _start_request(request):
    if not isinstance(request, dict):
        raise PresenceError("Activity request must be an object")
    kind = request.get("kind")
    fields = {"research": {"kind", "candidates"}, "dream": {"kind"},
              "reflect": {"kind", "text", "references"}, "rest": {"kind", "reason"}}
    if kind not in fields or set(request) != fields[kind]:
        raise PresenceError("Invalid activity kind or fields")
    if kind == "rest":
        _text(request["reason"], "reason")
    if kind == "reflect":
        _text(request["text"], "text")
    return kind


def start(home, wake_id, request):
    kind = _start_request(request)
    binding = _binding(home)
    core = read_core(binding)
    core_request = {**request, "kind": "choose"} if kind == "research" else request
    with AutonomyStore(home) as coordinator:
        try:
            existing = coordinator.get_wake(wake_id)
        except ValueError:
            existing = None
        if existing and existing.get("request"):
            coordinator.reserve_request(wake_id, request)  # Detect changed retries.
            if existing.get("progress", {}).get("start"):
                return {"allowed": False, "reason": "replayed", "wake": existing,
                        "result": existing["progress"]["start"]}
            # A core commit may have succeeded before its receipt reached this
            # sidecar. In that case core pending/budget changed legitimately.
            gate = coordinator.checkpoint(wake_id)
        else:
            if kind != "rest":
                from project_consciousness.identity_state import transition
                transition(core["state"], core_request)
            gate = coordinator.begin(wake_id, core["state"])
        if not gate["allowed"]:
            return gate
        coordinator.reserve_request(wake_id, request)
        if kind == "rest":
            result = {"status": "completed", "kind": "rest", "summary": request["reason"],
                      "source_ids": [], "question": None, "notification": None}
            coordinator.finish(wake_id, result)
            return {"allowed": False, "reason": "rest", "result": result}
        # Stable IDs recover a commit whose response was lost without spending
        # another credit or sampling the RNG again.
        event = apply_core(binding, core_request, wake_id + ":start")
        after = read_core(binding)
        with PresenceStore(home) as presence:
            import_memories(presence, after)
        result = {"kind": kind, "event": event,
                  "source_ids": [f"core:{binding['life_id']}:{item}"
                                 for item in event["result"].get("memory_ids", [])]}
        coordinator.save_progress(wake_id, "start", result)
        return {"allowed": True, "reason": "started", "wake_id": wake_id, **result}


def check(home, wake_id, step_id, kind, target):
    binding = _binding(home)
    _text(step_id, "step_id", 256)
    _text(target, "target", 2000)
    if kind == "repo":
        path = Path(target).resolve()
        root = Path(binding["project"]).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise PresenceError("Research target must exist inside the bound project", "SCOPE_DENIED")
        relative = path.relative_to(root)
        if any(part.casefold() in {".git", ".aws", ".ssh", ".codex", ".agents"} or part.casefold().startswith(".env")
               for part in relative.parts):
            raise PresenceError("Private configuration is outside autonomous research scope", "SCOPE_DENIED")
        target = str(path)
    elif kind == "web":
        url = urlsplit(target)
        hostname = (url.hostname or "").lower().rstrip(".")
        if (url.scheme not in {"http", "https"} or not hostname or url.username or url.password
                or "." not in hostname or hostname.endswith((".local", ".localhost", ".internal", ".localdomain"))):
            raise PresenceError("Use a public HTTP(S) source without credentials", "SCOPE_DENIED")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
            if not any(character.isalpha() for character in hostname.rsplit(".", 1)[-1]):
                raise PresenceError("Ambiguous numeric hosts are outside research scope", "SCOPE_DENIED")
        if address and not address.is_global:
            raise PresenceError("Private/reserved IPs are outside research scope", "SCOPE_DENIED")
    else:
        raise PresenceError("step kind must be repo or web")
    core = read_core(binding)
    if core["state"]["controls"]["paused"]:
        return {"allowed": False, "reason": "core_paused"}
    with AutonomyStore(home) as coordinator:
        wake = coordinator.get_wake(wake_id)
        progress = wake.get("progress", {}).get("start")
        if not progress or progress["kind"] != "research":
            return {"allowed": False, "reason": "no_research_decision"}
        decision = progress["event"]["result"]["decision"]
        pending = core["state"].get("pending")
        if not pending or pending["id"] != decision["id"]:
            return {"allowed": False, "reason": "decision_not_pending"}
        authorized = coordinator.authorize_step(wake_id, step_id)
        return {**authorized, "kind": kind, "target": target,
            "scope": "Read public sources or run bounded read-only checks; host permissions still apply."}


def complete(home, wake_id, request, reconcile=False):
    if not isinstance(request, dict):
        raise PresenceError("Completion must be an object")
    allowed = {"status", "summary", "source_ids", "question", "notification", "feedback"}
    if set(request) - allowed or not {"status", "summary", "source_ids", "question"} <= set(request):
        raise PresenceError("Completion requires status, summary, source_ids and question")
    if request["status"] not in {"completed", "failed", "uncertain"}:
        raise PresenceError("Completion status must be completed, failed or uncertain")
    _text(request["summary"], "summary")
    _text(request["question"], "question", 1000)
    binding = _binding(home)
    source_ids = request["source_ids"]
    if not isinstance(source_ids, list) or not source_ids or len(source_ids) > 16:
        raise PresenceError("source_ids must list 1..16 original records")
    with PresenceStore(home) as presence:
        sources = [presence.read(item) for item in source_ids]
    notification = request.get("notification")
    if notification is not None:
        if not isinstance(notification, dict) or set(notification) != {"text", "source_ids"}:
            raise PresenceError("notification requires text and source_ids")
        _text(notification["text"], "notification text", 2000)
        if (not isinstance(notification["source_ids"], list) or not notification["source_ids"]
                or not set(notification["source_ids"]) <= set(source_ids)):
            raise PresenceError("Notification must cite this activity's sources")
    with AutonomyStore(home) as coordinator:
        coordinator.checkpoint(wake_id)  # Persist lease expiration before any new core effect.
        wake = coordinator.get_wake(wake_id)
        if reconcile and wake["status"] != "uncertain" and "reconcile_request" not in wake["progress"]:
            raise PresenceError("Only uncertain wakes can be reconciled", "WAKE_NOT_UNCERTAIN")
        if not reconcile and wake["status"] == "uncertain":
            if ((wake.get("result") or {}).get("status") == "uncertain"
                    and wake["progress"].get("completion_request") == request):
                return wake
            raise PresenceError("Resolve this uncertain wake with reconcile", "WAKE_UNCERTAIN")
        kind = wake["request"]["kind"]
        progress = wake["progress"].get("start")
        if not progress and reconcile:
            event = lookup_core_receipt(binding, wake_id + ":start")
            if event:
                progress = {"kind": kind, "event": event,
                            "source_ids": [f"core:{binding['life_id']}:{item}"
                                           for item in event["result"].get("memory_ids", [])]}
                coordinator.save_progress(wake_id, "start", progress)
        if not progress:
            raise PresenceError("Recover the start receipt before completing", "INCOMPLETE_START")
        phase = "reconcile" if reconcile else "completion"
        feedback_event = None
        if kind == "research":
            feedback = request.get("feedback")
            fields = {"success", "value", "harm", "text", "source_uri"}
            if not isinstance(feedback, dict) or set(feedback) != fields:
                raise PresenceError("Research feedback requires success/value/harm/text/source_uri")
            _text(feedback["text"], "feedback text")
            _text(feedback["source_uri"], "feedback source_uri", 2000)
            if request["status"] == "uncertain":
                if any(feedback[key] is not None for key in ("success", "value", "harm")):
                    raise PresenceError("Uncertain feedback needs null success, value and harm")
            elif (type(feedback["success"]) is not bool
                  or feedback["success"] != (request["status"] == "completed")
                  or any(type(feedback[key]) not in (int, float) or not math.isfinite(feedback[key])
                         for key in ("value", "harm"))
                  or not -1 <= feedback["value"] <= 1 or not 0 <= feedback["harm"] <= 1):
                raise PresenceError("Feedback signals must agree with status and use bounded finite numbers")
            if request["status"] == "completed" and not any(
                    item["provenance"] in {"OBSERVED", "REPORTED"} for item in sources):
                raise PresenceError("Completed research needs reported/observed evidence")
            decision = progress["event"]["result"]["decision"]
            feedback_request = {**feedback, "kind": "feedback", "decision_id": decision["id"],
                                "status": "unknown" if request["status"] == "uncertain" else request["status"]}
        elif request.get("feedback") is not None:
            raise PresenceError("Dreams/reflections do not accept numeric feedback")
        coordinator.save_progress(wake_id, phase + "_request", request)
        if kind == "research":
            prior = lookup_core_receipt(binding, wake_id + ":completion:feedback") if reconcile else None
            if prior and prior["request"]["status"] != "unknown":
                if prior["request"] != feedback_request:
                    raise PresenceError("Recorded feedback differs from reconciliation", "IDEMPOTENCY_CONFLICT")
                feedback_event = prior
            else:
                feedback_event = apply_core(binding, feedback_request, wake_id + ":" + phase + ":feedback")
            coordinator.save_progress(wake_id, phase + "_feedback", feedback_event)
        core = read_core(binding)
        with PresenceStore(home) as presence:
            import_memories(presence, core)
        if request["status"] == "completed":
            refs = ((feedback_event or progress["event"])["result"].get("memory_ids", []))[:16]
            question = {"kind": "question", "domain": "understand", "text": request["question"], "references": refs}
            if kind == "research":
                question["domain"] = progress["event"]["result"]["decision"]["selected"]["domain"]
            prior = lookup_core_receipt(binding, wake_id + ":completion:question") if reconcile else None
            if prior:
                if prior["request"] != question:
                    raise PresenceError("Recorded question differs from reconciliation", "IDEMPOTENCY_CONFLICT")
                event = prior
            else:
                event = apply_core(binding, question, wake_id + ":" + phase + ":question")
            coordinator.save_progress(wake_id, phase + "_question", event)
        result = {"status": request["status"], "kind": kind, "summary": request["summary"],
                  "source_ids": source_ids, "question": request["question"], "notification": notification}
        if request["status"] == "uncertain":
            result["notification"] = None
        receipt = coordinator.reconcile(wake_id, result) if reconcile else coordinator.finish(wake_id, result)
        with PresenceStore(home) as presence:
            presence.record("autonomy", wake_id + ":" + phase, "memory", request["summary"],
                            {"kind": "autonomy-result", "wake_id": wake_id, "source_ids": source_ids},
                            provenance="SIMULATED" if kind == "dream" else "INFERRED" if kind == "reflect" else "REPORTED")
        return receipt
