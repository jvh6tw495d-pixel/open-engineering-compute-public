"""Math IR (Mathematical Intermediate Representation) — v0 foundation.

See ``docs/architecture/adr/0020-math-ir-foundation.md``. This package
represents problems without depending on a specific solver: a versioned,
closed set of Pydantic models (:mod:`oec.modeling.ir`) compiled to existing
governed backends (OPS/HiGHS for ``linear_program``, SciPy root-finding for
``scalar_root``) by :mod:`oec.modeling.compile_linear` and
:mod:`oec.modeling.compile_scalar_root`. It introduces no new solver logic
of its own.
"""
