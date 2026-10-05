"""Durable conversation archive, presentation identity and sourced claims.

This sidecar never writes to the reproducible v0.4 cognitive engine. Text in this
archive is evidence/data, not executable instructions. Retrieval is lexical.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata


class PresenceError(ValueError):
    def __init__(self, message, code="INVALID_INPUT"):
        super().__init__(message)
        self.code = code


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise PresenceError("Value must contain JSON-compatible data") from error


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise PresenceError(f"{label} must be a nonempty string without NUL")
    return value


def _source(value):
    if isinstance(value, str):
        _identifier(value, "source")
    elif not isinstance(value, dict) or not value:
        raise PresenceError("source must be a nonempty string or JSON object")
    return json.loads(_json(value))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _id(prefix, value):
    return prefix + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _tokens(text):
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return set(re.findall(r"[^\W_]+", folded, flags=re.UNICODE))


def _limit(value):
    if type(value) is not int or not 1 <= value <= 100:
        raise PresenceError("limit must be an integer between 1 and 100")
    return value


class PresenceStore:
    """One SQLite database per identity, with transactions for all mutations.

    Use a separate instance/connection in each process or thread. SQLite handles
    concurrent writers. Receipts and their resulting mutations commit together.
    """

    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "presence.sqlite3"
        self.connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=30000")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS record_tokens (
                token TEXT NOT NULL, record_id TEXT NOT NULL REFERENCES records(id),
                PRIMARY KEY (token, record_id));
            CREATE TABLE IF NOT EXISTS naming (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS claims (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL, claim_key TEXT NOT NULL, active INTEGER NOT NULL,
                result TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS active_claim_key
                ON claims(subject, claim_key) WHERE active=1;
            CREATE TABLE IF NOT EXISTS receipts (
                kind TEXT NOT NULL, request_id TEXT NOT NULL, payload TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY (kind, request_id));
        """)
        with self._write():
            self.connection.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version', '1')")
            if self._metadata("schema_version") != 1:
                raise PresenceError("Unsupported presence store schema", "SCHEMA_MISMATCH")
            self.connection.execute("INSERT OR IGNORE INTO metadata VALUES ('enabled', 'true')")

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

    def _metadata(self, key, default=None):
        row = self.connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def _set_metadata(self, key, value):
        self.connection.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, _json(value)))

    def bind(self, binding):
        required = {"project", "life", "python", "skill", "life_id", "agent_id"}
        if not isinstance(binding, dict) or set(binding) != required:
            raise PresenceError("binding must have project, life, python, skill, life_id and agent_id")
        binding = dict(binding)
        for key in required:
            _identifier(binding[key], key)
        for key in ("project", "life", "python", "skill"):
            if not Path(binding[key]).is_absolute():
                raise PresenceError(f"{key} must be an absolute path")
            binding[key] = str(Path(binding[key]).resolve())
        with self._write():
            existing = self.binding()
            if existing is not None and existing != binding:
                raise PresenceError("This home is already bound; use another home for another binding", "BINDING_CONFLICT")
            self._set_metadata("binding", binding)
        return binding

    def binding(self):
        return self._metadata("binding")

    def enabled(self):
        return self._metadata("enabled", True)

    def set_enabled(self, enabled):
        if type(enabled) is not bool:
            raise PresenceError("enabled must be a boolean")
        with self._write():
            self._set_metadata("enabled", enabled)
        return {"enabled": enabled}

    def record(self, session_id, turn_id, role, text, source, record_id=None, provenance=None):
        for label, value in (("session_id", session_id), ("turn_id", turn_id), ("text", text)):
            _identifier(value, label)
        if role not in ("user", "assistant", "memory"):
            raise PresenceError("role must be user, assistant or memory")
        if provenance is None:
            provenance = "INFERRED" if role == "assistant" else "REPORTED"
        if provenance not in ("OBSERVED", "REPORTED", "INFERRED", "SIMULATED"):
            raise PresenceError("Invalid provenance")
        if record_id is None:
            record_id = _id("record-", [session_id, turn_id, role])
        _identifier(record_id, "record_id")
        payload = {"session_id": session_id, "turn_id": turn_id, "role": role,
                   "text": text, "source": _source(source), "provenance": provenance}
        encoded = _json(payload)
        with self._write():
            row = self.connection.execute("SELECT payload, result FROM records WHERE id=?", (record_id,)).fetchone()
            if row is not None:
                if row[0] != encoded:
                    raise PresenceError("record_id reused with different content", "IDEMPOTENCY_CONFLICT")
                return json.loads(row[1])
            result = {"id": record_id, **payload, "created_at": _now()}
            self.connection.execute("INSERT INTO records(id, payload, result) VALUES (?, ?, ?)",
                                    (record_id, encoded, _json(result)))
            self.connection.executemany("INSERT INTO record_tokens(token, record_id) VALUES (?, ?)",
                                        ((token, record_id) for token in sorted(_tokens(text))))
        return result

    def read(self, record_id):
        _identifier(record_id, "record_id")
        row = self.connection.execute("SELECT result FROM records WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise PresenceError("Unknown record_id: " + record_id, "NOT_FOUND")
        return json.loads(row[0])

    def recent(self, limit=8):
        rows = self.connection.execute("SELECT result FROM records ORDER BY sequence DESC LIMIT ?", (_limit(limit),))
        return [json.loads(row[0]) for row in rows]

    def search(self, query, limit=8):
        _identifier(query, "query")
        _limit(limit)
        tokens = sorted(_tokens(query))
        if not tokens:
            return []
        # Bounded SQL parameter count; a query is a retrieval request, not a full
        # transcript. The archive and matching record text remain complete.
        if len(tokens) > 256:
            raise PresenceError("query must contain at most 256 distinct lexical tokens")
        placeholders = ",".join("?" for _ in tokens)
        rows = self.connection.execute(f"""
            SELECT r.result, COUNT(*) AS matched FROM record_tokens t
            JOIN records r ON r.id=t.record_id WHERE t.token IN ({placeholders})
            GROUP BY r.id ORDER BY matched DESC, r.sequence DESC LIMIT ?
        """, [*tokens, limit])
        return [{**json.loads(row[0]), "matched_tokens": row[1]} for row in rows]

    def _replay(self, kind, request_id, payload):
        row = self.connection.execute("SELECT payload, result FROM receipts WHERE kind=? AND request_id=?",
                                      (kind, request_id)).fetchone()
        if row is None:
            return None
        if row[0] != _json(payload):
            raise PresenceError("request_id reused with different content", "IDEMPOTENCY_CONFLICT")
        return json.loads(row[1])

    def _receipt(self, kind, request_id, payload, result):
        self.connection.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                                (kind, request_id, _json(payload), _json(result)))

    def profile(self):
        history = [json.loads(row[0]) for row in self.connection.execute("SELECT result FROM naming ORDER BY sequence")]
        return {"display_name": history[-1]["display_name"] if history else None, "naming_history": history}

    def name(self, display_name, reason, source, request_id):
        for label, value in (("display_name", display_name), ("reason", reason), ("request_id", request_id)):
            _identifier(value, label)
        if len(display_name) > 128 or any(unicodedata.category(c).startswith("C") for c in display_name):
            raise PresenceError("display_name must be at most 128 characters without control characters")
        payload = {"display_name": display_name, "reason": reason, "source": _source(source)}
        with self._write():
            replay = self._replay("name", request_id, payload)
            if replay is not None:
                return replay
            event = {"id": _id("name-", request_id), **payload, "created_at": _now()}
            self.connection.execute("INSERT INTO naming(result) VALUES (?)", (_json(event),))
            result = self.profile()
            self._receipt("name", request_id, payload, result)
        return result

    def claim(self, subject, key, text, evidence_ids, request_id, supersedes=None):
        if subject not in ("user", "agent", "question"):
            raise PresenceError("subject must be user, agent or question")
        for label, value in (("key", key), ("text", text), ("request_id", request_id)):
            _identifier(value, label)
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise PresenceError("evidence_ids must be a nonempty list of original record IDs")
        for item in evidence_ids:
            _identifier(item, "evidence_id")
        evidence_ids = sorted(set(evidence_ids))
        if supersedes is not None:
            _identifier(supersedes, "supersedes")
        payload = {"subject": subject, "key": key, "text": text, "evidence_ids": evidence_ids,
                   "supersedes": supersedes}
        with self._write():
            replay = self._replay("claim", request_id, payload)
            if replay is not None:
                return replay
            evidence = [self.read(record_id) for record_id in evidence_ids]
            active = self.connection.execute("SELECT id, result FROM claims WHERE subject=? AND claim_key=? AND active=1",
                                             (subject, key)).fetchone()
            if supersedes is not None and (active is None or active[0] != supersedes):
                raise PresenceError("supersedes must identify the active claim for this subject/key", "CLAIM_CONFLICT")
            if active is not None and supersedes is None:
                current = json.loads(active[1])
                if current["text"] == text and current["evidence_ids"] == evidence_ids:
                    self._receipt("claim", request_id, payload, current)
                    return current
                raise PresenceError("An active claim exists; supply its ID in supersedes", "CLAIM_CONFLICT")
            result = {"id": _id("claim-", request_id), **payload, "provenance": "INFERRED",
                      "evidence_provenance": {item["id"]: item["provenance"] for item in evidence},
                      "created_at": _now()}
            if active is not None:
                self.connection.execute("UPDATE claims SET active=0 WHERE id=?", (active[0],))
            self.connection.execute("INSERT INTO claims(id, subject, claim_key, active, result) VALUES (?, ?, ?, 1, ?)",
                                    (result["id"], subject, key, _json(result)))
            self._receipt("claim", request_id, payload, result)
        return result

    def read_claim(self, claim_id):
        _identifier(claim_id, "claim_id")
        row = self.connection.execute("SELECT result, active FROM claims WHERE id=?", (claim_id,)).fetchone()
        if row is None:
            raise PresenceError("Unknown claim_id: " + claim_id, "NOT_FOUND")
        return {**json.loads(row[0]), "active": bool(row[1])}

    def claims(self, subject=None, include_superseded=False):
        if subject is not None and subject not in ("user", "agent", "question"):
            raise PresenceError("subject must be user, agent or question")
        if type(include_superseded) is not bool:
            raise PresenceError("include_superseded must be a boolean")
        sql = "SELECT result FROM claims WHERE 1=1" if include_superseded else "SELECT result FROM claims WHERE active=1"
        params = ()
        if subject is not None:
            sql += " AND subject=?"
            params = (subject,)
        return [json.loads(row[0]) for row in self.connection.execute(sql + " ORDER BY sequence", params)]

    def status(self):
        counts = {table: self.connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                  for table in ("records", "claims", "naming")}
        counts["active_claims"] = self.connection.execute("SELECT COUNT(*) FROM claims WHERE active=1").fetchone()[0]
        return {"home": str(self.home), "enabled": self.enabled(), "binding": self.binding(),
                "profile": self.profile(), "counts": counts}
