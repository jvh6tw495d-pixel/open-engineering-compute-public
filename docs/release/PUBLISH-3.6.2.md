# Publish OEC 3.6.2 to PyPI — **DEFERRED**

**Do not upload.** Owner parked PyPI. `v3.6.2` is a git tag only.
Resume only with an explicit ask plus `UV_PUBLISH_TOKEN`.

This runbook supersedes `PUBLISH-3.6.1.md` for the 3.6.2 cut. Artifact
names below are **3.6.2 only**.

The PyPI **project** name is `open-engineering-compute` (`oec` is taken).
The import package and CLI stay `oec`.

## Preconditions

- [x] `[project].name = "open-engineering-compute"` in `pyproject.toml`
- [x] `[project].version = "3.6.2"`
- [x] `src/oec/__init__.py` reports `3.6.2` via
      `importlib.metadata.version("open-engineering-compute")` (fallback
      `"3.6.2"`)
- [ ] Working tree is clean on the release commit/tag
- [ ] Explicit owner ask + `UV_PUBLISH_TOKEN`

## Build

```powershell
uv lock
uv build
```

Must produce `dist/open_engineering_compute-3.6.2-py3-none-any.whl`.

```powershell
uv venv .venv-publish-check
uv pip install --python .venv-publish-check dist/open_engineering_compute-3.6.2-py3-none-any.whl
.venv-publish-check\Scripts\oec.exe version
```

`oec version` **must print exactly** `3.6.2`. Also:

```powershell
.venv-publish-check\Scripts\python.exe -c "import oec; assert oec.__version__ == '3.6.2'"
```

## Upload (blocked while DEFERRED)

```powershell
uv publish
# or
uv run twine upload dist/open_engineering_compute-3.6.2*
```

Do not glob `3.6.1`.

## Do not

- Do not upload while this runbook is **DEFERRED**.
- Do not `pip install oec` expecting this project.
- Do not move tags `v3.6.0-scientific-ai` or `v3.6.1`.
- Do not vendor TITAN.
