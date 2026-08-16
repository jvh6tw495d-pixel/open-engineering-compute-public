"""User-facing install hints for optional Learning backends.

OEC never auto-installs these packages. Calling a backend without them
fails closed with these messages. Operators install explicitly.
"""

from __future__ import annotations

ART_PYPI = "openpipe-art==0.5.18"
ART_IMPORT = "art"
ART_WRONG_PYPI = "art"
UNSLOTH_PIN = "unsloth==2026.8.18"
GUIDE = "docs/release/LEARNING-OPERATIONAL.md"

ART_MISSING = (
    "ART/GRPO is not auto-installed. Install OpenPipe ART explicitly: "
    f"uv pip install '{ART_PYPI}'. "
    f"Import name is '{ART_IMPORT}'. "
    f"Do not install the PyPI package '{ART_WRONG_PYPI}' (ASCII-art library). "
    f"See {GUIDE}."
)

ART_WRONG_PACKAGE = (
    "The installed 'art' module has no train_grpo. "
    f"You likely installed the wrong PyPI package '{ART_WRONG_PYPI}'. "
    f"Uninstall it and run: uv pip install '{ART_PYPI}'. "
    f"See {GUIDE}."
)

UNSLOTH_MISSING = (
    "Unsloth is not auto-installed and must not be added to the OEC project venv "
    f"(it downgrades torch/transformers). Create an isolated venv and install "
    f"'{UNSLOTH_PIN}' there, then run OEC with that interpreter. "
    f"See {GUIDE}."
)

AXOLOTL_MISSING = (
    "Axolotl is not auto-installed and cannot be installed on native Windows "
    "(depends on Linux-only triton wheels). Use WSL or Linux with an isolated "
    "venv. Do not pip install axolotl into the OEC venv with --no-deps. "
    f"See {GUIDE}."
)

HF_MISSING = (
    "Hugging Face training requires the optional extra oec[foundation] "
    "(transformers+peft). It is not pulled by a core install: "
    f"uv sync --extra foundation. See {GUIDE}."
)


def hint_for(backend: str) -> str:
    """Return the fail-closed install message for a named backend."""
    mapping = {
        "art": ART_MISSING,
        "unsloth": UNSLOTH_MISSING,
        "axolotl": AXOLOTL_MISSING,
        "huggingface": HF_MISSING,
    }
    return mapping.get(
        backend,
        "Optional Learning backend is not auto-installed. See " + GUIDE + ".",
    )
