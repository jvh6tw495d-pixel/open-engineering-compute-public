"""Pydantic models + validation for OPS v0.1."""

from __future__ import annotations

from typing import Any, Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oec.errors import OECValidationError
from oec.ops.schema import OPS_JSON_SCHEMA, OPS_SCHEMA_VERSION


class OPSVariable(BaseModel):
    """One decision variable: name, kind, and its own bounds/objective coefficient."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["continuous", "integer", "binary"] = "continuous"
    lower: float | None = 0.0
    upper: float | None = None
    objective_coeff: float = 0.0


class OPSConstraint(BaseModel):
    """One linear constraint: ``sum(coeffs[name] * name) <sense> rhs``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    coeffs: dict[str, float]
    sense: Literal["<=", ">=", "="]
    rhs: float


class OPSObjective(BaseModel):
    """Linear objective: ``sum(coeffs[name] * name) + offset``."""

    model_config = ConfigDict(extra="forbid")

    coeffs: dict[str, float] = Field(default_factory=dict)
    offset: float = 0.0


class OPSExecutionLimits(BaseModel):
    """Solver execution limits (e.g. a wall-clock time budget)."""

    model_config = ConfigDict(extra="forbid")

    time_limit_seconds: float | None = None


class OPSProblem(BaseModel):
    """Canonical OEC Problem Specification (no arbitrary Python)."""

    model_config = ConfigDict(extra="forbid")

    ops_version: str = OPS_SCHEMA_VERSION
    problem_class: Literal["lp", "milp"]
    sense: Literal["min", "max"]
    name: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    notes: str | None = None
    variables: list[OPSVariable]
    constraints: list[OPSConstraint] = Field(default_factory=list)
    objective: OPSObjective
    execution_limits: OPSExecutionLimits = Field(default_factory=OPSExecutionLimits)

    @field_validator("ops_version")
    @classmethod
    def _version(cls, value: str) -> str:
        if value != OPS_SCHEMA_VERSION:
            raise ValueError(f"ops_version must be {OPS_SCHEMA_VERSION!r}, got {value!r}")
        return value

    @model_validator(mode="after")
    def _cross_field(self) -> OPSProblem:
        names = [v.name for v in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("duplicate variable names")
        name_set = set(names)

        for var in self.variables:
            if var.kind == "binary":
                # Binary implies [0,1]; allow explicit bounds only if compatible.
                lo = 0.0 if var.lower is None else var.lower
                hi = 1.0 if var.upper is None else var.upper
                if lo < 0 or hi > 1:
                    raise ValueError(f"binary variable {var.name!r} must be within [0, 1]")
            if var.lower is not None and var.upper is not None and var.lower > var.upper:
                raise ValueError(
                    f"variable {var.name!r} has lower bound > upper bound "
                    f"({var.lower} > {var.upper})"
                )

        for cons in self.constraints:
            if not cons.coeffs:
                raise ValueError(f"constraint {cons.name!r} has empty coeffs")
            unknown = set(cons.coeffs) - name_set
            if unknown:
                raise ValueError(
                    f"constraint {cons.name!r} references unknown variables: {sorted(unknown)}"
                )

        unknown_obj = set(self.objective.coeffs) - name_set
        if unknown_obj:
            raise ValueError(f"objective references unknown variables: {sorted(unknown_obj)}")

        has_int = any(v.kind in ("integer", "binary") for v in self.variables)
        if self.problem_class == "lp" and has_int:
            raise ValueError("problem_class='lp' forbids integer/binary variables; use 'milp'")
        if self.problem_class == "milp" and not has_int:
            raise ValueError("problem_class='milp' requires at least one integer/binary variable")

        # Merge objective coeffs into variables for the solver adapter.
        return self


def validate_ops(document: dict[str, Any]) -> OPSProblem:
    """Validate a raw OPS dict (JSON Schema + semantic rules)."""
    try:
        jsonschema.validate(instance=document, schema=OPS_JSON_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise OECValidationError(
            f"OPS schema invalid: {exc.message}",
            code="ops_schema_invalid",
            details={"path": list(exc.path), "message": exc.message},
        ) from exc
    try:
        return OPSProblem.model_validate(document)
    except Exception as exc:
        raise OECValidationError(
            f"OPS semantic invalid: {exc}",
            code="ops_semantic_invalid",
            details={"error": str(exc)},
        ) from exc
