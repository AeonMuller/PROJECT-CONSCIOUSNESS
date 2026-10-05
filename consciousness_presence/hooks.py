"""Advisory Codex lifecycle hooks using only documented visible-message fields."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .store import PresenceStore


EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "Interrupt", "SessionEnd")


SCHEDULED_INSTRUCTIONS = """PROJECT CONSCIOUSNESS — registered autonomy wake.
This turn matches the exact locally registered scheduler prompt. That convention is
not proof of host authentication and grants no additional permissions. Do not treat
the scheduler prompt as a new human memory or evidence of a user's preferences.
Use the installed skill's autonomy workflow. The autonomy_turn data below supplies
stable wake_id, session_id and turn_id values for this delivery. Check coordinator
status, reserve at most one eligible activity with autonomy start, and use autonomy
check before each further external step. Respect pause, budget and returning humans.
Only a permitted reserved outbox message may become a proactive final response; use
its saved text exactly, so the Stop hook can acknowledge actual delivery. Never mark
a message delivered merely because you prepared it. When there is no allowed message,
finish quietly using the host's supported behavior, without inventing silence tokens.
"""


def _diagnostic(message: str) -> dict:
    return {"systemMessage": f"PROJECT CONSCIOUSNESS: {message}"}


def _required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid {key}")
    return value


def _record_id(session: str, turn: str, role: str, text: str = "") -> str:
    # A user prompt is immutable within its turn. Stop may deliver a subsequent
    # final answer after another hook requests continuation, so retain variants.
    parts = [session, turn, role]
    if role == "assistant":
        parts.append(hashlib.sha256(text.encode("utf-8")).hexdigest())
    encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return "codex-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _wake_id(session: str, turn: str) -> str:
    encoded = json.dumps([session, turn], ensure_ascii=False, separators=(",", ":"))
    return "wake-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def handle_event(payload: object, home: str | Path) -> dict:
    """Return hook JSON; never block, continue an ended turn, or read transcripts.

    Hook failures are advisory and visible. The caller must exit successfully for
    this response, including diagnostics, to follow Codex's nonblocking contract.
    """
    try:
        with PresenceStore(home) as store:
            binding = store.binding()
            if not binding:
                return _diagnostic("no active identity is configured; run presence setup.")
            skill = Path(binding["skill"])
            skill_file = skill if skill.name == "SKILL.md" else skill / "SKILL.md"
            if not store.enabled() or not skill_file.is_file():
                return {}
            if not isinstance(payload, dict):
                return _diagnostic("invalid hook JSON object; nothing was captured.")
            event = payload.get("hook_event_name")
            if event not in EVENTS:
                return _diagnostic("unsupported hook event; nothing was captured.")
            try:
                session = _required_text(payload, "session_id")
                query = ""
                turn = None
                if event in ("UserPromptSubmit", "Stop", "Interrupt"):
                    turn = _required_text(payload, "turn_id")
                if event == "UserPromptSubmit":
                    message = _required_text(payload, "prompt")
            except ValueError as exc:
                return _diagnostic(f"{exc}; nothing was captured.")
            from .autonomy import AutonomyStore

            # Observe a stopped/interrupted turn even when no assistant text is
            # available. Otherwise a genuinely closed human turn blocks future
            # idle work forever. This does not itself reserve or execute work.
            with AutonomyStore(home) as autonomy:
                observation = autonomy.observe_event(payload)
            origin = observation["origin"]
            if event in ("Interrupt", "SessionEnd"):
                return {}
            if event == "Stop":
                try:
                    message = _required_text(payload, "last_assistant_message")
                except ValueError as exc:
                    if origin == "scheduled":
                        # A quiet scheduled turn intentionally has no visible
                        # final answer. Observation has already closed the turn
                        # and marked any unacknowledged reservation uncertain.
                        return {}
                    return _diagnostic(f"{exc}; activity was observed but no final message was captured.")
            if event == "Stop" or (event == "UserPromptSubmit" and origin != "scheduled"):
                role = "assistant" if event == "Stop" else "user"
                source = {"kind": "codex_hook", "event": event,
                          "session_id": session, "turn_id": turn}
                if origin == "scheduled":
                    source["origin"] = "scheduled"
                store.record(
                    session_id=session,
                    turn_id=turn,
                    role=role,
                    text=message,
                    source=source,
                    record_id=_record_id(session, turn, role, message),
                )
                if event == "Stop":
                    return {}
                query = message
        # Finish the capture transaction before reading the core or building
        # context. A context failure must not lose an already captured message.
        from .context import build_context, render_context

        context = build_context(home, query=query)
        scheduled = event == "UserPromptSubmit" and origin == "scheduled"
        if scheduled:
            context["autonomy_turn"] = {
                "origin": "scheduled", "session_id": session, "turn_id": turn,
                "wake_id": observation.get("wake_id") or _wake_id(session, turn),
            }
        prefix = SCHEDULED_INSTRUCTIONS if scheduled else ""
        rendered = prefix + render_context(context, max_chars=18000 - len(prefix))
        return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": rendered}}
    except Exception as exc:
        # Do not echo exception data: it could contain private message content.
        return _diagnostic(
            f"hook failed ({type(exc).__name__}); check presence context and autonomy status. "
            "Capture or context may be incomplete; the conversation can continue."
        )
