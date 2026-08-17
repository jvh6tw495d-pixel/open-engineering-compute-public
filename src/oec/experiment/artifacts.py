"""Local filesystem artifact store for experiment records (W2.3)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from oec.experiment.record import ExperimentRecord, ProducedArtifact


def _safe_segment(raw: str) -> str:
    """Keep experiment ids from escaping the artifact root (Windows drive paths)."""
    if ".." in raw.replace("\\", "/"):
        raise ValueError(f"unsafe artifact path segment: {raw!r}")
    text = raw.replace("\\", "_").replace("/", "_").replace(":", "_")
    if not text or text in {".", ".."}:
        raise ValueError(f"unsafe artifact path segment: {raw!r}")
    return text


def default_artifact_root() -> Path:
    """``OEC_ARTIFACT_ROOT`` env or ``./.oec/artifacts`` under cwd."""
    env = os.environ.get("OEC_ARTIFACT_ROOT")
    if env:
        return Path(env)
    return Path.cwd() / ".oec" / "artifacts"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def persist_experiment_record(
    record: ExperimentRecord,
    *,
    artifact_root: str | Path | None = None,
    write_step_executions: bool = True,
) -> tuple[ExperimentRecord, tuple[ProducedArtifact, ...]]:
    """Write ``record.json`` (and optional step dumps) under the artifact root.

    Layout::

        {root}/{experiment_id}/{run_id}/record.json
        {root}/{experiment_id}/{run_id}/steps/{step_id}.json

    Returns ``(record_with_artifacts, produced)``.
    """
    root = Path(artifact_root) if artifact_root is not None else default_artifact_root()
    run_dir = root / _safe_segment(record.spec.id) / record.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    produced: list[ProducedArtifact] = []

    # Write step executions first so record can reference them
    if write_step_executions:
        steps_dir = run_dir / "steps"
        steps_dir.mkdir(exist_ok=True)
        for step in record.steps:
            if step.execution is None:
                continue
            step_path = steps_dir / f"{step.step_id}.json"
            payload = step.execution.model_dump(mode="json")
            step_path.write_text(
                json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
            )
            produced.append(
                ProducedArtifact(
                    name=f"step:{step.step_id}",
                    kind="json",
                    path=str(step_path.resolve()),
                    content_hash=_sha256_file(step_path),
                    media_type="application/json",
                )
            )

    # Write the record without embedding its own content hash. Rewriting the
    # file after hashing would make the stored digest stale.
    record_path = run_dir / "record.json"
    payload_record = record.model_copy(update={"artifacts_produced": tuple(produced)})
    record_path.write_text(
        json.dumps(payload_record.to_dict(), indent=2, default=str) + "\n", encoding="utf-8"
    )
    record_art = ProducedArtifact(
        name="record",
        kind="json",
        path=str(record_path.resolve()),
        content_hash=_sha256_file(record_path),
        media_type="application/json",
    )
    all_produced = (record_art, *produced)
    final = record.model_copy(update={"artifacts_produced": all_produced})
    return final, all_produced


def load_experiment_record(path: str | Path) -> dict[str, Any]:
    """Load a previously persisted experiment record JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"experiment record must be a JSON object, got {type(data).__name__}")
    return data
