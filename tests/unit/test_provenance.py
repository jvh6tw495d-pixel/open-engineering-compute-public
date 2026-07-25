from oec import __version__ as oec_version
from oec.execution.provenance import QuantityProvenance, SandboxReport, build_provenance


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
