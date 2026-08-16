"""Core-safe reinforcement-learning contracts (L9).

The contracts deliberately carry data only.  They do not import a model
runtime or prescribe an RL algorithm; those belong to optional backends.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class State(_Frozen):
    values: dict[str, Any] = Field(default_factory=dict)
    terminal: bool = False


class Action(_Frozen):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class Trajectory(_Frozen):
    """A checked sequence of environment transitions.

    There is one more state than action, and one reward per action.
    """

    states: tuple[State, ...] = Field(min_length=1)
    actions: tuple[Action, ...] = ()
    rewards: tuple[float, ...] = ()

    @model_validator(mode="after")
    def _consistent_lengths(self) -> Trajectory:
        if len(self.states) != len(self.actions) + 1:
            raise ValueError("trajectory must contain exactly one more state than actions")
        if len(self.rewards) != len(self.actions):
            raise ValueError("trajectory must contain one reward per action")
        return self

    @property
    def total_reward(self) -> float:
        return sum(self.rewards)


class Episode(_Frozen):
    episode_id: str = Field(min_length=1)
    trajectory: Trajectory
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def total_reward(self) -> float:
        return self.trajectory.total_reward


class Environment(_Frozen):
    """Named, serializable environment identity; domain contracts extend it."""

    name: str = Field(min_length=1)
    version: str = "0.1.0"
    metadata: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class RewardFunction(Protocol):
    def reward(self, verifier_scores: dict[str, float]) -> float: ...


class Policy(_Frozen):
    """A serializable policy reference; a backend owns the executable policy."""

    name: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class RLBackendName(StrEnum):
    ART = "art"


class RLConfig(_Frozen):
    backend: RLBackendName = RLBackendName.ART
    algorithm: str = "grpo"
    max_steps: int = Field(default=1, ge=1, le=10_000)
    seed: int = 0


class RLResult(_Frozen):
    status: str
    backend: str
    episodes: tuple[Episode, ...] = ()
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class ReinforcementTrainer(Protocol):
    """Optional RL backends accept only OEC's stable RL contract types."""

    name: str

    def train(self, environment: Environment, episodes: tuple[Episode, ...]) -> RLResult: ...
