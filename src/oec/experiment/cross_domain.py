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
    build_hybrid_training_experiment,
    build_hyperneat_experiment,
    build_neat_experiment,
    build_nsga2_experiment,
    build_optimize_single_experiment,
    problem_to_optimize_inputs,
    sphere_problem_2d,
)
from oec.experiment.neural import build_mlp_regressor_experiment, mlp_regressor_inputs
from oec.experiment.specs import (
    BindSpec,
    ExperimentSpec,
    ExperimentStep,
    MetricDirection,
    MetricSpec,
    ValidationSpec,
)
from oec.neural.contracts import DatasetSpec

_TINY_GPT2 = "sshleifer/tiny-gpt2"
_TINY_GPT2_REVISION = "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"


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
    model_id: str = _TINY_GPT2,
    revision: str = _TINY_GPT2_REVISION,
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
    if mode == "full":
        raise ValueError(
            "build_peft_train_then_generate_experiment cannot reload a full "
            "checkpoint via adapter_path; use mode='peft_lora'"
        )
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
                    "revision": revision,
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
                    "revision": revision,
                    "max_new_tokens": int(max_new_tokens),
                    "seed": int(seed),
                },
                binds_from=(
                    BindSpec.model_validate(
                        {"step_id": "train", "path": "result.artifact.path", "as": "adapter_path"}
                    ),
                    BindSpec.model_validate(
                        {
                            "step_id": "train",
                            "path": "result.artifact.sha256",
                            "as": "adapter_sha256",
                        }
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
    distill_inputs: dict[str, Any] = {
        "x": x,
        "y": y,
        "teacher_checkpoint": teacher_checkpoint,
        "student_hidden_dims": student_hidden_dims or [8],
        "epochs": int(epochs),
        "batch_size": min(16, len(x)),
        "max_epochs": max(int(epochs), 1),
        "max_batch_size": min(128, max(len(x), 1)),
        "seed": int(seed),
    }
    if teacher_normalize is not None:
        distill_inputs["teacher_normalize"] = teacher_normalize
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
                inputs=distill_inputs,
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


def build_full_stack_learning_experiment(
    *,
    experiment_id: str = "learning.full_stack",
    seed: int = 0,
    generations: int = 8,
    population: int = 10,
    mlp_epochs: int = 20,
    distill_epochs: int = 8,
    hybrid_evaluations: int = 3,
    peft_steps: int = 1,
    model_id: str = _TINY_GPT2,
    revision: str = _TINY_GPT2_REVISION,
) -> ExperimentSpec:
    """One small experiment: AG + NSGA-II + MLP + distill + hybrid + embed + PEFT.

    Smoke budgets only. Metrics are recorded, not quality claims.
    ``.train()`` still never auto-installs extras.
    """
    x = [[float(i)] for i in range(12)]
    y = [2.0 * float(i) + 1.0 for i in range(12)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.25)
    ga = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.GENETIC_ALGORITHM,
        budget=BudgetSpec(generations=generations, population=population),
        seed=seed,
    )
    nsga = build_nsga2_experiment(
        n_var=3,
        generations=max(4, generations // 2),
        population=max(8, population),
        seed=seed,
        experiment_id=f"{experiment_id}.nsga2",
    )
    train_inputs = mlp_regressor_inputs(
        dataset=dataset,
        hidden_dims=[8],
        epochs=mlp_epochs,
        lr=0.05,
        seed=seed,
        device="cpu",
    )
    return ExperimentSpec(
        id=experiment_id,
        title="Full-stack Learning: AG + neural + foundation LLM tools",
        description=(
            "Genetic algorithm on sphere, NSGA-II, MLP teacher, tabular distill, "
            "hybrid evo+gradient, builtin embed, PEFT LoRA, adapter-reload generate."
        ),
        seed=seed,
        tags=("learning", "evolutionary", "neural", "foundation", "full-stack"),
        required_extras=("evolutionary", "neural", "foundation"),
        steps=(
            ExperimentStep(
                step_id="ag",
                skill_id="evolutionary.optimize_single",
                inputs=problem_to_optimize_inputs(sphere_problem_2d(), ga),
            ),
            ExperimentStep(
                step_id="nsga2",
                skill_id="evolutionary.nsga2",
                inputs=dict(nsga.steps[0].inputs),
            ),
            ExperimentStep(
                step_id="train",
                skill_id="neural.mlp.regressor",
                inputs=train_inputs,
            ),
            ExperimentStep(
                step_id="distill",
                skill_id="neural.distill",
                inputs={
                    "x": x,
                    "y": y,
                    "student_hidden_dims": [4],
                    "epochs": int(distill_epochs),
                    "batch_size": 8,
                    "max_epochs": int(distill_epochs),
                    "max_batch_size": 16,
                    "seed": int(seed),
                },
                binds_from=(
                    BindSpec.model_validate(
                        {
                            "step_id": "train",
                            "path": "result.checkpoint",
                            "as": "teacher_checkpoint",
                        }
                    ),
                    BindSpec.model_validate(
                        {"step_id": "train", "path": "result.normalize", "as": "teacher_normalize"}
                    ),
                ),
            ),
            ExperimentStep(
                step_id="evaluate",
                skill_id="neural.evaluate",
                inputs={"x": x, "y": y, "task": "regression"},
                binds_from=(
                    BindSpec.model_validate(
                        {"step_id": "distill", "path": "result.checkpoint", "as": "checkpoint"}
                    ),
                    BindSpec.model_validate(
                        {"step_id": "distill", "path": "result.normalize", "as": "normalize"}
                    ),
                ),
            ),
            ExperimentStep(
                step_id="hybrid",
                skill_id="neural.training.hybrid",
                inputs={
                    "x": x,
                    "y": y,
                    "seed": int(seed),
                    "max_evaluations": int(hybrid_evaluations),
                    "inner_epochs": 3,
                    "epochs": 6,
                },
            ),
            ExperimentStep(
                step_id="embed",
                skill_id="foundation.embed",
                inputs={
                    "texts": [
                        "OEC Learning full-stack experiment",
                        "genetic algorithm, neural nets, PEFT",
                    ],
                    "backend": "builtin_hash",
                    "dim": 8,
                    "seed": int(seed),
                    "normalize": True,
                },
            ),
            ExperimentStep(
                step_id="peft",
                skill_id="foundation.peft_train",
                inputs={
                    "model_id": model_id,
                    "revision": revision,
                    "mode": "peft_lora",
                    "texts": [
                        "Open Engineering Compute governs training.",
                        "Adapters reload from a pinned artifact path.",
                    ],
                    "target_modules": ["c_attn"],
                    "max_steps": int(peft_steps),
                    "max_seq_len": 32,
                    "batch_size": 1,
                    "seed": int(seed),
                },
            ),
            ExperimentStep(
                step_id="generate",
                skill_id="foundation.generate",
                inputs={
                    "prompt": "OEC",
                    "model_id": model_id,
                    "revision": revision,
                    "max_new_tokens": 8,
                    "seed": int(seed),
                },
                binds_from=(
                    BindSpec.model_validate(
                        {"step_id": "peft", "path": "result.artifact.path", "as": "adapter_path"}
                    ),
                    BindSpec.model_validate(
                        {
                            "step_id": "peft",
                            "path": "result.artifact.sha256",
                            "as": "adapter_sha256",
                        }
                    ),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                name="ag_best_objective",
                path="result.best_objective",
                step_id="ag",
                direction=MetricDirection.MINIMIZE,
            ),
            MetricSpec(
                name="nsga2_nondominated",
                path="result.n_nondominated",
                step_id="nsga2",
                direction=MetricDirection.MAXIMIZE,
            ),
            MetricSpec(
                name="mlp_train_r2",
                path="result.train_metrics.r_squared",
                step_id="train",
                direction=MetricDirection.MAXIMIZE,
            ),
            MetricSpec(
                name="student_eval_r2",
                path="result.metrics.r_squared",
                step_id="evaluate",
                direction=MetricDirection.MAXIMIZE,
            ),
            MetricSpec(
                name="embed_dim",
                path="result.dim",
                step_id="embed",
                direction=MetricDirection.TARGET,
                target=8.0,
                target_abs_tol=0.0,
            ),
            MetricSpec(
                name="peft_steps",
                path="result.steps_run",
                step_id="peft",
                direction=MetricDirection.TARGET,
                target=float(peft_steps),
                target_abs_tol=0.0,
            ),
        ),
        validation=ValidationSpec(),
    )


def build_vision_head_vs_backbone_experiment(
    *,
    examples: list[dict[str, object]],
    n_classes: int,
    experiment_id: str = "vision.head_vs_backbone",
    seed: int = 0,
    epochs: int = 8,
    backbone: str = "resnet18",
    backbone_weights: str = "none",
    hidden_dims: list[int] | None = None,
    clip_revision: str | None = None,
) -> ExperimentSpec:
    """Compare MLP-on-frozen-features vs fine-tuned head on the same local images.

    This is the application pattern: the backbone is a backend; OEC owns the
    head and the comparison. Default weights=none so CI does not download ImageNet.
    """
    hidden = hidden_dims or [64, 64]
    shared: dict[str, object] = {
        "examples": examples,
        "n_classes": int(n_classes),
        "backbone": backbone,
        "backbone_weights": backbone_weights,
        "hidden_dims": hidden,
        "epochs": int(epochs),
        "seed": int(seed),
        "device": "cpu",
        "val_fraction": 0.25,
    }
    if clip_revision is not None:
        shared["clip_revision"] = clip_revision
    extras = ("neural",) if backbone == "resnet18" else ("neural", "foundation")
    return ExperimentSpec(
        id=experiment_id,
        title="Vision transfer: frozen-feature MLP vs fine-tuned head",
        description=(
            "Same local images. frozen_features trains an OEC MLP on backbone "
            "vectors; finetune_head freezes the backbone and trains a new head."
        ),
        seed=seed,
        tags=("vision", "neural", "transfer"),
        required_extras=extras,
        steps=(
            ExperimentStep(
                step_id="frozen_head",
                skill_id="neural.vision.transfer",
                inputs={**shared, "mode": "frozen_features"},
            ),
            ExperimentStep(
                step_id="finetune_head",
                skill_id="neural.vision.transfer",
                inputs={**shared, "mode": "finetune_head"},
            ),
        ),
        metrics=(
            MetricSpec(
                name="frozen_train_acc",
                path="result.train_metrics.accuracy",
                step_id="frozen_head",
                direction=MetricDirection.MAXIMIZE,
            ),
            MetricSpec(
                name="finetune_train_acc",
                path="result.train_metrics.accuracy",
                step_id="finetune_head",
                direction=MetricDirection.MAXIMIZE,
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


# Single source of truth for public builders (name → fn, domains, extras).
# MCP/CLI only expose this catalog (fail-closed). Helpers such as
# sphere_problem_2d / problem_to_optimize_inputs / build_mlp_regressor_* stay out.
# S4: public W5 evolutionary + hybrid experiment builders are catalogued here.
# NEAT is catalogued post-3.6 (ADR 0044). HyperNEAT remains excluded.
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
    # S4 — public declarative evolutionary / hybrid builders (W5).
    "build_optimize_single_experiment": {
        "fn": build_optimize_single_experiment,
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_nsga2_experiment": {
        "fn": build_nsga2_experiment,
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_neat_experiment": {
        "fn": build_neat_experiment,
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_hyperneat_experiment": {
        "fn": build_hyperneat_experiment,
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_hybrid_training_experiment": {
        "fn": build_hybrid_training_experiment,
        "domains": ["neural", "evolutionary"],
        "extras": ["neural", "evolutionary"],
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
    "build_full_stack_learning_experiment": {
        "fn": build_full_stack_learning_experiment,
        "domains": ["evolutionary", "neural", "foundation"],
        "extras": ["evolutionary", "neural", "foundation"],
    },
    "build_vision_head_vs_backbone_experiment": {
        "fn": build_vision_head_vs_backbone_experiment,
        "domains": ["neural", "vision"],
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
