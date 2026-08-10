# ruff: noqa
"""Scaffold neural skills N2–N5."""

from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1] / "skills" / "neural"


def write_skill(
    folder: str,
    skill_id: str,
    method_id: str,
    title: str,
    implementation: str,
    input_schema: str,
    test_body: str,
    example: str,
) -> None:
    d = root / folder
    (d / "examples").mkdir(parents=True, exist_ok=True)
    (d / "tests").mkdir(parents=True, exist_ok=True)
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
  timeout_seconds: 300
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - "PyTorch — https://pytorch.org/docs/stable/index.html"
  - "ADR 0031 / 0032 Neural Compute"

tags:
  - neural
  - experimental
""",
        encoding="utf-8",
    )
    (d / "skill.md").write_text(
        f"---\nid: {skill_id}\nversion: 0.1.0\n---\n\n# {title}\n\n"
        f"Requires `oec[neural]`. Merit owner: PyTorch.\n",
        encoding="utf-8",
    )
    (d / "references.md").write_text(
        "# References\n\n- PyTorch docs\n- ADR 0031 / 0032\n", encoding="utf-8"
    )
    (d / "output.schema.json").write_text(
        """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "backend": { "type": "string" },
    "train_metrics": { "type": "object" },
    "checkpoint": { "type": "object" },
    "seed": { "type": "integer" }
  },
  "required": ["backend", "train_metrics", "checkpoint"],
  "additionalProperties": true
}
""",
        encoding="utf-8",
    )
    (d / "input.schema.json").write_text(input_schema, encoding="utf-8")
    (d / "implementation.py").write_text(implementation, encoding="utf-8")
    (d / "validation.py").write_text(
        """from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class NeuralSkillValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill, normalized_inputs
        return []
""",
        encoding="utf-8",
    )
    (d / "tests" / "test_golden.py").write_text(
        f"""from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


{test_body}
""",
        encoding="utf-8",
    )
    (d / "examples" / "example.json").write_text(example, encoding="utf-8")


AE_IMPL = '''"""{sid}."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.autoencoder import train_autoencoder
from oec.kernel.neural.errors import TorchNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_autoencoder(
            inputs["x"],
            latent_dim=int(inputs.get("latent_dim", 8)),
            hidden_dims=list(inputs.get("hidden_dims") or [32, 16]),
            epochs=int(inputs.get("epochs", 40)),
            batch_size=int(inputs.get("batch_size", 16)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
            noise_std=float(inputs.get("noise_std", {noise})),
            activation=str(inputs.get("activation", "relu")),
        )
    except TorchNotAvailableError as exc:
        return {{
            "result": {{"error": exc.to_dict()}},
            "diagnostics": {{"converged": False, "message": exc.message, "backend": "torch"}},
        }}
    return {{
        "result": result,
        "diagnostics": {{
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "mse": result["train_metrics"]["mse"],
        }},
    }}
'''

SEQ_IMPL = '''"""{sid}."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.sequences import train_sequence_model


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_sequence_model(
            inputs["x"],
            inputs["y"],
            arch="{arch}",
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            hidden=int(inputs.get("hidden", 32)),
            n_layers=int(inputs.get("n_layers", 1)),
            epochs=int(inputs.get("epochs", 30)),
            batch_size=int(inputs.get("batch_size", 8)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
            kernel_size=int(inputs.get("kernel_size", 3)),
            dropout=float(inputs.get("dropout", 0.0)),
        )
    except TorchNotAvailableError as exc:
        return {{
            "result": {{"error": exc.to_dict()}},
            "diagnostics": {{"converged": False, "message": exc.message, "backend": "torch"}},
        }}
    return {{
        "result": result,
        "diagnostics": {{
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "train_metrics": result["train_metrics"],
        }},
    }}
'''

TX_IMPL = '''"""{sid}."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.transformer import train_transformer_sequence


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_transformer_sequence(
            inputs["x"],
            inputs["y"],
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            d_model=int(inputs.get("d_model", 32)),
            n_heads=int(inputs.get("n_heads", 4)),
            n_layers=int(inputs.get("n_layers", 2)),
            ff_dim=int(inputs.get("ff_dim", 64)),
            dropout=float(inputs.get("dropout", 0.0)),
            epochs=int(inputs.get("epochs", 25)),
            batch_size=int(inputs.get("batch_size", 8)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
        )
    except TorchNotAvailableError as exc:
        return {{
            "result": {{"error": exc.to_dict()}},
            "diagnostics": {{"converged": False, "message": exc.message, "backend": "torch"}},
        }}
    return {{
        "result": result,
        "diagnostics": {{
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "train_metrics": result["train_metrics"],
        }},
    }}
'''

GNN_IMPL = '''"""{sid}."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.gnn import train_gnn


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_gnn(
            inputs["node_features"],
            inputs["edge_index"],
            inputs["y"],
            train_mask=inputs.get("train_mask"),
            arch="{arch}",
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            hidden=int(inputs.get("hidden", 16)),
            n_layers=int(inputs.get("n_layers", 2)),
            heads=int(inputs.get("heads", 2)),
            epochs=int(inputs.get("epochs", 40)),
            lr=float(inputs.get("lr", 1e-2)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
            dropout=float(inputs.get("dropout", 0.0)),
        )
    except TorchNotAvailableError as exc:
        return {{
            "result": {{"error": exc.to_dict()}},
            "diagnostics": {{"converged": False, "message": exc.message, "backend": "torch"}},
        }}
    return {{
        "result": result,
        "diagnostics": {{
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "train_metrics": result["train_metrics"],
        }},
    }}
'''

AE_SCHEMA = """{
  "type": "object",
  "properties": {
    "x": {"type": "array", "minItems": 2, "items": {"type": "array", "items": {"type": "number"}}},
    "latent_dim": {"type": "integer", "minimum": 1, "default": 8},
    "hidden_dims": {"type": "array", "items": {"type": "integer", "minimum": 1}},
    "epochs": {"type": "integer", "minimum": 1, "default": 40},
    "batch_size": {"type": "integer", "minimum": 1, "default": 16},
    "lr": {"type": "number", "exclusiveMinimum": 0, "default": 0.001},
    "seed": {"type": "integer", "default": 42},
    "device": {"type": "string", "enum": ["cpu", "cuda", "auto"], "default": "cpu"},
    "noise_std": {"type": "number", "minimum": 0, "default": NOISE},
    "activation": {"type": "string", "enum": ["relu", "gelu", "tanh", "sigmoid"], "default": "relu"}
  },
  "required": ["x"],
  "additionalProperties": false
}
"""

SEQ_SCHEMA = """{
  "type": "object",
  "properties": {
    "x": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "array", "minItems": 1, "items": {"type": "number"}}
      }
    },
    "y": {"type": "array", "minItems": 2, "items": {"type": "number"}},
    "task": {"type": "string", "enum": ["regression", "classification"], "default": "regression"},
    "n_classes": {"type": "integer", "minimum": 1, "default": 1},
    "hidden": {"type": "integer", "minimum": 1, "default": 32},
    "n_layers": {"type": "integer", "minimum": 1, "default": 1},
    "epochs": {"type": "integer", "minimum": 1, "default": 30},
    "batch_size": {"type": "integer", "minimum": 1, "default": 8},
    "lr": {"type": "number", "exclusiveMinimum": 0, "default": 0.001},
    "seed": {"type": "integer", "default": 42},
    "device": {"type": "string", "enum": ["cpu", "cuda", "auto"], "default": "cpu"},
    "kernel_size": {"type": "integer", "minimum": 1, "default": 3},
    "dropout": {"type": "number", "minimum": 0, "maximum": 0.9, "default": 0.0}
  },
  "required": ["x", "y"],
  "additionalProperties": false
}
"""

TX_SCHEMA = """{
  "type": "object",
  "properties": {
    "x": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "array", "minItems": 1, "items": {"type": "number"}}
      }
    },
    "y": {"type": "array", "minItems": 2, "items": {"type": "number"}},
    "task": {"type": "string", "enum": ["regression", "classification"], "default": "regression"},
    "n_classes": {"type": "integer", "minimum": 1, "default": 1},
    "d_model": {"type": "integer", "minimum": 4, "default": 32},
    "n_heads": {"type": "integer", "minimum": 1, "default": 4},
    "n_layers": {"type": "integer", "minimum": 1, "default": 2},
    "ff_dim": {"type": "integer", "minimum": 4, "default": 64},
    "dropout": {"type": "number", "minimum": 0, "maximum": 0.9, "default": 0.0},
    "epochs": {"type": "integer", "minimum": 1, "default": 25},
    "batch_size": {"type": "integer", "minimum": 1, "default": 8},
    "lr": {"type": "number", "exclusiveMinimum": 0, "default": 0.001},
    "seed": {"type": "integer", "default": 42},
    "device": {"type": "string", "enum": ["cpu", "cuda", "auto"], "default": "cpu"}
  },
  "required": ["x", "y"],
  "additionalProperties": false
}
"""

GNN_SCHEMA = """{
  "type": "object",
  "properties": {
    "node_features": {
      "type": "array",
      "minItems": 2,
      "items": {"type": "array", "minItems": 1, "items": {"type": "number"}}
    },
    "edge_index": {
      "type": "array",
      "minItems": 2,
      "maxItems": 2,
      "items": {"type": "array", "items": {"type": "integer", "minimum": 0}}
    },
    "y": {"type": "array", "minItems": 2, "items": {"type": "number"}},
    "train_mask": {"type": "array", "items": {"type": "boolean"}},
    "task": {"type": "string", "enum": ["regression", "classification"], "default": "regression"},
    "n_classes": {"type": "integer", "minimum": 1, "default": 1},
    "hidden": {"type": "integer", "minimum": 1, "default": 16},
    "n_layers": {"type": "integer", "minimum": 1, "default": 2},
    "heads": {"type": "integer", "minimum": 1, "default": 2},
    "epochs": {"type": "integer", "minimum": 1, "default": 40},
    "lr": {"type": "number", "exclusiveMinimum": 0, "default": 0.01},
    "seed": {"type": "integer", "default": 42},
    "device": {"type": "string", "enum": ["cpu", "cuda", "auto"], "default": "cpu"},
    "dropout": {"type": "number", "minimum": 0, "maximum": 0.9, "default": 0.0}
  },
  "required": ["node_features", "edge_index", "y"],
  "additionalProperties": false
}
"""

AE_TEST = """
def test_reconstructs() -> None:
    import numpy as np
    rng = np.random.default_rng(0)
    x = (rng.normal(size=(40, 6))).tolist()
    out = implementation.execute({"x": x, "epochs": 25, "latent_dim": 4, "seed": 0, "device": "cpu"})
    assert out["result"]["backend"] == "torch"
    assert out["result"]["train_metrics"]["mse"] < 2.0
"""

SEQ_TEST = """
def test_sequence_runs() -> None:
    # y = mean of sequence feature 0
    x = []
    y = []
    for i in range(24):
        seq = [[float(i + t) * 0.1, 0.5] for t in range(6)]
        x.append(seq)
        y.append(sum(s[0] for s in seq) / 6.0)
    out = implementation.execute({
        "x": x, "y": y, "epochs": 20, "hidden": 16, "seed": 0, "device": "cpu", "task": "regression"
    })
    assert out["result"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
"""

TX_TEST = """
def test_transformer_runs() -> None:
    x = []
    y = []
    for i in range(20):
        seq = [[float(i + t) * 0.05] for t in range(5)]
        x.append(seq)
        y.append(float(i) * 0.05)
    out = implementation.execute({
        "x": x, "y": y, "epochs": 15, "d_model": 16, "n_heads": 2, "n_layers": 1,
        "ff_dim": 32, "seed": 0, "device": "cpu"
    })
    assert out["result"]["backend"] == "torch"
"""

GNN_TEST = """
def test_gnn_runs() -> None:
    # line graph 0-1-2-3, node value = index
    node_features = [[float(i), 1.0] for i in range(6)]
    edge_index = [[0, 1, 2, 3, 4], [1, 2, 3, 4, 5]]
    y = [float(i) for i in range(6)]
    out = implementation.execute({
        "node_features": node_features,
        "edge_index": edge_index,
        "y": y,
        "epochs": 30,
        "hidden": 8,
        "seed": 0,
        "device": "cpu",
        "task": "regression",
    })
    assert out["result"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
"""


def main() -> None:
    # N2
    write_skill(
        "autoencoder_basic",
        "neural.autoencoder.basic",
        "torch_autoencoder_basic",
        "Autoencoder Basic",
        AE_IMPL.format(sid="neural.autoencoder.basic", noise="0.0"),
        AE_SCHEMA.replace("NOISE", "0.0"),
        AE_TEST,
        '{"x": [[0,1,0],[1,0,1],[0.5,0.5,0.5],[1,1,0],[0,0,1]], "epochs": 20, "latent_dim": 2, "seed": 0}',
    )
    write_skill(
        "autoencoder_denoising",
        "neural.autoencoder.denoising",
        "torch_autoencoder_denoising",
        "Autoencoder Denoising",
        AE_IMPL.format(sid="neural.autoencoder.denoising", noise="0.1"),
        AE_SCHEMA.replace("NOISE", "0.1"),
        AE_TEST,
        '{"x": [[0,1,0],[1,0,1],[0.5,0.5,0.5],[1,1,0],[0,0,1]], "epochs": 20, "noise_std": 0.1, "seed": 0}',
    )

    # N3
    for arch, folder, sid, mid, title in [
        ("cnn1d", "cnn1d", "neural.cnn1d", "torch_cnn1d_train", "CNN1D Sequence"),
        ("lstm", "lstm", "neural.lstm", "torch_lstm_train", "LSTM Sequence"),
        ("gru", "gru", "neural.gru", "torch_gru_train", "GRU Sequence"),
        ("tcn", "tcn", "neural.tcn", "torch_tcn_train", "TCN Sequence"),
    ]:
        write_skill(
            folder,
            sid,
            mid,
            title,
            SEQ_IMPL.format(sid=sid, arch=arch),
            SEQ_SCHEMA,
            SEQ_TEST,
            '{"x": [[[0,1],[1,1],[2,1]],[[1,1],[2,1],[3,1]],[[2,1],[3,1],[4,1]],[[3,1],[4,1],[5,1]]], "y": [1,2,3,4], "epochs": 15, "seed": 0}',
        )

    # N4
    write_skill(
        "transformer_encoder",
        "neural.transformer.encoder",
        "torch_transformer_encoder_train",
        "Transformer Encoder Sequence",
        TX_IMPL.format(sid="neural.transformer.encoder"),
        TX_SCHEMA,
        TX_TEST,
        '{"x": [[[0],[1],[2]],[[1],[2],[3]],[[2],[3],[4]],[[3],[4],[5]]], "y": [1,2,3,4], "epochs": 12, "d_model": 16, "n_heads": 2, "seed": 0}',
    )
    write_skill(
        "transformer_sequence_regressor",
        "neural.transformer.sequence_regressor",
        "torch_transformer_seq_regressor",
        "Transformer Sequence Regressor",
        TX_IMPL.format(sid="neural.transformer.sequence_regressor"),
        TX_SCHEMA,
        TX_TEST,
        '{"x": [[[0],[1],[2]],[[1],[2],[3]],[[2],[3],[4]],[[3],[4],[5]]], "y": [1,2,3,4], "task": "regression", "epochs": 12, "d_model": 16, "n_heads": 2, "seed": 0}',
    )
    write_skill(
        "transformer_sequence_classifier",
        "neural.transformer.sequence_classifier",
        "torch_transformer_seq_classifier",
        "Transformer Sequence Classifier",
        TX_IMPL.format(sid="neural.transformer.sequence_classifier"),
        TX_SCHEMA,
        TX_TEST.replace('"task": "regression"', "").replace(
            "out = implementation.execute({",
            'out = implementation.execute({"task": "classification", "n_classes": 2, ',
        ),
        '{"x": [[[0],[0],[0]],[[1],[1],[1]],[[0],[0],[1]],[[1],[1],[0]]], "y": [0,1,0,1], "task": "classification", "n_classes": 2, "epochs": 20, "d_model": 16, "n_heads": 2, "seed": 0}',
    )

    # N5
    for arch, folder, sid, mid, title in [
        ("gcn", "gcn", "neural.gcn", "torch_gcn_train", "GCN Node Model"),
        (
            "graphsage",
            "graphsage",
            "neural.graphsage",
            "torch_graphsage_train",
            "GraphSAGE Node Model",
        ),
        ("gat", "gat", "neural.gat", "torch_gat_train", "GAT Node Model"),
    ]:
        write_skill(
            folder,
            sid,
            mid,
            title,
            GNN_IMPL.format(sid=sid, arch=arch),
            GNN_SCHEMA,
            GNN_TEST,
            '{"node_features": [[0,1],[1,1],[2,1],[3,1]], "edge_index": [[0,1,2],[1,2,3]], "y": [0,1,2,3], "epochs": 20, "seed": 0}',
        )
    print("N2-N5 skills ok")


if __name__ == "__main__":
    main()
