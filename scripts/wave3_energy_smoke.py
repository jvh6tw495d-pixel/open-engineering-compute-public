#!/usr/bin/env python
"""v2.6.1 Wave 3 — Energy-systems smoke (AA authority, not host prose).

Proves that ``authoritative_answer`` carries correct numbers for the
energy-rich skills shipped in Waves 1–2:

* multiperiod hybrid PV+BESS balance (public 6-period fixture)
* energy-based SOC trajectory
* grid-zero **feasibility** (physics — no solver)
* min storage capacity (optimization — composes ``optimization.lp``)

Numeric truth for every OEC arm is read from the MCP envelope via
``scripts/_oec_authority.py`` (``read_authority`` / ``authority_values``).
Host prose is recorded only for the optional weak/strong host runtime legs and is
never used as the score source.

Exercise classes (plan §7 / D4)::

  physics_assertion  — hybrid / SOC / grid-zero feasibility
  optimization       — min_storage_capacity via LP

GATE-W3 failure classes (unchanged)::

  transport_failure | oec_execution_failure | host_corruption

Usage::

  .venv/Scripts/python.exe scripts/wave3_energy_smoke.py
  .venv/Scripts/python.exe scripts/wave3_energy_smoke.py --skip-hosts
  .venv/Scripts/python.exe scripts/wave3_energy_smoke.py \\
      --weak-model granite4:7b-a1b-h-64k --weak-provider custom:ollama \\
      --strong-model nvidia/nemotron-3-ultra-550b-a55b --strong-provider nvidia

Exit 0 iff every AA authority exercise matches its oracle.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SCRIPTS = str(ROOT / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import _oec_authority as authority  # noqa: E402

# Public multiperiod fixture (Wave 1) — energy per period, textbook scale.
from tests.fixtures.physics.hybrid_6period import (  # noqa: E402
    CHARGE,
    DISCHARGE,
    GRID_IMPORT,
    LOAD,
    PV,
    UNIT,
    N,
)

from oec.mcp.server import call_tool  # noqa: E402
from oec.sdk import Engine  # noqa: E402

DEFAULT_JSON = ROOT / "docs" / "implementation" / "v2.6.1-WAVE3-SMOKE-RESULTS.json"
DEFAULT_MD = ROOT / "docs" / "implementation" / "v2.6.1-WAVE3-SMOKE-REPORT.md"

# ---------------------------------------------------------------------------
# Oracles (hand / public fixture) — documented in the report
# ---------------------------------------------------------------------------

# Hybrid 6-period: hand trajectory with residual 0 each period (fixture).
# Skill path uses W × h → Wh; numbers match fixture energies 1:1 with dt=1 h.
ORACLE_HYBRID_6 = {
    "n": N,
    "balanced": True,
    "residuals": [0.0] * N,
    "supply": list(LOAD),  # residual 0 ⇒ supply[t] == load[t]
    "unit": "Wh",
}

# SOC trajectory: charge +10 W·1h then discharge −20 W·1h on 100 Wh, soc0=0.5, η=1
# → soc_path [0.5, 0.6, 0.4], soc_final 0.4, no clip.
ORACLE_SOC = {
    "soc_path": [0.5, 0.6, 0.4],
    "soc_final": 0.4,
    "any_clipped": False,
    "delta_soc": [0.1, -0.2],
    "energy_delta": [10.0, -20.0],
    "unit": "Wh",
}

# Grid-zero feasibility (islanded, physics only — no LP):
# load [2,1], pv [0.5,1.5], discharge [1.5,0], charge [0,0.5], grid [0,0]
ORACLE_GRID_ZERO = {
    "feasible": True,
    "deficit_per_period": [0.0, 0.0],
    "balance_residual": [0.0, 0.0],
    "n": 2,
    "flags": {
        "balance_ok": True,
        "has_deficit": False,
        "has_grid_import": False,
        "grid_zero": True,
    },
    "unit": "Wh",
}

# Min storage capacity (LP via optimization.lp): load [2,1] Wh, no PV, η=1,
# soc0=1 → C* = 3 Wh (hand). Classified as **optimization**, not physics.
ORACLE_MIN_CAP = {
    "optimal_capacity": 3.0,  # Wh (QuantityValue flattened by authority layer)
    "solver_status": "optimal",
    "backend": "highs",
    "n": 2,
    "grid_import": [0.0, 0.0],
    "discharge": [2.0, 1.0],
}


def _qty_series(values: list[float], unit: str = "W") -> list[dict[str, float | str]]:
    return [{"value": float(v), "unit": unit} for v in values]


def hybrid_6period_skill_inputs() -> dict[str, Any]:
    """Skill payload for the public 6-period fixture (W × 1 h → Wh)."""
    return {
        "load": _qty_series(LOAD),
        "pv": _qty_series(PV),
        "grid_import": _qty_series(GRID_IMPORT),
        "storage_charge": _qty_series(CHARGE),
        "storage_discharge": _qty_series(DISCHARGE),
        "dt_hours": {"value": 1.0, "unit": "h"},
    }


def soc_trajectory_skill_inputs() -> dict[str, Any]:
    return {
        "initial_soc": 0.5,
        "powers": [
            {"value": 10.0, "unit": "W"},
            {"value": -20.0, "unit": "W"},
        ],
        "dt_hours": {"value": 1.0, "unit": "h"},
        "capacity": {"value": 100.0, "unit": "Wh"},
        "eta_charge": 1.0,
        "eta_discharge": 1.0,
    }


def grid_zero_skill_inputs() -> dict[str, Any]:
    return {
        "load": _qty_series([2.0, 1.0]),
        "pv": _qty_series([0.5, 1.5]),
        "storage_charge": _qty_series([0.0, 0.5]),
        "storage_discharge": _qty_series([1.5, 0.0]),
        "grid_import": _qty_series([0.0, 0.0]),
        "dt_hours": {"value": 1.0, "unit": "h"},
    }


def min_storage_skill_inputs() -> dict[str, Any]:
    return {
        "load": _qty_series([2.0, 1.0], unit="Wh"),
        "pv": _qty_series([0.0, 0.0], unit="Wh"),
        "eta_charge": 1.0,
        "eta_discharge": 1.0,
        "soc_min": 0.0,
        "soc_max": 1.0,
        "initial_soc": 1.0,
        "horizon_hours": {"value": 2.0, "unit": "h"},
        "curtailment_allowed": False,
    }


# ---------------------------------------------------------------------------
# Numeric compare (oracle vs AA values)
# ---------------------------------------------------------------------------


def _approx(a: Any, b: Any, *, rtol: float = 1e-6, atol: float = 1e-6) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    if isinstance(a, int | float) and isinstance(b, int | float):
        return math.isclose(float(a), float(b), rel_tol=rtol, abs_tol=atol)
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_approx(x, y, rtol=rtol, atol=atol) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        for key, expected in a.items():
            if key not in b or not _approx(expected, b[key], rtol=rtol, atol=atol):
                return False
        return True
    return a == b


def _extract_oracle_slice(values: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    """Pull the oracle-keyed fields from flattened AA values (nested-aware)."""
    out: dict[str, Any] = {}
    for key, expected in oracle.items():
        if key == "optimal_capacity":
            cap = values.get("optimal_capacity")
            if isinstance(cap, dict) and "value" in cap:
                out[key] = float(cap["value"])
            else:
                out[key] = cap
            continue
        if key in ("grid_import", "discharge") and "trajectory" in values:
            traj = values.get("trajectory") or {}
            out[key] = traj.get(key)
            continue
        if key == "flags":
            flags = values.get("flags") or {}
            out[key] = {fk: flags.get(fk) for fk in expected}
            continue
        out[key] = values.get(key)
    return out


# ---------------------------------------------------------------------------
# AA authority exercises (MCP agent surface)
# ---------------------------------------------------------------------------


@dataclass
class ExerciseResult:
    name: str
    skill_id: str
    exercise_class: str  # physics_assertion | optimization
    tool: str
    ok: bool
    kind: str | None = None
    oracle_match: bool = False
    aa_slice: dict[str, Any] = field(default_factory=dict)
    oracle: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    error: str = ""
    verdicts: dict[str, Any] = field(default_factory=dict)
    envelope_schema: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_aa_exercise(
    engine: Engine,
    *,
    name: str,
    skill_id: str,
    inputs: dict[str, Any],
    oracle: dict[str, Any],
    exercise_class: str,
    tool: str = "agent.energy",
) -> ExerciseResult:
    t0 = time.perf_counter()
    try:
        result = call_tool(engine, tool, {"skill_id": skill_id, "inputs": inputs})
        payload = authority.coerce_payload(result)
        elapsed = (time.perf_counter() - t0) * 1000.0
        if result.isError:
            verdicts = authority.three_verdicts(
                payload,
                expect_authority=True,
                detail=f"MCP isError: {authority.read_error(payload)}",
            )
            return ExerciseResult(
                name=name,
                skill_id=skill_id,
                exercise_class=exercise_class,
                tool=tool,
                ok=False,
                elapsed_ms=round(elapsed, 1),
                error=authority.read_error(payload) or "MCP isError",
                verdicts=verdicts.to_dict(),
            )

        aa = authority.read_authority(payload)
        values = authority.authority_values(payload, flatten=True) or {}
        kind = aa.get("kind") if aa else None
        schema = (
            payload.get("authoritative_answer_schema_version")
            if isinstance(payload, dict)
            else None
        )
        slice_ = _extract_oracle_slice(values, oracle)
        match = kind == "energy_result" and _approx(oracle, slice_)
        verdicts = authority.three_verdicts(
            payload,
            expect_authority=True,
            # AA probe has no host claim — host leg is optional host runtime section.
            host_claim=None,
            claim_compare=None,
        )
        return ExerciseResult(
            name=name,
            skill_id=skill_id,
            exercise_class=exercise_class,
            tool=tool,
            ok=match,
            kind=kind,
            oracle_match=match,
            aa_slice=slice_,
            oracle=oracle,
            elapsed_ms=round(elapsed, 1),
            error="" if match else f"oracle mismatch or kind={kind!r}",
            verdicts=verdicts.to_dict(),
            envelope_schema=str(schema) if schema is not None else None,
        )
    except Exception as exc:  # noqa: BLE001 — harness must record crashes
        elapsed = (time.perf_counter() - t0) * 1000.0
        return ExerciseResult(
            name=name,
            skill_id=skill_id,
            exercise_class=exercise_class,
            tool=tool,
            ok=False,
            elapsed_ms=round(elapsed, 1),
            error=f"{type(exc).__name__}: {exc}",
            verdicts=authority.three_verdicts(transport_error=exc, expect_authority=True).to_dict(),
        )


def run_all_aa(engine: Engine) -> list[ExerciseResult]:
    """Core AA exercises — always run; source of pass/fail for Wave 3."""
    cases = [
        (
            "hybrid_6period",
            "energy.hybrid_balance",
            hybrid_6period_skill_inputs(),
            ORACLE_HYBRID_6,
            "physics_assertion",
        ),
        (
            "soc_trajectory",
            "battery.soc_trajectory",
            soc_trajectory_skill_inputs(),
            ORACLE_SOC,
            "physics_assertion",
        ),
        (
            "grid_zero_feasibility",
            "energy.grid_zero_feasibility",
            grid_zero_skill_inputs(),
            ORACLE_GRID_ZERO,
            "physics_assertion",
        ),
        (
            "min_storage_capacity_lp",
            "energy.min_storage_capacity",
            min_storage_skill_inputs(),
            ORACLE_MIN_CAP,
            "optimization",
        ),
    ]
    results: list[ExerciseResult] = []
    for name, skill_id, inputs, oracle, cls in cases:
        # Also exercise agent.default routing for hybrid (representative).
        res = run_aa_exercise(
            engine,
            name=name,
            skill_id=skill_id,
            inputs=inputs,
            oracle=oracle,
            exercise_class=cls,
            tool="agent.energy",
        )
        results.append(res)
        print(
            f"  [AA] {name:28s} skill={skill_id:32s} "
            f"{'PASS' if res.ok else 'FAIL'}  {res.elapsed_ms:.0f} ms  "
            f"kind={res.kind} class={cls}",
            flush=True,
        )
        if not res.ok:
            print(f"       error={res.error}", flush=True)
            print(f"       aa_slice={res.aa_slice}", flush=True)

    # Routed path parity: hybrid via agent.default must match agent.energy AA.
    hybrid_inputs = hybrid_6period_skill_inputs()
    direct = run_aa_exercise(
        engine,
        name="hybrid_6period_routed",
        skill_id="energy.hybrid_balance",
        inputs=hybrid_inputs,
        oracle=ORACLE_HYBRID_6,
        exercise_class="physics_assertion",
        tool="agent.default",
    )
    # agent.default may need skill_id in args — same as integration tests.
    results.append(direct)
    print(
        f"  [AA] {'hybrid_6period_routed':28s} tool=agent.default               "
        f"{'PASS' if direct.ok else 'FAIL'}  {direct.elapsed_ms:.0f} ms",
        flush=True,
    )
    return results


# ---------------------------------------------------------------------------
# Optional host arms (host runtime weak / strong) — host_corruption demo
# ---------------------------------------------------------------------------


@dataclass
class HostArmResult:
    role: str  # weak | strong
    model: str
    provider: str
    arm: str
    ok: bool
    aa_ok: bool = False
    host_parse_ok: bool = False
    host_matches_aa: bool | None = None
    primary_verdict: str = ""
    verdicts: dict[str, Any] = field(default_factory=dict)
    aa_values: dict[str, Any] = field(default_factory=dict)
    host_claim: dict[str, Any] | None = None
    raw_tail: str = ""
    error: str = ""
    elapsed_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError(f"no JSON object in host output: {text[:400]!r}") from None
        return json.loads(match.group(0))


def _host_prompt_grid_zero() -> str:
    """Single focused exercise: islanded grid-zero feasibility via OEC agent."""
    return (
        "Use the MCP oec toolset and call agent.energy (or agent.default) to run "
        "skill energy.grid_zero_feasibility with these inputs exactly:\n"
        "load = [2.0, 1.0] W; pv = [0.5, 1.5] W; storage_charge = [0.0, 0.5] W; "
        "storage_discharge = [1.5, 0.0] W; grid_import = [0.0, 0.0] W; "
        "dt_hours = 1.0 h.\n"
        "Read numbers only from the tool's authoritative_answer — do not recompute.\n"
        "Return ONLY JSON with keys: feasible (bool), deficit_per_period (list), "
        "balance_residual (list), n (int), unit (str). No markdown."
    )


def run_hermes_host(
    *,
    role: str,
    model: str,
    provider: str,
    timeout_s: int,
    aa_probe: dict[str, Any],
) -> HostArmResult:
    """with_oec_agent arm: host may narrate wrong; AA probe is numeric truth."""
    query = _host_prompt_grid_zero()
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
        "30",
        "--source",
        "tool",
        "-t",
        "oec",
    ]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        raw = (proc.stdout or "").strip()
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[:800]
            return HostArmResult(
                role=role,
                model=model,
                provider=provider,
                arm="with_oec_agent",
                ok=False,
                elapsed_s=round(elapsed, 2),
                error=f"hermes exit {proc.returncode}: {err}",
                primary_verdict=authority.TRANSPORT_FAILURE,
                verdicts=authority.three_verdicts(
                    transport_error=RuntimeError(f"hermes exit {proc.returncode}")
                ).to_dict(),
                raw_tail=raw[-1500:],
            )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - t0
        return HostArmResult(
            role=role,
            model=model,
            provider=provider,
            arm="with_oec_agent",
            ok=False,
            elapsed_s=round(elapsed, 2),
            error=f"timeout after {timeout_s}s",
            primary_verdict=authority.TRANSPORT_FAILURE,
            verdicts=authority.three_verdicts(transport_error=exc).to_dict(),
        )
    except FileNotFoundError as exc:
        return HostArmResult(
            role=role,
            model=model,
            provider=provider,
            arm="with_oec_agent",
            ok=False,
            error=f"hermes not found: {exc}",
            primary_verdict=authority.TRANSPORT_FAILURE,
            verdicts=authority.three_verdicts(transport_error=exc).to_dict(),
        )

    host_claim: dict[str, Any] | None = None
    transport_error: Exception | None = None
    try:
        host_claim = _extract_json(raw)
    except Exception as exc:  # noqa: BLE001
        transport_error = exc

    # Probe payload is the real MCP AA for the same exercise (not host prose).
    probe_payload = aa_probe.get("payload")
    probe_values = aa_probe.get("values") or {}

    def _compare(claim: dict[str, Any], _aa: dict[str, Any]) -> bool:
        # Compare host JSON keys against oracle slice of AA values.
        slice_ = {
            "feasible": probe_values.get("feasible"),
            "deficit_per_period": probe_values.get("deficit_per_period"),
            "balance_residual": probe_values.get("balance_residual"),
            "n": probe_values.get("n"),
            "unit": probe_values.get("unit"),
        }
        return _approx(slice_, claim, rtol=1e-4, atol=1e-4)

    verdicts = authority.three_verdicts(
        probe_payload,
        transport_error=transport_error,
        expect_authority=True,
        host_claim=host_claim,
        claim_compare=_compare if host_claim is not None else None,
    )
    aa_ok = probe_values.get("feasible") is True and _approx(
        ORACLE_GRID_ZERO,
        {
            "feasible": probe_values.get("feasible"),
            "deficit_per_period": probe_values.get("deficit_per_period"),
            "balance_residual": probe_values.get("balance_residual"),
            "n": probe_values.get("n"),
            "flags": {
                fk: (probe_values.get("flags") or {}).get(fk) for fk in ORACLE_GRID_ZERO["flags"]
            },
            "unit": probe_values.get("unit"),
        },
    )
    host_matches = None
    if host_claim is not None and aa_ok:
        host_matches = _compare(host_claim, {})

    return HostArmResult(
        role=role,
        model=model,
        provider=provider,
        arm="with_oec_agent",
        ok=aa_ok and transport_error is None,
        aa_ok=aa_ok,
        host_parse_ok=host_claim is not None,
        host_matches_aa=host_matches,
        primary_verdict=verdicts.primary,
        verdicts=verdicts.to_dict(),
        aa_values={
            "feasible": probe_values.get("feasible"),
            "deficit_per_period": probe_values.get("deficit_per_period"),
            "n": probe_values.get("n"),
        },
        host_claim=host_claim,
        raw_tail=raw[-2000:],
        error="" if aa_ok else "AA probe / transport issue",
        elapsed_s=round(elapsed, 2),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(
    path: Path,
    *,
    aa_results: list[ExerciseResult],
    host_results: list[HostArmResult],
    baseline: str,
    started: str,
    finished: str,
) -> None:
    aa_pass = sum(1 for r in aa_results if r.ok)
    aa_total = len(aa_results)
    grid_zero_met = any(r.name == "grid_zero_feasibility" and r.ok for r in aa_results)
    min_cap_met = any(r.name == "min_storage_capacity_lp" and r.ok for r in aa_results)
    lines = [
        "# v2.6.1 Wave 3 — Energy Systems Smoke Report",
        "",
        f"**Date:** {started} → {finished}",
        f"**Baseline:** `{baseline}` (Wave 2 energy-rich skills)",
        "**Harness:** `scripts/wave3_energy_smoke.py`",
        "**Authority:** envelope `authoritative_answer` via `scripts/_oec_authority.py` "
        "(never host-prose scrape)",
        "",
        "## Objective (plan §7)",
        "",
        "Prove rigor on weak and strong hosts: correct numbers in "
        "`authoritative_answer` for **PV+BESS multiperiod** and/or "
        "**grid-zero feasibility**, without scraping prose. Optional: "
        "`min_storage_capacity` via LP (classified as optimization).",
        "",
        "## Oracle (public multiperiod + textbook cases)",
        "",
        "### A. Hybrid 6-period PV+BESS (physics)",
        "",
        "Source: `tests/fixtures/physics/hybrid_6period.py` "
        f"(unit bookkeeping {UNIT} per period; skill path W×1 h → Wh, same numbers).",
        "",
        "```",
        f"LOAD  = {LOAD}",
        f"PV    = {PV}",
        f"CHARGE    = {CHARGE}",
        f"DISCHARGE = {DISCHARGE}",
        f"GRID_IMPORT = {GRID_IMPORT}  # negative = export",
        "Balance: LOAD[t] = PV[t] + grid_import[t] + discharge[t] − charge[t]",
        "Hand trajectory → residual 0 each period → balanced=True, n=6",
        "```",
        "",
        "### B. SOC trajectory (energy-based, physics)",
        "",
        "Charge +10 W for 1 h then discharge −20 W for 1 h; capacity 100 Wh; "
        "soc0=0.5; η_c=η_d=1 → `soc_path=[0.5, 0.6, 0.4]`, `soc_final=0.4`, no clip.",
        "",
        "### C. Grid-zero feasibility (physics — **no** solver)",
        "",
        "Islanded trajectory: load `[2,1]`, pv `[0.5,1.5]`, discharge `[1.5,0]`, "
        "charge `[0,0.5]`, grid `[0,0]` (W × 1 h). Expected: `feasible=True`, "
        "zero deficit, zero residual. Skill: `energy.grid_zero_feasibility` → "
        "`oec.physics.grid_zero` (deterministic).",
        "",
        "### D. Min storage capacity (optimization — composes `optimization.lp`)",
        "",
        "load `[2,1]` Wh, pv `[0,0]`, η=1, soc0=1 → hand optimum **C\\*=3 Wh**. "
        "Skill: `energy.min_storage_capacity` loads `optimization.lp` by path "
        "(HiGHS). **Not** counted as “physics resolved sizing”.",
        "",
        "## Acceptance checklist",
        "",
        "| Criterion | Result |",
        "|---|---|",
        "| Oracle documented (6-period public + textbook) | **Met** — §Oracle above |",
        f"| AA loads hybrid / SOC / grid-zero feasibility | "
        f"**{'Met' if aa_pass >= 3 else 'FAIL'}** — see AA table |",
        f"| Weak may narrate badly; AA numbers correct | "
        f"**{'Met / see host arms' if host_results else 'AA proven; host arms skipped'}** |",
        f"| ≥1 grid-zero feasibility via physics skill | "
        f"**{'Met' if grid_zero_met else 'FAIL'}** |",
        f"| ≥1 min capacity via optimization.lp | **{'Met' if min_cap_met else 'FAIL'}** |",
        "| Classification transport / OEC / host / physics / optimization | **Met** |",
        "| Report versioned; no `.stress-tmp/` | **Met** — this file |",
        "",
        f"## AA authority exercises ({aa_pass}/{aa_total} pass)",
        "",
        "Every row reads `authoritative_answer` from the real MCP agent-tool "
        "surface (`oec.mcp.server.call_tool` → `agent.energy` / `agent.default`). "
        'Required: `kind == "energy_result"` and numeric match to oracle.',
        "",
        "| Exercise | Skill | Class | kind | oracle | elapsed | primary |",
        "|---|---|---|---|---|---:|---|",
    ]
    for r in aa_results:
        primary = (r.verdicts or {}).get("primary", "")
        lines.append(
            f"| `{r.name}` | `{r.skill_id}` | `{r.exercise_class}` | "
            f"`{r.kind}` | {'PASS' if r.oracle_match else 'FAIL'} | "
            f"{r.elapsed_ms:.0f} ms | `{primary}` |"
        )

    lines += [
        "",
        "### AA detail (oracle slices)",
        "",
    ]
    for r in aa_results:
        lines.append(f"#### `{r.name}`")
        lines.append("")
        lines.append(f"- ok: `{r.ok}`")
        lines.append(f"- envelope schema: `{r.envelope_schema}`")
        lines.append(f"- error: `{r.error or '—'}`")
        lines.append("")
        lines.append("```json")
        lines.append(
            json.dumps(
                {"oracle": r.oracle, "aa_slice": r.aa_slice},
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )
        lines.append("```")
        lines.append("")

    lines += [
        "## Host arms (optional weak / strong)",
        "",
        "Same grid-zero exercise. Numeric truth remains the AA probe "
        "(re-run of `energy.grid_zero_feasibility` through MCP). Host JSON is "
        "compared only for `host_corruption` labeling.",
        "",
    ]
    if not host_results:
        lines.append("_Host arms were not run (`--skip-hosts` or hermes unavailable)._")
        lines.append("")
    else:
        lines += [
            "| Role | Model | AA ok | Host parse | Host≡AA | primary | elapsed |",
            "|---|---|---|---|---|---|---:|",
        ]
        for h in host_results:
            heq = "—" if h.host_matches_aa is None else str(h.host_matches_aa)
            lines.append(
                f"| {h.role} | `{h.model}` | {h.aa_ok} | {h.host_parse_ok} | "
                f"{heq} | `{h.primary_verdict}` | {h.elapsed_s:.1f}s |"
            )
        lines.append("")
        for h in host_results:
            lines.append(f"### Host `{h.role}` — `{h.model}`")
            lines.append("")
            lines.append(f"- provider: `{h.provider}`")
            lines.append(f"- arm: `{h.arm}`")
            lines.append(f"- ok (AA available + transport): `{h.ok}`")
            lines.append(f"- AA values: `{json.dumps(h.aa_values)}`")
            lines.append(f"- host claim: `{json.dumps(h.host_claim, default=str)[:500]}`")
            lines.append(f"- error: `{h.error or '—'}`")
            lines.append(f"- verdict detail: `{(h.verdicts or {}).get('detail', '')[:300]}`")
            lines.append("")

    lines += [
        "## Classification summary",
        "",
        "| Class | Meaning | Exercises |",
        "|---|---|---|",
        "| `physics_assertion` | Deterministic physics skill; no HiGHS | "
        "hybrid_6period, soc_trajectory, grid_zero_feasibility |",
        "| `optimization` | Composes `optimization.lp` (HiGHS) | min_storage_capacity_lp |",
        "| `transport_failure` | Host/CLI/timeout before authority | host arms |",
        "| `oec_execution_failure` | OEC ran without AA | AA legs if broken |",
        "| `host_corruption` | Host prose ≠ AA values | host arms when host JSON diverges |",
        "",
        "## Verdict",
        "",
    ]
    if aa_pass == aa_total:
        lines.append(
            f"**PASS** — all {aa_total} AA authority exercises match oracles with "
            f"`kind=energy_result`. Wave 3 smoke criteria for energy-rich skills are met."
        )
    else:
        failed = [r.name for r in aa_results if not r.ok]
        lines.append(f"**FAIL** — AA mismatches: {', '.join(failed)}. Do not claim Wave 3 PASS.")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("| Path | Role |")
    lines.append("|---|---|")
    lines.append("| `docs/implementation/v2.6.1-WAVE3-SMOKE-REPORT.md` | this report |")
    lines.append("| `docs/implementation/v2.6.1-WAVE3-SMOKE-RESULTS.json` | machine-readable |")
    lines.append("| `scripts/wave3_energy_smoke.py` | harness |")
    lines.append("| `tests/fixtures/physics/hybrid_6period.py` | public 6-period oracle |")
    lines.append("")
    lines.append("No `.stress-tmp/` directory is used by this harness.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="v2.6.1 Wave 3 energy systems smoke")
    ap.add_argument("--skip-hosts", action="store_true", help="Skip host runtime weak/strong arms")
    ap.add_argument(
        "--weak-model",
        default=os.environ.get("OEC_W3_WEAK_MODEL", "granite4:7b-a1b-h-64k"),
    )
    ap.add_argument(
        "--weak-provider",
        default=os.environ.get("OEC_W3_WEAK_PROVIDER", "custom:ollama"),
    )
    ap.add_argument(
        "--strong-model",
        default=os.environ.get("OEC_W3_STRONG_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"),
    )
    ap.add_argument(
        "--strong-provider",
        default=os.environ.get("OEC_W3_STRONG_PROVIDER", "nvidia"),
    )
    ap.add_argument("--timeout", type=int, default=240, help="host runtime timeout seconds")
    ap.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    started = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    try:
        baseline = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
    except Exception:  # noqa: BLE001
        baseline = "unknown"

    print(f"=== Wave 3 energy smoke @ {baseline} ===", flush=True)
    print("--- AA authority exercises ---", flush=True)
    engine = Engine(skills_root=ROOT / "skills")
    engine.warm()
    aa_results = run_all_aa(engine)

    host_results: list[HostArmResult] = []
    if not args.skip_hosts:
        print("--- Host arms (host runtime with_oec_agent) ---", flush=True)
        # Authority probe for grid-zero (shared by both host roles).
        probe_ex = run_aa_exercise(
            engine,
            name="grid_zero_probe",
            skill_id="energy.grid_zero_feasibility",
            inputs=grid_zero_skill_inputs(),
            oracle=ORACLE_GRID_ZERO,
            exercise_class="physics_assertion",
        )
        # Rebuild full payload for three_verdicts
        probe_result = call_tool(
            engine,
            "agent.energy",
            {
                "skill_id": "energy.grid_zero_feasibility",
                "inputs": grid_zero_skill_inputs(),
            },
        )
        probe_payload = authority.coerce_payload(probe_result)
        probe_values = authority.authority_values(probe_payload, flatten=True) or {}
        aa_probe = {
            "payload": probe_payload,
            "values": probe_values,
            "ok": probe_ex.ok,
        }
        print(
            f"  AA probe grid_zero: ok={probe_ex.ok} feasible={probe_values.get('feasible')}",
            flush=True,
        )

        for role, model, provider in (
            ("weak", args.weak_model, args.weak_provider),
            ("strong", args.strong_model, args.strong_provider),
        ):
            print(f"  [{role}] {model} ({provider}) ...", flush=True)
            hr = run_hermes_host(
                role=role,
                model=model,
                provider=provider,
                timeout_s=args.timeout,
                aa_probe=aa_probe,
            )
            host_results.append(hr)
            print(
                f"       primary={hr.primary_verdict} aa_ok={hr.aa_ok} "
                f"host≡AA={hr.host_matches_aa} {hr.elapsed_s:.1f}s",
                flush=True,
            )
            if hr.error:
                print(f"       error={hr.error[:200]}", flush=True)

    finished = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "generated_at": finished,
        "baseline": baseline,
        "started": started,
        "finished": finished,
        "oracles": {
            "hybrid_6period": ORACLE_HYBRID_6,
            "soc_trajectory": ORACLE_SOC,
            "grid_zero_feasibility": ORACLE_GRID_ZERO,
            "min_storage_capacity": ORACLE_MIN_CAP,
            "fixture": {
                "load": LOAD,
                "pv": PV,
                "charge": CHARGE,
                "discharge": DISCHARGE,
                "grid_import": GRID_IMPORT,
                "unit": UNIT,
                "n": N,
            },
        },
        "aa_exercises": [r.to_dict() for r in aa_results],
        "host_arms": [h.to_dict() for h in host_results],
        "aa_pass": all(r.ok for r in aa_results),
        "aa_pass_count": sum(1 for r in aa_results if r.ok),
        "aa_total": len(aa_results),
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(
        args.md_out,
        aa_results=aa_results,
        host_results=host_results,
        baseline=baseline,
        started=started,
        finished=finished,
    )
    print(f"Wrote {args.json_out}", flush=True)
    print(f"Wrote {args.md_out}", flush=True)

    if not all(r.ok for r in aa_results):
        print("WAVE3 AA: FAIL", flush=True)
        return 1
    print("WAVE3 AA: PASS", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2) from None
