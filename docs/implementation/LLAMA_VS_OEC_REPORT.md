# Llama 3.1 8B vs OEC — experiment report

**Date:** 2026-07-26 17:30 UTC
**Model:** `llama3.1:8b` via Ollama (`http://127.0.0.1:11434`)
**Problem:** load = **13.7 MWh**, UFV = **6.25 MWh** (single period, η=1)
**Script:** `scripts/llama_oec_experiment.py`

---

## 1. Goal

Compare a limited local LLM solving a BESS energy-balance question:

1. **Arm A — Llama alone** (no tools, invents numbers freely).
2. **Arm B — Llama fills parameters only** into a **fixed OPS v0.1 template**;
   **OEC** runs `energy.balance`, `optimization.lp` (HiGHS), and
   `optimization.check_feasibility`.

Open Science desktop workbench was **not** used (GUI, no API from this harness).
OEC `integrations/open_science` is methodology proposals, not an LLM router.

---

## 2. Oracle (OEC ground truth)

| Metric | Value | Evidence |
|---|---|---|
| Deficit MWh | **7.449999999999999** | `energy.balance` residual = -7.449999999999999 |
| Min BESS MWh (zero grid) | **7.449999999999999** | `optimization.lp` objective |
| Feasible @ 6.0 MWh | **False** | `check_feasibility` |
| Feasible @ 7.45 MWh | **True** | `check_feasibility` |

### Provenance

```json
{
  "balance_run_id": "2a7d1044-122f-4f3c-8ebe-ca5834eaa358",
  "lp_run_id": "6bee3316-5e6b-4e75-90ca-f4d278079035",
  "lp_solver_status": "optimal",
  "lp_input_hash": "f8971e0735b6a63adb3a730b02f60848ed7fc35ad2ffb12f6e3dc17f658bfd69"
}
```

---

## 3. Arm A — Llama alone

**Score: 2/4**

| Metric | Llama | Oracle | OK |
|---|---|---|---|
| deficit_mwh | 7.45 | 7.449999999999999 | True |
| bess_min_mwh | 0 | 7.449999999999999 | False |
| feasible_6 | False | False | True |
| feasible_7_45 | False | True | False |

### Raw model output (truncated)

```text
{
  "deficit_mwh": 7.45,
  "bess_min_mwh": 0,
  "feasible_6": false,
  "feasible_7_45": false,
  "reasoning": "To balance with zero grid import, the BESS must be able to supply the deficit of 7.45 MWh. Since the max usable BESS is less than this value, it is not feasible for both cases."
}
```

### Interpretation

- Limited models often get the simple subtraction right but **hallucinate**
  BESS sizing / feasibility (inconsistent with their own deficit).
- No `run_id` / backend — answer is **not auditable** as scientific execution.

---

## 4. Arm B — Llama params + fixed OPS template + OEC

**Score: 4/4**

| Metric | Pipeline | Oracle | OK |
|---|---|---|---|
| deficit_mwh | 7.449999999999999 | 7.449999999999999 | True |
| bess_min_mwh | 7.449999999999999 | 7.449999999999999 | True |
| feasible_6 | False | False | True |
| feasible_7_45 | True | True | True |

### Parameters extracted by Llama

```json
{
  "load": 13.7,
  "ufv": 6.25
}
```

### OEC execution

```json
{
  "ok": true,
  "answer": {
    "deficit_mwh": 7.449999999999999,
    "bess_min_mwh": 7.449999999999999,
    "feasible_6": false,
    "feasible_7_45": true,
    "source": "llama_params + fixed_OPS_template + OEC",
    "lp_run_id": "ca746ede-68ae-4dfb-9d20-9a514e5b6617",
    "balance_run_id": "5453ce40-ab8f-44a4-a6c6-b691fb8e4cfd",
    "solver_status": "optimal"
  },
  "lp_run_id": "ca746ede-68ae-4dfb-9d20-9a514e5b6617",
  "balance_run_id": "5453ce40-ab8f-44a4-a6c6-b691fb8e4cfd",
  "solver_status": "optimal"
}
```

### Interpretation

- Llama is **not** trusted for the optimum: it only fills `load` / `ufv`.
- Structure of the LP is the **fixed OPS template** (schema-valid).
- Numerics come from **HiGHS** via `optimization.lp` + balance/feasibility skills.
- Provenance (`run_id`, optional `input_hash`) makes the answer **auditable**.

---

## 5. Head-to-head

| Arm | Score | Auditable? | Who owns numerics? |
|---|---|---|---|
| A Llama alone | **2/4** | No | Model weights / guessing |
| B Template + OEC | **4/4** | Yes (`run_id`) | OEC + HiGHS |

### Cheat resistance

| Failure mode | Arm A | Arm B |
|---|---|---|
| Invent BESS size | common | blocked (solver) |
| Contradict own deficit | common | impossible if OEC ran |
| Skip feasibility logic | common | `check_feasibility` |
| Fake run without OEC | easy | re-run checks hash/result |

---

## 6. Conclusions

1. Local **llama3.1:8b** can be invoked via Ollama from this repo.
2. Alone, it is **unreliable** on BESS min / feasibility even when deficit is right.
3. **Fixed OPS template + OEC** recovers the oracle when the model only extracts
   parameters — matching the product rule: *agent formulates, OEC computes*.
4. Open Science (GUI) was out of scope; use Ollama for local-model experiments.

---

## 7. Reproduce

```bash
cd <OEC repo>
ollama list   # needs llama3.1:8b
uv sync --extra optimization
uv run python scripts/llama_oec_experiment.py \
  --report docs/implementation/LLAMA_VS_OEC_REPORT.md
```

---

*End of report*
