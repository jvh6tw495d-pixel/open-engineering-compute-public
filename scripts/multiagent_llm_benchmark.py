"""Complex multi-agent OEC problem vs multiple local/cloud LLMs.

Problem: 6-period microgrid with BESS (energy balance + TOU cost min LP).
Oracle: Time-Series + Energy + Optimization + Scientific Reviewer (OEC only).

LLM arms (no tools unless noted):
  - Ollama: llama3.1:8b, nemotron-3-nano:4b, qwen2.5:7b-instruct
  - Claude CLI (if available): sonnet, opus

Usage:
  uv run python scripts/multiagent_llm_benchmark.py
  uv run python scripts/multiagent_llm_benchmark.py --skip-claude
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
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

# --- Problem data (known oracle; awkward decimals) ---
LOAD = [3.1, 2.4, 1.6, 2.15, 2.35, 2.1]  # sum 13.7
PV = [0.0, 1.45, 2.55, 1.35, 0.65, 0.25]  # sum 6.25
PRICE = [1.15, 0.55, 0.28, 0.42, 0.95, 1.35]  # TOU
T = len(LOAD)
CAP = 3.75  # BESS capacity MWh
PMAX = 1.35  # max charge/discharge per period MWh
SOC0 = 1.85  # initial SOC MWh


def _close(a: object, b: float, tol: float = 0.08) -> bool:
    try:
        return abs(float(a) - b) <= tol  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def build_multipperiod_ops() -> dict[str, Any]:
    """Min TOU grid cost with SOC dynamics (public textbook multi-period LP)."""
    variables: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    obj: dict[str, float] = {}

    for t in range(T):
        variables.append(
            {
                "name": f"g{t}",
                "kind": "continuous",
                "lower": 0,
                "upper": float(LOAD[t]),
            }
        )
        variables.append(
            {
                "name": f"c{t}",
                "kind": "continuous",
                "lower": 0,
                "upper": PMAX,
            }
        )
        variables.append(
            {
                "name": f"d{t}",
                "kind": "continuous",
                "lower": 0,
                "upper": PMAX,
            }
        )
        variables.append(
            {
                "name": f"s{t}",
                "kind": "continuous",
                "lower": 0,
                "upper": CAP,
            }
        )
        obj[f"g{t}"] = float(PRICE[t])

        # load = pv + g + d - c  =>  g + d - c = load - pv
        rhs = float(LOAD[t] - PV[t])
        constraints.append(
            {
                "name": f"bal{t}",
                "coeffs": {f"g{t}": 1.0, f"d{t}": 1.0, f"c{t}": -1.0},
                "sense": "=",
                "rhs": rhs,
            }
        )

        # SOC: s0 = SOC0 + c0 - d0
        # s_t = s_{t-1} + c_t - d_t
        if t == 0:
            # s0 - c0 + d0 = SOC0
            constraints.append(
                {
                    "name": "soc0",
                    "coeffs": {"s0": 1.0, "c0": -1.0, "d0": 1.0},
                    "sense": "=",
                    "rhs": float(SOC0),
                }
            )
        else:
            # s_t - s_{t-1} - c_t + d_t = 0
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
        "name": "microgrid_6period_bess_tou",
        "assumptions": [
            f"T={T} periods, CAP={CAP}, PMAX={PMAX}, SOC0={SOC0}",
            "eta=1, no simultaneous charge+discharge forced (linear relaxation)",
            "Public TOU cost min — not commercial BTM dispatch IP",
            f"LOAD={LOAD}",
            f"PV={PV}",
            f"PRICE={PRICE}",
        ],
        "variables": variables,
        "constraints": constraints,
        "objective": {"coeffs": obj},
    }


def oec_multiagent_oracle() -> dict[str, Any]:
    """Full multi-agent pipeline using OEC skills (deterministic harness)."""
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

    # Agent 1 — Time series: timegrid
    tg = ts.run_skill(
        "timeseries.timegrid",
        {
            "start": "2024-06-01T00:00:00",
            "end": "2024-06-01T05:00:00",
            "freq": "1h",
        },
    )

    # Agent 2 — Energy: load metrics + daily balance
    lm = energy.run_skill("energy.load_metrics", {"power_values": LOAD})
    bal = energy.run_skill(
        "energy.balance",
        {
            "energy_in": PV,
            "energy_out": LOAD,
            "storage_delta": 0.0,
        },
    )

    # Agent 3 — Optimization: multi-period LP
    ops = build_multipperiod_ops()
    opt_report = opt.execute_ops(ops)
    assert opt_report.execution is not None

    # Agent 4 — Scientific reviewer
    review = rev.review(opt_report.ops, opt_report.execution)

    # Optional describe on grid trajectory if optimal
    primal = opt_report.execution.result.get("primal") or {}
    grid = [float(primal.get(f"g{t}", 0.0)) for t in range(T)]
    charge = [float(primal.get(f"c{t}", 0.0)) for t in range(T)]
    discharge = [float(primal.get(f"d{t}", 0.0)) for t in range(T)]
    soc = [float(primal.get(f"s{t}", 0.0)) for t in range(T)]
    cost = float(opt_report.execution.result.get("objective_value") or 0.0)

    # Feasibility: capacity too small
    ops_tight = build_multipperiod_ops()
    # shrink CAP by rewriting variable uppers for s*
    for v in ops_tight["variables"]:
        if v["name"].startswith("s"):
            v["upper"] = 0.5  # impossible SOC window with SOC0=1.85
    feas = eng.run("optimization.check_feasibility", {"ops": ops_tight})

    return {
        "problem": {
            "T": T,
            "LOAD": LOAD,
            "PV": PV,
            "PRICE": PRICE,
            "CAP": CAP,
            "PMAX": PMAX,
            "SOC0": SOC0,
            "load_sum": sum(LOAD),
            "pv_sum": sum(PV),
            "deficit_no_storage": sum(LOAD) - sum(PV),
        },
        "agents": {
            "time_series": {
                "skill": "timeseries.timegrid",
                "run_id": tg.execution.run_id if tg.execution else None,
                "status": tg.execution.status.value if tg.execution else None,
                "n_points": (tg.execution.result or {}).get("n_points") if tg.execution else None,
            },
            "energy_load_metrics": {
                "skill": "energy.load_metrics",
                "run_id": lm.execution.run_id if lm.execution else None,
                "status": lm.execution.status.value if lm.execution else None,
                "result": lm.execution.result if lm.execution else None,
            },
            "energy_balance": {
                "skill": "energy.balance",
                "run_id": bal.execution.run_id if bal.execution else None,
                "status": bal.execution.status.value if bal.execution else None,
                "result": bal.execution.result if bal.execution else None,
            },
            "optimization": {
                "skill": "optimization.lp",
                "run_id": opt_report.execution.run_id,
                "status": opt_report.execution.status.value,
                "solver_status": opt_report.execution.result.get("solver_status"),
                "objective_value": cost,
                "input_hash": (opt_report.execution.provenance or {}).get("input_hash"),
            },
            "reviewer": {
                "passed": review.passed,
                "n_checks": len(review.checks),
            },
            "feasibility_impossible_cap": {
                "skill": "optimization.check_feasibility",
                "run_id": feas.run_id,
                "feasible": feas.result.get("feasible"),
                "solver_status": feas.result.get("solver_status"),
            },
        },
        "oracle_answers": {
            "load_sum_mwh": sum(LOAD),
            "pv_sum_mwh": sum(PV),
            "deficit_mwh": sum(LOAD) - sum(PV),
            "peak_load_mwh": max(LOAD),
            "load_factor": (sum(LOAD) / len(LOAD)) / max(LOAD),
            "min_tou_cost": cost,
            "grid_trajectory": grid,
            "charge_trajectory": charge,
            "discharge_trajectory": discharge,
            "soc_trajectory": soc,
            "total_grid_mwh": sum(grid),
            "total_discharge_mwh": sum(discharge),
            "total_charge_mwh": sum(charge),
            "reviewer_passed": review.passed,
            "impossible_cap_feasible": bool(feas.result.get("feasible")),
            "timegrid_n_points": (tg.execution.result or {}).get("n_points")
            if tg.execution
            else None,
        },
    }


PROBLEM_PROMPT = f"""
You are solving a multi-period microgrid + BESS problem. NO external tools.

DATA (6 periods, energy MWh per period, eta=1):
- LOAD = {LOAD}
- PV   = {PV}
- TOU price = {PRICE} (cost units per MWh grid import)
- BESS capacity CAP = {CAP} MWh
- Max charge/discharge per period PMAX = {PMAX} MWh
- Initial SOC SOC0 = {SOC0} MWh
- SOC dynamics: s[t] = s[t-1] + charge[t] - discharge[t], s[-1]=SOC0
- 0 <= s[t] <= CAP, 0 <= charge,discharge <= PMAX
- Power balance each t: LOAD[t] = PV[t] + grid[t] + discharge[t] - charge[t]
- Objective: minimize sum_t PRICE[t] * grid[t]
- grid[t] >= 0

Return ONLY JSON with keys:
  load_sum_mwh,
  pv_sum_mwh,
  deficit_mwh,          # load_sum - pv_sum
  peak_load_mwh,
  load_factor,          # mean(load)/peak
  min_tou_cost,         # optimal objective
  total_grid_mwh,       # sum optimal grid
  total_discharge_mwh,
  total_charge_mwh,
  grid_trajectory,      # list length 6
  soc_trajectory,       # list length 6 (end-of-period SOC)
  impossible_cap_feasible,  # if CAP were 0.5 MWh with SOC0={SOC0}, is problem feasible? true/false
  reasoning
No markdown fences.
"""


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
    """Call Claude Code CLI non-interactive (-p)."""
    import shutil

    claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_bin:
        raise RuntimeError("claude CLI not found on PATH")
    # Pass prompt on stdin — Windows argv length limit truncates long -p prompts.
    cmd = [
        claude_bin,
        "-p",
        "--model",
        model_alias,
        "--permission-mode",
        "plan",
        "--output-format",
        "text",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(_ROOT),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {(proc.stderr or proc.stdout)[:500]}")
    return proc.stdout


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError(f"no JSON: {text[:500]!r}") from err
        return json.loads(m.group(0))


@dataclass
class ModelRun:
    name: str
    provider: str
    ok: bool
    answer: dict[str, Any] | None = None
    raw: str = ""
    error: str = ""
    scores: dict[str, Any] = field(default_factory=dict)


def score_answer(ans: dict[str, Any] | None, oracle: dict[str, Any]) -> dict[str, Any]:
    o = oracle
    if not ans:
        return {"score": 0, "max": 10, "details": {}}

    details = {
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
        "grid_len": isinstance(ans.get("grid_trajectory"), list)
        and len(ans.get("grid_trajectory") or []) == 6,
    }
    # trajectory L1 distance bonus
    traj_ok = False
    if isinstance(ans.get("grid_trajectory"), list) and len(ans["grid_trajectory"]) == 6:
        try:
            l1 = sum(
                abs(float(ans["grid_trajectory"][i]) - o["grid_trajectory"][i]) for i in range(6)
            )
            traj_ok = l1 <= 1.0
            details["grid_traj_l1"] = l1
            details["grid_traj_ok"] = traj_ok
        except (TypeError, ValueError):
            details["grid_traj_ok"] = False
    else:
        details["grid_traj_ok"] = False

    # 9 scalar checks + trajectory
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
    score = sum(1 for k in keys if details.get(k) is True)
    return {"score": score, "max": 10, "details": details}


def run_model(name: str, provider: str) -> ModelRun:
    system = (
        "You are a careful optimization engineer. "
        "Solve rigorously. Return pure JSON only. No tools."
    )
    try:
        if provider == "ollama":
            raw = ollama_chat(name, PROBLEM_PROMPT, system=system)
        elif provider == "claude":
            raw = claude_chat(
                name,
                system + "\n\n" + PROBLEM_PROMPT,
            )
        else:
            raise ValueError(provider)
        ans = extract_json(raw)
        return ModelRun(name=name, provider=provider, ok=True, answer=ans, raw=raw)
    except Exception as exc:
        return ModelRun(
            name=name,
            provider=provider,
            ok=False,
            error=str(exc),
            raw=getattr(exc, "raw", "") if False else "",
        )


def write_report(
    path: Path,
    oracle_full: dict[str, Any],
    runs: list[ModelRun],
) -> None:
    o = oracle_full["oracle_answers"]
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# Multi-agent OEC vs multi-LLM benchmark",
        "",
        f"**Date:** {ts}",
        "**Script:** `scripts/multiagent_llm_benchmark.py`",
        "",
        "## 1. Complex problem (needs several OEC agents)",
        "",
        "6-period microgrid with BESS under time-of-use prices:",
        "",
        f"- LOAD = `{LOAD}` (sum **{sum(LOAD)}** MWh)",
        f"- PV = `{PV}` (sum **{sum(PV)}** MWh)",
        f"- PRICE = `{PRICE}`",
        f"- CAP = **{CAP}**, PMAX = **{PMAX}**, SOC0 = **{SOC0}**",
        "- Balance each period + SOC dynamics + minimize TOU grid cost",
        "",
        "### Agents / skills in the OEC oracle pipeline",
        "",
        "| Order | Agent | Skill | Role |",
        "|---|---|---|---|",
        "| 1 | Time-Series Specialist | `timeseries.timegrid` | 6h grid |",
        "| 2 | Energy Specialist | `energy.load_metrics` | peak / LF |",
        "| 3 | Energy Specialist | `energy.balance` | day residual |",
        "| 4 | Optimization Specialist | `optimization.lp` | multi-period BESS LP (HiGHS) |",
        "| 5 | Scientific Reviewer | checklist | audit OPS + ExecutionResult |",
        "| 6 | Engine | `optimization.check_feasibility` | CAP=0.5 trap |",
        "",
        "### Oracle answers (from OEC ExecutionResult only)",
        "",
        "```json",
        json.dumps(o, indent=2),
        "```",
        "",
        "### Oracle agent provenance (run_ids)",
        "",
        "```json",
        json.dumps(oracle_full["agents"], indent=2),
        "```",
        "",
        "---",
        "",
        "## 2. LLM comparison (no tools — pure generation)",
        "",
        "| Model | Provider | OK? | Score | min_cost OK | traj OK | notes |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in runs:
        sc = r.scores
        notes = r.error[:40] if r.error else ("json ok" if r.ok else "fail")
        cost_ok = sc.get("details", {}).get("min_cost")
        traj_ok = sc.get("details", {}).get("grid_traj_ok")
        lines.append(
            f"| `{r.name}` | {r.provider} | {r.ok} | "
            f"**{sc.get('score', 0)}/{sc.get('max', 10)}** | "
            f"{cost_ok} | {traj_ok} | {notes} |"
        )

    lines += [
        "",
        "### Per-model details",
        "",
    ]
    for r in runs:
        lines += [
            f"#### `{r.name}` ({r.provider})",
            "",
            f"- ok: `{r.ok}`",
            f"- score: `{r.scores}`",
            "",
            "Answer excerpt:",
            "```json",
            json.dumps(r.answer, indent=2, default=str)[:3000]
            if r.answer
            else json.dumps({"error": r.error}),
            "```",
            "",
            "Raw (truncated):",
            "```text",
            (r.raw or r.error)[:2000],
            "```",
            "",
        ]

    lines += [
        "---",
        "",
        "## 3. Why this is hard to cheat",
        "",
        "1. **Multi-period LP** — mental math fails on coupled SOC + TOU objective.",
        "2. **Awkward decimals** — not 14/7 round numbers.",
        "3. **Trap question** — `impossible_cap_feasible` with CAP=0.5 vs SOC0=1.85.",
        "4. **Trajectory** — must match HiGHS grid vector within L1≤1.0.",
        "5. **OEC oracle** has `run_id` / `input_hash` — LLM answers have neither.",
        "",
        "## 4. Conclusions",
        "",
        "- **OEC multi-agent pipeline** is ground truth (TS → Energy → Opt → Reviewer).",
        "- Local open models without tools struggle on optimal cost + trajectories.",
        "- Stronger models may match HiGHS on this instance, but still lack run_id audit.",
        "- Product rule: *agents formulate / OEC computes* remains the auditable path.",
        "",
        "## 5. Reproduce",
        "",
        "```bash",
        "ollama pull llama3.1:8b",
        "ollama pull nemotron-3-nano:4b",
        "ollama pull qwen2.5:7b-instruct",
        "uv sync --extra optimization",
        "uv run python scripts/multiagent_llm_benchmark.py --skip-claude",
        "# with Claude API configured:",
        "uv run python scripts/multiagent_llm_benchmark.py",
        "```",
        "",
        "*End of report*",
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
        default=_ROOT / "docs" / "implementation" / "MULTIAGENT_LLM_BENCHMARK.md",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=_ROOT / "docs" / "implementation" / "MULTIAGENT_LLM_BENCHMARK.json",
    )
    args = parser.parse_args()

    print("=== OEC multi-agent oracle ===")
    oracle_full = oec_multiagent_oracle()
    o = oracle_full["oracle_answers"]
    print(
        json.dumps(
            {
                "min_tou_cost": o["min_tou_cost"],
                "total_grid_mwh": o["total_grid_mwh"],
                "grid_trajectory": o["grid_trajectory"],
                "deficit_mwh": o["deficit_mwh"],
                "reviewer_passed": o["reviewer_passed"],
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
        models.extend(
            [
                ("sonnet", "claude"),
                ("opus", "claude"),
            ]
        )

    runs: list[ModelRun] = []
    for name, provider in models:
        print(f"\n=== {provider}:{name} ===")
        r = run_model(name, provider)
        r.scores = score_answer(r.answer, o)
        runs.append(r)
        print("ok", r.ok, "score", r.scores.get("score"), r.error[:120] if r.error else "")

    write_report(args.report, oracle_full, runs)
    args.json_out.write_text(
        json.dumps(
            {
                "oracle": oracle_full,
                "runs": [asdict(r) for r in runs],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print("Wrote", args.json_out)


if __name__ == "__main__":
    main()
