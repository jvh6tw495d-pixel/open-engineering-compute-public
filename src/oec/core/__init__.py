"""Scientific Kernel core types (v2.0) — domain-independent.

This package must not import skill domains (electrical, finance, …).
"""

from oec.core.diagnostics import Diagnostic, diagnostics_from_mapping
from oec.core.errors import (
    BackendUnavailableError,
    DimensionalIncompatibilityError,
    OverdeterminedProblemError,
    ScientificDomainError,
    UnderdeterminedProblemError,
)
from oec.core.provenance import ProvenanceRecord
from oec.core.scientific_result import ScientificResult, from_execution_result
from oec.core.types import Assumption, BackendRef, MethodRef
from oec.core.validity import ValidityDomain

__all__ = [
    "Assumption",
    "BackendRef",
    "BackendUnavailableError",
    "Diagnostic",
    "DimensionalIncompatibilityError",
    "MethodRef",
    "OverdeterminedProblemError",
    "ProvenanceRecord",
    "ScientificDomainError",
    "ScientificResult",
    "UnderdeterminedProblemError",
    "ValidityDomain",
    "diagnostics_from_mapping",
    "from_execution_result",
]
