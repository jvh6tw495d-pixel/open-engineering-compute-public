# Learning L1-L5 Terra review

**Verdict: PASS WITH HARDENING APPLIED** (2026-08-16)

This review audited the public `oec.learning` surface, ADR 0043, the L1-L5
wave gates, and focused unit coverage. No L6+ behavior was added.

## Findings fixed

1. **Dataset hash could become stale after construction (high).**
   `LearningDataset` is Pydantic-frozen, but its tuple contains mutable Python
   dictionaries. A caller could change a record after `content_hash` was bound
   and train on different content under the original identity. The dataset now
   rechecks its canonical hash before a learning run and before SFT text
   extraction. Hashing now accepts only canonical JSON values; arbitrary-object
   stringification is rejected rather than producing a potentially unstable
   digest.

2. **Foundation optional-extra mapping was name-based (medium).**
   `HuggingFaceBackend` previously inferred missing-extra failures from an
   exception class name. It now explicitly maps the three foundation optional
   dependency errors (Transformers, PEFT, bitsandbytes) to
   `BackendNotAvailableError`, preserving the cause and error type. Other
   training failures still propagate and are not misreported as a missing
   backend.

3. **The run record omitted replay inputs (medium).**
   `LearningRunRecord` now snapshots the full `LearningDataset` and
   `TrainingConfig`, alongside its existing identity fields. This closes the
   L3 hparams/input-record gap without changing backend contracts.

## Gate assessment

| Gate | Result | Evidence |
| --- | --- | --- |
| Core does not import ML/AI packages | Pass | A pristine-process test imports `oec.learning` and verifies no `torch`, `transformers`, `unsloth`, `axolotl`, or `art` module is loaded. |
| No HF types on public API | Pass | `oec.learning.__all__` exposes only OEC models, protocols, functions, and errors; HF imports stay inside the lazy backend method. |
| Dataset identity/integrity | Pass, bounded | Hash covers name/kind/version/split/seed/records; supplied hashes are verified; non-canonical payloads and post-bind mutation are rejected at consumption. |
| HF fail-closed behavior | Pass | Missing foundation extras are translated to the Learning-layer structured error; no fallback backend exists. |
| L1-L5 scope | Pass | Unsloth/Axolotl remain enum values only and fail closed; ART and L6+ are not implemented. |

## Residual limitations (not release blockers for the implemented slice)

- “Frozen” Pydantic contracts remain shallow for nested dictionaries generally.
  Dataset records are protected by consumption-boundary verification; other
  public metadata/details maps retain ordinary Pydantic semantics. Callers must
  treat records and result metadata as value data.
- The wave-plan L2 wording mentions loaders/transforms/lineage. L1-L5 provides
  inline, identifiable dataset contracts, not a persisted dataset loader or a
  transform graph. Do not claim those capabilities until a later, separately
  specified wave adds them.
- A successful real HF training integration test still requires the optional
  Foundation stack and a controlled local model fixture; the deterministic
  unit suite covers isolation and fail-closed behavior without downloads.

## Verification

`uv run pytest tests/unit/test_learning_l1_l5.py tests/unit/test_learning_l1_l5_hardening.py -q`

Result: **12 passed, 1 skipped** (the pre-existing conditional test skips when
Transformers is installed).
