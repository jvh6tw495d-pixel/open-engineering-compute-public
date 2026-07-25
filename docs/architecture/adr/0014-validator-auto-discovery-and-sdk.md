# ADR 0014: Validator auto-discovery, the `oec` SDK facade, and `oec run`'s exit codes

- **Status:** accepted
- **Date:** 2026-07-25

## Context

Since Sprint 03, `ExecutionService` has never assembled a skill's
validators itself — every caller (so far, only `tests/integration/
test_*_end_to_end.py`) hand-builds `ExecutionService(registry,
input_validators=[SchemaValidator(), <SkillSpecificValidator>()],
result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()])`
and must already know, out of band, which skill-specific validator class
to import. This was a deliberate deferral (see `docs/development/
codebase-map.md`'s "Decisions", every sprint from 03 through 05): three,
then six, skills weren't enough evidence to freeze the right convention.

Sprint 06 needs a real `oec run <skill_id>` CLI command and a public
Python SDK, both of which must execute *any* registered skill without
the caller knowing in advance which validator classes that skill needs.
`ExecutionService` itself binds one fixed validator list at construction
time (unchanged by this ADR — it stays a small, already-well-tested
class); something above it has to build the *right* list per skill.

Two problems get solved together here because they share the same
surface: (1) how a skill's own validator gets discovered, and (2) how a
caller who doesn't want to think about `ExecutionService`/`SkillRegistry`
at all gets a one-call way to run a skill.

Also folded in: an independent review of Sprint 05 (Opus) found that
`NumericalDiagnosticsValidator`'s key names (`iterations`/
`max_iterations`/`residual`/`tolerance`/`condition_number`, all read from
`diagnostics`) match **zero** of the six shipped skills' actual
diagnostics shapes (`n_iterations`/`n_function_evaluations`/`abs_error`/
`residuals`, and `max_iterations`/`tolerance` are caller *inputs*, never
echoed into `diagnostics`) — `CONVERGED_WITH_WARNINGS` has been
practically unreachable since Sprint 03. Wiring validators automatically
is exactly the moment to fix this, since it's the same file being
touched either way.

## Decision

### 1. `build_validators(skill) -> (input_validators, result_validators)`

New `src/oec/execution/factory.py`, `build_validators(skill: LoadedSkill)
-> tuple[list[InputValidator], list[ResultValidator]]`, reading
`skill.manifest.validation` (`ValidationPolicy`):

| Policy flag | Wiring |
|---|---|
| `schema` (default `true`) | shared `SchemaValidator()` |
| `dimensional` | shared `DimensionalValidator()` (already pipeline-wired since Sprint 02, just never included by any caller yet) |
| `mathematical` | the skill's **own** `validation.py` validator class, discovered by introspection (see below) |
| `physical` | **no shared validator wired** — see "physical stays documentation-only" below |
| `numerical` | shared `NumericalDiagnosticsValidator()` (result validator, now fixed — see part 3) |
| *(not policy-gated)* | `InvariantValidator()` (result validator) is **always** included — it's a structural guarantee (no NaN/Inf, output-schema shape), not an optional layer a skill can opt out of |

**Skill-validator discovery convention**: `build_validators` calls
`oec.testing.load_skill_module(skill.path, "validation")` (the same
public loader every skill's own test suite already uses) and scans
`vars(module)` for a class that (a) is defined *in that module* (not
imported — filters out `LoadedSkill`, `ExpressionError`, etc. that every
`validation.py` imports), and (b) declares a `layer` `ClassVar` and a
callable `validate` attribute (duck-typing the `InputValidator` protocol
— `Protocol` classes aren't `isinstance`-checkable without
`@runtime_checkable`, which the frozen `oec.validation.base` protocols
deliberately don't use, so structural inspection is the only option).
The first (and, by convention, only) matching class is instantiated
no-arg. If a skill declares `mathematical: true` but has no
`validation.py`, or the module has no matching class, this is a
`SkillEntrypointError` — a loud failure at registry/discovery time, not
a silently-skipped validator.

No skill's `validation.py` needed a single line changed for this — every
one of the six already exposes exactly one `*Validator` class with a
`layer` `ClassVar`, because that was already the template `solve_root`
established in Sprint 04. This ADR freezes that existing shape as the
actual contract, rather than requiring a new explicit registration
point (e.g. a module-level `VALIDATOR = ...` constant) that would have
meant touching all six skills for no functional gain.

### 2. `physical` stays documentation-only (explicit, not silent)

`oec.validation.physical` is (and remains, after this ADR) a set of pure
helper functions (`require_positive`, `require_probability`,
`require_above_absolute_zero`), not a pipeline-wired validator class —
unlike `dimensional`, which already has `DimensionalValidator`. A skill
that needs physical-limit checks calls these helpers from its own
`validation.py`, exactly the same pattern `oec.validation.mathematical`
already uses for cross-field math checks (see every skill's
`validation.py` so far). `physical: true` in a manifest is therefore
informational — it documents that the skill's own validator layer
includes physical checks, not a separate pipeline stage
`build_validators` wires in. This mirrors reality: no skill built through
Sprint 05 needed a *shared, skill-independent* physical check the way
`DimensionalValidator`'s `x-oec-unit` mechanism is skill-independent.
Revisit if a future skill needs physical checks that aren't naturally
scoped to one skill's own `validation.py`.

### 3. Fix `NumericalDiagnosticsValidator`'s dead key names

`src/oec/validation/numerical.py` now reads:

- **iterations**: `diagnostics.get("iterations")` or
  `diagnostics.get("n_iterations")` (first present).
- **max_iterations**: `normalized_inputs.get("max_iterations")` — this
  was the actual bug: every skill that accepts `max_iterations` takes it
  as a *caller input*, never echoes it into `diagnostics`, so reading it
  from `diagnostics` could never fire. `normalized_inputs` was already a
  parameter of `ResultValidator.validate` and simply wasn't being read.
- **residual**: `diagnostics.get("residual")`, `diagnostics.get("abs_error")`
  (`mathematics.integrate`'s name for the same concept), or — new —
  `max(abs(r) for r in diagnostics["residuals"])` when `diagnostics`
  has a `residuals` list (`mathematics.curve_fit`) instead of one scalar.
- **tolerance**: `normalized_inputs.get("tolerance")` or
  `diagnostics.get("tolerance")` (`integrate` echoes it into
  diagnostics; most skills only take it as input).
- **condition_number**: unchanged (`diagnostics.get("condition_number")`)
  — no shipped skill reports this yet; left as a forward-looking check
  for a future linear-algebra skill, not removed.

This is a **behavior fix to an existing validator**, not a new one — the
warning-tier `CONVERGED_WITH_WARNINGS` status becomes reachable for the
first time in this framework's history once a real skill call runs
close to its iteration limit or tolerance. No skill's `diagnostics`
shape changes; `NumericalDiagnosticsValidator` now actually reads what's
already there (plus `normalized_inputs`, which it always had access to
and never used for `max_iterations`/`tolerance`).

### 4. `oec` SDK facade — per-skill `ExecutionService`, not one shared instance

`ExecutionService` binds one validator list for its whole lifetime by
design (Sprint 03) — appropriate when a caller executes one known skill
repeatedly, wrong for a CLI/SDK that must run *any* registered skill.
Rather than change `ExecutionService`'s frozen, already-well-tested
constructor contract, a new facade owns *one `ExecutionService` per
skill id+version*, built lazily via `build_validators` and cached:

```python
# src/oec/sdk.py
class Engine:
    def __init__(self, skills_root: str | Path = "skills") -> None: ...
    def run(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        *,
        skill_version: str | None = None,
        seed: int | None = None,
        trace_id: str | None = None,
        requested_by: str | None = None,
    ) -> ExecutionResult: ...


def run(
    skill_id: str, inputs: dict[str, Any], *, skills_root: str | Path = "skills", **kwargs
) -> ExecutionResult:
    """One-shot convenience: builds a throwaway Engine and calls .run()."""
```

`Engine` wraps a `SkillRegistry` (built once, via `register_all`) and a
`dict[tuple[str, str], ExecutionService]` cache keyed by
`(skill_id, resolved_version)`. This is the "import direto em
Python/testes" surface deferred from Sprint 03 (`docs/sprints/
sprint-03-execution-validation.md`) — distinct from `oec.testing`, which
stays a test-authoring helper (`load_skill_module`, `write_skill_dir`),
not a runtime execution facade.

### 5. `oec run`'s exit codes

`oec run <skill_id>` maps `ExecutionResult.status` to a process exit
code, since a CLI's caller (a script, CI, another process) needs to
branch on success/failure without parsing output:

| Exit code | `ExecutionStatus` | Meaning |
|---|---|---|
| `0` | `VERIFIED`, `VALIDATED`, `CONVERGED_WITH_WARNINGS`, `APPROXIMATE` | Usable result — `APPROXIMATE`/`CONVERGED_WITH_WARNINGS` still exit `0` because the result is trustworthy-with-caveats, not a failure; the caveats are in the printed output, not the exit code. |
| `2` | `INCONCLUSIVE` | Ran, but the result cannot be trusted — distinct from a hard failure. |
| `3` | `INVALID` | Caller error (bad input) — distinct from `FAILED` so scripts can retry-with-different-input vs. treat-as-a-bug differently. |
| `4` | `FAILED` | Implementation crashed, timed out, or violated the convergence-reporting contract. |
| `1` | *(not a status)* | CLI-level error before/outside `ExecutionResult` — skill not found, malformed `--input` JSON, `--skills-root` doesn't exist. |

Exit code `1` is reserved for "the CLI itself couldn't even try" (mirrors
the general Unix convention of `1` for a generic/uncategorized failure),
kept distinct from every `ExecutionStatus`-derived code so a caller can
tell "your skill id was wrong" apart from "the skill ran and said
`INVALID`".

## Consequences

- Every `tests/integration/test_*_end_to_end.py`'s `_service()` helper
  becomes `build_validators(skill)` plus `ExecutionService(registry,
  input_validators=..., result_validators=...)` — same runtime behavior,
  proven by keeping those tests green after the refactor (they're the
  regression guard that auto-discovery reproduces the hand-wired
  behavior exactly).
- A future skill's `validation.py` must still expose exactly one class
  matching the discovery shape (`layer` + `validate`, defined in that
  module) if it declares `mathematical: true` — this was already true
  by convention; it is now enforced (a missing/ambiguous validator is a
  loud error, not silently no-validator).
- `oec.Engine` doing per-skill `ExecutionService` caching means a
  long-lived `Engine` (e.g. inside `oec run`'s process, or a future REST
  server in Sprint 07) builds each skill's validator set once, not once
  per call — the registry itself is also built once, not re-scanned per
  `run()`.
- `physical: true` remaining documentation-only is an explicit, narrow
  gap (not a silent one): if a future skill needs a *shared*
  cross-skill physical check, that is the trigger to add a
  `PhysicalValidator` class and revisit this ADR, not to invent one now
  without a real skill driving its shape.
