"""Mathematical validation for statistics.distribution_eval."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"
_OPS_NEED_X = frozenset({"pdf", "cdf"})
_OPS_NEED_P = frozenset({"ppf"})


class DistributionEvalValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        op = normalized_inputs.get("operation")
        if op in _OPS_NEED_X and "x" not in normalized_inputs:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"operation {op!r} requires 'x'"],
                )
            ]
        if op in _OPS_NEED_P and "p" not in normalized_inputs:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"operation {op!r} requires 'p'"],
                )
            ]
        params = normalized_inputs.get("params") or {}
        dist = normalized_inputs.get("distribution")
        if dist == "t" and "df" not in params:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["distribution 't' requires params.df"],
                )
            ]
        if dist == "chi2" and "df" not in params:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["distribution 'chi2' requires params.df"],
                )
            ]
        if dist == "beta" and ("a" not in params or "b" not in params):
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["distribution 'beta' requires params.a and params.b"],
                )
            ]
        return []
