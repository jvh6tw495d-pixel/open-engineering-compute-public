from pathlib import Path

from oec.testing import load_skill_module

_SKILL = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL, "implementation")


def test_distill_rejects_file_backed_teacher_checkpoint() -> None:
    out = implementation.execute(
        {
            "x": [[0.0], [1.0]],
            "y": [0.0, 1.0],
            "teacher_checkpoint": {"storage": "file", "path": "C:/untrusted.pt"},
        }
    )
    assert out["result"]["error"]["type"] == "ValueError"
    assert "json_inline" in out["result"]["error"]["message"]
