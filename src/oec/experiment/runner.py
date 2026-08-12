"""Sequential Experiment Engine (W2 / ADR 0034).

Each step is exactly one ``Engine.run`` → one ``ExecutionResult``.
Metrics are resolved only from declared paths into those results.
W2.2: ``binds_from`` dataflow + TARGET metric gates.
W2.3: optional local artifact persistence.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from oec import __version__
from oec.execution.models import ExecutionResult
from oec.experiment.artifacts import persist_experiment_record
from oec.experiment.record import (
    ExperimentRecord,
    ExperimentStatus,
    StepRecord,
    ValidationSummary,
)
from oec.experiment.resolve import (
    apply_binds,
    apply_validation_gates,
    resolve_metrics,
    should_abort_on_status,
)
from oec.experiment.specs import ExperimentSpec


class _EngineLike(Protocol):
    def run(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        *,
        skill_version: str | None = None,
        seed: int | None = None,
        trace_id: str | None = None,
        requested_by: str | None = None,
    ) -> ExecutionResult: ...


def config_hash(spec: ExperimentSpec) -> str:
    """SHA-256 of canonical JSON of the experiment spec (stable for same plan)."""
    payload = spec.model_dump(mode="json")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_experiment(
    engine: _EngineLike,
    spec: ExperimentSpec,
    *,
    requested_by: str | None = None,
    trace_id: str | None = None,
    artifact_root: str | Path | None = None,
    persist_artifacts: bool | None = None,
) -> ExperimentRecord:
    """Execute ``spec.steps`` sequentially and return an :class:`ExperimentRecord`.

    Authority: all numeric metrics come from step ``ExecutionResult`` fields.

    Seed is recorded on the experiment and passed to ``Engine.run`` for
    provenance only — it is **not** injected into skill inputs.

    ``persist_artifacts``: when True, write record under ``artifact_root``
    (or ``OEC_ARTIFACT_ROOT`` / ``.oec/artifacts``). Default True when
    ``artifact_root`` is set, else False.
    """
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    exp_trace = trace_id or str(uuid.uuid4())
    seed = int(spec.seed)
    notes: list[str] = []
    do_persist = (
        bool(persist_artifacts) if persist_artifacts is not None else artifact_root is not None
    )

    if not spec.steps:
        completed = datetime.now(UTC)
        record = ExperimentRecord(
            status=ExperimentStatus.INVALID,
            spec=spec,
            seed=seed,
            environment=_environment_snapshot(spec),
            steps=(),
            metrics=(),
            validation=ValidationSummary(passed=False, messages=("ExperimentSpec.steps is empty",)),
            reproducibility={
                "config_hash": config_hash(spec),
                "seed": seed,
                "trace_id": exp_trace,
            },
            started_at=started,
            completed_at=completed,
            duration_ms=(completed - started).total_seconds() * 1000.0,
            notes=("no steps",),
        )
        if do_persist:
            record, _ = persist_experiment_record(record, artifact_root=artifact_root)
        return record

    step_records: list[StepRecord] = []
    aborted = False
    infra_failed = False

    for step in spec.steps:
        try:
            inputs = apply_binds(step, tuple(step_records))
        except (KeyError, TypeError, ValueError) as exc:
            infra_failed = True
            step_records.append(
                StepRecord(
                    step_id=step.step_id,
                    skill_id=step.skill_id,
                    skill_version=step.skill_version,
                    execution=None,
                    error=f"bind_error: {exc}",
                )
            )
            notes.append(f"step {step.step_id!r} bind failed: {exc}")
            if spec.validation.abort_on_failed:
                aborted = True
                break
            continue

        try:
            execution = engine.run(
                step.skill_id,
                inputs,
                skill_version=step.skill_version,
                seed=seed,
                trace_id=f"{exp_trace}:{step.step_id}",
                requested_by=requested_by,
            )
            step_records.append(
                StepRecord(
                    step_id=step.step_id,
                    skill_id=step.skill_id,
                    skill_version=step.skill_version or execution.skill.version,
                    execution=execution,
                )
            )
            status_val = execution.status.value
            if should_abort_on_status(spec, status_val):
                notes.append(f"aborted after step {step.step_id!r} with status {status_val}")
                aborted = True
                break
        except Exception as exc:  # skill not found, validation raise, etc.
            infra_failed = True
            step_records.append(
                StepRecord(
                    step_id=step.step_id,
                    skill_id=step.skill_id,
                    skill_version=step.skill_version,
                    execution=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            notes.append(f"step {step.step_id!r} failed: {type(exc).__name__}: {exc}")
            if spec.validation.abort_on_failed:
                aborted = True
                break

    steps_t = tuple(step_records)
    metrics = resolve_metrics(spec, steps_t)
    validation = apply_validation_gates(spec, steps_t, metrics)

    if infra_failed and aborted:
        status = ExperimentStatus.FAILED
    elif aborted:
        status = ExperimentStatus.ABORTED
    elif not validation.passed:
        status = ExperimentStatus.VALIDATION_FAILED
    else:
        status = ExperimentStatus.COMPLETED

    completed = datetime.now(UTC)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    backends: list[Any] = []
    for sr in steps_t:
        if sr.execution is None:
            continue
        prov = sr.execution.provenance or {}
        for b in prov.get("backends") or []:
            if b not in backends:
                backends.append(b)

    record = ExperimentRecord(
        status=status,
        spec=spec,
        seed=seed,
        environment=_environment_snapshot(spec),
        steps=steps_t,
        metrics=metrics,
        validation=validation,
        reproducibility={
            "config_hash": config_hash(spec),
            "seed": seed,
            "trace_id": exp_trace,
            "oec_version": __version__,
            "backends": backends,
        },
        started_at=started,
        completed_at=completed,
        duration_ms=duration_ms,
        notes=tuple(notes),
    )

    if do_persist:
        record, _ = persist_experiment_record(record, artifact_root=artifact_root)

    return record


def _environment_snapshot(spec: ExperimentSpec) -> dict[str, Any]:
    return {
        "oec_version": __version__,
        "required_extras": list(spec.required_extras),
        "experiment_id": spec.id,
        "experiment_version": spec.version,
    }
