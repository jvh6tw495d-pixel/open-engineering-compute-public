---
id: mathematics.solve_ir
version: 0.1.0
status: experimental
domain: mathematics
title: Math IR Solver (Linear + Scalar Root)
---

# Purpose

Solve a problem expressed in OEC's Math IR
(`docs/architecture/adr/0020-math-ir-foundation.md`): a versioned, closed set
of Pydantic models for symbols, quantities, expressions, equations and linear
objectives/constraints. This skill classifies the submitted IR document and
compiles it to an existing governed backend — it introduces no new solver
logic of its own.

# Official methodology

Method id: `math_ir_v0`. Two problem classes are supported today:

- `linear_program` — compiled to an OPS v0.1 document and solved via HiGHS,
  the same path `optimization.lp` uses.
- `scalar_root` — exactly one equation in one unknown, compiled to a
  residual function and solved via SciPy (`scipy.optimize.brentq`/`newton`),
  the same kernel `numerical.root_system`'s method family uses.

# Assumptions

- Numeric evaluation of Math IR expressions treats literal magnitudes as
  already expressed in mutually consistent units; the IR checks dimensional
  *compatibility* before solving but does not yet rescale values (ADR 0020).
- v0 `scalar_root` supports exactly one equation and one unknown; systems
  are rejected explicitly, not silently widened.

# Numerical diagnostics

- `linear_program`: `diagnostics.converged` mirrors HiGHS's optimal/infeasible/
  unbounded/other status, same as `optimization.lp`.
- `scalar_root`: `diagnostics` is `RootFindingDiagnostics` (method, converged,
  iterations, function_calls, residual), same as `mathematics.solve_root`.

# References

See `references.md`.

# Changelog

- 0.1.0: initial Math IR v0 foundation (linear + scalar-root compilers).
