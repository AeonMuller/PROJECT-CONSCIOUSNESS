"""Merge the optional presence hooks without granting Codex hook trust."""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import tempfile
import uuid

from .hooks import EVENTS
from .store import PresenceStore


OWNER_ARGUMENT = "--hook-owner=project-consciousness-presence"


def _path(value: str | Path, *, file: bool = False) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("An absolute path is required.")
    path = Path(value).expanduser().resolve()
    if file and not path.is_file():
        raise ValueError(f"Required file does not exist: {path}")
    return path


def _windows_command(arguments: list[str]) -> str:
    # An explicit PowerShell invocation works whether Codex's parent command
    # shell is cmd.exe or PowerShell. UTF-16 base64 avoids nested shell expansion
    # of $, quotes, &, and backticks in user-selected paths. All child arguments
    # remain literal strings. The installation report exposes the decoded argv.
    literal = lambda value: "'" + value.replace("'", "''") + "'"
    script = "& " + " ".join(literal(value) for value in arguments) + "; exit $LASTEXITCODE"
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return "powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand " + encoded


def _owned(handler: object) -> bool:
    if not isinstance(handler, dict) or handler.get("type") != "command":
        return False
    command = handler.get("command")
    if not isinstance(command, str):
        return False
    try:
        return OWNER_ARGUMENT in shlex.split(command)
    except ValueError:
        return False


def _merge(existing: dict, command: str, windows_command: str) -> dict:
    merged = deepcopy(existing)
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Existing hooks.json hooks must be an object; no changes made.")
    for event in EVENTS:
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"Existing {event} groups must be an array; no changes made.")
        retained = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError(f"Invalid existing {event} group; no changes made.")
            handlers = group["hooks"]
            kept = [handler for handler in handlers if not _owned(handler)]
            if len(kept) == len(handlers):
                retained.append(group)
            elif kept:
                retained.append({**group, "hooks": kept})
        handler = {
            "type": "command", "command": command, "commandWindows": windows_command,
            "timeout": 3 if event in ("Interrupt", "SessionEnd") else 30,
            "statusMessage": "PROJECT CONSCIOUSNESS presence",
        }
        if event in ("SessionStart", "UserPromptSubmit"):
            handler["additionalContextLimit"] = 5000
        retained.append({"hooks": [handler]})
        hooks[event] = retained
    return merged


def install_hooks(codex_home: str | Path, python: str | Path,
                  launcher: str | Path, home: str | Path) -> dict:
    """Install one user-level identity integration, preserving unrelated hooks.

    This writes hooks.json only. Features, managed policy and trust configuration
    remain the host's responsibility. New/changed definitions require user review.
    """
    codex = _path(codex_home)
    executable = _path(python, file=True)
    script = _path(launcher, file=True)
    presence_home = _path(home)
    with PresenceStore(presence_home) as store:
        binding = store.binding()
    if not binding:
        raise ValueError("Run presence setup before installing hooks.")
    project = _path(binding["project"])
    arguments = [str(executable), "-B", "-X", "utf8", str(script),
                 "--project", str(project), "--home", str(presence_home),
                 OWNER_ARGUMENT, "hook"]
    command = shlex.join(arguments)
    windows_command = _windows_command(arguments)
    destination = codex / "hooks.json"
    original = destination.read_bytes() if destination.exists() else None
    existing = json.loads(original.decode("utf-8-sig")) if original is not None else {}
    if not isinstance(existing, dict):
        raise ValueError("Existing hooks.json must be an object; no changes made.")
    merged = _merge(existing, command, windows_command)
    changed = existing != merged
    backup = None
    if changed:
        codex.mkdir(parents=True, exist_ok=True)
        if original is not None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = codex / f"hooks.json.presence-backup-{stamp}-{uuid.uuid4().hex[:8]}"
            with backup.open("xb") as output:
                output.write(original)
        content = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                             dir=codex, delete=False) as output:
                temp_path = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            # Refuse to overwrite another editor's work since the initial read.
            current = destination.read_bytes() if destination.exists() else None
            if current != original:
                raise ValueError("hooks.json changed during installation; retry after review.")
            os.replace(temp_path, destination)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    return {"path": str(destination), "changed": changed,
            "backup": str(backup) if backup else None, "events": list(EVENTS),
            "arguments": arguments, "trust_review_required": True,
            "host_activation_verified": False,
            "next_step": "Review these hooks in Codex /hooks; then test a fresh chat."}
