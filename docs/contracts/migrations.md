# Deprecations and migrations guide (v2.9 RC)

Audience: integrators moving across OEC 2.5 → 2.7 → chemistry/registry →
public 3.0. This is the plan §13 “Deprecations + migrations guide”.

## 1. Skill Engine / ExecutionResult (stable)

| Topic | Guidance |
|-------|----------|
| Canonical interface result | `ExecutionResult` remains the CLI/REST/MCP contract |
| Scientific adapter | `oec.core.scientific_result.from_execution_result` — additive |
| Breaking change policy | No silent reshape of `ExecutionResult` fields without major bump |

## 2. Energy / battery (2.6.1 → 2.6.2)

| Old concept | Current |
|-------------|---------|
| “Coulomb counting” SOC language | **Energy-based** SOC (`power × time × η / capacity`) |
| Direct `kernel.energy.metrics.soc_update` from skills | Prefer `oec.physics.storage.energy_based_soc_update` (skills thin-wrap) |
| Skill `battery.soc_step` method id | `energy_based_step` (was mislabeled coulomb) |

Parity stress: `scripts/stress_parity_v262.py` / unit parity tests must stay green
if you re-touch these adapters.

## 3. Physics vs chemistry battery models (2.8)

| Need | Use |
|------|-----|
| Pack / BESS energy SOC trajectory | `oec.physics.storage` / `battery.*` skills |
| Reversible cell open-circuit voltage | `oec.chemistry.nernst_potential` / `chemistry.nernst` skill |
| Do **not** mix | Nernst is **not** a drop-in SOC integrator |

## 4. Multiphysics (2.7)

| Topic | Guidance |
|-------|----------|
| Coupling API | `oec.physics.coupling` (weak GS only in v0) |
| Strong / implicit coupling | **Not available** — do not assume monolithic solve |
| Clock ownership | One `clock_owner` per coupled run |

## 5. Model Registry (2.9)

| Topic | Guidance |
|-------|----------|
| Discover models | `from oec.registry import default_registry` |
| Fidelity | `reduced` \| `mid` \| `high` |
| Deprecate | `registry.deprecate(id, version, replaced_by=...)` |
| Not the same as | `oec.skills.registry` (filesystem skill packages) |

Seed entrypoints may move module path; prefer registry `entrypoint` strings
and skill ids over hard-coded private paths.

## 6. Scientific IR (2.9)

| Topic | Guidance |
|-------|----------|
| Document type | `oec.modeling.scientific_ir.ScientificDocument` |
| Math IR | Still domain-agnostic (`oec.modeling.ir`); Scientific IR **references** laws/species |
| Execution | IR does not solve — compile/run via domain owners / skills |

## 7. Public tree (3.0 Option A)

| Topic | Guidance |
|-------|----------|
| Prepare | `python scripts/prepare_public_alpha.py --dest … --init-git` |
| Forbidden brands | Must be 0 hits on public tree |
| Incubation remote | Must stay empty / private |
| First public tag | `v3.0.0` on clean public history (human-only push) |

## 8. Removed / never public

- Product brands listed in `scripts/check_forbidden_names.py`
- `docs/implementation/*` incubation reports (excluded from public copy)
- Host-integration harness scripts with private machine paths
