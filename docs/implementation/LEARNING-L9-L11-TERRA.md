# Learning L9-L11 Terra review

L9-L11 now provide core-safe RL data contracts, a lazy ART/GRPO adapter, and
deterministic, verifier-only domain rewards.  ART is deliberately not a core
dependency: a missing or incompatible ART installation raises the Learning
backend-availability error rather than selecting another backend.

## Remaining L12-L15 gaps

- **L12:** no end-to-end scientific or Python-worker RL demonstration yet; one
  must exercise a verifier environment, trajectory collection, ART, evaluation,
  and reproducible experiment record.
- **L13:** no durable backend capability registry or agentic metric suite yet;
  add permanent benchmark/golden sets before making backend-quality claims.
- **L14:** CI does not install/test the ART extra, discover optional RL
  capabilities, resume interrupted runs, or validate RL artifact integrity.
- **L15:** release/operational closure remains: documentation, migration and
  support policy, and a reproducible acceptance matrix have not been defined.
