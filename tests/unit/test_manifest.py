import pytest
from pydantic import ValidationError

from oec.common import VersionedRef
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    SchemaRefs,
    SkillManifest,
    SkillStatus,
)


def _base_manifest_kwargs() -> dict:
    return {
        "id": "electrical.voltage_drop",
        "version": "0.1.0",
        "status": SkillStatus.EXPERIMENTAL,
        "domain": "electrical",
        "title": "Voltage Drop",
        "entrypoint": EntrypointSpec(module="implementation", function="execute"),
        "schemas": SchemaRefs(input="input.schema.json", output="output.schema.json"),
        "method": VersionedRef(id="three_phase_impedance_voltage_drop", version="0.1.0"),
    }


def test_valid_manifest_constructs_with_defaults() -> None:
    manifest = SkillManifest(**_base_manifest_kwargs())
    assert manifest.status is SkillStatus.EXPERIMENTAL
    assert manifest.execution.deterministic is True
    assert manifest.execution.network_access is False
    assert manifest.validation.schema_layer is True
    assert manifest.references == []
    assert manifest.tags == []


@pytest.mark.parametrize(
    "bad_id",
    ["VoltageDrop", "voltage_drop", "electrical..voltage_drop", "electrical.Voltage_Drop", ""],
)
def test_invalid_skill_id_is_rejected(bad_id: str) -> None:
    kwargs = _base_manifest_kwargs()
    kwargs["id"] = bad_id
    with pytest.raises(ValidationError):
        SkillManifest(**kwargs)


@pytest.mark.parametrize("bad_version", ["0.1", "v0.1.0", "0.1.0-alpha", "latest"])
def test_invalid_skill_version_is_rejected(bad_version: str) -> None:
    kwargs = _base_manifest_kwargs()
    kwargs["version"] = bad_version
    with pytest.raises(ValidationError):
        SkillManifest(**kwargs)


def test_manifest_is_frozen() -> None:
    manifest = SkillManifest(**_base_manifest_kwargs())
    with pytest.raises(ValidationError):
        manifest.title = "Renamed"  # type: ignore[misc]


def test_validation_policy_accepts_schema_alias_from_yaml_shape() -> None:
    kwargs = _base_manifest_kwargs()
    manifest = SkillManifest(
        **kwargs,
        validation={
            "schema": False,
            "dimensional": True,
            "mathematical": True,
            "physical": True,
            "numerical": True,
        },
    )
    assert manifest.validation.schema_layer is False


def test_schema_refs_holds_input_and_output_paths() -> None:
    refs = SchemaRefs(input="input.schema.json", output="output.schema.json")
    assert refs.input == "input.schema.json"
    assert refs.output == "output.schema.json"


def test_manifest_parses_from_plan_shaped_yaml_dict() -> None:
    """The exact nested shape shown in the master plan's skill.yaml example (section 8.2)."""
    raw = {
        "id": "electrical.voltage_drop",
        "version": "0.1.0",
        "status": "experimental",
        "domain": "electrical",
        "title": "Voltage Drop",
        "entrypoint": {"module": "implementation", "function": "execute"},
        "schemas": {"input": "input.schema.json", "output": "output.schema.json"},
        "method": {"id": "three_phase_impedance_voltage_drop", "version": "0.1.0"},
        "execution": {
            "deterministic": True,
            "timeout_seconds": 5,
            "network_access": False,
            "filesystem_access": False,
        },
        "validation": {
            "schema": True,
            "dimensional": True,
            "mathematical": True,
            "physical": True,
            "numerical": True,
        },
    }
    manifest = SkillManifest(**raw)
    assert manifest.schemas.input == "input.schema.json"
    assert manifest.execution.timeout_seconds == 5
    assert manifest.validation.schema_layer is True
