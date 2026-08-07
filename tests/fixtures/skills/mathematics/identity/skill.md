---
id: mathematics.identity
version: 0.1.0
status: experimental
domain: mathematics
title: Identity
---

# Purpose

A minimal, deterministic skill that returns its numeric input unchanged.
It exists solely as a fixture to exercise the Skill Loader, Skill
Registry, and CLI during Sprint 01 — it is not part of OEC's engineering
skill catalog (see section 14 of the master plan for the real MVP
skills) and carries no methodology of its own.

# Problem definition

Given a single real number, return that same number.

# Supported problem classes

- Passing a real number through unchanged.

# Required inputs

- `value` (number): the input to return.

# Optional inputs

None.

# Units and dimensions

Dimensionless by design — this fixture predates the units engine
(Sprint 02) and intentionally avoids taking a position on physical
quantities.

# Official methodology

Identity function: `f(x) = x`.

# Mathematical formulation

`output.value = input.value`

# Assumptions

- The input is a finite real number.

# Conventions

None.

# Applicability limits

None — defined for all finite real numbers.

# Validation rules

- `value` must be present and numeric (enforced by `input.schema.json`).

# Numerical diagnostics

Not applicable; no numerical method is involved.

# Alternative methods

None.

# Failure conditions

None under normal operation.

# Worked examples

Input `{"value": 42}` → output `{"value": 42}`.

# References

None — this is a loader fixture, not an engineering skill.

# Known limitations

Not a real skill; do not use as a template for engineering skills without
adding methodology, units, golden cases, and references.

# Changelog

- 0.1.0: initial fixture for Sprint 01 loader/registry tests.
