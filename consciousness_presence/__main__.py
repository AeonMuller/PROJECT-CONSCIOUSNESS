"""Explicit operations and Codex hook entry point for conversational continuity."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .core import import_memories, read_core
from .paths import resolve_home
from .store import PresenceStore


def parser():
    root = argparse.ArgumentParser(description="Persistent conversational presence; no automatic core learning.")
    root.add_argument("--home", help="Private archive directory (defaults outside skill/checkout)")
    commands = root.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Bind an existing life without resetting it")
    for name in ("project", "life", "python", "skill"):
        setup.add_argument("--" + name, required=True)
    for command in ("status", "enable", "disable", "hook"):
        commands.add_parser(command)
    context = commands.add_parser("context")
    context.add_argument("--query", default="")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=8)
    read = commands.add_parser("read")
    read.add_argument("id")
    read_claim = commands.add_parser("read-claim")
    read_claim.add_argument("id")
    for command in ("record", "name", "claim"):
        request = commands.add_parser(command)
        request.add_argument("--request", required=True, help="UTF-8 JSON file with operation arguments")
    claims = commands.add_parser("claims")
    claims.add_argument("--subject", choices=("user", "agent", "question"))
    claims.add_argument("--all", action="store_true", help="Include superseded claims")
    install = commands.add_parser("install-hooks")
    install.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    install.add_argument("--launcher")
    autonomy = commands.add_parser("autonomy", help="Idle coordination and proactive delivery")
    operations = autonomy.add_subparsers(dest="operation", required=True)
    operations.add_parser("status")
    configure = operations.add_parser("configure")
    configure.add_argument("--request", required=True)
    register = operations.add_parser("register-prompt")
    register.add_argument("--file", required=True)
    for operation in ("start", "complete", "reconcile"):
        child = operations.add_parser(operation)
        child.add_argument("--wake-id", required=True)
        child.add_argument("--request", required=True)
    check = operations.add_parser("check")
    check.add_argument("--wake-id", required=True)
    check.add_argument("--step-id", required=True)
    check.add_argument("--kind", choices=("repo", "web"), required=True)
    check.add_argument("--target", required=True)
    outbox = operations.add_parser("outbox")
    outbox.add_argument("--session-id")
    outbox.add_argument("--turn-id")
    delivered = operations.add_parser("delivered")
    delivered.add_argument("--message-id", required=True)
    delivered.add_argument("--receipt", required=True, help="UTF-8 JSON file containing actual delivery evidence")
    close = operations.add_parser("close-turn")
    close.add_argument("--session-id", required=True)
    close.add_argument("--turn-id", required=True)
    close.add_argument("--reason", required=True)
    return root


def execute(args):
    home = resolve_home(args.home)
    if args.command == "autonomy":
        return execute_autonomy(home, args)
    if args.command == "hook":
        from .hooks import handle_event
        return handle_event(json.load(sys.stdin), home)
    if args.command == "context":
        from .context import build_context
        return build_context(home, args.query)
    if args.command == "setup":
        binding = {key: str(Path(getattr(args, key)).expanduser().resolve())
                   for key in ("project", "life", "python", "skill")}
        if not Path(binding["python"]).is_file():
            raise ValueError("--python must be an existing interpreter's absolute file path")
        if not (Path(binding["skill"]) / "SKILL.md").is_file():
            raise ValueError("--skill must be a directory containing SKILL.md")
        core = read_core(binding)
        binding.update(life_id=core["manifest"]["life_id"], agent_id=core["state"]["agent_id"])
        with PresenceStore(home) as store:
            store.bind(binding)
            import_memories(store, core)
            return {**store.status(), "home": str(home), "core_revision": core["state"]["revision"],
                    "host_activation": "pending hook installation/trust; setup alone does not capture chats"}
    if args.command == "install-hooks":
        from .install import install_hooks
        with PresenceStore(home) as store:
            binding = store.binding()
            if not binding:
                raise ValueError("Run setup first")
        launcher = args.launcher or str(Path(binding["skill"]) / "scripts" / "presence.py")
        return install_hooks(args.codex_home, binding["python"], launcher, home)
    with PresenceStore(home) as store:
        if args.command == "status":
            return {**store.status(), "home": str(home)}
        if not store.binding():
            raise ValueError("Run setup first")
        if args.command in ("enable", "disable"):
            store.set_enabled(args.command == "enable")
            return {"enabled": store.enabled()}
        if args.command == "search":
            return store.search(args.query, limit=args.limit)
        if args.command == "read":
            return store.read(args.id)
        if args.command == "read-claim":
            return store.read_claim(args.id)
        if args.command == "claims":
            return store.claims(subject=args.subject, include_superseded=args.all)
        if args.command in ("record", "name", "claim"):
            request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
            if not isinstance(request, dict):
                raise ValueError("Request must be a JSON object")
            return getattr(store, args.command)(**request)
    raise ValueError("Unknown command")


def execute_autonomy(home, args):
    from .autonomy import AutonomyStore
    from . import activity
    operation = args.operation
    request = None
    if getattr(args, "request", None):
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
    if operation == "start":
        return activity.start(home, args.wake_id, request)
    if operation in ("complete", "reconcile"):
        return activity.complete(home, args.wake_id, request, reconcile=operation == "reconcile")
    if operation == "check":
        return activity.check(home, args.wake_id, args.step_id, args.kind, args.target)
    with AutonomyStore(home) as coordinator:
        if operation == "status":
            return coordinator.status()
        if operation == "configure":
            return coordinator.configure(request)
        if operation == "register-prompt":
            return coordinator.register_prompt(Path(args.file).read_text(encoding="utf-8-sig"))
        if operation == "outbox":
            binding = activity._binding(home)
            if read_core(binding)["state"]["controls"]["paused"]:
                return None
            return coordinator.outbox(session_id=args.session_id, turn_id=args.turn_id)
        if operation == "delivered":
            return coordinator.delivered(args.message_id, json.loads(Path(args.receipt).read_text(encoding="utf-8-sig")))
        if operation == "close-turn":
            return coordinator.close_turn(args.session_id, args.turn_id, args.reason)
    raise ValueError("Unknown autonomy operation")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, sqlite3.Error) as error:
        failure = {"code": getattr(error, "code", "INVALID_INPUT"), "message": str(error)}
        if args.command == "hook":
            print(json.dumps({"systemMessage": "PROJECT CONSCIOUSNESS: " + failure["message"]}, ensure_ascii=False))
            return 0  # A failed memory write must not block the user's conversation.
        print(json.dumps({"error": failure}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
