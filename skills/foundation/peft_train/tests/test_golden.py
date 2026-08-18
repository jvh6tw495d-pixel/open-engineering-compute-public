import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _example_input() -> dict:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    return dict(data["input"])


def test_missing_extra_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No transformers installed -> structured fail-closed error, no invented artifact."""
    from oec.foundation import runtime

    monkeypatch.setattr(
        runtime, "probe_transformers", lambda: (False, None, "No module named 'transformers'")
    )
    out = implementation.execute(_example_input())
    result = out["result"]
    assert "artifact" not in result
    error = result["error"]
    assert error["code"] == "transformers_not_available"
    assert "message" in error
    assert out["diagnostics"]["converged"] is False


@pytest.mark.foundation
def test_real_artifact_with_extra(tmp_path: Path) -> None:
    pytest.importorskip("transformers")
    pytest.importorskip("peft")
    inputs = _example_input()
    inputs["artifact_root"] = str(tmp_path)
    out = implementation.execute(inputs)
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "transformers"
    artifact = result["artifact"]
    assert artifact["kind"] == "adapter"
    assert Path(artifact["path"]).is_dir()
    assert artifact["sha256"]
    assert artifact["base_model_id"] == "sshleifer/tiny-gpt2"
    assert result["steps_run"] == inputs["max_steps"]
    assert isinstance(result["final_loss"], float)
    assert out["diagnostics"]["converged"] is True


@pytest.mark.foundation
def test_full_mode_real_checkpoint(tmp_path: Path) -> None:
    pytest.importorskip("transformers")
    inputs = _example_input()
    inputs["mode"] = "full"
    inputs["artifact_root"] = str(tmp_path)
    out = implementation.execute(inputs)
    result = out["result"]
    assert "error" not in result
    assert result["method"] == "none"
    artifact = result["artifact"]
    assert artifact["kind"] == "checkpoint"
    assert Path(artifact["path"]).is_dir()


def test_mutually_exclusive_dataset_fields_reported() -> None:
    inputs = _example_input()
    inputs["dataset_path"] = "some/local/file.txt"
    try:
        implementation.execute(inputs)
    except Exception:
        return
    raise AssertionError("expected an exception for both texts and dataset_path being set")
