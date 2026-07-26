"""Gate: agent metrics harness (plan §7 / Opus F2)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("highspy")

from benchmarks.agent_metrics import (  # noqa: E402
    run_agent_metrics,
)


def test_agent_metrics_gates_green() -> None:
    report = run_agent_metrics(skills_root=_ROOT / "skills")
    assert report.n_ops_demos >= 2
    assert report.ops_valid_first_attempt_rate == 1.0
    assert report.classification_accuracy == 1.0
    assert report.invented_number_rate == 0.0
    assert report.reviewer_catch_rate == 1.0
    assert report.gates_green() is True
    d = report.to_dict()
    assert "details" in d
