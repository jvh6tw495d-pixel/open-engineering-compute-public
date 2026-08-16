"""L7 — Unsloth FineTune backend (fail-closed until extra exists)."""

from __future__ import annotations

from oec.learning.contracts import (
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingResult,
)
from oec.learning.datasets import LearningDataset
from oec.learning.errors import BackendNotAvailableError


class UnslothBackend:
    name = FineTuneBackendName.UNSLOTH

    def finetune(
        self,
        model: ModelRef,
        dataset: LearningDataset,
        config: TrainingConfig,
    ) -> TrainingResult:
        _ = (model, dataset, config)
        try:
            import unsloth  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            raise BackendNotAvailableError(
                "unsloth is not installed; L7 adapter is fail-closed",
                details={"backend": "unsloth", "error_type": type(exc).__name__},
            ) from exc
        raise BackendNotAvailableError(
            "unsloth is importable but the OEC adapter is not wired yet",
            details={"backend": "unsloth"},
        )
