"""Bounded episodic records and experimental access interventions.

Provenance is a typed claim, not a cryptographic proof of origin. Only the
observation encoder creates own OBSERVED records during a normal run. Synthetic
SIMULATED/REPORTED records may be valid data, but cannot support an own cue.
"""

from .contracts import LabError, canonical, clone


AGENT_ID = "agent-0"
MAX_RECORD_BYTES = 4096
SOURCE_KINDS = {"OBSERVED", "INFERRED", "SIMULATED", "REPORTED", "INTERVENED"}
READ_MODES = {"intact", "sham", "block_all", "mask_relevant", "mask_irrelevant"}
_FIELDS = {
    "record_id", "episode", "tick", "kind", "value", "source_kind",
    "origin_agent_id", "source_id",
}


def validate_tick(tick: int) -> None:
    if type(tick) is not int or tick < 0:
        raise LabError("INVALID_INPUT", "tick must be a nonnegative integer")


def validate_observation(observation: dict) -> None:
    if not isinstance(observation, dict) or set(observation) != {"episode", "phase", "value"}:
        raise LabError("INVALID_INPUT", "observation must contain episode, phase and value only")
    if type(observation["episode"]) is not int or observation["episode"] < 0:
        raise LabError("INVALID_INPUT", "episode must be a nonnegative integer")
    phase = observation["phase"]
    if not isinstance(phase, str) or phase not in {"cue", "distractor", "choice"}:
        raise LabError("INVALID_INPUT", "unknown observation phase")
    if phase == "cue" and (type(observation["value"]) is not int or observation["value"] not in (0, 1)):
        raise LabError("INVALID_INPUT", "cue must be binary")
    if phase == "choice" and observation["value"] is not None:
        raise LabError("INVALID_INPUT", "choice must not expose a cue")
    try:
        canonical(observation)
    except (TypeError, ValueError) as error:
        raise LabError("INVALID_INPUT", "observation is not finite JSON data") from error


def validate_record(record: dict, as_of_tick: int) -> None:
    validate_tick(as_of_tick)
    if not isinstance(record, dict):
        raise LabError("INVALID_INPUT", "memory record must be an object")
    fields = _FIELDS | ({"action", "result"} if record.get("kind") == "outcome" else set())
    if set(record) != fields:
        raise LabError("INVALID_INPUT", "unexpected memory record fields")
    validate_tick(record["tick"])
    if record["tick"] > as_of_tick:
        raise LabError("INVALID_PROVENANCE", "memory record is from a future tick")
    if type(record["episode"]) is not int or record["episode"] < 0:
        raise LabError("INVALID_INPUT", "record episode must be nonnegative")
    if not isinstance(record["kind"], str) or record["kind"] not in {"cue", "distractor", "outcome"}:
        raise LabError("INVALID_INPUT", "unknown memory kind")
    if record["kind"] == "cue" and (type(record["value"]) is not int or record["value"] not in (0, 1)):
        raise LabError("INVALID_INPUT", "record cue must be binary")
    if not isinstance(record["source_kind"], str) or record["source_kind"] not in SOURCE_KINDS:
        raise LabError("INVALID_PROVENANCE", "unknown source kind")
    for key in ("record_id", "source_id", "origin_agent_id"):
        if not isinstance(record[key], str) or not 1 <= len(record[key]) <= 128:
            raise LabError("INVALID_PROVENANCE", f"{key} must be a nonempty short string")
    source_id = record["source_id"]
    for prefix in ("observation:", "action:"):
        if source_id.startswith(prefix):
            suffix = source_id[len(prefix):]
            if not suffix.isascii() or not suffix.isdigit() or str(int(suffix)) != suffix:
                raise LabError("INVALID_PROVENANCE", "source tick must be canonical")
            if int(suffix) > record["tick"]:
                raise LabError("INVALID_PROVENANCE", "source cannot occur after its record")
    if record["source_kind"] == "OBSERVED" and record["origin_agent_id"] == AGENT_ID:
        prefix = "action" if record["kind"] == "outcome" else "observation"
        if source_id != f"{prefix}:{record['tick']}":
            raise LabError("INVALID_PROVENANCE", "own observed source must match its event tick")
        if record["record_id"] != source_id:
            raise LabError("INVALID_PROVENANCE", "own observed record must retain its source ID")
    if record["kind"] == "outcome":
        if (not isinstance(record["action"], str) or record["action"] not in {"wait", "left", "right"}
                or not isinstance(record["result"], dict)):
            raise LabError("INVALID_INPUT", "outcome requires an action and result object")
        if record["value"] is not None:
            raise LabError("INVALID_INPUT", "outcome value must be null; feedback belongs in result")
    try:
        size = len(canonical(record).encode("utf-8"))
    except (TypeError, ValueError) as error:
        raise LabError("INVALID_INPUT", "memory must contain finite JSON data") from error
    if size > MAX_RECORD_BYTES:
        raise LabError("BUDGET_EXHAUSTED", "memory record exceeds 4 KiB")


def validate_records(records: list, as_of_tick: int) -> None:
    validate_tick(as_of_tick)
    if not isinstance(records, list) or len(records) > 4096:
        raise LabError("INVALID_INPUT", "records must be a bounded list")
    ids = set()
    previous_tick = -1
    for record in records:
        validate_record(record, as_of_tick)
        if record["record_id"] in ids:
            raise LabError("IDEMPOTENCY_CONFLICT", "duplicate memory record ID")
        ids.add(record["record_id"])
        if record["tick"] < previous_tick:
            raise LabError("STATE_INCONSISTENT", "memory records must be chronological")
        previous_tick = record["tick"]


def append_record(records: list, record: dict, capacity: int, as_of_tick: int) -> tuple[list, bool]:
    """Append once, or return an equal clone for an exact retained duplicate.

    The runtime owns run-long idempotency; memory duplicate detection lasts only
    while an event is retained. Old events are evicted FIFO when capacity fills.
    """
    validate_records(records, as_of_tick)
    validate_record(record, as_of_tick)
    if type(capacity) is not int or not 1 <= capacity <= 4096:
        raise LabError("INVALID_INPUT", "invalid memory capacity")
    for existing in records:
        if existing["record_id"] == record["record_id"]:
            if existing != record:
                raise LabError("IDEMPOTENCY_CONFLICT", "memory ID reused with different data")
            return clone(records[-capacity:]), False
    if records and record["tick"] < records[-1]["tick"]:
        raise LabError("STALE_REVISION", "cannot append memory from an earlier tick")
    return clone((records + [record])[-capacity:]), True


def observation_record(observation: dict, tick: int) -> dict:
    validate_tick(tick)
    validate_observation(observation)
    if observation["phase"] == "choice":
        raise LabError("INVALID_INPUT", "choice contains no observation to encode")
    return {
        "record_id": f"observation:{tick}", "episode": observation["episode"],
        "tick": tick, "kind": observation["phase"], "value": clone(observation["value"]),
        "source_kind": "OBSERVED", "origin_agent_id": AGENT_ID,
        "source_id": f"observation:{tick}",
    }


def _access_view(records: list, episode: int, read_mode: str) -> list:
    """Apply an intervention before a reader or selector can see records."""
    if not isinstance(read_mode, str) or read_mode not in READ_MODES:
        raise LabError("INVALID_INPUT", "unknown read mode")
    if read_mode == "block_all":
        return []
    if read_mode == "mask_relevant":
        return [record for record in records if not (record["episode"] == episode and record["kind"] == "cue")]
    if read_mode == "mask_irrelevant":
        masked = next((record["record_id"] for record in records
                       if record["episode"] == episode and record["kind"] == "distractor"), None)
        return [record for record in records if record["record_id"] != masked]
    return records


def retrieve_episodic(records: list, episode: int, tick: int, read_mode: str) -> tuple[list, int]:
    """Retrieve the latest own observed cue from this episode, with sources.

    records_scanned counts records inspected by the cognitive reader after the
    access intervention, excluding validation and intervention bookkeeping.
    """
    validate_records(records, tick)
    view = _access_view(records, episode, read_mode)
    candidates = [record for record in view if (
        record["episode"] == episode and record["kind"] == "cue"
        and record["source_kind"] == "OBSERVED" and record["origin_agent_id"] == AGENT_ID
    )]
    latest = max(candidates, key=lambda record: (record["tick"], record["record_id"]), default=None)
    return clone([latest] if latest is not None else []), len(view)


def retrieve_history(records: list, episode: int, tick: int, read_mode: str) -> tuple[list, int]:
    """Independent flat-history scan with the same budget and provenance rule."""
    validate_records(records, tick)
    latest = None
    scanned = 0
    for entry in _access_view(records, episode, read_mode):
        scanned += 1
        if entry["episode"] != episode or entry["kind"] != "cue":
            continue
        if entry["source_kind"] != "OBSERVED" or entry["origin_agent_id"] != AGENT_ID:
            continue
        if latest is None or (entry["tick"], entry["record_id"]) > (latest["tick"], latest["record_id"]):
            latest = entry
    return clone([latest] if latest is not None else []), scanned


def memory_bytes(records: list) -> int:
    return len(canonical(records).encode("utf-8"))
