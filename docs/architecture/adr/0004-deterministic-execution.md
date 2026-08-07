# ADR 0004: Deterministic execution by default

- **Status:** accepted
- **Date:** 2026-07-24

## Context

OEC's central claim is that different models, agents, and clients running
the same skill with the same inputs get the same result. That claim is
false the moment a skill implementation depends on wall-clock time,
unseeded randomness, dict/set iteration order, or any other hidden source
of variance.

## Decision

Every skill is deterministic by default: given the same inputs, the same
skill version, and the same method version, repeated executions produce
identical output. `SkillManifest.execution_policy.deterministic` defaults
to `true`.

A skill that is genuinely stochastic (e.g. Monte Carlo uncertainty
propagation) must:

- declare `deterministic: false` explicitly in its manifest;
- accept an explicit `seed` (see `ExecutionRequest.seed`);
- record the seed, sample count, and sampling method used;
- report confidence intervals rather than a single point estimate.

There is no implicit default seed and no "mostly deterministic" state —
a skill is one or the other, declared up front.

## Consequences

- `ExecutionResult` is safe to use as a golden-case comparison target for
  any `deterministic: true` skill; a mismatch is a real regression, not
  noise.
- Reviewers can tell from `skill.yaml` alone whether a skill needs seed
  handling before trusting a bug report that "doesn't reproduce."
- Introducing randomness into a previously deterministic skill is a
  breaking change to its contract, not an implementation detail.
