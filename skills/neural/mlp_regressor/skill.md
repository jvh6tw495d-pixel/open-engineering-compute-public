---
id: neural.mlp.regressor
version: 0.1.0
status: experimental
domain: neural
title: MLP Regressor (PyTorch)
---

# MLP Regressor (PyTorch)

Supervised multilayer perceptron regression. **Merit owner: PyTorch.**
OEC provides the skill contract, seeds, fingerprints, and governance
(ADR 0031). Requires `uv sync --extra neural`.

## Inputs

- `x`: feature matrix
- `y`: continuous targets
- `capacity`: optional preset `tiny` | `medium` | `dense` | `wide`
  (expanded to `hidden_dims`; raw `hidden_dims` wins if both set)
- runtime: `epochs`, `lr`, `lr_scheduler`, `grad_clip`, `amp`, `max_params`,
  `checkpoint_storage` (`json_inline` | `file`), `seed`, `device`, …

## Outputs

Training metrics, `n_params`, optional `capacity`, normalization params, and a
checkpoint (`json_inline` state_dict or file path + sha256 under
`OEC_CACHE_DIR`) for `neural.predict` / `neural.evaluate`.

## Notes

- Stochastic: set `seed` for reproducibility (`deterministic_status` reported).
- Dense/wide default to file checkpoints unless `checkpoint_storage` is set.
- Not a physics conservation claim. See
  `docs/implementation/OEC_DENSE_NEURAL_AND_EVO_MATURITY.md` Part A.
