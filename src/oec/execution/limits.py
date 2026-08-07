"""Input size / shape limits enforced before skill validation (Phase A2).

These are *request* limits, not scientific validation: they stop pathological
payloads from hanging the process or exhausting memory. Defaults are generous
for normal engineering arrays and strict enough for Alpha multi-tenant-ish
API abuse. Override per :class:`~oec.execution.service.ExecutionService` if
needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from oec.validation.base import Severity, ValidationOutcome

LAYER = "limits"

# Defaults: ~1 MiB JSON, 100k elements per sequence, 64 nesting levels.
DEFAULT_MAX_INPUT_JSON_BYTES = 1_048_576
DEFAULT_MAX_SEQUENCE_LENGTH = 100_000
DEFAULT_MAX_DEPTH = 64


@dataclass(frozen=True, slots=True)
class InputLimits:
    """Hard limits applied to every execution's original ``inputs`` dict."""

    max_input_json_bytes: int = DEFAULT_MAX_INPUT_JSON_BYTES
    max_sequence_length: int = DEFAULT_MAX_SEQUENCE_LENGTH
    max_depth: int = DEFAULT_MAX_DEPTH


def check_input_limits(
    inputs: dict[str, Any],
    limits: InputLimits | None = None,
) -> list[ValidationOutcome]:
    """Return ERROR outcomes if ``inputs`` exceeds configured limits.

    An empty list means the payload is within bounds. Callers treat any
    ERROR here like other input-validation failures (status ``INVALID``).
    """
    cfg = limits or InputLimits()
    outcomes: list[ValidationOutcome] = []

    try:
        encoded = json.dumps(inputs, default=str, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        outcomes.append(
            ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[f"inputs are not JSON-serializable: {exc}"],
                details={"limit": "json_serializable"},
            )
        )
        return outcomes

    if len(encoded) > cfg.max_input_json_bytes:
        outcomes.append(
            ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"inputs JSON exceeds max_input_json_bytes="
                    f"{cfg.max_input_json_bytes} (got {len(encoded)} bytes)"
                ],
                details={
                    "limit": "max_input_json_bytes",
                    "max": cfg.max_input_json_bytes,
                    "actual": len(encoded),
                },
            )
        )

    depth_or_len = _walk_sequences(inputs, cfg, depth=0)
    outcomes.extend(depth_or_len)
    return outcomes


def _walk_sequences(value: Any, cfg: InputLimits, *, depth: int) -> list[ValidationOutcome]:
    if depth > cfg.max_depth:
        return [
            ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"inputs nesting exceeds max_depth={cfg.max_depth} "
                    f"(got depth > {cfg.max_depth})"
                ],
                details={"limit": "max_depth", "max": cfg.max_depth},
            )
        ]

    outcomes: list[ValidationOutcome] = []
    if isinstance(value, dict):
        for item in value.values():
            outcomes.extend(_walk_sequences(item, cfg, depth=depth + 1))
            if outcomes:
                return outcomes  # fail fast on first violation
    elif isinstance(value, list | tuple):
        if len(value) > cfg.max_sequence_length:
            return [
                ValidationOutcome(
                    layer=LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"sequence length exceeds max_sequence_length="
                        f"{cfg.max_sequence_length} (got {len(value)})"
                    ],
                    details={
                        "limit": "max_sequence_length",
                        "max": cfg.max_sequence_length,
                        "actual": len(value),
                    },
                )
            ]
        for item in value:
            outcomes.extend(_walk_sequences(item, cfg, depth=depth + 1))
            if outcomes:
                return outcomes
    return outcomes
