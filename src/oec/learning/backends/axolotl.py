"""L8 — Axolotl recipe backend (fail-closed until extra exists)."""

from __future__ import annotations

from typing import Any

from oec.learning.contracts import (
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.errors import BackendNotAvailableError
from oec.learning.experiments import LearningExperiment


class AxolotlBackend:
    name = FineTuneBackendName.AXOLOTL

    def finetune(
        self,
        model: ModelRef,
        dataset: LearningDataset,
        config: TrainingConfig,
    ) -> TrainingResult:
        _ = (model, dataset, config)
        try:
            import axolotl  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            raise BackendNotAvailableError(
                "axolotl is not installed; L8 adapter is fail-closed",
                details={"backend": "axolotl", "error_type": type(exc).__name__},
            ) from exc
        raise BackendNotAvailableError(
            "axolotl is importable but the OEC adapter is not wired yet",
            details={"backend": "axolotl"},
        )


def recipe_to_experiment(recipe: dict[str, Any], *, experiment_id: str) -> LearningExperiment:
    """Translate a declarative recipe into an OEC LearningExperiment (no execution)."""
    model_id = str(recipe.get("base_model") or recipe.get("model") or "unknown")
    texts = recipe.get("datasets") or recipe.get("texts") or [{"text": "placeholder"}]
    records = tuple(row if isinstance(row, dict) else {"text": str(row)} for row in texts)
    return LearningExperiment(
        experiment_id=experiment_id,
        model=ModelRef(model_id=model_id),
        dataset=LearningDataset(
            name=str(recipe.get("name") or experiment_id),
            kind=DatasetKind.SFT,
            records=records,
        ),
        config=TrainingConfig(
            method=TrainingMethod.LORA,
            backend=FineTuneBackendName.AXOLOTL,
            seed=int(recipe.get("seed") or 0),
        ),
        title="axolotl-recipe",
    )
