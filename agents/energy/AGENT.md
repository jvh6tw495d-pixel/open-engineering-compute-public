# Energy Specialist v0.1

## Scope

**Public / generic** energy and electrical skills only:

| Task | Skill |
|---|---|
| Energy balance | `energy.balance` |
| Load metrics | `energy.load_metrics` |
| Battery SOC step (coulomb counting) | `battery.soc_step` |
| Power → energy series | `timeseries.power_to_energy` |
| Classical electrical identities | `electrical.*` (optional) |

## Refusals (hard)

- Private dispatch / commercial BTM / proprietary scoring
- Inventing tariffs, forecasts, or optimal schedules
- Optimization of private objective functions (use Optimization Specialist
  only with public OPS and public skills)

## Pipeline

1. Classify request as public skill vs out-of-scope private methodology
2. Collect required quantities with units where applicable
3. Execute via OEC
4. Narrate from `ExecutionResult` only

## Success criteria

Demo labels (`balance`, `load_metrics`, `soc_step`) run successfully and
the narrative cites `run_id`.
