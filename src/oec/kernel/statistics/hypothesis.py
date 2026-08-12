"""Closed-catalog hypothesis tests (SciPy). Merit: SciPy.stats."""

from __future__ import annotations

from typing import Any, Literal, cast

import numpy as np
from scipy import stats

from oec.errors import NumericalDomainError

TestName = Literal["t_one_sample", "t_two_sample", "ks_1samp", "mannwhitney"]
AlternativeName = Literal["two-sided", "less", "greater"]

_TESTS: frozenset[str] = frozenset({"t_one_sample", "t_two_sample", "ks_1samp", "mannwhitney"})
_ALTS: frozenset[str] = frozenset({"two-sided", "less", "greater"})


def _as_float_array(name: str, values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or arr.size < 1:
        raise NumericalDomainError(f"{name} must be a non-empty 1-D array")
    if not np.all(np.isfinite(arr)):
        raise NumericalDomainError(f"{name} must contain only finite values")
    return arr


def run_hypothesis_test(
    *,
    test: str,
    sample: list[float] | None = None,
    sample_a: list[float] | None = None,
    sample_b: list[float] | None = None,
    popmean: float = 0.0,
    equal_var: bool = True,
    alternative: str = "two-sided",
    # ks_1samp reference distribution (closed)
    reference_distribution: str = "norm",
    reference_params: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run a closed-catalog hypothesis test via SciPy.

    Returns statistic, pvalue, and metadata. Does not invent significance claims
    beyond SciPy's numbers.
    """
    name = str(test).lower()
    alt_raw = str(alternative).lower()
    if name not in _TESTS:
        raise NumericalDomainError(
            f"unsupported test {test!r}; allowed: {sorted(_TESTS)}",
            details={"test": test},
        )
    if alt_raw not in _ALTS:
        raise NumericalDomainError(
            f"unsupported alternative {alternative!r}; allowed: {sorted(_ALTS)}",
            details={"alternative": alternative},
        )
    alt = cast(AlternativeName, alt_raw)

    result: dict[str, Any] = {
        "test": name,
        "alternative": alt,
        "backend": "scipy.stats",
    }

    if name == "t_one_sample":
        if sample is None:
            raise NumericalDomainError("t_one_sample requires 'sample'")
        x = _as_float_array("sample", sample)
        if x.size < 2:
            raise NumericalDomainError("t_one_sample requires at least 2 observations")
        t_res = stats.ttest_1samp(x, popmean=float(popmean), alternative=alt)
        result.update(
            {
                "statistic": float(t_res.statistic),
                "pvalue": float(t_res.pvalue),
                "df": float(x.size - 1),
                "popmean": float(popmean),
                "n": int(x.size),
            }
        )
        return result

    if name == "t_two_sample":
        if sample_a is None or sample_b is None:
            raise NumericalDomainError("t_two_sample requires 'sample_a' and 'sample_b'")
        a = _as_float_array("sample_a", sample_a)
        b = _as_float_array("sample_b", sample_b)
        if a.size < 2 or b.size < 2:
            raise NumericalDomainError("t_two_sample requires at least 2 observations per sample")
        t2_res = stats.ttest_ind(a, b, equal_var=bool(equal_var), alternative=alt)
        result.update(
            {
                "statistic": float(t2_res.statistic),
                "pvalue": float(t2_res.pvalue),
                "equal_var": bool(equal_var),
                "n_a": int(a.size),
                "n_b": int(b.size),
            }
        )
        return result

    if name == "mannwhitney":
        if sample_a is None or sample_b is None:
            raise NumericalDomainError("mannwhitney requires 'sample_a' and 'sample_b'")
        a = _as_float_array("sample_a", sample_a)
        b = _as_float_array("sample_b", sample_b)
        mw_res = stats.mannwhitneyu(a, b, alternative=alt)
        result.update(
            {
                "statistic": float(mw_res.statistic),
                "pvalue": float(mw_res.pvalue),
                "n_a": int(a.size),
                "n_b": int(b.size),
            }
        )
        return result

    # ks_1samp — reference is closed catalog (norm default)
    if sample is None:
        raise NumericalDomainError("ks_1samp requires 'sample'")
    x = _as_float_array("sample", sample)
    ref = str(reference_distribution).lower()
    params = {str(k): float(v) for k, v in (reference_params or {}).items()}
    if ref == "norm":
        loc = float(params.get("loc", 0.0))
        scale = float(params.get("scale", 1.0))
        if scale <= 0:
            raise NumericalDomainError("reference_params.scale must be > 0")
        cdf = stats.norm(loc=loc, scale=scale).cdf
        ref_meta = {"distribution": "norm", "loc": loc, "scale": scale}
    elif ref == "uniform":
        loc = float(params.get("loc", 0.0))
        scale = float(params.get("scale", 1.0))
        if scale <= 0:
            raise NumericalDomainError("reference_params.scale must be > 0")
        cdf = stats.uniform(loc=loc, scale=scale).cdf
        ref_meta = {"distribution": "uniform", "loc": loc, "scale": scale}
    else:
        raise NumericalDomainError(
            f"unsupported reference_distribution {reference_distribution!r}; "
            "allowed: ['norm', 'uniform']",
            details={"reference_distribution": reference_distribution},
        )

    ks_res = stats.kstest(x, cdf, alternative=alt)
    result.update(
        {
            "statistic": float(ks_res.statistic),
            "pvalue": float(ks_res.pvalue),
            "n": int(x.size),
            "reference": ref_meta,
        }
    )
    return result
