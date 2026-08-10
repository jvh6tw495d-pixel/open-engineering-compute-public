"""Agent-native scientific method selection (X3).

Maps a declarative problem class to candidate OEC skills, filters by
backend availability, optionally runs a thin benchmark, and returns a
recommendation. Agents formulate; OEC selects and (optionally) executes.
"""

from __future__ import annotations

from typing import Any, Literal

from oec.backends.registry import get_backend_capabilities
from oec.evolutionary.hashing import problem_fingerprint

ProblemClass = Literal[
    "soo_box",
    "multiobjective",
    "symbolic_regression",
    "blackbox",
    "neural_tabular",
    "neural_sequence",
    "neural_graph",
    "hybrid_surrogate",
    "hyperparam_search",
]

# Catalog: problem class → ordered candidates (preference order)
_CATALOG: dict[str, list[dict[str, str]]] = {
    "soo_box": [
        {
            "skill_id": "evolutionary.optimize_single",
            "method_id": "pymoo_optimize_single",
            "backend": "pymoo",
            "domain": "evolutionary_single",
        },
        {
            "skill_id": "evolutionary.blackbox_optimize",
            "method_id": "nevergrad_blackbox_optimize",
            "backend": "nevergrad",
            "domain": "blackbox_optimize",
        },
        {
            "skill_id": "evolutionary.differential_evolution",
            "method_id": "pymoo_de",
            "backend": "pymoo",
            "domain": "evolutionary_single",
        },
    ],
    "multiobjective": [
        {
            "skill_id": "evolutionary.nsga2",
            "method_id": "pymoo_nsga2",
            "backend": "pymoo",
            "domain": "evolutionary_multi",
        },
        {
            "skill_id": "evolutionary.pareto_search",
            "method_id": "pymoo_pareto_search",
            "backend": "pymoo",
            "domain": "evolutionary_multi",
        },
    ],
    "symbolic_regression": [
        {
            "skill_id": "evolutionary.genetic_programming",
            "method_id": "deap_genetic_programming",
            "backend": "deap",
            "domain": "genetic_programming",
        },
    ],
    "blackbox": [
        {
            "skill_id": "evolutionary.blackbox_optimize",
            "method_id": "nevergrad_blackbox_optimize",
            "backend": "nevergrad",
            "domain": "blackbox_optimize",
        },
        {
            "skill_id": "evolutionary.optimizer_portfolio",
            "method_id": "nevergrad_optimizer_portfolio",
            "backend": "nevergrad",
            "domain": "blackbox_optimize",
        },
    ],
    "neural_tabular": [
        {
            "skill_id": "neural.mlp.regressor",
            "method_id": "torch_mlp_regressor_train",
            "backend": "torch",
            "domain": "neural_train",
        },
        {
            "skill_id": "neural.mlp.classifier",
            "method_id": "torch_mlp_classifier_train",
            "backend": "torch",
            "domain": "neural_train",
        },
    ],
    "neural_sequence": [
        {
            "skill_id": "neural.lstm",
            "method_id": "torch_lstm_train",
            "backend": "torch",
            "domain": "neural_train",
        },
        {
            "skill_id": "neural.tcn",
            "method_id": "torch_tcn_train",
            "backend": "torch",
            "domain": "neural_train",
        },
        {
            "skill_id": "neural.transformer.sequence_regressor",
            "method_id": "torch_transformer_seq_regressor",
            "backend": "torch",
            "domain": "neural_train",
        },
    ],
    "neural_graph": [
        {
            "skill_id": "neural.gcn",
            "method_id": "torch_gcn_train",
            "backend": "torch",
            "domain": "neural_train",
        },
        {
            "skill_id": "neural.gat",
            "method_id": "torch_gat_train",
            "backend": "torch",
            "domain": "neural_train",
        },
    ],
    "hybrid_surrogate": [
        {
            "skill_id": "hybrid.surrogate_optimize",
            "method_id": "hybrid_surrogate_optimize",
            "backend": "torch",
            "domain": "neural_train",
            "also_requires": "nevergrad",
        },
    ],
    "hyperparam_search": [
        {
            "skill_id": "hybrid.evo_hyperparams",
            "method_id": "hybrid_evo_hyperparams",
            "backend": "torch",
            "domain": "neural_train",
            "also_requires": "nevergrad",
        },
    ],
}


def select_method(
    *,
    problem_class: str,
    budget_seconds: float | None = None,
    prefer_backend: str | None = None,
    run_probe_benchmark: bool = False,
    seed: int = 42,
) -> dict[str, Any]:
    """Select an available method for ``problem_class``.

    If ``run_probe_benchmark`` and class is soo_box/blackbox, runs a tiny
    shared-budget comparison among available candidates (X1 spirit).
    """
    if problem_class not in _CATALOG:
        raise ValueError(f"unknown problem_class {problem_class!r}; choose from {sorted(_CATALOG)}")

    caps = {c.name: c for c in get_backend_capabilities()}
    candidates = _CATALOG[problem_class]
    available: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []

    for c in candidates:
        backend = c["backend"]
        ok = caps.get(backend) is not None and caps[backend].available
        also = c.get("also_requires")
        if also and (caps.get(also) is None or not caps[also].available):
            ok = False
        entry = {**c, "backend_available": ok}
        if ok:
            available.append(entry)
        else:
            entry["reason"] = f"backend {backend!r} (or dependency) unavailable"
            unavailable.append(entry)

    if prefer_backend:
        preferred = [a for a in available if a["backend"] == prefer_backend]
        if preferred:
            available = preferred + [a for a in available if a not in preferred]

    # Soft budget hint (documentation only for v0)
    budget_note = None
    if budget_seconds is not None:
        if budget_seconds < 5:
            budget_note = "tight budget: prefer OnePlusOne / DE / small generations"
        elif budget_seconds > 60:
            budget_note = "ample budget: portfolio or NSGA with larger pop ok"

    selected = available[0] if available else None
    probe: dict[str, Any] | None = None

    if run_probe_benchmark and available and problem_class in ("soo_box", "blackbox"):
        probe = _probe_soo(available, seed=seed)

        if probe and probe.get("best_skill_id"):
            # re-order selected to probe winner if still available
            for a in available:
                if a["skill_id"] == probe["best_skill_id"]:
                    selected = a
                    break

    return {
        "problem_class": problem_class,
        "selected": selected,
        "available_candidates": available,
        "unavailable_candidates": unavailable,
        "prefer_backend": prefer_backend,
        "budget_seconds": budget_seconds,
        "budget_note": budget_note,
        "probe_benchmark": probe,
        "policy": (
            "Selection uses capability registry + optional probe benchmark. "
            "Agent must call the selected skill_id for execution; numbers come "
            "only from skill ExecutionResult (X3)."
        ),
        "problem_fingerprint": problem_fingerprint(
            {
                "problem_class": problem_class,
                "prefer_backend": prefer_backend,
                "run_probe": run_probe_benchmark,
                "seed": seed,
            }
        ),
        "message": "ok" if selected else "no_available_method",
    }


def _probe_soo(available: list[dict[str, Any]], *, seed: int) -> dict[str, Any]:
    """Tiny same-problem probe for SOO methods."""
    rows: list[dict[str, Any]] = []
    for cand in available[:3]:
        sid = cand["skill_id"]
        try:
            if "blackbox" in sid or "nevergrad" in cand["method_id"]:
                from oec.kernel.evolutionary.blackbox import blackbox_optimize

                res = blackbox_optimize(
                    built_in="sphere",
                    n_var=2,
                    budget=40,
                    optimizer="OnePlusOne",
                    seed=seed,
                )
                rows.append(
                    {
                        "skill_id": sid,
                        "best_objective": res["best_objective"],
                        "backend": cand["backend"],
                    }
                )
            elif cand["backend"] == "pymoo":
                from oec.evolutionary.contracts import (
                    AlgorithmName,
                    BudgetSpec,
                    BuiltInProblemName,
                    EvolutionaryAlgorithmSpec,
                    EvolutionaryProblemSpec,
                    VariableSpec,
                )
                from oec.kernel.evolutionary.optimize import optimize_single

                res_o = optimize_single(
                    EvolutionaryProblemSpec(
                        variables=[
                            VariableSpec(name="x1", lower=-2, upper=2),
                            VariableSpec(name="x2", lower=-2, upper=2),
                        ],
                        built_in=BuiltInProblemName.SPHERE,
                    ),
                    EvolutionaryAlgorithmSpec(
                        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
                        budget=BudgetSpec(generations=12, population=16),
                        seed=seed,
                    ),
                )
                rows.append(
                    {
                        "skill_id": sid,
                        "best_objective": res_o.best_objective,
                        "backend": cand["backend"],
                    }
                )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "skill_id": sid,
                    "error": str(exc),
                    "backend": cand["backend"],
                }
            )

    scored = [r for r in rows if "best_objective" in r]
    best = min(scored, key=lambda r: float(r["best_objective"])) if scored else None
    return {
        "mode": "soo_probe_sphere",
        "rows": rows,
        "best_skill_id": best["skill_id"] if best else None,
        "note": "Probe is a tiny sphere run under fixed budget — not universal ranking.",
    }
