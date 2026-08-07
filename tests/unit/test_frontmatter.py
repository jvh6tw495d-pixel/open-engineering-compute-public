import pytest

from oec.errors import SkillFrontMatterError
from oec.skills.loader.frontmatter import parse_front_matter
from oec.skills.schemas.manifest import SkillStatus

VALID_TEXT = """---
id: electrical.voltage_drop
version: 0.1.0
status: experimental
domain: electrical
title: Voltage Drop
---

# Purpose

Body text.
"""


def test_parses_valid_front_matter_and_body() -> None:
    front_matter, body = parse_front_matter(VALID_TEXT)
    assert front_matter.id == "electrical.voltage_drop"
    assert front_matter.version == "0.1.0"
    assert front_matter.status is SkillStatus.EXPERIMENTAL
    assert front_matter.domain == "electrical"
    assert front_matter.title == "Voltage Drop"
    assert body == "# Purpose\n\nBody text."


def test_missing_opening_delimiter_is_rejected() -> None:
    with pytest.raises(SkillFrontMatterError):
        parse_front_matter("id: electrical.voltage_drop\n")


def test_missing_closing_delimiter_is_rejected() -> None:
    with pytest.raises(SkillFrontMatterError):
        parse_front_matter("---\nid: electrical.voltage_drop\n")


def test_malformed_yaml_is_rejected() -> None:
    with pytest.raises(SkillFrontMatterError):
        parse_front_matter("---\nid: [unclosed\n---\nbody\n")


def test_non_mapping_front_matter_is_rejected() -> None:
    with pytest.raises(SkillFrontMatterError):
        parse_front_matter("---\n- just\n- a\n- list\n---\nbody\n")


def test_front_matter_missing_required_field_is_rejected() -> None:
    with pytest.raises(SkillFrontMatterError):
        parse_front_matter("---\nid: electrical.voltage_drop\nversion: 0.1.0\n---\nbody\n")


def test_empty_body_after_front_matter_is_allowed() -> None:
    text = (
        "---\n"
        "id: electrical.voltage_drop\n"
        "version: 0.1.0\n"
        "status: experimental\n"
        "domain: electrical\n"
        "title: Voltage Drop\n"
        "---\n"
    )
    _front_matter, body = parse_front_matter(text)
    assert body == ""
