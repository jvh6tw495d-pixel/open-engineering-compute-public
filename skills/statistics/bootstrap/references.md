# References — statistics.bootstrap

1. Efron, B., Tibshirani, R. J. (1993). *An Introduction to the
   Bootstrap*. Chapman & Hall, Chapters 12–13 — the percentile bootstrap
   method this skill implements; no algorithm is reimplemented here.
2. NumPy documentation:
   [`numpy.random.default_rng`](https://numpy.org/doc/stable/reference/random/index.html) —
   the PCG-64 generator used for deterministic resampling when a `seed`
   is supplied.
3. Closed-form sanity reference (used for golden properties): the
   bootstrap CI of the **mean** of a resampled sample must contain the
   sample mean for any non-degenerate seed; derivable from
   Jensen-inequality arguments in Efron & Tibshirani §12.6.