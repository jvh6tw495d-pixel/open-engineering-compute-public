#!/usr/bin/env bash
# Local Linux shell for OEC (Ubuntu WSL). Not the POST-OEC research harness.
set -euo pipefail

die() {
  echo "oec-wsl: $*" >&2
  exit 1
}

is_windows_mount_home() {
  local h="${1:-}"
  [[ "$h" =~ ^/mnt/[a-zA-Z](/|$) ]]
}

is_not_unix_abs() {
  local h="${1:-}"
  [[ -z "$h" || "$h" != /* ]]
}

is_unsafe_home() {
  is_not_unix_abs "${1:-}" || is_windows_mount_home "${1:-}"
}

# Fail-closed HOME: never use a Windows drive mount as Linux HOME.
# OEC_WSL_HOME if set must already be a Linux path (do not silently ignore).
# Leaked Windows HOME (e.g. C:Usersjoaop) is remapped to /root.
# /mnt/c/... is rejected so caches/uv are not written onto NTFS.
if [[ -n "${OEC_WSL_HOME+x}" ]]; then
  if is_unsafe_home "$OEC_WSL_HOME"; then
    die "OEC_WSL_HOME is unsafe (need a Linux path, not a Windows mount): ${OEC_WSL_HOME}"
  fi
  export HOME="$OEC_WSL_HOME"
elif is_windows_mount_home "${HOME:-}"; then
  die "HOME is a Windows drive mount; refusing ${HOME} (use HOME=/root or a Linux user home)"
elif is_not_unix_abs "${HOME:-}"; then
  export HOME=/root
fi
mkdir -p "$HOME"

# Linux-only PATH. Do not append the Windows PATH (uv.exe / python.exe hijack).
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"
hash -r

if [[ -d /usr/lib/wsl/lib ]]; then
  export LD_LIBRARY_PATH="/usr/lib/wsl/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OEC_ROOT="${OEC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [[ ! -d "$OEC_ROOT/src/oec" ]]; then
  die "OEC_ROOT is not an OEC checkout: $OEC_ROOT"
fi

VENV="${OEC_WSL_VENV:-$HOME/.oec-wsl/venv}"
EXTRAS="${OEC_WSL_EXTRAS:-neural,evolutionary,jax}"
STAMP="$HOME/.oec-wsl/cuda12"
OEC_WSL_UV_VERSION="${OEC_WSL_UV_VERSION:-0.12.5}"

IFS=',' read -r -a extra_list <<<"$EXTRAS"
has_jax_extra=0
for extra in "${extra_list[@]}"; do
  extra="${extra// /}"
  [[ "$extra" == "jax" ]] && has_jax_extra=1
done

is_linux_elf() {
  local p="${1:-}"
  [[ -n "$p" && -e "$p" ]] || return 1
  local real
  real="$(readlink -f "$p" 2>/dev/null || printf '%s' "$p")"
  [[ -f "$real" ]] || return 1
  case "$p" in /mnt/*) return 1 ;; esac
  case "$real" in /mnt/*) return 1 ;; esac
  local magic
  magic="$(dd if="$real" bs=1 count=4 2>/dev/null || true)"
  [[ "$magic" == $'\x7fELF' ]]
}

find_linux_uv() {
  local candidate=""
  candidate="$(command -v uv 2>/dev/null || true)"
  if is_linux_elf "$candidate"; then
    printf '%s\n' "$candidate"
    return 0
  fi
  if is_linux_elf "$HOME/.local/bin/uv"; then
    printf '%s\n' "$HOME/.local/bin/uv"
    return 0
  fi
  return 1
}

uv_triple() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) printf '%s\n' "x86_64-unknown-linux-gnu" ;;
    aarch64|arm64) printf '%s\n' "aarch64-unknown-linux-gnu" ;;
    *) die "unsupported uname -m for pinned uv: $arch" ;;
  esac
}

pinned_uv_sha256() {
  local ver="$1" triple="$2"
  if [[ "$ver" == "0.12.5" && "$triple" == "x86_64-unknown-linux-gnu" ]]; then
    printf '%s\n' "68a509da24b06b4223a1c0175fb5eb5bc79342b76cbeff0cfe51ac3f5b17b6b2"
    return 0
  fi
  return 1
}

curl_fetch() {
  local url="$1" out="$2"
  local part="${out}.part"
  command -v curl >/dev/null 2>&1 || return 1
  rm -f "$part"
  if curl -fL --retry 3 --retry-all-errors -C - --output "$part" "$url"; then
    mv -f "$part" "$out"
    return 0
  fi
  rm -f "$part"
  if curl -fL --retry 3 --retry-all-errors --output "$part" "$url"; then
    mv -f "$part" "$out"
    return 0
  fi
  rm -f "$part"
  return 1
}

verify_uv_sha256() {
  local tarball="$1" sumfile="$2" tar_name="$3" ver="$4" triple="$5"
  local actual pin downloaded=""
  actual="$(sha256sum "$tarball" | awk '{print $1}')"
  if pin="$(pinned_uv_sha256 "$ver" "$triple")"; then
    if [[ "$actual" != "$pin" ]]; then
      die "uv tarball sha256 mismatch (pinned): got $actual want $pin"
    fi
  fi
  if [[ -s "$sumfile" ]]; then
    downloaded="$(awk '{print $1}' "$sumfile" | head -n 1)"
    if [[ -z "$downloaded" ]]; then
      die "uv sha256 file was empty: $sumfile"
    fi
    if [[ -n "${pin:-}" && "$downloaded" != "$pin" ]]; then
      die "uv downloaded checksum $downloaded != pin $pin"
    fi
    if [[ "$actual" != "$downloaded" ]]; then
      die "uv tarball sha256 mismatch (release file): got $actual want $downloaded"
    fi
  elif [[ -z "${pin:-}" ]]; then
    die "no sha256 pin and no ${tar_name}.sha256; refusing to install uv"
  fi
}

install_uv_from_tarball() {
  local tarball="$1" triple="$2"
  local tmp src="" d
  tmp="$(mktemp -d)"
  tar -xzf "$tarball" -C "$tmp"
  if [[ -f "$tmp/uv-${triple}/uv" ]]; then
    src="$tmp/uv-${triple}"
  else
    for d in "$tmp"/uv-*; do
      if [[ -f "$d/uv" ]]; then
        src="$d"
        break
      fi
    done
  fi
  if [[ -z "$src" || ! -f "$src/uv" ]]; then
    rm -rf "$tmp"
    return 1
  fi
  mkdir -p "$HOME/.local/bin"
  cp "$src/uv" "$HOME/.local/bin/uv"
  chmod +x "$HOME/.local/bin/uv"
  if [[ -f "$src/uvx" ]]; then
    cp "$src/uvx" "$HOME/.local/bin/uvx"
    chmod +x "$HOME/.local/bin/uvx"
  fi
  rm -rf "$tmp"
  is_linux_elf "$HOME/.local/bin/uv"
}

install_linux_uv() {
  local ver="$OEC_WSL_UV_VERSION"
  local triple tar_name dest sum_dest base
  triple="$(uv_triple)"
  tar_name="uv-${triple}.tar.gz"
  dest="/tmp/${tar_name}"
  sum_dest="/tmp/${tar_name}.sha256"

  echo "Installing Linux uv ${ver} (${triple}) into $HOME/.local/bin ..."
  for base in \
    "https://github.com/astral-sh/uv/releases/download/${ver}" \
    "https://releases.astral.sh/github/uv/releases/download/${ver}"
  do
    if curl_fetch "${base}/${tar_name}" "$dest"; then
      curl_fetch "${base}/${tar_name}.sha256" "$sum_dest" || true
      verify_uv_sha256 "$dest" "$sum_dest" "$tar_name" "$ver" "$triple"
      if install_uv_from_tarball "$dest" "$triple"; then
        return 0
      fi
      echo "oec-wsl: tarball extract failed from $base" >&2
    fi
  done

  # Official installer as file-then-run only (never curl | sh).
  local installer="/tmp/uv-install-${ver}.sh"
  local head
  for base in \
    "https://github.com/astral-sh/uv/releases/download/${ver}/uv-installer.sh" \
    "https://astral.sh/uv/${ver}/install.sh" \
    "https://astral.sh/uv/install.sh"
  do
    if curl_fetch "$base" "$installer"; then
      head="$(dd if="$installer" bs=2 count=1 2>/dev/null || true)"
      if [[ "$head" == "#!" ]]; then
        echo "Falling back to official uv install.sh (file then run) ..."
        mkdir -p "$HOME/.local/bin"
        UV_INSTALL_DIR="$HOME/.local/bin" sh "$installer" || true
        if is_linux_elf "$HOME/.local/bin/uv"; then
          return 0
        fi
      fi
    fi
  done

  if command -v python3 >/dev/null 2>&1 && python3 -m pip --version >/dev/null 2>&1; then
    echo "Falling back to python3 -m pip install --user uv ..."
    python3 -m pip install --user uv || true
    if is_linux_elf "$HOME/.local/bin/uv"; then
      return 0
    fi
    if is_linux_elf "$(command -v uv 2>/dev/null || true)"; then
      return 0
    fi
  fi

  return 1
}

ensure_linux_uv() {
  local found=""
  if found="$(find_linux_uv)"; then
    return 0
  fi
  # Windows/interop uv on PATH is ignored; install a Linux ELF into ~/.local/bin.
  install_linux_uv || die "failed to install Linux uv ${OEC_WSL_UV_VERSION}"
  hash -r
  found="$(find_linux_uv)" || die "uv is missing or not a Linux ELF after install"
  if ! is_linux_elf "$found"; then
    die "uv at $found is not a Linux ELF (refusing Windows/interop uv)"
  fi
}

ensure_python_312() {
  local ok=0
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
      ok=1
    fi
  fi
  if [[ "$ok" != "1" ]]; then
    echo "python3 >= 3.12 not on PATH; uv python install 3.12"
    uv python install 3.12
  fi
}

jax_has_gpu() {
  "$VENV/bin/python" -c '
import sys
try:
    import jax
except Exception:
    sys.exit(1)
for d in jax.devices():
    plat = str(getattr(d, "platform", "")).lower()
    s = str(d).lower()
    if plat == "gpu" or "cuda" in plat or "cuda" in s:
        sys.exit(0)
sys.exit(1)
'
}

cuda_visible_in_distro() {
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    return 0
  fi
  [[ -e /dev/dxg ]]
}

print_banner() {
  echo "OEC WSL  (dev terminal, not POST-OEC; do not publish/upload from this shell)"
  echo "         root=$OEC_ROOT"
  echo "         python=$(command -v python 2>/dev/null || true)"
  if [[ "$(id -u)" == "0" ]]; then
    echo "         running as root; caches under $HOME"
  fi
  python -c "import oec; print('         oec', oec.__version__)" 2>/dev/null || echo "         oec: not importable"
  python -c '
import sys
try:
    import jax
except Exception:
    print("         jax: not importable")
    sys.exit(0)
devs = jax.devices()
kind = "CUDA" if any(
    str(getattr(d, "platform", "")).lower() == "gpu" or "cuda" in str(d).lower()
    for d in devs
) else "CPU"
print("         jax", jax.__version__, kind, devs)
' 2>/dev/null || echo "         jax: not importable"
  python -c "import torch; print('         torch', torch.__version__, 'cuda', torch.cuda.is_available())" 2>/dev/null || echo "         torch: not importable"
}

mkdir -p "$HOME/.oec-wsl"
ensure_linux_uv
ensure_python_312

WANT_CUDA=0
if [[ "${OEC_WSL_CPU_JAX:-0}" == "1" ]]; then
  rm -f "$STAMP"
  WANT_CUDA=0
elif [[ "${OEC_WSL_CUDA:-0}" == "1" ]]; then
  : >"$STAMP"
  WANT_CUDA=1
elif [[ -f "$STAMP" ]]; then
  WANT_CUDA=1
fi

if [[ "$WANT_CUDA" == "1" && "$has_jax_extra" != "1" ]]; then
  die "CUDA JAX requested but OEC_WSL_EXTRAS omits jax: $EXTRAS"
fi

if [[ "$WANT_CUDA" == "1" ]]; then
  if ! cuda_visible_in_distro; then
    die "CUDA requested but nvidia-smi / /dev/dxg is not available in this distro"
  fi
fi

if [[ "$VENV" == "$OEC_ROOT/.venv" || "$VENV" == "$OEC_ROOT/.venv/" ]]; then
  die "refusing to use the Windows-tree venv: $VENV"
fi

mkdir -p "$(dirname "$VENV")"
cd "$OEC_ROOT"
export UV_PROJECT_ENVIRONMENT="$VENV"
export VIRTUAL_ENV="$VENV"

need_sync=0
if [[ "${OEC_WSL_SETUP_ONLY:-0}" == "1" || "${OEC_WSL_FORCE_SYNC:-0}" == "1" ]]; then
  need_sync=1
elif [[ ! -x "$VENV/bin/python" ]]; then
  need_sync=1
elif ! "$VENV/bin/python" -c "import oec" >/dev/null 2>&1; then
  need_sync=1
fi

sync_args=(sync --inexact)
if [[ "${OEC_WSL_UNLOCK:-0}" != "1" ]]; then
  sync_args+=(--frozen)
fi
for extra in "${extra_list[@]}"; do
  extra="${extra// /}"
  [[ -n "$extra" ]] && sync_args+=(--extra "$extra")
done

if [[ "$need_sync" == "1" ]]; then
  echo "uv ${sync_args[*]}  (env=$VENV)"
  uv "${sync_args[@]}"
else
  echo "skip uv sync (venv already imports oec; set OEC_WSL_FORCE_SYNC=1 to refresh)"
fi

[[ -x "$VENV/bin/python" ]] || die "venv python missing after sync: $VENV/bin/python"

if [[ "$WANT_CUDA" == "1" ]]; then
  if ! "$VENV/bin/python" -c "import jax" >/dev/null 2>&1; then
    die "CUDA JAX requested but jax is not importable in $VENV"
  fi
  if ! jax_has_gpu; then
    JAX_VER="$("$VENV/bin/python" -c "from importlib.metadata import version; print(version('jax'))")"
    [[ -n "$JAX_VER" ]] || die "could not read jax version from the venv"
    echo "Overlay jax[cuda12]==${JAX_VER} (no --upgrade) ..."
    uv pip install --python "$VENV/bin/python" "jax[cuda12]==${JAX_VER}"
  fi
  if ! jax_has_gpu; then
    echo "oec-wsl: CUDA JAX requested but jax.devices() has no GPU/CUDA device:" >&2
    "$VENV/bin/python" -c "import jax; print(jax.__version__, jax.devices())" >&2 || true
    die "silent CPU JAX is a blocker (WANT_CUDA)"
  fi
fi

# Runtime PATH: venv first, then Linux-only paths.
export PATH="$VENV/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
hash -r

py="$(command -v python 2>/dev/null || true)"
case "$py" in
  "$VENV/bin/python"|"$VENV/bin/python3") ;;
  *) die "command -v python is ${py:-missing}, expected $VENV/bin/python" ;;
esac
case "$py" in
  "$OEC_ROOT/.venv"/*) die "refusing Windows-tree interpreter: $py" ;;
esac

uv_bin="$(command -v uv 2>/dev/null || true)"
is_linux_elf "$uv_bin" || die "command -v uv is not a Linux ELF: ${uv_bin:-missing}"
case "$uv_bin" in
  /mnt/*) die "uv must not live under /mnt/: $uv_bin" ;;
esac

RC="$HOME/.oec-wsl/bashrc"
mkdir -p "$(dirname "$RC")"
cat >"$RC" <<EOF
export HOME="$HOME"
export PATH="$VENV/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export OEC_ROOT="$OEC_ROOT"
export VIRTUAL_ENV="$VENV"
export UV_PROJECT_ENVIRONMENT="$VENV"
cd "\$OEC_ROOT"
echo "OEC WSL  (dev terminal, not POST-OEC; do not publish/upload from this shell)"
echo "         root=\$OEC_ROOT"
echo "         python=\$(command -v python)"
if [[ "\$(id -u)" == "0" ]]; then
  echo "         running as root; caches under \$HOME"
fi
python -c "import oec; print('         oec', oec.__version__)" 2>/dev/null || echo "         oec: not importable"
python -c '
import sys
try:
    import jax
except Exception:
    print("         jax: not importable")
    sys.exit(0)
devs = jax.devices()
kind = "CUDA" if any(
    str(getattr(d, "platform", "")).lower() == "gpu" or "cuda" in str(d).lower()
    for d in devs
) else "CPU"
print("         jax", jax.__version__, kind, devs)
' 2>/dev/null || echo "         jax: not importable"
python -c "import torch; print('         torch', torch.__version__, 'cuda', torch.cuda.is_available())" 2>/dev/null || echo "         torch: not importable"
echo "Commands: oec version | uv run pytest tests/unit/test_neural_architecture_zip_leftovers.py | pytest -m neural"
EOF

if [[ -n "${OEC_WSL_COMMAND:-}" ]]; then
  exec bash --rcfile "$RC" -ic "$OEC_WSL_COMMAND"
elif [[ $# -gt 0 ]]; then
  exec bash --rcfile "$RC" -ic "$*"
elif [[ "${OEC_WSL_SETUP_ONLY:-0}" == "1" ]]; then
  print_banner
  python -c "import oec; print('oec', oec.__version__)"
  if [[ "$WANT_CUDA" == "1" ]] && ! jax_has_gpu; then
    die "CUDA JAX requested but jax.devices() has no GPU/CUDA device"
  fi
  exit 0
fi

exec bash --rcfile "$RC" -i
