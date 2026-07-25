"""The single, shared Pint unit registry used across the kernel.

Pint quantities built from two different ``UnitRegistry`` instances are
not comparable or convertible, even if they represent the exact same
units — a well-documented Pint pitfall. To keep unit handling
deterministic (plan section 4.2), the whole kernel must build every
:class:`pint.Quantity` from this one instance rather than constructing
``pint.UnitRegistry()`` ad hoc elsewhere.

This does not yet curate which units are allowed — it uses Pint's
default unit set as-is, including units no engineering skill will ever
need. Curating an explicit allow-list is deferred until real skills
(Sprint 04+) reveal which units actually matter; see
``docs/architecture/adr/0011-single-shared-pint-registry.md``.
"""

from __future__ import annotations

import pint

ureg: pint.UnitRegistry = pint.UnitRegistry()  # type: ignore[type-arg]

# Reactive power uses the same physical dimension as watt / volt-ampere.
# Pint does not ship a ``var`` unit; electrical skills need it as both an
# accepted input label (convertible via ADR 0016) and an output unit string.
# Defining it once on the shared registry (ADR 0011) keeps every Quantity
# built from this instance comparable.
ureg.define("var = watt")
