# ruff: noqa: E501

"""Run a comparative Hermes benchmark across all active configured models.

Three arms:
  A. without_oec      -> no OEC toolset, model must solve alone
  B. with_oec_raw     -> explicit raw OEC tool calls (no agent.default)
  C. with_oec_agent   -> OEC via agent.default router

The canonical benchmark problem and scoring oracle are imported from
`scripts/multiagent_with_without_oec.py` so this script stays aligned with
existing thesis/report artifacts.

Authority (v2.5.3 Wave 3a): `with_oec_*` arms take their numeric truth from
the OEC envelope `authoritative_answer`, replayed once per run through the
real MCP agent-tool surface (`THESIS.oec_pipeline_envelope`) — never from
`extract_json` over host prose. Host prose is kept as `host_answer` (a claim
for the Wave-3b corruption comparison). Every run is classified with the
three labeled GATE-W3 verdicts: transport_failure | oec_execution_failure |
host_corruption (the last stays `pending_wave_3b` until Wave 2 lands
`claimed_answer`; see `scripts/_oec_authority.py`).

Usage:
  uv run python scripts/hermes_supertest.py --list-models
  uv run python scripts/hermes_supertest.py --limit 3
  uv run python scripts/hermes_supertest.py --models nvidia/nemotron-3-ultra-550b-a55b z-ai/glm-5.2
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SCRIPTS_DIR = str(ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import _oec_authority as authority  # noqa: E402

HERMES_CONFIG = Path(
    os.environ.get("HERMES_CONFIG_PATH", r"C:\Users\joaop\AppData\Local\hermes\config.yaml")
)
DEFAULT_JSON = ROOT / "docs" / "implementation" / "HERMES_SUPERTEST_RESULTS.json"
DEFAULT_MD = ROOT / "docs" / "implementation" / "HERMES_SUPERTEST_REPORT.md"


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
    # Wave 3a: authority + 3 labeled verdicts.
    host_answer: dict[str, Any] | None = None  # host prose JSON (claim for 3b)
    host_scores: dict[str, Any] = field(default_factory=dict)
    verdicts: authority.ThreeVerdicts = field(
        default_factory=lambda: authority.ThreeVerdicts.not_exercised("not run")
    )


def _normalize_models_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, dict):
        return [str(k).strip() for k in value if str(k).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return _normalize_models_field(parsed)
        except Exception:
            pass
        parts = [p.strip().strip("\"'") for p in re.split(r"[,\n]", text)]
        return [p for p in parts if p]
    return []


def discover_active_models(config_path: Path) -> list[ModelSpec]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    seen: set[tuple[str, str]] = set()
    found: list[ModelSpec] = []

    model_cfg = data.get("model") or {}
    default_model = str(model_cfg.get("default") or "").strip()
    default_provider = str(model_cfg.get("provider") or "").strip()
    if default_model and default_provider:
        key = (default_model, default_provider)
        seen.add(key)
        found.append(ModelSpec(default_model, default_provider, "default"))

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
        found.append(ModelSpec(model, provider, f"fallback_{idx}"))

    return found


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError(f"no JSON object in model output: {text[:600]!r}") from err
        return json.loads(match.group(0))


def build_queries() -> dict[str, str]:
    problem = THESIS.PROBLEM_TEXT.strip()
    base_keys = (
        "Retorne SOMENTE JSON com as chaves: "
        "load_sum_mwh, pv_sum_mwh, deficit_mwh, peak_load_mwh, load_factor, "
        "min_tou_cost, total_grid_mwh, total_discharge_mwh, total_charge_mwh, "
        "grid_trajectory, charge_trajectory, discharge_trajectory, soc_trajectory, "
        "impossible_cap_feasible, reviewer_passed, reasoning. "
        "Sem markdown."
    )

    without_oec = (
        "Resolva este problema sozinho. Não use ferramentas, MCP ou OEC. "
        "Faça o cálculo você mesmo.\n\n"
        f"{problem}\n\n{base_keys}"
    )

    with_oec_raw = (
        "Use o MCP oec, mas NÃO use agent.default. "
        "Use explicitamente ferramentas cruas do OEC quando necessário, priorizando: "
        "mcp__oec__energy_load_metrics, mcp__oec__energy_balance, "
        "mcp__oec__optimization_lp e mcp__oec__optimization_check_feasibility. "
        "Monte a resposta final a partir dos resultados dessas ferramentas.\n\n"
        f"{problem}\n\n{base_keys}"
    )

    with_oec_agent = (
        "Use o MCP oec e chame agent.default como entrada principal. "
        "Deixe o OEC escolher especialistas e ferramentas. "
        "Monte a resposta final a partir do que o OEC retornar.\n\n"
        f"{problem}\n\n{base_keys}"
    )

    return {
        "without_oec": without_oec,
        "with_oec_raw": with_oec_raw,
        "with_oec_agent": with_oec_agent,
    }


def run_hermes_query(
    model: str, provider: str, query: str, *, use_oec: bool, timeout_s: int
) -> str:
    cmd = [
        "hermes",
        "chat",
        "-q",
        query,
        "-m",
        model,
        "--provider",
        provider,
        "-Q",
        "--max-turns",
        "40",
        "--source",
        "tool",
    ]
    if use_oec:
        cmd.extend(["-t", "oec"])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"hermes exit {proc.returncode}: {(proc.stderr or proc.stdout)[:800]}")
    return proc.stdout.strip()


def _failed_run(spec: ModelSpec, arm: str, error: str, verdicts: authority.ThreeVerdicts) -> ArmRun:
    return ArmRun(
        model=spec.model,
        provider=spec.provider,
        arm=arm,
        ok=False,
        error=error,
        scores={"score": 0, "max": 10, "details": {}},
        verdicts=verdicts,
        source=spec.source,
    )


def run_arm(
    spec: ModelSpec,
    arm: str,
    query: str,
    *,
    timeout_s: int,
    probe: dict[str, Any] | None,
    probe_error: str,
) -> ArmRun:
    use_oec = arm != "without_oec"
    if not use_oec:
        # Control arm: host prose IS the measured surface (no OEC to read).
        try:
            raw = run_hermes_query(
                spec.model, spec.provider, query, use_oec=False, timeout_s=timeout_s
            )
            answer = extract_json(raw)
            return ArmRun(
                model=spec.model,
                provider=spec.provider,
                arm=arm,
                ok=True,
                answer=answer,
                host_answer=answer,
                raw=raw,
                scores=THESIS.score(answer, ORACLE),
                verdicts=authority.three_verdicts(oec_exercised=False),
                source=spec.source,
            )
        except Exception as exc:
            return _failed_run(
                spec,
                arm,
                str(exc),
                authority.three_verdicts(transport_error=exc, oec_exercised=False),
            )

    # with_oec_* arms: numeric truth comes from the authoritative envelope
    # probe (AA), never from extract_json over host prose.
    probe_answer = (probe or {}).get("answer")
    probe_tool_result = (probe or {}).get("authority_tool_result")
    try:
        raw = run_hermes_query(spec.model, spec.provider, query, use_oec=True, timeout_s=timeout_s)
    except Exception as exc:
        return _failed_run(spec, arm, str(exc), authority.three_verdicts(transport_error=exc))
    host_answer: dict[str, Any] | None = None
    transport_error: Exception | None = None
    try:
        host_answer = extract_json(raw)
    except Exception as exc:  # unparseable host output = transport leg failure
        transport_error = exc
    verdicts = authority.three_verdicts(
        probe_tool_result,
        transport_error=transport_error,
        expect_authority=True,
        detail="" if probe is not None else f"authority probe unavailable: {probe_error}",
    )
    ok = transport_error is None and probe_answer is not None
    error = ""
    if transport_error is not None:
        error = f"host output not parseable as JSON: {transport_error}"
    elif probe_answer is None:
        error = f"authority probe produced no authoritative answer: {probe_error}"
    return ArmRun(
        model=spec.model,
        provider=spec.provider,
        arm=arm,
        ok=ok,
        answer=probe_answer,
        host_answer=host_answer,
        raw=raw,
        scores=THESIS.score(probe_answer, ORACLE),
        host_scores=THESIS.score(host_answer, ORACLE) if host_answer else {},
        error=error,
        verdicts=verdicts,
        source=spec.source,
    )


def write_markdown_report(path: Path, *, models: list[ModelSpec], runs: list[ArmRun]) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    by_model: dict[tuple[str, str], dict[str, ArmRun]] = {}
    for run in runs:
        by_model.setdefault((run.model, run.provider), {})[run.arm] = run

    lines = [
        "# Hermes supertest report",
        "",
        f"**Date:** {timestamp}",
        f"**Config source:** `{HERMES_CONFIG}`",
        "**Arms:** `without_oec`, `with_oec_raw`, `with_oec_agent`",
        "",
        (
            "> **Authority (v2.5.3 Wave 3a):** `with_oec_*` scores are authority-backed — "
            "numbers come from the OEC envelope `authoritative_answer` (AA), not from host "
            "prose. What the host actually returned is scored separately as `host score`. "
            "Verdicts are the three labeled GATE-W3 classes: `transport_failure`, "
            "`oec_execution_failure`, `host_corruption` (the last stays `pending_wave_3b` "
            "until the Wave-2 `claimed_answer` comparator lands)."
        ),
        "",
        "## Active models tested",
        "",
        "| Model | Provider | Source |",
        "|---|---|---|",
    ]
    for spec in models:
        lines.append(f"| `{spec.model}` | `{spec.provider}` | `{spec.source}` |")

    lines += [
        "",
        "## Comparative scoreboard",
        "",
        (
            "| Model | Provider | A no OEC (host) | B OEC raw (AA) | C OEC agent (AA) "
            "| B verdict | C verdict | C host prose |"
        ),
        "|---|---|---:|---:|---:|---|---|---:|",
    ]

    for spec in models:
        row = by_model.get((spec.model, spec.provider), {})
        a = row.get("without_oec")
        b = row.get("with_oec_raw")
        c = row.get("with_oec_agent")

        def _score(run: ArmRun | None, key: str = "scores") -> str:
            if run is None:
                return "—"
            value = int((getattr(run, key) or {}).get("score", 0))
            return str(value) if run.ok else f"{value}*"

        b_verdict = b.verdicts.primary if b else "—"
        c_verdict = c.verdicts.primary if c else "—"
        c_host = _score(c, "host_scores")
        lines.append(
            f"| `{spec.model}` | `{spec.provider}` | "
            f"{_score(a)} | {_score(b)} | {_score(c)} | "
            f"`{b_verdict}` | `{c_verdict}` | {c_host} |"
        )

    lines += [
        "",
        "*run failed (`ok=false`); score shown for context only.",
        "",
        "## Verdict summary (GATE-W3)",
        "",
        "Labeled primary-verdict counts per arm — authority health, not accuracy.",
        "",
        "| Arm | total | ok | transport_failure | oec_execution_failure | host_corruption | not_exercised |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("without_oec", "with_oec_raw", "with_oec_agent"):
        counts = authority.verdict_counts(r.verdicts for r in runs if r.arm == arm)
        if counts["total"] == 0:
            continue
        lines.append(
            f"| `{arm}` | {counts['total']} | {counts[authority.OK]} "
            f"| {counts[authority.TRANSPORT_FAILURE]} "
            f"| {counts[authority.OEC_EXECUTION_FAILURE]} "
            f"| {counts[authority.HOST_CORRUPTION]} "
            f"| {counts[authority.NOT_EXERCISED]} |"
        )
    lines += [
        "",
        (
            "`host_corruption` is `pending_wave_3b` by design in Wave 3a: the labeled slot "
            "and the `claim_compare` hook exist, the Wave-2 `claimed_answer` comparator "
            "activates it in Wave 3b."
        ),
        "",
        "## Per-run details",
        "",
    ]

    for spec in models:
        row = by_model.get((spec.model, spec.provider), {})
        lines += [f"### `{spec.model}` ({spec.provider})", ""]
        for arm in ("without_oec", "with_oec_raw", "with_oec_agent"):
            run = row.get(arm)
            if run is None:
                continue
            v = run.verdicts
            lines += [
                f"#### `{arm}`",
                "",
                f"- ok: `{run.ok}`",
                f"- score: `{(run.scores or {}).get('score', 0)}/{(run.scores or {}).get('max', 10)}`",
                (
                    f"- verdicts: transport=`{v.transport}` oec_execution=`{v.oec_execution}` "
                    f"host_corruption=`{v.host_corruption}` → **{v.primary}**"
                ),
            ]
            if v.detail:
                lines.append(f"- verdict detail: `{v.detail}`")
            if arm != "without_oec":
                lines.append(
                    "- answer source: `authoritative_answer` (envelope probe); "
                    f"host prose score: `{(run.host_scores or {}).get('score', 0)}/10`"
                )
            if run.error:
                lines.append(f"- error: `{run.error}`")
            if run.answer is not None:
                lines += [
                    "",
                    "```json",
                    json.dumps(run.answer, indent=2, ensure_ascii=False),
                    "```",
                ]
            if run.host_answer is not None and arm != "without_oec":
                lines += [
                    "",
                    "Host prose answer (claim for Wave-3b comparison):",
                    "",
                    "```json",
                    json.dumps(run.host_answer, indent=2, ensure_ascii=False),
                    "```",
                ]
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes multi-model supertest across 3 arms")
    parser.add_argument("--config", type=Path, default=HERMES_CONFIG)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--models", nargs="*", default=None, help="Specific model names to run")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of discovered models")
    parser.add_argument("--timeout", type=int, default=900, help="Per-run timeout in seconds")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    models = discover_active_models(args.config)
    if args.models:
        wanted = set(args.models)
        models = [m for m in models if m.model in wanted]
    if args.limit is not None:
        models = models[: args.limit]

    if args.list_models:
        print(json.dumps([asdict(m) for m in models], indent=2))
        return 0

    queries = build_queries()

    # Authority probe (Wave 3a): replay the canonical problem once through the
    # real MCP agent-tool surface and hold its authoritative_answer as the
    # numeric truth for every with_oec_* run. OEC is deterministic given the
    # problem, so one probe covers all models.
    probe: dict[str, Any] | None = None
    probe_error = ""
    try:
        probe = THESIS.oec_pipeline_envelope(
            THESIS.LOAD,
            THESIS.PV,
            THESIS.PRICE,
            cap=THESIS.CAP,
            pmax=THESIS.PMAX,
            soc0=THESIS.SOC0,
        )
        print(
            "[supertest] authority probe ok: "
            f"min_tou_cost={probe['answer']['min_tou_cost']} "
            f"reviewer_passed={probe['answer']['reviewer_passed']}",
            file=sys.stderr,
        )
    except Exception as exc:
        probe_error = f"{type(exc).__name__}: {exc}"
        print(f"[supertest] authority probe FAILED: {probe_error}", file=sys.stderr)

    runs: list[ArmRun] = []
    for spec in models:
        for arm, query in queries.items():
            print(f"[supertest] {spec.model} | {spec.provider} | {arm}", file=sys.stderr)
            runs.append(
                run_arm(
                    spec, arm, query, timeout_s=args.timeout, probe=probe, probe_error=probe_error
                )
            )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config_path": str(args.config),
        "oracle": ORACLE,
        "authority_probe": {
            "ok": probe is not None,
            "error": probe_error,
            "method": (probe or {}).get("method"),
            "answer": (probe or {}).get("answer"),
            "provenance": (probe or {}).get("provenance"),
        },
        "models": [asdict(m) for m in models],
        "runs": [asdict(r) for r in runs],
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_report(args.md_out, models=models, runs=runs)
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
