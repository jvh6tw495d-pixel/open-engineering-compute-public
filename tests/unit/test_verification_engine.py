"""Verification Engine unit tests (ADR 0021).

Mirrors the fake-skill/real-skill-loading pattern established in
``tests/unit/test_execution_service.py``: a minimal skill directory is
written via ``oec.testing.write_skill_dir`` and loaded for real, so
``skill.manifest`` is a genuine ``SkillManifest`` rather than a hand-rolled
stub.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.skills.loader.loader import load_skill
from oec.testing import write_skill_dir
from oec.validation.base import Severity, ValidationOutcome
from oec.verification.engine import run_post_verification, run_pre_verification


def _load(tmp_path: Path, **write_kwargs: object) -> object:
    skill_dir = write_skill_dir(tmp_path, **write_kwargs)
    return load_skill(skill_dir)


def test_pre_verification_passes_with_no_outcomes(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    checks = run_pre_verification(skill, [])
    by_name = {c.name: c for c in checks}
    assert by_name["input_validation"].passed is True
    assert by_name["backend_fit"].passed is True


def test_pre_verification_input_validation_fails_on_schema_error(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    outcomes = [
        ValidationOutcome(layer="schema", severity=Severity.ERROR, messages=["missing field"])
    ]
    checks = run_pre_verification(skill, outcomes)
    by_name = {c.name: c for c in checks}
    assert by_name["input_validation"].passed is False
    assert "missing field" in by_name["input_validation"].message


def test_pre_verification_ignores_non_input_layers(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    outcomes = [ValidationOutcome(layer="numerical", severity=Severity.ERROR, messages=["oops"])]
    checks = run_pre_verification(skill, outcomes)
    by_name = {c.name: c for c in checks}
    assert by_name["input_validation"].passed is True


def test_pre_verification_backend_fit_fails_for_unavailable_highs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = _load(
        tmp_path,
        manifest_overrides={"method": {"id": "highs_lp", "version": "1", "iterative": True}},
    )

    import oec.backends.fallback as fallback
    from oec.backends.registry import BackendCapability

    monkeypatch.setattr(
        fallback,
        "get_backend_capabilities",
        lambda: [
            BackendCapability(
                name="highs", available=False, reason="nope", domains=frozenset({"lp"})
            )
        ],
    )

    checks = run_pre_verification(skill, [])
    by_name = {c.name: c for c in checks}
    assert by_name["backend_fit"].passed is False


def test_post_verification_convergence_only_for_iterative_methods(tmp_path: Path) -> None:
    non_iterative = _load(tmp_path)
    checks = run_post_verification(non_iterative, {}, {}, [], {})
    assert "convergence" not in {c.name for c in checks}

    iterative = _load(
        tmp_path,
        name="iterative_skill",
        manifest_overrides={
            "id": "mathematics.iterative_skill",
            "method": {"id": "identity", "version": "1", "iterative": True},
        },
        front_matter_overrides={"id": "mathematics.iterative_skill"},
    )
    checks = run_post_verification(iterative, {}, {"converged": True}, [], {})
    by_name = {c.name: c for c in checks}
    assert by_name["convergence"].passed is True


def test_post_verification_convergence_fails_when_not_converged(tmp_path: Path) -> None:
    skill = _load(
        tmp_path,
        manifest_overrides={"method": {"id": "identity", "version": "1", "iterative": True}},
    )
    checks = run_post_verification(skill, {}, {"converged": False}, [], {})
    by_name = {c.name: c for c in checks}
    assert by_name["convergence"].passed is False


def test_post_verification_residuals_summary_from_numerical_outcomes(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    outcomes = [
        ValidationOutcome(
            layer="numerical", severity=Severity.WARNING, messages=["poorly conditioned"]
        )
    ]
    checks = run_post_verification(skill, {}, {}, outcomes, {})
    by_name = {c.name: c for c in checks}
    assert by_name["residuals_and_conditioning"].passed is False
    assert "poorly conditioned" in by_name["residuals_and_conditioning"].message


def test_post_verification_lp_gap_report_is_informational_when_present(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    checks = run_post_verification(skill, {"mip_gap": 0.05}, {}, [], {})
    by_name = {c.name: c for c in checks}
    assert by_name["lp_gap_report"].passed is None
    assert by_name["lp_gap_report"].details["mip_gap"] == 0.05


def test_post_verification_lp_gap_report_omitted_when_absent(tmp_path: Path) -> None:
    """No mip_gap in the result -> no lp_gap_report entry at all, not a
    padded always-passing placeholder."""
    skill = _load(tmp_path)
    checks = run_post_verification(skill, {}, {}, [], {})
    assert "lp_gap_report" not in {c.name for c in checks}


def test_post_verification_provenance_integrity_checks_input_hash(tmp_path: Path) -> None:
    skill = _load(tmp_path)
    checks = run_post_verification(skill, {}, {}, [], {"input_hash": "abc123"})
    by_name = {c.name: c for c in checks}
    assert by_name["provenance_integrity"].passed is True

    checks_missing = run_post_verification(skill, {}, {}, [], {})
    by_name_missing = {c.name: c for c in checks_missing}
    assert by_name_missing["provenance_integrity"].passed is False
