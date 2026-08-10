#!/usr/bin/env python3
"""Checklist gate: agent narratives must cite run_id and invent zero numbers.

Runs controlled specialist demos (no live LLM) and applies:

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
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.common import narrative_authority_violations  # noqa: E402
from agents.optimization_specialist.specialist import OptimizationSpecialist  # noqa: E402


def main() -> int:
    skills = _ROOT / "skills"
    specialist = OptimizationSpecialist(skills_root=skills)
    demos = ("diet", "knapsack")
    failed = 0
    print("agent no-number-without-run_id checklist")
    print("=" * 50)
    for label in demos:
        try:
            report = specialist.run_demo(label)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] demo={label!r} raised: {exc}")
            failed += 1
            continue
        if report.execution is None:
            print(f"[FAIL] demo={label!r}: no ExecutionResult")
            failed += 1
            continue
        viol = narrative_authority_violations(report.narrative, report.execution)
        status = report.execution.status.value
        rid = report.execution.run_id
        if viol:
            print(f"[FAIL] demo={label!r} status={status} run_id={rid}")
            for v in viol:
                print(f"       - {v}")
            failed += 1
        else:
            print(f"[PASS] demo={label!r} status={status} run_id={rid}")
    print("=" * 50)
    if failed:
        print(f"{failed} demo(s) failed authority policy")
        return 1
    print("all demos cite run_id; invented-number rate = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
