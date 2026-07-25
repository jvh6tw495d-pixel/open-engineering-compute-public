# Open Science integration (optional)

Methodological review workflow for OEC skills: critique → **Method
Change Proposal** → experimental implementation → benchmarks → **human
review** → new skill version.

The OEC **core does not depend** on this folder. Open Science never
alters a skill with status `stable` automatically (handbook §15.2).

## Layout

```text
integrations/open_science/
├── README.md
├── proposal.schema.json   # Method Change Proposal JSON Schema
├── export.py              # create a proposal from a registered skill
├── import_proposal.py     # validate / import (no auto-write of skills)
├── workflow.py            # human review state transitions
├── examples/
└── tests/
```

## Flow

```text
Evidence or critique
        ↓
Method Change Proposal
        ↓
Experimental implementation   (human, new experimental version)
        ↓
Benchmark and golden tests
        ↓
Human review
        ↓
New skill version
```

## Quick start

```bash
# Export a draft proposal against a real skill
uv run python integrations/open_science/export.py \
  --skill-id mathematics.solve_root \
  --skills-root skills \
  --proposal-id mcp-2026-001 \
  --title "Document bracket preference more clearly" \
  --summary "Clarify default method selection when a bracket is supplied." \
  --rationale "Reviewers asked for an explicit statement of the brentq default." \
  --change-kind methodology \
  --change-description "Expand skill.md Official methodology section." \
  --author "reviewer@example.org" \
  --out integrations/open_science/examples/generated-draft.json

# Validate / import (never writes skill packages)
uv run python integrations/open_science/import_proposal.py \
  integrations/open_science/examples/sample_proposal.json \
  --skills-root skills
```

## Stable-skill guard

If the target skill's lifecycle status is `stable`:

- proposals may be filed and reviewed;
- `import_proposal --apply` is **always refused** in Alpha;
- even with `--human-approved`, this tool **does not rewrite** stable
  packages — a human must land a new experimental version out of band.

## Success criteria (Sprint 10 / Fase 8)

- [x] `proposal.schema.json` defined
- [x] export + import tools
- [x] review workflow transitions
- [x] examples + tests
- [x] core installs without this integration
- [x] stable skills cannot be auto-mutated
