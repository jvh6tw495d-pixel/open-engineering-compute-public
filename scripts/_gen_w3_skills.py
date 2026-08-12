"""One-shot generator for W3 applied-sciences skill packages."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills"


def write_skill(
    domain: str,
    name: str,
    skill_id: str,
    title: str,
    method_id: str,
    input_schema: dict,
    example_input: dict,
    impl_code: str,
    *,
    dimensional: bool = False,
    tags: list[str] | None = None,
) -> None:
    d = ROOT / domain / name
    (d / "examples").mkdir(parents=True, exist_ok=True)
    (d / "tests").mkdir(parents=True, exist_ok=True)
    tag_lines = "\n".join(f"  - {t}" for t in (tags or []))
    yaml = f"""id: {skill_id}
version: 0.1.0
status: experimental
domain: {domain}
title: {title}

entrypoint:
  module: implementation
  function: execute

schemas:
  input: input.schema.json
  output: output.schema.json

method:
  id: {method_id}
  version: 0.1.0
  iterative: false

execution:
  deterministic: true
  timeout_seconds: 10
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: {"true" if dimensional else "false"}
  mathematical: true
  physical: false
  numerical: true

references:
  - "Framework W3 Applied Sciences foundations"
  - "Classical textbook identities; OEC governs contract"

tags:
  - w3
  - applied-sciences
{tag_lines}
"""
    (d / "skill.yaml").write_text(yaml, encoding="utf-8")
    (d / "skill.md").write_text(
        f"""---
id: {skill_id}
version: 0.1.0
status: experimental
domain: {domain}
title: {title}
---

# Purpose

{title}. OEC governs the skill contract; numerical merit is classical
physics/chemistry as cited in references.

# Official methodology

Method id: `{method_id}`.

# Changelog

- 0.1.0: W3-MVP initial.
""",
        encoding="utf-8",
    )
    (d / "references.md").write_text(
        "# References\n\n- Framework roadmap W3 Applied Sciences\n",
        encoding="utf-8",
    )
    (d / "input.schema.json").write_text(
        json.dumps(input_schema, indent=2) + "\n", encoding="utf-8"
    )
    (d / "output.schema.json").write_text(
        json.dumps({"type": "object", "additionalProperties": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    (d / "implementation.py").write_text(impl_code, encoding="utf-8")
    (d / "validation.py").write_text(
        textwrap.dedent(
            f'''\
            """Validation for {skill_id}."""

            from __future__ import annotations

            from typing import Any, ClassVar

            from oec.skills.loader.models import LoadedSkill


            class Validator:
                layer: ClassVar[str] = "mathematical"

                def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
                    del skill, normalized_inputs
                    return []
            '''
        ),
        encoding="utf-8",
    )
    (d / "examples" / "example.json").write_text(
        json.dumps({"description": title, "input": example_input}, indent=2) + "\n",
        encoding="utf-8",
    )
    (d / "tests" / "test_golden.py").write_text(
        textwrap.dedent(
            """\
            import json
            from pathlib import Path

            from oec.testing import load_skill_module

            _SKILL_DIR = Path(__file__).resolve().parent.parent
            implementation = load_skill_module(_SKILL_DIR, "implementation")


            def test_example_runs() -> None:
                path = _SKILL_DIR / "examples" / "example.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                out = implementation.execute(data["input"])
                assert "result" in out
            """
        ),
        encoding="utf-8",
    )
    print("wrote", skill_id)


def qv(unit: str, *, positive: bool = False) -> dict:
    value: dict = {"type": "number"}
    if positive:
        value["exclusiveMinimum"] = 0
    return {
        "type": "object",
        "properties": {"value": value, "unit": {"type": "string"}},
        "required": ["value", "unit"],
        "additionalProperties": False,
        "x-oec-unit": unit,
    }


def main() -> None:
    write_skill(
        "waves",
        "phase_speed",
        "waves.phase_speed",
        "Wave Phase Speed (v = f λ)",
        "wave_phase_speed",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["frequency", "wavelength"],
            "properties": {
                "frequency": qv("Hz", positive=True),
                "wavelength": qv("m", positive=True),
            },
        },
        {"frequency": {"value": 50.0, "unit": "Hz"}, "wavelength": {"value": 6.0, "unit": "m"}},
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.kernel.units.quantity import QuantityValue
            from oec.physics.waves import (
                angular_frequency,
                period_from_frequency,
                phase_speed,
                wave_number,
            )


            def _qv(field: dict[str, Any]) -> QuantityValue:
                return QuantityValue(value=float(field["value"]), unit=field["unit"])


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                f = _qv(inputs["frequency"])
                lam = _qv(inputs["wavelength"])
                v = phase_speed(f, lam)
                return {
                    "result": {
                        "phase_speed": v.model_dump(mode="json"),
                        "period": period_from_frequency(f).model_dump(mode="json"),
                        "angular_frequency": angular_frequency(f).model_dump(mode="json"),
                        "wave_number": wave_number(lam).model_dump(mode="json"),
                    },
                    "diagnostics": {},
                }
            """
        ),
        dimensional=True,
        tags=["waves"],
    )

    write_skill(
        "optics",
        "snell",
        "optics.snell",
        "Snell's Law Refraction",
        "optics_snell",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["n1", "n2", "theta1_rad"],
            "properties": {
                "n1": {"type": "number", "exclusiveMinimum": 0},
                "n2": {"type": "number", "exclusiveMinimum": 0},
                "theta1_rad": {"type": "number", "minimum": 0, "maximum": 1.5707963267948966},
            },
        },
        {"n1": 1.0, "n2": 1.5, "theta1_rad": 0.5},
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.physics.optics import snell_refracted_angle


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                out = snell_refracted_angle(
                    float(inputs["n1"]), float(inputs["n2"]), float(inputs["theta1_rad"])
                )
                return {
                    "result": out,
                    "diagnostics": {"total_internal_reflection": out["total_internal_reflection"]},
                }
            """
        ),
        tags=["optics"],
    )

    write_skill(
        "optics",
        "thin_lens",
        "optics.thin_lens",
        "Thin Lens Image Distance",
        "optics_thin_lens",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["focal_length_m", "object_distance_m"],
            "properties": {
                "focal_length_m": {"type": "number"},
                "object_distance_m": {"type": "number"},
            },
        },
        {"focal_length_m": 0.1, "object_distance_m": 0.2},
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.physics.optics import thin_lens_image_distance, thin_lens_magnification


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                f = float(inputs["focal_length_m"])
                u = float(inputs["object_distance_m"])
                v = thin_lens_image_distance(f, u)
                m = thin_lens_magnification(u, v)
                return {
                    "result": {
                        "image_distance_m": v,
                        "magnification": m,
                        "focal_length_m": f,
                        "object_distance_m": u,
                    },
                    "diagnostics": {},
                }
            """
        ),
        tags=["optics"],
    )

    write_skill(
        "em",
        "coulomb",
        "em.coulomb",
        "Coulomb Force Magnitude",
        "em_coulomb",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["charge1", "charge2", "separation"],
            "properties": {
                "charge1": qv("C"),
                "charge2": qv("C"),
                "separation": qv("m", positive=True),
            },
        },
        {
            "charge1": {"value": 1e-6, "unit": "C"},
            "charge2": {"value": 1e-6, "unit": "C"},
            "separation": {"value": 0.1, "unit": "m"},
        },
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.kernel.units.quantity import QuantityValue
            from oec.physics.electromagnetism import coulomb_force


            def _qv(field: dict[str, Any]) -> QuantityValue:
                return QuantityValue(value=float(field["value"]), unit=field["unit"])


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                f = coulomb_force(
                    _qv(inputs["charge1"]), _qv(inputs["charge2"]), _qv(inputs["separation"])
                )
                return {"result": {"force": f.model_dump(mode="json")}, "diagnostics": {}}
            """
        ),
        dimensional=True,
        tags=["em"],
    )

    write_skill(
        "em",
        "parallel_plate_capacitor",
        "em.parallel_plate_capacitor",
        "Parallel-Plate Capacitor",
        "em_parallel_plate_capacitor",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["area", "gap"],
            "properties": {
                "area": qv("m ** 2", positive=True),
                "gap": qv("m", positive=True),
                "relative_permittivity": {"type": "number", "exclusiveMinimum": 0, "default": 1.0},
                "voltage": qv("V"),
            },
        },
        {
            "area": {"value": 0.01, "unit": "m**2"},
            "gap": {"value": 0.001, "unit": "m"},
            "relative_permittivity": 1.0,
            "voltage": {"value": 10.0, "unit": "V"},
        },
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.kernel.units.quantity import QuantityValue
            from oec.physics.electromagnetism import (
                capacitor_energy,
                parallel_plate_capacitance,
                parallel_plate_field,
            )


            def _qv(field: dict[str, Any]) -> QuantityValue:
                return QuantityValue(value=float(field["value"]), unit=field["unit"])


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                c = parallel_plate_capacitance(
                    _qv(inputs["area"]),
                    _qv(inputs["gap"]),
                    relative_permittivity=float(inputs.get("relative_permittivity", 1.0)),
                )
                result: dict[str, Any] = {"capacitance": c.model_dump(mode="json")}
                if "voltage" in inputs:
                    v = _qv(inputs["voltage"])
                    result["electric_field"] = parallel_plate_field(
                        v, _qv(inputs["gap"])
                    ).model_dump(mode="json")
                    result["energy"] = capacitor_energy(c, v).model_dump(mode="json")
                return {"result": result, "diagnostics": {}}
            """
        ),
        dimensional=True,
        tags=["em"],
    )

    write_skill(
        "statistical_physics",
        "ideal_gas",
        "statistical_physics.ideal_gas",
        "Ideal Gas Law",
        "ideal_gas_eos",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["amount_mol", "temperature", "volume"],
            "properties": {
                "amount_mol": {"type": "number", "exclusiveMinimum": 0},
                "temperature": qv("K", positive=True),
                "volume": qv("m ** 3", positive=True),
                "molar_mass_kg_per_mol": {"type": "number", "exclusiveMinimum": 0},
            },
        },
        {
            "amount_mol": 1.0,
            "temperature": {"value": 273.15, "unit": "K"},
            "volume": {"value": 0.0224, "unit": "m**3"},
            "molar_mass_kg_per_mol": 0.028,
        },
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.kernel.units.quantity import QuantityValue
            from oec.physics.statistical import ideal_gas_pressure, rms_speed_monatomic


            def _qv(field: dict[str, Any]) -> QuantityValue:
                return QuantityValue(value=float(field["value"]), unit=field["unit"])


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                p = ideal_gas_pressure(
                    float(inputs["amount_mol"]),
                    _qv(inputs["temperature"]),
                    _qv(inputs["volume"]),
                )
                result: dict[str, Any] = {"pressure": p.model_dump(mode="json")}
                if "molar_mass_kg_per_mol" in inputs:
                    result["rms_speed"] = rms_speed_monatomic(
                        float(inputs["molar_mass_kg_per_mol"]), _qv(inputs["temperature"])
                    ).model_dump(mode="json")
                return {"result": result, "diagnostics": {}}
            """
        ),
        dimensional=True,
        tags=["statistical"],
    )

    write_skill(
        "mechanics",
        "kinematics_1d",
        "mechanics.kinematics_1d",
        "1D Uniform Acceleration Kinematics",
        "mechanics_kinematics_1d",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["v0", "a", "t"],
            "properties": {
                "v0": qv("m / s"),
                "a": qv("m / s ** 2"),
                "t": qv("s", positive=True),
                "x0": qv("m"),
            },
        },
        {
            "v0": {"value": 0.0, "unit": "m/s"},
            "a": {"value": 9.81, "unit": "m/s**2"},
            "t": {"value": 2.0, "unit": "s"},
            "x0": {"value": 0.0, "unit": "m"},
        },
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.kernel.units.quantity import QuantityValue
            from oec.physics.mechanics import (
                uniform_acceleration_position,
                uniform_acceleration_velocity,
            )


            def _qv(field: dict[str, Any]) -> QuantityValue:
                return QuantityValue(value=float(field["value"]), unit=field["unit"])


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                v0 = _qv(inputs["v0"])
                a = _qv(inputs["a"])
                t = _qv(inputs["t"])
                x0 = _qv(inputs["x0"]) if "x0" in inputs else QuantityValue(value=0.0, unit="m")
                v = uniform_acceleration_velocity(v0, a, t)
                x = uniform_acceleration_position(x0, v0, a, t)
                return {
                    "result": {
                        "velocity": v.model_dump(mode="json"),
                        "position": x.model_dump(mode="json"),
                    },
                    "diagnostics": {},
                }
            """
        ),
        dimensional=True,
        tags=["mechanics"],
    )

    write_skill(
        "chemistry",
        "vanthoff",
        "chemistry.vanthoff",
        "van't Hoff Equilibrium Constant Shift",
        "chemistry_vanthoff",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["k1", "t1_k", "t2_k", "delta_h_j_per_mol"],
            "properties": {
                "k1": {"type": "number", "exclusiveMinimum": 0},
                "t1_k": {"type": "number", "exclusiveMinimum": 0},
                "t2_k": {"type": "number", "exclusiveMinimum": 0},
                "delta_h_j_per_mol": {"type": "number"},
            },
        },
        {"k1": 1.0, "t1_k": 298.15, "t2_k": 310.15, "delta_h_j_per_mol": 50000.0},
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.chemistry.thermochemistry import vanthoff_k2


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                out = vanthoff_k2(
                    k1=float(inputs["k1"]),
                    t1_k=float(inputs["t1_k"]),
                    t2_k=float(inputs["t2_k"]),
                    delta_h_j_per_mol=float(inputs["delta_h_j_per_mol"]),
                )
                assumptions = [
                    a.text if hasattr(a, "text") else str(a) for a in out["assumptions"]
                ]
                result = {k: v for k, v in out.items() if k != "assumptions"}
                result["assumptions"] = assumptions
                return {"result": result, "diagnostics": {}}
            """
        ),
        tags=["chemistry", "thermochemistry"],
    )

    write_skill(
        "chemistry",
        "hess_enthalpy",
        "chemistry.hess_enthalpy",
        "Hess Law Reaction Enthalpy",
        "chemistry_hess_enthalpy",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["steps"],
            "properties": {
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["delta_h_j_per_mol"],
                        "properties": {
                            "delta_h_j_per_mol": {"type": "number"},
                            "coefficient": {"type": "number", "default": 1.0},
                        },
                    },
                }
            },
        },
        {
            "steps": [
                {"delta_h_j_per_mol": -285800.0, "coefficient": 1.0},
                {"delta_h_j_per_mol": -393500.0, "coefficient": -1.0},
            ]
        },
        textwrap.dedent(
            """\
            from __future__ import annotations

            from typing import Any

            from oec.chemistry.thermochemistry import hess_reaction_enthalpy


            def execute(inputs: dict[str, Any]) -> dict[str, Any]:
                out = hess_reaction_enthalpy(list(inputs["steps"]))
                assumptions = [
                    a.text if hasattr(a, "text") else str(a) for a in out["assumptions"]
                ]
                return {
                    "result": {
                        "delta_h_j_per_mol": out["delta_h_j_per_mol"],
                        "n_steps": out["n_steps"],
                        "assumptions": assumptions,
                    },
                    "diagnostics": {},
                }
            """
        ),
        tags=["chemistry", "thermochemistry"],
    )
    print("done")


if __name__ == "__main__":
    main()
