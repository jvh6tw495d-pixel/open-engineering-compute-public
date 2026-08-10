---
id: neural.mlp.regressor
version: 0.1.0
---

# MLP Regressor (PyTorch)

Supervised multilayer perceptron regression. **Merit owner: PyTorch.**
OEC provides the skill contract, seeds, fingerprints, and governance
(ADR 0031). Requires `uv sync --extra neural`.

## Inputs

- `x`: feature matrix
- `y`: continuous targets
- hyperparameters: `hidden_dims`, `epochs`, `lr`, `seed`, …

## Outputs

Training metrics, normalization params, and a JSON-serializable checkpoint
for `neural.predict` / `neural.evaluate`.

## Notes

- Stochastic: set `seed` for reproducibility (`deterministic_status` reported).
- Not a physics conservation claim.
