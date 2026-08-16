"""Optional Learning backends never auto-install — user-facing contract."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from oec.learning import (
    ART_MISSING,
    ART_PYPI,
    ART_WRONG_PACKAGE,
    AXOLOTL_MISSING,
    HF_MISSING,
    UNSLOTH_MISSING,
    BackendNotAvailableError,
    ModelRef,
    TrainingConfig,
    capability_matrix,
    hint_for,
)
from oec.learning.backends.art import ARTBackend
from oec.learning.backends.axolotl import AxolotlBackend
from oec.learning.backends.unsloth import UnslothBackend
from oec.learning.contracts import FineTuneBackendName
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.environments import MathematicsEnvironment
from oec.learning.install_hints import GUIDE


def _dataset() -> LearningDataset:
    return LearningDataset(
        name="install-hint",
        kind=DatasetKind.SFT,
        records=({"text": "alpha"},),
    )


def test_public_hints_name_the_real_packages() -> None:
    assert "openpipe-art" in ART_PYPI
    assert "openpipe-art" in ART_MISSING
    assert "ASCII-art" in ART_MISSING
    assert "not auto-installed" in ART_MISSING
    assert "wrong PyPI package" in ART_WRONG_PACKAGE
    assert "isolated" in UNSLOTH_MISSING
    assert "downgrades" in UNSLOTH_MISSING
    assert "WSL" in AXOLOTL_MISSING
    assert "oec[foundation]" in HF_MISSING
    assert GUIDE in ART_MISSING
    assert hint_for("art") == ART_MISSING
    assert hint_for("unsloth") == UNSLOTH_MISSING


def test_art_missing_tells_user_to_install_openpipe_art(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import oec.learning.backends.art as art_module

    monkeypatch.setattr(
        art_module.importlib, "import_module", lambda _name: (_ for _ in ()).throw(ImportError())
    )
    with pytest.raises(BackendNotAvailableError, match="openpipe-art") as caught:
        ARTBackend().train(MathematicsEnvironment(), ())
    assert "not auto-installed" in str(caught.value)
    assert caught.value.details["pypi"] == ART_PYPI
    assert caught.value.details["wrong_pypi"] == "art"


def test_art_wrong_pypi_package_is_called_out(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.art as art_module

    monkeypatch.setattr(
        art_module.importlib, "import_module", lambda _name: SimpleNamespace(text2art=lambda _: "")
    )
    with pytest.raises(BackendNotAvailableError, match="wrong PyPI package") as caught:
        ARTBackend().train(MathematicsEnvironment(), ())
    assert "openpipe-art" in str(caught.value)
    assert caught.value.details["wrong_pypi"] == "art"


def test_unsloth_missing_forbids_project_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.unsloth as unsloth_module

    monkeypatch.setattr(
        unsloth_module.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ImportError()),
    )
    with pytest.raises(BackendNotAvailableError, match="isolated") as caught:
        UnslothBackend().finetune(
            ModelRef(model_id="m"),
            _dataset(),
            TrainingConfig(backend=FineTuneBackendName.UNSLOTH),
        )
    assert "not auto-installed" in str(caught.value)
    assert caught.value.details["isolated_venv"] is True


def test_axolotl_missing_is_wsl_or_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.axolotl as axolotl_module

    monkeypatch.setattr(
        axolotl_module.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ImportError()),
    )
    with pytest.raises(BackendNotAvailableError, match="WSL") as caught:
        AxolotlBackend().finetune(
            ModelRef(model_id="m"),
            _dataset(),
            TrainingConfig(backend=FineTuneBackendName.AXOLOTL),
        )
    assert "not auto-installed" in str(caught.value)
    assert caught.value.details["platform"] == "linux-or-wsl-only"


def test_capability_matrix_never_auto_installs_adapters() -> None:
    rows = {row["backend"]: row for row in capability_matrix()}
    assert rows["art"]["extra"] == "external:openpipe-art"
    assert rows["art"]["auto_install"] is False
    assert "openpipe-art" in rows["art"]["install"]
    assert rows["unsloth"]["auto_install"] is False
    assert "isolated" in rows["unsloth"]["install"]
    assert rows["axolotl"]["auto_install"] is False
    assert "WSL" in rows["axolotl"]["install"]
    assert rows["huggingface"]["auto_install"] is False
