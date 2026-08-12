"""Closed-catalog distribution evaluations (SciPy). Merit: SciPy.stats."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from scipy import stats

from oec.errors import NumericalDomainError

DistributionName = Literal["norm", "t", "uniform", "expon", "chi2", "beta"]
OperationName = Literal["pdf", "cdf", "ppf", "mean", "std", "sample"]

_SUPPORTED: frozenset[str] = frozenset({"norm", "t", "uniform", "expon", "chi2", "beta"})
_OPS: frozenset[str] = frozenset({"pdf", "cdf", "ppf", "mean", "std", "sample"})


def _build_dist(name: str, params: dict[str, float]) -> Any:
    if name == "norm":
        return stats.norm(loc=float(params.get("loc", 0.0)), scale=float(params.get("scale", 1.0)))
    if name == "t":
        if "df" not in params:
            raise NumericalDomainError("distribution 't' requires params.df", details=params)
        return stats.t(
            df=float(params["df"]),
            loc=float(params.get("loc", 0.0)),
            scale=float(params.get("scale", 1.0)),
        )
    if name == "uniform":
        # SciPy uniform: [loc, loc+scale]
        return stats.uniform(
            loc=float(params.get("loc", 0.0)), scale=float(params.get("scale", 1.0))
        )
    if name == "expon":
        return stats.expon(loc=float(params.get("loc", 0.0)), scale=float(params.get("scale", 1.0)))
    if name == "chi2":
        if "df" not in params:
            raise NumericalDomainError("distribution 'chi2' requires params.df", details=params)
        return stats.chi2(
            df=float(params["df"]),
            loc=float(params.get("loc", 0.0)),
            scale=float(params.get("scale", 1.0)),
        )
    if name == "beta":
        if "a" not in params or "b" not in params:
            raise NumericalDomainError(
                "distribution 'beta' requires params.a and params.b", details=params
            )
        return stats.beta(
            a=float(params["a"]),
            b=float(params["b"]),
            loc=float(params.get("loc", 0.0)),
            scale=float(params.get("scale", 1.0)),
        )
    raise NumericalDomainError(
        f"unsupported distribution {name!r}; allowed: {sorted(_SUPPORTED)}",
        details={"distribution": name},
    )


def evaluate_distribution(
    *,
    distribution: str,
    operation: str,
    params: dict[str, float] | None = None,
    x: float | list[float] | None = None,
    p: float | list[float] | None = None,
    n_samples: int = 1,
    seed: int | None = None,
) -> dict[str, Any]:
    """Evaluate a closed-catalog SciPy distribution operation.

    * ``pdf`` / ``cdf`` require ``x``
    * ``ppf`` requires ``p`` in [0, 1]
    * ``mean`` / ``std`` ignore x/p
    * ``sample`` uses ``n_samples`` and optional ``seed``
    """
    name = str(distribution).lower()
    op = str(operation).lower()
    if name not in _SUPPORTED:
        raise NumericalDomainError(
            f"unsupported distribution {distribution!r}; allowed: {sorted(_SUPPORTED)}",
            details={"distribution": distribution},
        )
    if op not in _OPS:
        raise NumericalDomainError(
            f"unsupported operation {operation!r}; allowed: {sorted(_OPS)}",
            details={"operation": operation},
        )

    params = {str(k): float(v) for k, v in (params or {}).items()}
    # Basic scale positivity for common cases
    if "scale" in params and params["scale"] <= 0:
        raise NumericalDomainError("params.scale must be > 0", details=params)
    if name == "t" and params.get("df", 1.0) <= 0:
        raise NumericalDomainError("params.df must be > 0 for t", details=params)
    if name == "chi2" and params.get("df", 1.0) <= 0:
        raise NumericalDomainError("params.df must be > 0 for chi2", details=params)
    if name == "beta" and (params.get("a", 1.0) <= 0 or params.get("b", 1.0) <= 0):
        raise NumericalDomainError("params.a and params.b must be > 0 for beta", details=params)

    dist = _build_dist(name, params)
    out: dict[str, Any] = {
        "distribution": name,
        "operation": op,
        "params": params,
        "backend": "scipy.stats",
    }

    if op in {"pdf", "cdf"}:
        if x is None:
            raise NumericalDomainError(f"operation {op!r} requires 'x'")
        xs = np.atleast_1d(np.asarray(x, dtype=float))
        values = dist.pdf(xs) if op == "pdf" else dist.cdf(xs)
        out["values"] = [float(v) for v in np.atleast_1d(values)]
        if xs.size == 1:
            out["value"] = out["values"][0]
        return out

    if op == "ppf":
        if p is None:
            raise NumericalDomainError("operation 'ppf' requires 'p'")
        ps = np.atleast_1d(np.asarray(p, dtype=float))
        if np.any(ps < 0.0) or np.any(ps > 1.0):
            raise NumericalDomainError("p must be in [0, 1]", details={"p": p})
        values = dist.ppf(ps)
        out["values"] = [float(v) for v in np.atleast_1d(values)]
        if ps.size == 1:
            out["value"] = out["values"][0]
        return out

    if op == "mean":
        out["value"] = float(dist.mean())
        return out

    if op == "std":
        out["value"] = float(dist.std())
        return out

    # sample
    if n_samples < 1:
        raise NumericalDomainError("n_samples must be >= 1", details={"n_samples": n_samples})
    rng = np.random.default_rng(seed)
    samples = dist.rvs(size=int(n_samples), random_state=rng)
    out["samples"] = [float(v) for v in np.atleast_1d(samples)]
    out["n_samples"] = int(n_samples)
    out["seed"] = seed
    return out
