from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError

import pytest
from pydantic import ValidationError

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _example_input() -> dict[str, Any]:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    return dict(data["input"])


def test_unreachable_server_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.foundation.vllm as vllm_mod

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise URLError("connection refused")

    monkeypatch.setattr(vllm_mod.urllib.request, "urlopen", boom)
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "text" not in result
    assert result["error"]["code"] == "vllm_unreachable"
    assert out["diagnostics"]["converged"] is False


def test_mocked_http_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.foundation.vllm as vllm_mod

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"choices": [{"text": " 4"}]}).encode("utf-8")

    monkeypatch.setattr(vllm_mod.urllib.request, "urlopen", lambda *_a, **_k: _Resp())
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "error" not in result
    assert result["text"] == " 4"
    assert result["backend"] == "vllm"
    assert result["merit_owner"] == "vllm"


def test_adapter_path_rejected() -> None:
    inputs = _example_input()
    inputs["adapter_path"] = "/tmp/adapter"
    with pytest.raises(ValidationError):
        from oec.foundation.contracts import VllmGenerateSpec

        VllmGenerateSpec.model_validate(inputs)


def test_bad_base_url_rejected() -> None:
    inputs = _example_input()
    inputs["base_url"] = "not-a-url"
    out = implementation.execute(inputs)
    assert "error" in out["result"]
    assert out["diagnostics"]["converged"] is False
