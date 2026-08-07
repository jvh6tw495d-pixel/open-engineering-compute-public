"""P1 (optional, D7) — light total harmonic distortion (THD) v0.

This is the *optional* P1 slice (D7): a light-weight, non-blocking THD
helper. It takes harmonic **magnitudes as input** (v0: no FFT/spectral
extraction from a waveform, no filter design) and reports the standard
ratio-based THD-F definition. This does not attempt to solve
electroquímica de célula, harmonic filter design, or resonance analysis.
"""

from __future__ import annotations

import math

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

THD_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Harmonic RMS magnitudes are supplied directly as input; this module does not"
        " perform FFT/spectral extraction from a raw waveform",
        source="D7 v0",
    ),
    Assumption(
        text="THD is defined relative to the fundamental (THD-F), not the RMS total (THD-R)",
        source="D7 v0",
    ),
)

_HARMONICS_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.ELECTRICAL,),
    description="Light THD-F v0 from input harmonic magnitudes (D7, optional P1 slice)",
)

THD_LAW = PhysicalLaw(
    id="electrical.harmonics.total_harmonic_distortion",
    name="Total harmonic distortion, THD-F (input magnitudes)",
    hypotheses=THD_ASSUMPTIONS,
    validity=_HARMONICS_VALIDITY,
    references=("IEEE 519",),
    evaluator=lambda state: float(
        math.sqrt(math.fsum(m**2 for m in state["harmonics"])) / state["fundamental"]
    ),
)


def total_harmonic_distortion(fundamental: QuantityValue, harmonics: list[QuantityValue]) -> float:
    """Compute THD-F = sqrt(Σ V_n^2) / V_1 for n >= 2 via the executed :data:`THD_LAW`.

    ``harmonics`` are converted to ``fundamental``'s unit before the ratio is
    formed, so a mix of e.g. V and mV inputs is handled correctly.
    """
    if fundamental.value <= 0:
        raise PhysicsEvaluationError("fundamental magnitude must be positive")
    if not harmonics:
        raise PhysicsEvaluationError("THD requires at least one harmonic magnitude")

    converted = [as_canonical(harmonic, fundamental.unit).value for harmonic in harmonics]
    return THD_LAW.evaluate({"fundamental": fundamental.value, "harmonics": converted})


__all__ = ["THD_ASSUMPTIONS", "THD_LAW", "total_harmonic_distortion"]
