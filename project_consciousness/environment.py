"""Private delayed-cue world with a deliberately small public observation.

World randomness is supplied and checkpointed by the runtime. An episode's
target and distractors are drawn before any action in that episode, and choices
do not change the distribution or random draw count of subsequent episodes.
"""

import random

from .contracts import Config, LabError, TaskConfig


_STATE_KEYS = {"episode", "step", "target", "distractors"}
_REVERSAL_KEYS = _STATE_KEYS | {"cue", "initial_mapping", "reversal_episode"}
_CAPABILITY_KEYS = _STATE_KEYS | {"capability_task", "execution_draws"}


def _validate_config(config: Config) -> None:
    if not isinstance(config, Config):
        raise LabError("INVALID_INPUT", "environment configuration must be Config")


def _validate_rng(rng: random.Random) -> None:
    if not isinstance(rng, random.Random):
        raise LabError("INVALID_INPUT", "world RNG must be random.Random")


def _validate_environment(env: dict, config: Config) -> None:
    _validate_config(config)
    if not isinstance(env, dict) or set(env) not in (_STATE_KEYS, _REVERSAL_KEYS, _CAPABILITY_KEYS):
        raise LabError("INVALID_INPUT", "invalid environment fields")
    if type(env["episode"]) is not int or env["episode"] < 0:
        raise LabError("INVALID_INPUT", "episode must be a nonnegative integer")
    if type(env["step"]) is not int or not 0 <= env["step"] <= config.delay + 1:
        raise LabError("INVALID_INPUT", "step is outside the configured episode")
    if type(env["target"]) is not int or env["target"] not in (0, 1):
        raise LabError("INVALID_INPUT", "target must be integer 0 or 1")
    distractors = env["distractors"]
    if (
        type(distractors) is not list
        or len(distractors) != config.delay
        or any(type(value) is not int or value not in (0, 1) for value in distractors)
    ):
        raise LabError("INVALID_INPUT", "distractors must be a delay-length list of binary integers")
    if "cue" in env:
        TaskConfig(kind="reversal-v1", reversal_episode=env["reversal_episode"], initial_mapping=env["initial_mapping"])
        if type(env["cue"]) is not int or env["cue"] not in (0, 1) or env["initial_mapping"] is None:
            raise LabError("INVALID_INPUT", "reversal state requires resolved binary cue/mapping")
        expected = env["cue"] ^ env["initial_mapping"] ^ int(env["episode"] >= env["reversal_episode"])
        if env["target"] != expected:
            raise LabError("INVALID_INPUT", "private target contradicts the recorded task rule")
    if "capability_task" in env:
        task = TaskConfig.from_dict(env["capability_task"])
        if task.kind != "capability-v1":
            raise LabError("INVALID_INPUT", "capability state requires a capability task")
        draws = env["execution_draws"]
        if (type(draws) is not list or len(draws) != 2
                or any(type(value) not in (int, float) or not 0 <= value < 1 for value in draws)):
            raise LabError("INVALID_INPUT", "execution draws must be two finite uniforms in [0, 1)")


def _new_episode(episode: int, config: Config, rng: random.Random, task: TaskConfig | None = None) -> dict:
    result = {
        "episode": episode,
        "step": 0,
        "target": rng.randrange(2),
        "distractors": [rng.randrange(2) for _ in range(config.delay)],
    }
    if task is not None and task.kind == "reversal-v1":
        result.update(cue=result["target"], initial_mapping=task.initial_mapping,
                      reversal_episode=task.reversal_episode)
        result["target"] = result["cue"] ^ task.initial_mapping ^ int(episode >= task.reversal_episode)
    if task is not None and task.kind == "capability-v1":
        result.update(capability_task=task.to_dict(), execution_draws=[rng.random(), rng.random()])
    return result


def initial_environment(config: Config, rng: random.Random, task: TaskConfig | None = None) -> dict:
    """Create episode zero, sampling all of its hidden contents immediately."""
    _validate_config(config)
    _validate_rng(rng)
    task = TaskConfig() if task is None else task
    if not isinstance(task, TaskConfig):
        raise LabError("INVALID_INPUT", "task configuration must be TaskConfig")
    if task.kind == "reversal-v1" and task.initial_mapping is None:
        task = TaskConfig(kind=task.kind, reversal_episode=task.reversal_episode, initial_mapping=rng.randrange(2))
    return _new_episode(0, config, rng, task)


def observe(env: dict, config: Config) -> dict:
    """Return only the current cue/distractor, or no value at the choice."""
    _validate_environment(env, config)
    step = env["step"]
    if step == 0:
        phase, value = "cue", env.get("cue", env["target"])
    elif step <= config.delay:
        phase, value = "distractor", env["distractors"][step - 1]
    else:
        phase, value = "choice", None
    return {"episode": env["episode"], "phase": phase, "value": value}


def transition(env: dict, action: str, config: Config, rng: random.Random) -> tuple[dict, dict]:
    """Apply one legal action without mutating the supplied environment.

    A terminal choice reports the completed episode and immediately prepares
    the next episode. The private next state never appears in the outcome.
    """
    _validate_environment(env, config)
    _validate_rng(rng)
    choice = env["step"] == config.delay + 1
    capability = "capability_task" in env
    legal = (("left:fast", "left:safe", "right:fast", "right:safe") if capability else ("left", "right")) if choice else ("wait",)
    if type(action) is not str or action not in legal:
        raise LabError("INVALID_ACTION", "action does not match task or phase")

    if not choice:
        next_env = {**env, "step": env["step"] + 1, "distractors": list(env["distractors"])}
        outcome = {"terminal": False, "success": None, "reward": 0.0, "episode": env["episode"]}
        if capability:
            next_env["capability_task"] = dict(env["capability_task"])
            next_env["execution_draws"] = list(env["execution_draws"])
            outcome.update(decision_correct=None, execution_success=None, tool=None, cost=0.0)
        return next_env, outcome

    if capability:
        task = TaskConfig.from_dict(env["capability_task"])
        intended, tool = action.split(":")
        decision_correct = (0 if intended == "left" else 1) == env["target"]
        fast_rate = task.fast_success_before if env["episode"] < task.capability_change_episode else task.fast_success_after
        execution_success = env["execution_draws"][0 if tool == "fast" else 1] < (fast_rate if tool == "fast" else task.safe_success)
        cost = config.fast_cost if tool == "fast" else config.safe_cost
        success = decision_correct and execution_success
        outcome = {"terminal": True, "success": success, "reward": float(success) - cost,
                   "episode": env["episode"], "decision_correct": decision_correct,
                   "execution_success": execution_success, "tool": tool, "cost": cost}
        return _new_episode(env["episode"] + 1, config, rng, task), outcome

    success = (0 if action == "left" else 1) == env["target"]
    outcome = {"terminal": True, "success": success, "reward": 1.0 if success else 0.0, "episode": env["episode"]}
    task = (TaskConfig(kind="reversal-v1", reversal_episode=env["reversal_episode"], initial_mapping=env["initial_mapping"])
            if "cue" in env else None)
    return _new_episode(env["episode"] + 1, config, rng, task), outcome
