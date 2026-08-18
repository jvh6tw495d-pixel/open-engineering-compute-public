import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _example_input() -> dict:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    return dict(data["input"])


def test_example_builtin_embed() -> None:
    out = implementation.execute(_example_input())
    assert out["result"]["backend"] == "builtin_hash"
    assert out["result"]["n"] == 2
    assert len(out["result"]["vectors"][0]) == 16


def test_transformers_backend_missing_extra_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No transformers installed -> structured fail-closed error, no invented vectors."""
    from oec.foundation import runtime

    monkeypatch.setattr(
        runtime, "probe_transformers", lambda: (False, None, "No module named 'transformers'")
    )
    inputs = _example_input()
    inputs["backend"] = "transformers"
    out = implementation.execute(inputs)
    result = out["result"]
    assert "vectors" not in result
    error = result["error"]
    assert error["code"] == "transformers_not_available"
    assert "message" in error
    assert out["diagnostics"]["converged"] is False


@pytest.mark.foundation
def test_transformers_backend_real_payload_with_extra() -> None:
    pytest.importorskip("transformers")
    inputs = _example_input()
    inputs["backend"] = "transformers"
    inputs["model_id"] = "sshleifer/tiny-gpt2"
    inputs["revision"] = "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"
    out = implementation.execute(inputs)
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "transformers"
    assert result["n"] == 2
    assert len(result["vectors"][0]) == inputs["dim"]
