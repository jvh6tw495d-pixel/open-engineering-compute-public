"""L8 Axolotl recipe adapter (integration-unverified)."""

from __future__ import annotations

import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from oec.learning.contracts import (
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import DatasetKind, LearningDataset, texts_from_sft
from oec.learning.errors import BackendNotAvailableError
from oec.learning.experiments import LearningExperiment

_RECIPE_KEYS = frozenset(
    {
        "base_model",
        "model_type",
        "tokenizer_type",
        "datasets",
        "adapter",
        "sequence_len",
        "micro_batch_size",
        "num_epochs",
        "max_steps",
        "seed",
        "output_dir",
    }
)


def _materialize_jsonl(dataset: LearningDataset) -> Path:
    texts = texts_from_sft(dataset)
    fd, name = tempfile.mkstemp(suffix=".jsonl", prefix="oec-axolotl-")
    os.close(fd)
    path = Path(name)
    with path.open("w", encoding="utf-8") as raw:
        for text in texts:
            raw.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
    return path


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
        jsonl = _materialize_jsonl(dataset)
        recipe: dict[str, Any] = {
            "base_model": model.model_id,
            "model_type": "AutoModelForCausalLM",
            "tokenizer_type": "AutoTokenizer",
            "datasets": [{"path": str(jsonl), "type": "completion", "field": "text"}],
            "adapter": "lora" if config.method.value == "sft" else config.method.value,
            "sequence_len": config.max_seq_len,
            "micro_batch_size": config.batch_size,
            "num_epochs": 1,
            "max_steps": config.max_steps,
            "seed": config.seed,
        }
        extra = {
            key: value
            for key, value in config.hyperparameters.items()
            if key in _RECIPE_KEYS and key not in recipe
        }
        recipe.update(extra)
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
            details={"recipe_path": str(jsonl), "dataset_file": str(jsonl)},
        )


def recipe_to_experiment(recipe: dict[str, Any], *, experiment_id: str) -> LearningExperiment:
    """Translate a declarative recipe into an OEC LearningExperiment (no execution)."""
    model_id = str(recipe.get("base_model") or recipe.get("model") or "unknown")
    raw_rows = recipe.get("texts") or recipe.get("datasets") or [{"text": "placeholder"}]
    records: list[dict[str, Any]] = []
    for row in raw_rows:
        if isinstance(row, str):
            records.append({"text": row})
            continue
        if not isinstance(row, dict):
            records.append({"text": str(row)})
            continue
        if "text" in row or "prompt" in row:
            records.append(row)
            continue
        if "path" in row:
            # Axolotl file-ref entry — not inline samples.
            records.append({"text": f"axolotl-path:{row['path']}"})
            continue
        records.append({"text": json.dumps(row, sort_keys=True, default=str)})
    if not records:
        records = [{"text": "placeholder"}]
    return LearningExperiment(
        experiment_id=experiment_id,
        model=ModelRef(model_id=model_id),
        dataset=LearningDataset(
            name=str(recipe.get("name") or experiment_id),
            kind=DatasetKind.SFT,
            records=tuple(records),
        ),
        config=TrainingConfig(
            method=TrainingMethod.LORA,
            backend=FineTuneBackendName.AXOLOTL,
            seed=int(recipe.get("seed") or 0),
        ),
        title="axolotl-recipe",
    )
