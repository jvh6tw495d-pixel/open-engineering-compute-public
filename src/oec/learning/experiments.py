"""Learning experiments — reproducible training runs (L3)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from oec.learning.contracts import (
    FineTuneBackendName,
    ModelFamily,
    ModelRef,
    TrainingConfig,
    TrainingResult,
)
from oec.learning.datasets import LearningDataset
from oec.learning.errors import BackendNotAvailableError
from oec.learning.hardware import capture_code_version, capture_environment, capture_hardware


class LearningExperiment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    experiment_id: str = Field(min_length=1)
    model: ModelRef
    dataset: LearningDataset
    config: TrainingConfig
    title: str | None = None


class LearningRunRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    run_id: str
    experiment_id: str
    code_version: dict[str, str | None]
    environment: dict[str, Any]
    hardware: dict[str, Any]
    dataset: LearningDataset
    dataset_name: str
    dataset_version: str
    dataset_hash: str
    model_id: str
    model_revision: str | None
    model_family: ModelFamily | None = None
    backend: FineTuneBackendName
    config: TrainingConfig
    seed: int
    result: TrainingResult
    identity_hash: str = ""
    source_run_id: str | None = None


def select_backend(name: FineTuneBackendName) -> Any:
    if name is FineTuneBackendName.HUGGINGFACE:
        from oec.learning.backends.huggingface import HuggingFaceBackend

        return HuggingFaceBackend()
    if name is FineTuneBackendName.UNSLOTH:
        from oec.learning.backends.unsloth import UnslothBackend

        return UnslothBackend()
    if name is FineTuneBackendName.AXOLOTL:
        from oec.learning.backends.axolotl import AxolotlBackend

        return AxolotlBackend()
    raise BackendNotAvailableError(
        f"backend {name.value!r} is not implemented",
        details={"backend": name.value},
    )


def run_learning_experiment(experiment: LearningExperiment) -> LearningRunRecord:
    """Execute a Learning experiment and freeze a reproducible record."""
    experiment.dataset.verify_integrity()
    backend = select_backend(experiment.config.backend)
    result = backend.finetune(experiment.model, experiment.dataset, experiment.config)
    record = LearningRunRecord(
        run_id=str(uuid4()),
        experiment_id=experiment.experiment_id,
        code_version=capture_code_version(),
        environment=capture_environment(),
        hardware=capture_hardware(),
        dataset=experiment.dataset,
        dataset_name=experiment.dataset.name,
        dataset_version=experiment.dataset.version,
        dataset_hash=experiment.dataset.content_hash,
        model_id=experiment.model.model_id,
        model_revision=experiment.model.revision,
        model_family=experiment.model.family,
        backend=experiment.config.backend,
        config=experiment.config,
        seed=experiment.config.seed,
        result=result,
    )
    return record.model_copy(update={"identity_hash": compute_run_identity(record)})


def compute_run_identity(record: LearningRunRecord) -> str:
    """Hash of the reproducible inputs — not the live metrics."""
    payload = {
        "experiment_id": record.experiment_id,
        "dataset_hash": record.dataset_hash,
        "model_id": record.model_id,
        "model_revision": record.model_revision,
        "model_family": None if record.model_family is None else str(record.model_family),
        "backend": str(record.backend),
        "config": record.config.model_dump(mode="json"),
        "seed": record.seed,
        "code_version": record.code_version,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
