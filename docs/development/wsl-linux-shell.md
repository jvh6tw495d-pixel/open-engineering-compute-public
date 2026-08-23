# OEC local Linux shell (WSL Ubuntu)

This is a **dev terminal**, not POST-OEC, TITAN, PyPI publishing, or
Unsloth-in-the-OEC-venv.

Windows PowerShell is fine for editing. GPU JAX wheels, Axolotl, and a lot of
scientific Linux wheels belong in Ubuntu. This machine already has
**Ubuntu 24.04 WSL2** with an **RTX 3070**.

Do **not** use the default WSL distro (`docker-desktop`). Always pin
`-d Ubuntu-24.04`. This Ubuntu currently logs in as **root** and Windows
sometimes leaks a broken `HOME` (`C:Usersjoaop` or `/mnt/c/Users/...`).
The launcher forces `HOME=/root` from PowerShell and **fail-closes** on a
Windows drive-mount HOME.

`oec[jax]` is **CPU jaxlib on every platform**, including this Ubuntu extra.
CUDA JAX is a **WSL overlay**, opt-in via `-CudaJax`, then **sticky** (stamp
`$HOME/.oec-wsl/cuda12`). `-CpuJax` unsticks it. CUDA must **not** enter the
`oec[jax]` extra in `pyproject.toml`.

Architecture IR JAX is a **correctness backend** (no `jit`; conv is loops;
GNN / attention / FNO stay torch-only). WSL is for CUDA wheels and Axolotl,
not because “JAX is missing on Windows”.

## Enter the shell (from Windows)

```powershell
cd C:\tmp\oec-3.6-integration
.\scripts\oec-wsl.ps1
```

Always `-d Ubuntu-24.04`. The `.ps1` clears `WSLENV`, sets `HOME=/root`, and
derives `OEC_ROOT` from `$PSScriptRoot` (the repo that contains `scripts/`).

First run:

```powershell
.\scripts\oec-wsl.ps1 -SetupOnly
```

Then, optional CUDA overlay (sticky after this):

```powershell
.\scripts\oec-wsl.ps1 -CudaJax -SetupOnly
```

Daily enter skips `uv sync` when `$HOME/.oec-wsl/venv` already imports `oec`.
Sync uses `uv sync --frozen --inexact` so CUDA plugins survive. Refresh with
`-ForceSync` / `OEC_WSL_FORCE_SYNC=1`. `OEC_WSL_UNLOCK=1` omits `--frozen`.

One-shot pytest (no interactive bash):

```powershell
.\scripts\oec-wsl.ps1 -Command "pytest tests/unit/test_neural_architecture_zip_leftovers.py"
.\scripts\oec-wsl.ps1 pytest tests/unit/test_neural_architecture_zip_leftovers.py
```

Default pytest `addopts` deselects `-m neural`. Run the zip-leftovers file or
`pytest -m neural` explicitly.

`-CudaJax` and `-CpuJax` together is an error.

## Direct WSL

The bash script derives `OEC_ROOT` from `BASH_SOURCE` (no hardcoded machine
path). You **must** set a Linux `HOME` (or let a leaked `C:Users...` remap to
`/root`). A HOME under `/mnt/c/...` is rejected.

```powershell
wsl -d Ubuntu-24.04 -- /bin/bash -lc "export HOME=/root; bash /mnt/c/tmp/oec-3.6-integration/scripts/oec-wsl.sh"
```

Do not invoke `wsl -d Ubuntu-24.04 -- bash scripts/oec-wsl.sh` without
`HOME=/root`. That is how Windows HOME leaks in.

## What it installs

Linux `uv` (pinned **0.12.5** x86_64 ELF into `$HOME/.local/bin`; never
`uv.exe` from `/mnt/c`). Then a Linux-side venv at `$HOME/.oec-wsl/venv`
(not `$OEC_ROOT/.venv`):

`uv sync --frozen --inexact --extra neural --extra evolutionary --extra jax`

Unsloth stays out of the OEC venv. Axolotl is optional via
`oec learning bootstrap --axolotl` **inside this Ubuntu**, not from
PowerShell. Axolotl env root: `$HOME/.local/share/oec-learning-envs`.

Add `foundation` with extras (Linux env, then force a sync):

```powershell
wsl -d Ubuntu-24.04 -- /bin/bash -lc "export HOME=/root OEC_WSL_EXTRAS=neural,evolutionary,jax,foundation OEC_WSL_FORCE_SYNC=1; bash /mnt/c/tmp/oec-3.6-integration/scripts/oec-wsl.sh"
```

The repo stays the Windows tree under `/mnt/c/...` so edits in this worktree
are what Linux runs. PATH inside the shell is Linux-only
(`$VENV/bin`, `$HOME/.local/bin`, `/usr/local/bin`, `/usr/bin`, `/bin`,
`/usr/sbin`, `/sbin`).

## Distro hardening (out of git)

Optional machine steps; the launcher still pins `-d Ubuntu-24.04`:

- Create a normal (non-root) Linux user and log in as that user.
- In `/etc/wsl.conf`, set `appendWindowsPath=false` under `[interop]` so
  Windows PATH cannot leak even before the launcher rewrites `PATH`.

This remains a **dev terminal**. Do not publish or upload from this shell.
