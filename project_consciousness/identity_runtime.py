"""Transactional identities with recorded intentions, replay and causal branches.

Hashes detect accidental or partial alteration; they are not signatures against an
attacker able to rewrite the complete archive. No external action executes here.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3
import uuid
import zlib

from . import __version__
from .contracts import LabError, canonical, clone, digest
from .identity_state import initial_state, transition, validate_state
from .runtime import source_fingerprint


SCHEMA_VERSION = 1
_CONTROLS = {"learning_enabled", "preferences_visible", "aversion_visible", "dream_enabled", "paused"}
_MANIFEST_FIELDS = {"schema_version", "package_version", "source_hash", "python", "sqlite",
                    "life_id", "created_at_utc", "seed", "name", "initial_revision", "initial_hash", "parent"}


def _object(value, description):
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError("expected object")
        canonical(result)
        return result
    except (ValueError, TypeError, UnicodeError) as error:
        raise LabError("STATE_INCONSISTENT", f"invalid {description} JSON object") from error


def _packed(state):
    return zlib.compress(canonical(state).encode("utf-8"), level=1)


def _unpacked(blob):
    try:
        state = _object(zlib.decompress(blob), "identity snapshot")
        validate_state(state)
        return state
    except (LabError, zlib.error, ValueError, TypeError) as error:
        raise LabError("STATE_INCONSISTENT", "identity snapshot cannot be decoded or validated") from error


def _hex_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_manifest(manifest):
    if set(manifest) != _MANIFEST_FIELDS:
        raise LabError("STATE_INCONSISTENT", "invalid identity manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise LabError("UNSUPPORTED_VERSION", "unsupported identity database schema")
    if type(manifest["initial_revision"]) is not int or manifest["initial_revision"] < 0:
        raise LabError("STATE_INCONSISTENT", "invalid identity origin revision")
    if type(manifest["seed"]) is not int or not 0 <= manifest["seed"] < 2**63:
        raise LabError("STATE_INCONSISTENT", "invalid recorded identity seed")
    if not all(isinstance(manifest[key], str) and manifest[key] for key in
               ("package_version", "python", "sqlite", "life_id", "created_at_utc", "name")):
        raise LabError("STATE_INCONSISTENT", "invalid identity provenance")
    if not _hex_hash(manifest["source_hash"]) or not _hex_hash(manifest["initial_hash"]):
        raise LabError("STATE_INCONSISTENT", "invalid identity provenance hash")
    parent = manifest["parent"]
    if parent is not None:
        fields = {"life_id", "path", "revision", "state_hash", "intervention", "prior_controls"}
        if not isinstance(parent, dict) or set(parent) != fields:
            raise LabError("STATE_INCONSISTENT", "invalid identity parent provenance")
        if (type(parent["revision"]) is not int or parent["revision"] != manifest["initial_revision"]
                or not _hex_hash(parent["state_hash"])):
            raise LabError("STATE_INCONSISTENT", "invalid identity parent boundary")
        if not all(isinstance(parent[key], str) and parent[key] for key in ("life_id", "path")):
            raise LabError("STATE_INCONSISTENT", "invalid identity parent identifier")
        _validate_controls(parent["intervention"])
        _validate_controls(parent["prior_controls"], complete=True)


def _validate_controls(overrides, complete=False):
    if (not isinstance(overrides, dict) or set(overrides) - _CONTROLS
            or (complete and set(overrides) != _CONTROLS)
            or any(type(value) is not bool for value in overrides.values())):
        raise LabError("INVALID_INPUT", "identity branches change only declared boolean controls")


def _event_hash(event):
    return digest({key: value for key, value in event.items() if key != "event_hash"})


def _origin_anchor(manifest):
    return digest({"manifest_hash": digest(manifest), "origin_hash": manifest["initial_hash"]})


def _inject_fault(stage, requested):
    if stage == requested:
        raise LabError("INJECTED_FAILURE", f"test fault at {stage}")


class LifeRuntime:
    """Persist one identity; each intention commits its complete resulting state."""

    def __init__(self, path, db, manifest):
        self.path = path
        self._db = db
        self.manifest = manifest
        # Our own validated commits preserve integrity. An external SQLite commit
        # changes data_version and forces a complete chain check before mutation.
        self._checked_data_version = None

    @classmethod
    def create(cls, path, seed=17, name="Aeon", budget=100):
        state = initial_state(seed, name, budget)
        validate_state(state)
        return cls._create(path, state, parent=None)

    @classmethod
    def _create(cls, path, state, parent):
        validate_state(state)
        manifest = {
            "schema_version": SCHEMA_VERSION, "package_version": __version__,
            "source_hash": source_fingerprint(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "life_id": str(uuid.uuid4()),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "seed": state["seed"], "name": state["name"], "initial_revision": state["revision"],
            "initial_hash": digest(state), "parent": parent,
        }
        _validate_manifest(manifest)
        path = Path(path).resolve()
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise LabError("OUTPUT_EXISTS", f"refusing to overwrite {path}") from error
        db = sqlite3.connect(path / "identity.sqlite", isolation_level=None, timeout=10)
        try:
            cls._configure(db)
            db.executescript("""
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE origin (id INTEGER PRIMARY KEY CHECK(id=1),
                                     state_blob BLOB NOT NULL, state_hash TEXT NOT NULL);
                CREATE TABLE events (
                    revision INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                    request_json TEXT NOT NULL, result_json TEXT NOT NULL,
                    state_blob BLOB NOT NULL, before_hash TEXT NOT NULL,
                    after_hash TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
            """)
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT INTO metadata VALUES (?, ?)", [
                ("manifest", canonical(manifest)), ("manifest_hash", digest(manifest)),
                ("head_revision", str(state["revision"])), ("head_hash", digest(state)),
                ("head_event_hash", _origin_anchor(manifest)),
            ])
            db.execute("INSERT INTO origin VALUES (1, ?, ?)", (_packed(state), digest(state)))
            db.commit()
            (path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
            return cls(path, db, manifest)
        except sqlite3.Error as error:
            if db.in_transaction:
                db.rollback()
            db.close()
            raise LabError("STORAGE_ERROR", "cannot create identity database: " + str(error)) from error
        except BaseException:
            if db.in_transaction:
                db.rollback()
            db.close()
            raise

    @staticmethod
    def _configure(db):
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=10000")

    @classmethod
    def open(cls, path):
        path = Path(path).resolve()
        database = path / "identity.sqlite"
        if not database.is_file():
            raise LabError("NOT_FOUND", f"no identity database at {database}")
        db = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=10)
        try:
            cls._configure(db)
            row = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
            if row is None:
                raise LabError("STATE_INCONSISTENT", "missing identity manifest")
            manifest = _object(row[0], "identity manifest")
            _validate_manifest(manifest)
            return cls(path, db, manifest)
        except sqlite3.Error as error:
            db.close()
            raise LabError("STATE_INCONSISTENT", "cannot read identity database: " + str(error)) from error
        except BaseException:
            db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._db.close()

    @contextmanager
    def _read_transaction(self):
        owns_transaction = not self._db.in_transaction
        if owns_transaction:
            self._db.execute("BEGIN")
        try:
            yield
        finally:
            if owns_transaction:
                self._db.rollback()

    def _meta(self, key):
        row = self._db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        if row is None:
            raise LabError("STATE_INCONSISTENT", f"missing identity metadata {key}")
        return row[0]

    def _check_manifest(self):
        recorded = _object(self._meta("manifest"), "identity manifest")
        _validate_manifest(recorded)
        if recorded != self.manifest or digest(recorded) != self._meta("manifest_hash"):
            raise LabError("STATE_INCONSISTENT", "identity manifest provenance hash mismatch")
        try:
            external = _object((self.path / "manifest.json").read_text(encoding="utf-8"), "manifest file")
        except (OSError, UnicodeError) as error:
            raise LabError("STATE_INCONSISTENT", "identity manifest file is unavailable") from error
        if external != recorded:
            raise LabError("STATE_INCONSISTENT", "identity manifest file differs from database")

    def _check_engine(self):
        self._check_manifest()
        if self.manifest["source_hash"] != source_fingerprint() or self.manifest["package_version"] != __version__:
            raise LabError("SOURCE_MISMATCH", "identity sources/version differ; reconstruct remains available")
        if self.manifest["python"] != platform.python_version() or self.manifest["sqlite"] != sqlite3.sqlite_version:
            raise LabError("RUNTIME_MISMATCH", "Python/SQLite differ from the recorded identity runtime")

    def _origin(self):
        row = self._db.execute("SELECT state_blob, state_hash FROM origin WHERE id=1").fetchone()
        if row is None:
            raise LabError("STATE_INCONSISTENT", "missing identity origin")
        state = _unpacked(row[0])
        if (digest(state) != row[1] or row[1] != self.manifest["initial_hash"]
                or state["revision"] != self.manifest["initial_revision"]
                or state["seed"] != self.manifest["seed"] or state["name"] != self.manifest["name"]):
            raise LabError("STATE_INCONSISTENT", "identity origin differs from manifest")
        parent = self.manifest["parent"]
        if parent is None:
            if state["revision"] != 0:
                raise LabError("STATE_INCONSISTENT", "root identity must start at revision zero")
        else:
            original = clone(state)
            original["controls"] = parent["prior_controls"]
            expected_controls = {**parent["prior_controls"], **parent["intervention"]}
            if state["controls"] != expected_controls or digest(original) != parent["state_hash"]:
                raise LabError("STATE_INCONSISTENT", "branch origin differs from declared intervention")
        return state

    def _snapshot(self):
        try:
            head = int(self._meta("head_revision"))
        except ValueError as error:
            raise LabError("STATE_INCONSISTENT", "invalid identity head revision") from error
        if head == self.manifest["initial_revision"]:
            state = self._origin()
        else:
            row = self._db.execute("SELECT state_blob, after_hash FROM events WHERE revision=?", (head,)).fetchone()
            if row is None:
                raise LabError("STATE_INCONSISTENT", "missing identity head snapshot")
            state = _unpacked(row[0])
            if digest(state) != row[1] or state["revision"] != head:
                raise LabError("STATE_INCONSISTENT", "identity snapshot hash/revision mismatch")
        if digest(state) != self._meta("head_hash"):
            raise LabError("STATE_INCONSISTENT", "identity head hash differs from snapshot")
        return state

    def snapshot(self):
        try:
            with self._read_transaction():
                self._check_manifest()
                return self._snapshot()
        except sqlite3.Error as error:
            raise LabError("STATE_INCONSISTENT", "cannot read identity snapshot: " + str(error)) from error

    @staticmethod
    def _decode_event(row):
        revision, request_id, request_json, result_json, before_hash, after_hash, previous_hash, event_hash = row
        event = {"revision": revision, "request_id": request_id,
                 "request": _object(request_json, "identity request"),
                 "result": _object(result_json, "identity result"), "before_hash": before_hash,
                 "after_hash": after_hash, "previous_hash": previous_hash, "event_hash": event_hash}
        if (type(revision) is not int or revision < 1 or not isinstance(request_id, str)
                or not 1 <= len(request_id) <= 256 or event["result"].get("revision") != revision
                or any(not _hex_hash(event[key]) for key in
                       ("before_hash", "after_hash", "previous_hash", "event_hash"))
                or _event_hash(event) != event_hash):
            raise LabError("STATE_INCONSISTENT", f"invalid identity event at revision {revision}")
        return event

    def _event_rows(self):
        return self._db.execute("SELECT revision,request_id,request_json,result_json,before_hash,after_hash,"
                                "previous_hash,event_hash FROM events ORDER BY revision")

    def events(self):
        try:
            with self._read_transaction():
                self._check_manifest()
                return [self._decode_event(row) for row in self._event_rows()]
        except sqlite3.Error as error:
            raise LabError("STATE_INCONSISTENT", "cannot read identity events: " + str(error)) from error

    def export_bundle(self):
        """Capture a verified state and its history at one SQLite read boundary."""
        try:
            with self._read_transaction():
                verification = self._verify("reconstruct")
                if not verification["valid"]:
                    raise LabError("STATE_INCONSISTENT", "cannot export a corrupt identity: "
                                   + "; ".join(verification["errors"]))
                return {"state": self._snapshot(), "events": [self._decode_event(row) for row in self._event_rows()],
                        "manifest": clone(self.manifest), "verification": verification}
        except sqlite3.Error as error:
            raise LabError("STATE_INCONSISTENT", "cannot export identity archive: " + str(error)) from error

    def apply(self, request, request_id, expected_revision=None, fail_at=None):
        if not isinstance(request, dict):
            raise LabError("INVALID_INPUT", "identity request must be a JSON object")
        try:
            request = clone(request)
        except (ValueError, TypeError) as error:
            raise LabError("INVALID_INPUT", "identity request must contain finite JSON values") from error
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 256:
            raise LabError("INVALID_INPUT", "request_id must contain 1 to 256 characters")
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
            raise LabError("INVALID_INPUT", "expected_revision must be a nonnegative integer")
        if fail_at not in {None, "before_commit", "after_commit"}:
            raise LabError("INVALID_INPUT", "unknown fault injection point")
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._check_engine()
            data_version = self._db.execute("PRAGMA data_version").fetchone()[0]
            if data_version != self._checked_data_version:
                integrity = self._verify("reconstruct")
                if not integrity["valid"]:
                    raise LabError("STATE_INCONSISTENT", "; ".join(integrity["errors"]))
                self._checked_data_version = data_version
            row = self._db.execute(
                "SELECT revision,request_id,request_json,result_json,before_hash,after_hash,previous_hash,event_hash "
                "FROM events WHERE request_id=?", (request_id,)).fetchone()
            if row is not None:
                event = self._decode_event(row)
                if canonical(event["request"]) != canonical(request):
                    raise LabError("IDEMPOTENCY_CONFLICT", "request_id already belongs to a different payload")
                self._db.rollback()
                return event
            before = self._snapshot()
            if expected_revision is not None and expected_revision != before["revision"]:
                raise LabError("STALE_REVISION", f"expected revision {expected_revision}; current is {before['revision']}")
            after, result = transition(before, request)
            validate_state(after)
            if (after["revision"] != before["revision"] + 1 or not isinstance(result, dict)
                    or result.get("revision") != after["revision"]):
                raise LabError("STATE_INCONSISTENT", "identity transition produced an invalid revision")
            event = {"revision": after["revision"], "request_id": request_id,
                     "request": request, "result": result, "before_hash": digest(before),
                     "after_hash": digest(after), "previous_hash": self._meta("head_event_hash")}
            event["event_hash"] = _event_hash(event)
            self._db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (event["revision"], request_id, canonical(request), canonical(result), _packed(after),
                              event["before_hash"], event["after_hash"], event["previous_hash"], event["event_hash"]))
            self._db.executemany("UPDATE metadata SET value=? WHERE key=?", [
                (str(after["revision"]), "head_revision"), (event["after_hash"], "head_hash"),
                (event["event_hash"], "head_event_hash"),
            ])
            _inject_fault("before_commit", fail_at)
            self._db.commit()
            _inject_fault("after_commit", fail_at)
            return clone(event)
        except sqlite3.Error as error:
            if self._db.in_transaction:
                self._db.rollback()
            raise LabError("STORAGE_ERROR", "cannot commit identity request: " + str(error)) from error
        except BaseException:
            if self._db.in_transaction:
                self._db.rollback()
            raise

    def run(self, cycles):
        if type(cycles) is not int or not 0 <= cycles <= 10000:
            raise LabError("INVALID_INPUT", "cycles must be an integer from 0 to 10000")
        events = []
        while len(events) < cycles:
            state = self.snapshot()
            if state["controls"]["paused"] or state["budget_remaining"] == 0 or state["pending"] is not None:
                break
            try:
                event = self.apply({"kind": "cycle"}, "cycle-" + str(uuid.uuid4()),
                                   expected_revision=state["revision"])
            except LabError as error:
                if error.code == "STALE_REVISION":
                    continue
                raise
            events.append(event)
        return events

    def fork(self, path, overrides=None):
        overrides = {} if overrides is None else overrides
        _validate_controls(overrides)
        overrides = clone(overrides)
        with self._read_transaction():
            self._check_engine()
            integrity = self._verify("reconstruct")
            if not integrity["valid"]:
                raise LabError("STATE_INCONSISTENT", "cannot branch a corrupt identity: " + "; ".join(integrity["errors"]))
            state = self._snapshot()
            parent = {"life_id": self.manifest["life_id"], "path": str(self.path),
                      "revision": state["revision"], "state_hash": digest(state),
                      "intervention": overrides, "prior_controls": clone(state["controls"])}
            state["controls"].update(overrides)
        return self._create(path, state, parent)

    def _verify(self, mode):
        errors = []
        verified = 0
        try:
            self._check_manifest()
            if mode == "recompute":
                self._check_engine()
            state = self._origin()
            if mode == "recompute" and self.manifest["parent"] is None:
                expected = initial_state(state["seed"], state["name"], state["budget_remaining"])
                if expected != state:
                    raise LabError("STATE_INCONSISTENT", "identity origin initialization diverged")
            previous_hash = _origin_anchor(self.manifest)
            for row in self._event_rows():
                event = self._decode_event(row)
                revision = event["revision"]
                if revision != state["revision"] + 1 or event["before_hash"] != digest(state):
                    raise LabError("STATE_INCONSISTENT", f"broken identity sequence at revision {revision}")
                if event["previous_hash"] != previous_hash:
                    raise LabError("STATE_INCONSISTENT", f"broken identity event chain at revision {revision}")
                blob = self._db.execute("SELECT state_blob FROM events WHERE revision=?", (revision,)).fetchone()[0]
                after = _unpacked(blob)
                if after["revision"] != revision or digest(after) != event["after_hash"]:
                    raise LabError("STATE_INCONSISTENT", f"invalid identity state at revision {revision}")
                if mode == "recompute":
                    computed, result = transition(state, event["request"])
                    if computed != after or result != event["result"]:
                        raise LabError("STATE_INCONSISTENT", f"identity recomputation diverged at revision {revision}")
                state = after
                previous_hash = event["event_hash"]
                verified += 1
            if (state["revision"] != int(self._meta("head_revision")) or digest(state) != self._meta("head_hash")
                    or previous_hash != self._meta("head_event_hash")):
                raise LabError("STATE_INCONSISTENT", "identity head metadata differs from final event")
        except (LabError, ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, sqlite3.Error) as error:
            errors.append(str(error))
        return {"valid": not errors, "events": verified, "mode": mode, "errors": errors}

    def verify(self, mode="recompute"):
        if mode not in {"reconstruct", "recompute"}:
            raise LabError("INVALID_INPUT", "mode must be reconstruct or recompute")
        try:
            with self._read_transaction():
                return self._verify(mode)
        except sqlite3.Error as error:
            return {"valid": False, "events": 0, "mode": mode, "errors": [str(error)]}
