# Multi-agent OEC vs multi-LLM benchmark

**Date:** 2026-07-26 17:55 UTC
**Script:** `scripts/multiagent_llm_benchmark.py`

## 1. Complex problem (needs several OEC agents)

6-period microgrid with BESS under time-of-use prices:

- LOAD = `[3.1, 2.4, 1.6, 2.15, 2.35, 2.1]` (sum **13.7** MWh)
- PV = `[0.0, 1.45, 2.55, 1.35, 0.65, 0.25]` (sum **6.25** MWh)
- PRICE = `[1.15, 0.55, 0.28, 0.42, 0.95, 1.35]`
- CAP = **3.75**, PMAX = **1.35**, SOC0 = **1.85**
- Balance each period + SOC dynamics + minimize TOU grid cost

### Agents / skills in the OEC oracle pipeline

| Order | Agent | Skill | Role |
|---|---|---|---|
| 1 | Time-Series Specialist | `timeseries.timegrid` | 6h grid |
| 2 | Energy Specialist | `energy.load_metrics` | peak / LF |
| 3 | Energy Specialist | `energy.balance` | day residual |
| 4 | Optimization Specialist | `optimization.lp` | multi-period BESS LP (HiGHS) |
| 5 | Scientific Reviewer | checklist | audit OPS + ExecutionResult |
| 6 | Engine | `optimization.check_feasibility` | CAP=0.5 trap |

### Oracle answers (from OEC ExecutionResult only)

```json
{
  "load_sum_mwh": 13.7,
  "pv_sum_mwh": 6.25,
  "deficit_mwh": 7.449999999999999,
  "peak_load_mwh": 3.1,
  "load_factor": 0.7365591397849461,
  "min_tou_cost": 4.2825,
  "grid_trajectory": [
    1.75,
    0.44999999999999996,
    0.40000000000000036,
    2.15,
    0.3500000000000001,
    0.5
  ],
  "charge_trajectory": [
    0.0,
    0.0,
    1.35,
    1.35,
    0.0,
    0.0
  ],
  "discharge_trajectory": [
    1.35,
    0.5,
    0.0,
    0.0,
    1.35,
    1.35
  ],
  "soc_trajectory": [
    0.5,
    -0.0,
    1.35,
    2.7,
    1.35,
    0.0
  ],
  "total_grid_mwh": 5.6000000000000005,
  "total_discharge_mwh": 4.550000000000001,
  "total_charge_mwh": 2.7,
  "reviewer_passed": true,
  "impossible_cap_feasible": false,
  "timegrid_n_points": 6
}
```

### Oracle agent provenance (run_ids)

```json
{
  "time_series": {
    "skill": "timeseries.timegrid",
    "run_id": "b7665d9c-11c9-41b7-9a59-6f82fbb1d0af",
    "status": "VERIFIED",
    "n_points": 6
  },
  "energy_load_metrics": {
    "skill": "energy.load_metrics",
    "run_id": "d8946594-4997-4185-8b44-674fd3b8b658",
    "status": "VERIFIED",
    "result": {
      "n": 6,
      "peak": 3.1,
      "average": 2.283333333333333,
      "load_factor": 0.7365591397849461,
      "min": 1.6
    }
  },
  "energy_balance": {
    "skill": "energy.balance",
    "run_id": "9cb88b9e-c3f9-4c7b-84e6-11382de46234",
    "status": "VERIFIED",
    "result": {
      "total_in": 6.25,
      "total_out": 13.7,
      "storage_delta": 0.0,
      "residual": -7.449999999999999,
      "balanced": false,
      "tolerance": 1e-06
    }
  },
  "optimization": {
    "skill": "optimization.lp",
    "run_id": "b323198c-07b5-4f9c-802b-7d46d930f4de",
    "status": "VALIDATED",
    "solver_status": "optimal",
    "objective_value": 4.2825,
    "input_hash": "e1074558459b6ec917619a4c4588ea930ada9205a6f720fdf53d5c5e7900c218"
  },
  "reviewer": {
    "passed": true,
    "n_checks": 10
  },
  "feasibility_impossible_cap": {
    "skill": "optimization.check_feasibility",
    "run_id": "966a9036-70af-41c8-9e81-dfe62b89e1e4",
    "feasible": false,
    "solver_status": "infeasible"
  }
}
```

---

## 2. LLM comparison (no tools — pure generation)

| Model | Provider | OK? | Score | min_cost OK | traj OK | notes |
|---|---|---|---|---|---|---|
| `llama3.1:8b` | ollama | True | **3/10** | False | False | json ok |
| `nemotron-3-nano:4b` | ollama | True | **4/10** | False | False | json ok |
| `qwen2.5:7b-instruct` | ollama | True | **2/10** | False | False | json ok |
| `sonnet` | claude | False | **0/10** | None | None | Command '['C:\\Users\\joaop\\AppData\\Lo |
| `opus` | claude | True | **10/10** | True | True | json ok |

### Per-model details

#### `llama3.1:8b` (ollama)

- ok: `True`
- score: `{'score': 3, 'max': 10, 'details': {'load_sum': False, 'pv_sum': True, 'deficit': False, 'peak_load': True, 'load_factor': False, 'min_cost': False, 'total_grid': False, 'total_discharge': False, 'impossible_cap': True, 'grid_len': True, 'grid_traj_l1': 4.0, 'grid_traj_ok': False}}`

Answer excerpt:
```json
{
  "load_sum_mwh": 12.55,
  "pv_sum_mwh": 6.2,
  "deficit_mwh": 6.35,
  "peak_load_mwh": 3.1,
  "load_factor": 0.202,
  "min_tou_cost": 4.73,
  "total_grid_mwh": 8.55,
  "total_discharge_mwh": 2.85,
  "total_charge_mwh": 5.7,
  "grid_trajectory": [
    1.15,
    0.55,
    0.28,
    0.42,
    0.95,
    1.35
  ],
  "soc_trajectory": [
    1.85,
    3.4,
    2.75,
    2.17,
    1.52,
    1.32
  ],
  "impossible_cap_feasible": false,
  "reasoning": "The problem is feasible for the given capacity of 3.75 MWh and initial SOC of 1.85 MWh."
}
```

Raw (truncated):
```text
{
    "load_sum_mwh": 12.55,
    "pv_sum_mwh": 6.2,
    "deficit_mwh": 6.35,
    "peak_load_mwh": 3.1,
    "load_factor": 0.202,
    "min_tou_cost": 4.73,
    "total_grid_mwh": 8.55,
    "total_discharge_mwh": 2.85,
    "total_charge_mwh": 5.7,
    "grid_trajectory": [1.15, 0.55, 0.28, 0.42, 0.95, 1.35],
    "soc_trajectory": [1.85, 3.4, 2.75, 2.17, 1.52, 1.32],
    "impossible_cap_feasible": false,
    "reasoning": "The problem is feasible for the given capacity of 3.75 MWh and initial SOC of 1.85 MWh."
}
```

#### `nemotron-3-nano:4b` (ollama)

- ok: `True`
- score: `{'score': 4, 'max': 10, 'details': {'load_sum': True, 'pv_sum': True, 'deficit': False, 'peak_load': False, 'load_factor': True, 'min_cost': False, 'total_grid': True, 'total_discharge': False, 'impossible_cap': False, 'grid_len': True, 'grid_traj_l1': 5.180000000000001, 'grid_traj_ok': False}}`

Answer excerpt:
```json
{
  "load_sum_mwh": 13.7,
  "pv_sum_mwh": 6.25,
  "deficit_ mwh": 7.45,
  "peak_load_ mwh": 3.1,
  "load_factor": 0.7365,
  "min_tou_cost": 6.316,
  "total_grid_mwh": 5.68,
  "total_discharge_mwh": 2.72,
  "total_charge_mwh": 0.95,
  "grid_trajectory": [
    1.75,
    0.45,
    0,
    0,
    1.63,
    1.85
  ],
  "soc_trajectory": [
    0.5,
    0,
    0.95,
    0.07,
    0,
    0
  ],
  "impossible_feasible": false,
  "reasoning": "The BESS can supply up to its capacity and max discharge limits; grid usage minimized by using BESS where possible. With CAP=3.75 MWh and SOC0=1.85 MWh the problem is feasible. If CAP were reduced to 0.5 MWh while SOC0 remains 1.85, the SOC would exceed capacity, making it infeasible."
}
```

Raw (truncated):
```text
{
  "load_sum_mwh": 13.7,
  "pv_sum_mwh": 6.25,
  "deficit_ mwh": 7.45,
  "peak_load_ mwh": 3.1,
  "load_factor": 0.7365,
  "min_tou_cost": 6.316,
  "total_grid_mwh": 5.68,
  "total_discharge_mwh": 2.72,
  "total_charge_mwh": 0.95,
  "grid_trajectory": [1.75, 0.45, 0, 0, 1.63, 1.85],
  "soc_trajectory": [0.5, 0, 0.95, 0.07, 0, 0],
  "impossible_feasible": false,
  "reasoning": "The BESS can supply up to its capacity and max discharge limits; grid usage minimized by using BESS where possible. With CAP=3.75 MWh and SOC0=1.85 MWh the problem is feasible. If CAP were reduced to 0.5 MWh while SOC0 remains 1.85, the SOC would exceed capacity, making it infeasible."
}
```

#### `qwen2.5:7b-instruct` (ollama)

- ok: `True`
- score: `{'score': 2, 'max': 10, 'details': {'load_sum': False, 'pv_sum': False, 'deficit': False, 'peak_load': True, 'load_factor': False, 'min_cost': False, 'total_grid': False, 'total_discharge': False, 'impossible_cap': True, 'grid_len': True, 'grid_traj_l1': 6.199999999999999, 'grid_traj_ok': False}}`

Answer excerpt:
```json
{
  "load_sum_mwh": 13.4,
  "pv_sum_mwh": 7.25,
  "deficit_mwh": 6.15,
  "peak_load_mwh": 3.1,
  "load_factor": 0.4355,
  "min_tou_cost": 3.985,
  "total_grid_mwh": 7.25,
  "total_discharge_mwh": 6.15,
  "total_charge_mwh": 5.4,
  "grid_trajectory": [
    0,
    0.55,
    1.35,
    0.8,
    1.7,
    1.2
  ],
  "soc_trajectory": [
    1.85,
    2.6,
    2.95,
    2.2,
    2.45,
    2.1
  ],
  "impossible_cap_feasible": false,
  "reasoning": "With a BESS capacity of only 0.5 MWh and an initial SOC of 1.85 MWh, the problem is infeasible as there isn't enough storage to handle the peak load without violating constraints."
}
```

Raw (truncated):
```text
{
  "load_sum_mwh": 13.4,
  "pv_sum_mwh": 7.25,
  "deficit_mwh": 6.15,
  "peak_load_mwh": 3.1,
  "load_factor": 0.4355,
  "min_tou_cost": 3.985,
  "total_grid_mwh": 7.25,
  "total_discharge_mwh": 6.15,
  "total_charge_mwh": 5.4,
  "grid_trajectory": [0, 0.55, 1.35, 0.8, 1.7, 1.2],
  "soc_trajectory": [1.85, 2.6, 2.95, 2.2, 2.45, 2.1],
  "impossible_cap_feasible": false,
  "reasoning": "With a BESS capacity of only 0.5 MWh and an initial SOC of 1.85 MWh, the problem is infeasible as there isn't enough storage to handle the peak load without violating constraints."
}
```

#### `sonnet` (claude)

- ok: `False`
- score: `{'score': 0, 'max': 10, 'details': {}}`

Answer excerpt:
```json
{"error": "Command '['C:\\\\Users\\\\joaop\\\\AppData\\\\Local\\\\claude-cli\\\\bin\\\\claude.CMD', '-p', '--model', 'sonnet', '--permission-mode', 'plan', '--output-format', 'text']' timed out after 600 seconds"}
```

Raw (truncated):
```text
Command '['C:\\Users\\joaop\\AppData\\Local\\claude-cli\\bin\\claude.CMD', '-p', '--model', 'sonnet', '--permission-mode', 'plan', '--output-format', 'text']' timed out after 600 seconds
```

#### `opus` (claude)

- ok: `True`
- score: `{'score': 10, 'max': 10, 'details': {'load_sum': True, 'pv_sum': True, 'deficit': True, 'peak_load': True, 'load_factor': True, 'min_cost': True, 'total_grid': True, 'total_discharge': True, 'impossible_cap': True, 'grid_len': True, 'grid_traj_l1': 4.996003610813204e-16, 'grid_traj_ok': True}}`

Answer excerpt:
```json
{
  "load_sum_mwh": 13.7,
  "pv_sum_mwh": 6.25,
  "deficit_mwh": 7.45,
  "peak_load_mwh": 3.1,
  "load_factor": 0.7365591397849462,
  "min_tou_cost": 4.2825,
  "total_grid_mwh": 5.6,
  "total_discharge_mwh": 4.55,
  "total_charge_mwh": 2.7,
  "grid_trajectory": [
    1.75,
    0.45,
    0.4,
    2.15,
    0.35,
    0.5
  ],
  "soc_trajectory": [
    0.5,
    0.0,
    1.35,
    2.7,
    1.35,
    0.0
  ],
  "impossible_cap_feasible": false,
  "reasoning": "Reformulated the LP by substituting grid[t]=net[t]+b[t] where net=LOAD-PV=[3.1,0.95,-0.95,0.80,1.70,1.85] and b[t]=charge[t]-discharge[t]. Objective becomes minimize sum(PRICE*b) plus a constant. Expressing via end-of-period SOC s (s[-1]=1.85), the objective is separable linear J=0.60*s0+0.27*s1-0.14*s2-0.53*s3-0.40*s4+1.35*s5 (const dropped), so we want s0,s1,s5 small and s2,s3,s4 large. Box/step constraints: b in [-1.35,1.35], grid>=0 forces b>=-net (notably b2>=0.95 since PV surplus 0.95 must be stored, and discharge caps b1>=-0.95, b3>=-0.80), and 0<=s<=3.75. Optimal vertex: discharge full 1.35 at t0 (price 1.15) drawing down initial SOC, discharge 0.50 more at t1 (SOC floor-limited), charge 1.35 at cheap t2 (0.28, absorbing free PV) and 1.35 at t3 (0.42) to reach s3=2.70, then discharge full 1.35 at both t4 (0.95) and t5 (1.35), the two highest late-price periods, ending empty. SOC=[0.50,0,1.35,2.70,1.35,0]; grid=[1.75,0.45,0.40,2.15,0.35,0.50]. All power balances and bounds verified; grid_sum=deficit+charge-discharge=7.45+2.70-4.55=5.60. Cost=1.15*1.75+0.55*0.45+0.28*0.40+0.42*2.15+0.95*0.35+1.35*0.50=4.2825. Each binding constraint checked\u2014no feasible direction lowers J, so this is the global optimum. For CAP=0.5 with SOC0=1.85: the initial SOC 1.85 already exceeds the 0.5 cap, and even ignoring that, the forced charge b2>=0.95 at t2 pushes SOC above 0.5, so the problem is infeasible."
}
```

Raw (truncated):
```text
{"load_sum_mwh": 13.7, "pv_sum_mwh": 6.25, "deficit_mwh": 7.45, "peak_load_mwh": 3.1, "load_factor": 0.7365591397849462, "min_tou_cost": 4.2825, "total_grid_mwh": 5.6, "total_discharge_mwh": 4.55, "total_charge_mwh": 2.7, "grid_trajectory": [1.75, 0.45, 0.4, 2.15, 0.35, 0.5], "soc_trajectory": [0.5, 0.0, 1.35, 2.7, 1.35, 0.0], "impossible_cap_feasible": false, "reasoning": "Reformulated the LP by substituting grid[t]=net[t]+b[t] where net=LOAD-PV=[3.1,0.95,-0.95,0.80,1.70,1.85] and b[t]=charge[t]-discharge[t]. Objective becomes minimize sum(PRICE*b) plus a constant. Expressing via end-of-period SOC s (s[-1]=1.85), the objective is separable linear J=0.60*s0+0.27*s1-0.14*s2-0.53*s3-0.40*s4+1.35*s5 (const dropped), so we want s0,s1,s5 small and s2,s3,s4 large. Box/step constraints: b in [-1.35,1.35], grid>=0 forces b>=-net (notably b2>=0.95 since PV surplus 0.95 must be stored, and discharge caps b1>=-0.95, b3>=-0.80), and 0<=s<=3.75. Optimal vertex: discharge full 1.35 at t0 (price 1.15) drawing down initial SOC, discharge 0.50 more at t1 (SOC floor-limited), charge 1.35 at cheap t2 (0.28, absorbing free PV) and 1.35 at t3 (0.42) to reach s3=2.70, then discharge full 1.35 at both t4 (0.95) and t5 (1.35), the two highest late-price periods, ending empty. SOC=[0.50,0,1.35,2.70,1.35,0]; grid=[1.75,0.45,0.40,2.15,0.35,0.50]. All power balances and bounds verified; grid_sum=deficit+charge-discharge=7.45+2.70-4.55=5.60. Cost=1.15*1.75+0.55*0.45+0.28*0.40+0.42*2.15+0.95*0.35+1.35*0.50=4.2825. Each binding constraint checked—no feasible direction lowers J, so this is the global optimum. For CAP=0.5 with SOC0=1.85: the initial SOC 1.85 already exceeds the 0.5 cap, and even ignoring that, the forced charge b2>=0.95 at t2 pushes SOC above 0.5, so the problem is infeasible."}

```

---

## 3. Why this is hard to cheat

1. **Multi-period LP** — mental math fails on coupled SOC + TOU objective.
2. **Awkward decimals** — not 14/7 round numbers.
3. **Trap question** — `impossible_cap_feasible` with CAP=0.5 vs SOC0=1.85.
4. **Trajectory** — must match HiGHS grid vector within L1≤1.0.
5. **OEC oracle** has `run_id` / `input_hash` — LLM answers have neither.

## 4. Conclusions (this run)

| System | Score /10 | min_tou_cost | Notes |
|---|---|---|---|
| **OEC multi-agent (oracle)** | **10** | **4.2825** | HiGHS + run_ids + reviewer pass |
| **Claude Opus** | **10** | **4.2825** | Matched oracle without tools; **no** OEC provenance |
| llama3.1:8b | 3 | 4.73 | Weak trajectory / cost |
| nemotron-3-nano:4b | 4 | 6.316 | Weak optimum |
| qwen2.5:7b-instruct | 2 | 3.985 | Underestimated cost |
| Claude Sonnet | 0 | — | CLI timeout (600s) this run |

- OEC remains the **auditable** ground truth (`run_id`, `input_hash`, backends).
- Opus can solve this LP-scale problem “in head” — still cannot replace OEC for **reproducible** claims unless it calls OEC.
- Local models fail the hard parts (cost + grid trajectory + trap feasibility).

## 5. Reproduce

```bash
ollama pull llama3.1:8b
ollama pull nemotron-3-nano:4b
ollama pull qwen2.5:7b-instruct
uv sync --extra optimization
uv run python scripts/multiagent_llm_benchmark.py --skip-claude
# with Claude API configured:
uv run python scripts/multiagent_llm_benchmark.py
```

*End of report*
