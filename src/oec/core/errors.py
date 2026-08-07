"""Core scientific errors (domain-independent). Extend :class:`oec.errors.OECError`."""

from __future__ import annotations

from oec.errors import OECError, OECValidationError


class ScientificDomainError(OECValidationError):
    """Value outside declared scientific domain / ValidityDomain."""

    default_code = "scientific_domain_error"


class DimensionalIncompatibilityError(OECValidationError):
    """Operation is dimensionally invalid."""

    default_code = "dimensional_incompatibility"


class BackendUnavailableError(OECError):
    """Required computational backend is not installed or not selectable."""

    default_code = "backend_unavailable"


class UnderdeterminedProblemError(OECValidationError):
    """Problem has fewer constraints/data than needed for a unique solution."""

    default_code = "underdetermined_problem"


class OverdeterminedProblemError(OECValidationError):
    """Problem has conflicting constraints with no feasible solution."""

    default_code = "overdetermined_problem"
