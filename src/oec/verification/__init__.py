"""Verification Engine (v2.4, ADR 0021): a structured pre/post report,
folded additively into ``ExecutionResult.validation["verification"]``.

This is an honest v0: it mostly *aggregates* signals the existing validator
layers (schema/dimensional/mathematical/physical/numerical) already
compute, plus two genuinely new checks (``backend_fit``, ``lp_gap``). It
does not redefine ``ExecutionStatus`` semantics (ADR 0007) or the
convergence-declaration contract (ADR 0013) — see ``docs/architecture/adr/
0021-backend-registry-and-verification-engine.md``.
"""
