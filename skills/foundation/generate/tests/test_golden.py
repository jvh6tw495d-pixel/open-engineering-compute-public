import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _example_input() -> dict:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    return data["input"]


def test_missing_extra_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No transformers installed -> structured fail-closed error, no invented text."""
    from oec.foundation import runtime

    monkeypatch.setattr(
        runtime, "probe_transformers", lambda: (False, None, "No module named 'transformers'")
    )
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "text" not in result
    error = result["error"]
    assert error["code"] == "transformers_not_available"
    assert "message" in error
    assert out["diagnostics"]["converged"] is False


@pytest.mark.foundation
def test_real_payload_with_extra() -> None:
    pytest.importorskip("transformers")
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "transformers"
    assert isinstance(result["text"], str) and result["text"]
    assert result["model_id"] == "sshleifer/tiny-gpt2"
    assert out["diagnostics"]["converged"] is True
