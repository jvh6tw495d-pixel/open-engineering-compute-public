"""Unified computational kernel: root-finding, interpolation,
differentiation, integration, and ODE solving under one shared diagnostics
shape (v2.5 "Mathematics Complete" prerequisite, ADR 0022).

Before this package, root-finding used a Pydantic result/diagnostics pair,
root-system and ODE used an ad-hoc dict, and interpolation/integration had
no kernel module at all (their logic lived inline in skill
``implementation.py`` files). Every domain here now returns its own frozen
result model wrapping the shared :class:`~oec.kernel.computational.
diagnostics.ComputationalDiagnostics` — the payload differs by domain (a
root vs. a trajectory vs. interpolated values), the diagnostics contract
does not.
"""
