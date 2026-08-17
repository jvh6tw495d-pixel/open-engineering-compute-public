"""User-facing install hints for optional Learning backends.

OEC never auto-installs these packages. Calling a backend without them
fails closed with these messages. Operators install explicitly.
"""

from __future__ import annotations

ART_PYPI = "openpipe-art==0.5.18"
ART_IMPORT = "art"
ART_WRONG_PYPI = "art"
UNSLOTH_PIN = "unsloth==2026.8.18"
AXOLOTL_PIN = "axolotl"
GUIDE = "docs/release/LEARNING-OPERATIONAL.md"
BOOTSTRAP_ALL = "oec learning bootstrap --all"
BOOTSTRAP_ART = "oec learning bootstrap --art"
BOOTSTRAP_UNSLOTH = "oec learning bootstrap --unsloth"
BOOTSTRAP_AXOLOTL = "oec learning bootstrap --axolotl"
BOOTSTRAP_EXTRAS = "oec learning bootstrap --extras"

ART_MISSING = (
    "ART/GRPO is not auto-installed. Install OpenPipe ART explicitly: "
    f"{BOOTSTRAP_ART}  (or: uv pip install '{ART_PYPI}'). "
    f"Import name is '{ART_IMPORT}'. "
    f"Do not install the PyPI package '{ART_WRONG_PYPI}' (ASCII-art library). "
    f"See {GUIDE}."
)

ART_WRONG_PACKAGE = (
    "The installed 'art' module has no train_grpo. "
    f"You likely installed the wrong PyPI package '{ART_WRONG_PYPI}'. "
    f"Uninstall it and run: {BOOTSTRAP_ART}  (or: uv pip install '{ART_PYPI}'). "
    f"See {GUIDE}."
)

UNSLOTH_MISSING = (
    "Unsloth is not auto-installed and must not be added to the OEC project venv "
    f"(it downgrades torch/transformers). Create an isolated venv with "
    f"{BOOTSTRAP_UNSLOTH} (installs '{UNSLOTH_PIN}'), then run OEC with that "
    f"interpreter. See {GUIDE}."
)

AXOLOTL_MISSING = (
    "Axolotl is not auto-installed and cannot be installed on native Windows "
    "(depends on Linux-only triton wheels). On WSL or Linux run "
    f"{BOOTSTRAP_AXOLOTL}. Do not pip install axolotl into the OEC venv with "
    f"--no-deps. See {GUIDE}."
)

HF_MISSING = (
    "Hugging Face training requires the optional extra oec[foundation] "
    "(transformers+peft). It is not pulled by a core install: "
    f"{BOOTSTRAP_EXTRAS}  (or: uv sync --extra foundation). See {GUIDE}."
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
