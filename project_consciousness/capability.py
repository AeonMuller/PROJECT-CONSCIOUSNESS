"""Persistent estimates of execution reliability, with two equivalent layouts.

These are engineering predictors of observable tool outcomes. Naming a layout
"self" does not establish introspection or a distinctive cognitive mechanism.
"""

import math

from .contracts import LabError, canonical, clone


TOOLS = ("fast", "safe")


def _probability(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _hash(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def initial_model(backend: str = "self") -> dict:
    if not isinstance(backend, str) or backend not in {"self", "generic"}:
        raise LabError("INVALID_INPUT", "unknown capability backend")
    probabilities = {"fast": 0.5, "safe": 0.5} if backend == "self" else [0.5, 0.5]
    return {"backend": backend, "probabilities": probabilities, "updates": 0, "last_update": None}


def validate_model(model: dict, tick: int | None = None) -> None:
    if tick is not None and (type(tick) is not int or tick < 0):
        raise LabError("INVALID_INPUT", "capability validation tick must be nonnegative")
    if not isinstance(model, dict) or set(model) != {"backend", "probabilities", "updates", "last_update"}:
        raise LabError("INVALID_INPUT", "capability model has unexpected fields")
    backend = model["backend"]
    values = model["probabilities"]
    if backend == "self":
        if not isinstance(values, dict) or set(values) != set(TOOLS):
            raise LabError("INVALID_INPUT", "self capability model requires fast and safe probabilities")
        values = [values[tool] for tool in TOOLS]
    elif backend == "generic":
        if not isinstance(values, list) or len(values) != 2:
            raise LabError("INVALID_INPUT", "generic capability model requires two probabilities")
    else:
        raise LabError("INVALID_INPUT", "unknown capability backend")
    if not all(_probability(value) for value in values):
        raise LabError("INVALID_INPUT", "capability estimates must be finite probabilities")
    if type(model["updates"]) is not int or model["updates"] < 0:
        raise LabError("INVALID_INPUT", "capability updates must be nonnegative")
    last = model["last_update"]
    if model["updates"] == 0:
        if last is not None or values != [0.5, 0.5]:
            raise LabError("STATE_INCONSISTENT", "untrained capabilities must retain their neutral prior")
        return
    if not isinstance(last, dict) or set(last) != {"tick", "episode", "input_hash"}:
        raise LabError("INVALID_INPUT", "trained capabilities require feedback lineage")
    for field in ("tick", "episode"):
        if type(last[field]) is not int or last[field] < 0:
            raise LabError("INVALID_INPUT", "capability feedback time must be nonnegative")
    if tick is not None and last["tick"] > tick:
        raise LabError("INVALID_PROVENANCE", "capability update is from a future tick")
    if not _hash(last["input_hash"]):
        raise LabError("INVALID_INPUT", "capability input_hash must be a SHA256 digest")


def model_estimates(model: dict) -> list:
    validate_model(model)
    probabilities = model["probabilities"]
    return [probabilities[tool] for tool in TOOLS] if model["backend"] == "self" else list(probabilities)


def model_bytes(model: dict) -> int:
    validate_model(model)
    return len(canonical(model).encode("utf-8"))


def update_model(model: dict, tool: str, execution_success: bool, tick: int,
                 episode: int, rate: float, input_hash: str) -> dict:
    """Update only the tool that supplied feedback; Runtime owns retries."""
    validate_model(model, tick)
    if type(tick) is not int or tick < 0 or type(episode) is not int or episode < 0:
        raise LabError("INVALID_INPUT", "capability feedback time must be nonnegative")
    if not isinstance(tool, str) or tool not in TOOLS or type(execution_success) is not bool:
        raise LabError("INVALID_INPUT", "capability learning requires tool execution feedback")
    if not _probability(rate) or rate == 0 or not _hash(input_hash):
        raise LabError("INVALID_INPUT", "capability rate or feedback hash is invalid")
    last = model["last_update"]
    if last is not None and (tick <= last["tick"] or episode <= last["episode"]):
        raise LabError("STALE_REVISION", "capability feedback must follow its previous update")
    result = clone(model)
    key = tool if model["backend"] == "self" else TOOLS.index(tool)
    old = result["probabilities"][key]
    result["probabilities"][key] = old + rate * (float(execution_success) - old)
    result["updates"] += 1
    result["last_update"] = {"tick": tick, "episode": episode, "input_hash": input_hash}
    validate_model(result, tick)
    return result
