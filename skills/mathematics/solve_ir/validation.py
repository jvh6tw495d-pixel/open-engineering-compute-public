"""Validation for mathematics.solve_ir — structural + dimensional Math IR checks."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import ValidationError

from oec.core.errors import ScientificDomainError
from oec.modeling.classify import classify
from oec.modeling.dimensions import check_equation_dimensions
from oec.modeling.ir import MathProblem
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class MathIRValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        ir_doc = normalized_inputs.get("ir")
        if not isinstance(ir_doc, dict):
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'ir' must be an object (Math IR v0 document)"],
                )
            ]

        try:
            problem = MathProblem.model_validate(ir_doc)
        except ValidationError as exc:
            return [ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[str(exc)])]

        try:
            problem_class = classify(problem)
        except ScientificDomainError as exc:
            return [ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[str(exc)])]

        if problem_class == "scalar_root":
            symbol_units = {symbol.name: symbol.unit for symbol in problem.symbols}
            try:
                for equation in problem.equations:
                    check_equation_dimensions(equation, symbol_units)
            except Exception as exc:  # noqa: BLE001
                return [
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[str(exc)])
                ]

        return []
