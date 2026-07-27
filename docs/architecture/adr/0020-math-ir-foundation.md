# ADR 0020: Math IR v0 foundation (linear + scalar-root compilers)

- **Status:** accepted
- **Date:** 2026-07-27
- **Phase:** v2.2 (Step B of `v2.1-delivery-status-and-v2.5-next-steps.md`)

## Context

The v2.1 delivery report authorized exactly one next slice: a versioned Math
IR — closed Pydantic models for symbols, literals, quantities, expressions,
equations, objectives and constraints — compiled to two existing governed
backends (OPS/HiGHS for linear programs, SciPy root-finding for scalar
equations), gated by parity tests against the paths that already exist
(`optimization.lp`, `numerical.root_system`). `OEC_V3_IMPLEMENTATION_PLAN.md`
section 6 designed the intent; no code existed yet.

## Decision

1. **Expressions are a closed Pydantic node tree, not opaque strings**
   (`oec.modeling.ir.Expr`, a discriminated union of `NumberLiteral`,
   `QuantityLiteral`, `ConstantRef`, `SymbolRef`, `UnaryOp`, `BinaryOp`,
   `FunctionCall`). This is what makes structural/dimensional validation
   possible ahead of any numeric evaluation — a string expression cannot be
   dimension-checked without re-parsing it, so the tree, not text, is the
   canonical form.
2. **One audited grammar, not two.** `oec.modeling.expressions.parse_expression`
   builds this tree from a string using
   `oec.kernel.numerics.expressions.parse_and_validate` — the same
   ast-whitelist that already rejected SymPy's `parse_expr` as a sandbox-escape
   vector (see that module's docstring) — rather than re-implementing or
   relaxing the whitelist. The IR grammar is a strict *subset*: `%` and
   `//` are accepted by the kernel evaluator (for plain-float use) but are
   not representable in the IR, because their dimensional behavior on
   physical quantities is not well-defined.
3. **The linear variant is tied to OPS**, per the V3 plan: `MathProblem`
   reuses `oec.ops.models.OPSObjective`/`OPSConstraint` directly rather than
   defining a second linear representation. `oec.modeling.compile_linear`
   translates to an `OPSProblem` and calls the *same* `ops_to_linear_parts`
   -> `solve_linear` sequence `optimization.lp` already uses — no new solver
   logic.
4. **The scalar-root variant is v0-scoped to exactly one equation in one
   unknown**, explicitly rejected (not silently widened) otherwise. It
   compiles to a residual closure evaluated via `oec.modeling.evaluate`
   (plain-magnitude numeric evaluation — literals must already share
   consistent units; the IR checks dimensional *compatibility* before
   solving but does not yet rescale, an explicit non-goal below) and solved
   via `oec.kernel.numerics.root_finding.find_root_bracketed`/
   `find_root_from_guess`, chosen by the existing, already-tested
   `select_default_method` (bracket takes precedence over a guess).
5. **`oec.modeling.classify.classify` is deterministic and non-silent.**
   An objective and equations may never both be present; equation/unknown
   count mismatches raise `UnderdeterminedProblemError`/
   `OverdeterminedProblemError`; an explicit `problem_class` that disagrees
   with the inferred one is a hard error. This is the first real use of
   these two errors and of `DimensionalIncompatibilityError`
   (`oec.core.errors`) — all three existed, unused, since the v2.0
   Scientific Kernel.
6. **The Backend Capability skeleton is intentionally tiny**
   (`oec.backends.registry.get_backend_capabilities`): only availability/
   version descriptors for `highs` and `scipy`. No selection, fallback, or
   adapter abstraction — that is the v2.4 Backend Registry
   (`docs/implementation/technical-debt.md` D-CUR-14).
7. **New experimental skill `mathematics.solve_ir`** classifies a submitted
   IR document and dispatches to the two compilers. Its input schema is
   opaque (`{"ir": {"type": "object"}}`), deep-validated by
   `MathProblem.model_validate` — the same precedent `optimization.lp`
   already sets for `ops`, including keeping `validation.dimensional`/
   `physical: false` in `skill.yaml` so `scripts/audit_physical_units.py`
   does not attempt to scan the opaque field.

## Non-goals (v0)

- MILP-in-IR (Math IR symbols carry no `kind`; only continuous LP).
- Systems of equations / multiple unknowns in the scalar-root compiler
  (structural under/overdetermined checks in `classify` are general;
  `compile_scalar_root` itself is deliberately narrower for v0).
- ODE-in-IR, PDEs, tensor quantities.
- General uncertainty propagation (unchanged from v2.1's `Uncertainty`/
  `UncertainQuantity`, which remain representation-only).
- Automatic unit *rescaling* during scalar-root numeric evaluation (only
  dimensional *compatibility* is checked pre-solve; values must already
  share consistent magnitude scale).
- Symbolic simplification/differentiation, or any `sympy` string-parsing
  path (`sympy.parse_expr`/`sympify` remain out of scope per the existing
  rejection documented in `oec.kernel.numerics.expressions`).
- A full Backend Registry with selection/fallback/adapters (v2.4).

## Consequences

- `optimization.lp`/`numerical.root_system` are unchanged; `mathematics.solve_ir`
  is purely additive and calls the same kernel functions they do.
- A Math IR document can be dimensionally validated before any solver runs,
  which neither existing path could do (both are dimension-blind today).
- The v2.2 stop gate — one LP and one scalar-root problem solved
  exclusively through the IR, matching the existing governed paths — is
  proven by `tests/integration/test_math_ir_linear_parity.py` and
  `tests/integration/test_math_ir_scalar_root_parity.py`.
- Package version, `CHANGELOG.md`, README status and any tag remain
  unchanged in this pass; those are a separate closeout step once this
  implementation is reviewed and accepted, mirroring the v2.1 pattern.
