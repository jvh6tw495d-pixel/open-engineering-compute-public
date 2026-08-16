# OEC Learning — operational surface

**Branch:** `feat/learning-l1-l5`
**Meaning of operational:** a caller can run the path without monkeypatch and
without invented metrics. Missing extras fail closed.

## Operational now (reference path)

| Path | Extra | How to run |
|------|--------|------------|
| Contracts, persist, replay, rewards | none (core) | `pytest tests/unit/test_learning_*.py` |
| Hugging Face LoRA / adapter chain | `oec[foundation]` | `pytest -m learning_smoke` |
| Tabular distill (`teacher_checkpoint`) | `oec[neural]` | `pytest -m learning_smoke` |
| Worker FineTune sequence + `ExecutionResult` evaluate | foundation for live train | `WorkerPipeline.run()` |

## Operational when the external package is installed

These are **not** default CI extras (`--all-extras` is an explicit list of
api/mcp/optimization/neural/evolutionary/foundation only).

| Adapter | Install | Test |
|---------|---------|------|
| Unsloth | `pip install unsloth` | `pytest -m learning_adapter` |
| Axolotl | `pip install axolotl` | `pytest -m learning_adapter` |
| ART | the GRPO `art` package that exposes `train_grpo` | `pytest -m learning_adapter` |

Absent package → `BackendNotAvailableError`. Present but API mismatch → same error.

## Not in this operational cut

- Kronos / temporal FMs
- POST-OEC harness
- Foundation-model (text) distillation
- Declaring Unsloth/Axolotl/ART better than HF without a measured suite
