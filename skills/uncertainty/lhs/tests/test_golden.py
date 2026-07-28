from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_lhs_seeded_shape_and_bounds() -> None:
    out = implementation.execute({"n_samples": 5, "bounds": [[0.0, 2.0], [-1.0, 1.0]], "seed": 1})
    samples = out["result"]["samples"]
    assert len(samples) == 5
    assert out["result"]["n_dim"] == 2
    for row in samples:
        assert 0.0 <= row[0] <= 2.0
        assert -1.0 <= row[1] <= 1.0


def test_lhs_deterministic_with_seed() -> None:
    a = implementation.execute({"n_samples": 4, "bounds": [[0.0, 1.0]], "seed": 7})["result"][
        "samples"
    ]
    b = implementation.execute({"n_samples": 4, "bounds": [[0.0, 1.0]], "seed": 7})["result"][
        "samples"
    ]
    assert a == b


def test_lhs_single_sample_boundary_is_deterministic_and_in_bounds() -> None:
    """n_samples=1 is the applicability floor (skill.md). A single stratum
    still yields a value inside bounds, and the same seed is deterministic."""
    out = implementation.execute({"n_samples": 1, "bounds": [[0.0, 1.0]], "seed": 0})["result"]
    assert out["n_samples"] == 1
    assert out["n_dim"] == 1
    assert len(out["samples"]) == 1
    assert 0.0 <= out["samples"][0][0] <= 1.0

    repeat = implementation.execute({"n_samples": 1, "bounds": [[0.0, 1.0]], "seed": 0})["result"]
    assert out["samples"] == repeat["samples"]
