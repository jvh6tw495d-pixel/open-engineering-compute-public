"""Golden case framework (plan section 12.6): known-good input/output pairs
used to catch regressions in a skill's numeric behavior.

This is development-time regression protection (run by pytest against
stored expected values), not a runtime validator — it never runs as
part of :class:`~oec.execution.service.ExecutionService`'s pipeline. See
``docs/architecture/adr/0007-validation-status-model.md`` for why
``ExecutionStatus.VERIFIED`` is deliberately *not* defined as "matched a
golden case at runtime."
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict


class GoldenCase(BaseModel):
    """One known-good input/output pair for a skill, per plan section 12.6."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    skill_id: str
    skill_version: str
    inputs: dict[str, Any]
    expected_result: dict[str, Any]
    tolerance: float = 1e-9
    source: str
    justification: str


def diff_against_golden(actual_result: dict[str, Any], golden: GoldenCase) -> list[str]:
    """Compare ``actual_result`` to ``golden.expected_result``.

    Returns a list of human-readable mismatch descriptions; an empty
    list means the result matches within ``golden.tolerance``. Numeric
    leaves are compared with :func:`math.isclose`; everything else with
    exact equality.
    """
    return _diff(actual_result, golden.expected_result, golden.tolerance, path="result")


def assert_matches_golden(actual_result: dict[str, Any], golden: GoldenCase) -> None:
    """Raise ``AssertionError`` with every mismatch if ``actual_result`` doesn't match."""
    mismatches = diff_against_golden(actual_result, golden)
    if mismatches:
        joined = "\n".join(mismatches)
        raise AssertionError(
            f"result does not match golden case {golden.id!r} ({golden.source}):\n{joined}"
        )


def _diff(actual: Any, expected: Any, tolerance: float, *, path: str) -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected a mapping, got {type(actual).__name__}"]
        mismatches: list[str] = []
        for key in expected:
            if key not in actual:
                mismatches.append(f"{path}.{key}: missing from actual result")
                continue
            mismatches.extend(_diff(actual[key], expected[key], tolerance, path=f"{path}.{key}"))
        extra_keys = set(actual) - set(expected)
        mismatches.extend(f"{path}.{key}: unexpected key in actual result" for key in extra_keys)
        return mismatches

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: expected a list of length {len(expected)}, got {actual!r}"]
        mismatches = []
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            mismatches.extend(_diff(actual_item, expected_item, tolerance, path=f"{path}[{index}]"))
        return mismatches

    if isinstance(expected, int | float) and not isinstance(expected, bool):
        if not isinstance(actual, int | float) or isinstance(actual, bool):
            return [f"{path}: expected a number, got {actual!r}"]
        if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
            return [f"{path}: expected {expected!r} (tolerance {tolerance}), got {actual!r}"]
        return []

    if actual != expected:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []
