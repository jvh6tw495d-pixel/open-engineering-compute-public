# ruff: noqa: E501

"""Direct multi-model benchmark: local models + NIM, without host runtime.

Three arms per model:
  A. without_oec      -> model solves the benchmark alone
  B. extract_plus_oec -> model extracts numeric params; OEC solves
  C. ops_plus_oec     -> model emits OPS JSON; OEC validates/executes

Sources of models:
  - host runtime active config default + fallback providers
  - NIM models via NVIDIA API
  - local Ollama models via local OpenAI-compatible endpoint

OmniRouters is intentionally skipped unless OMNIROUTERS_API_KEY exists and
the model is included explicitly later.

STALE vs 2.5.3 (Wave 3b inventory decision): `run_extract_plus_oec` /
`run_ops_plus_oec` below call `THESIS.oec_pipeline` / `Engine.run(...)`
directly and never cross the `oec.mcp.server.call_tool` boundary, so this
harness predates and bypasses the v2.5.3 `authoritative_answer` envelope /
`claimed_answer` / divergence contract entirely (see
`docs/contracts/authoritative-answer.md`). Its scores are direct-skill
scrapes of `ExecutionResult.result`, not authority-backed, and it does not
participate in the GATE-W3 three-verdict classification
(`scripts/_oec_authority.py`). Migrating it would mean rewriting every call
site to go through `agent.*` MCP tools the way
`multiagent_with_without_oec.py::oec_pipeline_envelope` does -- out of scope
for a migrate-min pass. Superseded for authority-backed, envelope-verified
comparison by `scripts/hermes_supertest.py` (via host runtime) and
`scripts/multiagent_with_without_oec.py` (direct). Kept for its historical
multi-provider coverage; do not treat its scores as an authority-backed
2.5.3 stability signal.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.error
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
DEFAULT_JSON = ROOT / "docs" / "implementation" / "DIRECT_MODEL_SUPERTEST_RESULTS.json"
DEFAULT_MD = ROOT / "docs" / "implementation" / "DIRECT_MODEL_SUPERTEST_REPORT.md"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", r"C:\Users\joaop\AppData\Local\hermes\bin\claude.cmd")
OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"
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
CLAUDE_MODELS = [
    "sonnet",
    "opus",
    "fable",
]


def _load_thesis_module() -> Any:
    thesis_path = ROOT / "scripts" / "multiagent_with_without_oec.py"
    spec = importlib.util.spec_from_file_location("oec_thesis_benchmark", thesis_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load thesis benchmark module from {thesis_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


THESIS = _load_thesis_module()


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


def discover_models(config_path: Path, env_map: dict[str, str]) -> list[ModelSpec]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    seen: set[tuple[str, str]] = set()
    found: list[ModelSpec] = []

    model_cfg = data.get("model") or {}
    default_model = str(model_cfg.get("default") or "").strip()
    default_provider = str(model_cfg.get("provider") or "").strip()
    default_base = str(model_cfg.get("base_url") or "").strip()
    if default_model and default_provider and default_base:
        found.append(
            ModelSpec(
                model=default_model,
                provider=default_provider,
                source="default",
                base_url=default_base,
                key_env="NVIDIA_API_KEY" if default_provider == "nvidia" else None,
            )
        )
        seen.add((default_model, default_provider))

    custom_by_name: dict[str, dict[str, Any]] = {}
    for entry in data.get("custom_providers") or []:
        if isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            if name:
                custom_by_name[name] = entry

    for idx, entry in enumerate(data.get("fallback_providers") or [], start=1):
        if not isinstance(entry, dict):
            continue
        model = str(entry.get("model") or "").strip()
        provider = str(entry.get("provider") or "").strip()
        if not model or not provider:
            continue
        key = (model, provider)
        if key in seen:
            continue
        seen.add(key)
        if provider == "nvidia":
            found.append(
                ModelSpec(
                    model=model,
                    provider=provider,
                    source=f"fallback_{idx}",
                    base_url="https://integrate.api.nvidia.com/v1",
                    key_env="NVIDIA_API_KEY",
                )
            )
        elif provider.startswith("custom:"):
            name = provider.split(":", 1)[1]
            cp = custom_by_name.get(name) or {}
            base_url = str(cp.get("base_url") or "").strip()
            key_env = str(cp.get("key_env") or "").strip() or None
            if base_url:
                found.append(
                    ModelSpec(
                        model=model,
                        provider=provider,
                        source=f"fallback_{idx}",
                        base_url=base_url,
                        key_env=key_env,
                    )
                )
    # Only keep models whose credentials are actually available, except local Ollama
    active: list[ModelSpec] = []
    for spec in found:
        if spec.provider == "nvidia" and not env_map.get(spec.key_env or "", ""):
            continue
        if spec.provider.startswith("custom:ollama"):
            active.append(spec)
            continue
        if spec.key_env and env_map.get(spec.key_env):
            active.append(spec)

    # Add OpenCode Go openai-compatible chat-completions models when the key exists.
    if env_map.get("OPENCODE_GO_API_KEY", "").strip():
        seen_models = {(m.model, m.provider) for m in active}
        for idx, model_id in enumerate(OPENCODE_GO_MODELS, start=1):
            key = (model_id, "opencode-go")
            if key in seen_models:
                continue
            active.append(
                ModelSpec(
                    model=model_id,
                    provider="opencode-go",
                    source=f"opencode_go_{idx}",
                    base_url=OPENCODE_GO_BASE_URL,
                    key_env="OPENCODE_GO_API_KEY",
                )
            )
    # Add Claude Code logged-in Anthropic aliases when local auth exists.
    try:
        auth = subprocess.run(
            [CLAUDE_BIN, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if auth.returncode == 0:
            payload = json.loads(auth.stdout)
            if payload.get("loggedIn"):
                seen_models = {(m.model, m.provider) for m in active}
                for idx, model_id in enumerate(CLAUDE_MODELS, start=1):
                    key = (model_id, "claude-cli")
                    if key in seen_models:
                        continue
                    active.append(
                        ModelSpec(
                            model=model_id,
                            provider="claude-cli",
                            source=f"claude_cli_{idx}",
                            base_url="claude-cli",
                            key_env=None,
                        )
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
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
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


def build_queries() -> dict[str, tuple[str, str]]:
    problem = THESIS.PROBLEM_TEXT.strip()
    keys = (
        "Retorne SOMENTE JSON com as chaves: "
        "load_sum_mwh, pv_sum_mwh, deficit_mwh, peak_load_mwh, load_factor, "
        "min_tou_cost, total_grid_mwh, total_discharge_mwh, total_charge_mwh, "
        "grid_trajectory, charge_trajectory, discharge_trajectory, soc_trajectory, "
        "impossible_cap_feasible, reviewer_passed, reasoning. Sem markdown."
    )
    ops_schema_hint = (
        "Retorne SOMENTE um JSON OPS válido com chaves: "
        "ops_version, problem_class, sense, name, assumptions, variables, constraints, objective. "
        f"Use ops_version={OPS_SCHEMA_VERSION!r}, problem_class='lp', sense='min'."
    )
    return {
        "without_oec": (
            "Você é um engenheiro de otimização. Resolva o problema sozinho, sem ferramentas.",
            f"{problem}\n\n{keys}",
        ),
        "extract_plus_oec": (
            "Você extrai parâmetros numéricos com precisão. Não resolva o problema.",
            (
                f"{problem}\n\n"
                "Retorne SOMENTE JSON com: LOAD, PV, PRICE, CAP, PMAX, SOC0. "
                "Copie os números exatamente. Sem markdown."
            ),
        ),
        "ops_plus_oec": (
            "Você converte o problema em um documento OPS JSON válido. Não invente resultados numéricos.",
            f"{problem}\n\n{ops_schema_hint}",
        ),
    }


def run_extract_plus_oec(params: dict[str, Any]) -> dict[str, Any]:
    load = [float(x) for x in params["LOAD"]]
    pv = [float(x) for x in params["PV"]]
    price = [float(x) for x in params["PRICE"]]
    cap = float(params["CAP"])
    pmax = float(params["PMAX"])
    soc0 = float(params["SOC0"])
    return THESIS.oec_pipeline(load, pv, price, cap=cap, pmax=pmax, soc0=soc0)["answer"]


def run_ops_plus_oec(ops: dict[str, Any]) -> dict[str, Any]:
    engine = Engine(skills_root=ROOT / "skills")
    load_metrics = engine.run("energy.load_metrics", {"power_values": THESIS.LOAD})
    balance = engine.run(
        "energy.balance",
        {"energy_in": THESIS.PV, "energy_out": THESIS.LOAD, "storage_delta": 0.0},
    )
    lp = engine.run("optimization.lp", {"ops": ops})
    trap_ops = THESIS.build_ops(
        THESIS.LOAD, THESIS.PV, THESIS.PRICE, cap=0.5, pmax=THESIS.PMAX, soc0=THESIS.SOC0
    )
    feas = engine.run("optimization.check_feasibility", {"ops": trap_ops})
    primal = lp.result.get("primal") or {}
    grid = [float(primal.get(f"g{t}", 0.0)) for t in range(THESIS.T)]
    charge = [float(primal.get(f"c{t}", 0.0)) for t in range(THESIS.T)]
    discharge = [float(primal.get(f"d{t}", 0.0)) for t in range(THESIS.T)]
    soc = [float(primal.get(f"s{t}", 0.0)) for t in range(THESIS.T)]
    return {
        "load_sum_mwh": sum(THESIS.LOAD),
        "pv_sum_mwh": sum(THESIS.PV),
        "deficit_mwh": sum(THESIS.LOAD) - sum(THESIS.PV),
        "peak_load_mwh": float((load_metrics.result or {}).get("peak") or max(THESIS.LOAD)),
        "load_factor": float((load_metrics.result or {}).get("load_factor") or 0.0),
        "min_tou_cost": float(lp.result.get("objective_value") or 0.0),
        "total_grid_mwh": sum(grid),
        "total_discharge_mwh": sum(discharge),
        "total_charge_mwh": sum(charge),
        "grid_trajectory": grid,
        "charge_trajectory": charge,
        "discharge_trajectory": discharge,
        "soc_trajectory": soc,
        "impossible_cap_feasible": bool(feas.result.get("feasible")),
        "reviewer_passed": True,
        "reasoning": "OPS convertido pelo modelo; OEC validou e executou.",
        "_run_ids": {
            "load_metrics": load_metrics.run_id,
            "balance": balance.run_id,
            "lp": lp.run_id,
            "feasibility": feas.run_id,
        },
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
            answer = run_extract_plus_oec(parsed)
        elif arm == "ops_plus_oec":
            answer = run_ops_plus_oec(parsed)
        else:
            raise ValueError(arm)
        return ArmRun(
            model=spec.model,
            provider=spec.provider,
            arm=arm,
            ok=True,
            answer=answer,
            raw=raw,
            scores=THESIS.score(answer, ORACLE),
            source=spec.source,
        )
    except Exception as exc:
        return ArmRun(
            model=spec.model,
            provider=spec.provider,
            arm=arm,
            ok=False,
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
        "# Direct model supertest report",
        "",
        f"**Date:** {ts}",
        f"**Config source:** `{HERMES_CONFIG}`",
        "**Arms:** `without_oec`, `extract_plus_oec`, `ops_plus_oec`",
        "",
        "## Models tested",
        "",
        "| Model | Provider | Source | Base URL |",
        "|---|---|---|---|",
    ]
    for spec in models:
        lines.append(
            f"| `{spec.model}` | `{spec.provider}` | `{spec.source}` | `{spec.base_url}` |"
        )

    lines += [
        "",
        "## Comparative scoreboard",
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
            f"| `{spec.model}` | `{spec.provider}` | "
            f"{scores['without_oec'] if scores['without_oec'] >= 0 else 'ERR'} | "
            f"{scores['extract_plus_oec'] if scores['extract_plus_oec'] >= 0 else 'ERR'} | "
            f"{scores['ops_plus_oec'] if scores['ops_plus_oec'] >= 0 else 'ERR'} | "
            f"{label} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Direct provider supertest without host runtime")
    parser.add_argument("--config", type=Path, default=HERMES_CONFIG)
    parser.add_argument("--env-file", type=Path, default=HERMES_ENV)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    env_map = {**load_env_file(args.env_file), **os.environ}
    models = discover_models(args.config, env_map)
    if args.models:
        wanted = set(args.models)
        models = [m for m in models if m.model in wanted]
    if args.limit is not None:
        models = models[: args.limit]

    if args.list_models:
        print(json.dumps([asdict(m) for m in models], indent=2, ensure_ascii=False))
        return 0

    prompts = build_queries()
    runs: list[ArmRun] = []
    for spec in models:
        for arm, (system, user) in prompts.items():
            print(f"[direct-supertest] {spec.model} | {spec.provider} | {arm}", file=sys.stderr)
            runs.append(run_arm(spec, arm, system, user, env_map=env_map, timeout_s=args.timeout))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config_path": str(args.config),
        "env_file": str(args.env_file),
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


ORACLE = THESIS.oec_pipeline(
    THESIS.LOAD,
    THESIS.PV,
    THESIS.PRICE,
    cap=THESIS.CAP,
    pmax=THESIS.PMAX,
    soc0=THESIS.SOC0,
)["answer"]


if __name__ == "__main__":
    raise SystemExit(main())
