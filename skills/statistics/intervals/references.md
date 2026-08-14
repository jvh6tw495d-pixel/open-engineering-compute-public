# References — statistics.intervals

1. SciPy documentation:
   [`scipy.stats.t`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html) and
   [`scipy.stats.norm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html) —
   the quantile implementations this skill uses; OEC only translates
   structured inputs.
2. Montgomery, D. C., Runger, G. C. (2018). *Applied Statistics and
   Probability for Engineers*, 7th ed., Wiley, Chapter 8 — the
   confidence-interval formulas for the mean, the Student-t and Gaussian
   variants, and the closed-form symmetric interval construction.
3. Press, W. H. et al. (2007). *Numerical Recipes*, 3rd ed., Chapter 15 —
   arbitrary-precision reference values confirmed against mpmath for the
   golden case (a known sample mean / sample standard deviation with a
   known t-quantile yields a deterministic CI half-width).
