"""SymPy backend adapter — hard runtime dependency (core)."""

from __future__ import annotations

BACKEND_NAME = "sympy"


def probe() -> tuple[bool, str | None, str | None]:
    try:
        import sympy
    except ImportError as exc:
        return False, None, str(exc)
    return True, sympy.__version__, None
