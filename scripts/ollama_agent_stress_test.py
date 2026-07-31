"""Reliability/robustness stress test of the OEC MCP agent-first tool surface.

Unlike `scripts/hermes_supertest.py` / `scripts/hard_lp_supertest.py` (which are
scored-accuracy leaderboards across many models), this harness drives ONE small
local model against the REAL MCP server and measures *robustness*, not accuracy:

  - does the server survive noisy, small-model tool calls without crashing/hanging?
  - does every failure come back in one of OEC's structured JSON error shapes
    instead of the mcp SDK's generic unstructured error text?
  - does `agent.default` degrade gracefully when it cannot infer a specialist?

The driver model genuinely picks the tool and builds the arguments itself
(Ollama `/api/chat` native function calling); nothing is hand-scripted.

Usage:
  .venv/Scripts/python.exe scripts/ollama_agent_stress_test.py
  .venv/Scripts/python.exe scripts/ollama_agent_stress_test.py --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(r"C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC")
UV_EXE = Path(r"C:\Users\joaop\AppData\Local\hermes\bin\uv.exe")
OLLAMA = "http://127.0.0.1:11434"
MODEL = "nemotron-3-nano:4b-64k"

DEFAULT_JSON = ROOT / "docs" / "implementation" / "OLLAMA_AGENT_STRESS_TEST_RESULTS.json"
DEFAULT_MD = ROOT / "docs" / "implementation" / "OLLAMA_AGENT_STRESS_TEST_REPORT.md"
DEFAULT_UV_CACHE = ROOT / ".uv-cache"
DEFAULT_SERVER_TEMP = ROOT / ".stress-tmp"

SYSTEM_PROMPT = (
    "You are an engineering assistant wired to the OEC compute server. "
    "For any quantitative engineering request, call exactly one OEC tool. "
    "Prefer `agent.default` (the router) unless the user explicitly names a low-level skill. "
    "If no tool fits the request, answer in plain text without calling a tool. "
    "Never invent tool names."
)

# ---------------------------------------------------------------------------
# Prompt battery: 5 real domains + adversarial/ambiguous/nonsense buckets.
# ---------------------------------------------------------------------------
PROMPTS: list[tuple[str, str]] = [
    # --- optimization / LP ---
    ("optimization", "Solve the classic diet LP demo and give me the optimal objective value."),
    (
        "optimization",
        "Minimize 3x + 5y subject to x + y >= 10, x >= 0, y >= 0. Set this up as a linear "
        "program and solve it.",
    ),
    (
        "optimization",
        "I have a binary knapsack with capacity 10 and items of weights [3,4,5] and values "
        "[4,5,8]. Run the knapsack optimization.",
    ),
    ("optimization", "Check whether the LP constraints x >= 5 and x <= 2 are feasible."),
    (
        "optimization",
        "Run the 'min x+y cover' optimization demo through the optimization specialist.",
    ),
    # --- scientific review ---
    (
        "review",
        "Audit this solver result: the model claims objective 42.0 with solver status "
        "'optimal'. Review it without re-solving.",
    ),
    (
        "review",
        "I need an independent scientific review of an optimization execution result. "
        "The execution had status 'optimal' and objective 12.5.",
    ),
    ("review", "Please review and audit my LP write-up for scientific validity."),
    (
        "review",
        "Verify that a claimed optimal objective of -1e9 is credible for a bounded "
        "minimization problem.",
    ),
    # --- applied mathematics ---
    ("mathematics", "Compute the square root of 2 numerically."),
    ("mathematics", "Find the root of the function f(x) = x^2 - 2 on the interval [0, 3]."),
    ("mathematics", "Integrate f(x) = x^2 from 0 to 1."),
    ("mathematics", "Give me descriptive statistics for the sample [1, 2, 3, 4, 5, 100]."),
    ("mathematics", "Run a Monte Carlo estimate demo through the applied mathematics specialist."),
    # --- time series ---
    ("timeseries", "Resample this time series to hourly resolution: values [1,2,3,4,5,6]."),
    ("timeseries", "Detect outliers in the series [10, 11, 10, 12, 400, 11, 10]."),
    (
        "timeseries",
        "Compute the partial autocorrelation (PACF) of the series "
        "[1, 3, 2, 5, 4, 7, 6, 9, 8, 11] up to lag 3.",
    ),
    ("timeseries", "Fill the missing values in the series [1, null, 3, null, 5]."),
    ("timeseries", "Apply a rolling mean with window 3 over [1,2,3,4,5,6,7,8]."),
    # --- energy / battery ---
    (
        "energy",
        "A battery at 50% SOC with 100 kWh capacity charges at 20 kW for 1 hour. "
        "What is the new state of charge?",
    ),
    (
        "energy",
        "Compute the energy balance between a load of [10, 12, 15] MWh and PV generation "
        "of [4, 9, 3] MWh.",
    ),
    ("energy", "Give me the load metrics (peak, load factor) for [10, 12, 15, 9] MWh."),
    (
        "energy",
        "Compute the three-phase power for a 400 V line-to-line, 50 A, power factor 0.92 "
        "system.",
    ),
    ("energy", "Run the battery soc_step demo through the energy specialist."),
    # --- ambiguous / multi-domain (router confusion bait) ---
    (
        "ambiguous_multidomain",
        "I have a battery time series and I want to optimize its dispatch, then have the "
        "result reviewed. Where do I start?",
    ),
    (
        "ambiguous_multidomain",
        "Analyze the energy optimization of my PV time series using linear programming "
        "and statistical review.",
    ),
    (
        "ambiguous_multidomain",
        "Do the thing with the numbers.",
    ),
    (
        "ambiguous_multidomain",
        "Help me with my engineering problem.",
    ),
    (
        "ambiguous_multidomain",
        "Compute the derivative of the battery SOC constraint in my LP objective function "
        "over the time series.",
    ),
    (
        "ambiguous_multidomain",
        "Which OEC specialist should handle a Yule-Walker autoregression fit that feeds an "
        "energy dispatch MILP?",
    ),
    # --- malformed / missing / nonsensical numeric data ---
    (
        "malformed_numeric",
        "Compute the load factor for this data: [].",
    ),
    (
        "malformed_numeric",
        "Solve the LP with objective coefficients ['a', 'b'] and constraint matrix "
        "'not a matrix'.",
    ),
    (
        "malformed_numeric",
        "Set the battery SOC to -500% with a capacity of zero kWh and step it forward.",
    ),
    (
        "malformed_numeric",
        "Resample a time series that has no timestamps and no values to 15-minute " "resolution.",
    ),
    (
        "malformed_numeric",
        "Find the root of f(x) = 5 on the bracket [1, 2] (there is no sign change).",
    ),
    (
        "malformed_numeric",
        "Compute descriptive statistics for the value 'banana'.",
    ),
    # --- off-topic / nonsense ---
    ("offtopic", "What is the capital of Australia?"),
    ("offtopic", "Write me a haiku about a stapler."),
    ("offtopic", "purple monkey dishwasher optimize the flumph"),
    ("offtopic", "Book me a flight to Lisbon next Tuesday."),
    ("offtopic", "asdkjfh 8734 ]]][[ ;;; ???"),
]


# ---------------------------------------------------------------------------
# Result records
# ---------------------------------------------------------------------------
@dataclass
class ToolCallRecord:
    turn_index: int
    tool_name: str
    arguments: Any
    known_tool: bool
    is_error: bool | None = None
    latency_s: float = 0.0
    error_shape: str = ""  # oec_error_result | oec_error_to_dict | unstructured | n/a
    error_shape_ok: bool | None = None
    selected_agent: str | None = None
    response_excerpt: str = ""
    harness_exception: str = ""


@dataclass
class PromptRun:
    index: int
    category: str
    prompt: str
    model_turns: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    final_text: str = ""
    ollama_error: str = ""
    total_s: float = 0.0
    no_tool_called: bool = False


def _tool_catalog_for_ollama(tools: list[Any]) -> list[dict[str, Any]]:
    out = []
    for t in tools:
        schema = t.inputSchema or {"type": "object", "properties": {}}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": (t.description or "")[:400],
                    "parameters": schema,
                },
            }
        )
    return out


def _classify_error_shape(text: str) -> tuple[str, bool]:
    """Return (shape_label, is_acceptable_structured_shape).

    OEC has exactly two legitimate structured error payloads:
      A) `_error_result`  -> {"error": str, "details": {"tool": ..., "error_type": ...}}
      B) `OECError.to_dict` -> {"code": str, "message": str, "details": {...}}
    Anything else (notably the mcp SDK's generic unstructured error string) is a
    regression against fix #2 and is flagged.
    """
    try:
        payload = json.loads(text)
    except Exception:
        return "unstructured_non_json", False
    if not isinstance(payload, dict):
        return "unstructured_non_object", False
    if "error" in payload:
        details = payload.get("details")
        if isinstance(details, dict) and "tool" in details:
            return "oec_error_result", True
        return "error_key_without_details", False
    if {"code", "message", "details"} <= set(payload):
        return "oec_error_to_dict", True
    return "unrecognized_json", False


async def _ollama_chat(
    client: httpx.AsyncClient, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> dict[str, Any]:
    resp = await client.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0.4, "num_ctx": 32768},
        },
        timeout=300.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Ollama /api/chat returned non-object JSON: {type(data).__name__}")
    return data


async def run_prompt(
    session: ClientSession,
    client: httpx.AsyncClient,
    ollama_tools: list[dict[str, Any]],
    known_names: set[str],
    index: int,
    category: str,
    prompt: str,
    max_model_turns: int,
) -> PromptRun:
    run = PromptRun(index=index, category=category, prompt=prompt)
    started = time.perf_counter()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    for turn in range(max_model_turns):
        try:
            data = await _ollama_chat(client, messages, ollama_tools)
        except Exception as exc:
            run.ollama_error = f"{type(exc).__name__}: {exc}"
            break
        run.model_turns += 1
        message = data.get("message") or {}
        messages.append(message)
        calls = message.get("tool_calls") or []
        if not calls:
            run.final_text = (message.get("content") or "")[:1500]
            break

        for call in calls:
            fn = (call or {}).get("function") or {}
            name = str(fn.get("name") or "")
            args = fn.get("arguments")
            args_parse_error = ""
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError as exc:
                    args_parse_error = f"tool call arguments were a non-JSON string: {exc}"
            rec = ToolCallRecord(
                turn_index=turn,
                tool_name=name,
                arguments=args,
                known_tool=name in known_names,
                harness_exception=args_parse_error,
            )
            call_started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool(name, args if isinstance(args, dict) else {"_raw": args}),
                    timeout=180.0,
                )
                rec.latency_s = round(time.perf_counter() - call_started, 3)
                rec.is_error = bool(result.isError)
                blocks = [
                    getattr(c, "text", "") for c in (result.content or []) if hasattr(c, "text")
                ]
                text = "\n".join(blocks)
                rec.response_excerpt = text[:1200]
                if rec.is_error:
                    rec.error_shape, rec.error_shape_ok = _classify_error_shape(text)
                else:
                    rec.error_shape, rec.error_shape_ok = "n/a", None
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            rec.selected_agent = parsed.get("selected_agent")
                    except Exception:
                        pass
                messages.append({"role": "tool", "content": text[:4000], "name": name})
            except TimeoutError:
                rec.latency_s = round(time.perf_counter() - call_started, 3)
                rec.harness_exception = "TIMEOUT: call_tool exceeded 180s (possible server hang)"
                messages.append({"role": "tool", "content": "timeout", "name": name})
            except Exception as exc:
                rec.latency_s = round(time.perf_counter() - call_started, 3)
                rec.harness_exception = f"{type(exc).__name__}: {exc}"
                messages.append(
                    {"role": "tool", "content": f"harness error: {exc}"[:500], "name": name}
                )
            run.tool_calls.append(rec)

    run.no_tool_called = not run.tool_calls
    run.total_s = round(time.perf_counter() - started, 3)
    return run


async def run_concurrency_probe(session: ClientSession) -> dict[str, Any]:
    """Fire overlapping call_tool requests to confirm Engine.run queues cleanly (ADR 0015)."""
    payloads = [
        ("agent.applied_mathematics", {"demo_label": "sqrt2"}),
        ("agent.energy", {"demo_label": "load_metrics"}),
        ("agent.time_series", {"demo_label": "resample"}),
        ("agent.optimization_specialist", {"demo_label": "diet"}),
        ("agent.applied_mathematics", {"demo_label": "integrate_x2"}),
        ("agent.energy", {"demo_label": "balance"}),
        ("list_agents", {}),
        ("agent.default", {"request": "compute the square root of 2"}),
    ]
    started = time.perf_counter()
    results = await asyncio.gather(
        *(session.call_tool(n, a) for n, a in payloads), return_exceptions=True
    )
    elapsed = round(time.perf_counter() - started, 3)
    out: list[dict[str, Any]] = []
    for (name, args), res in zip(payloads, results, strict=True):
        if isinstance(res, BaseException):
            out.append({"tool": name, "args": args, "exception": f"{type(res).__name__}: {res}"})
        else:
            text = "\n".join(
                getattr(c, "text", "") for c in (res.content or []) if hasattr(c, "text")
            )
            out.append(
                {
                    "tool": name,
                    "args": args,
                    "isError": bool(res.isError),
                    "excerpt": text[:200],
                }
            )
    return {"parallel_calls": len(payloads), "wall_clock_s": elapsed, "results": out}


async def main_async(args: argparse.Namespace) -> int:
    stderr_path = Path(args.server_log)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    prompts = PROMPTS[: args.limit] if args.limit else PROMPTS
    uv_cache_dir = Path(args.uv_cache_dir)
    server_temp_dir = Path(args.server_temp_dir)
    uv_cache_dir.mkdir(parents=True, exist_ok=True)
    server_temp_dir.mkdir(parents=True, exist_ok=True)

    params = StdioServerParameters(
        command=str(UV_EXE),
        args=[
            "--directory",
            str(ROOT),
            "run",
            "--extra",
            "mcp",
            "--extra",
            "optimization",
            "oec",
            "server",
            "mcp",
            "--skills-root",
            str(ROOT / "skills"),
        ],
        env={
            "UV_CACHE_DIR": str(uv_cache_dir),
            "TMP": str(server_temp_dir),
            "TEMP": str(server_temp_dir),
        },
        # Deliberately NOT the repo root: reproduces the Hermes launch condition
        # that used to trigger ModuleNotFoundError: No module named 'agents'.
        cwd=r"C:\Windows",
    )

    run_started = time.perf_counter()
    runs: list[PromptRun] = []
    concurrency: dict[str, Any] = {}
    fatal = ""

    with stderr_path.open("w", encoding="utf-8") as errlog:
        try:
            async with (
                stdio_client(params, errlog=errlog) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                tools = (await session.list_tools()).tools
                known_names = {t.name for t in tools}
                ollama_tools = _tool_catalog_for_ollama(tools)
                print(
                    f"[stress] catalog: {len(tools)} tools exposed to {MODEL}",
                    file=sys.stderr,
                )

                async with httpx.AsyncClient() as client:
                    for i, (category, prompt) in enumerate(prompts, start=1):
                        print(
                            f"[stress] {i}/{len(prompts)} [{category}] {prompt[:60]}",
                            file=sys.stderr,
                        )
                        run = await run_prompt(
                            session,
                            client,
                            ollama_tools,
                            known_names,
                            i,
                            category,
                            prompt,
                            args.max_model_turns,
                        )
                        runs.append(run)

                print("[stress] concurrency probe", file=sys.stderr)
                concurrency = await run_concurrency_probe(session)

                # Liveness check AFTER everything: is the server still healthy?
                post = await session.call_tool("list_agents", {})
                concurrency["server_alive_after_run"] = not post.isError
        except Exception:
            fatal = traceback.format_exc()

    total_s = round(time.perf_counter() - run_started, 2)
    server_stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "ollama_endpoint": OLLAMA,
        "server_launch": {
            "command": str(UV_EXE),
            "args": params.args,
            "cwd": params.cwd,
            "env_overrides": params.env,
        },
        "total_wall_clock_s": total_s,
        "fatal_harness_error": fatal,
        "runs": [asdict(r) for r in runs],
        "concurrency_probe": concurrency,
        "server_stderr_tail": server_stderr[-8000:],
    }
    out_json = Path(args.json_out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Total wall clock: {total_s}s")
    return 1 if fatal else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-model-turns", type=int, default=3)
    parser.add_argument("--json-out", default=str(DEFAULT_JSON))
    parser.add_argument(
        "--server-log",
        default=str(ROOT / "docs" / "implementation" / ".mcp_server_stderr.log"),
    )
    parser.add_argument("--uv-cache-dir", default=str(DEFAULT_UV_CACHE))
    parser.add_argument("--server-temp-dir", default=str(DEFAULT_SERVER_TEMP))
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
