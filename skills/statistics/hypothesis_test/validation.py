"""Mathematical validation for statistics.hypothesis_test."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class HypothesisTestValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        test = normalized_inputs.get("test")
        if test in {"t_one_sample", "ks_1samp"} and "sample" not in normalized_inputs:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"test {test!r} requires 'sample'"],
                )
            ]
        if test in {"t_two_sample", "mannwhitney"}:
            missing = [k for k in ("sample_a", "sample_b") if k not in normalized_inputs]
            if missing:
                return [
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[f"test {test!r} requires {missing}"],
                    )
                ]
        return []
