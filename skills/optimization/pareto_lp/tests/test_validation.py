from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").ParetoLpValidator()


def test_empty_obj() -> None:
    assert V.validate(None, {"objective_a": {}, "objective_b": {"x": 1}, "n_points": 5})  # type: ignore[arg-type]
