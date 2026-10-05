"""Two cue-specific estimates learned from public binary feedback.

The binary task structure is assumed: exactly one action is correct. Parameters
are engineering estimates, not a model of subjective certainty or consciousness.
"""

import math

from .contracts import LabError, canonical, clone


def initial_learner() -> dict:
    return {"q_left": [0.5, 0.5], "updates": 0, "last_update": None}


def _probability(value) -> bool:
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def validate_learner(learner: dict, as_of_tick: int | None = None) -> None:
    if as_of_tick is not None and (type(as_of_tick) is not int or as_of_tick < 0):
        raise LabError("INVALID_INPUT", "learner validation tick must be nonnegative")
    if not isinstance(learner, dict) or set(learner) != {"q_left", "updates", "last_update"}:
        raise LabError("INVALID_INPUT", "learner has unexpected fields")
    values = learner["q_left"]
    if not isinstance(values, list) or len(values) != 2 or not all(_probability(value) for value in values):
        raise LabError("INVALID_INPUT", "q_left must contain two finite probabilities")
    if type(learner["updates"]) is not int or learner["updates"] < 0:
        raise LabError("INVALID_INPUT", "learner updates must be a nonnegative integer")
    last = learner["last_update"]
    if learner["updates"] == 0:
        if last is not None or values != [0.5, 0.5]:
            raise LabError("STATE_INCONSISTENT", "an untrained learner must retain its neutral prior")
        return
    if not isinstance(last, dict) or set(last) != {"tick", "episode", "evidence_id", "input_hash"}:
        raise LabError("INVALID_INPUT", "trained learner requires last-update lineage")
    for key in ("tick", "episode"):
        if type(last[key]) is not int or last[key] < 0:
            raise LabError("INVALID_INPUT", "last-update time must be a nonnegative integer")
    if as_of_tick is not None and last["tick"] > as_of_tick:
        raise LabError("INVALID_PROVENANCE", "learner was updated in a future tick")
    evidence_id = last["evidence_id"]
    if not isinstance(evidence_id, str) or len(evidence_id) > 128 or not evidence_id.startswith("observation:"):
        raise LabError("INVALID_PROVENANCE", "learner evidence must identify an observation")
    suffix = evidence_id[len("observation:"):]
    if (not suffix.isascii() or not suffix.isdigit() or str(int(suffix)) != suffix
            or int(suffix) > last["tick"]):
        raise LabError("INVALID_PROVENANCE", "learner evidence tick is invalid")
    signature = last["input_hash"]
    if not isinstance(signature, str) or len(signature) != 64 or any(c not in "0123456789abcdef" for c in signature):
        raise LabError("INVALID_INPUT", "learner input_hash must be a SHA256 digest")


def learner_bytes(learner: dict) -> int:
    validate_learner(learner)
    return len(canonical(learner).encode("utf-8"))


def is_update_retry(learner: dict, tick: int, input_hash: str) -> bool:
    """An exact latest retry is inert; altered or older feedback is rejected.

    The runtime owns run-long event replay. This bounded lineage protects the
    learner even when its corresponding episodic outcome has been evicted.
    """
    last = learner["last_update"]
    if last is None or tick > last["tick"]:
        return False
    if tick < last["tick"]:
        raise LabError("STALE_REVISION", "feedback precedes the most recent learner update")
    if input_hash != last["input_hash"]:
        raise LabError("IDEMPOTENCY_CONFLICT", "learning tick reused with different feedback or decision")
    return True


def update_learner(learner: dict, *, cue: int, evidence_id: str, tick: int,
                   episode: int, action: str, success: bool, rate: float,
                   input_hash: str) -> dict:
    """Update one estimate after the caller verifies read-authorized evidence."""
    validate_learner(learner, tick)
    if type(tick) is not int or tick < 0 or type(episode) is not int or episode < 0:
        raise LabError("INVALID_INPUT", "learning tick and episode must be nonnegative integers")
    if type(cue) is not int or cue not in (0, 1):
        raise LabError("INVALID_INPUT", "learning cue must be binary")
    if type(success) is not bool or action not in ("left", "right"):
        raise LabError("INVALID_INPUT", "learning requires binary action feedback")
    if not _probability(rate) or rate == 0:
        raise LabError("INVALID_INPUT", "learning rate must be in (0, 1]")
    if is_update_retry(learner, tick, input_hash):
        return clone(learner)
    last = learner["last_update"]
    if last is not None and (episode <= last["episode"] or evidence_id == last["evidence_id"]):
        raise LabError("IDEMPOTENCY_CONFLICT", "an episode or evidence cannot update the model twice")
    result = clone(learner)
    target_left = float((action == "left") == success)
    result["q_left"][cue] += rate * (target_left - result["q_left"][cue])
    result["updates"] += 1
    result["last_update"] = {"tick": tick, "episode": episode,
                             "evidence_id": evidence_id, "input_hash": input_hash}
    validate_learner(result, tick)
    return result
