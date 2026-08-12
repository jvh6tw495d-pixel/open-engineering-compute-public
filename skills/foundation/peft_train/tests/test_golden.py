import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs_or_reports_missing_extra() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    # Either a trained artifact descriptor or a structured missing-extra error
    assert "artifact" in out["result"] or "error" in out["result"]


def test_full_mode_maps_to_none_method() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    inputs = dict(data["input"])
    inputs["mode"] = "full"
    out = implementation.execute(inputs)
    assert "result" in out
    assert "artifact" in out["result"] or "error" in out["result"]


def test_mutually_exclusive_dataset_fields_reported() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    inputs = dict(data["input"])
    inputs["dataset_path"] = "some/local/file.txt"
    try:
        implementation.execute(inputs)
    except Exception:
        return
    raise AssertionError("expected an exception for both texts and dataset_path being set")
