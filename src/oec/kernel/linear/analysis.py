"""Matrix analysis helpers (NumPy). Merit: NumPy/LAPACK.

A single module for the linear-algebra kernel: ``matrix_properties`` (the
existing backlog skill), the eigendecomposition, least-squares, and residual
norm helpers introduced in v2.3 Wave A. No LAPACK is reimplemented here —
OEC only translates structured inputs and maps solver status (ADR 0008).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _as_2d_matrix(a: list[list[float]]) -> Any:
    matrix: Any = np.array(a, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("A must be 2-D")
    return matrix


def matrix_properties(a: list[list[float]]) -> dict[str, Any]:
    matrix = _as_2d_matrix(a)
    m, n = int(matrix.shape[0]), int(matrix.shape[1])
    rank = int(np.linalg.matrix_rank(matrix))
    cond = float(np.linalg.cond(matrix)) if min(m, n) > 0 else float("inf")

    result: dict[str, Any] = {
        "shape": [m, n],
        "rank": rank,
        "condition_number": cond,
        "backend": "numpy",
    }

    # Eigenvalues only for square matrices
    if m == n and m > 0:
        eigvals: Any = np.linalg.eigvals(matrix)
        result["eigenvalues_real"] = [float(np.real(v)) for v in eigvals]
        result["eigenvalues_imag"] = [float(np.imag(v)) for v in eigvals]

    u: Any
    s: Any
    vh: Any
    u, s, vh = np.linalg.svd(matrix, full_matrices=False)
    result["singular_values"] = [float(val) for val in list(s)]
    result["svd_u_shape"] = [int(u.shape[0]), int(u.shape[1])]
    result["svd_vh_shape"] = [int(vh.shape[0]), int(vh.shape[1])]
    return result


def eigendecomposition(a: list[list[float]]) -> dict[str, Any]:
    """Eigenvalues and right eigenvectors of a square matrix.

    Returns eigenvalues as parallel ``eigenvalues_real`` /
    ``eigenvalues_imag`` lists (the canonical OEC shape for complex results
    that round-trip through JSON), and the right-eigenvector matrix as a
    list of columns (column ``j`` is the eigenvector for eigenvalue ``j``).
    """
    matrix = _as_2d_matrix(a)
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("eigendecomposition requires a square matrix")
    eigvals: Any
    eigvecs: Any
    eigvals, eigvecs = np.linalg.eig(matrix)
    eigenvalues_real = [float(np.real(v)) for v in eigvals]
    eigenvalues_imag = [float(np.imag(v)) for v in eigvals]
    # eigvecs is (n,n) with column j as eigenvector of eigenvalue j.
    columns: list[list[float]] = []
    for j in range(eigvecs.shape[1]):
        col = eigvecs[:, j]
        col_list = [float(np.real(x)) for x in col]
        columns.append(col_list)
    return {
        "eigenvalues_real": eigenvalues_real,
        "eigenvalues_imag": eigenvalues_imag,
        "eigenvector_columns": columns,
        "eigenvector_norms": [
            float(np.linalg.norm(eigvecs[:, j])) for j in range(eigvecs.shape[1])
        ],
        "n": int(matrix.shape[0]),
        "backend": "numpy",
        # Iterative factorisation is not iterative from OEC's contract point
        # of view — one call, deterministic per ADR 0004. converged is None
        # per ADR 0013 amendment (exact, not iterative).
        "converged": None,
    }


def least_squares(a: list[list[float]], b: list[float]) -> dict[str, Any]:
    """Least-squares solution of ``A @ x ≈ b`` (NumPy ``linalg.lstsq``).

    Works for square, overdetermined, and rank-deficient systems;
    ``rank`` and ``singular_values`` report conditioning; the residual
    vector is given back so callers can use ``residual_norms`` separately.
    """
    matrix: Any = np.array(a, dtype=float)
    rhs: Any = np.array(b, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("A must be 2-D")
    if rhs.ndim != 1:
        raise ValueError("b must be 1-D")
    if matrix.shape[0] != rhs.shape[0]:
        raise ValueError("A rows and b length must match")

    solution: Any
    residuals: Any
    rank: int
    singular_values: Any
    solution, residuals, rank, singular_values = np.linalg.lstsq(matrix, rhs, rcond=None)
    # NumPy returns residuals as ``||b - A x||^2`` only when m > n and rank = n;
    # otherwise an empty array. Be honest: leave residual sum of squares None
    # when it is not computable.
    residual_sum_of_squares: float | None = float(residuals[0]) if residuals.size > 0 else None

    residual_vector = rhs - matrix @ solution
    return {
        "solution": [float(x) for x in solution],
        "residuals": [float(r) for r in residual_vector],
        "rank": int(rank),
        "singular_values": [float(s) for s in singular_values],
        "residual_sum_of_squares": residual_sum_of_squares,
        "backend": "numpy",
        # See ``eigendecomposition`` for the converged-None convention.
        "converged": None,
    }


def residual_norms(r: list[float]) -> dict[str, Any]:
    """Three standard norms of a residual vector (L1, L2, L∞).

    No factorisation is involved — this is a direct closed-form
    computation. ``converged`` is ``None`` per ADR 0013 (exact call).
    """
    vec: Any = np.array(r, dtype=float)
    if vec.ndim != 1:
        raise ValueError("residual must be 1-D")
    norm_l1 = float(np.sum(np.abs(vec)))
    norm_l2 = float(np.sqrt(np.dot(vec, vec)))
    norm_linf = float(np.max(np.abs(vec))) if vec.size else 0.0
    return {
        "l1": norm_l1,
        "l2": norm_l2,
        "linf": norm_linf,
        "n": int(vec.size),
        "backend": "numpy",
        "converged": None,
    }
