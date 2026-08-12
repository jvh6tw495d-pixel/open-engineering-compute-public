from __future__ import annotations

import pytest

from oec.neural.contracts import DistillationSpec


def test_distillation_spec_rejects_invalid_temperature() -> None:
    with pytest.raises(ValueError, match="temperature"):
        DistillationSpec(temperature=0.0)
