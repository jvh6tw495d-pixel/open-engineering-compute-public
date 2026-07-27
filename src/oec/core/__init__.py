"""Scientific Kernel core types (v2.0) — domain-independent.

This package must not import skill domains (electrical, finance, …).
"""

from oec.core.scientific_result import ScientificResult, from_execution_result
from oec.core.types import Assumption, BackendRef, MethodRef

__all__ = [
    "Assumption",
    "BackendRef",
    "MethodRef",
    "ScientificResult",
    "from_execution_result",
]
