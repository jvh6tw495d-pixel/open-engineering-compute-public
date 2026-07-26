from oec import __version__ as oec_version
from oec.execution.provenance import (
    QuantityProvenance,
    SandboxReport,
    build_provenance,
    hash_inputs,
    installed_backends,
)


def _sandbox() -> SandboxReport:
    return SandboxReport(
        timeout_enforced=True,
        network_isolation_enforced=False,
        filesystem_isolation_enforced=False,
        memory_limit_enforced=False,
    )


def test_build_provenance_includes_oec_version() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    assert record["oec_version"] == oec_version


def test_build_provenance_reports_the_sandbox_honestly() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    assert record["sandbox"] == {
        "timeout_enforced": True,
        "network_isolation_enforced": False,
        "filesystem_isolation_enforced": False,
        "memory_limit_enforced": False,
    }


def test_build_provenance_carries_request_metadata() -> None:
    record = build_provenance(
        trace_id="trace-123", requested_by="joao", seed=42, sandbox=_sandbox()
    )
    assert record["trace_id"] == "trace-123"
    assert record["requested_by"] == "joao"
    assert record["seed"] == 42


def test_build_provenance_defaults_units_to_empty() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    assert record["units"] == {}


def test_build_provenance_preserves_original_units() -> None:
    units = {
        "voltage": QuantityProvenance(original_unit="kV", normalized_unit="V"),
    }
    record = build_provenance(
        trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox(), units=units
    )
    assert record["units"]["voltage"] == {"original_unit": "kV", "normalized_unit": "V"}


def test_build_provenance_git_commit_is_a_string_or_none() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    assert record["git_commit"] is None or isinstance(record["git_commit"], str)


def test_hash_inputs_is_stable_under_key_reordering() -> None:
    a = hash_inputs({"b": 1, "a": {"z": 2, "y": 3}})
    b = hash_inputs({"a": {"y": 3, "z": 2}, "b": 1})
    assert a == b
    assert len(a) == 64


def test_build_provenance_includes_input_hash_from_inputs() -> None:
    inputs = {"expression": "x**2 - 2", "bracket": [0, 2]}
    record = build_provenance(
        trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox(), inputs=inputs
    )
    assert record["input_hash"] == hash_inputs(inputs)


def test_build_provenance_empty_inputs_hash_is_stable() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    assert record["input_hash"] == hash_inputs({})


def test_build_provenance_lists_installed_backends() -> None:
    record = build_provenance(trace_id="abc", requested_by=None, seed=None, sandbox=_sandbox())
    names = {b["name"] for b in record["backends"]}
    # Core scientific deps of oec must appear when the test env is synced.
    assert {"numpy", "scipy", "pint"} <= names
    for backend in record["backends"]:
        assert backend["version"]
    assert installed_backends()  # non-empty in dev env
