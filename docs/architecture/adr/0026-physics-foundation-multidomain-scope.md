# ADR 0026: Physics Foundation multidomain scope for v2.6 (P1–P5 v0, DC power flow canon, energy-rich deferral)

- **Status:** Draft — Wave 0; accept on Wave 6
- **Date:** 2026-08-03
- **Phase:** v2.6.0 "Physics Foundation P1–P5 v0", Wave 0 (`docs/implementation/
  v2.6-EXECUTION-PLAN.md`, decisions D1, D4, D6, D7)

## Context

`OEC_V3_IMPLEMENTATION_PLAN.md` §10 names "Physics Complete" as a roadmap
milestone covering `oec.physics` plus the P1–P5 domain slices (electrical,
thermal, mechanics, fluids, materials) and the four domain objects
(ADR 0024). An earlier v2.6 draft narrowed this to an "energy-first" scope
(PV/BESS/hybrid/grid-zero) instead — a divergence from V3 §10 that the
Codex audit (`docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §B risks 2,
3, 8, 9) flagged alongside two further gaps: P1 was left as "DC power flow
or radial branch-flow" without a single fixed contract, and the release's
implied claim ("Physics Complete") was stronger than what its own smoke
plan (two slices) or timeline (V3 estimates 12–20+ weeks for the full
industrial milestone) could support.

This ADR restores V3 §10's multidomain scope for 2.6.0 and fixes the
specific ambiguities the audit raised, so the release can be planned and
gated against a single, unambiguous contract rather than a moving target.

## Decision

### 1. Claim: "Physics Foundation P1–P5 v0", not "Physics Complete"

The publishable claim for 2.6.0 is **Physics Foundation P1–P5 v0**
(catalog synonym: "Engineering Physics Foundation"). V3 §10's "Physics
Complete" name continues to describe the long-run roadmap milestone; it is
not used bare in the 2.6.0 CHANGELOG or release notes without the
foundation/v0 qualifier. The distinction matters because "Physics Complete"
unqualified implies a depth (optics, acoustics, fields, quantum — none of
which are in scope) this release does not deliver; "Foundation v0" states
accurately what is: a working platform plus P1–P5 at v0 depth.

### 2. Scope: platform + domain objects + P1–P5 v0, energy-rich excluded

2.6.0 delivers the `oec.physics` package (ADR 0024), the four domain
objects, and five slices at v0 depth, mapped from V3 §10 as follows:

| Slice | Domain | v0 delivery this release |
|-------|--------|---------------------------|
| **P1** | Advanced electrical | `dc_power_flow` (see §3); optional light harmonics/THD (see §5); layered on top of the existing classic electrical skills, not a rewrite of them |
| **P2** | Thermal | 1D conduction (Fourier); sensible heat capacity |
| **P3** | Mechanics (particle/1D) | kinematics (constant-velocity/constant-acceleration); kinetic/potential energy, work |
| **P4** | Fluids (0D/1D) | Bernoulli + friction losses (Darcy-Weisbach) with the friction factor `f` as a **known input** — Reynolds number, the Colebrook equation, and flow-regime classification are explicitly future extensions, not this release |
| **P5** | Materials | property lookup tables + a v0 uniaxial linear material law (Hooke) — **not** a structural/elastic solver; general structural analysis is future work |

Energy-rich functionality — storage/BESS trajectories, a generic
feature-rich PV model, multi-period hybrid dispatch, grid-zero, and
service-metrics/EaaS — is explicitly **not** part of 2.6.0. It is deferred
to `v2.6.1-EXECUTION-PLAN.md` in full, including any skill or agent
surface for it; `kernel/energy/metrics.py` and the existing `energy.*`/
`battery.soc_step` skills stay exactly as they are in 2.6.0 and are picked
up by the 2.6.1 program. Pressure to fold energy-rich work back into
2.6.0 "because it's related" is a stop condition (v2.6 plan §14), not a
scope judgment call available mid-wave.

### 3. P1 canonical model: DC linear power flow, meshed topology

P1's canonical deliverable is **DC linear power flow on a meshed
topology** (`oec.physics.electrical.dc_power_flow`, skill
`electrical.dc_power_flow`) — not "DC or radial branch-flow." DC and
radial-branch-flow are different models with different inputs, hypotheses,
and correctness oracles; leaving the choice open until implementation time
would mean freezing an API around whichever one got written first, rather
than a deliberate decision. The contract is fixed here, before Wave 3's
implementation and locked at the Wave 1 API/type level:

| Aspect | Fixed contract |
|--------|----------------|
| Inputs | line topology (from/to); line susceptance `B_ij` (or reactance `X_ij` with `B = 1/X` documented); active power injections `P_i` per bus; slack/reference bus |
| Outputs | bus angles θ (relative to slack); line flows `P_ij`; per-node balance residual; a `balanced` flag |
| Hypotheses | linear network; resistive losses neglected (classic DC model); `|V| ≈ 1` pu flat; active power only; steady state; connected graph |
| Oracles | KCL: per-node injection + flow residual ≈ 0 (tolerance per ADR 0025); sum of injections ≈ 0 (lossless DC model); determinism (ADR 0004) |
| Out of scope for P1 v0 | AC power flow; optimal power flow/dispatch (routed to the Optimization Specialist + `optimization.lp`, never reimplemented as physics); rotating machines; sequence components; radial branch-flow as a *substitute* for this canonical model (it remains available as a future, separate extension) |

GATE-W3 checks adherence to this contract; it does not reopen DC-vs-radial.

### 4. Explicit non-goals held constant through the release

The following stay out of 2.6.0 regardless of remaining schedule, and
pulling any of them in without a new ADR/re-gate is a stop condition
(v2.6 plan §14, §17):

- Multiphysics coupling / co-simulation (V3 §11) — v2.7, which needs a
  coupling-readiness contract this release does not define.
- Electrochemistry / cell chemistry, species transport (V3 chemistry
  milestone) — v2.8+.
- AC power flow, rotating machines, power-quality analysis beyond optional
  v0 THD.
- A structural/elasticity solver (P5 stays uniaxial-constitutive-only).
- Reynolds number / Colebrook / flow-regime classification for P4 (friction
  factor stays an input in v0).
- A unified Model Registry / Scientific IR (v2.9).
- Rewriting the six classic `electrical.*` skills.

### 5. THD/harmonics: genuinely optional, never a P1 blocker

The minimum P1 gate is exactly one skill: `electrical.dc_power_flow`
(§3). Light harmonics/THD (`oec.physics.harmonics`,
`electrical.harmonics_thd`) may be added after that first P1 slice is
complete and merged, if the schedule allows it in Waves 3–4; if it does
not land, that is recorded as residual debt, not a release blocker and not
a NO-GO at any gate. This keeps the mandatory P1 surface small and
deliberately avoids the earlier plan's mistake of implying THD was part of
the P1 core.

### 6. Gates: end-to-end integration across P1–P4, not a two-slice smoke

The release's Definition of Done raises the acceptance bar from an earlier
"smoke covering two slices" to: at least one skill per slice for **P1, P2,
P3, and P4**, each declaring conservation, units, and hypotheses in its
contract; zero imports of private decision engines anywhere in the physics
surface; and Wave 5 smoke that exercises the full skill→engine→envelope
path **for every one of P1–P4** (not a sampled subset), each with a
domain-specific correctness oracle (P1: DC power-flow residual; P2/P3/P4:
their own domain oracles). P5 ships its module and at least one skill or a
tested, documented public API consumed by another slice; an
`authoritative_answer` smoke path for P5 is recommended but not gate-
blocking if P5 only exposes a tested API. This is the standard V3 §10 gate
(≥1 skill per P1–P4 slice, zero private engines) made explicit and
elevated to end-to-end, closing the audit's "claim exceeds gates" finding.

## Non-goals (this release)

See §4 above for the explicit, held-constant exclusions; in addition:
- Curated per-domain `authoritative_answer.values` subsets — values stay
  `execution.result` verbatim (ADR 0023, unchanged by this release).
- Any REST/SDK/CLI surface for the envelope (ADR 0023 non-goal, D-CUR-27) —
  physics results reach hosts through the same MCP agent-tool path as
  everything else normalized by ADR 0023.
- Packaging `agents/` under `src/oec/agents` (D-CUR-21) — unrelated to
  physics scope, tracked separately.

## Consequences

- The release claim matches what Wave 5 smoke actually proves: correct
  `authoritative_answer` numbers across P1–P4, end to end, not a subset
  dressed up as the full V3 §10 milestone.
- P1 has one implementation to build against from Wave 1 onward — no
  mid-implementation rework from discovering DC and radial models diverge
  in oracle or input shape.
- Energy-rich work (2.6.1) can proceed on a stable `oec.physics` and
  `kernel.energy` foundation without racing 2.6.0's own scope, and without
  re-litigating conservation ownership (ADR 0024 §4, inherited unchanged).
- P4 and P5's explicit v0 boundaries (friction factor as input; uniaxial
  constitutive law only) mean neither slice silently grows into a
  full CFD or structural-solver claim this release does not make.
- Residual, not closed by this ADR: whether THD lands in 2.6.0 or slips
  to debt is a schedule outcome, not decided here; whether P1's canonical
  DC model gets a radial-branch-flow companion is future, separately
  ADR'd work.

## References

- `docs/implementation/v2.6-EXECUTION-PLAN.md` §0 (D1, D4, D6, D7), Wave 3
  §7, Wave 4 §8, Wave 5 §9, §16 (DoD), §17 (out of scope)
- `docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §B risks 2, 3, 8, 9
- `docs/implementation/PHYSICS-CATALOG.md`
- ADR 0024 (physics library architecture, layering, conservation ownership)
- ADR 0025 (units and dimensional API, tolerance policy)
- ADR 0016 (classic electrical skills, dimensional normalization)
- `OEC_V3_IMPLEMENTATION_PLAN.md` §10 (Physics Complete roadmap milestone),
  §11 (Multiphysics)
