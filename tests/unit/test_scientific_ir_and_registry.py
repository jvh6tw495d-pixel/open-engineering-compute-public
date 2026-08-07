"""Unit tests for Scientific IR v0 and Model Registry (v2.9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.modeling.scientific_ir import (
    SCIENTIFIC_IR_SCHEMA_VERSION,
    ConservationGoal,
    LawRef,
    PropertyRef,
    ReactionDecl,
    ScientificDocument,
    SpeciesDecl,
)
from oec.registry import (
    FidelityLevel,
    ModelRecord,
    ModelRegistry,
    ModelRegistryError,
    default_registry,
)


def test_scientific_document_roundtrip() -> None:
    doc = ScientificDocument(
        id="demo.water",
        title="Water formation example",
        species=(
            SpeciesDecl(id="H2", name="Hydrogen", formula={"H": 2}, phase="g"),
            SpeciesDecl(id="O2", name="Oxygen", formula={"O": 2}, phase="g"),
            SpeciesDecl(id="H2O", name="Water", formula={"H": 2, "O": 1}, phase="g"),
        ),
        reactions=(
            ReactionDecl(
                id="water_formation",
                name="formation",
                nu={"H2": -2.0, "O2": -1.0, "H2O": 2.0},
            ),
        ),
        laws=(LawRef(id="chemistry.stoichiometry", domain="chemistry"),),
        properties=(PropertyRef(id="diffusivity.H2", source="table"),),
        conservation=(ConservationGoal(id="atom_H", quantity="mole", unit="mol"),),
        problem={"kind": "stoichiometry", "reaction_id": "water_formation"},
        assumptions=("Ideal gas",),
        references=("v2.9 Scientific IR v0",),
    )
    assert doc.schema_version == SCIENTIFIC_IR_SCHEMA_VERSION
    m = doc.to_manifest()
    doc2 = ScientificDocument.from_manifest(m)
    assert doc2.id == doc.id
    assert len(doc2.species) == 3
    assert doc2.reactions[0].nu["H2"] == -2.0


def test_scientific_document_rejects_unknown_species_in_reaction() -> None:
    with pytest.raises(ValueError, match="undeclared"):
        ScientificDocument(
            id="bad",
            title="bad",
            species=(SpeciesDecl(id="A", name="A", formula={"C": 1}),),
            reactions=(ReactionDecl(id="r", name="r", nu={"A": -1.0, "B": 1.0}),),
        )


def test_model_registry_register_get_list() -> None:
    reg = ModelRegistry()
    rec = ModelRecord(
        id="demo.model",
        version="1.0.0",
        domain="demo",
        fidelity=FidelityLevel.REDUCED,
        entrypoint="oec.chemistry:Species",
        title="Demo",
        tags=("t1",),
    )
    reg.register(rec)
    assert len(reg) == 1
    assert reg.get("demo.model", "1.0.0").title == "Demo"
    assert reg.latest("demo.model").version == "1.0.0"
    listed = reg.list(domain="demo", fidelity="reduced")
    assert len(listed) == 1
    with pytest.raises(ModelRegistryError):
        reg.register(rec)  # duplicate


def test_model_registry_deprecate_and_catalog(tmp_path: Path) -> None:
    reg = ModelRegistry()
    reg.register(
        ModelRecord(
            id="x",
            version="0.1.0",
            domain="d",
            fidelity=FidelityLevel.MID,
            entrypoint="mod:fn",
            title="X",
        )
    )
    reg.deprecate("x", "0.1.0", replaced_by="x@0.2.0")
    assert reg.get("x", "0.1.0").deprecated
    assert reg.list() == []  # hides deprecated
    assert len(reg.list(include_deprecated=True)) == 1

    path = tmp_path / "catalog.json"
    reg.save_json(path)
    reg2 = ModelRegistry()
    n = reg2.load_json(path)
    assert n == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1.0"


def test_default_registry_has_2_7_2_8_2_9_seeds() -> None:
    reg = default_registry()
    assert len(reg) >= 5
    chem = reg.list(domain="chemistry")
    assert any(r.id.startswith("chemistry.") for r in chem)
    coupling = reg.list(domain="physics.coupling")
    assert len(coupling) >= 1
    mid = reg.list(fidelity=FidelityLevel.MID)
    assert any(r.id.endswith("nernst") or "nernst" in r.id for r in mid)
    sir = reg.list(domain="modeling", tag="2.9")
    assert len(sir) >= 1
