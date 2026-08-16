"""Learning dataset and run persistence (L2) plus experiment replay (L3).

Core-safe: this module uses Pydantic + stdlib only. Backends stay lazy via
``select_backend``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oec.learning.contracts import ModelRef, TrainingResult
from oec.learning.datasets import LearningDataset
from oec.learning.errors import DatasetIntegrityError
from oec.learning.experiments import LearningRunRecord, select_backend

DATASET_FILENAME = "dataset.json"
RUN_FILENAME = "record.json"


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
    return record


def replay_learning_experiment(record: LearningRunRecord) -> TrainingResult:
    """Re-run ``select_backend().finetune`` from a frozen run snapshot.

    Returns the backend ``TrainingResult`` as-is. Missing extras fail closed
    with ``BackendNotAvailableError``; metrics are never invented here.
    """
    record.dataset.verify_integrity()
    if record.dataset_hash != record.dataset.content_hash:
        raise DatasetIntegrityError(
            "run record dataset_hash does not match snapshot dataset",
            details={"expected": record.dataset.content_hash, "got": record.dataset_hash},
        )
    backend = select_backend(record.config.backend)
    model = ModelRef(model_id=record.model_id, revision=record.model_revision)
    result = backend.finetune(model, record.dataset, record.config)
    if not isinstance(result, TrainingResult):
        raise TypeError("backend finetune must return TrainingResult")
    return result


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
