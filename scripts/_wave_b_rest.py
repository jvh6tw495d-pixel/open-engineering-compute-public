"""Remaining Wave B skill scaffolds."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def scaffold_rest(
    root: Path,
    w: Callable[[Path, str], None],
    yaml: Callable[..., str],
    jdump: Callable[[object], str],
) -> None:
    # --- morris ---
    b = root / "uncertainty" / "morris"
    w(b / "skill.yaml", yaml("uncertainty.morris", "Morris Elementary Effects", "morris_linear_screen"))
    w(
        b / "skill.md",
        """---
id: uncertainty.morris
---

# Purpose

Morris elementary-effects screening for a linear model
`f(x) = intercept + coeffs·x` on rectangular bounds.

# Official methodology

Method id: `morris_linear_screen`. Reports `mu`, `mu_star`, `sigma` per factor.

# Known limitations

- Linear models only (no arbitrary callables in the sandbox).
""",
    )
    w(b / "references.md", "# References\n\n1. Morris (1991), Technometrics.\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "bounds": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {"type": "number"},
                        },
                    },
                    "coeffs": {"type": "array", "minItems": 1, "items": {"type": "number"}},
                    "intercept": {"type": "number"},
                    "n_trajectories": {"type": "integer", "exclusiveMinimum": 0},
                    "n_levels": {"type": "integer", "minimum": 2},
                    "seed": {"type": ["integer", "null"]},
                },
                "required": ["bounds", "coeffs"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "mu": {"type": "array", "items": {"type": "number"}},
                    "mu_star": {"type": "array", "items": {"type": "number"}},
                    "sigma": {"type": "array", "items": {"type": "number"}},
                    "n_dim": {"type": "integer"},
                    "n_trajectories": {"type": "integer"},
                    "n_levels": {"type": "integer"},
                    "delta_unit": {"type": "number"},
                    "model": {"type": "string"},
                    "seed": {"type": ["integer", "null"]},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                },
                "required": ["mu", "mu_star", "sigma", "n_dim", "backend", "converged"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""uncertainty.morris entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.morris import morris_screen


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = morris_screen(
        inputs["bounds"],
        inputs["coeffs"],
        intercept=float(inputs.get("intercept", 0.0)),
        n_trajectories=int(inputs.get("n_trajectories", 10)),
        n_levels=int(inputs.get("n_levels", 4)),
        seed=inputs.get("seed"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_dim": out["n_dim"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MorrisValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        bounds = normalized_inputs.get("bounds")
        coeffs = normalized_inputs.get("coeffs")
        if not isinstance(bounds, list) or not isinstance(coeffs, list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["bounds and coeffs required"],
                )
            ]
        if len(bounds) != len(coeffs):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["coeffs length must match bounds"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "two_factor_linear.json",
        jdump(
            {
                "description": "Linear f=2*x0; mu_star of factor 0 dominates",
                "input": {
                    "bounds": [[0.0, 1.0], [0.0, 1.0]],
                    "coeffs": [2.0, 0.0],
                    "n_trajectories": 20,
                    "seed": 0,
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.MorrisValidator()


def test_length_mismatch() -> None:
    out = V.validate(None, {"bounds": [[0, 1]], "coeffs": [1.0, 2.0]})  # type: ignore[arg-type]
    assert out and out[0].severity.value == "error"
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_active_factor_has_larger_mu_star() -> None:
    out = implementation.execute(
        {
            "bounds": [[0.0, 1.0], [0.0, 1.0]],
            "coeffs": [3.0, 0.0],
            "n_trajectories": 30,
            "seed": 1,
        }
    )["result"]
    assert out["mu_star"][0] > out["mu_star"][1]
    assert abs(out["mu"][0] - 3.0) < 0.5
''',
    )

    # --- propagate_linear ---
    b = root / "uncertainty" / "propagate_linear"
    w(
        b / "skill.yaml",
        yaml("uncertainty.propagate_linear", "Linear Uncertainty Propagation", "linear_delta_method"),
    )
    w(
        b / "skill.md",
        """---
id: uncertainty.propagate_linear
---

# Purpose

First-order (delta-method) uncertainty propagation: `Σ_y = J Σ_x Jᵀ`.

# Official methodology

Method id: `linear_delta_method`. Jacobian may be a gradient or matrix.
""",
    )
    w(b / "references.md", "# References\n\n1. Standard first-order error propagation / delta method.\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "jacobian": {},
                    "covariance": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "array", "items": {"type": "number"}},
                    },
                    "nominal": {"type": ["array", "null"], "items": {"type": "number"}},
                },
                "required": ["jacobian", "covariance"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "output_dim": {"type": "integer"},
                    "variance": {},
                    "std": {},
                    "covariance": {"type": "array"},
                    "nominal": {"type": ["array", "null"]},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                    "method": {"type": "string"},
                },
                "required": [
                    "output_dim",
                    "variance",
                    "std",
                    "covariance",
                    "backend",
                    "converged",
                    "method",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""uncertainty.propagate_linear entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.propagate import propagate_linear


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = propagate_linear(
        inputs["jacobian"],
        inputs["covariance"],
        nominal=inputs.get("nominal"),
    )
    return {
        "result": out,
        "diagnostics": {
            "output_dim": out["output_dim"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class PropagateLinearValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        cov = normalized_inputs.get("covariance")
        if not isinstance(cov, list) or not cov or not isinstance(cov[0], list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["covariance must be a square matrix"],
                )
            ]
        n = len(cov)
        if any(not isinstance(row, list) or len(row) != n for row in cov):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["covariance must be square"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "scalar_sum.json",
        jdump(
            {
                "description": "y=x0+x1 independent unit var -> var=2",
                "input": {
                    "jacobian": [1.0, 1.0],
                    "covariance": [[1.0, 0.0], [0.0, 1.0]],
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.PropagateLinearValidator()


def test_nonsquare() -> None:
    out = V.validate(
        None, {"jacobian": [1, 1], "covariance": [[1.0, 0.0]]}
    )  # type: ignore[arg-type]
    assert out
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_independent_sum_variance() -> None:
    out = implementation.execute(
        {
            "jacobian": [1.0, 1.0],
            "covariance": [[1.0, 0.0], [0.0, 1.0]],
        }
    )["result"]
    assert abs(out["variance"] - 2.0) < 1e-12
    assert abs(out["std"] - 2.0**0.5) < 1e-12
''',
    )

    # --- state_space_simulate ---
    b = root / "dynamics" / "state_space_simulate"
    w(
        b / "skill.yaml",
        yaml(
            "dynamics.state_space_simulate",
            "LTI State-Space Simulate",
            "lti_state_space_sim",
        ),
    )
    w(
        b / "skill.md",
        """---
id: dynamics.state_space_simulate
---

# Purpose

Simulate an LTI state-space model under a sampled input sequence.

# Official methodology

Discrete: `x⁺=Ax+Bu`, `y=Cx+Du`. Continuous: ZOH via matrix exponential then same.
""",
    )
    w(b / "references.md", "# References\n\n1. Chen — Linear System Theory.\n2. SciPy `expm` for continuous ZOH.\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "A": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "B": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "C": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "D": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "u": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "x0": {"type": "array", "items": {"type": "number"}},
                    "dt": {"type": "number", "exclusiveMinimum": 0},
                    "time_base": {
                        "type": "string",
                        "enum": ["discrete", "continuous"],
                    },
                },
                "required": ["A", "B", "C", "D", "u", "x0", "dt"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "t": {"type": "array", "items": {"type": "number"}},
                    "x": {"type": "array"},
                    "y": {"type": "array"},
                    "n_steps": {"type": "integer"},
                    "n_states": {"type": "integer"},
                    "n_inputs": {"type": "integer"},
                    "n_outputs": {"type": "integer"},
                    "dt": {"type": "number"},
                    "time_base": {"type": "string"},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                },
                "required": ["t", "x", "y", "n_steps", "backend", "converged"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""dynamics.state_space_simulate entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.dynamics.state_space import simulate_state_space


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = simulate_state_space(
        inputs["A"],
        inputs["B"],
        inputs["C"],
        inputs["D"],
        inputs["u"],
        inputs["x0"],
        dt=float(inputs["dt"]),
        time_base=str(inputs.get("time_base", "discrete")),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_steps": out["n_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class StateSpaceValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("A")
        if not isinstance(a, list) or not a or len(a) != len(a[0]):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be square"],
                )
            ]
        if float(normalized_inputs.get("dt", 0)) <= 0:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["dt must be > 0"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "integrator.json",
        jdump(
            {
                "description": "Discrete integrator",
                "input": {
                    "A": [[1.0]],
                    "B": [[1.0]],
                    "C": [[1.0]],
                    "D": [[0.0]],
                    "u": [[1.0], [1.0], [1.0]],
                    "x0": [0.0],
                    "dt": 1.0,
                    "time_base": "discrete",
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.StateSpaceValidator()


def test_nonsquare() -> None:
    assert V.validate(None, {"A": [[1.0, 0.0]], "dt": 1.0})  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_discrete_integrator_ramp() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "B": [[1.0]],
            "C": [[1.0]],
            "D": [[0.0]],
            "u": [[1.0], [1.0], [1.0]],
            "x0": [0.0],
            "dt": 1.0,
            "time_base": "discrete",
        }
    )["result"]
    assert out["x"] == [[0.0], [1.0], [2.0]]
    assert out["y"] == [[0.0], [1.0], [2.0]]
''',
    )

    # --- stability_margins ---
    b = root / "dynamics" / "stability_margins"
    w(
        b / "skill.yaml",
        yaml("dynamics.stability_margins", "LTI Stability Margins", "eigenvalue_stability"),
    )
    w(
        b / "skill.md",
        """---
id: dynamics.stability_margins
---

# Purpose

Eigenvalue-based stability check for an LTI state matrix A.

# Official methodology

Continuous: stable iff all Re(λ)<0. Discrete: stable iff all |λ|<1.
""",
    )
    w(b / "references.md", "# References\n\n1. Classical LTI eigenvalue stability criteria.\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "A": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "time_base": {
                        "type": "string",
                        "enum": ["continuous", "discrete"],
                    },
                },
                "required": ["A"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "eigenvalues_real": {"type": "array", "items": {"type": "number"}},
                    "eigenvalues_imag": {"type": "array", "items": {"type": "number"}},
                    "eigenvalues_modulus": {"type": "array", "items": {"type": "number"}},
                    "stable": {"type": "boolean"},
                    "stability_margin": {"type": "number"},
                    "criterion": {"type": "string"},
                    "time_base": {"type": "string"},
                    "n": {"type": "integer"},
                    "spectral_abscissa": {"type": "number"},
                    "spectral_radius": {"type": "number"},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                },
                "required": [
                    "eigenvalues_real",
                    "eigenvalues_imag",
                    "stable",
                    "stability_margin",
                    "criterion",
                    "time_base",
                    "backend",
                    "converged",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""dynamics.stability_margins entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.dynamics.stability import stability_margins


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = stability_margins(
        inputs["A"],
        time_base=str(inputs.get("time_base", "continuous")),
    )
    return {
        "result": out,
        "diagnostics": {
            "stable": out["stable"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class StabilityValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("A")
        if not isinstance(a, list) or not a or not isinstance(a[0], list) or len(a) != len(a[0]):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be square"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "stable_scalar.json",
        jdump({"description": "A=[-1] continuous stable", "input": {"A": [[-1.0]], "time_base": "continuous"}}),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.StabilityValidator()


def test_square_required() -> None:
    assert V.validate(None, {"A": [[1.0, 2.0]]})  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_stable_continuous() -> None:
    out = implementation.execute({"A": [[-2.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is True
    assert abs(out["stability_margin"] - 2.0) < 1e-12


def test_unstable_continuous() -> None:
    out = implementation.execute({"A": [[1.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is False
''',
    )

    # --- pid_discrete ---
    b = root / "control" / "pid_discrete"
    w(b / "skill.yaml", yaml("control.pid_discrete", "Discrete PID Controller", "position_pid_discrete"))
    w(
        b / "skill.md",
        """---
id: control.pid_discrete
---

# Purpose

Position-form discrete PID over aligned reference and measurement series.

# Official methodology

`u = Kp e + Ki dt Σe + Kd Δe/dt` with optional saturation.
""",
    )
    w(b / "references.md", "# References\n\n1. Åström & Hägglund — PID Controllers.\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "reference": {"type": "array", "minItems": 1, "items": {"type": "number"}},
                    "measurement": {"type": "array", "minItems": 1, "items": {"type": "number"}},
                    "kp": {"type": "number"},
                    "ki": {"type": "number"},
                    "kd": {"type": "number"},
                    "dt": {"type": "number", "exclusiveMinimum": 0},
                    "u_min": {"type": ["number", "null"]},
                    "u_max": {"type": ["number", "null"]},
                },
                "required": ["reference", "measurement", "kp", "ki", "kd", "dt"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "u": {"type": "array", "items": {"type": "number"}},
                    "error": {"type": "array", "items": {"type": "number"}},
                    "n": {"type": "integer"},
                    "kp": {"type": "number"},
                    "ki": {"type": "number"},
                    "kd": {"type": "number"},
                    "dt": {"type": "number"},
                    "saturated_steps": {"type": "integer"},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                    "method": {"type": "string"},
                },
                "required": ["u", "error", "n", "backend", "converged", "method"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""control.pid_discrete entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.control.pid import pid_discrete


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = pid_discrete(
        inputs["reference"],
        inputs["measurement"],
        kp=float(inputs["kp"]),
        ki=float(inputs["ki"]),
        kd=float(inputs["kd"]),
        dt=float(inputs["dt"]),
        u_min=inputs.get("u_min"),
        u_max=inputs.get("u_max"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n": out["n"],
            "saturated_steps": out["saturated_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class PidValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        r = normalized_inputs.get("reference")
        m = normalized_inputs.get("measurement")
        if not isinstance(r, list) or not isinstance(m, list) or len(r) != len(m) or not r:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["reference and measurement must be equal non-empty lists"],
                )
            ]
        if float(normalized_inputs.get("dt", 0)) <= 0:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["dt must be > 0"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "proportional_step.json",
        jdump(
            {
                "description": "P-only",
                "input": {
                    "reference": [1.0, 1.0],
                    "measurement": [0.0, 0.0],
                    "kp": 2.0,
                    "ki": 0.0,
                    "kd": 0.0,
                    "dt": 0.1,
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.PidValidator()


def test_length_mismatch() -> None:
    assert V.validate(
        None, {"reference": [1.0], "measurement": [0.0, 0.0], "dt": 0.1}
    )  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_proportional_only() -> None:
    out = implementation.execute(
        {
            "reference": [1.0, 1.0, 1.0],
            "measurement": [0.0, 0.0, 0.0],
            "kp": 2.0,
            "ki": 0.0,
            "kd": 0.0,
            "dt": 0.1,
        }
    )["result"]
    assert out["u"] == [2.0, 2.0, 2.0]
    assert out["error"] == [1.0, 1.0, 1.0]
''',
    )

    # --- kalman_filter ---
    b = root / "control" / "kalman_filter"
    w(
        b / "skill.yaml",
        yaml(
            "control.kalman_filter",
            "Discrete Linear Kalman Filter",
            "discrete_linear_kalman",
            iterative=True,
        ),
    )
    w(
        b / "skill.md",
        """---
id: control.kalman_filter
---

# Purpose

Discrete time-invariant linear Kalman filter (predict–update).

# Official methodology

Standard KF equations with constant A,B,C,Q,R. Optional input sequence `u`.
""",
    )
    w(b / "references.md", "# References\n\n1. Kalman (1960).\n")
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "A": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "B": {
                        "type": ["array", "null"],
                        "items": {"type": "array", "items": {"type": "number"}},
                    },
                    "C": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "Q": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "R": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "z": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "x0": {"type": "array", "items": {"type": "number"}},
                    "P0": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "u": {
                        "type": ["array", "null"],
                        "items": {"type": "array", "items": {"type": "number"}},
                    },
                },
                "required": ["A", "C", "Q", "R", "z", "x0", "P0"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "x_filtered": {"type": "array"},
                    "innovations": {"type": "array"},
                    "n_steps": {"type": "integer"},
                    "n_states": {"type": "integer"},
                    "n_outputs": {"type": "integer"},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                    "method": {"type": "string"},
                },
                "required": [
                    "x_filtered",
                    "innovations",
                    "n_steps",
                    "backend",
                    "converged",
                    "method",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""control.kalman_filter entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.control.kalman import kalman_filter_linear


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = kalman_filter_linear(
        inputs["A"],
        inputs.get("B"),
        inputs["C"],
        inputs["Q"],
        inputs["R"],
        inputs["z"],
        inputs["x0"],
        inputs["P0"],
        u=inputs.get("u"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_steps": out["n_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class KalmanValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("A")
        if not isinstance(a, list) or not a or len(a) != len(a[0]):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be square"],
                )
            ]
        z = normalized_inputs.get("z")
        if not isinstance(z, list) or not z:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["z must be a non-empty series"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "static_scalar.json",
        jdump(
            {
                "description": "Static scalar KF step",
                "input": {
                    "A": [[1.0]],
                    "C": [[1.0]],
                    "Q": [[0.0]],
                    "R": [[1.0]],
                    "z": [[5.0]],
                    "x0": [0.0],
                    "P0": [[1.0]],
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.KalmanValidator()


def test_requires_z() -> None:
    assert V.validate(None, {"A": [[1.0]], "z": []})  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_static_scalar_moves_toward_measurement() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "C": [[1.0]],
            "Q": [[0.0]],
            "R": [[1.0]],
            "z": [[5.0]],
            "x0": [0.0],
            "P0": [[1.0]],
        }
    )["result"]
    assert abs(out["x_filtered"][0][0] - 2.5) < 1e-12
''',
    )
