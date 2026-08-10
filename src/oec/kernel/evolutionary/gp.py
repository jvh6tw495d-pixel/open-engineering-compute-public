"""Genetic programming symbolic regression via DEAP (E3).

Trees use only the closed operator IR in ``gp_operators`` (no Python eval).
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np

from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp_operators import (
    BINARY_OPS,
    UNARY_OPS,
    eval_tree,
    tree_depth,
    tree_size,
)


def _require_deap() -> Any:
    try:
        import deap
        from deap import base, creator, gp, tools
    except ImportError as exc:
        raise DeapNotAvailableError(
            "DEAP is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return deap, base, creator, gp, tools


def _deap_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("deap")
    except Exception:  # noqa: BLE001
        return None


def _rand_const() -> float:
    return random.uniform(-2.0, 2.0)


def _primitive_set(n_var: int, gp_mod: Any) -> Any:
    pset = gp_mod.PrimitiveSet("MAIN", n_var)
    for name, bin_fn in BINARY_OPS.items():
        pset.addPrimitive(bin_fn, 2, name=name)
    for name, un_fn in UNARY_OPS.items():
        pset.addPrimitive(un_fn, 1, name=name)
    pset.addEphemeralConstant("rand", _rand_const)
    rename = {f"ARG{i}": f"x{i}" for i in range(n_var)}
    pset.renameArguments(**rename)
    return pset


def _tree_list_to_ir(tree: list[Any]) -> Any:
    """Walk DEAP prefix PrimitiveTree list into IR dict."""
    index = 0

    def walk() -> Any:
        nonlocal index
        node = tree[index]
        index += 1
        arity = getattr(node, "arity", 0)
        if arity == 0:
            s = str(node)
            if s.startswith("ARG"):
                return {"var": "x" + s[3:]}
            if s.startswith("x"):
                return {"var": s}
            try:
                return {"const": float(s)}
            except ValueError:
                return {"const": 0.0}
        args = [walk() for _ in range(arity)]
        return {"op": node.name, "args": args}

    return walk()


def _sample_target(
    target: str, n_var: int, n_samples: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2.0, 2.0, size=(n_samples, n_var))
    if target == "poly2":
        y = x[:, 0] ** 2 + 0.5 * x[:, 0] + 0.1
    elif target == "sin_x":
        y = np.sin(x[:, 0])
    elif target == "keijzer":
        y = x[:, 0] ** 3 + x[:, 0] ** 2 + x[:, 0]
    else:
        raise ValueError(f"unknown GP target {target}")
    return x, y


def run_genetic_programming(
    *,
    n_var: int = 1,
    target: str = "poly2",
    n_samples: int = 40,
    population: int = 80,
    generations: int = 25,
    max_depth: int = 5,
    max_size: int = 40,
    seed: int = 42,
    tournament_size: int = 3,
    cx_prob: float = 0.5,
    mut_prob: float = 0.2,
) -> dict[str, Any]:
    """Symbolic regression GP with DEAP; returns best IR tree + MSE."""
    _deap, base, creator, gp, tools = _require_deap()
    del _deap

    random.seed(seed)
    np.random.seed(seed)

    if hasattr(creator, "FitnessMin"):
        del creator.FitnessMin
    if hasattr(creator, "Individual"):
        del creator.Individual

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMin)

    pset = _primitive_set(n_var, gp)
    toolbox = base.Toolbox()
    toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=1, max_=max_depth)
    toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("compile", gp.compile, pset=pset)

    x_data, y_data = _sample_target(target, n_var, n_samples, seed)

    def _fitness(individual: Any) -> tuple[float]:
        if len(individual) > max_size or individual.height > max_depth:
            return (1e6,)
        try:
            func = toolbox.compile(expr=individual)
        except Exception:  # noqa: BLE001
            return (1e6,)
        preds: list[float] = []
        for row in x_data:
            try:
                val = func(float(row[0])) if n_var == 1 else func(*[float(v) for v in row])
                if not np.isfinite(val):
                    return (1e6,)
                preds.append(float(val))
            except Exception:  # noqa: BLE001
                return (1e6,)
        mse = float(np.mean((np.asarray(preds) - y_data) ** 2))
        return (mse,)

    toolbox.register("evaluate", _fitness)
    toolbox.register("select", tools.selTournament, tournsize=tournament_size)
    toolbox.register("mate", gp.cxOnePoint)
    toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
    toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

    def _limit_height(ind: Any) -> int:
        return int(ind.height)

    toolbox.decorate("mate", gp.staticLimit(key=_limit_height, max_value=max_depth))
    toolbox.decorate("mutate", gp.staticLimit(key=_limit_height, max_value=max_depth))

    pop = toolbox.population(n=population)
    hof = tools.HallOfFame(1)
    history: list[dict[str, float]] = []

    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)
    hof.update(pop)

    for gen in range(generations):
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))
        for i in range(1, len(offspring), 2):
            if random.random() < cx_prob:
                offspring[i - 1], offspring[i] = toolbox.mate(offspring[i - 1], offspring[i])
                del offspring[i - 1].fitness.values
                del offspring[i].fitness.values
        for i in range(len(offspring)):
            if random.random() < mut_prob:
                (offspring[i],) = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid:
            ind.fitness.values = toolbox.evaluate(ind)
        pop[:] = offspring
        hof.update(pop)
        fits = [ind.fitness.values[0] for ind in pop]
        history.append(
            {
                "generation": float(gen + 1),
                "best_mse": float(min(fits)),
                "mean_mse": float(np.mean(fits)),
            }
        )

    best = hof[0]
    best_ir = _tree_list_to_ir(list(best))
    env0 = {f"x{i}": float(x_data[0, i]) for i in range(n_var)}
    try:
        _ = eval_tree(best_ir, env0)
        ir_ok = True
    except Exception:  # noqa: BLE001
        ir_ok = False

    return {
        "backend": "deap",
        "backend_version": _deap_version(),
        "algorithm": "genetic_programming",
        "seed": seed,
        "deterministic_status": "practical",
        "target": target,
        "best_mse": float(best.fitness.values[0]),
        "best_expression": str(best),
        "best_tree_ir": best_ir,
        "tree_size": tree_size(best_ir),
        "tree_depth": tree_depth(best_ir),
        "ir_eval_ok": ir_ok,
        "n_generations": generations,
        "population": population,
        "max_depth": max_depth,
        "max_size": max_size,
        "history": history[-5:],
        "n_samples": n_samples,
        "n_var": n_var,
        "problem_fingerprint": problem_fingerprint(
            {"target": target, "n_var": n_var, "n_samples": n_samples, "seed": seed}
        ),
        "message": "ok",
    }


def run_evolution_strategy(
    *,
    n_var: int = 2,
    built_in: str = "sphere",
    population: int = 30,
    generations: int = 40,
    seed: int = 42,
    sigma: float = 0.5,
) -> dict[str, Any]:
    """Simple GA/ES-style real-valued search on built-in SOO problems (DEAP)."""
    _deap, base, creator, gp, tools = _require_deap()
    del _deap, gp

    from oec.evolutionary.contracts import BuiltInProblemName
    from oec.kernel.evolutionary.problems import evaluate_built_in

    random.seed(seed)
    np.random.seed(seed)
    problem = BuiltInProblemName(built_in)

    if hasattr(creator, "FitnessMinES"):
        del creator.FitnessMinES
    if hasattr(creator, "IndividualES"):
        del creator.IndividualES
    creator.create("FitnessMinES", base.Fitness, weights=(-1.0,))
    creator.create("IndividualES", list, fitness=creator.FitnessMinES)

    toolbox = base.Toolbox()

    def init_ind() -> Any:
        return creator.IndividualES([random.uniform(-5, 5) for _ in range(n_var)])

    toolbox.register("individual", init_ind)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def evaluate(ind: list[float]) -> tuple[float]:
        return (evaluate_built_in(problem, np.asarray(ind, dtype=float)),)

    toolbox.register("evaluate", evaluate)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("mate", tools.cxBlend, alpha=0.5)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=sigma, indpb=0.3)

    pop = toolbox.population(n=population)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)
    best = tools.selBest(pop, 1)[0]
    history: list[dict[str, float]] = []

    for gen in range(generations):
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))
        for i in range(1, len(offspring), 2):
            if random.random() < 0.5:
                offspring[i - 1], offspring[i] = toolbox.mate(offspring[i - 1], offspring[i])
                del offspring[i - 1].fitness.values
                del offspring[i].fitness.values
        for i in range(len(offspring)):
            if random.random() < 0.3:
                (offspring[i],) = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values
            for j in range(n_var):
                offspring[i][j] = min(5.0, max(-5.0, float(offspring[i][j])))
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid:
            ind.fitness.values = toolbox.evaluate(ind)
        pop[:] = offspring
        cur_best = tools.selBest(pop, 1)[0]
        if cur_best.fitness.values[0] < best.fitness.values[0]:
            best = toolbox.clone(cur_best)
        history.append(
            {
                "generation": float(gen + 1),
                "best_objective": float(best.fitness.values[0]),
            }
        )

    return {
        "backend": "deap",
        "backend_version": _deap_version(),
        "algorithm": "evolution_strategy",
        "seed": seed,
        "deterministic_status": "practical",
        "built_in": built_in,
        "best_objective": float(best.fitness.values[0]),
        "best_x": {f"x{i}": float(best[i]) for i in range(n_var)},
        "n_generations": generations,
        "population": population,
        "history": history[-5:],
        "problem_fingerprint": problem_fingerprint(
            {"built_in": built_in, "n_var": n_var, "seed": seed}
        ),
        "message": "ok",
    }
