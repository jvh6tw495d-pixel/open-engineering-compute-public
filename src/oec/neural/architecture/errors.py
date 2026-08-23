"""Architecture IR errors (ADR 0047)."""

from __future__ import annotations

from oec.errors import OECError


class UnknownBlockError(OECError):
    default_code = "unknown_architecture_block"


class UnknownFamilyError(OECError):
    default_code = "unknown_architecture_family"


class DuplicateBlockError(OECError):
    default_code = "duplicate_architecture_block"


class ArchitectureValidationError(OECError):
    default_code = "architecture_validation_error"
