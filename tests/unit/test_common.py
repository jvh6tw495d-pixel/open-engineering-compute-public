import pytest
from pydantic import ValidationError

from oec.common import VersionedRef


def test_versioned_ref_holds_id_and_version() -> None:
    ref = VersionedRef(id="scipy.brentq", version="1")
    assert ref.id == "scipy.brentq"
    assert ref.version == "1"


def test_versioned_ref_is_frozen() -> None:
    ref = VersionedRef(id="scipy.brentq", version="1")
    with pytest.raises(ValidationError):
        ref.version = "2"  # type: ignore[misc]


def test_versioned_ref_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VersionedRef(id="scipy.brentq", version="1", extra_field="nope")  # type: ignore[call-arg]
