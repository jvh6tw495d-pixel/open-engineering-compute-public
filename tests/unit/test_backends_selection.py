"""Backend selection-by-domain tests (ADR 0021)."""

from __future__ import annotations

import pytest

from oec.backends.selection import select_backend_for
from oec.core.errors import BackendUnavailableError


def test_select_backend_for_lp_returns_highs() -> None:
    backend = select_backend_for("lp")
    assert backend.name == "highs"


def test_select_backend_for_root_finding_returns_scipy() -> None:
    backend = select_backend_for("root_finding")
    assert backend.name == "scipy"


def test_select_backend_for_rng_returns_numpy() -> None:
    backend = select_backend_for("rng")
    assert backend.name == "numpy"


def test_select_backend_for_unknown_domain_raises() -> None:
    with pytest.raises(BackendUnavailableError):
        select_backend_for("not_a_real_domain")
