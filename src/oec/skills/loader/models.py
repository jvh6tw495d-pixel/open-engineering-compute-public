"""The result of successfully loading a skill directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.schemas.manifest import SkillManifest


class LoadedSkill(BaseModel):
    """A skill whose manifest, front matter, and declared artifacts all
    checked out — everything the registry and, later, the execution
    service need without re-reading the filesystem."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest: SkillManifest
    front_matter: SkillFrontMatter
    path: Path
    body: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
