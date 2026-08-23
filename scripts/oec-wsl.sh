#!/usr/bin/env bash
# Local Linux shell for OEC (Ubuntu WSL). Not the POST-OEC research harness.
set -euo pipefail

if [[ "${HOME:-}" != /* ]]; then
  export HOME=/root
fi
export HOME="${OEC_WSL_HOME:-$HOME}"
mkdir -p "$HOME"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

OEC_ROOT="${OEC_ROOT:-/mnt/c/tmp/oec-3.6-integration}"
VENV="${OEC_WSL_VENV:-$HOME/.oec-wsl/venv}"
EXTRAS="${OEC_WSL_EXTRAS:-neural,evolutionary,jax}"

if [[ ! -d "$OEC_ROOT/src/oec" ]]; then
  echo "OEC_ROOT is not an OEC checkout: $OEC_ROOT" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv into $HOME/.local/bin ..."
  if ! curl -fsSL --retry 3 --retry-all-errors https://astral.sh/uv/install.sh | sh; then
    echo "astral.sh installer failed; falling back to pip ..."
    python3 -m pip install --user uv
  fi
  export PATH="$HOME/.local/bin:$HOME/.local/bin:$PATH"
  hash -r
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not on PATH after install" >&2
  exit 1
fi

mkdir -p "$(dirname "$VENV")"
cd "$OEC_ROOT"

sync_args=(sync)
IFS=',' read -r -a extra_list <<<"$EXTRAS"
for extra in "${extra_list[@]}"; do
  extra="${extra// /}"
  [[ -n "$extra" ]] && sync_args+=(--extra "$extra")
done

echo "uv ${sync_args[*]}  (env=$VENV)"
UV_PROJECT_ENVIRONMENT="$VENV" uv "${sync_args[@]}"

if [[ "${OEC_WSL_CUDA:-0}" == "1" ]]; then
  echo "Installing JAX CUDA wheels into the WSL venv (Linux only) ..."
  UV_PROJECT_ENVIRONMENT="$VENV" uv pip install --python "$VENV/bin/python" --upgrade "jax[cuda12]"
fi

RC="$HOME/.oec-wsl/bashrc"
mkdir -p "$(dirname "$RC")"
cat >"$RC" <<EOF
export HOME="$HOME"
export PATH="$HOME/.local/bin:\$PATH"
export OEC_ROOT="$OEC_ROOT"
export VIRTUAL_ENV="$VENV"
export PATH="$VENV/bin:\$PATH"
export UV_PROJECT_ENVIRONMENT="$VENV"
cd "\$OEC_ROOT"
echo "OEC WSL  root=\$OEC_ROOT"
echo "         python=\$(command -v python)"
python -c "import oec; print('         oec', oec.__version__)" 2>/dev/null || true
python -c "import jax, jaxlib; print('         jax', jax.__version__, jax.devices())" 2>/dev/null || echo "         jax: not importable (CPU extra missing or CUDA not installed)"
python -c "import torch; print('         torch', torch.__version__, 'cuda', torch.cuda.is_available())" 2>/dev/null || echo "         torch: not importable"
echo "Commands: oec version | uv run pytest tests/unit/test_neural_architecture_zip_leftovers.py"
EOF

if [[ "${OEC_WSL_SETUP_ONLY:-0}" == "1" ]]; then
  UV_PROJECT_ENVIRONMENT="$VENV" "$VENV/bin/python" -c "import oec; print('oec', oec.__version__)"
  exit 0
fi

exec bash --rcfile "$RC" -i
