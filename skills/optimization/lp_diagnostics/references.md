# References — optimization.lp_diagnostics

1. HiGHS — https://highs.dev/ — the highspy APIs `allVarDuals` /
   `allRowValue` / `allConstrDuals` used here to surface reduced costs,
   slacks, and duals of the solve result. OEC only translates structured
   inputs and maps solver status, it does not reimplement the solver
   (ADR 0008).
2. Chvatal, V. (1983). *Linear Programming*. W. H. Freeman, Chapter 5 —
   the KKT optimality report (primal feasibility, dual feasibility,
   complementary slackness) that this skill surfaces in a structured
   shape.
3. Closed-form sanity reference (golden case below): the min-cost diet
   LP from Chvatal §3.1 with the known optimal vertex (Dantzig's example)
   has zero reduced cost on basic variables; derivable independently of
   any HiGHS call by hand-checking the basic system.
