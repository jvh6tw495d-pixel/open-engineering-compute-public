"""Thin per-backend probes (ADR 0021).

Each adapter module exposes ``BACKEND_NAME: str`` and
``probe() -> tuple[bool, str | None, str | None]`` (available, version,
reason) — no shared base class, no dependency on `registry.py`'s model, so
`registry.py` can import these without any circularity. These are
capability *availability* probes only; the capability *domains* a backend
declares live in `oec.backends.capabilities`, kept separate on purpose.
"""
