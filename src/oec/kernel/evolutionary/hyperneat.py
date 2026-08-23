"""Governed HyperNEAT / ES-HyperNEAT: NEAT-evolved CPPN + closed substrate (ADR 0045/0048)."""

from __future__ import annotations

import math
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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

QueryFn = Callable[[float, float, float, float], float]


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


def _variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((item - mean) ** 2 for item in values) / len(values)


def _cppn_activate(net: Any, coords: tuple[float, float, float, float]) -> float:
    """Order-independent CPPN query. Resets recurrent state when present."""
    reset = getattr(net, "reset", None)
    if callable(reset):
        reset()
    raw = float(net.activate(coords)[0])
    return raw if math.isfinite(raw) else 0.0


def _make_cppn(neat: Any, genome: Any, config: Any, feed_forward: bool) -> Any:
    if feed_forward:
        return neat.nn.FeedForwardNetwork.create(genome, config)
    return neat.nn.RecurrentNetwork.create(genome, config)


def _express_substrate(
    neat: Any,
    genome: Any,
    config: Any,
    nodes: list[HyperNeatSubstrateNodeIR],
    threshold: float,
    feed_forward: bool,
) -> list[NeatConnectionIR]:
    net = _make_cppn(neat, genome, config, feed_forward)
    expressed: list[NeatConnectionIR] = []
    for src in nodes:
        for tgt in nodes:
            if src.x >= tgt.x:
                continue
            raw = _cppn_activate(net, (src.x, src.y, tgt.x, tgt.y))
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


@dataclass
class _Quad:
    x: float
    y: float
    width: float
    depth: int
    weight: float = 0.0
    children: tuple[_Quad, ...] = ()


@dataclass
class _TmpNode:
    kind: Literal["input", "hidden", "output"]
    x: float
    y: float
    id: int = -1


def _quant(value: float, max_depth: int) -> float:
    bins = 2**max_depth
    step = 2.0 / float(bins)
    n = round((value + 1.0) / step)
    q = n * step - 1.0
    return max(-1.0, min(1.0, q))


def _build_quadtree(
    sample: Callable[[float, float], float],
    *,
    max_depth: int,
    variance_threshold: float,
    initial_depth: int,
    x: float = 0.0,
    y: float = 0.0,
    width: float = 1.0,
    depth: int = 0,
    weight: float | None = None,
) -> _Quad:
    center = sample(x, y) if weight is None else weight
    offsets = ((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0))
    children: list[_Quad] = []
    for ox, oy in offsets:
        cx = x + ox * width / 2.0
        cy = y + oy * width / 2.0
        cw = width / 2.0
        children.append(_Quad(cx, cy, cw, depth + 1, sample(cx, cy)))
    var = _variance([child.weight for child in children])
    should_split = depth < initial_depth or (
        depth < max_depth and var >= variance_threshold and width > 1e-3
    )
    if should_split:
        children = [
            _build_quadtree(
                sample,
                max_depth=max_depth,
                variance_threshold=variance_threshold,
                initial_depth=initial_depth,
                x=child.x,
                y=child.y,
                width=child.width,
                depth=child.depth,
                weight=child.weight,
            )
            for child in children
        ]
    return _Quad(x, y, width, depth, center, tuple(children))


def _extract_points(
    sample: Callable[[float, float], float],
    node: _Quad,
    *,
    variance_threshold: float,
    band_threshold: float,
    weight_threshold: float,
) -> list[tuple[float, float, float]]:
    found: list[tuple[float, float, float]] = []
    for child in node.children:
        child_var = _variance([gc.weight for gc in child.children]) if child.children else 0.0
        if child.children and child_var >= variance_threshold:
            found.extend(
                _extract_points(
                    sample,
                    child,
                    variance_threshold=variance_threshold,
                    band_threshold=band_threshold,
                    weight_threshold=weight_threshold,
                )
            )
            continue
        weight = child.weight
        left = sample(child.x - child.width, child.y)
        right = sample(child.x + child.width, child.y)
        down = sample(child.x, child.y - child.width)
        up = sample(child.x, child.y + child.width)
        band = max(
            min(abs(weight - up), abs(weight - down)),
            min(abs(weight - left), abs(weight - right)),
        )
        if band > band_threshold and abs(weight) >= weight_threshold:
            found.append((child.x, child.y, weight))
    return found


def _nearest(nodes: list[_TmpNode], x: float, y: float, max_dist: float) -> _TmpNode | None:
    best: _TmpNode | None = None
    best_d = max_dist
    for node in nodes:
        dist = math.hypot(node.x - x, node.y - y)
        if dist <= best_d:
            best = node
            best_d = dist
    return best


def _col_snap(count: int) -> float:
    spacing = 2.0 / max(count - 1, 1) if count > 1 else 1.0
    return 0.5 * spacing + 0.2


def _es_express(
    query: QueryFn,
    n_in: int,
    n_out: int,
    *,
    max_depth: int,
    variance_threshold: float,
    band_threshold: float,
    weight_threshold: float,
    max_hidden: int,
    max_iteration: int,
) -> tuple[list[HyperNeatSubstrateNodeIR], list[NeatConnectionIR], int]:
    """Gauci & Stanley ES-HyperNEAT: per-source quadtree, extraction, band, iterate."""
    inputs = [_TmpNode("input", -1.0, y) for y in _ys(n_in)]
    outputs = [_TmpNode("output", 1.0, y) for y in _ys(n_out)]
    hidden: list[_TmpNode] = []
    hidden_index: dict[tuple[float, float], _TmpNode] = {}
    raw_conns: list[tuple[_TmpNode, _TmpNode, float]] = []
    initial_depth = min(2, max_depth)
    out_snap = _col_snap(n_out)
    in_snap = _col_snap(n_in)

    def outgoing_sample(src: _TmpNode) -> Callable[[float, float], float]:
        def sample(tx: float, ty: float) -> float:
            return query(src.x, src.y, tx, ty)

        return sample

    def resolve_dest(tx: float, ty: float, src: _TmpNode, create: bool) -> _TmpNode | None:
        qx = _quant(tx, max_depth)
        qy = _quant(ty, max_depth)
        if qx >= 0.85:
            return _nearest(outputs, 1.0, qy, out_snap)
        if qx <= -0.95 or qx <= src.x:
            return None
        key = (qx, qy)
        existing = hidden_index.get(key)
        if existing is not None:
            return existing
        if not create or len(hidden) >= max_hidden:
            return None
        node = _TmpNode("hidden", qx, qy)
        hidden.append(node)
        hidden_index[key] = node
        return node

    def extract_outgoing(src: _TmpNode, *, create_hidden: bool) -> list[_TmpNode]:
        sample = outgoing_sample(src)
        tree = _build_quadtree(
            sample,
            max_depth=max_depth,
            variance_threshold=variance_threshold,
            initial_depth=initial_depth,
        )
        new_nodes: list[_TmpNode] = []
        for tx, ty, weight in _extract_points(
            sample,
            tree,
            variance_threshold=variance_threshold,
            band_threshold=band_threshold,
            weight_threshold=weight_threshold,
        ):
            if tx <= src.x:
                continue
            before = len(hidden)
            tgt = resolve_dest(tx, ty, src, create_hidden)
            if tgt is None or tgt is src or tgt.x <= src.x:
                continue
            raw_conns.append((src, tgt, weight))
            if create_hidden and len(hidden) > before and tgt.kind == "hidden":
                new_nodes.append(tgt)
        return new_nodes

    pending: list[_TmpNode] = []
    for src in inputs:
        pending.extend(extract_outgoing(src, create_hidden=True))

    n_iter = 0
    while pending and n_iter < max_iteration:
        n_iter += 1
        nxt: list[_TmpNode] = []
        for src in pending:
            nxt.extend(extract_outgoing(src, create_hidden=True))
        pending = nxt

    for dst in outputs:

        def sample_in(sx: float, sy: float, dest: _TmpNode = dst) -> float:
            return query(sx, sy, dest.x, dest.y)

        tree = _build_quadtree(
            sample_in,
            max_depth=max_depth,
            variance_threshold=variance_threshold,
            initial_depth=initial_depth,
        )
        for sx, sy, weight in _extract_points(
            sample_in,
            tree,
            variance_threshold=variance_threshold,
            band_threshold=band_threshold,
            weight_threshold=weight_threshold,
        ):
            if dst.x <= sx:
                continue
            qx = _quant(sx, max_depth)
            qy = _quant(sy, max_depth)
            origin = (
                _nearest(inputs, -1.0, qy, in_snap) if qx <= -0.85 else hidden_index.get((qx, qy))
            )
            if origin is None or origin.x >= dst.x:
                continue
            raw_conns.append((origin, dst, weight))

    nodes_ir: list[HyperNeatSubstrateNodeIR] = []
    for nid, node in enumerate((*inputs, *hidden, *outputs)):
        node.id = nid
        nodes_ir.append(HyperNeatSubstrateNodeIR(id=nid, kind=node.kind, x=node.x, y=node.y))

    seen: set[tuple[int, int]] = set()
    conns_ir: list[NeatConnectionIR] = []
    for src, tgt, weight in raw_conns:
        key = (src.id, tgt.id)
        if key in seen or src.id == tgt.id:
            continue
        seen.add(key)
        conns_ir.append(
            NeatConnectionIR(
                source=src.id,
                target=tgt.id,
                weight=weight,
                enabled=True,
                innovation=None,
            )
        )
    return nodes_ir, conns_ir, n_iter


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


def _es_kwargs(algorithm: HyperNeatAlgorithmSpec) -> dict[str, Any]:
    return {
        "max_depth": algorithm.es_max_depth,
        "variance_threshold": algorithm.es_variance_threshold,
        "band_threshold": algorithm.es_band_threshold,
        "weight_threshold": algorithm.weight_threshold,
        "max_hidden": algorithm.es_max_hidden,
        "max_iteration": algorithm.es_max_iteration,
    }


def _express_genome(
    neat: Any,
    genome: Any,
    config: Any,
    algorithm: HyperNeatAlgorithmSpec,
    n_in: int,
    n_out: int,
) -> tuple[list[HyperNeatSubstrateNodeIR], list[NeatConnectionIR], int]:
    if algorithm.substrate is HyperNeatSubstrateName.LAYERED_1D:
        nodes = _layered_1d(n_in, n_out, algorithm.hidden_layers, algorithm.hidden_width)
        expressed = _express_substrate(
            neat,
            genome,
            config,
            nodes,
            algorithm.weight_threshold,
            algorithm.feed_forward,
        )
        return nodes, expressed, 0
    if algorithm.substrate is HyperNeatSubstrateName.ES_QUADTREE:
        net = _make_cppn(neat, genome, config, algorithm.feed_forward)

        def query(sx: float, sy: float, tx: float, ty: float) -> float:
            return _cppn_activate(net, (sx, sy, tx, ty))

        nodes, expressed, n_iter = _es_express(query, n_in, n_out, **_es_kwargs(algorithm))
        return nodes, expressed, n_iter
    raise ValueError(f"unsupported substrate {algorithm.substrate}")


def _substrate_ir(
    algorithm: HyperNeatAlgorithmSpec,
    nodes: list[HyperNeatSubstrateNodeIR],
    expressed: list[NeatConnectionIR],
    n_in: int,
    n_out: int,
    n_iterations_used: int,
) -> HyperNeatSubstrateIR:
    n_hidden = sum(1 for node in nodes if node.kind == "hidden")
    if algorithm.substrate is HyperNeatSubstrateName.ES_QUADTREE:
        return HyperNeatSubstrateIR(
            name="es_quadtree",
            kind="es_hyperneat",
            extraction="gauci_quadtree",
            nodes=tuple(nodes),
            connections=tuple(expressed),
            n_inputs=n_in,
            n_outputs=n_out,
            hidden_layers=None,
            hidden_width=None,
            actual_hidden=n_hidden,
            weight_threshold=algorithm.weight_threshold,
            max_depth=algorithm.es_max_depth,
            variance_threshold=algorithm.es_variance_threshold,
            band_threshold=algorithm.es_band_threshold,
            max_iteration=algorithm.es_max_iteration,
            n_iterations_used=n_iterations_used,
        )
    return HyperNeatSubstrateIR(
        name="layered_1d",
        kind="layered_1d",
        extraction="cartesian",
        nodes=tuple(nodes),
        connections=tuple(expressed),
        n_inputs=n_in,
        n_outputs=n_out,
        hidden_layers=algorithm.hidden_layers,
        hidden_width=algorithm.hidden_width,
        actual_hidden=n_hidden,
        weight_threshold=algorithm.weight_threshold,
    )


def run_hyperneat(problem: NeatProblemSpec, algorithm: HyperNeatAlgorithmSpec) -> HyperNeatResult:
    """Evolve a CPPN that queries a closed substrate (fixed or ES-HyperNEAT)."""
    if algorithm.substrate not in HyperNeatSubstrateName:
        raise ValueError(f"unsupported substrate {algorithm.substrate}")
    neat = _require_neat()
    _seed_all(neat, algorithm.seed)
    n_in, n_out = _io_dims(problem)

    with tempfile.TemporaryDirectory(prefix="oec-hyperneat-") as tmp:
        cfg_path = Path(tmp) / "cppn.cfg"
        _write_config(cfg_path, n_inputs=4, n_outputs=1, algo=algorithm)
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
                nodes, expressed, _n_iter = _express_genome(
                    neat, genome, cfg, algorithm, n_in, n_out
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

    nodes, expressed, n_iter = _express_genome(neat, winner, config, algorithm, n_in, n_out)
    cppn = _genotype_ir(winner, n_inputs=4, n_outputs=1, feed_forward=algorithm.feed_forward)
    substrate = _substrate_ir(algorithm, nodes, expressed, n_in, n_out, n_iter)
    best_fit = float(winner.fitness) if winner.fitness is not None else float(history[-1])
    return HyperNeatResult(
        backend="neat-python",
        backend_version=_neat_version(),
        algorithm=(
            "es_hyperneat"
            if algorithm.substrate is HyperNeatSubstrateName.ES_QUADTREE
            else "hyperneat"
        ),
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
                "es_max_depth": algorithm.es_max_depth,
                "es_variance_threshold": algorithm.es_variance_threshold,
                "es_max_hidden": algorithm.es_max_hidden,
                "es_band_threshold": algorithm.es_band_threshold,
                "es_max_iteration": algorithm.es_max_iteration,
            }
        ),
        message="ok",
    )
