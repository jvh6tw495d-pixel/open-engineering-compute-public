"""Learning datasets — version, provenance, splits (L2)."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oec.learning.errors import DatasetIntegrityError


class DatasetKind(StrEnum):
    SUPERVISED = "supervised"
    SCIENTIFIC = "scientific"
    SFT = "sft"
    PREFERENCE = "preference"
    DISTILLATION = "distillation"
    TOOL_USE = "tool_use"
    TRAJECTORY = "trajectory"
    RL = "rl"


class DatasetSplit(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class DatasetProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = "inline"
    license: str | None = None
    note: str | None = None


class LearningDataset(BaseModel):
    """Identified dataset: version + content hash, no HF Dataset object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = Field(min_length=1)
    kind: DatasetKind = DatasetKind.SFT
    version: str = Field(default="0.1.0", min_length=1)
    records: tuple[dict[str, Any], ...] = Field(min_length=1)
    split: DatasetSplit = DatasetSplit.TRAIN
    seed: int = 0
    provenance: DatasetProvenance = Field(default_factory=DatasetProvenance)
    content_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def _bind_hash(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        records = payload.get("records") or ()
        digest = compute_dataset_hash(
            name=str(payload.get("name") or ""),
            kind=payload.get("kind") or DatasetKind.SFT,
            version=str(payload.get("version") or "0.1.0"),
            records=tuple(records),
            split=payload.get("split") or DatasetSplit.TRAIN,
            seed=int(payload.get("seed") or 0),
        )
        existing = payload.get("content_hash")
        if existing in (None, ""):
            payload["content_hash"] = digest
        elif existing != digest:
            raise DatasetIntegrityError(
                "dataset content_hash does not match canonical payload",
                details={"expected": digest, "got": existing},
            )
        return payload

    def verify_integrity(self) -> None:
        """Reject records changed after construction before they reach a backend."""
        digest = compute_dataset_hash(
            name=self.name,
            kind=self.kind,
            version=self.version,
            records=self.records,
            split=self.split,
            seed=self.seed,
        )
        if digest != self.content_hash:
            raise DatasetIntegrityError(
                "dataset records changed after content_hash was bound",
                details={"expected": self.content_hash, "got": digest},
            )


def compute_dataset_hash(
    *,
    name: str,
    kind: DatasetKind | str,
    version: str,
    records: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    split: DatasetSplit | str,
    seed: int,
) -> str:
    payload = {
        "name": name,
        "kind": str(kind),
        "version": version,
        "split": str(split),
        "seed": seed,
        "records": list(records),
    }
    try:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise DatasetIntegrityError(
            "dataset hash payload must contain canonical JSON values",
            details={"reason": str(exc)},
        ) from exc
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def split_records(
    records: list[dict[str, Any]],
    *,
    val_fraction: float = 0.2,
    seed: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic train/val split (no sklearn)."""
    if not 0.0 <= val_fraction < 1.0:
        raise DatasetIntegrityError("val_fraction must be in [0, 1)")
    if len(records) < 2:
        return list(records), []
    indexed = list(enumerate(records))
    indexed.sort(key=lambda item: hashlib.sha256(f"{seed}:{item[0]}".encode()).hexdigest())
    n_val = int(len(indexed) * val_fraction)
    val = [item[1] for item in indexed[:n_val]]
    train = [item[1] for item in indexed[n_val:]]
    return train, val


def texts_from_sft(dataset: LearningDataset) -> list[str]:
    dataset.verify_integrity()
    texts: list[str] = []
    for row in dataset.records:
        if "text" in row and isinstance(row["text"], str):
            texts.append(row["text"])
        elif "prompt" in row and isinstance(row["prompt"], str):
            texts.append(str(row.get("completion") or row["prompt"]))
        else:
            texts.append(json.dumps(row, sort_keys=True, default=str))
    if not texts:
        raise DatasetIntegrityError("SFT dataset produced no texts")
    return texts
