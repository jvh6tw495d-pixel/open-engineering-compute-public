# Contributing to Open Engineering Compute

Thank you for considering a contribution. OEC is **skill-first**:
changes to methodology belong in versioned skills with tests, not in
silent interface logic.

## SciPy and numerical credit

OEC applies **governance** (contracts, validation, provenance, interfaces)
around numerical engines — primarily **SciPy**. Do **not** present wrappers
as novel OEC algorithms. Skill docs and `references.md` must attribute the
upstream SciPy/NumPy entry points. See
[docs/concepts/mathematical-engine-and-governance.md](docs/concepts/mathematical-engine-and-governance.md).

## Development setup

```bash
uv sync --all-extras
uv run pre-commit install
uv run pytest
uv run ruff check .
uv run mypy
```

## Skill contributions

New skills must follow the package layout under `skills/`:

- `skill.yaml` + `skill.md`
- `input.schema.json` / `output.schema.json` (use `x-oec-unit` for physical quantities)
- `implementation.py` (deterministic; no unit conversion — ADR 0016)
- `validation.py` (skill-specific checks; reuse `oec.validation.physical` helpers)
- `references.md`, `examples/`, golden + property tests

Open Science **Method Change Proposals**
(`integrations/open_science/`) are the preferred path for methodology
changes to published skills. Stable skills are never auto-mutated.

## Code style

- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`)
- Ruff format/lint; mypy strict on `src/oec`
- Prefer small, reviewable PRs

## What not to include

- Private product names, client data, proprietary formulations (ADR 0008)
- Secrets, credentials, absolute machine-specific paths in committed files
- Dependencies that force the core to require optional integrations

## License

By contributing, you agree that your contributions are licensed under
the project's Apache-2.0 license (see `LICENSE`).
