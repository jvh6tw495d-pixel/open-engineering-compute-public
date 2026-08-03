# ADR 0025: Physics units and dimensional API (Pint reuse, `atol + rtol×scale` tolerance)

- **Status:** Draft — Wave 0; harden/accepted-candidate on Wave 2; accept on Wave 6
- **Date:** 2026-08-03
- **Phase:** v2.6.0 "Physics Foundation P1–P5 v0", Wave 0–2 (`docs/implementation/
  v2.6-EXECUTION-PLAN.md`, decision D5)

## Context

OEC already has one dimensional-correctness story, built across three
prior ADRs: a single shared Pint registry (ADR 0011), `QuantityValue` as
the canonical quantity shape (ADR 0003), and central dimensional
normalization at the `ExecutionService` boundary via `x-oec-unit`
(ADR 0016). `oec.modeling.dimensions` additionally provides
`infer_dimension`/`dimension_of` for the Math IR expression path
(ADR 0020). `oec.physics` (ADR 0024) is a new consumer of both — it must
not become a second, parallel unit system.

The Codex audit (`docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §B
risk 7) separately flagged that conservation checks proposed for
`oec.physics.conservation` risked using one generic absolute tolerance
across every domain (e.g. a flat `1e-6`), which is unsound once residuals
span domains with wildly different characteristic scales and units (watts
vs. pascals vs. kg/s vs. per-unit). A tolerance without a declared scale
and unit produces false passes on large-magnitude problems and false
failures on small-magnitude ones.

## Decision

### 1. Reuse only: `kernel.units` + `QuantityValue` + `modeling.dimensions`

`src/oec/physics/units.py` provides helpers (`as_canonical`,
`require_compatible`, and similar) built strictly on top of
`oec.kernel.units.registry` and `QuantityValue`. Instantiating a second
`pint.UnitRegistry` anywhere inside `oec.physics` is forbidden and is a
GATE-W2 automatic NO-GO. Skill-level unit declaration (`x-oec-unit`) and
normalization continue to happen exactly where ADR 0016 puts them — inside
`ExecutionService`, before a skill calls into `oec.physics`. `oec.physics`
itself never calls `apply_dimensional_normalization`; it either receives
already-canonical magnitudes or accepts a `QuantityValue` and converts it
explicitly via `kernel.units`, never through a second, ad-hoc conversion
path.

`src/oec/physics/dimensions.py` is a thin façade over
`oec.modeling.dimensions`, used only where the underlying computation goes
through the Math IR `Expr` path. It does not reimplement dimension algebra;
where a call is a plain numeric API rather than an IR expression, the
relevant checks come from `oec.validation.physical` and domain-specific
validation, not from a re-parsed dimension string.

### 2. Public dimensional API surface lives in `oec.physics`

Consumers of `oec.physics` (skills across P1–P5) get their dimensional
guarantees through this package's public helpers, not by hand-rolling unit
math per skill. A canonical-units table is documented in Wave 2
(`docs/contracts/units.md`, "Physics library consumers" section) covering
at minimum: `W`, `V`, `A`, `Ω`, `K`, `W/(m·K)`, `m`, `m/s`, `Pa`,
`kg/m³`, `J`, `N`, `Pa` (stress) — one characteristic unit per P1–P4 slice
at minimum. An incompatible unit is always a structured, fail-closed error;
silent coercion between incompatible dimensions is never acceptable
anywhere in this package.

### 3. Tolerance policy: `atol + rtol × scale`, never a bare absolute number

Every conservation/balance check produced by `oec.physics.conservation`
(ADR 0024 §4) resolves `balanced` as:

```
balanced  ⇔  |residual| ≤ atol + rtol × scale
```

where `residual` is the imbalance in the check's canonical unit (W, Pa,
kg/s, pu, J, …), `atol` is an absolute tolerance in that same unit, `rtol`
is a dimensionless relative tolerance, and `scale` is the problem's
characteristic scale (e.g. `max(|balance terms|)`, or a documented
reference flow/capacity). This is a **cross-unit policy** — the formula
itself is domain-agnostic — but it is explicitly not a single generic
tolerance value shared blindly across domains: each domain's default
`atol`/`rtol` pair is declared in the Wave 2 canonical-units table, and
every `ConservationCheck` result records the `atol`, `rtol`, `scale`, and
residual unit it actually used, so a caller can audit exactly what
"balanced" meant for that call. A conservation check that reports
`balanced` without also reporting these four fields is incomplete by this
ADR's definition, not merely under-documented.

`kernel.energy.metrics.energy_balance`'s existing `tolerance: float`
signature is legacy and is not rewritten to this form in 2.6.0 (ADR 0024
§4, zero-churn policy); migrating it to `atol + rtol×scale` is tracked as
residual debt for a later release that actually touches
`kernel.energy.metrics`.

## Non-goals (this release)

- A generic, engine-wide `x-oec-unit`-to-`oec.physics` auto-conversion
  layer beyond what `ExecutionService` (ADR 0016) already does — physics
  code still explicitly requests conversion via `kernel.units` when it
  needs to.
- Rewriting `oec.modeling.dimensions`'s algebra, or extending
  `infer_dimension` with new dimension kinds for this release —
  `oec.physics` consumes what already exists.
- Migrating `kernel.energy.metrics.energy_balance` to the
  `atol + rtol×scale` form — deferred, see §3 above.
- A cross-domain default tolerance table beyond the minimum P1–P4
  characteristic-unit set required for Wave 2 acceptance; expanding
  coverage to every physical quantity in the catalog is future work.

## Consequences

- Every skill built on `oec.physics` inherits the same dimensional
  guarantees the rest of OEC already relies on (ADR 0003/0011/0016) —
  there is exactly one Pint registry and one normalization boundary in the
  whole system, not two.
- Conservation results are auditable: a caller can see not just whether a
  check passed, but the exact tolerance policy and scale that produced
  that verdict, which is a precondition for trusting multi-domain
  residuals (electrical pu vs. thermal watts vs. fluid kg/s) side by side.
- A domain that has not yet had its canonical unit/tolerance defaults
  documented in the Wave 2 table cannot ship a conservation check that
  claims a default — it must either extend the table or pass an explicit
  `atol`/`rtol`/`scale`.
- Residual, not closed by this ADR: `kernel.energy.metrics.energy_balance`
  continues to use a single float `tolerance` parameter through 2.6.0;
  its migration to this policy is explicit debt, not silently implied by
  this ADR's acceptance.

## References

- `docs/implementation/v2.6-EXECUTION-PLAN.md` §0 (D5), Wave 2, §16 (DoD)
- `docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §B risk 7
- ADR 0024 (physics library architecture, conservation ownership)
- ADR 0003 (units are mandatory / `QuantityValue`)
- ADR 0011 (single shared Pint registry)
- ADR 0016 (central dimensional normalization)
- `docs/contracts/units.md`
- `src/oec/kernel/energy/metrics.py` (`energy_balance`, legacy `tolerance`)
