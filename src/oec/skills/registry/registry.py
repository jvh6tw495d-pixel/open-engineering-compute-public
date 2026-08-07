"""In-memory registry of loaded skills: discovery, resolution, and search.

Mirrors the API sketched in plan section 10.2:
``list_skills``, ``get_skill``, ``search``, ``register``, ``validate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from oec.errors import SkillError, SkillNotFoundError, SkillVersionConflictError
from oec.skills.lifecycle.lifecycle import is_loadable_by_default
from oec.skills.loader.loader import load_skill
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import SkillManifest

_MANIFEST_FILENAME = "skill.yaml"


def _version_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in version.split("."))
    return (major, minor, patch)


def discover_skill_dirs(root: Path) -> list[Path]:
    """Find every directory under ``root`` that directly contains a ``skill.yaml``."""
    if not root.is_dir():
        return []
    return sorted(manifest_path.parent for manifest_path in root.rglob(_MANIFEST_FILENAME))


@dataclass(frozen=True)
class RegistrationFailure:
    """A skill directory that failed to load, and why."""

    path: Path
    error: SkillError


@dataclass
class RegistrationReport:
    """Outcome of registering every skill found under a root directory."""

    loaded: list[LoadedSkill] = field(default_factory=list)
    failures: list[RegistrationFailure] = field(default_factory=list)


class SkillRegistry:
    """Holds loaded skills, indexed by id and version."""

    def __init__(self) -> None:
        self._skills: dict[str, dict[str, LoadedSkill]] = {}

    def register(self, path: Path) -> LoadedSkill:
        """Load the skill at ``path`` and add it to the registry.

        Raises :class:`~oec.errors.SkillVersionConflictError` if a skill
        with the same id and version is already registered, and whatever
        :func:`oec.skills.loader.loader.load_skill` raises for an invalid
        skill directory.
        """
        skill = load_skill(path)
        versions = self._skills.setdefault(skill.manifest.id, {})
        if skill.manifest.version in versions:
            existing = versions[skill.manifest.version]
            raise SkillVersionConflictError(
                f"skill {skill.manifest.id!r} version {skill.manifest.version!r} "
                "is already registered",
                details={
                    "skill_id": skill.manifest.id,
                    "version": skill.manifest.version,
                    "existing_path": str(existing.path),
                    "conflicting_path": str(path),
                },
            )
        versions[skill.manifest.version] = skill
        return skill

    def register_all(self, root: Path) -> RegistrationReport:
        """Register every skill found under ``root``.

        A single invalid skill directory does not stop discovery of its
        siblings — each failure is collected instead of raised, so one
        broken skill cannot take the whole catalog down.
        """
        report = RegistrationReport()
        for skill_dir in discover_skill_dirs(root):
            try:
                report.loaded.append(self.register(skill_dir))
            except SkillError as exc:
                report.failures.append(RegistrationFailure(path=skill_dir, error=exc))
        return report

    def list_skills(self, *, include_retired: bool = False) -> list[SkillManifest]:
        """List manifests of all registered skills, sorted by id then version."""
        manifests = [
            skill.manifest
            for versions in self._skills.values()
            for skill in versions.values()
            if include_retired or is_loadable_by_default(skill.manifest.status)
        ]
        return sorted(manifests, key=lambda m: (m.id, _version_key(m.version)))

    def get_skill(self, skill_id: str, version: str | None = None) -> LoadedSkill:
        """Resolve a skill by id, and optionally an exact version.

        Without ``version``, resolves to the highest version among
        non-retired registrations; if only retired versions exist, an
        explicit ``version`` is required (retired skills are not resolved
        by default, per plan section 8.3).
        """
        versions = self._skills.get(skill_id)
        if not versions:
            raise SkillNotFoundError(
                f"no skill registered with id {skill_id!r}", details={"skill_id": skill_id}
            )

        if version is not None:
            skill = versions.get(version)
            if skill is None:
                raise SkillNotFoundError(
                    f"skill {skill_id!r} has no registered version {version!r}",
                    details={
                        "skill_id": skill_id,
                        "version": version,
                        "available_versions": sorted(versions, key=_version_key),
                    },
                )
            return skill

        candidates = {
            v: s for v, s in versions.items() if is_loadable_by_default(s.manifest.status)
        }
        if not candidates:
            raise SkillNotFoundError(
                f"skill {skill_id!r} only has retired versions; pass an explicit version",
                details={
                    "skill_id": skill_id,
                    "available_versions": sorted(versions, key=_version_key),
                },
            )
        best_version = max(candidates, key=_version_key)
        return candidates[best_version]

    def search(
        self,
        *,
        domain: str | None = None,
        tags: list[str] | None = None,
        include_retired: bool = False,
    ) -> list[SkillManifest]:
        """List registered skills filtered by domain and/or required tags."""
        results = self.list_skills(include_retired=include_retired)
        if domain is not None:
            results = [manifest for manifest in results if manifest.domain == domain]
        if tags:
            required = set(tags)
            results = [manifest for manifest in results if required.issubset(manifest.tags)]
        return results

    def validate(self, skill_id: str, version: str | None = None) -> SkillManifest:
        """Confirm ``skill_id`` (optionally at ``version``) is registered and valid.

        Since every registered skill has already passed full manifest,
        front-matter, and artifact validation at load time, this is a
        resolution check that surfaces the same structured errors
        ``get_skill`` would.
        """
        return self.get_skill(skill_id, version).manifest
