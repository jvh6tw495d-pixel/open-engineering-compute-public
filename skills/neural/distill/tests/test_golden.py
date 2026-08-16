from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

_REG = Path(__file__).resolve().parents[2] / "mlp_regressor"
_SKILL = Path(__file__).resolve().parent.parent
train_impl = load_skill_module(_REG, "implementation")
distill_impl = load_skill_module(_SKILL, "implementation")
pytestmark = pytest.mark.neural


def test_distill_student_is_evaluable() -> None:
    x = [[float(i)] for i in range(10)]
    y = [2.0 * i + 1.0 for i in range(10)]
    teacher = train_impl.execute(
        {"x": x, "y": y, "hidden_dims": [8], "epochs": 60, "lr": 0.05, "val_fraction": 0.0}
    )
    out = distill_impl.execute(
        {
            "x": x,
            "y": y,
            "teacher_checkpoint": teacher["result"]["checkpoint"],
            "teacher_normalize": teacher["result"].get("normalize"),
            "student_hidden_dims": [4],
            "epochs": 60,
            "batch_size": 10,
            "max_epochs": 60,
            "max_batch_size": 10,
        }
    )
    assert out["diagnostics"]["student_checkpoint_compatible"] is True
    assert out["result"]["checkpoint"]


def test_distill_rejects_budget_above_contract_cap() -> None:
    out = distill_impl.execute(
        {
            "x": [[0.0], [1.0]],
            "y": [0.0, 1.0],
            "teacher_checkpoint": {},
            "epochs": 2,
            "max_epochs": 1,
        }
    )
    assert out["result"]["error"]["type"] == "ValueError"
    assert "epochs exceeds max_epochs" in out["result"]["error"]["message"]
