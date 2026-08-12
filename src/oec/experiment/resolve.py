"""Resolve metric paths, binds_from, and experiment validation gates (W2.2)."""

from __future__ import annotations

from typing import Any

from oec.execution.models import ExecutionResult
from oec.experiment.record import MetricValue, StepRecord, ValidationSummary
from oec.experiment.specs import BindSpec, ExperimentSpec, ExperimentStep, MetricDirection


def walk_path(payload: Any, path: str) -> Any:
    """Walk a dotted path into nested dicts/lists (e.g. ``result.rmse``)."""
    cur: Any = payload
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(cur, dict):
            if part not in cur:
                raise KeyError(f"missing key {part!r} in path {path!r}")
            cur = cur[part]
        elif isinstance(cur, list):
            idx = int(part)
            cur = cur[idx]
        else:
            raise KeyError(f"cannot descend into {type(cur).__name__} at {part!r} of {path!r}")
    return cur


def execution_as_dict(execution: ExecutionResult) -> dict[str, Any]:
    return execution.model_dump(mode="json")


def resolve_path_from_execution(execution: ExecutionResult, path: str) -> Any:
    return walk_path(execution_as_dict(execution), path)


def _step_map(steps: tuple[StepRecord, ...]) -> dict[str, StepRecord]:
    return {s.step_id: s for s in steps}


def apply_binds(
    step: ExperimentStep,
    prior_steps: tuple[StepRecord, ...],
) -> dict[str, Any]:
    """Merge ``step.inputs`` with values bound from prior step executions.

    Explicit ``inputs`` keys win over binds if both set the same key
    (base inputs first, then binds override — binds are the dataflow edge).
    """
    merged = dict(step.inputs)
    if not step.binds_from:
        return merged
    by_id = _step_map(prior_steps)
    for bind in step.binds_from:
        bind_spec = bind if isinstance(bind, BindSpec) else BindSpec.model_validate(bind)
        src = by_id.get(bind_spec.step_id)
        if src is None or src.execution is None:
            raise KeyError(
                f"bind step_id={bind_spec.step_id!r} not available "
                f"(missing or no execution) for target step {step.step_id!r}"
            )
        value = resolve_path_from_execution(src.execution, bind_spec.path)
        merged[bind_spec.as_key] = value
    return merged


def resolve_metrics(spec: ExperimentSpec, steps: tuple[StepRecord, ...]) -> tuple[MetricValue, ...]:
    """Extract declared metrics from step executions. Never invents numbers."""
    by_id = _step_map(steps)
    last_step_id = steps[-1].step_id if steps else None
    resolved: list[MetricValue] = []

    for metric in spec.metrics:
        step_id = metric.step_id or last_step_id
        if step_id is None:
            resolved.append(
                MetricValue(
                    name=metric.name,
                    value=None,
                    path=metric.path,
                    step_id=None,
                    direction=metric.direction.value,
                    target=metric.target,
                    error="no steps available to resolve metric",
                )
            )
            continue
        step = by_id.get(step_id)
        if step is None or step.execution is None:
            resolved.append(
                MetricValue(
                    name=metric.name,
                    value=None,
                    path=metric.path,
                    step_id=step_id,
                    direction=metric.direction.value,
                    target=metric.target,
                    error=f"step {step_id!r} missing or has no execution",
                )
            )
            continue
        try:
            raw = resolve_path_from_execution(step.execution, metric.path)
            value = float(raw)
            abs_err: float | None = None
            if metric.target is not None:
                abs_err = abs(value - float(metric.target))
            resolved.append(
                MetricValue(
                    name=metric.name,
                    value=value,
                    path=metric.path,
                    step_id=step_id,
                    direction=metric.direction.value,
                    target=metric.target,
                    abs_error_to_target=abs_err,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            resolved.append(
                MetricValue(
                    name=metric.name,
                    value=None,
                    path=metric.path,
                    step_id=step_id,
                    direction=metric.direction.value,
                    target=metric.target,
                    error=str(exc),
                )
            )
    return tuple(resolved)


def apply_validation_gates(
    spec: ExperimentSpec,
    steps: tuple[StepRecord, ...],
    metrics: tuple[MetricValue, ...],
) -> ValidationSummary:
    """Check step statuses and metric thresholds from ValidationSpec (W2.2)."""
    messages: list[str] = []
    metric_checks: dict[str, bool] = {}
    policy = spec.validation
    allowed = set(policy.require_step_status_in)

    for step in steps:
        if step.execution is None:
            messages.append(f"step {step.step_id!r}: no execution ({step.error})")
            continue
        status = step.execution.status.value
        if status not in allowed:
            messages.append(
                f"step {step.step_id!r}: status {status!r} not in allowed {sorted(allowed)}"
            )

    by_name = {m.name: m for m in metrics}

    for name, max_v in policy.metric_max.items():
        mv = by_name.get(name)
        if mv is None or mv.value is None:
            messages.append(f"metric {name!r}: missing for metric_max gate")
            metric_checks[name] = False
            continue
        ok = mv.value <= float(max_v)
        metric_checks[name] = ok
        if not ok:
            messages.append(f"metric {name!r}: value {mv.value} exceeds metric_max {max_v}")

    for name, min_v in policy.metric_min.items():
        mv = by_name.get(name)
        if mv is None or mv.value is None:
            messages.append(f"metric {name!r}: missing for metric_min gate")
            metric_checks[name] = False
            continue
        ok = mv.value >= float(min_v)
        metric_checks[name] = ok
        if not ok:
            messages.append(f"metric {name!r}: value {mv.value} below metric_min {min_v}")

    # TARGET direction: hard gate when target_abs_tol is set (spec or validation map)
    for metric in spec.metrics:
        if metric.direction != MetricDirection.TARGET or metric.target is None:
            continue
        mv = by_name.get(metric.name)
        tol = policy.metric_target_abs_tol.get(metric.name)
        if tol is None:
            tol = metric.target_abs_tol
        if tol is None:
            continue  # soft target only
        if mv is None or mv.value is None:
            messages.append(f"metric {metric.name!r}: missing for TARGET gate")
            metric_checks[metric.name] = False
            continue
        err = abs(mv.value - float(metric.target))
        ok = err <= float(tol)
        metric_checks[metric.name] = ok
        if not ok:
            messages.append(
                f"metric {metric.name!r}: |value-target|={err} exceeds tol={tol} "
                f"(value={mv.value}, target={metric.target})"
            )

    if policy.require_all_metrics:
        for mv in metrics:
            if mv.error:
                messages.append(f"metric {mv.name!r}: {mv.error}")
                metric_checks.setdefault(mv.name, False)

    return ValidationSummary(
        passed=len(messages) == 0,
        messages=tuple(messages),
        metric_checks=metric_checks,
    )


def should_abort_on_status(spec: ExperimentSpec, status_value: str) -> bool:
    policy = spec.validation
    return (status_value == "INVALID" and policy.abort_on_invalid) or (
        status_value == "FAILED" and policy.abort_on_failed
    )
