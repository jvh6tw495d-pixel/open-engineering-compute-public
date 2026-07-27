"""Unit tests for oec.core Scientific Kernel (domain-independent)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from oec.common import VersionedRef
from oec.core import (
    Assumption,
    BackendRef,
    BackendUnavailableError,
    Diagnostic,
    MethodRef,
    ProvenanceRecord,
    ScientificDomainError,
    ScientificResult,
    ValidityDomain,
    from_execution_result,
)
from oec.execution.models import ExecutionResult, ExecutionStatus


def _sample_er(**kwargs: object) -> ExecutionResult:
    base = {
        "run_id": "run-test-001",
        "status": ExecutionStatus.VALIDATED,
        "skill": VersionedRef(id="mathematics.solve_root", version="0.1.0"),
        "method": VersionedRef(id="scalar_root_finding", version="0.1.0"),
        "result": {"root": 1.41421356237, "method": "brentq"},
        "assumptions": ["bracket isolates a single root"],
        "diagnostics": {"converged": True, "nit": 8},
        "warnings": [],
        "validation": {"outcomes": []},
        "provenance": {
            "input_hash": "abc123",
            "oec_version": "2.0.0",
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
    assert isinstance(sr, ScientificResult)
    assert sr.run_id == "run-test-001"
    assert sr.status is ExecutionStatus.VALIDATED
    assert sr.skill_id == "mathematics.solve_root"
    assert sr.skill_version == "0.1.0"
    assert sr.method == MethodRef(id="scalar_root_finding", version="0.1.0")
    assert sr.value["root"] == 1.41421356237


def test_backends_via_provenance_record() -> None:
    sr = from_execution_result(_sample_er())
    assert sr.backends == [
        BackendRef(name="numpy", version="2.0.0"),
        BackendRef(name="scipy", version="1.14.0"),
    ]
    assert sr.backend_names == ["numpy", "scipy"]
    assert sr.provenance.input_hash == "abc123"
    assert isinstance(sr.provenance, ProvenanceRecord)


def test_assumptions_and_diagnostics_typed() -> None:
    sr = from_execution_result(_sample_er())
    assert sr.assumptions[0] == Assumption(
        text="bracket isolates a single root", source="execution"
    )
    assert any(isinstance(d, Diagnostic) for d in sr.diagnostics)
    assert any(d.code == "converged" for d in sr.diagnostics)
    assert sr.diagnostics_raw.get("nit") == 8


def test_empty_assumptions_and_backends() -> None:
    sr = from_execution_result(
        _sample_er(assumptions=[], provenance={"input_hash": "x", "backends": []})
    )
    assert sr.assumptions == []
    assert sr.backends == []


def test_scientific_result_is_frozen() -> None:
    sr = from_execution_result(_sample_er())
    with pytest.raises(ValidationError):
        sr.run_id = "mutated"  # type: ignore[misc]


def test_invalid_status_preserved() -> None:
    sr = from_execution_result(_sample_er(status=ExecutionStatus.INVALID, result={}))
    assert sr.status is ExecutionStatus.INVALID
    assert sr.value == {}


def test_value_is_independent_copy() -> None:
    er = _sample_er()
    sr = from_execution_result(er)
    er.result["root"] = 0.0
    assert sr.value["root"] == 1.41421356237


def test_validity_domain_optional() -> None:
    vd = ValidityDomain(description="x in bracket", constraints=["bracket isolates root"])
    sr = from_execution_result(_sample_er(), validity=vd)
    assert sr.validity is not None
    assert sr.validity.description == "x in bracket"


def test_core_errors_are_oec_errors() -> None:
    err = ScientificDomainError("out of domain", details={"param": "x"})
    assert err.code == "scientific_domain_error"
    assert err.to_dict()["details"]["param"] == "x"
    assert BackendUnavailableError("no highs").code == "backend_unavailable"


def test_core_module_does_not_import_domain_skills() -> None:
    """Verify the import boundary in a fresh interpreter, not pytest's process.

    Other tests legitimately import domain skills. Inspecting this process's
    ``sys.modules`` therefore makes this architectural check order-dependent.
    """
    import subprocess
    import sys

    probe = """
import sys
import oec.core as core_mod

domain = sorted(name for name in sys.modules if name.startswith('skills.'))
assert not domain, domain
assert hasattr(core_mod, 'ScientificResult')
assert hasattr(core_mod, 'ValidityDomain')
assert hasattr(core_mod, 'Diagnostic')
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "oec.core imported domain skills in a fresh interpreter:\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
