"""VerificationReport model tests (ADR 0021)."""

from __future__ import annotations

from oec.verification.report import PostVerificationCheck, PreVerificationCheck, VerificationReport


def test_pre_check_defaults() -> None:
    check = PreVerificationCheck(name="input_validation", passed=True)
    assert check.message is None
    assert check.details == {}


def test_post_check_defaults() -> None:
    check = PostVerificationCheck(name="convergence", passed=True)
    assert check.message is None
    assert check.details == {}


def test_verification_report_defaults_to_empty_lists() -> None:
    report = VerificationReport()
    assert report.pre == []
    assert report.post == []


def test_verification_report_round_trips_through_json() -> None:
    report = VerificationReport(
        pre=[PreVerificationCheck(name="backend_fit", passed=False, message="missing")],
        post=[PostVerificationCheck(name="lp_gap", passed=True, details={"mip_gap": 0.01})],
    )
    dumped = report.model_dump(mode="json")
    assert dumped["pre"][0]["name"] == "backend_fit"
    assert dumped["post"][0]["details"]["mip_gap"] == 0.01
