"""The shared diagnostics shape every computational domain returns (ADR 0022)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ComputationalDiagnostics(BaseModel):
    """Solver diagnostics common across root/interp/diff/int/ode.

    Unlike most OEC models, this one allows extra keys (``extra="allow"``),
    mirroring :class:`~oec.execution.provenance.ProvenanceRecord` (ADR
    0017): domain-specific diagnostics (QUADPACK's ``abs_error``/
    ``tolerance``, a differentiation ``step`` size) shouldn't force every
    other domain to declare fields it never uses. The four fields below are
    the stable, guaranteed cross-domain contract; everything else rides
    along as extra data, read via ``.model_dump()``.

    ``converged`` follows the ADR 0013 amendment: ``None`` means "this call
    was exact, not iterative" (e.g. interpolation, tabulated integration,
    finite-difference differentiation) — distinct from ``False`` (an
    iterative method that ran and did not converge).
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    method: str
    backend: str
    converged: bool | None
    iterations: int | None = None
    function_calls: int | None = None
    residual: float | None = None
    message: str = ""
