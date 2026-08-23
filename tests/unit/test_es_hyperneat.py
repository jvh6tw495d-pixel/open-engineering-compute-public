"""ES-HyperNEAT is Gauci & Stanley, not a diagonal-presence quadtree (ADR 0048)."""

from __future__ import annotations

import pytest

from oec.evolutionary.contracts import (
    HyperNeatAlgorithmSpec,
    HyperNeatSubstrateName,
)
from oec.evolutionary.results import HyperNeatSubstrateIR, HyperNeatSubstrateNodeIR
from oec.kernel.evolutionary.hyperneat import _es_express


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "max_depth": 3,
        "variance_threshold": 0.03,
        "band_threshold": 0.05,
        "weight_threshold": 0.2,
        "max_hidden": 16,
        "max_iteration": 1,
    }
    base.update(overrides)
    return base


def _hidden_xy(
    nodes: list[HyperNeatSubstrateNodeIR],
) -> list[tuple[float, float]]:
    return [(node.x, node.y) for node in nodes if node.kind == "hidden"]


def _peak(tx0: float, ty0: float, radius: float = 0.08):
    """Thin isolated peak at a depth-2 quadtree centre (band survives pruning)."""

    def query(sx: float, sy: float, tx: float, ty: float) -> float:
        del sy
        if tx <= sx:
            return 0.0
        if abs(tx - tx0) < radius and abs(ty - ty0) < radius:
            return 0.9
        return 0.0

    return query


def test_diagonal_presence_is_not_how_hidden_are_discovered() -> None:
    """Old heuristic queried CPPN(x,y,x,y). That is identically 0 here."""
    query = _peak(0.25, 0.25)
    nodes, conns, _n_iter = _es_express(query, 1, 1, **_kwargs())
    assert query(0.25, 0.25, 0.25, 0.25) == 0.0
    assert query(-0.25, -0.25, -0.25, -0.25) == 0.0
    hidden = _hidden_xy(nodes)
    assert hidden, "hidden must come from 4D extraction, not the diagonal"
    assert any(abs(x - 0.25) < 0.15 and abs(y - 0.25) < 0.15 for x, y in hidden)
    assert conns


def test_per_source_trees_depend_on_source_coordinates() -> None:
    nodes_lo, _, _ = _es_express(_peak(0.25, -0.75), 1, 1, **_kwargs())
    nodes_hi, _, _ = _es_express(_peak(0.25, 0.75), 1, 1, **_kwargs())
    ys_lo = [y for _x, y in _hidden_xy(nodes_lo)]
    ys_hi = [y for _x, y in _hidden_xy(nodes_hi)]
    assert ys_lo and ys_hi
    assert sum(ys_lo) / len(ys_lo) < 0.0
    assert sum(ys_hi) / len(ys_hi) > 0.0


def test_two_inputs_at_opposite_y_extract_different_hidden() -> None:
    def query(sx: float, sy: float, tx: float, ty: float) -> float:
        if tx <= sx:
            return 0.0
        target_y = 0.75 if sy > 0.0 else -0.75
        if abs(tx - 0.25) < 0.08 and abs(ty - target_y) < 0.08:
            return 0.9
        return 0.0

    nodes, _conns, _n_iter = _es_express(query, 2, 1, **_kwargs())
    hidden = _hidden_xy(nodes)
    assert hidden
    assert min(y for _x, y in hidden) < 0.0
    assert max(y for _x, y in hidden) > 0.0


def test_uniform_field_is_band_pruned() -> None:
    def flat(_sx: float, _sy: float, _tx: float, _ty: float) -> float:
        return 0.9

    _n_flat, conns_flat, _ = _es_express(flat, 1, 1, **_kwargs(band_threshold=0.3))
    _n_peak, conns_peak, _ = _es_express(_peak(0.25, 0.25), 1, 1, **_kwargs(band_threshold=0.3))
    assert conns_flat == []
    assert conns_peak, "a thin band must survive pruning that kills a flat field"


def test_iteration_grows_hidden_to_the_right() -> None:
    def query(sx: float, sy: float, tx: float, ty: float) -> float:
        del sy
        if abs(ty - 0.25) > 0.08:
            return 0.0
        dx = tx - sx
        on_chain = abs(tx + 0.25) < 0.08 or abs(tx - 0.25) < 0.08 or abs(tx - 0.75) < 0.08
        if on_chain and 0.4 <= dx <= 0.9:
            return 0.9
        return 0.0

    nodes_1, _, n_iter_1 = _es_express(query, 1, 1, **_kwargs(max_iteration=1))
    nodes_2, _, n_iter_2 = _es_express(query, 1, 1, **_kwargs(max_iteration=2))
    xs_1 = [x for x, _y in _hidden_xy(nodes_1)]
    xs_2 = [x for x, _y in _hidden_xy(nodes_2)]
    assert n_iter_1 >= 1
    assert n_iter_2 >= n_iter_1
    assert xs_1
    assert max(xs_2) > max(xs_1)
    assert len(xs_2) > len(xs_1)


def test_max_hidden_cap_is_enforced() -> None:
    def query(sx: float, sy: float, tx: float, ty: float) -> float:
        del sy
        if tx <= sx:
            return 0.0
        gx = round((tx - 0.25) / 0.5) * 0.5 + 0.25
        gy = round((ty - 0.25) / 0.5) * 0.5 + 0.25
        if abs(tx - gx) < 0.08 and abs(ty - gy) < 0.08:
            return 0.9
        return 0.0

    nodes, _conns, _ = _es_express(query, 2, 1, **_kwargs(max_hidden=4, max_iteration=3))
    assert len(_hidden_xy(nodes)) <= 4


def test_es_ir_rejects_layered_width_fields() -> None:
    with pytest.raises(ValueError, match="must not set hidden_layers"):
        HyperNeatSubstrateIR(
            name="es_quadtree",
            kind="es_hyperneat",
            extraction="gauci_quadtree",
            nodes=(),
            connections=(),
            n_inputs=2,
            n_outputs=1,
            hidden_layers=0,
            hidden_width=3,
            actual_hidden=0,
            weight_threshold=0.2,
            max_depth=3,
            band_threshold=0.3,
        )


def test_hyperneat_rejects_recurrent_cppn() -> None:
    with pytest.raises(ValueError, match="feed_forward"):
        HyperNeatAlgorithmSpec(feed_forward=False)
    with pytest.raises(ValueError, match="feed_forward"):
        HyperNeatAlgorithmSpec(
            substrate=HyperNeatSubstrateName.ES_QUADTREE,
            feed_forward=False,
        )
