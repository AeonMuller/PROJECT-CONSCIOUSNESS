"""Shared validated configuration and canonical, portable serialization."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random
from typing import Any


class LabError(ValueError):
    """A machine-readable error at a laboratory boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def clone(value: Any) -> Any:
    return json.loads(canonical(value))


def restore_rng(state: list | tuple) -> random.Random:
    def tuples(value):
        return tuple(tuples(item) for item in value) if isinstance(value, (tuple, list)) else value

    rng = random.Random()
    rng.setstate(tuples(state))
    return rng


def seeded_rng(seed: int, stream: str) -> random.Random:
    return random.Random(int(digest({"seed": seed, "stream": stream}), 16))


@dataclass(frozen=True)
class Config:
    delay: int = 3
    capacity: int = 64
    agent_mode: str = "episodic"
    read_mode: str = "intact"
    write_enabled: bool = True
    policy_mode: str = "fixed"
    learning_enabled: bool = True
    learning_rate: float = 0.25

    def __post_init__(self):
        if type(self.delay) is not int or not 1 <= self.delay <= 100:
            raise LabError("INVALID_INPUT", "delay must be an integer from 1 to 100")
        if type(self.capacity) is not int or not 1 <= self.capacity <= 4096:
            raise LabError("INVALID_INPUT", "capacity must be an integer from 1 to 4096")
        if not isinstance(self.agent_mode, str) or self.agent_mode not in {"episodic", "history", "reactive"}:
            raise LabError("INVALID_INPUT", "unknown agent_mode")
        if not isinstance(self.read_mode, str) or self.read_mode not in {"intact", "sham", "block_all", "mask_relevant", "mask_irrelevant"}:
            raise LabError("INVALID_INPUT", "unknown read_mode")
        if type(self.write_enabled) is not bool:
            raise LabError("INVALID_INPUT", "write_enabled must be boolean")
        if not isinstance(self.policy_mode, str) or self.policy_mode not in {"fixed", "learned"}:
            raise LabError("INVALID_INPUT", "unknown policy_mode")
        if type(self.learning_enabled) is not bool:
            raise LabError("INVALID_INPUT", "learning_enabled must be boolean")
        if (type(self.learning_rate) not in (int, float) or not 0 < self.learning_rate <= 1
                or not math.isfinite(self.learning_rate)):
            raise LabError("INVALID_INPUT", "learning_rate must be finite in (0, 1]")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        if not isinstance(data, dict):
            raise LabError("INVALID_INPUT", "configuration must be an object")
        try:
            return cls(**data)
        except TypeError as error:
            raise LabError("INVALID_INPUT", str(error)) from error


@dataclass(frozen=True)
class TaskConfig:
    """Private world construction settings; never passed to an agent."""

    kind: str = "delayed-cue-v1"
    reversal_episode: int = 40
    initial_mapping: int | None = None

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in {"delayed-cue-v1", "reversal-v1"}:
            raise LabError("INVALID_INPUT", "unknown task kind")
        if type(self.reversal_episode) is not int or not 1 <= self.reversal_episode <= 1000000:
            raise LabError("INVALID_INPUT", "reversal_episode must be an integer from 1 to 1000000")
        if self.initial_mapping is not None and (type(self.initial_mapping) is not int or self.initial_mapping not in (0, 1)):
            raise LabError("INVALID_INPUT", "initial_mapping must be null, 0 or 1")
        if self.kind == "delayed-cue-v1" and (self.initial_mapping is not None or self.reversal_episode != 40):
            raise LabError("INVALID_INPUT", "reversal settings require reversal-v1")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskConfig":
        if not isinstance(data, dict):
            raise LabError("INVALID_INPUT", "task configuration must be an object")
        try:
            return cls(**data)
        except TypeError as error:
            raise LabError("INVALID_INPUT", str(error)) from error
