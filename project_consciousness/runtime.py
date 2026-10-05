"""Transactional execution, complete snapshots, branches and deterministic replay."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import uuid
import zlib

from . import __version__
from .agent import advance_agent, initial_agent, record_result
from .contracts import Config, LabError, TaskConfig, canonical, clone, digest, restore_rng, seeded_rng
from .environment import initial_environment, observe, transition


SCHEMA_VERSION = 1


def source_fingerprint() -> str:
    """Fingerprint executable package sources, excluding caches and generated data."""
    package = Path(__file__).parent
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.glob("*.py"))})


def _packed(value: dict) -> bytes:
    return zlib.compress(canonical(value).encode("utf-8"), level=1)


def _unpacked(value: bytes) -> dict:
    try:
        state = json.loads(zlib.decompress(value))
        if not isinstance(state, dict) or set(state) != {"tick", "agent", "environment", "rng", "config"}:
            raise ValueError("invalid snapshot fields")
        if type(state["tick"]) is not int or state["tick"] < 0:
            raise ValueError("invalid snapshot tick")
        if not all(isinstance(state[key], dict) for key in ("agent", "environment", "rng", "config")):
            raise ValueError("invalid snapshot component")
        if set(state["rng"]) != {"world", "policy"}:
            raise ValueError("invalid random streams")
        Config.from_dict(state["config"])
        return state
    except (zlib.error, ValueError, UnicodeError, TypeError) as error:
        raise LabError("STATE_INCONSISTENT", "snapshot cannot be decoded") from error


def _json_object(value: str, name: str) -> dict:
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError("expected an object")
        return result
    except (ValueError, TypeError) as error:
        raise LabError("STATE_INCONSISTENT", f"invalid {name} JSON object") from error


def _validate_manifest(manifest):
    required = {"schema_version", "package_version", "source_hash", "python", "sqlite", "run_id",
                "created_at_utc", "seed", "config", "config_hash", "initial_tick", "initial_hash", "parent", "task"}
    if set(manifest) != required:
        raise LabError("STATE_INCONSISTENT", "invalid manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise LabError("UNSUPPORTED_VERSION", "unsupported database schema")
    if type(manifest["initial_tick"]) is not int or manifest["initial_tick"] < 0:
        raise LabError("STATE_INCONSISTENT", "invalid origin tick")
    if type(manifest["seed"]) is not int or not 0 <= manifest["seed"] < 2**63:
        raise LabError("STATE_INCONSISTENT", "invalid recorded seed")
    if manifest["parent"] is not None and not isinstance(manifest["parent"], dict):
        raise LabError("STATE_INCONSISTENT", "invalid branch provenance")


def _inject_fault(stage: str, requested: str | None) -> None:
    if stage == requested:
        raise LabError("INJECTED_FAILURE", f"test fault at {stage}")


def _advance(before: dict) -> tuple[dict, dict]:
    """Compute on isolated values. The agent never receives the private bundle."""
    config = Config.from_dict(before["config"])
    world_rng = restore_rng(before["rng"]["world"])
    policy_rng = restore_rng(before["rng"]["policy"])
    observation = observe(clone(before["environment"]), config)
    agent, decision = advance_agent(clone(before["agent"]), observation, before["tick"], config, policy_rng)
    # Lock the prediction before the evaluator computes the consequence.
    decision = clone(decision)
    environment, outcome = transition(clone(before["environment"]), decision["action"], config, world_rng)
    agent = record_result(agent, observation, decision, outcome, before["tick"], config)
    after = clone({
        "tick": before["tick"] + 1,
        "agent": agent,
        "environment": environment,
        "rng": {"world": world_rng.getstate(), "policy": policy_rng.getstate()},
        "config": config.to_dict(),
    })
    trace = {
        "tick": before["tick"],
        "observation": observation,
        "decision": decision,
        "outcome": outcome,
        "state_hash": digest(after),
        "post_memory_bytes": len(canonical(agent["records"]).encode("utf-8")),
        "post_memory_records": len(agent["records"]),
    }
    if "learner" in agent:
        trace.update(post_model_hash=digest(agent["learner"]), post_model_version=agent["learner"]["updates"],
                     post_model_bytes=len(canonical(agent["learner"]).encode("utf-8")),
                     post_agent_bytes=len(canonical(agent).encode("utf-8")))
    return after, trace


def _event_hash(tick, input_hash, trace, before_hash, after_hash, previous_hash):
    return digest({"tick": tick, "input_hash": input_hash, "trace": trace,
                   "before_hash": before_hash, "after_hash": after_hash,
                   "previous_event_hash": previous_hash})


class Runtime:
    """One SQLite writer; a new object may resume the last committed boundary."""

    def __init__(self, path: Path, db: sqlite3.Connection, manifest: dict):
        self.path = path
        self._db = db
        self.manifest = manifest
        self._checked = False

    @classmethod
    def create(cls, path: str | Path, seed: int = 17, config: Config | None = None,
               task: TaskConfig | None = None) -> "Runtime":
        if type(seed) is not int or not 0 <= seed < 2**63:
            raise LabError("INVALID_INPUT", "seed must be an integer in [0, 2**63)")
        config = Config() if config is None else config
        if not isinstance(config, Config):
            raise LabError("INVALID_INPUT", "agent configuration must be Config")
        world = seeded_rng(seed, "world")
        policy = seeded_rng(seed, "policy")
        initial = clone({"tick": 0, "agent": initial_agent(config),
                         "environment": initial_environment(config, world, task),
                         "rng": {"world": world.getstate(), "policy": policy.getstate()},
                         "config": config.to_dict()})
        return cls._create(path, seed, initial, parent=None)

    @classmethod
    def _create(cls, path, seed, initial, parent) -> "Runtime":
        path = Path(path).resolve()
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise LabError("OUTPUT_EXISTS", f"refusing to overwrite {path}") from error
        manifest = {
            "schema_version": SCHEMA_VERSION, "package_version": __version__,
            "source_hash": source_fingerprint(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "run_id": str(uuid.uuid4()),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "seed": seed, "config": initial["config"], "config_hash": digest(initial["config"]),
            "initial_tick": initial["tick"], "initial_hash": digest(initial),
            "parent": parent, "task": "reversal-v1" if "cue" in initial["environment"] else "delayed-cue-v1",
        }
        db = sqlite3.connect(path / "run.sqlite", isolation_level=None, timeout=3)
        try:
            cls._configure(db)
            db.executescript("""
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE origin (id INTEGER PRIMARY KEY CHECK(id=1),
                                     state_blob BLOB NOT NULL, state_hash TEXT NOT NULL);
                CREATE TABLE events (
                    tick INTEGER PRIMARY KEY, input_hash TEXT NOT NULL,
                    trace_json TEXT NOT NULL, state_blob BLOB NOT NULL,
                    before_hash TEXT NOT NULL, after_hash TEXT NOT NULL,
                    previous_event_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
            """)
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT INTO metadata VALUES (?, ?)", [
                ("manifest", canonical(manifest)), ("manifest_hash", digest(manifest)),
                ("head_tick", str(initial["tick"])),
                ("head_hash", digest(initial)), ("head_event_hash", digest(initial))])
            db.execute("INSERT INTO origin VALUES (1, ?, ?)", (_packed(initial), digest(initial)))
            db.commit()
            (path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return cls(path, db, manifest)
        except BaseException:
            db.close()
            raise

    @staticmethod
    def _configure(db):
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=3000")

    @classmethod
    def open(cls, path: str | Path) -> "Runtime":
        path = Path(path).resolve()
        database = path / "run.sqlite"
        if not database.is_file():
            raise LabError("NOT_FOUND", f"no run database at {database}")
        db = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=3)
        try:
            cls._configure(db)
            row = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
            if row is None:
                raise LabError("STATE_INCONSISTENT", "missing manifest")
            manifest = _json_object(row[0], "manifest")
            _validate_manifest(manifest)
            return cls(path, db, manifest)
        except BaseException:
            db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._db.close()

    def _meta(self, key):
        row = self._db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        if row is None:
            raise LabError("STATE_INCONSISTENT", f"missing {key}")
        return row[0]

    def _check_engine(self):
        self._check_manifest()
        if self.manifest["source_hash"] != source_fingerprint():
            raise LabError("SOURCE_MISMATCH", "package sources differ from the recorded run; reconstruct remains available")
        if self.manifest["python"] != platform.python_version() or self.manifest["sqlite"] != sqlite3.sqlite_version:
            raise LabError("RUNTIME_MISMATCH", "Python/SQLite differ from the recorded runtime")

    def _check_manifest(self):
        recorded = _json_object(self._meta("manifest"), "manifest")
        _validate_manifest(recorded)
        if recorded != self.manifest or digest(recorded) != self._meta("manifest_hash"):
            raise LabError("STATE_INCONSISTENT", "manifest provenance hash mismatch")

    def snapshot(self, tick: int | None = None) -> dict:
        if tick is None:
            tick = int(self._meta("head_tick"))
        if type(tick) is not int or tick < self.manifest["initial_tick"]:
            raise LabError("INVALID_INPUT", "snapshot tick precedes the run origin")
        if tick == self.manifest["initial_tick"]:
            row = self._db.execute("SELECT state_blob, state_hash FROM origin WHERE id=1").fetchone()
        else:
            row = self._db.execute("SELECT state_blob, after_hash FROM events WHERE tick=?", (tick - 1,)).fetchone()
        if row is None:
            raise LabError("NOT_FOUND", f"no committed snapshot at tick {tick}")
        state = _unpacked(row[0])
        if digest(state) != row[1] or state["tick"] != tick:
            raise LabError("STATE_INCONSISTENT", "snapshot hash/tick mismatch")
        return state

    def step(self, expected_tick: int | None = None, fail_at: str | None = None) -> dict:
        if expected_tick is not None and (type(expected_tick) is not int or expected_tick < 0):
            raise LabError("INVALID_INPUT", "expected_tick must be nonnegative")
        if fail_at not in {None, "before_commit", "after_commit"}:
            raise LabError("INVALID_INPUT", "unknown fault injection point")
        self._check_engine()
        if not self._checked:
            integrity = self.verify("reconstruct")
            if not integrity["valid"]:
                raise LabError("STATE_INCONSISTENT", "; ".join(integrity["errors"]))
            self._checked = True
        try:
            self._db.execute("BEGIN IMMEDIATE")
            head = int(self._meta("head_tick"))
            tick = head if expected_tick is None else expected_tick
            if tick < head:
                row = self._db.execute("SELECT trace_json FROM events WHERE tick=?", (tick,)).fetchone()
                if row is None:
                    raise LabError("STALE_REVISION", "tick is not part of this branch")
                self._db.rollback()
                return _json_object(row[0], "trace")
            if tick != head:
                raise LabError("STALE_REVISION", f"expected next tick {head}, received {tick}")
            before = self.snapshot(head)
            before_hash = digest(before)
            if self._meta("head_hash") != before_hash:
                raise LabError("STATE_INCONSISTENT", "head hash differs from snapshot")
            input_hash = digest({"state_hash": before_hash, "config": before["config"]})
            after, trace = _advance(before)
            after_hash = digest(after)
            previous_hash = self._meta("head_event_hash")
            event_hash = _event_hash(tick, input_hash, trace, before_hash, after_hash, previous_hash)
            self._db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (tick, input_hash, canonical(trace), _packed(after), before_hash,
                              after_hash, previous_hash, event_hash))
            self._db.executemany("UPDATE metadata SET value=? WHERE key=?", [
                (str(tick + 1), "head_tick"), (after_hash, "head_hash"), (event_hash, "head_event_hash")])
            _inject_fault("before_commit", fail_at)
            self._db.commit()
            _inject_fault("after_commit", fail_at)
            return trace
        except BaseException:
            if self._db.in_transaction:
                self._db.rollback()
            raise

    def run(self, ticks: int) -> list[dict]:
        if type(ticks) is not int or ticks < 0:
            raise LabError("INVALID_INPUT", "ticks must be a nonnegative integer")
        return [self.step() for _ in range(ticks)]

    def traces(self) -> list[dict]:
        return [_json_object(row[0], "trace") for row in self._db.execute("SELECT trace_json FROM events ORDER BY tick")]

    def fork(self, path: str | Path, tick: int | None = None, overrides: dict | None = None) -> "Runtime":
        self._check_engine()
        verification = self.verify("reconstruct")
        if not verification["valid"]:
            raise LabError("STATE_INCONSISTENT", "cannot fork a corrupt run")
        state = self.snapshot(tick)
        overrides = {} if overrides is None else overrides
        if not isinstance(overrides, dict) or set(overrides) - {"read_mode", "write_enabled", "agent_mode", "learning_enabled"}:
            raise LabError("INVALID_INPUT", "forks only change reader, writer, agent mode or learning_enabled")
        if "learning_enabled" in overrides and state["config"].get("policy_mode", "fixed") != "learned":
            raise LabError("INVALID_INPUT", "learning intervention requires a learned policy")
        parent = {"run_id": self.manifest["run_id"], "path": str(self.path),
                  "tick": state["tick"], "state_hash": digest(state), "intervention": clone(overrides)}
        state["config"] = Config.from_dict({**state["config"], **overrides}).to_dict()
        return self._create(path, self.manifest["seed"], state, parent)

    def verify(self, mode: str = "recompute") -> dict:
        if mode not in {"reconstruct", "recompute"}:
            raise LabError("INVALID_INPUT", "mode must be reconstruct or recompute")
        errors = []
        verified = 0
        try:
            self._check_manifest()
            if mode == "recompute":
                self._check_engine()
            state = self.snapshot(self.manifest["initial_tick"])
            if digest(state) != self.manifest["initial_hash"]:
                raise LabError("STATE_INCONSISTENT", "origin differs from manifest")
            if state["config"] != self.manifest["config"] or digest(state["config"]) != self.manifest["config_hash"]:
                raise LabError("STATE_INCONSISTENT", "configuration differs from manifest")
            previous_hash = digest(state)
            for row in self._db.execute("SELECT tick,input_hash,trace_json,state_blob,before_hash,after_hash,previous_event_hash,event_hash FROM events ORDER BY tick"):
                tick, input_hash, trace_json, blob, before_hash, after_hash, prior, event_hash = row
                trace = _json_object(trace_json, "trace")
                after = _unpacked(blob)
                if tick != state["tick"] or before_hash != digest(state):
                    raise LabError("STATE_INCONSISTENT", f"broken sequence at tick {tick}")
                if after["tick"] != tick + 1 or after_hash != digest(after) or trace.get("state_hash") != after_hash:
                    raise LabError("STATE_INCONSISTENT", f"invalid state at tick {tick}")
                if input_hash != digest({"state_hash": before_hash, "config": state["config"]}):
                    raise LabError("STATE_INCONSISTENT", f"input differs at tick {tick}")
                if prior != previous_hash or event_hash != _event_hash(tick, input_hash, trace, before_hash, after_hash, prior):
                    raise LabError("STATE_INCONSISTENT", f"event hash differs at tick {tick}")
                if mode == "recompute":
                    computed, computed_trace = _advance(state)
                    if computed != after or computed_trace != trace:
                        raise LabError("STATE_INCONSISTENT", f"recomputation diverged at tick {tick}")
                previous_hash = event_hash
                state = after
                verified += 1
            if state["tick"] != int(self._meta("head_tick")) or digest(state) != self._meta("head_hash") or previous_hash != self._meta("head_event_hash"):
                raise LabError("STATE_INCONSISTENT", "head metadata differs from final event")
        except (LabError, ValueError, KeyError, TypeError, IndexError, AttributeError, sqlite3.Error) as error:
            errors.append(str(error))
        return {"valid": not errors, "ticks": verified, "mode": mode, "errors": errors}
