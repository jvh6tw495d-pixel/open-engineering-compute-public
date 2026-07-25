---
id: electrical.transformer_loading
version: 0.1.0
status: experimental
domain: electrical
title: Transformer Loading
---

# Purpose

Compute a transformer's operating loading percent, headroom, and an
overload warning from its nameplate apparent-power rating and either
an operating apparent power or an operating current on the same
winding.

# Problem definition

Given `S_rated` and either `S_load` or `(I_load, I_rated)`, compute
`loading_percent = 100 · S_load / S_rated`, `headroom = S_rated −
S_load`, and whether loading meets/exceeds a threshold (default 100%).

# Supported problem classes

- Load given as apparent power.
- Load given as current (ratio to rated current on the same winding).

# Required inputs

- `rated_apparent_power` (`QuantityValue`, `x-oec-unit: "W"`).
- `load_type` (`apparent_power` | `current`).

Conditionally required:

- `load_apparent_power` iff `load_type: apparent_power`.
- `load_current` and `rated_current` iff `load_type: current`.

# Optional inputs

- `overload_threshold_percent` (number `> 0`, default `100`).

# Units and dimensions

Canonical conversion via ADR 0016. Outputs report apparent power in
`VA` (same dimension as `W`).

# Official methodology

Closed-form loading ratio; no thermal model.

# Mathematical formulation

```
S_load = load_apparent_power                         (load_type=apparent_power)
S_load = S_rated · (I_load / I_rated)                 (load_type=current)
loading_percent = 100 · S_load / S_rated
headroom        = S_rated − S_load
overload_warning = loading_percent >= threshold
```

# Assumptions

- Continuous RMS loading ratio only — not a thermal or loss-of-life
  study (IEEE C57.91 ambient/history factors are out of scope).
- Current path assumes `load_current` and `rated_current` are on the
  same winding at the same voltage base.

# Conventions

`headroom` is signed: negative means overloaded.

# Applicability limits

- No harmonic derating, no ambient temperature, no cooling-class
  multipliers.
- No multi-winding cross-loading.

# Validation rules

- Cross-field presence for `load_type`.
- Positivity of all power/current magnitudes and threshold.

# Numerical diagnostics

`diagnostics` is always `{}`.

# Alternative methods

IEEE C57.91 aging/thermal loading would be a separate future skill.

# Failure conditions

- Missing/extra load fields → `INVALID`.
- Non-positive magnitudes → `INVALID`.

# Worked examples

See `examples/`.

# References

See `references.md`.

# Known limitations

- Ratio only; not a thermal model.

# Changelog

- 0.1.0: initial version (Sprint 09).
