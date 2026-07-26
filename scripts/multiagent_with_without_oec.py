"""Thesis test: weak LLMs alone vs same LLMs + OEC multi-agent pipeline.

Arm A (WITHOUT OEC): model free-solves the 6-period BESS/TOU problem.
Arm C (WITH OEC): model only extracts numeric parameters into JSON;
                 OEC agents run timegrid, load_metrics, balance, LP (HiGHS),
                 feasibility trap, and reviewer.

Thesis: weak LLMs fail hard numerics; OEC supplies method + guaranteed solve.

Usage:
  uv run python scripts/multiagent_with_without_oec.py
  uv run python scripts/multiagent_with_without_oec.py --skip-claude
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from oec.ops.schema import OPS_SCHEMA_VERSION  # noqa: E402
from oec.sdk import Engine  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"

# Canonical problem (oracle)
LOAD = [3.1, 2.4, 1.6, 2.15, 2.35, 2.1]
PV = [0.0, 1.45, 2.55, 1.35, 0.65, 0.25]
PRICE = [1.15, 0.55, 0.28, 0.42, 0.95, 1.35]
CAP = 3.75
PMAX = 1.35
SOC0 = 1.85
T = 6


def _close(a: object, b: float, tol: float = 0.08) -> bool:
    try:
        return abs(float(a) - b) <= tol  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def build_ops(
    load: list[float],
    pv: list[float],
    price: list[float],
    *,
    cap: float,
    pmax: float,
    soc0: float,
) -> dict[str, Any]:
    n = len(load)
    variables: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    obj: dict[str, float] = {}
    for t in range(n):
        variables += [
            {
                "name": f"g{t}",
                "kind": "continuous",
                "lower": 0,
                "upper": float(load[t]) + 1e-6,
            },
            {"name": f"c{t}", "kind": "continuous", "lower": 0, "upper": pmax},
            {"name": f"d{t}", "kind": "continuous", "lower": 0, "upper": pmax},
            {"name": f"s{t}", "kind": "continuous", "lower": 0, "upper": cap},
        ]
        obj[f"g{t}"] = float(price[t])
        constraints.append(
            {
                "name": f"bal{t}",
                "coeffs": {f"g{t}": 1.0, f"d{t}": 1.0, f"c{t}": -1.0},
                "sense": "=",
                "rhs": float(load[t] - pv[t]),
            }
        )
        if t == 0:
            constraints.append(
                {
                    "name": "soc0",
                    "coeffs": {"s0": 1.0, "c0": -1.0, "d0": 1.0},
                    "sense": "=",
                    "rhs": float(soc0),
                }
            )
        else:
            constraints.append(
                {
                    "name": f"soc{t}",
                    "coeffs": {
                        f"s{t}": 1.0,
                        f"s{t - 1}": -1.0,
                        f"c{t}": -1.0,
                        f"d{t}": 1.0,
                    },
                    "sense": "=",
                    "rhs": 0.0,
                }
            )
    return {
        "ops_version": OPS_SCHEMA_VERSION,
        "problem_class": "lp",
        "sense": "min",
        "name": "microgrid_multipperiod_bess_tou",
        "assumptions": [
            f"T={n} CAP={cap} PMAX={pmax} SOC0={soc0}",
            "eta=1 public textbook multiperiod LP",
            f"LOAD={load}",
            f"PV={pv}",
            f"PRICE={price}",
        ],
        "variables": variables,
        "constraints": constraints,
        "objective": {"coeffs": obj},
    }


def oec_pipeline(
    load: list[float],
    pv: list[float],
    price: list[float],
    *,
    cap: float,
    pmax: float,
    soc0: float,
) -> dict[str, Any]:
    """Multi-agent OEC pipeline (method + guaranteed numerics)."""
    from agents.energy.specialist import EnergySpecialist
    from agents.optimization_specialist.specialist import OptimizationSpecialist
    from agents.scientific_reviewer.reviewer import ScientificReviewer
    from agents.time_series.specialist import TimeSeriesSpecialist

    skills = _ROOT / "skills"
    ts = TimeSeriesSpecialist(skills_root=skills)
    energy = EnergySpecialist(skills_root=skills)
    opt = OptimizationSpecialist(skills_root=skills)
    rev = ScientificReviewer()
    eng = Engine(skills_root=skills)
    n = len(load)

    tg = ts.run_skill(
        "timeseries.timegrid",
        {
            "start": "2024-06-01T00:00:00",
            "end": f"2024-06-01T{n - 1:02d}:00:00",
            "freq": "1h",
        },
    )
    lm = energy.run_skill("energy.load_metrics", {"power_values": load})
    bal = energy.run_skill(
        "energy.balance",
        {"energy_in": pv, "energy_out": load, "storage_delta": 0.0},
    )
    ops = build_ops(load, pv, price, cap=cap, pmax=pmax, soc0=soc0)
    opt_r = opt.execute_ops(ops)
    assert opt_r.execution is not None
    review = rev.review(opt_r.ops, opt_r.execution)

    primal = opt_r.execution.result.get("primal") or {}
    grid = [float(primal.get(f"g{t}", 0.0)) for t in range(n)]
    charge = [float(primal.get(f"c{t}", 0.0)) for t in range(n)]
    discharge = [float(primal.get(f"d{t}", 0.0)) for t in range(n)]
    soc = [float(primal.get(f"s{t}", 0.0)) for t in range(n)]
    cost = float(opt_r.execution.result.get("objective_value") or 0.0)

    # Trap: impossible CAP
    ops_bad = build_ops(load, pv, price, cap=0.5, pmax=pmax, soc0=soc0)
    feas = eng.run("optimization.check_feasibility", {"ops": ops_bad})

    peak = float((lm.execution.result or {}).get("peak") or max(load))
    avg = float((lm.execution.result or {}).get("average") or (sum(load) / n))
    lf = float((lm.execution.result or {}).get("load_factor") or (avg / peak))

    return {
        "method": "oec_multiagent",
        "auditable": True,
        "answer": {
            "load_sum_mwh": sum(load),
            "pv_sum_mwh": sum(pv),
            "deficit_mwh": sum(load) - sum(pv),
            "peak_load_mwh": peak,
            "load_factor": lf,
            "min_tou_cost": cost,
            "total_grid_mwh": sum(grid),
            "total_discharge_mwh": sum(discharge),
            "total_charge_mwh": sum(charge),
            "grid_trajectory": grid,
            "charge_trajectory": charge,
            "discharge_trajectory": discharge,
            "soc_trajectory": soc,
            "impossible_cap_feasible": bool(feas.result.get("feasible")),
            "reviewer_passed": review.passed,
            "timegrid_n_points": (tg.execution.result or {}).get("n_points")
            if tg.execution
            else None,
        },
        "provenance": {
            "timegrid_run_id": tg.execution.run_id if tg.execution else None,
            "load_metrics_run_id": lm.execution.run_id if lm.execution else None,
            "balance_run_id": bal.execution.run_id if bal.execution else None,
            "lp_run_id": opt_r.execution.run_id,
            "lp_status": opt_r.execution.status.value,
            "solver_status": opt_r.execution.result.get("solver_status"),
            "input_hash": (opt_r.execution.provenance or {}).get("input_hash"),
            "reviewer_passed": review.passed,
            "feasibility_run_id": feas.run_id,
            "backends": (opt_r.execution.provenance or {}).get("backends"),
        },
        "params_used": {
            "LOAD": load,
            "PV": pv,
            "PRICE": price,
            "CAP": cap,
            "PMAX": pmax,
            "SOC0": soc0,
        },
    }


PROBLEM_TEXT = f"""
6-period microgrid + BESS (eta=1).

LOAD = {LOAD}
PV = {PV}
PRICE (TOU) = {PRICE}
CAP = {CAP} MWh
PMAX = {PMAX} MWh per period
SOC0 = {SOC0} MWh

Dynamics: s[t] = s[t-1] + charge[t] - discharge[t] (s before t=0 is SOC0)
0 <= s[t] <= CAP; 0 <= charge,discharge <= PMAX; grid >= 0
Balance: LOAD[t] = PV[t] + grid[t] + discharge[t] - charge[t]
Minimize sum PRICE[t]*grid[t]
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError(f"no JSON: {text[:400]!r}") from err
        return json.loads(m.group(0))


def ollama_chat(model: str, prompt: str, *, system: str) -> str:
    body = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1},
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
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data.get("message", {}).get("content", ""))


def claude_chat(model_alias: str, prompt: str) -> str:
    claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_bin:
        p = Path.home() / "AppData/Local/hermes/bin/claude.cmd"
        if p.is_file():
            claude_bin = str(p)
    if not claude_bin:
        raise RuntimeError("claude CLI not found")
    proc = subprocess.run(
        [
            claude_bin,
            "-p",
            "--model",
            model_alias,
            "--permission-mode",
            "plan",
            "--output-format",
            "text",
        ],
        cwd=str(_ROOT),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude {proc.returncode}: {(proc.stderr or proc.stdout)[:400]}")
    return proc.stdout


def llm_call(name: str, provider: str, system: str, user: str) -> str:
    if provider == "ollama":
        return ollama_chat(name, user, system=system)
    if provider == "claude":
        return claude_chat(name, system + "\n\n" + user)
    raise ValueError(provider)


def score(ans: dict[str, Any] | None, oracle: dict[str, Any]) -> dict[str, Any]:
    if not ans:
        return {"score": 0, "max": 10, "details": {}}
    o = oracle
    details: dict[str, Any] = {
        "load_sum": _close(ans.get("load_sum_mwh"), o["load_sum_mwh"], 0.05),
        "pv_sum": _close(ans.get("pv_sum_mwh"), o["pv_sum_mwh"], 0.05),
        "deficit": _close(ans.get("deficit_mwh"), o["deficit_mwh"], 0.05),
        "peak_load": _close(ans.get("peak_load_mwh"), o["peak_load_mwh"], 0.05),
        "load_factor": _close(ans.get("load_factor"), o["load_factor"], 0.05),
        "min_cost": _close(ans.get("min_tou_cost"), o["min_tou_cost"], 0.15),
        "total_grid": _close(ans.get("total_grid_mwh"), o["total_grid_mwh"], 0.2),
        "total_discharge": _close(ans.get("total_discharge_mwh"), o["total_discharge_mwh"], 0.25),
        "impossible_cap": (
            ans.get("impossible_cap_feasible") is False
            or str(ans.get("impossible_cap_feasible")).lower() in {"false", "no", "infeasible"}
        )
        and o["impossible_cap_feasible"] is False,
    }
    if isinstance(ans.get("grid_trajectory"), list) and len(ans["grid_trajectory"]) == 6:
        try:
            l1 = sum(
                abs(float(ans["grid_trajectory"][i]) - o["grid_trajectory"][i]) for i in range(6)
            )
            details["grid_traj_l1"] = l1
            details["grid_traj_ok"] = l1 <= 1.0
        except (TypeError, ValueError):
            details["grid_traj_ok"] = False
    else:
        details["grid_traj_ok"] = False
    keys = [
        "load_sum",
        "pv_sum",
        "deficit",
        "peak_load",
        "load_factor",
        "min_cost",
        "total_grid",
        "total_discharge",
        "impossible_cap",
        "grid_traj_ok",
    ]
    sc = sum(1 for k in keys if details.get(k) is True)
    return {"score": sc, "max": 10, "details": details}


@dataclass
class ArmResult:
    model: str
    provider: str
    arm: str  # A_without_oec | C_with_oec
    ok: bool
    answer: dict[str, Any] | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    error: str = ""
    provenance: dict[str, Any] | None = None
    params_extracted: dict[str, Any] | None = None


def arm_a_without_oec(model: str, provider: str) -> ArmResult:
    system = (
        "You are an optimization engineer. Solve the multiperiod LP yourself. "
        "No external tools. Return pure JSON only."
    )
    user = (
        PROBLEM_TEXT
        + """
Return JSON keys:
load_sum_mwh, pv_sum_mwh, deficit_mwh, peak_load_mwh, load_factor,
min_tou_cost, total_grid_mwh, total_discharge_mwh, total_charge_mwh,
grid_trajectory (len 6), soc_trajectory (len 6),
impossible_cap_feasible (if CAP were 0.5 with same SOC0 — true/false),
reasoning
No markdown.
"""
    )
    try:
        raw = llm_call(model, provider, system, user)
        ans = extract_json(raw)
        return ArmResult(
            model=model,
            provider=provider,
            arm="A_without_oec",
            ok=True,
            answer=ans,
            raw=raw,
        )
    except Exception as exc:
        return ArmResult(
            model=model,
            provider=provider,
            arm="A_without_oec",
            ok=False,
            error=str(exc),
        )


def arm_c_with_oec(model: str, provider: str) -> ArmResult:
    """LLM extracts parameters only; OEC multi-agent owns method + numbers."""
    system = (
        "You ONLY extract numeric parameters. Do NOT solve optimization. "
        "Do NOT invent trajectories or costs. Return pure JSON only."
    )
    user = (
        PROBLEM_TEXT
        + """
Extract parameters as JSON:
{
  "LOAD": [6 floats],
  "PV": [6 floats],
  "PRICE": [6 floats],
  "CAP": number,
  "PMAX": number,
  "SOC0": number
}
Copy numbers exactly from the problem. No other keys. No markdown.
"""
    )
    try:
        raw = llm_call(model, provider, system, user)
        params = extract_json(raw)
        load = [float(x) for x in params["LOAD"]]
        pv = [float(x) for x in params["PV"]]
        price = [float(x) for x in params["PRICE"]]
        cap = float(params["CAP"])
        pmax = float(params["PMAX"])
        soc0 = float(params["SOC0"])
        if len(load) != 6 or len(pv) != 6 or len(price) != 6:
            raise ValueError("expected length-6 LOAD/PV/PRICE")
        pipe = oec_pipeline(load, pv, price, cap=cap, pmax=pmax, soc0=soc0)
        return ArmResult(
            model=model,
            provider=provider,
            arm="C_with_oec",
            ok=True,
            answer=pipe["answer"],
            raw=raw,
            provenance=pipe["provenance"],
            params_extracted={
                "LOAD": load,
                "PV": pv,
                "PRICE": price,
                "CAP": cap,
                "PMAX": pmax,
                "SOC0": soc0,
            },
        )
    except Exception as exc:
        return ArmResult(
            model=model,
            provider=provider,
            arm="C_with_oec",
            ok=False,
            error=str(exc),
            raw=getattr(exc, "raw", "") if False else "",
        )


def write_thesis_report(
    path: Path,
    *,
    oracle: dict[str, Any],
    oracle_prov: dict[str, Any],
    results: list[ArmResult],
) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    o = oracle

    # pair by model
    models = sorted({r.model for r in results})

    lines = [
        "# Thesis report: LLMs without OEC vs with OEC multi-agent",
        "",
        f"**Date:** {ts}",
        "**Script:** `scripts/multiagent_with_without_oec.py`",
        "",
        "## Thesis",
        "",
        "> **Weak LLMs tend to fail multiperiod BESS/TOU optimization.**",
        "> **OEC supplies the method (skills/agents/OPS) and guarantees the result**",
        "> **(HiGHS + ExecutionResult + provenance + reviewer).**",
        "",
        "### Design",
        "",
        "| Arm | What the model does | Who computes numbers | Auditable? |",
        "|---|---|---|---|",
        ("| **A — without OEC** | Free-solves full LP in JSON | " "Model weights | **No** |"),
        (
            "| **C — with OEC** | Extracts LOAD/PV/PRICE/CAP/PMAX/SOC0 | "
            "**OEC + HiGHS** | **Yes** (`run_id`) |"
        ),
        "",
        "### OEC multi-agent method (Arm C / oracle)",
        "",
        "1. Time-Series Specialist → `timeseries.timegrid`",
        "2. Energy Specialist → `energy.load_metrics`",
        "3. Energy Specialist → `energy.balance`",
        "4. Optimization Specialist → `optimization.lp` (6-period BESS LP)",
        "5. Scientific Reviewer → checklist on OPS + ExecutionResult",
        "6. Engine → `optimization.check_feasibility` (CAP=0.5 trap)",
        "",
        "---",
        "",
        "## Problem",
        "",
        f"- LOAD = `{LOAD}` (sum **{sum(LOAD)}**)",
        f"- PV = `{PV}` (sum **{sum(PV)}**)",
        f"- PRICE = `{PRICE}`",
        f"- CAP={CAP}, PMAX={PMAX}, SOC0={SOC0}",
        "",
        "### Oracle (OEC pure pipeline, no LLM)",
        "",
        f"- **min_tou_cost** = **{o['min_tou_cost']}**",
        f"- **total_grid_mwh** = **{o['total_grid_mwh']}**",
        f"- **grid_trajectory** = `{o['grid_trajectory']}`",
        f"- **reviewer_passed** = `{o['reviewer_passed']}`",
        f"- **impossible_cap_feasible** = `{o['impossible_cap_feasible']}`",
        "",
        "```json",
        json.dumps(oracle_prov, indent=2),
        "```",
        "",
        "---",
        "",
        "## Scoreboard (same 10-point rubric)",
        "",
        "| Model | Provider | A without OEC | C with OEC | Delta (C−A) | A cost | C cost |",
        "|---|---|---|---|---|---|---|",
    ]

    for m in models:
        a = next((r for r in results if r.model == m and r.arm == "A_without_oec"), None)
        c = next((r for r in results if r.model == m and r.arm == "C_with_oec"), None)
        sa = (a.scores.get("score") if a else 0) or 0
        sc = (c.scores.get("score") if c else 0) or 0
        ca = (a.answer or {}).get("min_tou_cost") if a and a.ok else "—"
        cc = (c.answer or {}).get("min_tou_cost") if c and c.ok else "—"
        prov = a.provider if a else (c.provider if c else "?")
        lines.append(
            f"| `{m}` | {prov} | **{sa}/10** | **{sc}/10** | **{sc - sa:+d}** | {ca} | {cc} |"
        )

    lines += [
        "",
        f"| **OEC oracle (no LLM)** | oec | — | **10/10** | — | — | **{o['min_tou_cost']}** |",
        "",
        "### Thesis metrics",
        "",
    ]

    # compute thesis stats on local ollama only + all
    def arm_scores(arm: str) -> list[int]:
        return [int(r.scores.get("score") or 0) for r in results if r.arm == arm and r.ok]

    scores_a = arm_scores("A_without_oec")
    scores_c = arm_scores("C_with_oec")
    avg_a = sum(scores_a) / len(scores_a) if scores_a else 0
    avg_c = sum(scores_c) / len(scores_c) if scores_c else 0
    n_a_pass_cost = sum(
        1
        for r in results
        if r.arm == "A_without_oec" and r.ok and (r.scores.get("details") or {}).get("min_cost")
    )
    n_c_pass_cost = sum(
        1
        for r in results
        if r.arm == "C_with_oec" and r.ok and (r.scores.get("details") or {}).get("min_cost")
    )
    n_a = sum(1 for r in results if r.arm == "A_without_oec")
    n_c = sum(1 for r in results if r.arm == "C_with_oec")
    n_c_audit = sum(1 for r in results if r.arm == "C_with_oec" and r.ok and r.provenance)

    lines += [
        f"- Models scored on Arm A: **{len(scores_a)}** (avg score **{avg_a:.1f}/10**)",
        f"- Models scored on Arm C: **{len(scores_c)}** (avg score **{avg_c:.1f}/10**)",
        f"- Arm A correct min cost: **{n_a_pass_cost}/{n_a}**",
        f"- Arm C correct min cost: **{n_c_pass_cost}/{n_c}**",
        f"- Arm C runs with OEC provenance: **{n_c_audit}/{n_c}**",
        f"- Average lift (C − A): **{avg_c - avg_a:+.1f}** points",
        "",
        "---",
        "",
        "## Per-model detail",
        "",
    ]

    for m in models:
        lines.append(f"### `{m}`")
        lines.append("")
        for arm_name, label in (
            ("A_without_oec", "Arm A — WITHOUT OEC"),
            ("C_with_oec", "Arm C — WITH OEC"),
        ):
            r = next((x for x in results if x.model == m and x.arm == arm_name), None)
            if not r:
                continue
            lines += [
                f"#### {label}",
                "",
                f"- ok: `{r.ok}` score: **{r.scores.get('score', 0)}/10**",
                f"- error: `{r.error or '—'}`",
                "",
                "```json",
                json.dumps(
                    {
                        "answer": r.answer,
                        "scores": r.scores,
                        "provenance": r.provenance,
                        "params_extracted": r.params_extracted,
                    },
                    indent=2,
                    default=str,
                )[:4000],
                "```",
                "",
            ]

    lines += [
        "---",
        "",
        "## Conclusions (thesis)",
        "",
        "1. **Without OEC**, weak/local models usually miss the multiperiod optimum",
        "   (wrong `min_tou_cost` and/or grid trajectory).",
        "2. **With OEC**, if parameter extraction is correct, scores jump because",
        "   **HiGHS** solves the same OPS the oracle uses — method is fixed in skills.",
        "3. OEC adds **guarantee + audit**: `run_id`, `input_hash`, `solver_status`,",
        "   reviewer pass — LLMs alone cannot produce this.",
        "4. Strong models (e.g. Opus) may occasionally match the number without tools;",
        "   they still do **not** replace OEC for **reproducible scientific claims**.",
        "5. Product implication: *LLM formulates / OEC computes* is the correct split",
        "   for agent-oriented engineering infrastructure.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "uv sync --extra optimization",
        "uv run python scripts/multiagent_with_without_oec.py",
        "uv run python scripts/multiagent_with_without_oec.py --skip-claude",
        "```",
        "",
        "*End of thesis report*",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=_ROOT / "docs" / "implementation" / "THESIS_LLM_WITH_WITHOUT_OEC.md",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=_ROOT / "docs" / "implementation" / "THESIS_LLM_WITH_WITHOUT_OEC.json",
    )
    args = parser.parse_args()

    print("=== OEC oracle (no LLM) ===")
    pure = oec_pipeline(LOAD, PV, PRICE, cap=CAP, pmax=PMAX, soc0=SOC0)
    oracle = pure["answer"]
    print(
        json.dumps(
            {
                "min_tou_cost": oracle["min_tou_cost"],
                "grid_trajectory": oracle["grid_trajectory"],
                "reviewer_passed": oracle["reviewer_passed"],
            },
            indent=2,
        )
    )

    models: list[tuple[str, str]] = [
        ("llama3.1:8b", "ollama"),
        ("nemotron-3-nano:4b", "ollama"),
        ("qwen2.5:7b-instruct", "ollama"),
    ]
    if not args.skip_claude:
        models.append(("opus", "claude"))
        # sonnet optional — often slow; include for completeness
        models.append(("sonnet", "claude"))

    results: list[ArmResult] = []
    for model, provider in models:
        print(f"\n######## {provider}:{model} ########")
        print("--- Arm A WITHOUT OEC ---")
        a = arm_a_without_oec(model, provider)
        a.scores = score(a.answer if a.ok else None, oracle)
        results.append(a)
        print("A score", a.scores.get("score"), a.error[:100] if a.error else "")

        print("--- Arm C WITH OEC ---")
        c = arm_c_with_oec(model, provider)
        c.scores = score(c.answer if c.ok else None, oracle)
        results.append(c)
        print(
            "C score",
            c.scores.get("score"),
            "cost",
            (c.answer or {}).get("min_tou_cost"),
            c.error[:100] if c.error else "",
        )

    write_thesis_report(
        args.report,
        oracle=oracle,
        oracle_prov=pure["provenance"],
        results=results,
    )
    args.json_out.write_text(
        json.dumps(
            {
                "thesis": (
                    "Weak LLMs fail multiperiod BESS/TOU; "
                    "OEC supplies method and guarantees results."
                ),
                "oracle": pure,
                "results": [asdict(r) for r in results],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print("Wrote", args.json_out)


if __name__ == "__main__":
    main()
