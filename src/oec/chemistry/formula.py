"""Elemental formula parsing and molar mass (IUPAC conventional masses).

Masses are conventional engineering values sufficient for mass-balance
bookkeeping — not a full isotopic library.
"""

from __future__ import annotations

import re

from oec.chemistry.errors import ChemistryEvaluationError

# Conventional atomic masses (g/mol) — subset used in engineering examples
ATOMIC_MASS_G_PER_MOL: dict[str, float] = {
    "H": 1.00794,
    "C": 12.0107,
    "N": 14.0067,
    "O": 15.9994,
    "F": 18.9984,
    "Na": 22.9897,
    "Mg": 24.3050,
    "Al": 26.9815,
    "Si": 28.0855,
    "P": 30.9738,
    "S": 32.065,
    "Cl": 35.453,
    "K": 39.0983,
    "Ca": 40.078,
    "Fe": 55.845,
    "Cu": 63.546,
    "Zn": 65.38,
    "Br": 79.904,
    "I": 126.904,
}

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")


def parse_formula(formula: str) -> dict[str, int]:
    """Parse a simple formula string without parentheses, e.g. ``H2O``, ``CO2``.

    Nested groups ``(OH)2`` are **not** supported in v0.
    """
    s = formula.strip()
    if not s:
        raise ChemistryEvaluationError("formula string must be non-empty")
    if "(" in s or ")" in s:
        raise ChemistryEvaluationError(
            "parenthesized formula groups are not supported in v0",
            details={"formula": formula},
        )
    pos = 0
    out: dict[str, int] = {}
    for match in _TOKEN.finditer(s):
        if match.start() != pos:
            raise ChemistryEvaluationError(
                f"could not parse formula near {s[pos:]!r}",
                details={"formula": formula},
            )
        el = match.group(1)
        count_s = match.group(2)
        count = int(count_s) if count_s else 1
        if count <= 0:
            raise ChemistryEvaluationError(
                f"invalid atom count for {el}",
                details={"formula": formula},
            )
        out[el] = out.get(el, 0) + count
        pos = match.end()
    if pos != len(s):
        raise ChemistryEvaluationError(
            f"trailing unparsed formula text {s[pos:]!r}",
            details={"formula": formula},
        )
    if not out:
        raise ChemistryEvaluationError("formula produced no elements", details={"formula": formula})
    return out


def molar_mass_g_per_mol(formula: dict[str, int]) -> float:
    """Molar mass from elemental map using :data:`ATOMIC_MASS_G_PER_MOL`."""
    if not formula:
        raise ChemistryEvaluationError("empty formula for molar mass")
    total = 0.0
    for el, n in formula.items():
        if el not in ATOMIC_MASS_G_PER_MOL:
            raise ChemistryEvaluationError(
                f"unknown element {el!r} for molar mass (extend ATOMIC_MASS_G_PER_MOL)",
                details={"element": el},
            )
        if n <= 0:
            raise ChemistryEvaluationError(f"invalid count for {el}")
        total += ATOMIC_MASS_G_PER_MOL[el] * n
    return total


def formula_to_string(formula: dict[str, int]) -> str:
    """Canonical Hill-like string (C, H, then alphabetical) for simple maps."""
    if not formula:
        return ""
    parts: list[str] = []
    for el in ("C", "H"):
        if el in formula:
            n = formula[el]
            parts.append(el if n == 1 else f"{el}{n}")
    for el in sorted(k for k in formula if k not in {"C", "H"}):
        n = formula[el]
        parts.append(el if n == 1 else f"{el}{n}")
    return "".join(parts)


__all__ = [
    "ATOMIC_MASS_G_PER_MOL",
    "formula_to_string",
    "molar_mass_g_per_mol",
    "parse_formula",
]
