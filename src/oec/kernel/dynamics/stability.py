"""Basic LTI stability margins from state matrix poles. Merit: NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np


def stability_margins(
    a: list[list[float]],
    *,
    time_base: str = "continuous",
) -> dict[str, Any]:
    """Eigenvalue-based stability check for an LTI state matrix ``A``.

    Continuous: stable iff all Re(λ) < 0.
    Discrete: stable iff all |λ| < 1.
    """
    if time_base not in {"continuous", "discrete"}:
        raise ValueError("time_base must be 'continuous' or 'discrete'")
    a_m = np.asarray(a, dtype=float)
    if a_m.ndim != 2 or a_m.shape[0] != a_m.shape[1]:
        raise ValueError("A must be square")
    if a_m.shape[0] == 0:
        raise ValueError("A must be non-empty")

    eigvals = np.linalg.eigvals(a_m)
    real = [float(np.real(v)) for v in eigvals]
    imag = [float(np.imag(v)) for v in eigvals]
    mag = [float(np.abs(v)) for v in eigvals]

    if time_base == "continuous":
        spectral_abscissa = float(np.max(np.real(eigvals)))
        stable = spectral_abscissa < 0.0
        margin = float(-spectral_abscissa)  # distance of abscissa to imaginary axis
        criterion = "all_real_parts_negative"
    else:
        spectral_radius = float(np.max(np.abs(eigvals)))
        stable = spectral_radius < 1.0
        margin = float(1.0 - spectral_radius)
        criterion = "all_moduli_less_than_one"
        spectral_abscissa = spectral_radius  # report radius under same field name? better separate

    result: dict[str, Any] = {
        "eigenvalues_real": real,
        "eigenvalues_imag": imag,
        "eigenvalues_modulus": mag,
        "stable": bool(stable),
        "stability_margin": margin,
        "criterion": criterion,
        "time_base": time_base,
        "n": int(a_m.shape[0]),
        "backend": "numpy",
        "converged": None,
    }
    if time_base == "continuous":
        result["spectral_abscissa"] = spectral_abscissa
    else:
        result["spectral_radius"] = float(np.max(np.abs(eigvals)))
    return result
