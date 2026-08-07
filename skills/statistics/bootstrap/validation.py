from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class BootstrapValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        samples = normalized_inputs.get("samples")
        if not isinstance(samples, list) or not samples:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["samples must be a non-empty 1D list"],
                )
            ]
        if any(not isinstance(x, (int, float)) for x in samples):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["samples must contain numbers only"],
                )
            ]
        statistic = normalized_inputs.get("statistic", "mean")
        if statistic not in ("mean", "median", "variance"):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[f"unsupported statistic {statistic!r}"],
                )
            ]
        return []