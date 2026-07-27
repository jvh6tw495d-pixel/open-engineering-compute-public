# References — optimization.infeasibility_explain

1. HiGHS — https://highs.dev/ — the feasibility-only "zero objective" solve
   this skill uses. OEC only translates structured inputs and maps solver
   status (ADR 0008).
2. Chinneck, J. W. (2008). *Feasibility and Infeasibility in
   Optimization*. Springer — the IIS heuristic this skill approximates:
   the drop-one sensitivity scan for the simplest possible IIS candidate
   set. A polynomial-time extraction is a v2.4 candidate.
3. Closed-form sanity references (golden cases below): the bound-conflict
   case (`x` with `lower = 1 > upper = 0`) makes the LP infeasible before
   any solve; derivable by direct inspection of the bound pairs.