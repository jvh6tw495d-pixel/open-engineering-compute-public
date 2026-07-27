from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.PidValidator()


def test_length_mismatch() -> None:
    assert V.validate(
        None, {"reference": [1.0], "measurement": [0.0, 0.0], "dt": 0.1}
    )  # type: ignore[arg-type]
