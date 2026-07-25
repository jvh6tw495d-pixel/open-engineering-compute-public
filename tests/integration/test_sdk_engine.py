"""Integration tests for oec.sdk.Engine/run (ADR 0014): the public SDK
facade running against the real skills/ directory, exercising validator
auto-discovery end to end (not hand-wired, unlike the other
test_*_end_to_end.py files -- this is what those would collapse into).
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

import pytest

from oec import sdk
from oec.errors import SkillNotFoundError
from oec.execution.models import ExecutionStatus


def test_engine_runs_solve_root() -> None:
    engine = sdk.Engine(skills_root="skills")
    result = engine.run("mathematics.solve_root", {"expression": "x**2 - 2", "bracket": [0, 2]})
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["root"], math.sqrt(2), rel_tol=1e-9)


def test_engine_runs_optimize_constrained() -> None:
    engine = sdk.Engine(skills_root="skills")
    result = engine.run(
        "mathematics.optimize_constrained",
        {
            "variables": ["x", "y"],
            "expression": "x**2 + y**2",
            "x0": [0.0, 0.0],
            "bounds": [[-10, 10], [-10, 10]],
            "constraints": [{"type": "ineq", "expression": "x + y - 1"}],
        },
    )
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["x"][0], 0.5, abs_tol=1e-6)


def test_engine_caches_execution_service_per_skill() -> None:
    """Whitebox check that the same ExecutionService instance is reused
    across repeated calls to the same skill, not rebuilt per call."""
    engine = sdk.Engine(skills_root="skills")
    engine.run("mathematics.solve_root", {"expression": "x - 1", "bracket": [0, 2]})
    service_after_first = engine._services[("mathematics.solve_root", "0.1.0")]  # noqa: SLF001
    engine.run("mathematics.solve_root", {"expression": "x - 2", "bracket": [0, 3]})
    service_after_second = engine._services[("mathematics.solve_root", "0.1.0")]  # noqa: SLF001
    assert service_after_first is service_after_second
    assert len(engine._services) == 1  # noqa: SLF001


def test_engine_unknown_skill_raises() -> None:
    engine = sdk.Engine(skills_root="skills")
    with pytest.raises(SkillNotFoundError):
        engine.run("mathematics.not_a_real_skill", {})


def test_engine_tolerates_broken_sibling_skill(tmp_path: Path) -> None:
    """A broken skill directory elsewhere under skills_root must not
    prevent Engine from running an unrelated, healthy skill -- mirrors
    `oec skills list`'s existing tolerance for individual registration
    failures (src/oec/cli/main.py::_load_registry)."""
    skills_copy = tmp_path / "skills"
    shutil.copytree("skills", skills_copy)
    broken_dir = skills_copy / "mathematics" / "broken_skill"
    broken_dir.mkdir()
    (broken_dir / "skill.yaml").write_text("not: [valid, skill, yaml: shape", encoding="utf-8")

    engine = sdk.Engine(skills_root=skills_copy)

    assert len(engine.registration_failures) == 1
    result = engine.run("mathematics.solve_root", {"expression": "x - 1", "bracket": [0, 2]})
    assert result.status is ExecutionStatus.VALIDATED


def test_module_level_run_convenience() -> None:
    result = sdk.run(
        "mathematics.solve_root",
        {"expression": "x**2 - 2", "bracket": [0, 2]},
        skills_root="skills",
    )
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["root"], math.sqrt(2), rel_tol=1e-9)


def test_engine_run_forwards_provenance_fields() -> None:
    engine = sdk.Engine(skills_root="skills")
    result = engine.run(
        "mathematics.solve_root",
        {"expression": "x - 1", "bracket": [0, 2]},
        trace_id="my-trace-id",
        requested_by="test-suite",
        seed=42,
    )
    assert result.provenance["requested_by"] == "test-suite"
    assert result.provenance["trace_id"] == "my-trace-id"
    assert result.provenance["seed"] == 42
