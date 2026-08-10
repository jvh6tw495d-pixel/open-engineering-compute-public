"""Generate ADR 0033 neural.training / neural.search skills."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "neural"

BASE_XY = {
    "x": {
        "type": "array",
        "minItems": 2,
        "items": {"type": "array", "items": {"type": "number"}},
    },
    "y": {"type": "array", "minItems": 2, "items": {"type": "number"}},
    "seed": {"type": "integer", "default": 42},
    "device": {"type": "string", "enum": ["cpu", "cuda", "auto"], "default": "cpu"},
}

BUDGET = {
    **BASE_XY,
    "max_evaluations": {"type": "integer", "default": 12, "minimum": 2},
    "budget": {"type": "integer", "minimum": 2},
    "inner_epochs": {"type": "integer", "default": 20},
    "epochs": {"type": "integer"},
    "max_wall_time_s": {"type": ["number", "null"]},
}

VALIDATOR = """from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class NeuralEvoTrainingValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x and y must be equal-length lists"],
                )
            ]
        if len(x) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["need at least 2 samples"],
                )
            ]
        return []
"""

GOLDEN = """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_smoke() -> None:
    x = [[float(i)] for i in range(16)]
    y = [2.0 * i + 1.0 for i in range(16)]
    out = implementation.execute(
        {
            "x": x,
            "y": y,
            "seed": 0,
            "max_evaluations": 4,
            "inner_epochs": 8,
            "epochs": 15,
            "device": "cpu",
        }
    )
    assert "result" in out
    assert out["diagnostics"].get("backend") in (
        "torch",
        "hybrid",
        "neuroevolution",
        "benchmark",
    )
"""


def write_skill(
    folder: str,
    skill_id: str,
    title: str,
    method_id: str,
    impl: str,
    props: dict,
) -> None:
    d = ROOT / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "tests").mkdir(exist_ok=True)
    (d / "examples").mkdir(exist_ok=True)
    (d / "skill.md").write_text(
        f"""---
id: {skill_id}
version: 0.1.0
status: experimental
domain: neural
title: {title}
---

# {title}

ADR 0033 evolutionary neural training modes. Requires `oec[neural]`;
hybrid/search/neuroevolution/benchmark also need `oec[evolutionary]`.
""",
        encoding="utf-8",
    )
    (d / "skill.yaml").write_text(
        f"""id: {skill_id}
version: 0.1.0
status: experimental
domain: neural
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
  iterative: true

execution:
  deterministic: false
  timeout_seconds: 600
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - "ADR 0033 Evolutionary Neural Training"
  - "PyTorch + OEC Evolutionary"

tags:
  - neural
  - experimental
""",
        encoding="utf-8",
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"{skill_id} input",
        "type": "object",
        "properties": props,
        "required": ["x", "y"],
        "additionalProperties": False,
    }
    (d / "input.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    (d / "output.schema.json").write_text(
        json.dumps({"type": "object", "additionalProperties": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    (d / "validation.py").write_text(VALIDATOR, encoding="utf-8")
    (d / "implementation.py").write_text(impl, encoding="utf-8")
    (d / "references.md").write_text("- ADR 0033\n- PyTorch / Nevergrad\n", encoding="utf-8")
    (d / "examples" / "example.json").write_text(
        json.dumps(
            {
                "x": [[float(i)] for i in range(12)],
                "y": [2.0 * i + 1 for i in range(12)],
                "seed": 0,
                "max_evaluations": 6,
                "inner_epochs": 10,
                "epochs": 20,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (d / "tests" / "test_golden.py").write_text(GOLDEN, encoding="utf-8")
    print("wrote", skill_id)


SUP_IMPL = '''"""neural.training.supervised — unified supervised gradient entry (ADR 0033 W1)."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import train_mlp
from oec.neural.contracts import (
    ActivationName,
    DatasetSpec,
    DeviceSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.runtime import TrainingRuntimeSpec, resolve_mlp_hidden_dims


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x, y = inputs["x"], inputs["y"]
    raw = inputs.get("hidden_dims")
    hidden, cap = resolve_mlp_hidden_dims(
        capacity=inputs.get("capacity") or "tiny",
        hidden_dims=list(raw) if raw is not None else None,
    )
    if raw is not None:
        cap = None
    opt_name = OptimizerName(str(inputs.get("optimizer", "adam")))
    model = NeuralModelSpec(
        input_dim=len(x[0]),
        hidden_dims=list(hidden),
        activation=ActivationName(inputs.get("activation", "relu")),
        dropout=float(inputs.get("dropout", 0.0)),
    )
    patience = inputs.get("early_stopping_patience", 10)
    training = TrainingSpec(
        task=NeuralTask.REGRESSION,
        epochs=int(inputs.get("epochs", 80)),
        batch_size=int(inputs.get("batch_size", 16)),
        loss=LossName(str(inputs.get("loss", "mse"))),
        optimizer=OptimizerSpec(
            name=opt_name,
            lr=float(inputs.get("lr", 0.01)),
            weight_decay=float(inputs.get("weight_decay", 0.0)),
            momentum=float(inputs.get("momentum", 0.0)),
        ),
        seed=int(inputs.get("seed", 42)),
        device=DeviceSpec(device=inputs.get("device", "cpu")),
        normalize_x=bool(inputs.get("normalize_x", True)),
        early_stopping_patience=None if patience is None else int(patience),
    )
    runtime = TrainingRuntimeSpec(
        seed=training.seed,
        device=training.device,
        epochs=training.epochs,
        batch_size=training.batch_size,
        optimizer=training.optimizer,
        lr_scheduler=str(inputs.get("lr_scheduler", "none")),
        grad_clip=inputs.get("grad_clip"),
        early_stopping_patience=training.early_stopping_patience,
        checkpoint_storage=str(inputs.get("checkpoint_storage", "json_inline")),
    )
    try:
        result = train_mlp(
            DatasetSpec(x=x, y=y, val_fraction=float(inputs.get("val_fraction", 0.2))),
            model,
            training,
            runtime=runtime,
            capacity=cap,
        )
    except (TorchNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "torch", "message": msg},
        }
    payload = result.model_dump(mode="json")
    payload["history"] = (payload.get("history") or [])[-5:]
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "backend": "torch",
            "mode": "gradient",
            "seed": result.seed,
            "n_params": result.n_params,
            "capacity": result.capacity,
            "train_metrics": result.train_metrics,
        },
    }
'''

GRAD_IMPL = SUP_IMPL.replace("neural.training.supervised", "neural.training.gradient").replace(
    '"adam"', '"adamw"'
)


def hybrid_impl(fn: str, extra: str = "") -> str:
    return f'''"""ADR 0033 evolutionary neural training skill."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import {fn}


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = {fn}(
            inputs["x"],
            inputs["y"],
            max_evaluations=int(inputs.get("max_evaluations", inputs.get("budget", 12))),
            seed=int(inputs.get("seed", 42)),
            inner_epochs=int(inputs.get("inner_epochs", inputs.get("epochs", 20))),
            device=str(inputs.get("device", "cpu")),
            max_wall_time_s=inputs.get("max_wall_time_s"),
            {extra}
        )
    except (TorchNotAvailableError, NevergradNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {{
            "result": {{"error": {{"message": msg}}}},
            "diagnostics": {{"converged": False, "backend": "hybrid", "message": msg}},
        }}
    return {{
        "result": result,
        "diagnostics": {{
            "converged": True,
            "backend": "hybrid",
            "seed": result.get("seed"),
            "mode": result.get("mode"),
            "n_trials": result.get("n_trials"),
            "best_config": result.get("best_config"),
        }},
    }}
'''


NEURO_IMPL = '''"""neural.training.neuroevolution — weight evo for small MLPs (ADR 0033 W4)."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import neuroevolution_train


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = neuroevolution_train(
            inputs["x"],
            inputs["y"],
            max_evaluations=int(inputs.get("max_evaluations", 40)),
            seed=int(inputs.get("seed", 42)),
            hidden=int(inputs.get("hidden", 8)),
            max_params=int(inputs.get("max_params", 500)),
            device=str(inputs.get("device", "cpu")),
        )
    except (TorchNotAvailableError, NevergradNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "neuroevolution", "message": msg},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "neuroevolution",
            "seed": result.get("seed"),
            "best_mse": result.get("best_mse"),
            "n_params": result.get("n_params"),
        },
    }
'''

BENCH_IMPL = '''"""neural.benchmark.training_strategy — gradient vs hybrid vs neuroevolution."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import benchmark_training_strategies


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = benchmark_training_strategies(
            inputs["x"],
            inputs["y"],
            seed=int(inputs.get("seed", 42)),
            max_evaluations=int(inputs.get("max_evaluations", 8)),
            inner_epochs=int(inputs.get("inner_epochs", 12)),
            device=str(inputs.get("device", "cpu")),
        )
    except (TorchNotAvailableError, NevergradNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "benchmark", "message": msg},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "benchmark",
            "seed": result.get("seed"),
            "arms": [a.get("strategy") for a in result.get("arms", [])],
        },
    }
'''


def main() -> None:
    sup_props = {
        **BASE_XY,
        "capacity": {"type": "string", "enum": ["tiny", "medium", "dense", "wide"]},
        "epochs": {"type": "integer", "default": 80},
        "lr": {"type": "number", "default": 0.01},
        "optimizer": {
            "type": "string",
            "enum": ["adam", "adamw", "sgd", "rmsprop", "lbfgs"],
            "default": "adam",
        },
        "momentum": {"type": "number", "default": 0},
        "weight_decay": {"type": "number", "default": 0},
        "dropout": {"type": "number", "default": 0},
        "batch_size": {"type": "integer", "default": 16},
        "hidden_dims": {"type": "array", "items": {"type": "integer"}},
        "activation": {"type": "string", "default": "relu"},
        "loss": {"type": "string", "default": "mse"},
        "lr_scheduler": {
            "type": "string",
            "enum": ["none", "cosine", "step"],
            "default": "none",
        },
        "val_fraction": {"type": "number", "default": 0.2},
        "normalize_x": {"type": "boolean", "default": True},
    }
    write_skill(
        "training_supervised",
        "neural.training.supervised",
        "Supervised Gradient Training",
        "torch_supervised_train",
        SUP_IMPL,
        sup_props,
    )
    write_skill(
        "training_gradient",
        "neural.training.gradient",
        "Gradient Training (explicit)",
        "torch_gradient_train",
        GRAD_IMPL,
        {**sup_props, "optimizer": {**sup_props["optimizer"], "default": "adamw"}},
    )
    hybrid_props = {
        **BUDGET,
        "facets": {"type": "array", "items": {"type": "string"}},
        "multiobjective": {"type": "boolean", "default": False},
    }
    write_skill(
        "training_hybrid",
        "neural.training.hybrid",
        "Hybrid Evolutionary + Gradient Training",
        "hybrid_evolutionary_gradient",
        hybrid_impl(
            "hybrid_evolutionary_train",
            'facets=list(inputs.get("facets") or ["hyperparameters", "architecture"]), '
            'multiobjective=bool(inputs.get("multiobjective", False)),',
        ),
        hybrid_props,
    )
    for folder, sid, title, mid, fn in [
        (
            "search_hyperparameters",
            "neural.search.hyperparameters",
            "Evolutionary Hyperparameter Search",
            "neural_search_hyperparameters",
            "search_hyperparameters",
        ),
        (
            "search_architecture",
            "neural.search.architecture",
            "Evolutionary Architecture Search + Pareto",
            "neural_search_architecture",
            "search_architecture",
        ),
        (
            "search_features",
            "neural.search.features",
            "Feature Subset Evolution",
            "neural_search_features",
            "search_features",
        ),
        (
            "search_loss_weights",
            "neural.search.loss_weights",
            "Loss Weight Evolution",
            "neural_search_loss_weights",
            "search_loss_weights",
        ),
        (
            "search_policy",
            "neural.search.policy",
            "Training Policy Evolution",
            "neural_search_policy",
            "search_policy",
        ),
    ]:
        write_skill(folder, sid, title, mid, hybrid_impl(fn), BUDGET)

    write_skill(
        "training_neuroevolution",
        "neural.training.neuroevolution",
        "Direct Neuroevolution (small MLP)",
        "neural_neuroevolution",
        NEURO_IMPL,
        {
            **BASE_XY,
            "max_evaluations": {"type": "integer", "default": 40},
            "hidden": {"type": "integer", "default": 8},
            "max_params": {"type": "integer", "default": 500},
        },
    )
    write_skill(
        "benchmark_training_strategy",
        "neural.benchmark.training_strategy",
        "Training Strategy Benchmark",
        "neural_benchmark_training_strategy",
        BENCH_IMPL,
        BUDGET,
    )
    print("all skills written under", ROOT)


if __name__ == "__main__":
    main()
