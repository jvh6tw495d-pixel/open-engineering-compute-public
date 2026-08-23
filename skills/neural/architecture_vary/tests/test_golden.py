from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")


def test_widen_mutates() -> None:
    graph = {
        "nodes": [
            {
                "id": "a",
                "block_id": "linear",
                "config": {"in_features": 4, "out_features": 8, "activation": "relu"},
            },
            {
                "id": "b",
                "block_id": "linear",
                "config": {"in_features": 8, "out_features": 2, "activation": "none"},
            },
        ],
        "edges": [{"source": "a", "target": "b"}],
    }
    out = implementation.execute({"mode": "mutate", "operator": "widen", "seed": 0, "graph": graph})
    result = out["result"]
    assert "error" not in result
    assert result["fingerprint"]
    assert result["operator"] == "widen"
