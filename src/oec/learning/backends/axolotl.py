"""L8 Axolotl recipe adapter."""

from __future__ import annotations

import importlib
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
        self, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        try:
            importlib.import_module("axolotl")
        except Exception as exc:
            raise BackendNotAvailableError(
                "axolotl is not installed; L8 adapter is fail-closed",
                details={"backend": "axolotl", "error_type": type(exc).__name__},
            ) from exc
        recipe: dict[str, Any] = {
            "base_model": model.model_id,
            "model_type": "AutoModelForCausalLM",
            "tokenizer_type": "AutoTokenizer",
            "datasets": [{"path": list(dataset.records), "type": "alpaca"}],
            "adapter": config.method.value,
            "sequence_len": config.max_seq_len,
            "micro_batch_size": config.batch_size,
            "num_epochs": 1,
            "max_steps": config.max_steps,
            "seed": config.seed,
            **config.hyperparameters,
        }
        try:
            train_module = importlib.import_module("axolotl.cli.train")
            train = getattr(train_module, "train", None)
            if not callable(train):
                raise AttributeError("axolotl.cli.train.train")
            raw = train(recipe)
        except Exception as exc:
            raise BackendNotAvailableError(
                "adapter not wired to this axolotl version",
                details={"backend": "axolotl", "error_type": type(exc).__name__},
            ) from exc
        metrics = raw if isinstance(raw, dict) else {}
        return TrainingResult(
            status="ok",
            backend=self.name,
            method=config.method,
            model=model,
            metrics={
                key: float(value)
                for key, value in metrics.items()
                if isinstance(value, (int, float))
            },
            message="axolotl.cli.train.train",
            details={"recipe": recipe},
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
            name=str(recipe.get("name") or experiment_id), kind=DatasetKind.SFT, records=records
        ),
        config=TrainingConfig(
            method=TrainingMethod.LORA,
            backend=FineTuneBackendName.AXOLOTL,
            seed=int(recipe.get("seed") or 0),
        ),
        title="axolotl-recipe",
    )
