"""Learning experiments — reproducible training runs (L3)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oec.learning.contracts import (
    FineTuneBackendName,
    ModelFamily,
    ModelRef,
    TrainingConfig,
    TrainingResult,
)
from oec.learning.datasets import LearningDataset
from oec.learning.errors import BackendNotAvailableError
from oec.learning.hardware import (
    capture_code_version,
    capture_dependency_versions,
    capture_environment,
    capture_hardware,
)


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
    dependency_versions: dict[str, str | None] = Field(default_factory=dict)
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

    @model_validator(mode="after")
    def _consistent_snapshot(self) -> LearningRunRecord:
        if self.dataset_name != self.dataset.name:
            raise ValueError("dataset_name does not match snapshot dataset")
        if self.dataset_version != self.dataset.version:
            raise ValueError("dataset_version does not match snapshot dataset")
        if self.dataset_hash != self.dataset.content_hash:
            raise ValueError("dataset_hash does not match snapshot dataset")
        if self.backend != self.config.backend:
            raise ValueError("record backend does not match config.backend")
        if self.seed != self.config.seed:
            raise ValueError("record seed does not match config.seed")
        if self.result.backend != self.backend:
            raise ValueError("result.backend does not match record backend")
        if self.result.model is not None:
            if self.result.model.model_id != self.model_id:
                raise ValueError("result.model.model_id does not match record model_id")
            if self.result.model.revision != self.model_revision:
                raise ValueError("result.model.revision does not match record model_revision")
            if self.model_family is not None and self.result.model.family != self.model_family:
                raise ValueError("result.model.family does not match record model_family")
        return self


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
        dependency_versions=capture_dependency_versions(),
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
    """Hash of reproducible inputs only (not run_id, experiment label, or metrics)."""
    payload = {
        "dataset_hash": record.dataset_hash,
        "model_id": record.model_id,
        "model_revision": record.model_revision,
        "model_family": None if record.model_family is None else str(record.model_family),
        "backend": str(record.backend),
        "config": record.config.model_dump(mode="json"),
        "seed": record.seed,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
