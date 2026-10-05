"""Versioned reads and explicit operations for a v0.4 life in its recorded runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import zlib


class CoreError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _invoke(binding, operation=None, mode="--apply"):
    """Use explicit paths rather than whichever project happens to be the cwd."""
    project = Path(binding["project"]).resolve()
    if not (project / "project_consciousness" / "identity_runtime.py").is_file():
        raise CoreError("PROJECT_MISSING", f"Core checkout missing: {project}")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project)
    environment["PYTHONUTF8"] = "1"
    try:
        command = [binding["python"], "-B", "-P", "-m", "consciousness_presence.core", binding["life"]]
        if operation is not None:
            command.append(mode)
        result = subprocess.run(command, input=json.dumps(operation, ensure_ascii=False, allow_nan=False)
                                if operation is not None else None,
                                env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CoreError("CORE_UNAVAILABLE", str(error)) from error
    try:
        data = json.loads(result.stdout)
    except ValueError as error:
        raise CoreError("CORE_UNAVAILABLE", result.stderr[-2000:] or "Core returned no JSON") from error
    if result.returncode:
        failure = data.get("error", {})
        raise CoreError(failure.get("code", "CORE_UNAVAILABLE"), failure.get("message", "Core read failed"))
    if operation is not None:
        return data
    for key, actual in (("life_id", data["manifest"]["life_id"]), ("agent_id", data["state"]["agent_id"])):
        if binding.get(key) and binding[key] != actual:
            raise CoreError("IDENTITY_MISMATCH", f"Bound {key} differs from core")
    return data


def read_core(binding):
    return _invoke(binding)


def apply_core(binding, request, request_id, expected_revision=None):
    """Apply only a declared core operation, retaining the core's atomic receipts."""
    return _invoke(binding, {"request": request, "request_id": request_id,
                            "expected_revision": expected_revision,
                            "life_id": binding["life_id"], "agent_id": binding["agent_id"]})


def lookup_core_receipt(binding, request_id):
    return _invoke(binding, {"request_id": request_id, "life_id": binding["life_id"],
                             "agent_id": binding["agent_id"]}, mode="--receipt")


def _apply_v04(life_path, operation):
    from project_consciousness.identity_runtime import LifeRuntime
    with LifeRuntime.open(life_path) as runtime:
        if (runtime.manifest["life_id"] != operation["life_id"]
                or runtime.snapshot()["agent_id"] != operation["agent_id"]):
            raise CoreError("IDENTITY_MISMATCH", "Bound identity changed before application")
        return runtime.apply(operation["request"], operation["request_id"], operation["expected_revision"])


def _read_v04(life_path, receipt=None):
    # This adapter pins the v0.4 snapshot schema. All blobs are validated by the
    # existing exporter before historical memories are extracted in the same read.
    from project_consciousness import __version__ as core_version
    from project_consciousness.identity_runtime import LifeRuntime
    from project_consciousness.runtime import source_fingerprint

    path = Path(life_path).resolve()
    uri = (path / "identity.sqlite").as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, isolation_level=None, timeout=10) as db:
        db.execute("BEGIN")
        try:
            row = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
            if row is None:
                raise CoreError("STATE_INCONSISTENT", "Missing manifest")
            manifest = json.loads(row[0])
            if manifest.get("schema_version") != 1 or core_version != "0.4.0":
                raise CoreError("UNSUPPORTED_VERSION", "Presence bridge expects v0.4 schema 1")
            if manifest["source_hash"] != source_fingerprint() or manifest["package_version"] != core_version:
                raise CoreError("SOURCE_MISMATCH", "Bound checkout differs from the recorded life")
            if manifest["python"] != platform.python_version() or manifest["sqlite"] != sqlite3.sqlite_version:
                raise CoreError("RUNTIME_MISMATCH", "Use the life's recorded Python and SQLite versions")
            runtime = LifeRuntime(path, db, manifest)
            bundle = runtime.export_bundle()
            if receipt is not None:
                if (manifest["life_id"] != receipt["life_id"]
                        or bundle["state"]["agent_id"] != receipt["agent_id"]):
                    raise CoreError("IDENTITY_MISMATCH", "Bound identity differs")
                return next((event for event in bundle["events"]
                             if event["request_id"] == receipt["request_id"]), None)
            found = {}
            rows = db.execute(
                "SELECT ? AS revision, state_blob FROM origin UNION ALL "
                "SELECT revision, state_blob FROM events ORDER BY revision",
                (manifest["initial_revision"],),
            )
            for revision, blob in rows:
                for memory in json.loads(zlib.decompress(blob))["memories"]:
                    found.setdefault(memory["id"], {"memory": memory, "revision": revision})
            return {"state": bundle["state"], "manifest": bundle["manifest"],
                    "verification": bundle["verification"], "memories": list(found.values())}
        finally:
            db.rollback()


def import_memories(store, core):
    life_id = core["manifest"]["life_id"]
    for item in core["memories"]:
        memory = item["memory"]
        source = {"kind": "core-v0.4", "life_id": life_id, "revision": item["revision"],
                  "memory_id": memory["id"], "source_uri": memory["source_uri"],
                  "references": memory["references"], "domain": memory["domain"]}
        store.record(
            session_id=f"life:{life_id}", turn_id=memory["id"], role="memory", text=memory["text"],
            source=source, record_id=f"core:{life_id}:{memory['id']}",
            provenance=memory["source_kind"],
        )


if __name__ == "__main__":
    try:
        if sys.argv[2:] == ["--apply"]:
            result = _apply_v04(sys.argv[1], json.load(sys.stdin))
        elif sys.argv[2:] == ["--receipt"]:
            result = _read_v04(sys.argv[1], receipt=json.load(sys.stdin))
        else:
            result = _read_v04(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (ValueError, OSError, sqlite3.Error, KeyError, IndexError, zlib.error) as error:
        print(json.dumps({"error": {"code": getattr(error, "code", "CORE_UNAVAILABLE"),
                                    "message": str(error)}}, ensure_ascii=False))
        raise SystemExit(2)
