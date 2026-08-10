"""Graph neural nets in pure PyTorch (N5) — no PyG/DGL dependency.

Message-passing GCN / GraphSAGE / GAT for node-level regression or
classification. Merit: PyTorch; OEC governs contracts (ADR 0032).
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.metrics import classification_metrics, regression_metrics
from oec.kernel.neural.seeding import torch_version
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint

GnnArch = Literal["gcn", "graphsage", "gat"]


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as functional
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn, functional


def _normalize_adj(torch: Any, edge_index: Any, n_nodes: int) -> Any:
    """Symmetric normalized adjacency with self-loops (GCN)."""
    row, col = edge_index[0], edge_index[1]
    # add self loops
    loops = torch.arange(n_nodes, device=edge_index.device)
    row = torch.cat([row, loops])
    col = torch.cat([col, loops])
    ones = torch.ones(row.shape[0], device=edge_index.device)
    deg = torch.zeros(n_nodes, device=edge_index.device).scatter_add_(0, row, ones)
    deg_inv_sqrt = deg.clamp(min=1).pow(-0.5)
    values = deg_inv_sqrt[row] * deg_inv_sqrt[col]
    with torch.sparse.check_sparse_tensor_invariants(False):
        adj = torch.sparse_coo_tensor(
            torch.stack([row, col]), values, (n_nodes, n_nodes)
        ).coalesce()
    return adj


def build_gnn(
    arch: GnnArch,
    in_dim: int,
    *,
    hidden: int = 32,
    n_layers: int = 2,
    output_dim: int = 1,
    heads: int = 2,
    dropout: float = 0.0,
) -> Any:
    torch, nn, functional = _require_torch()

    class GCNLayer(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self, din: int, dout: int) -> None:
            super().__init__()
            self.lin = nn.Linear(din, dout)

        def forward(self, x: Any, adj: Any) -> Any:
            support = self.lin(x)
            return torch.sparse.mm(adj, support)

    class SAGELayer(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self, din: int, dout: int) -> None:
            super().__init__()
            self.lin_self = nn.Linear(din, dout)
            self.lin_nei = nn.Linear(din, dout)

        def forward(self, x: Any, adj: Any) -> Any:
            nei = torch.sparse.mm(adj, x)
            return self.lin_self(x) + self.lin_nei(nei)

    class GATLayer(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self, din: int, dout: int, heads: int) -> None:
            super().__init__()
            self.heads = heads
            self.dout = dout
            self.lin = nn.Linear(din, dout * heads, bias=False)
            self.attn = nn.Parameter(torch.empty(1, heads, 2 * dout))
            nn.init.xavier_uniform_(self.attn)

        def forward(self, x: Any, edge_index: Any) -> Any:
            # edge_index without forced self loops for simplicity; add them
            n = x.size(0)
            loops = torch.arange(n, device=x.device)
            row = torch.cat([edge_index[0], loops])
            col = torch.cat([edge_index[1], loops])
            h = self.lin(x).view(n, self.heads, self.dout)
            h_i = h[row]
            h_j = h[col]
            cat = torch.cat([h_i, h_j], dim=-1)
            e = (cat * self.attn).sum(dim=-1)
            e = functional.leaky_relu(e, 0.2)
            # softmax per destination
            e = e - e.max()
            exp_e = e.exp()
            denom = torch.zeros(n, self.heads, device=x.device)
            denom = denom.scatter_add_(0, col.unsqueeze(-1).expand_as(exp_e), exp_e)
            alpha = exp_e / denom[col].clamp(min=1e-9)
            out = torch.zeros(n, self.heads, self.dout, device=x.device)
            out = out.scatter_add_(
                0,
                col.unsqueeze(-1).unsqueeze(-1).expand(-1, self.heads, self.dout),
                h_i * alpha.unsqueeze(-1),
            )
            return out.mean(dim=1)

    class GNN(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__()
            self.arch = arch
            self.layers = nn.ModuleList()
            dims = [in_dim] + [hidden] * (n_layers - 1) + [output_dim]
            for i in range(len(dims) - 1):
                din, dout = dims[i], dims[i + 1]
                if arch == "gcn":
                    self.layers.append(GCNLayer(din, dout))
                elif arch == "graphsage":
                    self.layers.append(SAGELayer(din, dout))
                else:
                    self.layers.append(GATLayer(din, dout, heads=heads))
            self.dropout = dropout

        def forward(self, x: Any, edge_index: Any, adj: Any | None = None) -> Any:
            h = x
            for i, layer in enumerate(self.layers):
                if self.arch == "gat":
                    h = layer(h, edge_index)
                else:
                    assert adj is not None
                    h = layer(h, adj)
                if i < len(self.layers) - 1:
                    h = functional.relu(h)
                    if self.dropout > 0:
                        h = functional.dropout(h, p=self.dropout, training=self.training)
            return h

    return GNN()


def train_gnn(
    node_features: Any,
    edge_index: Any,
    y: Any,
    *,
    train_mask: list[bool] | None = None,
    arch: GnnArch = "gcn",
    task: Literal["regression", "classification"] = "regression",
    n_classes: int = 1,
    hidden: int = 32,
    n_layers: int = 2,
    heads: int = 2,
    epochs: int = 80,
    lr: float = 1e-2,
    seed: int = 42,
    device: str = "cpu",
    dropout: float = 0.0,
    runtime: Any | None = None,
    capacity: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    from oec.kernel.neural.runtime import (
        count_parameters,
        enforce_max_params,
        fit_fullbatch,
        prepare_device_and_seeds,
        save_checkpoint,
    )
    from oec.neural.contracts import DeviceSpec, OptimizerName, OptimizerSpec
    from oec.neural.runtime import TrainingRuntimeSpec

    torch, nn, _functional = _require_torch()
    del _functional
    x = np.asarray(node_features, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("node_features must be 2D [n_nodes, feats]")
    n_nodes, in_dim = x.shape
    edges = np.asarray(edge_index, dtype=np.int64)
    if edges.ndim != 2 or edges.shape[0] != 2:
        raise ValueError("edge_index must be shape [2, n_edges]")
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    if y_arr.shape[0] != n_nodes:
        raise ValueError("y must have one label/value per node")
    if train_mask is None:
        mask = np.ones(n_nodes, dtype=bool)
    else:
        mask = np.asarray(train_mask, dtype=bool)
        if mask.shape[0] != n_nodes:
            raise ValueError("train_mask length mismatch")

    out_dim = 1 if task == "regression" or n_classes == 2 else n_classes
    rt: TrainingRuntimeSpec = runtime or TrainingRuntimeSpec(
        seed=seed,
        device=DeviceSpec(device=device),
        epochs=epochs,
        batch_size=max(n_nodes, 1),
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=lr),
        early_stopping_patience=None,
    )
    resolved, det = prepare_device_and_seeds(rt)
    model = build_gnn(
        arch,
        in_dim,
        hidden=hidden,
        n_layers=n_layers,
        output_dim=out_dim,
        heads=heads,
        dropout=dropout,
    ).to(resolved)
    n_params = count_parameters(model)
    enforce_max_params(n_params, rt.max_params)

    if task == "regression":
        crit: Any = nn.MSELoss()
    elif n_classes == 2:
        crit = nn.BCEWithLogitsLoss()
    else:
        crit = nn.CrossEntropyLoss()

    x_t = torch.tensor(x, dtype=torch.float32, device=resolved)
    e_t = torch.tensor(edges, dtype=torch.long, device=resolved)
    adj = None if arch == "gat" else _normalize_adj(torch, e_t, n_nodes)
    mask_t = torch.tensor(mask, dtype=torch.bool, device=resolved)
    if task == "regression" or n_classes == 2:
        y_t = torch.tensor(y_arr, dtype=torch.float32, device=resolved).view(-1, 1)
    else:
        y_t = torch.tensor(y_arr, dtype=torch.long, device=resolved)

    def _loss_fn() -> Any:
        pred = model(x_t, e_t, adj)
        if task == "classification" and n_classes > 2:
            return crit(pred[mask_t], y_t[mask_t])
        return crit(pred[mask_t], y_t[mask_t].view_as(pred[mask_t]))

    history, epochs_ran = fit_fullbatch(model, _loss_fn, crit, rt, device=resolved)

    model.eval()
    with torch.no_grad():
        pred = model(x_t, e_t, adj).cpu().numpy()
    y_m = y_arr[mask]
    p_m = pred[mask]
    if task == "regression":
        metrics = regression_metrics(y_m, p_m.reshape(-1))
    elif n_classes == 2:
        labels = (1 / (1 + np.exp(-p_m.reshape(-1))) >= 0.5).astype(int)
        metrics = classification_metrics(y_m.astype(int), labels, 2)
    else:
        labels = np.argmax(p_m, axis=1)
        metrics = classification_metrics(y_m.astype(int), labels, n_classes)

    spec = {
        "architecture": arch,
        "in_dim": in_dim,
        "hidden": hidden,
        "n_layers": n_layers,
        "output_dim": out_dim,
        "heads": heads,
        "dropout": dropout,
        "task": task,
        "n_classes": n_classes,
        "n_nodes": n_nodes,
        "n_edges": int(edges.shape[1]),
    }
    meta = {
        "architecture": arch,
        "model_spec": spec,
        "task": f"gnn_{task}",
        "n_params": n_params,
        "capacity": capacity,
    }
    ckpt, cref = save_checkpoint(
        storage=rt.checkpoint_storage,
        state_dict=model.state_dict(),
        meta=meta,
        run_id=run_id,
    )
    # node_features for fingerprint: use list form
    nf = x.tolist() if hasattr(x, "tolist") else node_features
    return {
        "task": f"gnn_{task}",
        "backend": "torch",
        "backend_version": torch_version(),
        "device": resolved,
        "seed": rt.seed,
        "deterministic_status": det,
        "epochs_ran": epochs_ran,
        "train_metrics": metrics,
        "history": history[-5:],
        "checkpoint": ckpt,
        "checkpoint_ref": cref.model_dump(mode="json"),
        "n_train": int(mask.sum()),
        "n_params": n_params,
        "capacity": capacity,
        "runtime": {
            "lr_scheduler": rt.lr_scheduler,
            "grad_clip": rt.grad_clip,
            "amp": rt.amp,
            "max_params": rt.max_params,
            "checkpoint_storage": rt.checkpoint_storage,
        },
        "dataset_fingerprint": dataset_fingerprint(nf, y_arr.tolist()),
        "model_fingerprint": model_spec_fingerprint(spec),
        "arch": arch,
    }
