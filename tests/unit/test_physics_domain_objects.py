"""Executable domain-object and conservation-result contracts."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics import (
    BoundaryCondition,
    ConservationCheck,
    ConservationLaw,
    MaterialProperty,
    PhysicalLaw,
    PhysicsDomain,
    PhysicsResult,
    ValidityFrame,
)


def _assumptions() -> tuple[Assumption, ...]:
    return (Assumption(text="steady state", source="unit-test stub"),)


def _validity(*domains: PhysicsDomain) -> ValidityFrame:
    return ValidityFrame(domains=domains, description="Wave 1 executable stub")


def test_four_domain_objects_are_instantiable_with_shared_assumptions() -> None:
    physical_law = PhysicalLaw(
        id="dummy.linear",
        name="Dummy linear law",
        hypotheses=_assumptions(),
        validity=_validity(PhysicsDomain.MECHANICS),
        references=("unit-test oracle",),
        evaluator=lambda state: float(state["coefficient"] * state["input"]),
    )
    conservation_law = ConservationLaw(
        id="dummy.balance",
        name="Dummy balance",
        hypotheses=_assumptions(),
        validity=_validity(PhysicsDomain.ELECTRICAL, PhysicsDomain.THERMAL),
        references=("unit-test oracle",),
        evaluator=lambda state: float(state["inflow"] - state["outflow"] - state["stored"]),
    )
    material_property = MaterialProperty(
        id="dummy.conductivity",
        name="Dummy conductivity",
        hypotheses=_assumptions(),
        validity=_validity(PhysicsDomain.MATERIALS),
        references=("unit-test datasheet",),
        value=QuantityValue(value=12.0, unit="W/(m*K)"),
    )
    boundary_condition = BoundaryCondition(
        id="dummy.temperature.boundary",
        name="Dummy fixed temperature",
        hypotheses=_assumptions(),
        validity=_validity(PhysicsDomain.THERMAL),
        references=("unit-test setup",),
        condition_type="dirichlet",
        value=QuantityValue(value=300.0, unit="K"),
        target="node-1",
    )

    assert physical_law.evaluate({"coefficient": 2.0, "input": 3.0}) == 6.0
    assert conservation_law.hypotheses[0].text == "steady state"
    assert material_property.hypotheses[0].source == "unit-test stub"
    assert boundary_condition.hypotheses[0].text == "steady state"
    with pytest.raises(ValidationError):
        material_property.name = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("domain_stub", "unit", "expected_balanced"),
    [
        ({"domain": "electrical", "inflow": 100.0, "outflow": 99.95, "stored": 0.0}, "W", True),
        ({"domain": "thermal", "inflow": 500.0, "outflow": 498.0, "stored": 0.0}, "W", False),
    ],
)
def test_conservation_law_executes_across_two_domain_stubs(
    domain_stub: dict[str, Any], unit: str, expected_balanced: bool
) -> None:
    law = ConservationLaw(
        id="generic.steady_balance",
        name="Generic steady balance",
        hypotheses=_assumptions(),
        validity=_validity(PhysicsDomain.ELECTRICAL, PhysicsDomain.THERMAL),
        references=("hand-solved dummy balance",),
        evaluator=lambda state: float(state["inflow"] - state["outflow"] - state["stored"]),
    )

    check = law.check(domain_stub, atol=0.1, rtol=0.001, scale=100.0, unit=unit)

    assert isinstance(check, ConservationCheck)
    assert check.balanced is expected_balanced
    assert check.atol == 0.1
    assert check.rtol == 0.001
    assert check.scale == 100.0
    assert check.unit == unit


def test_result_types_are_strict_and_do_not_collapse_status_to_success() -> None:
    result = PhysicsResult(
        residual=0.05,
        balanced=True,
        atol=0.1,
        rtol=0.001,
        scale=10.0,
        unit="W",
    )

    assert "success" not in type(result).model_fields
    with pytest.raises(ValidationError):
        ConservationCheck(
            residual=0.0,
            balanced=True,
            atol=0.0,
            rtol=0.0,
            scale=0.0,
            unit="W",
            success=True,
        )
