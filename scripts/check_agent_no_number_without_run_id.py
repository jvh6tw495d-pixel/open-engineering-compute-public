#!/usr/bin/env python3
"""Checklist gate: agent narratives must cite run_id and invent zero numbers.

Runs controlled specialist demos across domains (no live LLM) and applies:

1. ``run_id`` must appear in every narrative attached to an ExecutionResult.
2. ``narrative_invented_numbers`` rate must be 0 (grounded in ExecutionResult).

Exit codes:
  0 — all demos pass
  1 — one or more authority violations
  2 — runtime / import failure

Usage (from repo root)::

    uv run python scripts/check_agent_no_number_without_run_id.py
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    try:
        from agents.applied_mathematics.specialist import AppliedMathematicsSpecialist
        from agents.common import narrative_authority_violations
        from agents.energy.specialist import EnergySpecialist
        from agents.optimization_specialist.specialist import OptimizationSpecialist
        from agents.time_series.specialist import TimeSeriesSpecialist
    except ImportError as exc:
        print(f"[FAIL] import error (run from repo root): {exc}")
        return 2

    skills = _ROOT / "skills"
    # One demo per specialist domain that ships a narrative path
    suite: list[tuple[str, Callable[[], Any], str]] = [
        ("optimization", lambda: OptimizationSpecialist(skills_root=skills), "diet"),
        ("optimization", lambda: OptimizationSpecialist(skills_root=skills), "knapsack"),
        ("applied_mathematics", lambda: AppliedMathematicsSpecialist(skills_root=skills), "sqrt2"),
        ("energy", lambda: EnergySpecialist(skills_root=skills), "load_metrics"),
        ("time_series", lambda: TimeSeriesSpecialist(skills_root=skills), "detect_outliers"),
    ]

    failed = 0
    runtime_errors = 0
    print("agent no-number-without-run_id checklist")
    print("=" * 50)
    for domain, factory, label in suite:
        key = f"{domain}/{label}"
        try:
            specialist = factory()
            report = specialist.run_demo(label)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] demo={key!r} raised: {exc}")
            runtime_errors += 1
            continue
        if report.execution is None:
            print(f"[FAIL] demo={key!r}: no ExecutionResult")
            failed += 1
            continue
        narrative = getattr(report, "narrative", "") or ""
        viol = narrative_authority_violations(narrative, report.execution)
        status = report.execution.status.value
        rid = report.execution.run_id
        if viol:
            print(f"[FAIL] demo={key!r} status={status} run_id={rid}")
            for v in viol:
                print(f"       - {v}")
            failed += 1
        else:
            print(f"[PASS] demo={key!r} status={status} run_id={rid}")
    print("=" * 50)
    if runtime_errors:
        print(f"{runtime_errors} demo(s) raised unexpectedly")
        return 2
    if failed:
        print(f"{failed} demo(s) failed authority policy")
        return 1
    print("all demos cite run_id; invented-number rate = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
