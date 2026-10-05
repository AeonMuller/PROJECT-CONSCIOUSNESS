"""Memory-grounded choice and causal use of observable execution estimates."""

from .capability import TOOLS, initial_model, model_bytes, model_estimates, update_model, validate_model
from .contracts import Config, LabError, clone, digest
from .memory import (
    AGENT_ID, append_record, memory_bytes, observation_record, retrieve_episodic,
    retrieve_history, validate_observation, validate_records, validate_tick,
)


_PREDICTION_FIELDS = {
    "intended_action", "tool", "probability_left", "probability_fast", "confidence",
    "predicted_target_left", "predicted_execution_success", "predicted_success",
    "capability_view", "expected_utilities",
}
_DECISION_FIELDS = _PREDICTION_FIELDS | {
    "action", "memory_ids", "encoded_ids", "records_scanned", "memory_bytes",
    "model_version", "model_hash", "model_bytes",
}


def initial_agent(config: Config) -> dict:
    return {"records": [], "capability": initial_model(config.capability_backend)}


def _copy_state(state: dict, tick: int, config: Config) -> dict:
    if not isinstance(state, dict) or set(state) != {"records", "capability"}:
        raise LabError("INVALID_INPUT", "capability agent state has unexpected fields")
    validate_records(state["records"], tick)
    validate_model(state["capability"], tick)
    if state["capability"]["backend"] != config.capability_backend:
        raise LabError("STATE_INCONSISTENT", "capability model backend differs from configuration")
    return clone(state)


def _read_cues(state: dict, observation: dict, tick: int, config: Config) -> tuple[list, int]:
    if observation["phase"] != "choice" or config.agent_mode == "reactive":
        return [], 0
    reader = retrieve_history if config.agent_mode == "history" else retrieve_episodic
    return reader(state["records"], observation["episode"], tick, config.read_mode)


def _visible_estimates(model: dict, read_mode: str) -> list:
    # The cut happens before the tool policy sees any model-derived quantity.
    return [0.5, 0.5] if read_mode == "blocked" else model_estimates(model)


def _tool_distribution(estimates: list, costs: list, decision_correct: float,
                       exploration: float) -> tuple[float, list]:
    """Only public numerical inputs; no intervention labels or model access."""
    utilities = [decision_correct * estimate - cost for estimate, cost in zip(estimates, costs)]
    probability_fast = (0.5 if utilities[0] == utilities[1] else
                        1.0 - exploration / 2 if utilities[0] > utilities[1] else exploration / 2)
    return probability_fast, utilities


def _select_tool(estimates: list, costs: list, decision_correct: float,
                 exploration: float, rng) -> tuple[str, float, list]:
    probability_fast, utilities = _tool_distribution(estimates, costs, decision_correct, exploration)
    tool = "fast" if rng.random() < probability_fast else "safe"
    return tool, probability_fast, utilities


def advance_agent(state: dict, observation: dict, tick: int, config: Config, rng) -> tuple[dict, dict]:
    validate_tick(tick)
    validate_observation(observation)
    result = _copy_state(state, tick, config)
    encoded_ids = []
    if config.write_enabled and config.agent_mode != "reactive" and observation["phase"] != "choice":
        record = observation_record(observation, tick)
        result["records"], added = append_record(result["records"], record, config.capacity, tick)
        if added:
            encoded_ids.append(record["record_id"])
    cues, scanned = _read_cues(result, observation, tick, config)
    model = result["capability"]
    decision = {
        "action": "wait", **dict.fromkeys(_PREDICTION_FIELDS),
        "memory_ids": [record["record_id"] for record in cues], "encoded_ids": encoded_ids,
        "records_scanned": scanned, "memory_bytes": memory_bytes(result["records"]),
        "model_version": model["updates"], "model_hash": digest(model), "model_bytes": model_bytes(model),
    }
    if observation["phase"] != "choice":
        return result, decision
    probability_left = float(cues[0]["value"] == 0) if cues else 0.5
    intended = (("left" if rng.random() < 0.5 else "right") if not cues else
                "left" if probability_left == 1.0 else "right")
    correct = probability_left if intended == "left" else 1.0 - probability_left
    view = _visible_estimates(model, config.capability_read_mode)
    tool, probability_fast, utilities = _select_tool(
        view, [config.fast_cost, config.safe_cost], correct, config.capability_exploration, rng)
    execution = view[TOOLS.index(tool)]
    success = correct * execution
    decision.update({
        "action": f"{intended}:{tool}", "intended_action": intended, "tool": tool,
        "probability_left": probability_left, "probability_fast": probability_fast,
        "confidence": success, "predicted_target_left": probability_left,
        "predicted_execution_success": execution, "predicted_success": success,
        "capability_view": view, "expected_utilities": utilities,
    })
    return result, decision


def _validate_feedback(state: dict, observation: dict, decision: dict, outcome: dict,
                       tick: int, config: Config) -> str:
    choice = observation["phase"] == "choice"
    if not isinstance(decision, dict) or set(decision) != _DECISION_FIELDS:
        raise LabError("INVALID_INPUT", "capability decision has unexpected fields")
    for field in ("records_scanned", "memory_bytes", "model_bytes", "model_version"):
        if type(decision[field]) is not int or decision[field] < 0:
            raise LabError("INVALID_INPUT", "decision counters must be nonnegative integers")
    if (not isinstance(outcome, dict)
            or set(outcome) != {"terminal", "success", "reward", "episode", "decision_correct", "execution_success", "tool", "cost"}
            or type(outcome["episode"]) is not int or outcome["episode"] != observation["episode"]
            or type(outcome["terminal"]) is not bool or outcome["terminal"] != choice
            or type(outcome["reward"]) not in (float, int) or type(outcome["cost"]) not in (float, int)):
        raise LabError("INVALID_INPUT", "capability feedback does not match the public contract")
    try:
        signature = digest({"observation": observation, "decision": decision, "outcome": outcome,
                            "tick": tick, "config": config.to_dict()})
    except (TypeError, ValueError) as error:
        raise LabError("INVALID_INPUT", "capability feedback must contain finite JSON") from error
    model = state["capability"]
    if (decision["model_version"] != model["updates"] or decision["model_hash"] != digest(model)
            or decision["model_bytes"] != model_bytes(model)
            or decision["memory_bytes"] != memory_bytes(state["records"])):
        raise LabError("STATE_INCONSISTENT", "decision must refer to its pre-feedback state")
    cues, scanned = _read_cues(state, observation, tick, config)
    if decision["memory_ids"] != [record["record_id"] for record in cues] or decision["records_scanned"] != scanned:
        raise LabError("INVALID_PROVENANCE", "decision cue differs from authorized memory")
    if not isinstance(decision["encoded_ids"], list):
        raise LabError("INVALID_INPUT", "encoded memory IDs must be a list")
    if choice:
        intended, tool = decision["intended_action"], decision["tool"]
        if not isinstance(intended, str) or intended not in ("left", "right") or not isinstance(tool, str) or tool not in TOOLS:
            raise LabError("INVALID_INPUT", "choice requires an intended side and tool")
        if decision["action"] != f"{intended}:{tool}" or decision["encoded_ids"]:
            raise LabError("STATE_INCONSISTENT", "choice action or encoded memory is inconsistent")
        if any(type(outcome[field]) is not bool for field in ("success", "decision_correct", "execution_success")):
            raise LabError("INVALID_INPUT", "terminal feedback flags must be boolean")
        for field in ("probability_left", "probability_fast", "confidence", "predicted_target_left",
                      "predicted_execution_success", "predicted_success"):
            if type(decision[field]) not in (float, int) or not 0 <= decision[field] <= 1:
                raise LabError("INVALID_INPUT", "choice probabilities must be numerical values in [0, 1]")
        for field in ("capability_view", "expected_utilities"):
            if (not isinstance(decision[field], list) or len(decision[field]) != 2
                    or any(type(value) not in (float, int) for value in decision[field])):
                raise LabError("INVALID_INPUT", "tool views must contain two numerical values")
        cost = config.fast_cost if tool == "fast" else config.safe_cost
        if (outcome["tool"] != tool or outcome["cost"] != cost
                or outcome["success"] != (outcome["decision_correct"] and outcome["execution_success"])
                or outcome["reward"] != float(outcome["success"]) - cost):
            raise LabError("STATE_INCONSISTENT", "tool, execution and decision feedback are inconsistent")
        left = float(cues[0]["value"] == 0) if cues else 0.5
        correct = left if intended == "left" else 1.0 - left
        if cues and correct != 1.0:
            raise LabError("STATE_INCONSISTENT", "intended side differs from the supplied cue policy")
        if cues and not outcome["decision_correct"]:
            raise LabError("STATE_INCONSISTENT", "decision feedback contradicts the fixed cue-to-side rule")
        view = _visible_estimates(model, config.capability_read_mode)
        probability_fast, utilities = _tool_distribution(
            view, [config.fast_cost, config.safe_cost], correct, config.capability_exploration)
        execution = view[TOOLS.index(tool)]
        expected = {
            "probability_left": left, "predicted_target_left": left,
            "probability_fast": probability_fast, "predicted_execution_success": execution,
            "predicted_success": correct * execution, "confidence": correct * execution,
            "capability_view": view, "expected_utilities": utilities,
        }
        if any(decision[key] != value for key, value in expected.items()):
            raise LabError("STATE_INCONSISTENT", "decision prediction differs from its pre-feedback view")
        if (probability_fast == 0 and tool == "fast") or (probability_fast == 1 and tool == "safe"):
            raise LabError("STATE_INCONSISTENT", "selected tool has zero policy probability")
    else:
        if decision["action"] != "wait" or any(decision[field] is not None for field in _PREDICTION_FIELDS):
            raise LabError("STATE_INCONSISTENT", "wait must not carry a choice or prediction")
        if (any(outcome[field] is not None for field in ("success", "decision_correct", "execution_success", "tool"))
                or outcome["cost"] != 0 or outcome["reward"] != 0):
            raise LabError("INVALID_INPUT", "wait must not carry terminal feedback")
        expected_id = f"observation:{tick}"
        if decision["encoded_ids"] not in ([], [expected_id]):
            raise LabError("INVALID_PROVENANCE", "encoded IDs must identify the current observation")
        if decision["encoded_ids"] and not any(record["record_id"] == expected_id for record in state["records"]):
            raise LabError("INVALID_PROVENANCE", "encoded observation is absent from state")
    return signature


def record_result(state: dict, observation: dict, decision: dict, outcome: dict, tick: int, config: Config) -> dict:
    """Consume feedback once from advance_agent's state; Runtime owns retries."""
    validate_tick(tick)
    validate_observation(observation)
    result = _copy_state(state, tick, config)
    signature = _validate_feedback(result, observation, decision, outcome, tick, config)
    if observation["phase"] == "choice" and config.capability_learning_enabled:
        result["capability"] = update_model(
            result["capability"], decision["tool"], outcome["execution_success"], tick,
            observation["episode"], config.capability_learning_rate, signature)
    if config.write_enabled and config.agent_mode != "reactive":
        record = {
            "record_id": f"action:{tick}", "episode": observation["episode"], "tick": tick,
            "kind": "outcome", "value": None, "source_kind": "OBSERVED",
            "origin_agent_id": AGENT_ID, "source_id": f"action:{tick}",
            "action": decision["action"], "result": outcome,
        }
        result["records"], _ = append_record(result["records"], record, config.capacity, tick)
    return result
