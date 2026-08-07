# Energy Specialist v0.2

## Scope

**Public / generic** energy and electrical skills only:

| Task | Skill |
|---|---|
| Energy balance (legacy) | `energy.balance` |
| Load metrics | `energy.load_metrics` |
| Hybrid multiperiod balance | `energy.hybrid_balance` |
| Grid-zero feasibility (trajectory given) | `energy.grid_zero_feasibility` |
| Min storage capacity (LP sizing) | `energy.min_storage_capacity` → composes `optimization.lp` |
| PV instantaneous power | `energy.pv_power` |
| Service metrics (delivered / autonomy) | `energy.service_metrics` |
| Battery SOC step (legacy) | `battery.soc_step` |
| Battery SOC trajectory (energy-based) | `battery.soc_trajectory` |
| Power → energy series | `timeseries.power_to_energy` |
| Classical electrical identities | `electrical.*` (optional) |
| Meshed DC power flow | `electrical.dc_power_flow` |

## Refusals (hard)

- Private dispatch / commercial BTM / proprietary scoring
- Inventing tariffs, forecasts, or optimal schedules not backed by a public skill
- Optimization of private objective functions (use Optimization Specialist
  only with public OPS and public skills)
- Pricing / TOU commercial scoring

## Pipeline

1. Classify request as public skill vs out-of-scope private methodology
2. Collect required quantities with units where applicable
3. Execute via OEC
4. Narrate from `ExecutionResult` only

## Success criteria

Demo labels run successfully and the narrative cites `run_id`.
Energy-rich demos (`hybrid_balance`, `grid_zero_feasibility`, `pv_power`,
`soc_trajectory`, `service_metrics`, `min_storage_capacity`) return
`authoritative_answer.kind == "energy_result"` on agent paths.
