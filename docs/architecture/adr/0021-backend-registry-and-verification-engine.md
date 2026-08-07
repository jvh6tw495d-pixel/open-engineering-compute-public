# ADR 0021: Backend Capability Registry and Verification Engine (v2.4, S1–S3)

- **Status:** accepted
- **Date:** 2026-07-27
- **Phase:** v2.4, slices S1–S3 (`docs/implementation/v2.4-team-brief.md`)

## Context (S0 inventory)

`docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md` §8 scopes v2.4 as three
workstreams: a Backend Capability Registry (`src/oec/backends/{registry.py,
capabilities.py, selection.py, fallback.py, adapters/}`), a Verification
Engine (structured pre/post checks on every execution), and an *optional*
unification of `root/interp/diff/int/ode` under `kernel/computational`. The
plan gives no per-file spec beyond the file tree and three Gate v2.4 bullets
— the internal design was left to construction.

A repo-wide research pass before writing any code found:

- **The v2.2 skeleton (ADR 0020) already existed**: `src/oec/backends/
  registry.py` with a `BackendCapability{name, available, version, reason}`
  model covering only `highs`/`scipy`. No `capabilities.py`/`selection.py`/
  `fallback.py`/`adapters/` existed yet. `numpy` — used in 20+ kernel
  modules, the most-used backend in the codebase — was entirely absent.
- **`oec.execution.provenance.installed_backends()`/`BackendRef` (ADR 0017)
  is a separate, independent probe** of `numpy`/`scipy`/`sympy`/`pint`/
  `pandas`/`highspy`, with an incompatible schema (`version: str` required,
  no "unavailable" concept). It exists for environment audit-trail
  bookkeeping, not capability-aware selection/fallback.
- **Kernel backend usage survey**: numpy is used everywhere (dense linear
  algebra) plus explicit RNG (`np.random.default_rng`) in four modules;
  scipy is used for `optimize` (root scalar/system, curve_fit, minimize,
  minimize_scalar), `integrate` (ODE), `linalg.expm`, and `stats`
  (confidence intervals) — **`scipy.interpolate` is not called anywhere in
  the kernel today**; highs has exactly one access point
  (`kernel/optimization/highs.py`), already gated by
  `HighsNotAvailableError`.
- **The "computational unify" item (S4) is a materially bigger lift than its
  one-line description**: differentiation doesn't exist anywhere in the
  codebase (would be built from scratch); interpolation and integration have
  no kernel module at all (implemented ad hoc inside skill
  `implementation.py` files); only root-finding and ODE have kernel modules,
  and those two already disagree on result shape
  (`RootFindingResult` Pydantic model vs. a `success`-style plain dict).
  Unifying five things that don't share a common shape today — one of which
  doesn't exist — is a different, larger project than "unify five
  siblings," and the brief itself recommends deferring it under calendar
  pressure.
- **`SkillManifest` has no field declaring a required backend capability.**
  Adding one is a skill-authoring contract change across 62+ skills.
- **`ExecutionResult` is `extra="forbid"`**; `validation` already holds
  `{"outcomes": [...]}`. Any new structured object must nest inside an
  existing field, not add a new top-level key.
- `oec.execution.limits.InputLimits`/`check_input_limits` is the closest
  existing "declarative policy + independent check returning
  `list[ValidationOutcome]`" pattern in the codebase.

## Decision

### Backend Capability Registry (S1)

1. **`installed_backends()`/`BackendRef` (ADR 0017) are not touched.** They
   keep recording "which engines were present at runtime" for the audit
   trail. The registry is the separate, richer source of truth for
   capability domains, selection, and fallback. Merging the two would
   require either loosening `BackendRef`'s required `version: str` or
   dropping the registry's `available`/`reason` fields — a real schema
   change to an already-stable, tested ADR 0017 contract for no functional
   gain.
2. **`capabilities.py`** holds static declarations only:
   `DECLARED_CAPABILITIES: dict[str, frozenset[str]]` — `numpy` →
   `{dense_linear_algebra, rng}`, `scipy` → `{root_finding, root_system,
   curve_fit, optimize, integrate_ivp, linalg, stats}` (no `interpolate` —
   declaring an unused capability would be aspirational, not honest),
   `highs` → `{lp, milp}` — plus which backends are required (`numpy`,
   `scipy`) vs. optional extras (`highs`).
3. **`adapters/{numpy,scipy,highs}_backend.py`** are thin `probe() ->
   tuple[bool, str | None, str | None]` functions, moved out of
   `registry.py`'s v2.2 `_highs_capability()`/`_scipy_capability()`
   (behavior unchanged) plus a new numpy probe. No shared base class or
   import of `registry.py`'s model — this avoids any circular import
   between `registry.py` (which imports the adapters) and the adapters.
4. **`registry.py`** grows `BackendCapability` with `domains: frozenset[str]`
   and `required: bool`; `get_backend_capabilities()` aggregates each
   adapter's probe with `capabilities.py`'s static declarations.
5. **`selection.py`** — `select_backend_for(domain) -> BackendCapability` is
   an honest 1:1 lookup, not a scoring algorithm: no capability domain has
   more than one candidate backend today. It is still the correct seam for
   a future multi-backend choice, and removes hand-coded "which backend
   serves X" logic from call sites.
6. **`fallback.py`** — `check_backend_availability(method_id) ->
   list[ValidationOutcome]` mirrors `InputLimits`/`check_input_limits`'s
   shape exactly. "Backend fit vs. skill declaration" is scoped narrowly:
   since the manifest has no capability-declaration field, a small explicit
   `method.id -> capability domain` map covers exactly the skills with a
   genuine optional hard dependency today — every HiGHS-backed method id
   (`highs_lp`, `highs_milp`, `highs_feasibility`, `highs_lp_diagnostics`,
   `highs_weighted_sum`, `highs_scenario_batch`), found via a repo-wide
   survey of `skills/optimization/*/skill.yaml`. A method id with no entry
   has no declared requirement — not the same as declaring it always
   available. Missing backend → one `ERROR`-severity outcome, layer
   `"backend_fit"`. No silent solver swap.

### Verification Engine (S2 pre + S3 post)

7. **`VerificationReport` nests inside `ExecutionResult.validation`** as a
   new `"verification"` key, alongside the existing `"outcomes"` key —
   additive, no new top-level `ExecutionResult` field, keeps
   `tests/integration/test_execution_result_contract.py` green with zero
   changes there.
8. **The engine mostly aggregates existing signals; it does not
   re-implement checks that already exist.** `SchemaValidator`,
   `DimensionalValidator`, and `NumericalDiagnosticsValidator` already cover
   "inputs present," "units/domain," and "convergence/residual/
   conditioning." Concretely, v0 checks:
   - **Pre:** `input_validation` (derived from whether any
     schema/dimensional/mathematical/physical-layer outcome is an `ERROR`)
     + `backend_fit` (new, via `oec.backends.fallback`).
   - **Post:** `convergence` (reads `diagnostics["converged"]` under the
     existing ADR 0013 contract, only when `method.iterative`) +
     `residuals_and_conditioning` (derived from the `numerical`-layer
     outcomes) + `provenance_integrity` (new, real pass/fail: confirms
     `provenance["input_hash"]` is present) + `lp_gap_report` (reports
     `result["mip_gap"]` **only when present** — `passed` is always
     `None`, not a pass/fail gate, since no OEC-configured gap tolerance
     exists to evaluate against; see the amendment below).
   - This is an honest v0, not a claim of "full formal verification"
     without both pre **and** post structure (forbidden per the brief §7).
9. **Verification does not redefine `ExecutionStatus` (ADR 0007) or the
   convergence-declaration contract (ADR 0013).** It reads the same
   `diagnostics["converged"]` `execute()` already enforces; it never
   introduces a second, competing convergence signal, and a failed
   verification check does not by itself change `status` — it is a
   parallel, additive report.
10. **Wired as a plain pipeline stage in `ExecutionService.execute`**, like
    `compute_status`/`build_provenance` — not an injected
    `InputValidator`/`ResultValidator`. It is cross-cutting and always-on,
    not a per-skill pluggable layer. Two additive call sites in
    `src/oec/execution/service.py`: `run_pre_verification(skill, outcomes)`
    right after input-validator outcomes are known, and
    `run_post_verification(skill, result, diagnostics, outcomes,
    provenance)` right after `provenance` is built (post-checks are skipped
    — empty list — when `implementation_failed`, since there is no result to
    check).

## Non-goals (v0, this pass)

- **S4 (computational-kernel unification)** — explicitly deferred with the
  concrete evidence above (differentiation absent, interpolation/
  integration not modularized, root/ODE already disagree on shape). Not a
  slip; a documented deferral per the DoD's own "or explicitly deferred"
  allowance.
- No `SkillManifest` schema change to declare backend capability
  requirements (would touch 62+ skills).
- No multi-backend selection heuristics (nothing to choose between yet).
- No change to `oec.execution.provenance`/ADR 0017's contract.
- Package version, `CHANGELOG.md`, README, and any git tag — declared
  separately, once this is reviewed and accepted, mirroring the v2.1/v2.2
  pattern.

## Consequences

- `optimization.lp`/`.milp`/`.check_feasibility`/`.lp_diagnostics`/
  `.multiobjective`/`.scenario_batch` and every other existing skill are
  unchanged; every execution now additionally carries a structured
  `validation["verification"]` report.
- A missing HiGHS install now produces a clear, structured `backend_fit`
  `ERROR` outcome ahead of the solver call attempting and failing on its
  own, for the skills mapped in `fallback.py`.
- Future work can extend `capabilities.py`'s declarations (e.g. adding
  `scipy.interpolate` once a kernel module actually calls it, or JAX/SymPy
  as optional extras) without touching `selection.py`/`fallback.py`'s
  logic.

## Amendment (2026-07-27, post-review)

An independent review (fable, requested by the user the same day) found the
original `lp_gap` post-check was `passed=True` hardcoded — it could never
fail, making it a reporting field wearing a check's costume despite the
commit message billing it as one of "two genuinely new checks." The
original `reproducibility` check was also misnamed: it only confirms
`provenance["input_hash"]` is present, not that anything was actually
re-run and compared.

Fixed, not just relabeled:

- `PostVerificationCheck.passed` widened from `bool` to `bool | None`
  (`None` = informational, not evaluated — same convention
  `ComputationalDiagnostics.converged` already uses, ADR 0022).
- `lp_gap` → `lp_gap_report`, `passed` always `None`, and the entry is
  **omitted entirely** when no `mip_gap` is present, rather than padding
  the post-check list with an always-passing placeholder.
- `reproducibility` → `provenance_integrity`, kept as a real `bool`
  check (it can, in principle, fail if `build_provenance` ever regressed)
  — its name no longer implies re-execution verification that doesn't
  exist.
- `backend_fit` and `provenance_integrity` are the two real pass/fail
  post/pre checks this engine adds; `lp_gap_report` is reporting, not a
  check, and is documented as such everywhere it's referenced.
