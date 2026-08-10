"""Part B E-D0/E-D1 contracts (no pymoo required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.evolutionary.contracts import EvolutionaryProblemSpec, VariableSpec
from oec.evolutionary.runtime import EvolutionaryRuntimeSpec, InequalityConstraintSpec


def test_runtime_resolved_seeds() -> None:
    rt = EvolutionaryRuntimeSpec(seed=7)
    assert rt.resolved_seeds() == [7]
    rt2 = EvolutionaryRuntimeSpec(seed=0, seeds=[1, 2, 3])
    assert rt2.resolved_seeds() == [1, 2, 3]


def test_hv_reference_validation() -> None:
    with pytest.raises(ValidationError):
        EvolutionaryRuntimeSpec(hv_reference=[1.0])
    ok = EvolutionaryRuntimeSpec(hv_reference=[1.0, 1.0])
    assert len(ok.hv_reference or []) == 2


def test_constraint_spec() -> None:
    c = InequalityConstraintSpec(
        name="g1",
        tree={"op": "sub", "args": [{"const": 1.0}, {"var": "x"}]},
    )
    assert c.name == "g1"


def test_problem_constraints_shape() -> None:
    with pytest.raises(ValidationError):
        EvolutionaryProblemSpec(
            variables=[VariableSpec(name="x", lower=0, upper=1)],
            constraints=[{"name": "bad"}],  # missing tree
        )
