# ruff: noqa: E501

"""Harder 12-period BESS/TOU LP benchmark across multiple LLM providers.

STALE vs 2.5.3 (Wave 3b inventory decision): this harness calls `Engine.run(...)`
directly (see the two `Engine(skills_root=...)` construction sites below) and
never crosses the `oec.mcp.server.call_tool` boundary, so it predates and
bypasses the v2.5.3 `authoritative_answer` envelope / `claimed_answer` /
divergence contract entirely (see `docs/contracts/authoritative-answer.md`).
Its scores are direct-skill scrapes, not authority-backed, and it does not
participate in the GATE-W3 three-verdict classification
(`scripts/_oec_authority.py`). Migrating it would mean rewriting every call
site to go through `agent.*` MCP tools the way
`multiagent_with_without_oec.py::oec_pipeline_envelope` does -- out of scope
for a migrate-min pass. Kept for its harder-LP historical coverage; do not
treat its scores as an authority-backed 2.5.3 stability signal.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from oec.ops.schema import OPS_SCHEMA_VERSION  # noqa: E402
from oec.sdk import Engine  # noqa: E402

HERMES_CONFIG = Path(
    os.environ.get("HERMES_CONFIG_PATH", r"C:\Users\joaop\AppData\Local\hermes\config.yaml")
)
HERMES_ENV = Path(os.environ.get("HERMES_ENV_PATH", r"C:\Users\joaop\AppData\Local\hermes\.env"))
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", r"C:\Users\joaop\AppData\Local\hermes\bin\claude.cmd")
OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_JSON = ROOT / "docs" / "implementation" / "HARD_LP_SUPERTEST_RESULTS.json"
DEFAULT_MD = ROOT / "docs" / "implementation" / "HARD_LP_SUPERTEST_REPORT.md"

LOAD = [3.42, 3.08, 2.77, 2.95, 3.18, 3.36, 3.05, 2.88, 3.27, 3.51, 3.14, 2.91]
PV = [0.00, 0.18, 0.62, 1.15, 1.86, 2.24, 2.08, 1.54, 0.97, 0.38, 0.06, 0.00]
PRICE = [1.42, 1.18, 0.74, 0.39, 0.31, 0.28, 0.33, 0.57, 0.92, 1.36, 1.58, 1.47]
GRID_CAP = [3.4, 3.2, 2.9, 2.7, 2.5, 2.4, 2.4, 2.6, 2.8, 3.0, 3.1, 3.2]
CAP = 4.60
PMAX = 1.20
SOC0 = 2.35
SOC_END_MIN = 1.80
TOTAL_DISCHARGE_CAP = 4.20
T = len(LOAD)

OPENCODE_GO_MODELS = [
    "grok-4.5",
    "glm-5.2",
    "glm-5.1",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "hy3",
]
CLAUDE_MODELS = ["sonnet", "opus", "fable"]


@dataclass(frozen=True)
class ModelSpec:
    model: str
    provider: str
    source: str
    base_url: str
    key_env: str | None = None


@dataclass
class ArmRun:
    model: str
    provider: str
    arm: str
    ok: bool
    answer: dict[str, Any] | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    error: str = ""
    source: str = ""


def load_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError(f"no JSON object in model output: {text[:600]!r}") from err
        return json.loads(match.group(0))


def build_ops(
    load: list[float],
    pv: list[float],
    price: list[float],
    grid_cap: list[float],
    *,
    cap: float,
    pmax: float,
    soc0: float,
    soc_end_min: float,
    total_discharge_cap: float,
) -> dict[str, Any]:
    variables: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    obj: dict[str, float] = {}
    for t in range(len(load)):
        variables += [
            {"name": f"g{t}", "kind": "continuous", "lower": 0, "upper": float(grid_cap[t])},
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
                    "coeffs": {f"s{t}": 1.0, f"s{t - 1}": -1.0, f"c{t}": -1.0, f"d{t}": 1.0},
                    "sense": "=",
                    "rhs": 0.0,
                }
            )
    constraints.append(
        {
            "name": "terminal_soc",
            "coeffs": {f"s{len(load) - 1}": 1.0},
            "sense": ">=",
            "rhs": float(soc_end_min),
        }
    )
    constraints.append(
        {
            "name": "total_discharge_budget",
            "coeffs": {f"d{t}": 1.0 for t in range(len(load))},
            "sense": "<=",
            "rhs": float(total_discharge_cap),
        }
    )
    return {
        "ops_version": OPS_SCHEMA_VERSION,
        "problem_class": "lp",
        "sense": "min",
        "name": "microgrid_12period_bess_hard_lp",
        "assumptions": [
            f"T={len(load)} CAP={cap} PMAX={pmax} SOC0={soc0} SOC_END_MIN={soc_end_min}",
            f"TOTAL_DISCHARGE_CAP={total_discharge_cap}",
            f"LOAD={load}",
            f"PV={pv}",
            f"PRICE={price}",
            f"GRID_CAP={grid_cap}",
        ],
        "variables": variables,
        "constraints": constraints,
        "objective": {"coeffs": obj},
    }


def oec_pipeline(params: dict[str, Any]) -> dict[str, Any]:
    eng = Engine(skills_root=ROOT / "skills")
    ops = build_ops(
        params["LOAD"],
        params["PV"],
        params["PRICE"],
        params["GRID_CAP"],
        cap=float(params["CAP"]),
        pmax=float(params["PMAX"]),
        soc0=float(params["SOC0"]),
        soc_end_min=float(params["SOC_END_MIN"]),
        total_discharge_cap=float(params["TOTAL_DISCHARGE_CAP"]),
    )
    lm = eng.run("energy.load_metrics", {"power_values": params["LOAD"]})
    lp = eng.run("optimization.lp", {"ops": ops})
    bad = build_ops(
        params["LOAD"],
        params["PV"],
        params["PRICE"],
        params["GRID_CAP"],
        cap=0.8,
        pmax=float(params["PMAX"]),
        soc0=float(params["SOC0"]),
        soc_end_min=float(params["SOC_END_MIN"]),
        total_discharge_cap=float(params["TOTAL_DISCHARGE_CAP"]),
    )
    feas = eng.run("optimization.check_feasibility", {"ops": bad})
    primal = lp.result.get("primal") or {}
    grid = [float(primal.get(f"g{t}", 0.0)) for t in range(T)]
    charge = [float(primal.get(f"c{t}", 0.0)) for t in range(T)]
    discharge = [float(primal.get(f"d{t}", 0.0)) for t in range(T)]
    soc = [float(primal.get(f"s{t}", 0.0)) for t in range(T)]
    return {
        "load_sum_mwh": sum(params["LOAD"]),
        "pv_sum_mwh": sum(params["PV"]),
        "deficit_mwh": sum(params["LOAD"]) - sum(params["PV"]),
        "peak_load_mwh": float((lm.result or {}).get("peak") or max(params["LOAD"])),
        "load_factor": float((lm.result or {}).get("load_factor") or 0.0),
        "min_tou_cost": float(lp.result.get("objective_value") or 0.0),
        "total_grid_mwh": sum(grid),
        "total_discharge_mwh": sum(discharge),
        "total_charge_mwh": sum(charge),
        "terminal_soc_mwh": soc[-1] if soc else 0.0,
        "grid_trajectory": grid,
        "charge_trajectory": charge,
        "discharge_trajectory": discharge,
        "soc_trajectory": soc,
        "impossible_cap_feasible": bool(feas.result.get("feasible")),
    }


def _close(a: object, b: float, tol: float = 0.08) -> bool:
    try:
        return abs(float(a) - b) <= tol
    except (TypeError, ValueError):
        return False


def score(ans: dict[str, Any] | None, oracle: dict[str, Any]) -> dict[str, Any]:
    if not ans:
        return {"score": 0, "max": 10, "details": {}}
    details: dict[str, Any] = {
        "load_sum": _close(ans.get("load_sum_mwh"), oracle["load_sum_mwh"], 0.05),
        "pv_sum": _close(ans.get("pv_sum_mwh"), oracle["pv_sum_mwh"], 0.05),
        "deficit": _close(ans.get("deficit_mwh"), oracle["deficit_mwh"], 0.05),
        "peak_load": _close(ans.get("peak_load_mwh"), oracle["peak_load_mwh"], 0.05),
        "load_factor": _close(ans.get("load_factor"), oracle["load_factor"], 0.05),
        "min_cost": _close(ans.get("min_tou_cost"), oracle["min_tou_cost"], 0.2),
        "total_grid": _close(ans.get("total_grid_mwh"), oracle["total_grid_mwh"], 0.25),
        "total_discharge": _close(
            ans.get("total_discharge_mwh"), oracle["total_discharge_mwh"], 0.25
        ),
        "terminal_soc": _close(ans.get("terminal_soc_mwh"), oracle["terminal_soc_mwh"], 0.15),
        "impossible_cap": (
            ans.get("impossible_cap_feasible") is False
            or str(ans.get("impossible_cap_feasible")).lower() in {"false", "no", "infeasible"}
        )
        and oracle["impossible_cap_feasible"] is False,
    }
    return {"score": sum(1 for v in details.values() if v is True), "max": 10, "details": details}


def discover_models(config_path: Path, env_map: dict[str, str]) -> list[ModelSpec]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    seen: set[tuple[str, str]] = set()
    found: list[ModelSpec] = []
    model_cfg = data.get("model") or {}
    if model_cfg.get("default") and model_cfg.get("provider") and model_cfg.get("base_url"):
        found.append(
            ModelSpec(
                str(model_cfg["default"]),
                str(model_cfg["provider"]),
                "default",
                str(model_cfg["base_url"]),
                "NVIDIA_API_KEY",
            )
        )
        seen.add((str(model_cfg["default"]), str(model_cfg["provider"])))
    custom_by_name: dict[str, dict[str, Any]] = {}
    for entry in data.get("custom_providers") or []:
        if isinstance(entry, dict) and entry.get("name"):
            custom_by_name[str(entry["name"])] = entry
    for idx, entry in enumerate(data.get("fallback_providers") or [], start=1):
        if not isinstance(entry, dict):
            continue
        model = str(entry.get("model") or "").strip()
        provider = str(entry.get("provider") or "").strip()
        if not model or not provider or (model, provider) in seen:
            continue
        seen.add((model, provider))
        if provider == "nvidia":
            found.append(
                ModelSpec(
                    model,
                    provider,
                    f"fallback_{idx}",
                    "https://integrate.api.nvidia.com/v1",
                    "NVIDIA_API_KEY",
                )
            )
        elif provider.startswith("custom:"):
            name = provider.split(":", 1)[1]
            cp = custom_by_name.get(name) or {}
            base_url = str(cp.get("base_url") or "").strip()
            key_env = str(cp.get("key_env") or "").strip() or None
            if base_url:
                found.append(ModelSpec(model, provider, f"fallback_{idx}", base_url, key_env))
    active: list[ModelSpec] = []
    for spec in found:
        if spec.provider == "nvidia" and not env_map.get(spec.key_env or "", ""):
            continue
        if spec.provider.startswith("custom:ollama"):
            active.append(spec)
            continue
        if spec.key_env and env_map.get(spec.key_env):
            active.append(spec)
    if env_map.get("OPENCODE_GO_API_KEY", "").strip():
        seen_models = {(m.model, m.provider) for m in active}
        for idx, model_id in enumerate(OPENCODE_GO_MODELS, start=1):
            if (model_id, "opencode-go") not in seen_models:
                active.append(
                    ModelSpec(
                        model_id,
                        "opencode-go",
                        f"opencode_go_{idx}",
                        OPENCODE_GO_BASE_URL,
                        "OPENCODE_GO_API_KEY",
                    )
                )
    try:
        auth = subprocess.run(
            [CLAUDE_BIN, "auth", "status"], capture_output=True, text=True, timeout=20, check=False
        )
        if auth.returncode == 0 and json.loads(auth.stdout).get("loggedIn"):
            for idx, model_id in enumerate(CLAUDE_MODELS, start=1):
                active.append(
                    ModelSpec(model_id, "claude-cli", f"claude_cli_{idx}", "claude-cli", None)
                )
    except Exception:
        pass
    return active


def openai_chat_completion(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    api_key: str | None,
    timeout_s: int,
) -> str:
    body = {"model": model, "messages": messages, "temperature": 0.1, "stream": False}
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return str(payload["choices"][0]["message"]["content"])


def call_model(
    spec: ModelSpec, system: str, user: str, *, env_map: dict[str, str], timeout_s: int
) -> str:
    if spec.provider == "claude-cli":
        proc = subprocess.run(
            [
                CLAUDE_BIN,
                "-p",
                "--model",
                spec.model,
                "--output-format",
                "text",
                "--permission-mode",
                "dontAsk",
                "--tools",
                "",
                "--system-prompt",
                system,
            ],
            input=user,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                (proc.stderr or proc.stdout or f"claude exited {proc.returncode}").strip()
            )
        return proc.stdout.strip()
    api_key = env_map.get(spec.key_env or "", "") if spec.key_env else None
    return openai_chat_completion(
        spec.base_url,
        spec.model,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        api_key=api_key,
        timeout_s=timeout_s,
    )


PROBLEM_TEXT = f"""
12-period microgrid + BESS hard LP.

LOAD = {LOAD}
PV = {PV}
PRICE = {PRICE}
GRID_CAP = {GRID_CAP}
CAP = {CAP} MWh
PMAX = {PMAX} MWh per period
SOC0 = {SOC0} MWh
Terminal SOC must satisfy SOC[T-1] >= {SOC_END_MIN} MWh
Total discharge budget: sum(discharge[t]) <= {TOTAL_DISCHARGE_CAP} MWh

Dynamics: s[t] = s[t-1] + charge[t] - discharge[t] (s before t=0 is SOC0)
Bounds: 0 <= s[t] <= CAP; 0 <= charge, discharge <= PMAX; 0 <= grid[t] <= GRID_CAP[t]
Balance: LOAD[t] = PV[t] + grid[t] + discharge[t] - charge[t]
Objective: minimize sum PRICE[t] * grid[t]
"""


def build_queries() -> dict[str, tuple[str, str]]:
    keys = (
        "Retorne SOMENTE JSON com as chaves: "
        "load_sum_mwh, pv_sum_mwh, deficit_mwh, peak_load_mwh, load_factor, "
        "min_tou_cost, total_grid_mwh, total_discharge_mwh, total_charge_mwh, terminal_soc_mwh, "
        "grid_trajectory, charge_trajectory, discharge_trajectory, soc_trajectory, "
        "impossible_cap_feasible, reasoning. Sem markdown."
    )
    ops_schema_hint = (
        "Retorne SOMENTE um JSON OPS válido com chaves: "
        "ops_version, problem_class, sense, name, assumptions, variables, constraints, objective. "
        f"Use ops_version={OPS_SCHEMA_VERSION!r}, problem_class='lp', sense='min'."
    )
    return {
        "without_oec": (
            "Você é um engenheiro de otimização. Resolva o problema sozinho, sem ferramentas.",
            f"{PROBLEM_TEXT}\n\n{keys}",
        ),
        "extract_plus_oec": (
            "Você extrai parâmetros numéricos com precisão. Não resolva o problema.",
            f"{PROBLEM_TEXT}\n\nRetorne SOMENTE JSON com: LOAD, PV, PRICE, GRID_CAP, CAP, PMAX, SOC0, SOC_END_MIN, TOTAL_DISCHARGE_CAP. Copie os números exatamente. Sem markdown.",
        ),
        "ops_plus_oec": (
            "Você converte o problema em um documento OPS JSON válido. Não invente resultados numéricos.",
            f"{PROBLEM_TEXT}\n\n{ops_schema_hint}",
        ),
    }


def run_arm(
    spec: ModelSpec, arm: str, system: str, user: str, *, env_map: dict[str, str], timeout_s: int
) -> ArmRun:
    try:
        raw = call_model(spec, system, user, env_map=env_map, timeout_s=timeout_s)
        parsed = extract_json(raw)
        if arm == "without_oec":
            answer = parsed
        elif arm == "extract_plus_oec":
            answer = oec_pipeline(parsed)
        elif arm == "ops_plus_oec":
            eng = Engine(skills_root=ROOT / "skills")
            lp = eng.run("optimization.lp", {"ops": parsed})
            lm = eng.run("energy.load_metrics", {"power_values": LOAD})
            bad = build_ops(
                LOAD,
                PV,
                PRICE,
                GRID_CAP,
                cap=0.8,
                pmax=PMAX,
                soc0=SOC0,
                soc_end_min=SOC_END_MIN,
                total_discharge_cap=TOTAL_DISCHARGE_CAP,
            )
            feas = eng.run("optimization.check_feasibility", {"ops": bad})
            primal = lp.result.get("primal") or {}
            answer = {
                "load_sum_mwh": sum(LOAD),
                "pv_sum_mwh": sum(PV),
                "deficit_mwh": sum(LOAD) - sum(PV),
                "peak_load_mwh": float((lm.result or {}).get("peak") or max(LOAD)),
                "load_factor": float((lm.result or {}).get("load_factor") or 0.0),
                "min_tou_cost": float(lp.result.get("objective_value") or 0.0),
                "total_grid_mwh": sum(float(primal.get(f"g{t}", 0.0)) for t in range(T)),
                "total_discharge_mwh": sum(float(primal.get(f"d{t}", 0.0)) for t in range(T)),
                "total_charge_mwh": sum(float(primal.get(f"c{t}", 0.0)) for t in range(T)),
                "terminal_soc_mwh": float(primal.get(f"s{T - 1}", 0.0)),
                "grid_trajectory": [float(primal.get(f"g{t}", 0.0)) for t in range(T)],
                "charge_trajectory": [float(primal.get(f"c{t}", 0.0)) for t in range(T)],
                "discharge_trajectory": [float(primal.get(f"d{t}", 0.0)) for t in range(T)],
                "soc_trajectory": [float(primal.get(f"s{t}", 0.0)) for t in range(T)],
                "impossible_cap_feasible": bool(feas.result.get("feasible")),
            }
        else:
            raise ValueError(arm)
        return ArmRun(
            spec.model,
            spec.provider,
            arm,
            True,
            answer=answer,
            raw=raw,
            scores=score(answer, ORACLE),
            source=spec.source,
        )
    except Exception as exc:
        return ArmRun(
            spec.model,
            spec.provider,
            arm,
            False,
            error=str(exc),
            scores={"score": 0, "max": 10, "details": {}},
            source=spec.source,
        )


def write_markdown(path: Path, *, models: list[ModelSpec], runs: list[ArmRun]) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    by_model: dict[tuple[str, str], dict[str, ArmRun]] = {}
    for run in runs:
        by_model.setdefault((run.model, run.provider), {})[run.arm] = run
    lines = [
        "# Hard LP supertest report",
        "",
        f"**Date:** {ts}",
        "**Arms:** `without_oec`, `extract_plus_oec`, `ops_plus_oec`",
        "",
        "| Model | Provider | A sem OEC | B extrair+OEC | C OPS+OEC | Best |",
        "|---|---|---:|---:|---:|---|",
    ]
    for spec in models:
        row = by_model.get((spec.model, spec.provider), {})
        scores = {
            arm: int((row.get(arm).scores or {}).get("score", 0)) if row.get(arm) else -1
            for arm in ("without_oec", "extract_plus_oec", "ops_plus_oec")
        }
        best = max(scores, key=scores.get)
        label = {"without_oec": "A", "extract_plus_oec": "B", "ops_plus_oec": "C"}[best]
        lines.append(
            f"| `{spec.model}` | `{spec.provider}` | {scores['without_oec'] if scores['without_oec'] >= 0 else 'ERR'} | {scores['extract_plus_oec'] if scores['extract_plus_oec'] >= 0 else 'ERR'} | {scores['ops_plus_oec'] if scores['ops_plus_oec'] >= 0 else 'ERR'} | {label} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard LP supertest")
    parser.add_argument("--config", type=Path, default=HERMES_CONFIG)
    parser.add_argument("--env-file", type=Path, default=HERMES_ENV)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    env_map = {**load_env_file(args.env_file), **os.environ}
    models = discover_models(args.config, env_map)
    if args.models:
        wanted = set(args.models)
        models = [m for m in models if m.model in wanted]
    if args.list_models:
        print(json.dumps([asdict(m) for m in models], indent=2, ensure_ascii=False))
        return 0
    prompts = build_queries()
    runs: list[ArmRun] = []
    for spec in models:
        for arm, (system, user) in prompts.items():
            print(f"[hard-supertest] {spec.model} | {spec.provider} | {arm}", file=sys.stderr)
            runs.append(run_arm(spec, arm, system, user, env_map=env_map, timeout_s=args.timeout))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "oracle": ORACLE,
        "models": [asdict(m) for m in models],
        "runs": [asdict(r) for r in runs],
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(args.md_out, models=models, runs=runs)
    print(f"Wrote JSON: {args.json_out}")
    print(f"Wrote Markdown: {args.md_out}")
    return 0


ORACLE = oec_pipeline(
    {
        "LOAD": LOAD,
        "PV": PV,
        "PRICE": PRICE,
        "GRID_CAP": GRID_CAP,
        "CAP": CAP,
        "PMAX": PMAX,
        "SOC0": SOC0,
        "SOC_END_MIN": SOC_END_MIN,
        "TOTAL_DISCHARGE_CAP": TOTAL_DISCHARGE_CAP,
    }
)


if __name__ == "__main__":
    raise SystemExit(main())
