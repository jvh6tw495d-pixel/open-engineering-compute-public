"""Learning-layer errors — fail-closed, no silent backend swap."""

from __future__ import annotations

from oec.errors import OECError


class LearningError(OECError):
    """Base error for ``oec.learning``."""

    default_code = "learning_error"


class BackendNotAvailableError(LearningError):
    """Raised when a named backend extra is not installed."""

    default_code = "learning_backend_not_available"


class DatasetIntegrityError(LearningError):
    """Raised when dataset version/provenance cannot be verified."""

    default_code = "learning_dataset_integrity"


class BenchmarkError(LearningError):
    """Raised when two runs cannot be compared under one protocol."""

    default_code = "learning_benchmark_error"
