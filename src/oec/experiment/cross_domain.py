"""W7 — Cross-domain scientific experiment library.

Canonical ``ExperimentSpec`` builders that compose Core / Applied / Neural /
Evolutionary / Foundation skills. Pure planning — no invented numbers.
"""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
)
from oec.experiment.evolutionary import (
    build_optimize_single_experiment,
    sphere_problem_2d,
)
from oec.experiment.neural import build_mlp_regressor_experiment
from oec.experiment.specs import (
    BindSpec,
    ExperimentSpec,
    ExperimentStep,
    MetricDirection,
    MetricSpec,
    ValidationSpec,
)
from oec.neural.contracts import DatasetSpec


def build_physics_kinematics_experiment(
    *,
    experiment_id: str = "w7.physics_kinematics",
    seed: int = 0,
    t_s: float = 2.0,
    a: float = 9.81,
) -> ExperimentSpec:
    """Mechanics kinematics with target speed gate (applied sciences)."""
    return ExperimentSpec(
        id=experiment_id,
        title="W7: free-fall kinematics",
        seed=seed,
        tags=("w7", "physics", "mechanics"),
        steps=(
            ExperimentStep(
                step_id="fall",
                skill_id="mechanics.kinematics_1d",
                inputs={
                    "v0": {"value": 0.0, "unit": "m/s"},
                    "a": {"value": float(a), "unit": "m/s**2"},
                    "t": {"value": float(t_s), "unit": "s"},
                    "x0": {"value": 0.0, "unit": "m"},
                },
            ),
        ),
        metrics=(
            MetricSpec(
                name="speed",
                path="result.velocity.value",
                step_id="fall",
                direction=MetricDirection.TARGET,
                target=float(a * t_s),
                target_abs_tol=1e-6,
            ),
        ),
    )


def build_wave_then_stats_experiment(
    *,
    experiment_id: str = "w7.wave_then_stats",
    seed: int = 0,
    frequency_hz: float = 50.0,
    wavelength_m: float = 6.0,
) -> ExperimentSpec:
    """Wave phase speed then descriptive stats on a short series."""
    return ExperimentSpec(
        id=experiment_id,
        title="W7: wave phase speed + descriptive statistics",
        seed=seed,
        tags=("w7", "waves", "statistics"),
        steps=(
            ExperimentStep(
                step_id="wave",
                skill_id="waves.phase_speed",
                inputs={
                    "frequency": {"value": float(frequency_hz), "unit": "Hz"},
                    "wavelength": {"value": float(wavelength_m), "unit": "m"},
                },
            ),
            ExperimentStep(
                step_id="describe",
                skill_id="statistics.describe",
                inputs={"values": [frequency_hz, wavelength_m, frequency_hz * wavelength_m]},
            ),
        ),
        metrics=(
            MetricSpec(
                name="phase_speed",
                path="result.phase_speed.value",
                step_id="wave",
                direction=MetricDirection.TARGET,
                target=float(frequency_hz * wavelength_m),
                target_abs_tol=1e-9,
            ),
            MetricSpec(
                name="mean",
                path="result.mean",
                step_id="describe",
                direction=MetricDirection.MINIMIZE,
            ),
        ),
    )


def build_monte_carlo_then_describe_experiment(
    *,
    experiment_id: str = "w7.mc_uncertainty",
    seed: int = 0,
    n_samples: int = 200,
) -> ExperimentSpec:
    """Monte Carlo mean estimate then descriptive stats on fixed samples."""
    return ExperimentSpec(
        id=experiment_id,
        title="W7: Monte Carlo + describe",
        seed=seed,
        tags=("w7", "statistics", "uncertainty"),
        steps=(
            ExperimentStep(
                step_id="mc",
                skill_id="statistics.monte_carlo",
                inputs={
                    "expression": "x**2",
                    "n_samples": int(n_samples),
                    "low": 0.0,
                    "high": 1.0,
                    "seed": int(seed),
                    "symbol": "x",
                },
            ),
            ExperimentStep(
                step_id="describe",
                skill_id="statistics.describe",
                inputs={"values": [0.1, 0.2, 0.3, 0.4, 0.5]},
            ),
        ),
        metrics=(
            MetricSpec(
                name="mc_mean",
                path="result.mean",
                step_id="mc",
                direction=MetricDirection.TARGET,
                target=1.0 / 3.0,
                target_abs_tol=0.15,
            ),
        ),
    )


def build_evo_sphere_experiment(
    *,
    experiment_id: str = "w7.evo_sphere",
    seed: int = 0,
    generations: int = 12,
    population: int = 12,
    max_objective: float = 0.5,
) -> ExperimentSpec:
    """Evolutionary sphere optimize with objective gate."""
    return build_optimize_single_experiment(
        problem=sphere_problem_2d(),
        algorithm=EvolutionaryAlgorithmSpec(
            algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
            budget=BudgetSpec(generations=generations, population=population),
            seed=seed,
        ),
        experiment_id=experiment_id,
        seed=seed,
        max_objective=max_objective,
        title="W7: evolutionary sphere + objective gate",
    )


def build_physics_to_neural_surrogate_experiment(
    *,
    experiment_id: str = "w7.physics_neural_surrogate",
    seed: int = 0,
    epochs: int = 30,
) -> ExperimentSpec:
    """Synthetic linear law data → MLP regressor (physics-informed toy surrogate).

    Data is generated **declaratively in the experiment plan** (not by inventing
    numbers after the fact): y = 2x+1 on a fixed grid.
    """
    x = [[float(i)] for i in range(12)]
    y = [2.0 * float(i) + 1.0 for i in range(12)]
    ds = DatasetSpec(x=x, y=y, val_fraction=0.25)
    return build_mlp_regressor_experiment(
        dataset=ds,
        experiment_id=experiment_id,
        seed=seed,
        epochs=epochs,
        hidden_dims=[16],
        lr=0.05,
        title="W7: synthetic linear physics → neural surrogate",
        require_r2_min=None,
    )


def build_foundation_embed_then_stats_experiment(
    *,
    experiment_id: str = "w7.foundation_embed_stats",
    seed: int = 0,
    texts: list[str] | None = None,
    dim: int = 16,
) -> ExperimentSpec:
    """Builtin-hash embed + descriptive stats on first vector components."""
    texts = texts or ["open engineering compute", "scientific skills"]
    # After embed we cannot bind vector lists into describe easily without a
    # list path — so describe uses fixed series; embed metric checks dim.
    return ExperimentSpec(
        id=experiment_id,
        title="W7: foundation embed (builtin) + stats",
        seed=seed,
        tags=("w7", "foundation", "statistics"),
        steps=(
            ExperimentStep(
                step_id="embed",
                skill_id="foundation.embed",
                inputs={
                    "texts": texts,
                    "backend": "builtin_hash",
                    "dim": int(dim),
                    "seed": int(seed),
                    "normalize": True,
                },
            ),
            ExperimentStep(
                step_id="describe",
                skill_id="statistics.describe",
                inputs={"values": [float(dim), float(len(texts)), float(seed)]},
            ),
        ),
        metrics=(
            MetricSpec(
                name="embed_dim",
                path="result.dim",
                step_id="embed",
                direction=MetricDirection.TARGET,
                target=float(dim),
                target_abs_tol=0.0,
            ),
            MetricSpec(
                name="n_texts",
                path="result.n",
                step_id="embed",
                direction=MetricDirection.TARGET,
                target=float(len(texts)),
                target_abs_tol=0.0,
            ),
        ),
        validation=ValidationSpec(),
    )


def build_peft_train_then_generate_experiment(
    *,
    experiment_id: str = "s1.peft_train_then_generate",
    seed: int = 0,
    model_id: str = "sshleifer/tiny-gpt2",
    texts: list[str] | None = None,
    mode: str = "peft_lora",
    max_steps: int = 2,
    prompt: str = "Hello",
    max_new_tokens: int = 8,
) -> ExperimentSpec:
    """S1: train a LoRA/QLoRA/full adapter, then reload it for generation.

    ``foundation.generate``'s ``adapter_path`` is bound from
    ``foundation.peft_train``'s artifact descriptor — the reload is
    provenance-driven, not a re-guessed path. Requires ``oec[foundation]``;
    both steps fail closed without it (ADR 0041).
    """
    texts = texts or ["open engineering compute", "scientific skills for agents"]
    return ExperimentSpec(
        id=experiment_id,
        title="S1: PEFT train then adapter-reload generate",
        seed=seed,
        tags=("s1", "foundation", "peft"),
        required_extras=("foundation",),
        steps=(
            ExperimentStep(
                step_id="train",
                skill_id="foundation.peft_train",
                inputs={
                    "model_id": model_id,
                    "mode": mode,
                    "texts": texts,
                    "target_modules": ["c_attn"],
                    "max_steps": int(max_steps),
                    "max_seq_len": 32,
                    "batch_size": 2,
                    "seed": int(seed),
                },
            ),
            ExperimentStep(
                step_id="generate",
                skill_id="foundation.generate",
                inputs={
                    "prompt": prompt,
                    "model_id": model_id,
                    "max_new_tokens": int(max_new_tokens),
                    "seed": int(seed),
                },
                binds_from=(
                    BindSpec.model_validate(
                        {"step_id": "train", "path": "result.artifact.path", "as": "adapter_path"}
                    ),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                name="steps_run",
                path="result.steps_run",
                step_id="train",
                direction=MetricDirection.TARGET,
                target=float(max_steps),
                target_abs_tol=0.0,
            ),
            MetricSpec(
                name="max_new_tokens",
                path="result.max_new_tokens",
                step_id="generate",
                direction=MetricDirection.TARGET,
                target=float(max_new_tokens),
                target_abs_tol=0.0,
            ),
        ),
        validation=ValidationSpec(),
    )


def build_distill_then_eval_experiment(
    *,
    teacher_checkpoint: dict[str, Any],
    teacher_normalize: dict[str, list[float]] | None = None,
    experiment_id: str = "s2.distill_then_eval",
    seed: int = 0,
    x: list[list[float]] | None = None,
    y: list[float] | None = None,
    student_hidden_dims: list[int] | None = None,
    epochs: int = 80,
) -> ExperimentSpec:
    """S2 tabular distillation followed by evaluation of the student artifact."""
    x = x or [[float(i)] for i in range(12)]
    y = y or [2.0 * float(i) + 1.0 for i in range(12)]
    return ExperimentSpec(
        id=experiment_id,
        title="S2: tabular distill then student evaluation",
        seed=seed,
        tags=("s2", "neural", "distillation"),
        required_extras=("neural",),
        steps=(
            ExperimentStep(
                step_id="distill",
                skill_id="neural.distill",
                inputs={
                    "x": x,
                    "y": y,
                    "teacher_checkpoint": teacher_checkpoint,
                    "teacher_normalize": teacher_normalize,
                    "student_hidden_dims": student_hidden_dims or [8],
                    "epochs": int(epochs),
                    "batch_size": min(16, len(x)),
                    "max_epochs": max(int(epochs), 1),
                    "max_batch_size": min(128, max(len(x), 1)),
                    "seed": int(seed),
                },
            ),
            ExperimentStep(
                step_id="evaluate",
                skill_id="neural.evaluate",
                inputs={"x": x, "y": y, "task": "regression"},
                binds_from=(
                    BindSpec.model_validate(
                        {
                            "step_id": "distill",
                            "path": "result.checkpoint",
                            "as": "checkpoint",
                        }
                    ),
                    BindSpec.model_validate(
                        {
                            "step_id": "distill",
                            "path": "result.normalize",
                            "as": "normalize",
                        }
                    ),
                ),
            ),
        ),
        validation=ValidationSpec(),
    )


def build_root_bind_to_distribution_experiment(
    *,
    experiment_id: str = "w7.root_to_pdf",
    seed: int = 0,
) -> ExperimentSpec:
    """Math root → normal PDF at that root (bind path)."""
    return ExperimentSpec(
        id=experiment_id,
        title="W7: solve root then PDF at root",
        seed=seed,
        tags=("w7", "mathematics", "statistics"),
        steps=(
            ExperimentStep(
                step_id="root",
                skill_id="mathematics.solve_root",
                inputs={"expression": "x**2 - 4", "bracket": [0, 3]},
            ),
            ExperimentStep(
                step_id="pdf",
                skill_id="statistics.distribution_eval",
                inputs={
                    "distribution": "norm",
                    "operation": "pdf",
                    "params": {"loc": 0.0, "scale": 1.0},
                },
                binds_from=(
                    BindSpec.model_validate({"step_id": "root", "path": "result.root", "as": "x"}),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                name="pdf",
                path="result.value",
                step_id="pdf",
                direction=MetricDirection.MAXIMIZE,
            ),
        ),
    )


# Single source of truth for W7 public builders (name → fn, domains, extras).
# Imported helpers (build_optimize_single_experiment, build_mlp_regressor_*)
# must NOT appear here — MCP/CLI only expose this catalog.
_CROSS_DOMAIN_BUILDER_CATALOG: dict[str, dict[str, Any]] = {
    "build_physics_kinematics_experiment": {
        "fn": build_physics_kinematics_experiment,
        "domains": ["mechanics"],
        "extras": [],
    },
    "build_wave_then_stats_experiment": {
        "fn": build_wave_then_stats_experiment,
        "domains": ["waves", "statistics"],
        "extras": [],
    },
    "build_monte_carlo_then_describe_experiment": {
        "fn": build_monte_carlo_then_describe_experiment,
        "domains": ["statistics"],
        "extras": [],
    },
    "build_evo_sphere_experiment": {
        "fn": build_evo_sphere_experiment,
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_physics_to_neural_surrogate_experiment": {
        "fn": build_physics_to_neural_surrogate_experiment,
        "domains": ["neural"],
        "extras": ["neural"],
    },
    "build_foundation_embed_then_stats_experiment": {
        "fn": build_foundation_embed_then_stats_experiment,
        "domains": ["foundation", "statistics"],
        "extras": [],
    },
    "build_peft_train_then_generate_experiment": {
        "fn": build_peft_train_then_generate_experiment,
        "domains": ["foundation"],
        "extras": ["foundation"],
    },
    "build_distill_then_eval_experiment": {
        "fn": build_distill_then_eval_experiment,
        "domains": ["neural"],
        "extras": ["neural"],
    },
    "build_root_bind_to_distribution_experiment": {
        "fn": build_root_bind_to_distribution_experiment,
        "domains": ["mathematics", "statistics"],
        "extras": [],
    },
}


def list_cross_domain_builders() -> list[dict[str, Any]]:
    """Catalog of W7 builders for CLI / MCP / docs."""
    return [
        {
            "name": name,
            "domains": list(meta["domains"]),
            "extras": list(meta["extras"]),
        }
        for name, meta in _CROSS_DOMAIN_BUILDER_CATALOG.items()
    ]


def get_cross_domain_builder(name: str) -> Any | None:
    """Return a catalogued builder callable, or ``None`` if unknown.

    Fail-closed: only names in :func:`list_cross_domain_builders` resolve.
    Never ``getattr`` the module namespace for host-supplied names.
    """
    meta = _CROSS_DOMAIN_BUILDER_CATALOG.get(name)
    if meta is None:
        return None
    fn = meta["fn"]
    return fn if callable(fn) else None
