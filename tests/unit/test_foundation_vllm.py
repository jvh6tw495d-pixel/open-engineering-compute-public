"""vLLM remote client contracts (ADR 0046)."""

from __future__ import annotations

from urllib.error import URLError

import pytest
from pydantic import ValidationError

from oec.foundation.contracts import GenerationBackend, VllmGenerateSpec
from oec.foundation.errors import VllmUnreachableError
from oec.foundation.vllm import run_vllm_generate


def test_base_url_must_be_http() -> None:
    with pytest.raises(ValidationError):
        VllmGenerateSpec(base_url="ftp://x", model_id="m", prompt="hi")


def test_adapter_path_forbidden() -> None:
    with pytest.raises(ValidationError):
        VllmGenerateSpec.model_validate(
            {
                "base_url": "http://127.0.0.1:8000",
                "model_id": "m",
                "prompt": "hi",
                "adapter_path": "/tmp/x",
            }
        )


def test_unreachable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.foundation.vllm as vllm_mod

    monkeypatch.setattr(
        vllm_mod.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("down")),
    )
    spec = VllmGenerateSpec(base_url="http://127.0.0.1:9", model_id="m", prompt="hi")
    with pytest.raises(VllmUnreachableError) as exc:
        run_vllm_generate(spec)
    assert exc.value.code == "vllm_unreachable"


def test_backend_enum() -> None:
    spec = VllmGenerateSpec(base_url="http://localhost:8000", model_id="m", prompt="p")
    assert spec.backend is GenerationBackend.VLLM
