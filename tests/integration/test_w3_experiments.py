"""W3 experiment demos under experiments/w3_*.json."""

from __future__ import annotations

import json
from pathlib import Path

from oec.experiment import ExperimentStatus
from oec.sdk import Engine

_ROOT = Path(__file__).resolve().parents[2]
_EXPS = list((_ROOT / "experiments").glob("w3_*.json"))


def test_w3_experiment_files_exist() -> None:
    assert len(_EXPS) >= 3


def test_w3_experiments_complete() -> None:
    engine = Engine(skills_root=str(_ROOT / "skills"))
    for path in sorted(_EXPS):
        spec = json.loads(path.read_text(encoding="utf-8"))
        record = engine.run_experiment(spec)
        assert record.status == ExperimentStatus.COMPLETED, (
            path.name,
            record.status,
            record.validation.messages,
            record.notes,
        )
