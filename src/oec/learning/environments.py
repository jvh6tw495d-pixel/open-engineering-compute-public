"""Deterministic verifier-backed RL environments (L11)."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from oec.learning.rl import Environment


class EnvironmentName(StrEnum):
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    ELECTRICAL_ENGINEERING = "electrical_engineering"
    TOOL_USE = "tool_use"
    PYTHON = "python"


class EnvironmentSpec(Environment):
    name: EnvironmentName


class VerifierScores(Environment):
    """Raw outputs from deterministic verifiers; no model-judge field exists."""

    name: Literal["verifier_scores"] = "verifier_scores"
    correct: float = Field(default=0.0, ge=0.0)
    units: float = Field(default=0.0, ge=0.0)
    constraints: float = Field(default=0.0, ge=0.0)
    tokens: float = Field(default=0.0, ge=0.0)
    latency: float = Field(default=0.0, ge=0.0)


class RewardSpec(Environment):
    """A closed linear reward over normalized deterministic verifier scores.

    Every verifier supplies a deterministic score.  ``tokens`` and ``latency``
    are normalized efficiency scores (higher is better), so all weights remain
    simple non-negative contributions and the boundary stays free of LLM judges.
    """

    # Environment fields are overridden with a stable reward-contract identity.
    name: Literal["reward_spec"] = "reward_spec"
    correct: float = Field(
        default=1.0, ge=0.0, validation_alias=AliasChoices("correct", "w_correct")
    )
    units: float = Field(default=0.0, ge=0.0, validation_alias=AliasChoices("units", "w_units"))
    constraints: float = Field(
        default=0.0, ge=0.0, validation_alias=AliasChoices("constraints", "w_constraints")
    )
    tokens: float = Field(default=0.0, ge=0.0, validation_alias=AliasChoices("tokens", "w_tokens"))
    latency: float = Field(
        default=0.0, ge=0.0, validation_alias=AliasChoices("latency", "w_latency")
    )

    @model_validator(mode="after")
    def _has_signal(self) -> RewardSpec:
        if not any((self.correct, self.units, self.constraints, self.tokens, self.latency)):
            raise ValueError("at least one reward weight must be positive")
        return self

    def reward(self, verifier_scores: dict[str, float]) -> float:
        expected = {"correct", "units", "constraints", "tokens", "latency"}
        unknown = set(verifier_scores) - expected
        missing = expected - set(verifier_scores)
        if unknown or missing:
            raise ValueError(f"verifier scores must contain exactly {sorted(expected)}")
        for name, value in verifier_scores.items():
            is_valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            if not is_valid or value < 0.0:
                raise ValueError(f"verifier score {name!r} must be a non-negative number")
            if not math.isfinite(float(value)):
                raise ValueError(f"verifier score {name!r} must be finite")
        weights = {
            "correct": self.correct,
            "units": self.units,
            "constraints": self.constraints,
            "tokens": self.tokens,
            "latency": self.latency,
        }
        return sum(weights[name] * float(verifier_scores[name]) for name in weights)


class _VerifierEnvironment(Environment):
    reward_spec: RewardSpec = Field(default_factory=RewardSpec)

    def reward(self, verifier_scores: dict[str, float]) -> float:
        return self.reward_spec.reward(verifier_scores)


class MathematicsEnvironment(_VerifierEnvironment):
    name: Literal["mathematics"] = "mathematics"


class PhysicsEnvironment(_VerifierEnvironment):
    name: Literal["physics"] = "physics"


class ElectricalEngineeringEnvironment(_VerifierEnvironment):
    name: Literal["electrical_engineering"] = "electrical_engineering"


class ToolUseEnvironment(_VerifierEnvironment):
    name: Literal["tool_use"] = "tool_use"


def compute_reward(scores: VerifierScores | dict[str, float], spec: RewardSpec) -> float:
    """Compute a reward exclusively from deterministic verifier output."""

    if isinstance(scores, VerifierScores):
        payload = scores.model_dump(exclude={"name", "version", "metadata"})
    else:
        payload = scores
    return spec.reward(payload)
