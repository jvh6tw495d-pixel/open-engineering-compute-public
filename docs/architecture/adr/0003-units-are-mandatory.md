# ADR 0003: Physical quantities are never bare floats

- **Status:** accepted
- **Date:** 2026-07-24

## Context

Engineering bugs caused by unit mismatches (kW vs. W, V vs. kV, degrees vs.
radians) are common, silent, and expensive — they don't raise exceptions,
they produce a confidently wrong number. A framework whose stated purpose
is numerically consistent, auditable engineering results cannot allow a
physical quantity to travel through the system as an undecorated `float`.

## Decision

Every physical quantity crossing a skill boundary (inputs, outputs,
intermediate normalized values) is represented as an explicit
value+unit pair, publicly serialized as:

```json
{ "value": 75, "unit": "kW" }
```

Internally, the Engineering Kernel uses a units engine (Pint) to normalize,
convert, and validate dimensional compatibility before any numerical method
runs. Incompatible units fail validation with a structured error
(`oec.errors.OECValidationError`); they are never silently coerced. The
quantity's original unit, as submitted, is preserved in the execution's
provenance even after normalization.

This ADR does not implement the units engine itself — that is Sprint 02
(Engineering Kernel). It fixes the contract that later sprints must honor.

## Consequences

- No skill implementation may accept or return a bare `float` for a
  physical quantity in its public schema.
- Two callers submitting the same physical quantity in different but
  compatible units (e.g. `380 V` vs. `0.38 kV`) must get the same
  normalized result.
- Dimensionless numbers (counts, ratios, power factor) are explicitly
  exempt and remain plain numbers — this ADR governs physical quantities,
  not all numeric input.
