# OEC Learning — how optional backends are installed

**Rule:** calling Unsloth, Axolotl, or ART **never downloads or pip-installs
anything**. A missing package raises `BackendNotAvailableError` with the
exact install command. A core `pip install oec` only has contracts.

The PyPI package `art` is the **wrong** package (ASCII-art). ART is
`openpipe-art`. Unsloth must not share the OEC venv. Axolotl is Linux/WSL
only.

Foundation-model distillation is **out of this cut** (owner decision pending).

## What you get with a core install

```text
import oec.learning          # always works
ARTBackend().train(...)      # BackendNotAvailableError — does not pip install
UnslothBackend().finetune()  # same
AxolotlBackend().finetune()  # same
```

## Reference path (same venv as OEC)

```bash
uv sync --extra foundation    # Hugging Face LoRA / PEFT
uv sync --extra neural        # tabular neural.distill_mlp only
```

## ART / GRPO — OpenPipe ART, not PyPI `art`

The import name is `art`. The **PyPI name is `openpipe-art`**.

```bash
uv pip install "openpipe-art==0.5.18"
```

```bash
# WRONG — ASCII-art library, same import name, no train_grpo
pip install art
```

If you already installed the wrong package:

```bash
uv pip uninstall art
uv pip install "openpipe-art==0.5.18"
```

## Unsloth — isolated venv (never the OEC project venv)

Unsloth resolves on Windows but **downgrades torch 2.13→2.11 and
transformers 5.15→5.5**. That breaks `oec[neural]` / `oec[foundation]`.

```powershell
$py = "$env:LOCALAPPDATA\oec-learning-envs\unsloth\Scripts\python.exe"
uv venv "$env:LOCALAPPDATA\oec-learning-envs\unsloth" --python 3.12
uv pip install --python $py "unsloth==2026.8.18"
# Run Learning Unsloth calls with that interpreter. OEC does not
# auto-switch interpreters and does not read an env var for this.
```

## Axolotl — Linux or WSL only

Native Windows cannot install Axolotl (`triton` has no `win_amd64` wheel).
Do not use `pip install axolotl --no-deps`.

```bash
# inside WSL/Ubuntu
uv venv ~/.local/share/oec-learning-envs/axolotl --python 3.12
uv pip install --python ~/.local/share/oec-learning-envs/axolotl/bin/python axolotl
```

## Tests

```bash
uv run pytest tests/unit/test_learning_l1_l5.py tests/unit/test_learning_store.py
uv run pytest -m learning_smoke -o addopts= --no-cov    # needs foundation+neural
uv run pytest -m learning_adapter -o addopts= --no-cov  # fail-closed unless extras exist
```
