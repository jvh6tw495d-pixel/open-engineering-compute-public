"""Governed HyperNEAT: NEAT-evolved CPPN + fixed substrate (ADR 0045)."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    HyperNeatAlgorithmSpec,
    HyperNeatSubstrateName,
    NeatFitnessName,
    NeatProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import (
    HyperNeatResult,
    HyperNeatSubstrateIR,
    HyperNeatSubstrateNodeIR,
    NeatConnectionIR,
)
from oec.kernel.evolutionary.neat import (
    _XOR_X,
    _XOR_Y,
    _genotype_ir,
    _io_dims,
    _neat_version,
    _require_neat,
    _seed_all,
    _write_config,
)


def _ys(count: int) -> list[float]:
    if count <= 1:
        return [0.0]
    return [-1.0 + 2.0 * i / (count - 1) for i in range(count)]


def _layered_1d(
    n_in: int,
    n_out: int,
    hidden_layers: int,
    hidden_width: int,
) -> list[HyperNeatSubstrateNodeIR]:
    nodes: list[HyperNeatSubstrateNodeIR] = []
    nid = 0
    for y in _ys(n_in):
        nodes.append(HyperNeatSubstrateNodeIR(id=nid, kind="input", x=-1.0, y=y))
        nid += 1
    for layer in range(hidden_layers):
        x = -1.0 + 2.0 * (layer + 1) / (hidden_layers + 1)
        for y in _ys(hidden_width):
            nodes.append(HyperNeatSubstrateNodeIR(id=nid, kind="hidden", x=x, y=y))
            nid += 1
    for y in _ys(n_out):
        nodes.append(HyperNeatSubstrateNodeIR(id=nid, kind="output", x=1.0, y=y))
        nid += 1
    return nodes


def _express_substrate(
    neat: Any,
    genome: Any,
    config: Any,
    nodes: list[HyperNeatSubstrateNodeIR],
    threshold: float,
    feed_forward: bool,
) -> list[NeatConnectionIR]:
    if feed_forward:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
    else:
        net = neat.nn.RecurrentNetwork.create(genome, config)
    expressed: list[NeatConnectionIR] = []
    for src in nodes:
        for tgt in nodes:
            if src.x >= tgt.x:
                continue
            raw = float(net.activate((src.x, src.y, tgt.x, tgt.y))[0])
            if not math.isfinite(raw):
                continue
            if abs(raw) < threshold:
                continue
            expressed.append(
                NeatConnectionIR(
                    source=src.id,
                    target=tgt.id,
                    weight=raw,
                    enabled=True,
                    innovation=None,
                )
            )
    return expressed


def _sigmoid(value: float) -> float:
    if value >= 20.0:
        return 1.0
    if value <= -20.0:
        return 0.0
    return float(1.0 / (1.0 + math.exp(-value)))


def _forward(
    nodes: list[HyperNeatSubstrateNodeIR],
    connections: list[NeatConnectionIR],
    features: tuple[float, ...],
    n_out: int,
) -> list[float]:
    incoming: dict[int, list[tuple[int, float]]] = {node.id: [] for node in nodes}
    for conn in connections:
        incoming[conn.target].append((conn.source, conn.weight))
    values: dict[int, float] = {}
    inputs = [node for node in nodes if node.kind == "input"]
    for i, node in enumerate(inputs):
        values[node.id] = float(features[i]) if i < len(features) else 0.0
    for node in sorted(nodes, key=lambda item: (item.x, item.id)):
        if node.kind == "input":
            continue
        total = 0.0
        for src, weight in incoming[node.id]:
            total += values.get(src, 0.0) * weight
        values[node.id] = _sigmoid(total)
    outputs = [node for node in nodes if node.kind == "output"]
    outputs.sort(key=lambda item: item.id)
    if not outputs:
        return [0.0] * n_out
    return [values.get(node.id, 0.0) for node in outputs]


def _score(
    problem: NeatProblemSpec,
    nodes: list[HyperNeatSubstrateNodeIR],
    connections: list[NeatConnectionIR],
    n_out: int,
) -> float:
    if problem.fitness == NeatFitnessName.XOR:
        score = 4.0
        for xs, yt in zip(_XOR_X, _XOR_Y, strict=True):
            pred = _forward(nodes, connections, xs, 1)
            score -= (pred[0] - yt) ** 2
        return float(score)
    assert problem.x is not None and problem.y is not None
    if problem.fitness == NeatFitnessName.TABULAR_REGRESSION:
        err = 0.0
        for row, yt in zip(problem.x, problem.y, strict=True):
            pred = _forward(nodes, connections, tuple(row), 1)
            err += (pred[0] - float(yt)) ** 2
        return float(-err / len(problem.y))
    correct = 0
    for row, yt in zip(problem.x, problem.y, strict=True):
        pred = _forward(nodes, connections, tuple(row), n_out)
        label = (1 if pred[0] >= 0.5 else 0) if n_out == 1 else int(np.argmax(pred))
        if label == int(yt):
            correct += 1
    return float(correct / len(problem.y))


def run_hyperneat(problem: NeatProblemSpec, algorithm: HyperNeatAlgorithmSpec) -> HyperNeatResult:
    """Evolve a CPPN that queries a closed substrate."""
    if algorithm.substrate is not HyperNeatSubstrateName.LAYERED_1D:
        raise ValueError(f"unsupported substrate {algorithm.substrate}")
    neat = _require_neat()
    _seed_all(neat, algorithm.seed)
    n_in, n_out = _io_dims(problem)
    nodes = _layered_1d(n_in, n_out, algorithm.hidden_layers, algorithm.hidden_width)

    with tempfile.TemporaryDirectory(prefix="oec-hyperneat-") as tmp:
        cfg_path = Path(tmp) / "cppn.cfg"
        _write_config(cfg_path, n_inputs=4, n_outputs=1, algo=algorithm)
        # CPPN activations: rewrite the activation lines for HyperNEAT.
        text = cfg_path.read_text(encoding="utf-8")
        old_act = (
            "activation_default      = sigmoid\n"
            "activation_mutate_rate  = 0.0\n"
            "activation_options      = sigmoid"
        )
        new_act = (
            "activation_default      = tanh\n"
            "activation_mutate_rate  = 0.1\n"
            "activation_options      = sigmoid tanh gauss sin"
        )
        cfg_path.write_text(text.replace(old_act, new_act), encoding="utf-8")
        config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            str(cfg_path),
        )
        n_eval = 0
        history: list[float] = []

        def eval_genomes(genomes: list[Any], cfg: Any) -> None:
            nonlocal n_eval
            best = -math.inf
            for _gid, genome in genomes:
                n_eval += 1
                expressed = _express_substrate(
                    neat,
                    genome,
                    cfg,
                    nodes,
                    algorithm.weight_threshold,
                    algorithm.feed_forward,
                )
                fit = _score(problem, nodes, expressed, n_out)
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

    expressed = _express_substrate(
        neat,
        winner,
        config,
        nodes,
        algorithm.weight_threshold,
        algorithm.feed_forward,
    )
    cppn = _genotype_ir(winner, n_inputs=4, n_outputs=1, feed_forward=algorithm.feed_forward)
    substrate = HyperNeatSubstrateIR(
        name=algorithm.substrate.value,
        nodes=tuple(nodes),
        connections=tuple(expressed),
        n_inputs=n_in,
        n_outputs=n_out,
        hidden_layers=algorithm.hidden_layers,
        hidden_width=algorithm.hidden_width,
        weight_threshold=algorithm.weight_threshold,
    )
    best_fit = float(winner.fitness) if winner.fitness is not None else float(history[-1])
    return HyperNeatResult(
        backend="neat-python",
        backend_version=_neat_version(),
        algorithm="hyperneat",
        seed=algorithm.seed,
        fitness=problem.fitness.value,
        best_fitness=best_fit,
        cppn=cppn,
        substrate=substrate,
        n_cppn_nodes=len(cppn.nodes),
        n_substrate_connections=len(expressed),
        n_species=n_species,
        n_evaluations=n_eval,
        n_generations=len(history),
        history_best=history,
        problem_fingerprint=problem_fingerprint(
            {
                **problem.model_dump(mode="json"),
                "substrate": algorithm.substrate.value,
                "hidden_layers": algorithm.hidden_layers,
                "hidden_width": algorithm.hidden_width,
                "weight_threshold": algorithm.weight_threshold,
            }
        ),
        message="ok",
    )
