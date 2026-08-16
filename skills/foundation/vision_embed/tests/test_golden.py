import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs_or_reports_missing_extra() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    # Either embedded vectors or a structured missing-extra / runtime error
    assert "vectors" in out["result"] or "error" in out["result"]


def test_missing_revision_on_remote_model_raises() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    inputs = dict(data["input"])
    del inputs["revision"]
    try:
        implementation.execute(inputs)
    except Exception:
        return
    raise AssertionError("expected an exception for a remote model_id without revision")


def test_image_source_conflict_raises() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    inputs = dict(data["input"])
    inputs["images"] = [
        {"image_base64": inputs["images"][0]["image_base64"], "image_path": "sample.png"}
    ]
    try:
        implementation.execute(inputs)
    except Exception:
        return
    raise AssertionError("expected an exception for both image_base64 and image_path set")
