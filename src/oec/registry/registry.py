"""In-memory Model Registry with optional JSON catalog load/save."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from oec.registry.models import FidelityLevel, ModelRecord, ModelRegistryError


class ModelRegistry:
    """Register, query, and export model records by id/version/fidelity."""

    def __init__(self) -> None:
        self._records: dict[str, ModelRecord] = {}

    def __len__(self) -> int:
        return len(self._records)

    def register(self, record: ModelRecord, *, overwrite: bool = False) -> None:
        key = record.key
        if key in self._records and not overwrite:
            raise ModelRegistryError(
                f"model already registered: {key}",
                details={"key": key},
            )
        self._records[key] = record

    def get(self, model_id: str, version: str) -> ModelRecord:
        key = f"{model_id}@{version}"
        try:
            return self._records[key]
        except KeyError as exc:
            raise ModelRegistryError(
                f"model not found: {key}",
                details={"key": key},
            ) from exc

    def latest(self, model_id: str) -> ModelRecord:
        """Return the lexicographically greatest version for ``model_id``.

        v0 uses string sort on the version field (good enough for dotted
        numeric versions like 0.1.0, 1.0.0). Not a full SemVer parser.
        """
        matches = [r for r in self._records.values() if r.id == model_id]
        if not matches:
            raise ModelRegistryError(
                f"no versions registered for {model_id!r}",
                details={"id": model_id},
            )
        return max(matches, key=lambda r: r.version)

    def list(
        self,
        *,
        domain: str | None = None,
        fidelity: FidelityLevel | str | None = None,
        include_deprecated: bool = False,
        tag: str | None = None,
    ) -> list[ModelRecord]:
        out: list[ModelRecord] = []
        fid = FidelityLevel(fidelity) if isinstance(fidelity, str) else fidelity
        for rec in self._records.values():
            if not include_deprecated and rec.deprecated:
                continue
            if domain is not None and rec.domain != domain:
                continue
            if fid is not None and rec.fidelity != fid:
                continue
            if tag is not None and tag not in rec.tags:
                continue
            out.append(rec)
        return sorted(out, key=lambda r: (r.domain, r.id, r.version))

    def deprecate(
        self, model_id: str, version: str, *, replaced_by: str | None = None
    ) -> ModelRecord:
        old = self.get(model_id, version)
        new = old.model_copy(update={"deprecated": True, "replaced_by": replaced_by})
        self._records[new.key] = new
        return new

    def to_catalog(self) -> dict[str, object]:
        return {
            "schema_version": "0.1.0",
            "models": [r.to_manifest() for r in self.list(include_deprecated=True)],
        }

    def load_catalog(self, data: dict[str, object], *, overwrite: bool = False) -> int:
        models = data.get("models", [])
        if not isinstance(models, list):
            raise ModelRegistryError("catalog.models must be a list")
        n = 0
        for item in models:
            if not isinstance(item, dict):
                raise ModelRegistryError("catalog model entries must be objects")
            rec = ModelRecord.from_manifest(item)
            self.register(rec, overwrite=overwrite)
            n += 1
        return n

    def save_json(self, path: Path | str) -> None:
        p = Path(path)
        payload = json.dumps(self.to_catalog(), indent=2, sort_keys=True) + "\n"
        p.write_text(payload, encoding="utf-8")

    def load_json(self, path: Path | str, *, overwrite: bool = False) -> int:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ModelRegistryError("catalog root must be an object")
        return self.load_catalog(data, overwrite=overwrite)


def _builtin_records() -> Iterable[ModelRecord]:
    """Seed catalog of foundation models shipped in 2.7–2.9."""
    seeds = [
        ModelRecord(
            id="physics.coupling.wire_i2r",
            version="0.1.0",
            domain="physics.coupling",
            fidelity=FidelityLevel.MID,
            entrypoint="oec.physics.coupling.electrical_thermal:run_wire_i2r_coupling",
            title="Weak co-sim wire I²R electrical–thermal",
            summary="Gauss–Seidel coupling of resistive heating and 1-D thermal equilibrium",
            tags=("multiphysics", "2.7"),
            assumptions=("Weak staggered coupling", "Steady thermal"),
        ),
        ModelRecord(
            id="chemistry.stoichiometry.water_formation",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.REDUCED,
            entrypoint="oec.chemistry.stoichiometry:water_formation_reaction",
            title="Water formation stoichiometry",
            summary="2 H2 + O2 → 2 H2O atom-balanced reaction",
            tags=("chemistry", "2.8", "C1"),
        ),
        ModelRecord(
            id="chemistry.transport.fick_1d",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.REDUCED,
            entrypoint="oec.chemistry.transport:fick_flux_1d",
            title="1-D Fick diffusion flux",
            summary="Species transport wave-0 precondition for chemistry",
            tags=("chemistry", "2.8", "transport"),
        ),
        ModelRecord(
            id="chemistry.kinetics.arrhenius",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.MID,
            entrypoint="oec.chemistry.kinetics:arrhenius_rate_constant",
            title="Arrhenius rate constant",
            tags=("chemistry", "2.8", "C3"),
        ),
        ModelRecord(
            id="chemistry.electrochemistry.nernst",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.MID,
            entrypoint="oec.chemistry.electrochemistry:nernst_potential",
            title="Nernst cell potential",
            summary="Generic reversible cell; not BESS energy-based SOC",
            tags=("chemistry", "2.8", "C4"),
            assumptions=("Reversible cell", "Activity quotient supplied"),
        ),
        ModelRecord(
            id="chemistry.equilibrium.qc_kc",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.MID,
            entrypoint="oec.chemistry.equilibrium:evaluate_equilibrium",
            title="Concentration Qc vs Kc",
            tags=("chemistry", "2.8", "C2"),
        ),
        ModelRecord(
            id="chemistry.kinetics.batch_trajectory",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.MID,
            entrypoint="oec.chemistry.kinetics:batch_extent_trajectory",
            title="Isothermal batch extent trajectory",
            tags=("chemistry", "2.8", "C3"),
        ),
        ModelRecord(
            id="chemistry.formula.parse",
            version="0.1.0",
            domain="chemistry",
            fidelity=FidelityLevel.REDUCED,
            entrypoint="oec.chemistry.formula:parse_formula",
            title="Elemental formula parse + molar mass",
            tags=("chemistry", "2.8", "C1"),
        ),
        ModelRecord(
            id="modeling.scientific_ir.document",
            version="0.1.0",
            domain="modeling",
            fidelity=FidelityLevel.REDUCED,
            entrypoint="oec.modeling.scientific_ir:ScientificDocument",
            title="Scientific IR document v0",
            summary="Math IR + species + laws + properties envelope",
            tags=("scientific_ir", "2.9"),
        ),
    ]
    return seeds


def default_registry() -> ModelRegistry:
    """Return a registry pre-seeded with foundation models."""
    reg = ModelRegistry()
    for rec in _builtin_records():
        reg.register(rec)
    return reg


__all__ = ["ModelRegistry", "default_registry"]
