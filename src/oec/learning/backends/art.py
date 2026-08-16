"""Optional ART/GRPO reinforcement-learning adapter (L10)."""

from __future__ import annotations

import importlib
from typing import Any

from oec.learning.errors import BackendNotAvailableError
from oec.learning.rl import Environment, Episode, Policy, RLConfig, RLResult, Trajectory


class ARTBackend:
    """ART GRPO adapter.

    ART remains optional.  Importing this module is safe on a core-only
    installation; attempting to train without ART fails closed.
    """

    name = "art"
    algorithm = "grpo"

    def train(
        self,
        environment: Environment | Policy,
        episodes: tuple[Episode, ...] | Trajectory,
        config: RLConfig | None = None,
    ) -> RLResult:
        try:
            art: Any = importlib.import_module("art")
        except Exception as exc:
            raise BackendNotAvailableError(
                "ART backend requires the optional 'art' package",
                details={"backend": self.name, "algorithm": self.algorithm},
            ) from exc

        train_grpo = getattr(art, "train_grpo", None)
        if not callable(train_grpo):
            raise BackendNotAvailableError(
                "installed 'art' package does not expose train_grpo",
                details={"backend": self.name, "algorithm": self.algorithm},
            )
        if isinstance(episodes, Trajectory):
            episode_items: tuple[Episode, ...] = ()
        else:
            episode_items = episodes
        raw = train_grpo(environment=environment, episodes=episode_items, config=config)
        if isinstance(raw, RLResult):
            return raw
        metrics = raw if isinstance(raw, dict) else {}
        numeric_metrics = {
            key: float(value) for key, value in metrics.items() if isinstance(value, (int, float))
        }
        return RLResult(
            status="ok",
            backend=self.name,
            episodes=episode_items,
            metrics=numeric_metrics,
            message="ART GRPO training completed",
            details={"algorithm": self.algorithm},
        )
