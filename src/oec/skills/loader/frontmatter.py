"""Parses the YAML front matter of a skill's ``skill.md`` (plan section 8.1).

``skill.md`` opens with a ``---`` delimited YAML block carrying the five
fields a human reviewer needs at a glance (``id``, ``version``, ``status``,
``domain``, ``title``); everything below it is free-form Markdown prose.
This front matter is cross-checked against ``skill.yaml`` by the loader —
see :mod:`oec.skills.loader.loader` — so a skill cannot silently disagree
with itself about what it is.
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from oec.errors import SkillFrontMatterError
from oec.skills.schemas.manifest import SkillStatus

_DELIMITER = "---"


class SkillFrontMatter(BaseModel):
    """The human-facing identity fields declared at the top of ``skill.md``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    status: SkillStatus
    domain: str
    title: str


def parse_front_matter(text: str) -> tuple[SkillFrontMatter, str]:
    """Split ``skill.md`` content into its front matter and Markdown body.

    Raises :class:`SkillFrontMatterError` if the front matter block is
    missing, is not valid YAML, or doesn't match the expected shape.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIMITER:
        raise SkillFrontMatterError(
            "skill.md must start with a '---' delimited YAML front matter block",
            details={"first_line": lines[0] if lines else ""},
        )

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == _DELIMITER
        )
    except StopIteration as exc:
        raise SkillFrontMatterError(
            "skill.md front matter block is missing its closing '---'"
        ) from exc

    raw_front_matter = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")

    try:
        parsed = yaml.safe_load(raw_front_matter)
    except yaml.YAMLError as exc:
        raise SkillFrontMatterError(
            f"skill.md front matter is not valid YAML: {exc}",
        ) from exc

    if not isinstance(parsed, dict):
        raise SkillFrontMatterError(
            "skill.md front matter must be a YAML mapping",
            details={"parsed_type": type(parsed).__name__},
        )

    try:
        front_matter = SkillFrontMatter(**parsed)
    except ValidationError as exc:
        raise SkillFrontMatterError(
            f"skill.md front matter does not match the expected shape: {exc}",
            details={"errors": exc.errors(include_url=False)},
        ) from exc

    return front_matter, body
