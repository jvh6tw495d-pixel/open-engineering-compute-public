"""Verification Engine (v2.4, ADR 0021): a structured pre/post report,
folded additively into ``ExecutionResult.validation["verification"]``.

This is an honest v0: it mostly *aggregates* signals the existing validator
layers (schema/dimensional/mathematical/physical/numerical) already
compute, plus two genuinely new pass/fail checks (``backend_fit``,
``provenance_integrity``) and one purely informational report
(``lp_gap_report``, ``passed`` always ``None`` -- no OEC-configured gap
tolerance exists to evaluate against). It does not redefine
``ExecutionStatus`` semantics (ADR 0007) or the convergence-declaration
contract (ADR 0013) — see ``docs/architecture/adr/
0021-backend-registry-and-verification-engine.md``.
"""
