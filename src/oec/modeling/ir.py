"""Math IR v0: a versioned, closed Pydantic model set for problems OEC
compiles to existing governed backends (ADR 0020).

Every expression node is one of a fixed set of discriminated types — there
is no way to construct a node outside this set, and no node type accepts
arbitrary Python. This is what lets a Math IR document be built entirely
from validated JSON (or from :func:`oec.modeling.expressions.parse_expression`,
which builds the same node types from a string via the audited AST whitelist
in :mod:`oec.kernel.numerics.expressions` — never ``eval``/``exec``).

The ``linear_program`` variant deliberately reuses OPS's own
:class:`~oec.ops.models.OPSObjective`/:class:`~oec.ops.models.OPSConstraint`
rather than a second linear representation ("tied to OPS", per
``docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md`` section 6.1).
"""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oec.kernel.numerics.expressions import ALLOWED_FUNCTIONS
from oec.kernel.units.constants import constants
from oec.kernel.units.quantity import QuantityValue
from oec.ops.models import OPSConstraint, OPSObjective

IR_SCHEMA_VERSION = "0.1.0"


class Symbol(BaseModel):
    """A named unknown/parameter: optionally dimensioned, optionally bounded."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    unit: str | None = None  # None => dimensionless
    lower: float | None = None
    upper: float | None = None

    @field_validator("unit")
    @classmethod
    def _validate_unit(cls, value: str | None) -> str | None:
        if value is None:
            return value
        QuantityValue(value=1.0, unit=value)  # raises ValueError if not Pint-parseable
        return value


class NumberLiteral(BaseModel):
    """A plain, dimensionless numeric literal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["number"] = "number"
    value: float

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: float) -> float:
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"literal value must be finite, got {value!r}")
        return value


class QuantityLiteral(BaseModel):
    """A dimensioned literal — a :class:`QuantityValue` embedded in the tree."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["quantity"] = "quantity"
    value: QuantityValue


class ConstantRef(BaseModel):
    """A reference to a named entry in the SI constants catalogue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["constant"] = "constant"
    key: str

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        if value not in constants():
            raise ValueError(f"unknown scientific constant {value!r}")
        return value


class SymbolRef(BaseModel):
    """A reference to a declared :class:`Symbol` by name."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["symbol"] = "symbol"
    name: str


class UnaryOp(BaseModel):
    """Unary plus/minus over a sub-expression."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["unary"] = "unary"
    op: Literal["+", "-"]
    operand: Expr


class BinaryOp(BaseModel):
    """A binary arithmetic operation over two sub-expressions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["binary"] = "binary"
    op: Literal["+", "-", "*", "/", "**"]
    left: Expr
    right: Expr


class FunctionCall(BaseModel):
    """A call to one of the fixed set of allowed math functions.

    The allowed names are exactly :data:`oec.kernel.numerics.expressions.ALLOWED_FUNCTIONS`
    — one audited whitelist, not a second one redefined here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["call"] = "call"
    name: str
    args: list[Expr]

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if value not in ALLOWED_FUNCTIONS:
            raise ValueError(f"unknown function {value!r}; allowed: {sorted(ALLOWED_FUNCTIONS)}")
        return value


Expr = Annotated[
    NumberLiteral | QuantityLiteral | ConstantRef | SymbolRef | UnaryOp | BinaryOp | FunctionCall,
    Field(discriminator="kind"),
]

for _node_cls in (UnaryOp, BinaryOp, FunctionCall):
    _node_cls.model_rebuild()


class Equation(BaseModel):
    """An equality constraint ``lhs == rhs`` (residual is ``lhs - rhs``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lhs: Expr
    rhs: Expr


Equation.model_rebuild()


class MathProblem(BaseModel):
    """The Math IR v0 root document.

    Exactly one of the two variants applies, determined by
    :func:`oec.modeling.classify.classify` (never silently):

    - ``linear_program``: ``objective`` is set; ``constraints`` are OPS-shaped.
    - ``scalar_root``: ``equations``/``unknowns`` are set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ir_version: str = IR_SCHEMA_VERSION
    problem_class: Literal["linear_program", "scalar_root"] | None = None
    symbols: list[Symbol]
    assumptions: list[str] = Field(default_factory=list)
    notes: str = ""

    # linear_program variant (tied to OPS — see module docstring).
    sense: Literal["min", "max"] = "min"
    objective: OPSObjective | None = None
    constraints: list[OPSConstraint] = Field(default_factory=list)

    # scalar_root variant (v0: exactly one equation, one unknown).
    equations: list[Equation] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    initial_guess: dict[str, float] = Field(default_factory=dict)
    bracket: dict[str, tuple[float, float]] = Field(default_factory=dict)

    @field_validator("ir_version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if value != IR_SCHEMA_VERSION:
            raise ValueError(f"ir_version must be {IR_SCHEMA_VERSION!r}, got {value!r}")
        return value

    @model_validator(mode="after")
    def _cross_field(self) -> MathProblem:
        names = [s.name for s in self.symbols]
        if len(names) != len(set(names)):
            raise ValueError("duplicate symbol names")
        name_set = set(names)

        for symbol in self.symbols:
            bounds_inverted = (
                symbol.lower is not None
                and symbol.upper is not None
                and symbol.lower > symbol.upper
            )
            if bounds_inverted:
                raise ValueError(
                    f"symbol {symbol.name!r} has lower bound > upper bound "
                    f"({symbol.lower} > {symbol.upper})"
                )

        if self.objective is not None:
            unknown_obj = set(self.objective.coeffs) - name_set
            if unknown_obj:
                raise ValueError(f"objective references unknown symbols: {sorted(unknown_obj)}")

        for constraint in self.constraints:
            unknown_cons = set(constraint.coeffs) - name_set
            if unknown_cons:
                raise ValueError(
                    f"constraint {constraint.name!r} references unknown symbols: "
                    f"{sorted(unknown_cons)}"
                )

        unknown_unknowns = set(self.unknowns) - name_set
        if unknown_unknowns:
            raise ValueError(f"unknowns reference undeclared symbols: {sorted(unknown_unknowns)}")

        extra_guess = set(self.initial_guess) - set(self.unknowns)
        if extra_guess:
            raise ValueError(f"initial_guess references undeclared unknowns: {sorted(extra_guess)}")

        extra_bracket = set(self.bracket) - set(self.unknowns)
        if extra_bracket:
            raise ValueError(f"bracket references undeclared unknowns: {sorted(extra_bracket)}")

        return self
