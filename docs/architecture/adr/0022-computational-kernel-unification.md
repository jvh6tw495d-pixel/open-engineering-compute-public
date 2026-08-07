# ADR 0022: Computational kernel unification (v2.5 prerequisite)

- **Status:** accepted
- **Date:** 2026-07-27
- **Phase:** v2.5 "Mathematics Complete" hard gate — the "computational"
  prerequisite (deferred from v2.4 as S4, ADR 0021)

## Context

`OEC_V3_IMPLEMENTATION_PLAN.md` §9's v2.5 checklist (V3 §16) requires
"Applied + computational + verification" operational. Verification shipped
in v2.4 (ADR 0021); "computational" is exactly the item ADR 0021 explicitly
deferred as S4: unifying root-finding, interpolation, differentiation,
integration, and ODE solving under `src/oec/kernel/computational/`.

Before this ADR, three incompatible shapes existed, and one domain didn't
exist at all:

| Domain | Location | Shape |
|---|---|---|
| root (scalar) | `kernel/numerics/root_finding.py` | Pydantic `RootFindingResult{root, diagnostics: RootFindingDiagnostics}` |
| root (system) | `kernel/numerics/root_system.py` | ad-hoc `dict{x, success, message, residual_norm, nfev, method, backend}` |
| ODE | `kernel/numerics/ode.py` | ad-hoc `dict{t, y, success, message, nfev, method, backend}` |
| interpolation | none — inline in `skills/mathematics/interpolate/implementation.py` | n/a |
| integration | none — inline in `skills/mathematics/integrate/implementation.py` (function mode via QUADPACK, tabulated mode via Simpson/trapezoid) | n/a |
| differentiation | did not exist anywhere | n/a |

Exactly 7 files imported the three existing kernel modules directly
(confirmed by grep): `skills/mathematics/solve_root/implementation.py`,
`skills/numerical/root_system/implementation.py`,
`skills/numerical/ode_ivp/implementation.py`,
`src/oec/modeling/compile_scalar_root.py` (the v2.2 Math IR scalar-root
compiler), `tests/unit/test_root_finding.py` (renamed to
`test_kernel_computational_roots.py`), `tests/property/
test_root_finding_properties.py`, `tests/installation/
test_installation_smoke.py`.

## Decision

1. **Full migration, no compatibility shims.** Seven importers is small
   enough to update directly rather than leaving deprecated re-export
   shims behind ("don't use backwards-compatibility shims when you can
   just change the code"). `kernel/numerics/{root_finding,root_system,
   ode}.py` are deleted; their logic moved into `kernel/computational/`.
2. **One shared `ComputationalDiagnostics` model, per-domain result
   wrappers.** Forcing every domain's payload (a root vs. a trajectory vs.
   interpolated values) into one shape would be artificial — what actually
   unifies them is the diagnostics contract, generalized from
   `RootFindingDiagnostics` (the more mature, already-Pydantic, ADR
   0007/0013-aligned shape) rather than the ad-hoc dicts:
   `ComputationalDiagnostics{method, backend, converged, iterations,
   function_calls, residual, message}`. Each domain gets its own frozen
   result model wrapping it: `RootResult`, `RootSystemResult`,
   `ODEResult`, `InterpolationResult`, `IntegrationResult`,
   `DifferentiationResult`.
3. **`ComputationalDiagnostics` uses `extra="allow"`**, unlike most OEC
   models — mirroring `ProvenanceRecord` (ADR 0017), for the same reason:
   domain-specific diagnostics (QUADPACK's `abs_error`/`tolerance`, a
   differentiation `step`) shouldn't force every other domain to declare
   fields it never uses. The four core fields stay a stable, guaranteed
   contract; everything else rides along as extra data via
   `.model_dump()`.
4. **Skill boundaries are unaffected.** Every migrated skill's
   `implementation.py` already reshaped its kernel call's raw output into
   its own `result`/`diagnostics` dicts before returning (`ode_ivp`/
   `root_system` already dropped `backend`/`method` and renamed
   `nfev`→`n_function_evaluations`). Migrating to the new kernel functions
   changed what's *inside* that reshaping step, not the shape it produces
   — every existing skill schema, manifest, and golden test is unchanged
   and unmodified. No skill version bump (no schema/behavior change, per
   `docs/contracts/skill-versioning.md`'s bump table).
5. **Differentiation is finite-difference, hand-rolled, not a SciPy
   wrapper.** `scipy.misc.derivative` was removed from modern SciPy;
   `scipy.optimize.approx_fprime` only does forward differences with no
   step control. A small central/forward/backward implementation with the
   standard adaptive step (`h = max(|x|, 1) · ε^(1/3)` for central,
   `ε^(1/2)` for one-sided) is the right-sized, auditable choice — not a
   reimplementation of existing functionality, since nothing suitable
   remains to wrap.
6. **New minimal experimental skill `mathematics.differentiate`** gives
   the differentiation module a real SDK/CLI/REST/MCP-visible surface,
   matching how every other kernel domain already has at least one skill,
   and how Math IR shipped `mathematics.solve_ir` as its v0 proof of use
   (ADR 0020). Reuses the existing safe expression parser
   (`oec.kernel.numerics.expressions.compile_expression`) — no new parsing
   surface.

## Non-goals (this slice)

- DAE, symbolic differentiation, autodiff/JAX (explicitly excluded from
  core per the V3 plan's "Computational (bounded)" table).
- `scipy.sparse` paths.
- Gradient/Jacobian for vector-valued or multivariate functions —
  `mathematics.differentiate` is scalar-to-scalar only for v0.
- Golden-set expansion to 130 cases and the public-API documentation
  audit — separate, larger v2.5 slices, not started here.
- Any change to `oec.execution.provenance`/ADR 0017's `installed_backends`
  contract.

## Consequences

- `RootFindingDiagnostics`/`RootFindingResult` no longer exist;
  `RootResult`/`ComputationalDiagnostics` (`oec.kernel.computational.
  roots`) replace them. Anything outside this repo importing the old
  names would break — none exists (private incubation, no public
  release yet).
- `oec.core.errors` still has an unused `DimensionalIncompatibilityError`/
  `UnderdeterminedProblemError` vocabulary unrelated to this change;
  `NumericalDomainError` remains the right error type for malformed
  computational calls, unchanged.
- Every existing root/ODE/interpolate/integrate skill's golden tests pass
  unmodified, proving zero behavior change at the skill boundary.
- `mathematics.differentiate`'s `find_root_from_guess`/`select_default_
  method` docstring no longer needs to disclaim "no expression-
  differentiation support yet" — that gap is closed, though
  `select_default_method` itself still never auto-selects `newton` (a
  caller must still pass `fprime` explicitly; auto-wiring
  `mathematics.differentiate` into root-finding's Newton path is a
  possible future skill-composition enhancement, not done here).
