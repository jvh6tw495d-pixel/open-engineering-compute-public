"""Metric helpers (numpy) for neural evaluation."""

from __future__ import annotations

import math

import numpy as np


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = (1.0 if ss_res == 0.0 else 0.0) if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    if not math.isfinite(r2):
        r2 = 0.0
    return {"mae": mae, "rmse": rmse, "r_squared": r2}


def classification_metrics(
    y_true: np.ndarray, y_pred_labels: np.ndarray, n_classes: int
) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=int).reshape(-1)
    y_pred_labels = np.asarray(y_pred_labels, dtype=int).reshape(-1)
    acc = float(np.mean(y_true == y_pred_labels))
    # macro-F1
    f1s: list[float] = []
    for c in range(n_classes):
        tp = float(np.sum((y_true == c) & (y_pred_labels == c)))
        fp = float(np.sum((y_true != c) & (y_pred_labels == c)))
        fn = float(np.sum((y_true == c) & (y_pred_labels != c)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1s.append(0.0 if (prec + rec) == 0 else 2 * prec * rec / (prec + rec))
    return {"accuracy": acc, "f1_macro": float(np.mean(f1s)) if f1s else 0.0}
