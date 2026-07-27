"""Unit tests for oec.core ScientificResult (domain-independent)."""

from __future__ import annotations

from datetime import UTC, datetime

from oec.common import VersionedRef
from oec.core import ScientificResult, from_execution_result
from oec.core.types import Assumption, BackendRef, MethodRef
from oec.execution.models import ExecutionResult, ExecutionStatus


def _sample_er(**kwargs: object) -> ExecutionResult:
    base = {
        "run_id": "run-test-001",
        "status": ExecutionStatus.VALIDATED,
        "skill": VersionedRef(id="mathematics.solve_root", version="0.1.0"),
        "method": VersionedRef(id="scalar_root_finding", version="0.1.0"),
        "result": {"root": 1.41421356237, "method": "brentq"},
        "assumptions": ["bracket isolates a single root"],
        "diagnostics": {"converged": True},
        "warnings": [],
        "validation": {"outcomes": []},
        "provenance": {
            "input_hash": "abc123",
            "backends": [
                {"name": "numpy", "version": "2.0.0"},
                {"name": "scipy", "version": "1.14.0"},
            ],
        },
        "started_at": datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC),
        "completed_at": datetime(2026, 7, 27, 12, 0, 1, tzinfo=UTC),
        "duration_ms": 12.5,
    }
    base.update(kwargs)
    return ExecutionResult.model_validate(base)


def test_from_execution_result_maps_core_fields() -> None:
    sr = from_execution_result(_sample_er())
    assert sr.run_id == "run-test-001"
    assert sr.status is ExecutionStatus.VALIDATED
    assert sr.skill_id == "mathematics.solve_root"
    assert sr.skill_version == "0.1.0"
    assert sr.method == MethodRef(id="scalar_root_finding", version="0.1.0")
    assert sr.value["root"] == 1.41421356237


def test_backends_extracted_from_provenance() -> None:
    sr = from_execution_result(_sample_er())
    assert sr.backends == [
        BackendRef(name="numpy", version="2.0.0"),
        BackendRef(name="scipy", version="1.14.0"),
    ]
    assert sr.backend_names == ["numpy", "scipy"]


def test_assumptions_become_typed() -> None:
    sr = from_execution_result(_sample_er())
    assert len(sr.assumptions) == 1
    assert sr.assumptions[0] == Assumption(
        text="bracket isolates a single root", source="execution"
    )


def test_empty_assumptions_and_backends() -> None:
    sr = from_execution_result(
        _sample_er(assumptions=[], provenance={"input_hash": "x", "backends": []})
    )
    assert sr.assumptions == []
    assert sr.backends == []


def test_scientific_result_is_frozen() -> None:
    sr = from_execution_result(_sample_er())
    try:
        sr.run_id = "mutated"  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised


def test_invalid_status_preserved() -> None:
    sr = from_execution_result(_sample_er(status=ExecutionStatus.INVALID, result={}))
    assert sr.status is ExecutionStatus.INVALID
    assert sr.value == {}


def test_public_export_from_oec_core() -> None:
    assert ScientificResult is not None
    assert callable(from_execution_result)


def test_value_is_independent_copy() -> None:
    er = _sample_er()
    sr = from_execution_result(er)
    er.result["root"] = 0.0
    assert sr.value["root"] == 1.41421356237


def test_core_module_does_not_import_domain_skills() -> None:
    # Domain packages must not be loaded as a side-effect of importing core.
    import sys

    import oec.core as core_mod

    domain = [n for n in sys.modules if n.startswith("skills.")]
    assert domain == []
    assert hasattr(core_mod, "ScientificResult")
