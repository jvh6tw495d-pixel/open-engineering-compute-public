"""Chemistry-domain exceptions."""

from oec.errors import OECError


class ChemistryError(OECError):
    """Base error raised by the chemistry library."""

    default_code = "chemistry_error"


class StoichiometryError(ChemistryError):
    """Raised when a reaction is not atom-balanced or extent is invalid."""

    default_code = "stoichiometry_error"


class ChemistryEvaluationError(ChemistryError):
    """Raised when a chemistry primitive cannot be evaluated."""

    default_code = "chemistry_evaluation_error"


__all__ = ["ChemistryError", "ChemistryEvaluationError", "StoichiometryError"]
