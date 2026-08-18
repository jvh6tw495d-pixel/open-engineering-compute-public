import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _example_input() -> dict:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    return data["input"]


def _weights_cached(model_id: str, revision: str) -> bool:
    """True only if a real weight file for this pinned revision is on disk.

    Never triggers a download — a cache miss here means the live test skips.
    """
    from huggingface_hub import try_to_load_from_cache

    for filename in ("pytorch_model.bin", "model.safetensors"):
        hit = try_to_load_from_cache(model_id, filename, revision=revision)
        if isinstance(hit, str):
            return True
    return False


def test_missing_extra_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No transformers installed -> structured fail-closed error, no invented vectors."""
    from oec.foundation import runtime

    monkeypatch.setattr(
        runtime, "probe_transformers", lambda: (False, None, "No module named 'transformers'")
    )
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "vectors" not in result
    error = result["error"]
    assert error["code"] == "transformers_not_available"
    assert "message" in error
    assert out["diagnostics"]["converged"] is False


@pytest.mark.foundation
def test_real_payload_with_extra() -> None:
    pytest.importorskip("transformers")
    pytest.importorskip("PIL")
    data = _example_input()
    if not _weights_cached(data["model_id"], data["revision"]):
        pytest.skip(f"{data['model_id']}@{data['revision']} weights not cached locally")
    out = implementation.execute(data)
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "transformers"
    assert result["model_id"] == data["model_id"]
    assert isinstance(result["vectors"], list) and result["vectors"]
    assert len(result["vectors"][0]) == data["dim"]
    assert out["diagnostics"]["converged"] is True


def test_missing_revision_on_remote_model_raises() -> None:
    inputs = dict(_example_input())
    del inputs["revision"]
    with pytest.raises(ValidationError):
        implementation.execute(inputs)


def test_image_source_conflict_raises() -> None:
    inputs = dict(_example_input())
    inputs["images"] = [
        {"image_base64": inputs["images"][0]["image_base64"], "image_path": "sample.png"}
    ]
    with pytest.raises(ValidationError):
        implementation.execute(inputs)
