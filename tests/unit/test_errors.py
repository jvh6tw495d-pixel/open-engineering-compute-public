from oec.errors import (
    ExecutionError,
    OECError,
    OECValidationError,
    SkillError,
    SkillManifestError,
    SkillNotFoundError,
)


def test_oec_error_default_code_and_empty_details() -> None:
    err = OECError("something went wrong")
    assert err.code == "oec_error"
    assert err.message == "something went wrong"
    assert err.details == {}


def test_oec_error_to_dict_is_structured_and_secret_free() -> None:
    err = OECError("bad input", code="custom_code", details={"field": "voltage"})
    assert err.to_dict() == {
        "code": "custom_code",
        "message": "bad input",
        "details": {"field": "voltage"},
    }


def test_subclasses_have_distinct_default_codes() -> None:
    assert SkillError("x").code == "skill_error"
    assert SkillNotFoundError("x").code == "skill_not_found"
    assert SkillManifestError("x").code == "skill_manifest_invalid"
    assert OECValidationError("x").code == "validation_error"
    assert ExecutionError("x").code == "execution_error"


def test_all_oec_exceptions_are_catchable_as_oec_error() -> None:
    for exc_cls in (
        SkillError,
        SkillNotFoundError,
        SkillManifestError,
        OECValidationError,
        ExecutionError,
    ):
        assert issubclass(exc_cls, OECError)
