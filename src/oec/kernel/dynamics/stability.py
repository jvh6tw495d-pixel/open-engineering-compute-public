"""Spectral stability of LTI state matrices (not gain/phase margins). Merit: NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np

# Boundary tolerance for classifying poles as marginal
_BOUNDARY_TOL = 1e-12


def stability_margins(
    a: list[list[float]],
    *,
    time_base: str = "continuous",
    boundary_tol: float = _BOUNDARY_TOL,
) -> dict[str, Any]:
    """Spectral stability classification for an LTI state matrix ``A``.

    This reports **pole / spectral** margins only:

    * continuous: spectral abscissa = max Re(λ); stable iff max Re(λ) < -tol
    * discrete: spectral radius = max |λ|; stable iff radius < 1 - tol

    It does **not** compute classical gain margin, phase margin, or robust
    stability margins of a loop transfer function (B23-04).
    """
    if time_base not in {"continuous", "discrete"}:
        raise ValueError("time_base must be 'continuous' or 'discrete'")
    if boundary_tol < 0:
        raise ValueError("boundary_tol must be >= 0")
    a_m = np.asarray(a, dtype=float)
    if a_m.ndim != 2 or a_m.shape[0] != a_m.shape[1]:
        raise ValueError("A must be square")
    if a_m.shape[0] == 0:
        raise ValueError("A must be non-empty")

    eigvals = np.linalg.eigvals(a_m)
    real = [float(np.real(v)) for v in eigvals]
    imag = [float(np.imag(v)) for v in eigvals]
    mag = [float(np.abs(v)) for v in eigvals]
    tol = float(boundary_tol)

    if time_base == "continuous":
        spectral_abscissa = float(np.max(np.real(eigvals)))
        if spectral_abscissa < -tol:
            classification = "stable"
        elif abs(spectral_abscissa) <= tol:
            classification = "marginal"
        else:
            classification = "unstable"
        margin = float(-spectral_abscissa)
        criterion = "spectral_abscissa"
        metric_name = "spectral_abscissa"
        metric_value = spectral_abscissa
    else:
        spectral_radius = float(np.max(np.abs(eigvals)))
        if spectral_radius < 1.0 - tol:
            classification = "stable"
        elif abs(spectral_radius - 1.0) <= tol:
            classification = "marginal"
        else:
            classification = "unstable"
        margin = float(1.0 - spectral_radius)
        criterion = "spectral_radius"
        metric_name = "spectral_radius"
        metric_value = spectral_radius

    return {
        "eigenvalues_real": real,
        "eigenvalues_imag": imag,
        "eigenvalues_modulus": mag,
        "stable": classification == "stable",
        "classification": classification,
        "spectral_stability_margin": margin,
        # Backward-compatible alias
        "stability_margin": margin,
        "margin_kind": "spectral_pole_margin_not_gain_phase",
        "criterion": criterion,
        metric_name: metric_value,
        "boundary_tol": tol,
        "time_base": time_base,
        "n": int(a_m.shape[0]),
        "backend": "numpy",
        "converged": None,
    }
