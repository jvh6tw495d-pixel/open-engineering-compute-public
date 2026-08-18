"""Governed NEAT via neat-python (ADR 0044)."""

from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path
from typing import Any, Literal

import numpy as np

from oec.evolutionary.contracts import NeatAlgorithmSpec, NeatFitnessName, NeatProblemSpec
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import NeatConnectionIR, NeatGenotypeIR, NeatNodeIR, NeatResult
from oec.kernel.evolutionary.errors import NeatNotAvailableError

_XOR_X: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.0, 1.0),
    (1.0, 0.0),
    (1.0, 1.0),
)
_XOR_Y: tuple[float, ...] = (0.0, 1.0, 1.0, 0.0)


def _require_neat() -> Any:
    try:
        import neat
    except ImportError as exc:
        raise NeatNotAvailableError(
            "neat-python is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return neat


def _neat_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("neat-python")
    except Exception:  # noqa: BLE001
        return None


def _seed_all(neat: Any, seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    reproducibility = getattr(neat, "reproducibility", None)
    setter = getattr(reproducibility, "set_seed", None) if reproducibility is not None else None
    if callable(setter):
        setter(seed)
    elif callable(getattr(neat, "set_seed", None)):
        neat.set_seed(seed)


def _io_dims(problem: NeatProblemSpec) -> tuple[int, int]:
    if problem.fitness == NeatFitnessName.XOR:
        return 2, 1
    assert problem.x is not None and problem.y is not None
    n_in = len(problem.x[0])
    if problem.fitness == NeatFitnessName.TABULAR_REGRESSION:
        return n_in, 1
    labels = [int(v) for v in problem.y]
    n_classes = max(labels) + 1 if labels else 1
    n_out = 1 if n_classes <= 2 else n_classes
    return n_in, n_out


def _write_config(
    path: Path,
    *,
    n_inputs: int,
    n_outputs: int,
    algo: NeatAlgorithmSpec,
) -> None:
    feed = "True" if algo.feed_forward else "False"
    text = f"""[NEAT]
fitness_criterion     = max
fitness_threshold     = 1.0e9
pop_size              = {int(algo.population)}
reset_on_extinction   = False
no_fitness_termination = True

[DefaultGenome]
activation_default      = sigmoid
activation_mutate_rate  = 0.0
activation_options      = sigmoid
aggregation_default     = sum
aggregation_mutate_rate = 0.0
aggregation_options     = sum
bias_init_mean          = 0.0
bias_init_stdev         = 1.0
bias_init_type          = gaussian
bias_max_value          = 30.0
bias_min_value          = -30.0
bias_mutate_power       = 0.5
bias_mutate_rate        = 0.7
bias_replace_rate       = 0.1
compatibility_disjoint_coefficient = {float(algo.compatibility_disjoint_coefficient)}
compatibility_weight_coefficient   = {float(algo.compatibility_weight_coefficient)}
conn_add_prob           = {float(algo.conn_add_prob)}
conn_delete_prob        = {float(algo.conn_delete_prob)}
enabled_default         = True
enabled_mutate_rate     = 0.01
enabled_rate_to_true_add  = 0.0
enabled_rate_to_false_add = 0.0
feed_forward            = {feed}
initial_connection      = full_direct
node_add_prob           = {float(algo.node_add_prob)}
node_delete_prob        = {float(algo.node_delete_prob)}
num_hidden              = {int(algo.num_hidden)}
num_inputs              = {int(n_inputs)}
num_outputs             = {int(n_outputs)}
response_init_mean      = 1.0
response_init_stdev     = 0.0
response_init_type      = gaussian
response_max_value      = 30.0
response_min_value      = -30.0
response_mutate_power   = 0.0
response_mutate_rate    = 0.0
response_replace_rate   = 0.0
weight_init_mean        = 0.0
weight_init_stdev       = 1.0
weight_init_type        = gaussian
weight_max_value        = 30
weight_min_value        = -30
weight_mutate_power     = 0.5
weight_mutate_rate      = 0.8
weight_replace_rate     = 0.1
single_structural_mutation = false
structural_mutation_surer  = default

[DefaultSpeciesSet]
compatibility_threshold = {float(algo.compatibility_threshold)}

[DefaultStagnation]
species_fitness_func = max
max_stagnation       = 20
species_elitism      = 2

[DefaultReproduction]
elitism            = {int(algo.elitism)}
survival_threshold = 0.2
min_species_size   = 2
"""
    path.write_text(text, encoding="utf-8")


def _activate(
    neat: Any,
    genome: Any,
    config: Any,
    features: tuple[float, ...],
    feed_forward: bool,
) -> list[float]:
    if feed_forward:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
    else:
        net = neat.nn.RecurrentNetwork.create(genome, config)
    return [float(v) for v in net.activate(features)]


def _fitness_xor(neat: Any, genome: Any, config: Any, feed_forward: bool) -> float:
    score = 4.0
    for xs, yt in zip(_XOR_X, _XOR_Y, strict=True):
        pred = _activate(neat, genome, config, xs, feed_forward)
        score -= (pred[0] - yt) ** 2
    return float(score)


def _fitness_regression(
    neat: Any,
    genome: Any,
    config: Any,
    feed_forward: bool,
    x: list[list[float]],
    y: list[float],
) -> float:
    err = 0.0
    for row, yt in zip(x, y, strict=True):
        pred = _activate(neat, genome, config, tuple(row), feed_forward)
        err += (pred[0] - float(yt)) ** 2
    return float(-err / len(y))


def _fitness_classification(
    neat: Any,
    genome: Any,
    config: Any,
    feed_forward: bool,
    x: list[list[float]],
    y: list[float],
    n_out: int,
) -> float:
    correct = 0
    for row, yt in zip(x, y, strict=True):
        pred = _activate(neat, genome, config, tuple(row), feed_forward)
        label = (1 if pred[0] >= 0.5 else 0) if n_out == 1 else int(np.argmax(pred))
        if label == int(yt):
            correct += 1
    return float(correct / len(y))


def _node_kind(node_id: int, n_outputs: int) -> Literal["input", "hidden", "output"]:
    if node_id < 0:
        return "input"
    if 0 <= node_id < n_outputs:
        return "output"
    return "hidden"


def _innovation(conn: Any) -> int | None:
    innov = getattr(conn, "innovation", None)
    if isinstance(innov, int):
        return innov
    return None


def _genotype_ir(
    genome: Any,
    *,
    n_inputs: int,
    n_outputs: int,
    feed_forward: bool,
) -> NeatGenotypeIR:
    nodes: list[NeatNodeIR] = [NeatNodeIR(id=-(i + 1), kind="input") for i in range(n_inputs)]
    for key, node in sorted(genome.nodes.items(), key=lambda kv: int(kv[0])):
        nodes.append(
            NeatNodeIR(
                id=int(key),
                kind=_node_kind(int(key), n_outputs),
                bias=float(getattr(node, "bias", 0.0)),
                response=float(getattr(node, "response", 1.0)),
                activation=str(getattr(node, "activation", "sigmoid")),
                aggregation=str(getattr(node, "aggregation", "sum")),
            )
        )
    connections: list[NeatConnectionIR] = []
    items = sorted(
        genome.connections.items(),
        key=lambda kv: (int(kv[0][0]), int(kv[0][1])),
    )
    for key, conn in items:
        source, target = key
        connections.append(
            NeatConnectionIR(
                source=int(source),
                target=int(target),
                weight=float(conn.weight),
                enabled=bool(conn.enabled),
                innovation=_innovation(conn),
            )
        )
    fitness = float(genome.fitness) if genome.fitness is not None else None
    key_id = int(genome.key) if getattr(genome, "key", None) is not None else None
    return NeatGenotypeIR(
        nodes=tuple(nodes),
        connections=tuple(connections),
        n_inputs=n_inputs,
        n_outputs=n_outputs,
        feed_forward=feed_forward,
        fitness=fitness,
        key=key_id,
    )


def run_neat(problem: NeatProblemSpec, algorithm: NeatAlgorithmSpec) -> NeatResult:
    """Evolve a topology under a closed fitness catalog."""
    neat = _require_neat()
    _seed_all(neat, algorithm.seed)
    n_in, n_out = _io_dims(problem)

    with tempfile.TemporaryDirectory(prefix="oec-neat-") as tmp:
        cfg_path = Path(tmp) / "neat.cfg"
        _write_config(cfg_path, n_inputs=n_in, n_outputs=n_out, algo=algorithm)
        config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            str(cfg_path),
        )

        x = problem.x
        y = problem.y
        feed = algorithm.feed_forward
        n_eval = 0
        history: list[float] = []

        def eval_genomes(genomes: list[Any], cfg: Any) -> None:
            nonlocal n_eval
            best = -math.inf
            for _gid, genome in genomes:
                n_eval += 1
                if problem.fitness == NeatFitnessName.XOR:
                    fit = _fitness_xor(neat, genome, cfg, feed)
                elif problem.fitness == NeatFitnessName.TABULAR_REGRESSION:
                    assert x is not None and y is not None
                    fit = _fitness_regression(neat, genome, cfg, feed, x, y)
                else:
                    assert x is not None and y is not None
                    fit = _fitness_classification(neat, genome, cfg, feed, x, y, n_out)
                if not math.isfinite(fit):
                    fit = -1.0e9
                genome.fitness = fit
                if fit > best:
                    best = fit
            history.append(float(best) if math.isfinite(best) else -1.0e9)

        pop = neat.Population(config)
        winner = pop.run(eval_genomes, algorithm.generations)

    n_species = 0
    species_set = getattr(pop, "species", None)
    species = getattr(species_set, "species", None) if species_set is not None else None
    if species is not None:
        n_species = len(species)

    genotype = _genotype_ir(
        winner, n_inputs=n_in, n_outputs=n_out, feed_forward=algorithm.feed_forward
    )
    best_fit = float(winner.fitness) if winner.fitness is not None else float(history[-1])
    return NeatResult(
        backend="neat-python",
        backend_version=_neat_version(),
        algorithm="neat",
        seed=algorithm.seed,
        fitness=problem.fitness.value,
        best_fitness=best_fit,
        genotype=genotype,
        n_nodes=len(genotype.nodes),
        n_connections=len(genotype.connections),
        n_enabled_connections=sum(1 for c in genotype.connections if c.enabled),
        n_species=n_species,
        n_evaluations=n_eval,
        n_generations=len(history),
        history_best=history,
        problem_fingerprint=problem_fingerprint(problem.model_dump(mode="json")),
        message="ok",
    )
