"""Agent metrics harness (plan §7) — measurable gates for Alpha claims.

Metrics (controlled golden demos only; no live LLM):

1. OPS valid on first attempt (demo labels → execute_ops)
2. LP/MILP classification accuracy
3. Explicit assumptions present on successful demos
4. Invented-number rate = 0 (narrative numbers ⊆ ExecutionResult values)
5. Reviewer catch rate on known-bad cases
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.optimization_specialist.specialist import OptimizationSpecialist  # noqa: E402
from agents.scientific_reviewer.reviewer import ScientificReviewer  # noqa: E402

from oec.execution.models import ExecutionResult  # noqa: E402

_NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?")


@dataclass
class AgentMetricsReport:
    """Aggregate agent metrics for a controlled suite."""

    ops_valid_first_attempt_rate: float
    classification_accuracy: float
    assumptions_present_rate: float
    invented_number_rate: float
    reviewer_catch_rate: float
    n_ops_demos: int = 0
    n_ops_valid: int = 0
    n_class_correct: int = 0
    n_with_assumptions: int = 0
    n_narratives_checked: int = 0
    n_invented: int = 0
    n_reviewer_cases: int = 0
    n_reviewer_caught: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def gates_green(
        self,
        *,
        min_ops_valid: float = 1.0,
        min_class_acc: float = 1.0,
        max_invented: float = 0.0,
        min_reviewer_catch: float = 1.0,
    ) -> bool:
        return (
            self.ops_valid_first_attempt_rate >= min_ops_valid
            and self.classification_accuracy >= min_class_acc
            and self.invented_number_rate <= max_invented
            and self.reviewer_catch_rate >= min_reviewer_catch
        )


def _numbers_in_text(text: str) -> set[str]:
    """Normalize numeric tokens from free text for subset checks."""
    found: set[str] = set()
    for m in _NUMBER.findall(text):
        try:
            found.add(f"{float(m):.12g}")
        except ValueError:
            found.add(m)
    return found


def _numbers_from_execution(er: ExecutionResult) -> set[str]:
    allowed: set[str] = set()
    res = er.result or {}

    def walk(obj: Any) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, int | float):
            allowed.add(f"{float(obj):.12g}")
        elif isinstance(obj, str):
            allowed.update(_numbers_in_text(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list | tuple):
            for v in obj:
                walk(v)

    walk(res)
    walk(er.diagnostics or {})
    walk(er.provenance or {})
    # Structural ids/versions may appear in narrative by design
    allowed.add(er.skill.version)
    allowed.add(er.method.version)
    return allowed


def narrative_invented_numbers(narrative: str, er: ExecutionResult) -> list[str]:
    """Return numeric tokens in narrative that are not grounded in ExecutionResult.

    Allows run_id / hashes / skill id strings by ignoring pure hex UUID segments.
    """
    allowed = _numbers_from_execution(er)
    invented: list[str] = []
    # Strip known non-scientific identifiers from narrative before scanning
    cleaned = narrative
    cleaned = cleaned.replace(er.run_id, " ")
    if er.provenance:
        ih = str(er.provenance.get("input_hash") or "")
        if ih:
            cleaned = cleaned.replace(ih, " ")
    for tok in _numbers_in_text(cleaned):
        if tok in allowed:
            continue
        # Ignore integers that only appear as status codes / zero counts if absent
        # from result: treat as invented
        invented.append(tok)
    return invented


def run_agent_metrics(skills_root: str | Path | None = None) -> AgentMetricsReport:
    """Execute controlled golden suite and return metrics report."""
    root = Path(skills_root) if skills_root else _ROOT / "skills"
    specialist = OptimizationSpecialist(skills_root=root)
    reviewer = ScientificReviewer()

    demos: list[tuple[str, str]] = [
        ("diet", "lp"),
        ("knapsack", "milp"),
    ]
    details: list[dict[str, Any]] = []
    n_valid = 0
    n_class = 0
    n_assumptions = 0
    n_narr = 0
    n_invented = 0

    for label, expected_class in demos:
        report = specialist.run_demo(label)
        valid = report.ops_valid and report.execution is not None
        class_ok = report.problem_class == expected_class
        has_assumptions = bool(report.assumptions)
        invented: list[str] = []
        if report.execution is not None and report.narrative:
            n_narr += 1
            invented = narrative_invented_numbers(report.narrative, report.execution)
            if invented:
                n_invented += 1
        if valid:
            n_valid += 1
        if class_ok:
            n_class += 1
        if has_assumptions:
            n_assumptions += 1
        details.append(
            {
                "demo": label,
                "ops_valid": valid,
                "problem_class": report.problem_class,
                "expected_class": expected_class,
                "class_ok": class_ok,
                "has_assumptions": has_assumptions,
                "invented_tokens": invented,
                "status": None if report.execution is None else report.execution.status.value,
            }
        )

    # Reviewer catch rate: invalid OPS + forged objective claim
    catch_cases = 0
    caught = 0

    # Case A: invalid OPS
    bad_ops = {"problem_class": "lp"}  # incomplete
    # Need a dummy execution — build a minimal forged one via specialist partial
    good = specialist.run_demo("diet")
    assert good.execution is not None
    rev_a = reviewer.review(bad_ops, good.execution)
    catch_cases += 1
    if not rev_a.passed:
        caught += 1
    details.append({"reviewer_case": "invalid_ops", "caught": not rev_a.passed})

    # Case B: forged objective claim on valid solve
    forged_obj = None
    if good.execution.result and "objective_value" in good.execution.result:
        real = float(good.execution.result["objective_value"])
        forged_obj = real + 999.0
    rev_b = reviewer.review(
        good.ops,
        good.execution,
        claimed_objective=forged_obj if forged_obj is not None else 999.0,
    )
    catch_cases += 1
    if not rev_b.passed:
        caught += 1
    details.append({"reviewer_case": "forged_objective", "caught": not rev_b.passed})

    # Case C: status claim inconsistent
    rev_c = reviewer.review(
        good.ops,
        good.execution,
        claimed_solver_status="infeasible"
        if good.execution.result.get("solver_status") == "optimal"
        else "optimal",
    )
    catch_cases += 1
    if not rev_c.passed:
        caught += 1
    details.append({"reviewer_case": "inconsistent_status_claim", "caught": not rev_c.passed})

    n = len(demos)
    return AgentMetricsReport(
        ops_valid_first_attempt_rate=n_valid / n if n else 0.0,
        classification_accuracy=n_class / n if n else 0.0,
        assumptions_present_rate=n_assumptions / n if n else 0.0,
        invented_number_rate=n_invented / n_narr if n_narr else 0.0,
        reviewer_catch_rate=caught / catch_cases if catch_cases else 0.0,
        n_ops_demos=n,
        n_ops_valid=n_valid,
        n_class_correct=n_class,
        n_with_assumptions=n_assumptions,
        n_narratives_checked=n_narr,
        n_invented=n_invented,
        n_reviewer_cases=catch_cases,
        n_reviewer_caught=caught,
        details=details,
    )


def main() -> None:
    report = run_agent_metrics()
    import json

    print(json.dumps(report.to_dict(), indent=2))
    if not report.gates_green():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
