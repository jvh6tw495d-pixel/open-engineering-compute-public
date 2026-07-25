# ADR 0013: A method declares `iterative` explicitly; convergence omission is a contract violation

- **Status:** accepted
- **Date:** 2026-07-25

## Context

`compute_status` (ADR 0007) treats `converged is None` as "an exact,
closed-form method — no convergence concept applies" and routes it
toward `ExecutionStatus.VERIFIED`. `converged` came from
`diagnostics.get("converged")`, where `diagnostics` is whatever the
skill's own implementation returned.

An independent review of Sprint 03 caught the resulting bug before any
real skill existed to trigger it: **a skill using a genuinely iterative
method (e.g. `math.solve_root`'s Brent/bisection/Newton/secant) that
simply forgets to set `diagnostics["converged"]` is indistinguishable,
from `compute_status`'s point of view, from an exact method that has no
convergence concept at all.** Both produce `converged is None`. The
buggy skill would silently receive `ExecutionStatus.VERIFIED` — the
*strongest* claim the system can make — for a result nobody actually
confirmed converged.

## Decision

`SkillManifest.method` is now a `MethodRef` (not the generic
`VersionedRef` used elsewhere), with a required `iterative: bool` field:

```yaml
method:
  id: brentq_root_finding
  version: 0.1.0
  iterative: true
```

The Execution Service reads this *before* trusting `diagnostics`:

- `iterative: false` (exact/closed-form): `converged` passed to
  `compute_status` is always `None`, regardless of what `diagnostics`
  contains. An exact method has nothing to declare here.
- `iterative: true`: `diagnostics` **must** contain a `"converged"` key.
  If it doesn't, that is treated exactly like a runner contract
  violation or a crash — `ExecutionStatus.FAILED`, with a clear message
  in `diagnostics["error_output"]` — never silently defaulted to
  `VERIFIED` or `VALIDATED`. If present, its value (coerced to `bool`)
  becomes `converged`.

No default, no inference from "the key happened to be missing." A
method that iterates has to say so about itself in `skill.yaml`, and its
implementation has to say what happened at runtime — two independent,
required declarations, not one guessed from the other's absence.

## Consequences

- `VersionedRef` (`oec.common`) stays a minimal, generic `{id, version}`
  pair — used as-is for `ExecutionResult.skill`/`.method`, which don't
  need an `iterative` flag (they're backward-pointing audit references,
  not forward-looking method contracts). Only `SkillManifest.method`
  gained the richer `MethodRef` type.
- Every `skill.yaml` written from Sprint 04 onward must declare
  `method.iterative` — there is no migration path for old manifests
  because none existed yet when this landed (the only prior skill,
  `mathematics.identity`, is a loader/registry test fixture, updated
  alongside this change).
- A skill author who copies `math.solve_root`'s template and forgets to
  update `iterative` for a different method gets a loud `FAILED` on the
  first real execution that omits `diagnostics["converged"]`, not a
  silently wrong `VERIFIED` months later.
