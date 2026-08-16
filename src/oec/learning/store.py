"""Learning dataset and run persistence (L2) plus experiment replay (L3).

Core-safe: this module uses Pydantic + stdlib only. Backends stay lazy via
``select_backend``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from oec.learning.contracts import ModelFamily, ModelRef, TrainingResult
from oec.learning.datasets import LearningDataset
from oec.learning.errors import DatasetIntegrityError
from oec.learning.experiments import (
    LearningRunRecord,
    compute_run_identity,
    select_backend,
)
from oec.learning.hardware import capture_code_version, capture_environment, capture_hardware

DATASET_FILENAME = "dataset.json"
RUN_FILENAME = "record.json"


class ReplayReport(BaseModel):
    """Rerun from a snapshot. This is not a bit-identical reproduction proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    source_run_id: str
    record: LearningRunRecord
    comparison: dict[str, Any] = Field(default_factory=dict)


def save_dataset(dataset: LearningDataset, directory: str | Path) -> Path:
    """Write schema + records + content_hash JSON under ``directory``."""
    dataset.verify_integrity()
    path = _as_json_file(directory, DATASET_FILENAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    dumped = dataset.model_dump(mode="json")
    excluded = {"records", "content_hash"}
    identity = {key: value for key, value in dumped.items() if key not in excluded}
    payload = {
        "schema": identity,
        "records": dumped["records"],
        "content_hash": dumped["content_hash"],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_dataset(directory: str | Path) -> LearningDataset:
    """Load a persisted dataset and re-verify its content hash."""
    path = _as_json_file(directory, DATASET_FILENAME)
    payload = _read_json_object(path)
    dataset = LearningDataset.model_validate(_dataset_payload(payload, source=str(path)))
    dataset.verify_integrity()
    return dataset


def save_run(record: LearningRunRecord, path: str | Path) -> Path:
    """Persist a learning run record as JSON."""
    record.dataset.verify_integrity()
    dest = _as_json_file(path, RUN_FILENAME)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dest


def load_run(path: str | Path) -> LearningRunRecord:
    """Load a learning run record and re-verify the snapshot dataset hash."""
    src = _as_json_file(path, RUN_FILENAME)
    payload = _read_json_object(src)
    nested = payload.get("dataset")
    if isinstance(nested, dict):
        LearningDataset.model_validate(_dataset_payload(nested, source=str(src)))
    record = LearningRunRecord.model_validate(payload)
    record.dataset.verify_integrity()
    if record.dataset_hash != record.dataset.content_hash:
        raise DatasetIntegrityError(
            "run record dataset_hash does not match snapshot dataset",
            details={"expected": record.dataset.content_hash, "got": record.dataset_hash},
        )
    if record.identity_hash:
        expected = compute_run_identity(record)
        if record.identity_hash != expected:
            raise DatasetIntegrityError(
                "run identity_hash does not match canonical inputs",
                details={"expected": expected, "got": record.identity_hash},
            )
    return record


def replay_learning_experiment(record: LearningRunRecord) -> ReplayReport:
    """Re-run ``select_backend().finetune`` from a frozen snapshot.

    Returns a new ``LearningRunRecord`` plus a metric comparison. Missing
    extras fail closed. Metrics are never invented here.
    """
    record.dataset.verify_integrity()
    if record.dataset_hash != record.dataset.content_hash:
        raise DatasetIntegrityError(
            "run record dataset_hash does not match snapshot dataset",
            details={"expected": record.dataset.content_hash, "got": record.dataset_hash},
        )
    backend = select_backend(record.config.backend)
    family = record.model_family or ModelFamily.TRANSFORMERS
    model = ModelRef(
        model_id=record.model_id,
        revision=record.model_revision,
        family=family,
    )
    result = backend.finetune(model, record.dataset, record.config)
    if not isinstance(result, TrainingResult):
        raise TypeError("backend finetune must return TrainingResult")
    rerun = LearningRunRecord(
        run_id=str(uuid4()),
        experiment_id=f"{record.experiment_id}.replay",
        code_version=capture_code_version(),
        environment=capture_environment(),
        hardware=capture_hardware(),
        dataset=record.dataset,
        dataset_name=record.dataset_name,
        dataset_version=record.dataset_version,
        dataset_hash=record.dataset_hash,
        model_id=record.model_id,
        model_revision=record.model_revision,
        model_family=family,
        backend=record.config.backend,
        config=record.config,
        seed=record.seed,
        result=result,
        source_run_id=record.run_id,
    )
    rerun = rerun.model_copy(update={"identity_hash": compute_run_identity(rerun)})
    comparison: dict[str, Any] = {
        "source_run_id": record.run_id,
        "rerun_id": rerun.run_id,
        "identity_hash_source": record.identity_hash or compute_run_identity(record),
        "identity_hash_rerun": rerun.identity_hash,
    }
    shared = set(record.result.metrics) & set(result.metrics)
    if shared:
        comparison["metric_delta"] = {
            key: float(result.metrics[key]) - float(record.result.metrics[key])
            for key in sorted(shared)
        }
    return ReplayReport(source_run_id=record.run_id, record=rerun, comparison=comparison)


def _as_json_file(path: str | Path, filename: str) -> Path:
    dest = Path(path)
    if dest.suffix.lower() == ".json":
        return dest
    return dest / filename


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DatasetIntegrityError(
            "persisted learning JSON must be an object",
            details={"path": str(path), "got": type(payload).__name__},
        )
    return payload


def _dataset_payload(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    if "schema" in payload and "records" in payload:
        schema = payload["schema"]
        if not isinstance(schema, dict):
            raise DatasetIntegrityError(
                "persisted dataset schema must be a JSON object",
                details={"source": source},
            )
        data = {
            **schema,
            "records": payload["records"],
            "content_hash": payload.get("content_hash"),
        }
    else:
        data = dict(payload)
    digest = data.get("content_hash")
    if digest in (None, ""):
        raise DatasetIntegrityError(
            "persisted dataset is missing content_hash",
            details={"source": source},
        )
    return data
