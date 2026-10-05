#!/usr/bin/env python3
"""Portable presence CLI launcher; generated hooks always pass explicit paths."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def _bound_project(home: str | None) -> Path | None:
    location = home if home is not None else os.environ.get("PROJECT_CONSCIOUSNESS_PRESENCE_HOME")
    if location is not None and not location.strip():
        raise ValueError("Presence home cannot be empty.")
    presence_home = Path(location).expanduser().resolve() if location is not None else (
        Path.home() / ".project-consciousness" / "presence")
    database = presence_home / "presence.sqlite3"
    if not database.is_file():
        return None
    try:
        # Locate only the configured registry, never a database in the caller's
        # cwd. Read-only URI mode cannot create or modify a registry on lookup.
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT value FROM metadata WHERE key='binding'").fetchone()
        finally:
            connection.close()
        binding = json.loads(row[0]) if row is not None else None
        location = binding.get("project") if isinstance(binding, dict) else None
        if not isinstance(location, str) or not location.strip() or not Path(location).is_absolute():
            raise ValueError("The presence registry has no valid bound project; run setup explicitly.")
        return Path(location).resolve()
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        raise ValueError("The configured presence registry cannot be read; check its installation.") from exc


def resolve_project(explicit: str | None, home: str | None = None) -> Path:
    location = explicit if explicit is not None else os.environ.get("PROJECT_CONSCIOUSNESS_HOME")
    if location is not None:
        if not location.strip():
            raise ValueError("Project path cannot be empty.")
        candidates = [Path(location).expanduser().resolve()]
    else:
        bound = _bound_project(home)
        candidates = [bound] if bound is not None else list(Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "consciousness_presence" / "__main__.py").is_file():
            return candidate
    raise ValueError("Use --project PATH or PROJECT_CONSCIOUSNESS_HOME to locate the checkout.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the persistent presence CLI from any folder.")
    parser.add_argument("--project", metavar="PATH")
    parser.add_argument("--home", metavar="PATH")
    parser.add_argument("--hook-owner", help=argparse.SUPPRESS)
    parser.add_argument("presence_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    forwarded = args.presence_args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    hook_mode = forwarded == ["hook"]
    # Pipes on Windows must use the documented UTF-8 JSON format even when the
    # user's terminal encoding differs. The child inherits the same byte streams.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        if sys.version_info < (3, 12):
            raise ValueError("Python 3.12 or later is required.")
        project = resolve_project(args.project, args.home)
        environment = os.environ.copy()
        previous = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(project) + (os.pathsep + previous if previous else "")
        environment["PYTHONUTF8"] = "1"
        command = [sys.executable, "-B", "-P", "-m", "consciousness_presence"]
        if args.home is not None:
            command += ["--home", args.home]
        command += forwarded
        return subprocess.run(command, env=environment, check=False).returncode
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError) as exc:
        if hook_mode:
            print(json.dumps({"systemMessage": "PROJECT CONSCIOUSNESS launcher unavailable; "
                              "capture/context did not run. Check its project installation."}))
            return 0
        print(json.dumps({"error": {"code": "INVALID_PROJECT", "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
