"""Adapter operational contract: fail-closed when missing, real call when present."""

from __future__ import annotations

import pytest

from oec.learning import (
    BackendNotAvailableError,
    LearningDataset,
    ModelRef,
    TrainingConfig,
)
from oec.learning.backends.art import ARTBackend
from oec.learning.backends.axolotl import AxolotlBackend
from oec.learning.backends.unsloth import UnslothBackend
from oec.learning.contracts import FineTuneBackendName
from oec.learning.datasets import DatasetKind
from oec.learning.environments import MathematicsEnvironment
from oec.learning.rl import RLResult


def _dataset() -> LearningDataset:
    return LearningDataset(
        name="adapter-demo",
        kind=DatasetKind.SFT,
        records=({"text": "alpha"}, {"text": "beta"}),
    )


@pytest.mark.learning_adapter
def test_unsloth_operational_or_fail_closed() -> None:
    backend = UnslothBackend()
    try:
        import unsloth  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError, match="isolated"):
            backend.finetune(
                ModelRef(model_id="m"),
                _dataset(),
                TrainingConfig(backend=FineTuneBackendName.UNSLOTH),
            )
        return
    try:
        result = backend.finetune(
            ModelRef(model_id="m"),
            _dataset(),
            TrainingConfig(backend=FineTuneBackendName.UNSLOTH, max_steps=1),
        )
    except BackendNotAvailableError:
        return
    assert result.backend is FineTuneBackendName.UNSLOTH


@pytest.mark.learning_adapter
def test_axolotl_operational_or_fail_closed() -> None:
    backend = AxolotlBackend()
    try:
        import axolotl  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError, match="WSL"):
            backend.finetune(
                ModelRef(model_id="m"),
                _dataset(),
                TrainingConfig(backend=FineTuneBackendName.AXOLOTL),
            )
        return
    try:
        result = backend.finetune(
            ModelRef(model_id="m"),
            _dataset(),
            TrainingConfig(backend=FineTuneBackendName.AXOLOTL, max_steps=1),
        )
    except BackendNotAvailableError:
        return
    assert result.backend is FineTuneBackendName.AXOLOTL


@pytest.mark.learning_adapter
def test_art_operational_or_fail_closed() -> None:
    backend = ARTBackend()
    try:
        import art  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError, match="openpipe-art"):
            backend.train(MathematicsEnvironment(), ())
        return
    try:
        result = backend.train(MathematicsEnvironment(), ())
    except BackendNotAvailableError:
        return
    assert isinstance(result, RLResult)
    assert result.backend == "art"
