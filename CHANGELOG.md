# Changelog

All notable changes to Open Engineering Compute are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-25

### Added

- Skill Engine: loader, registry, lifecycle, manifests (`skill.yaml` + `skill.md`)
- Engineering kernel: units (Pint), numerics, optimization
- Validation engine: schema, dimensional, mathematical, physical helpers, numerical, invariants, golden cases
- Execution pipeline with subprocess sandbox, provenance, graded status (ADR 0007)
- Central dimensional normalization (ADR 0016)
- Public surfaces: Python SDK, CLI (`oec`), REST API (`/v1`), MCP server
- MVP mathematics skills (6): solve_root, interpolate, integrate, optimize_scalar, optimize_constrained, curve_fit
- MVP electrical skills (6): three_phase_power, current_from_power, voltage_drop, power_factor_correction, transformer_loading, per_unit_conversion
- Optional integrations: Odysseus (MCP host config) and Open Science (Method Change Proposal)
- Public Alpha preparation scripts and security/community docs

### Notes

- Private incubation history is not the public history (ADR 0008).
- REST/MCP ship without auth in Alpha (ADR 0015).
