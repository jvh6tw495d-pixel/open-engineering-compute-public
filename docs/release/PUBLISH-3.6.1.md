# Publish OEC 3.6.1 to PyPI (human)

Short runbook. `oec` is **already taken** on PyPI (Observatory for Economic
Complexity, PyPI user `yahiaali`, `0.3.0`) — the PyPI **project** name for
this package is `open-engineering-compute`. The **import package** stays
`oec` (`import oec`, `from oec.sdk import Engine`), and the installed CLI
script stays `oec`. Only the name typed into `pip install ...` changes.

## Preconditions

- [x] `[project].name = "open-engineering-compute"` in `pyproject.toml`
      (`[tool.hatch.build.targets.wheel] packages = ["src/oec"]` unchanged)
- [x] `[project.urls]` Homepage/Repository point at the public GitHub mirror
- [ ] `CHANGELOG.md` has a dated `## [3.6.1]` entry (already present for this
      release — bump the version + add a new entry for future releases)
- [ ] Working tree is clean on the release commit/tag
- [ ] You have a PyPI API token for the `open-engineering-compute` project
      (`~/.pypirc` or `UV_PUBLISH_TOKEN` / `TWINE_PASSWORD` env var)

## Build

```powershell
uv lock
uv build
```

This produces `dist/open_engineering_compute-3.6.1-py3-none-any.whl` and the
matching sdist. Confirm the wheel exists and installs correctly before
uploading:

```powershell
uv venv .venv-publish-check
uv pip install --python .venv-publish-check dist/open_engineering_compute-3.6.1-py3-none-any.whl
.venv-publish-check\Scripts\oec.exe version
```

The installed console script is still `oec` — only the artifact/project name
changed.

## Upload

Pick one. Both authenticate against the `open-engineering-compute` PyPI
project, not `oec`.

```powershell
# uv
uv publish

# or twine
uv run twine upload dist/open_engineering_compute-3.6.1*
```

## Install (what users run)

```bash
pip install open-engineering-compute
pip install 'open-engineering-compute[foundation]'   # extras keep their names
```

`import oec` and the `oec` CLI command are unaffected by the PyPI project
rename.

## Do not

- Do not `pip install oec` expecting this project — that PyPI name belongs to
  a different, unrelated package.
- Do not rename the import package (`src/oec`) or the CLI script (`oec`).
- Do not upload from a dirty working tree or a commit that isn't tagged.
