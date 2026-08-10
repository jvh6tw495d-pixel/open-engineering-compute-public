from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_gnn_runs() -> None:
    # line graph 0-1-2-3, node value = index
    node_features = [[float(i), 1.0] for i in range(6)]
    edge_index = [[0, 1, 2, 3, 4], [1, 2, 3, 4, 5]]
    y = [float(i) for i in range(6)]
    out = implementation.execute(
        {
            "node_features": node_features,
            "edge_index": edge_index,
            "y": y,
            "epochs": 30,
            "hidden": 8,
            "seed": 0,
            "device": "cpu",
            "task": "regression",
        }
    )
    assert out["result"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
