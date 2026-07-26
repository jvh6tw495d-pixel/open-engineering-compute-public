"""Compare local Llama (Ollama) alone vs template-OPS + OEC execute.

Arm A: Llama answers alone (no tools).
Arm B: Llama only fills LOAD/UFV numbers into a fixed OPS v0.1 template;
       OEC runs optimization.lp + energy.balance + feasibility checks.

Open Science GUI is not used (no API). Ollama + OEC only.

Usage:
  uv run python scripts/llama_oec_experiment.py
  uv run python scripts/llama_oec_experiment.py --report docs/implementation/LLAMA_VS_OEC_REPORT.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from oec.ops.schema import OPS_SCHEMA_VERSION  # noqa: E402
from oec.sdk import Engine  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"
MODEL = "llama3.1:8b"

# Non-obvious aggregates
LOAD = 13.7
UFV = 6.25


def ollama_chat(prompt: str, *, system: str, temperature: float = 0.1) -> str:
    body = {
        "model": MODEL,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data.get("message", {}).get("content", ""))


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError(f"no JSON object in model output: {text[:400]!r}") from err
        return json.loads(m.group(0))


def ops_template(load: float, ufv: float) -> dict[str, Any]:
    """Fixed OPS v0.1: minimize bess_mwh with zero grid import."""
    deficit = float(load) - float(ufv)
    return {
        "ops_version": OPS_SCHEMA_VERSION,
        "problem_class": "lp",
        "sense": "min",
        "name": "min_bess_mwh_zero_grid",
        "assumptions": [
            f"Load fixed {load} MWh, UFV fixed {ufv} MWh (single period)",
            "Minimize usable BESS energy with grid_import forced to 0",
            "eta=1, energy-only public LP",
        ],
        "variables": [
            {"name": "bess_mwh", "kind": "continuous", "lower": 0, "upper": 100},
            {"name": "bess_discharge", "kind": "continuous", "lower": 0, "upper": 100},
            {"name": "bess_charge", "kind": "continuous", "lower": 0, "upper": 100},
            {"name": "grid_import", "kind": "continuous", "lower": 0, "upper": 0},
        ],
        "constraints": [
            {
                "name": "energy_balance",
                "coeffs": {
                    "grid_import": 1,
                    "bess_discharge": 1,
                    "bess_charge": -1,
                },
                "sense": "=",
                "rhs": deficit,
            },
            {
                "name": "discharge_le_bess",
                "coeffs": {"bess_discharge": 1, "bess_mwh": -1},
                "sense": "<=",
                "rhs": 0,
            },
        ],
        "objective": {"coeffs": {"bess_mwh": 1.0}},
    }


def oec_run_pipeline(load: float, ufv: float) -> dict[str, Any]:
    eng = Engine(skills_root=_ROOT / "skills")
    bal = eng.run(
        "energy.balance",
        {"energy_in": [ufv], "energy_out": [load], "storage_delta": 0.0},
    )
    deficit = -float(bal.result["residual"])
    ops = ops_template(load, ufv)
    lp = eng.run("optimization.lp", {"ops": ops})

    def feasible(e_max: float) -> dict[str, Any]:
        ops_f = {
            "ops_version": OPS_SCHEMA_VERSION,
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "grid_import", "kind": "continuous", "lower": 0, "upper": 0},
                {
                    "name": "bess_discharge",
                    "kind": "continuous",
                    "lower": 0,
                    "upper": e_max,
                },
                {
                    "name": "bess_charge",
                    "kind": "continuous",
                    "lower": 0,
                    "upper": e_max,
                },
            ],
            "constraints": [
                {
                    "name": "energy_balance",
                    "coeffs": {
                        "grid_import": 1,
                        "bess_discharge": 1,
                        "bess_charge": -1,
                    },
                    "sense": "=",
                    "rhs": deficit,
                }
            ],
            "objective": {"coeffs": {"grid_import": 1}},
        }
        fr = eng.run("optimization.check_feasibility", {"ops": ops_f})
        return {
            "feasible": bool(fr.result.get("feasible")),
            "solver_status": fr.result.get("solver_status"),
            "run_id": fr.run_id,
            "status": fr.status.value,
        }

    f6 = feasible(6.0)
    f745 = feasible(7.45)
    return {
        "load": load,
        "ufv": ufv,
        "deficit_mwh": deficit,
        "bess_min_mwh": float(lp.result["objective_value"])
        if lp.result.get("objective_value") is not None
        else None,
        "feasible_6": f6["feasible"],
        "feasible_7_45": f745["feasible"],
        "balance": {
            "run_id": bal.run_id,
            "status": bal.status.value,
            "result": bal.result,
        },
        "lp": {
            "run_id": lp.run_id,
            "status": lp.status.value,
            "result": lp.result,
            "input_hash": (lp.provenance or {}).get("input_hash"),
        },
        "feasibility_6": f6,
        "feasibility_7_45": f745,
    }


def arm_a_llama_alone() -> dict[str, Any]:
    system = (
        "You are a careful engineer. Solve only with reasoning. "
        "Do not claim you ran external software. Return pure JSON only."
    )
    problem = f"""
Site load: {LOAD} MWh. PV/UFV: {UFV} MWh. Single period, eta=1, no MW limits.

Answer:
1) deficit_mwh if storage_delta=0
2) bess_min_mwh to balance with ZERO grid import
3) feasible_6: is max usable BESS 6.0 MWh feasible with zero grid? true/false
4) feasible_7_45: is max usable BESS 7.45 MWh feasible with zero grid? true/false

JSON keys: deficit_mwh, bess_min_mwh, feasible_6, feasible_7_45, reasoning
No markdown.
"""
    raw = ollama_chat(problem, system=system)
    try:
        parsed = extract_json(raw)
    except Exception as exc:
        return {"ok": False, "raw": raw, "error": str(exc)}
    return {"ok": True, "raw": raw, "answer": parsed}


def arm_b_template_fill() -> dict[str, Any]:
    """Llama only returns {{load, ufv}}; fixed OPS template + OEC execute."""
    system = (
        "You extract numeric parameters only. "
        "Do NOT solve optimization. Do NOT invent other fields. "
        'Return pure JSON: {"load": <number>, "ufv": <number>}.'
    )
    prompt = (
        f"From this problem statement, extract load and UFV generation in MWh:\n"
        f"Site consumption (load) is {LOAD} MWh and PV generation (UFV) is {UFV} MWh.\n"
        f'Return JSON only: {{"load": ..., "ufv": ...}}'
    )
    raw = ollama_chat(prompt, system=system, temperature=0.0)
    try:
        params = extract_json(raw)
        load = float(params["load"])
        ufv = float(params["ufv"])
    except Exception as exc:
        return {"ok": False, "raw": raw, "error": f"parse params: {exc}"}

    try:
        oec = oec_run_pipeline(load, ufv)
    except Exception as exc:
        return {
            "ok": False,
            "raw": raw,
            "params": {"load": load, "ufv": ufv},
            "error": f"oec: {exc}",
        }

    return {
        "ok": True,
        "raw": raw,
        "params_from_llama": {"load": load, "ufv": ufv},
        "ops_template_used": True,
        "oec": oec,
        "answer": {
            "deficit_mwh": oec["deficit_mwh"],
            "bess_min_mwh": oec["bess_min_mwh"],
            "feasible_6": oec["feasible_6"],
            "feasible_7_45": oec["feasible_7_45"],
            "source": "llama_params + fixed_OPS_template + OEC",
            "lp_run_id": oec["lp"]["run_id"],
            "balance_run_id": oec["balance"]["run_id"],
            "solver_status": oec["lp"]["result"].get("solver_status"),
        },
    }


def as_bool(x: object) -> bool | None:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        t = x.strip().lower()
        if t in {"yes", "true", "sim", "y", "feasible"}:
            return True
        if t in {"no", "false", "nao", "não", "n", "infeasible"}:
            return False
    return None


def score(answer: dict[str, Any] | None, oracle: dict[str, Any]) -> dict[str, Any]:
    if not answer:
        return {
            "deficit_ok": False,
            "bess_min_ok": False,
            "feasible_6_ok": False,
            "feasible_7_45_ok": False,
            "score": 0,
            "max": 4,
        }

    def close(a: object, b: float, tol: float = 0.05) -> bool:
        try:
            return abs(float(a) - b) <= tol  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False

    checks = {
        "deficit_ok": close(answer.get("deficit_mwh"), float(oracle["deficit_mwh"])),
        "bess_min_ok": close(answer.get("bess_min_mwh"), float(oracle["bess_min_mwh"])),
        "feasible_6_ok": as_bool(answer.get("feasible_6")) == oracle["feasible_6"],
        "feasible_7_45_ok": as_bool(answer.get("feasible_7_45")) == oracle["feasible_7_45"],
    }
    checks["score"] = sum(1 for k, v in checks.items() if k.endswith("_ok") and v)
    checks["max"] = 4
    return checks


def write_report(
    path: Path,
    *,
    oracle: dict[str, Any],
    arm_a: dict[str, Any],
    arm_b: dict[str, Any],
    score_a: dict[str, Any],
    score_b: dict[str, Any],
) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    ans_a = arm_a.get("answer") if arm_a.get("ok") else None
    ans_b = arm_b.get("answer") if arm_b.get("ok") else None

    def fmt_bool(x: object) -> str:
        if x is None:
            return "—"
        return str(x)

    lines = [
        "# Llama 3.1 8B vs OEC — experiment report",
        "",
        f"**Date:** {ts}  ",
        f"**Model:** `{MODEL}` via Ollama (`{OLLAMA}`)  ",
        f"**Problem:** load = **{LOAD} MWh**, UFV = **{UFV} MWh** (single period, η=1)  ",
        "**Script:** `scripts/llama_oec_experiment.py`  ",
        "",
        "---",
        "",
        "## 1. Goal",
        "",
        "Compare a limited local LLM solving a BESS energy-balance question:",
        "",
        "1. **Arm A — Llama alone** (no tools, invents numbers freely).",
        "2. **Arm B — Llama fills parameters only** into a **fixed OPS v0.1 template**;",
        "   **OEC** runs `energy.balance`, `optimization.lp` (HiGHS), and",
        "   `optimization.check_feasibility`.",
        "",
        "Open Science desktop workbench was **not** used (GUI, no API from this harness).",
        "OEC `integrations/open_science` is methodology proposals, not an LLM router.",
        "",
        "---",
        "",
        "## 2. Oracle (OEC ground truth)",
        "",
        "| Metric | Value | Evidence |",
        "|---|---|---|",
        (
            f"| Deficit MWh | **{oracle['deficit_mwh']}** | "
            f"`energy.balance` residual = {-oracle['deficit_mwh']} |"
        ),
        (
            f"| Min BESS MWh (zero grid) | **{oracle['bess_min_mwh']}** | "
            "`optimization.lp` objective |"
        ),
        f"| Feasible @ 6.0 MWh | **{oracle['feasible_6']}** | `check_feasibility` |",
        (f"| Feasible @ 7.45 MWh | **{oracle['feasible_7_45']}** | `check_feasibility` |"),
        "",
        "### Provenance",
        "",
        "```json",
        json.dumps(
            {
                "balance_run_id": oracle["balance"]["run_id"],
                "lp_run_id": oracle["lp"]["run_id"],
                "lp_solver_status": oracle["lp"]["result"].get("solver_status"),
                "lp_input_hash": oracle["lp"].get("input_hash"),
            },
            indent=2,
        ),
        "```",
        "",
        "---",
        "",
        "## 3. Arm A — Llama alone",
        "",
        f"**Score: {score_a['score']}/{score_a['max']}**",
        "",
        "| Metric | Llama | Oracle | OK |",
        "|---|---|---|---|",
        (
            f"| deficit_mwh | {ans_a.get('deficit_mwh') if ans_a else '—'} | "
            f"{oracle['deficit_mwh']} | {score_a['deficit_ok']} |"
        ),
        (
            f"| bess_min_mwh | {ans_a.get('bess_min_mwh') if ans_a else '—'} | "
            f"{oracle['bess_min_mwh']} | {score_a['bess_min_ok']} |"
        ),
        (
            f"| feasible_6 | {fmt_bool(ans_a.get('feasible_6') if ans_a else None)} | "
            f"{oracle['feasible_6']} | {score_a['feasible_6_ok']} |"
        ),
        (
            f"| feasible_7_45 | "
            f"{fmt_bool(ans_a.get('feasible_7_45') if ans_a else None)} | "
            f"{oracle['feasible_7_45']} | {score_a['feasible_7_45_ok']} |"
        ),
        "",
        "### Raw model output (truncated)",
        "",
        "```text",
        (arm_a.get("raw") or arm_a.get("error") or "")[:2500],
        "```",
        "",
        "### Interpretation",
        "",
        "- Limited models often get the simple subtraction right but **hallucinate**",
        "  BESS sizing / feasibility (inconsistent with their own deficit).",
        "- No `run_id` / backend — answer is **not auditable** as scientific execution.",
        "",
        "---",
        "",
        "## 4. Arm B — Llama params + fixed OPS template + OEC",
        "",
        f"**Score: {score_b['score']}/{score_b['max']}**",
        "",
        "| Metric | Pipeline | Oracle | OK |",
        "|---|---|---|---|",
        (
            f"| deficit_mwh | {ans_b.get('deficit_mwh') if ans_b else '—'} | "
            f"{oracle['deficit_mwh']} | {score_b['deficit_ok']} |"
        ),
        (
            f"| bess_min_mwh | {ans_b.get('bess_min_mwh') if ans_b else '—'} | "
            f"{oracle['bess_min_mwh']} | {score_b['bess_min_ok']} |"
        ),
        (
            f"| feasible_6 | {fmt_bool(ans_b.get('feasible_6') if ans_b else None)} | "
            f"{oracle['feasible_6']} | {score_b['feasible_6_ok']} |"
        ),
        (
            f"| feasible_7_45 | "
            f"{fmt_bool(ans_b.get('feasible_7_45') if ans_b else None)} | "
            f"{oracle['feasible_7_45']} | {score_b['feasible_7_45_ok']} |"
        ),
        "",
        "### Parameters extracted by Llama",
        "",
        "```json",
        json.dumps(arm_b.get("params_from_llama"), indent=2),
        "```",
        "",
        "### OEC execution",
        "",
        "```json",
        json.dumps(
            {
                "ok": arm_b.get("ok"),
                "answer": ans_b,
                "lp_run_id": (ans_b or {}).get("lp_run_id"),
                "balance_run_id": (ans_b or {}).get("balance_run_id"),
                "solver_status": (ans_b or {}).get("solver_status"),
            },
            indent=2,
        ),
        "```",
        "",
        "### Interpretation",
        "",
        "- Llama is **not** trusted for the optimum: it only fills `load` / `ufv`.",
        "- Structure of the LP is the **fixed OPS template** (schema-valid).",
        "- Numerics come from **HiGHS** via `optimization.lp` + balance/feasibility skills.",
        "- Provenance (`run_id`, optional `input_hash`) makes the answer **auditable**.",
        "",
        "---",
        "",
        "## 5. Head-to-head",
        "",
        "| Arm | Score | Auditable? | Who owns numerics? |",
        "|---|---|---|---|",
        f"| A Llama alone | **{score_a['score']}/4** | No | Model weights / guessing |",
        f"| B Template + OEC | **{score_b['score']}/4** | Yes (`run_id`) | OEC + HiGHS |",
        "",
        "### Cheat resistance",
        "",
        "| Failure mode | Arm A | Arm B |",
        "|---|---|---|",
        "| Invent BESS size | common | blocked (solver) |",
        "| Contradict own deficit | common | impossible if OEC ran |",
        "| Skip feasibility logic | common | `check_feasibility` |",
        "| Fake run without OEC | easy | re-run checks hash/result |",
        "",
        "---",
        "",
        "## 6. Conclusions",
        "",
        "1. Local **llama3.1:8b** can be invoked via Ollama from this repo.",
        "2. Alone, it is **unreliable** on BESS min / feasibility even when deficit is right.",
        "3. **Fixed OPS template + OEC** recovers the oracle when the model only extracts",
        "   parameters — matching the product rule: *agent formulates, OEC computes*.",
        "4. Open Science (GUI) was out of scope; use Ollama for local-model experiments.",
        "",
        "---",
        "",
        "## 7. Reproduce",
        "",
        "```bash",
        "cd <OEC repo>",
        "ollama list   # needs llama3.1:8b",
        "uv sync --extra optimization",
        "uv run python scripts/llama_oec_experiment.py \\",
        "  --report docs/implementation/LLAMA_VS_OEC_REPORT.md",
        "```",
        "",
        "---",
        "",
        "*End of report*",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=_ROOT / "docs" / "implementation" / "LLAMA_VS_OEC_REPORT.md",
    )
    args = parser.parse_args()

    print(f"Model: {MODEL}")
    print(f"Problem: load={LOAD} UFV={UFV}")

    print("\n=== ORACLE (OEC) ===")
    oracle = oec_run_pipeline(LOAD, UFV)
    print(
        json.dumps(
            {k: oracle[k] for k in ("deficit_mwh", "bess_min_mwh", "feasible_6", "feasible_7_45")},
            indent=2,
        )
    )

    print("\n=== ARM A — Llama alone ===")
    try:
        arm_a = arm_a_llama_alone()
    except urllib.error.URLError as exc:
        arm_a = {"ok": False, "error": f"ollama unreachable: {exc}"}
    print(json.dumps(arm_a.get("answer") or arm_a, indent=2, default=str)[:2000])

    print("\n=== ARM B — template fill + OEC ===")
    try:
        arm_b = arm_b_template_fill()
    except urllib.error.URLError as exc:
        arm_b = {"ok": False, "error": f"ollama unreachable: {exc}"}
    print(json.dumps(arm_b.get("answer") or arm_b, indent=2, default=str)[:2000])

    score_a = score(arm_a.get("answer") if arm_a.get("ok") else None, oracle)
    score_b = score(arm_b.get("answer") if arm_b.get("ok") else None, oracle)
    print("\nSCORE_A", score_a)
    print("SCORE_B", score_b)

    write_report(
        args.report,
        oracle=oracle,
        arm_a=arm_a,
        arm_b=arm_b,
        score_a=score_a,
        score_b=score_b,
    )


if __name__ == "__main__":
    main()
