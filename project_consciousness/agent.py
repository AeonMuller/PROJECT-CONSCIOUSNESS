"""A causal-memory policy over a public observation, with no hidden cue cache."""

from .contracts import Config, LabError, clone, digest
from .learning import initial_learner, is_update_retry, learner_bytes, update_learner, validate_learner
from .memory import (
    AGENT_ID, append_record, memory_bytes, observation_record, retrieve_episodic,
    retrieve_history, validate_observation, validate_records, validate_tick,
)


def initial_agent(config: Config | None = None) -> dict:
    config = config or Config()
    state = {"records": []}
    if config.policy_mode == "learned":
        state["learner"] = initial_learner()
    return state


def _copy_state(state: dict, tick: int, config: Config) -> dict:
    keys = {"records", "learner"} if config.policy_mode == "learned" else {"records"}
    if not isinstance(state, dict) or set(state) != keys:
        raise LabError("INVALID_INPUT", "agent state does not match the configured policy")
    validate_records(state["records"], tick)
    if "learner" in state:
        validate_learner(state["learner"], tick)
    return clone(state)


def _choose(phase: str, cues: list, rng) -> tuple[str, float | None, float | None]:
    """No intervention label, private world or configuration reaches policy."""
    if phase != "choice":
        return "wait", None, None
    if cues:
        probability_left = 1.0 if cues[0]["value"] == 0 else 0.0
        return ("left" if probability_left == 1.0 else "right"), probability_left, 1.0
    return ("left" if rng.random() < 0.5 else "right"), 0.5, 0.5


def _read_cues(state: dict, observation: dict, tick: int, config: Config) -> tuple[list, int]:
    if observation["phase"] != "choice" or config.agent_mode == "reactive":
        return [], 0
    reader = retrieve_history if config.agent_mode == "history" else retrieve_episodic
    return reader(state["records"], observation["episode"], tick, config.read_mode)


def _learned_prediction(learner: dict, phase: str, cues: list) -> tuple[float | None, dict | None]:
    if phase != "choice":
        return None, None
    if not cues:
        return 0.5, None
    evidence = {"cue": cues[0]["value"], "record_id": cues[0]["record_id"]}
    return learner["q_left"][evidence["cue"]], evidence


def _selection_probability(prediction: float) -> float:
    return 1.0 if prediction > 0.5 else 0.0 if prediction < 0.5 else 0.5


def advance_agent(state: dict, observation: dict, tick: int, config: Config, rng) -> tuple[dict, dict]:
    validate_tick(tick)
    validate_observation(observation)
    next_state = _copy_state(state, tick, config)
    encoded_ids = []
    if config.write_enabled and config.agent_mode != "reactive" and observation["phase"] != "choice":
        record = observation_record(observation, tick)
        next_state["records"], added = append_record(next_state["records"], record, config.capacity, tick)
        if added:
            encoded_ids.append(record["record_id"])
    cues, scanned = _read_cues(next_state, observation, tick, config)
    learned_fields = {}
    if config.policy_mode == "learned":
        learner = next_state["learner"]
        prediction, evidence = _learned_prediction(learner, observation["phase"], cues)
        if prediction is None:
            action, probability_left, confidence = "wait", None, None
        else:
            probability_left = _selection_probability(prediction)
            action = ("left" if rng.random() < 0.5 else "right") if probability_left == 0.5 else (
                "left" if probability_left == 1.0 else "right")
            confidence = prediction if action == "left" else 1.0 - prediction
        learned_fields = {"predicted_target_left": prediction, "predicted_success": confidence,
                          "model_version": learner["updates"], "model_hash": digest(learner),
                          "learning_evidence": evidence, "model_bytes": learner_bytes(learner)}
    else:
        action, probability_left, confidence = _choose(observation["phase"], cues, rng)
    decision = {
        "action": action, "probability_left": probability_left, "confidence": confidence,
        "memory_ids": [record["record_id"] for record in cues], "encoded_ids": encoded_ids,
        "records_scanned": scanned, "memory_bytes": memory_bytes(next_state["records"]),
        **learned_fields,
    }
    return next_state, decision


def record_result(state: dict, observation: dict, decision: dict, outcome: dict, tick: int, config: Config) -> dict:
    """Assimilate feedback into the pre-feedback state returned by advance_agent.

    Runtime.step owns persistent retries for all policies, including frozen
    models whose evidence may be evicted by an already-recorded outcome. The
    learner additionally guards its most recent actual parameter update.
    """
    validate_tick(tick)
    validate_observation(observation)
    next_state = _copy_state(state, tick, config)
    if config.policy_mode == "fixed" and (not config.write_enabled or config.agent_mode == "reactive"):
        return next_state
    if (not isinstance(decision, dict) or not isinstance(decision.get("action"), str)
            or decision["action"] not in {"wait", "left", "right"}):
        raise LabError("INVALID_INPUT", "invalid action result linkage")
    if not isinstance(outcome, dict):
        raise LabError("INVALID_INPUT", "outcome must be an object")
    if "episode" in outcome and outcome["episode"] != observation["episode"]:
        raise LabError("INVALID_INPUT", "outcome belongs to another episode")
    if (observation["phase"] == "choice") == (decision["action"] == "wait"):
        raise LabError("INVALID_INPUT", "action is incompatible with observation phase")
    if config.policy_mode == "learned":
        _assimilate_learning(next_state, observation, decision, outcome, tick, config)
    if not config.write_enabled or config.agent_mode == "reactive":
        return next_state
    record = {
        "record_id": f"action:{tick}", "episode": observation["episode"], "tick": tick,
        "kind": "outcome", "value": None, "source_kind": "OBSERVED",
        "origin_agent_id": AGENT_ID, "source_id": f"action:{tick}",
        "action": decision["action"], "result": outcome,
    }
    next_state["records"], _ = append_record(next_state["records"], record, config.capacity, tick)
    return next_state


def _assimilate_learning(state: dict, observation: dict, decision: dict, outcome: dict,
                         tick: int, config: Config) -> None:
    """Validate the locked decision and feedback before mutating the copied model."""
    choice = observation["phase"] == "choice"
    expected_fields = {"action", "probability_left", "confidence", "memory_ids", "encoded_ids",
                       "records_scanned", "memory_bytes", "predicted_target_left", "predicted_success",
                       "model_version", "model_hash", "learning_evidence", "model_bytes"}
    if set(decision) != expected_fields:
        raise LabError("INVALID_INPUT", "learned decision has unexpected fields")
    evidence = decision["learning_evidence"]
    if evidence is not None and (not isinstance(evidence, dict) or set(evidence) != {"cue", "record_id"}
            or type(evidence["cue"]) is not int or evidence["cue"] not in (0, 1)
            or not isinstance(evidence["record_id"], str)):
        raise LabError("INVALID_PROVENANCE", "learning evidence must identify one binary cue")
    for field in ("probability_left", "confidence", "predicted_target_left", "predicted_success"):
        if choice and type(decision[field]) not in (float, int):
            raise LabError("INVALID_INPUT", "choice probabilities must be numbers")
    for field in ("records_scanned", "memory_bytes", "model_bytes", "model_version"):
        if type(decision[field]) is not int or decision[field] < 0:
            raise LabError("INVALID_INPUT", "decision counters must be nonnegative integers")
    if (set(outcome) != {"episode", "terminal", "success", "reward"}
            or type(outcome["episode"]) is not int or outcome["episode"] != observation["episode"]
            or type(outcome["terminal"]) is not bool or outcome["terminal"] != choice
            or type(outcome["reward"]) not in (float, int)):
        raise LabError("INVALID_INPUT", "learning feedback must match the public outcome contract")
    if choice:
        if type(outcome["success"]) is not bool or outcome["reward"] != float(outcome["success"]):
            raise LabError("INVALID_INPUT", "terminal success must be boolean and consistent with reward")
    elif outcome["success"] is not None or outcome["reward"] != 0.0:
        raise LabError("INVALID_INPUT", "nonterminal feedback cannot carry a success or reward")
    try:
        input_hash = digest({"observation": observation, "decision": decision, "outcome": outcome,
                             "tick": tick, "config": config.to_dict()})
    except (TypeError, ValueError) as error:
        raise LabError("INVALID_INPUT", "learning feedback must be finite JSON") from error
    learner = state["learner"]
    if choice and config.learning_enabled and is_update_retry(learner, tick, input_hash):
        return
    cues, _ = _read_cues(state, observation, tick, config)
    prediction, evidence = _learned_prediction(learner, observation["phase"], cues)
    if decision.get("learning_evidence") != evidence or decision.get("memory_ids") != [c["record_id"] for c in cues]:
        raise LabError("INVALID_PROVENANCE", "learning evidence differs from the read-authorized decision cue")
    expected_probability = None if prediction is None else _selection_probability(prediction)
    expected_success = None if prediction is None else prediction if decision["action"] == "left" else 1 - prediction
    if (type(decision.get("model_version")) is not int or decision["model_version"] != learner["updates"]
            or decision.get("model_hash") != digest(learner)
            or decision.get("predicted_target_left") != prediction
            or decision.get("predicted_success") != expected_success
            or decision.get("confidence") != expected_success
            or decision.get("probability_left") != expected_probability
            or decision.get("model_bytes") != learner_bytes(learner)):
        raise LabError("STATE_INCONSISTENT", "decision prediction does not match the pre-feedback model")
    if choice and expected_probability != 0.5:
        expected_action = "left" if expected_probability == 1.0 else "right"
        if decision["action"] != expected_action:
            raise LabError("STATE_INCONSISTENT", "decision action does not match its declared policy")
    if choice and evidence is not None and config.learning_enabled:
        state["learner"] = update_learner(
            learner, cue=evidence["cue"], evidence_id=evidence["record_id"], tick=tick,
            episode=observation["episode"], action=decision["action"], success=outcome["success"],
            rate=config.learning_rate, input_hash=input_hash,
        )
