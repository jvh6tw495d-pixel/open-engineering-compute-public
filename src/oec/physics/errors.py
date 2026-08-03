"""Physics-domain exceptions."""

from oec.errors import OECError


class PhysicsError(OECError):
    """Base error raised by the physics library."""

    default_code = "physics_error"


class PhysicsEvaluationError(PhysicsError):
    """Raised when an executable physical law cannot be evaluated."""

    default_code = "physics_evaluation_error"


class ConservationError(PhysicsError):
    """Raised for an invalid conservation-check request."""

    default_code = "conservation_error"


__all__ = ["ConservationError", "PhysicsError", "PhysicsEvaluationError"]
