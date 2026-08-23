# OEC local Linux shell (WSL Ubuntu)

This is a **dev terminal**, not the POST-OEC research harness.

Windows PowerShell is fine for editing. GPU JAX, Axolotl, and a lot of
scientific wheels behave better in Linux. This machine already has
**Ubuntu 24.04 WSL2** with the **RTX 3070** visible (`nvidia-smi`).

Do **not** use the default WSL distro (`docker-desktop`). Always `-d Ubuntu-24.04`.
This Ubuntu currently logs in as **root** and Windows sometimes leaks a broken
`HOME` (`C:Usersjoaop`). The launcher forces `HOME=/root`.

## Enter the shell (from Windows)

```powershell
cd C:\tmp\oec-3.6-integration
.\scripts\oec-wsl.ps1
```

First run installs `uv` under Linux `$HOME/.local` (forced to `/root` because
this Ubuntu image currently has a broken Windows-leaked `HOME`) and syncs a
**Linux-side venv** at `~/.oec-wsl/venv`. The repo stays the Windows tree
(`/mnt/c/tmp/oec-3.6-integration`) so edits in this worktree are what Linux
runs.

Setup only (no interactive bash):

```powershell
.\scripts\oec-wsl.ps1 -SetupOnly
```

JAX **CUDA** (Linux wheels; does not belong in `oec[jax]` on Windows):

```powershell
.\scripts\oec-wsl.ps1 -CudaJax
```

Inside the shell you should see `jax.devices()` include `cuda:0` after that.

## What it installs

`uv sync --extra neural --extra evolutionary --extra jax`

Unsloth still stays out of the OEC venv. Axolotl is optional via
`oec learning bootstrap --axolotl` **inside this Ubuntu**, not from PowerShell.

## Direct WSL

```bash
wsl -d Ubuntu-24.04 -- bash /mnt/c/tmp/oec-3.6-integration/scripts/oec-wsl.sh
```
