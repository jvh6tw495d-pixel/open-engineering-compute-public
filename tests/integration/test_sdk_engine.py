"""Integration tests for oec.sdk.Engine/run (ADR 0014): the public SDK
facade running against the real skills/ directory, exercising validator
auto-discovery end to end (not hand-wired, unlike the other
test_*_end_to_end.py files -- this is what those would collapse into).
"""

from __future__ import annotations

import math
import shutil
import threading
import time
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


def test_engine_warm_builds_every_skill_service_up_front() -> None:
    """warm() (ADR 0015) populates the whole _services cache before any
    run() call -- required for REST/MCP so a skill's validator-discovery
    failure surfaces at startup, not on that skill's first request."""
    engine = sdk.Engine(skills_root="skills")
    assert len(engine._services) == 0  # noqa: SLF001
    engine.warm()
    manifests = engine._registry.list_skills(include_retired=True)  # noqa: SLF001
    assert len(engine._services) == len(manifests)  # noqa: SLF001
    assert len(manifests) >= 6  # the six MVP math skills, at minimum


def test_engine_warm_surfaces_a_broken_skill_validator_immediately(tmp_path: Path) -> None:
    """A skill declaring mathematical:true with no matching InputValidator
    class in its validation.py must fail at warm() time, not silently,
    and not only on that skill's first run()."""
    from oec.errors import SkillEntrypointError
    from oec.testing import write_skill_dir

    write_skill_dir(
        tmp_path,
        manifest_overrides={
            "validation": {
                "schema": True,
                "dimensional": False,
                "mathematical": True,
                "physical": False,
                "numerical": False,
            }
        },
    )
    engine = sdk.Engine(skills_root=tmp_path)
    with pytest.raises(SkillEntrypointError):
        engine.warm()


def test_engine_run_is_serialized_across_threads() -> None:
    """ADR 0015: Engine.run() is one critical section, so N concurrent
    calls on the same Engine take roughly N times as long as one call --
    not ~1x, which is what parallel (unserialized) execution would look
    like. A wall-clock check, not an instrumentation one: subprocess
    execution happens on the OS side, where Python-level hooks around
    the call site can't reliably observe overlap directly, but blocked
    threads waiting on Engine's internal lock show up unambiguously in
    total elapsed time."""
    engine = sdk.Engine(skills_root="skills")
    inputs = {"expression": "x - 1", "bracket": [0, 2]}

    start = time.monotonic()
    engine.run("mathematics.solve_root", inputs)
    single_call_duration = time.monotonic() - start

    n = 4
    threads = [
        threading.Thread(target=engine.run, args=("mathematics.solve_root", inputs))
        for _ in range(n)
    ]
    start = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    total_duration = time.monotonic() - start

    # Serialized: ~n * single_call_duration. Parallel: ~1 * single_call_duration.
    # A 2x floor is a generous margin below the theoretical ~4x, avoiding
    # flakiness from timing noise while still failing if run() overlapped.
    assert total_duration >= single_call_duration * 2
