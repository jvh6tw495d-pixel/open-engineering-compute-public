# Launch the OEC Linux shell in Ubuntu-24.04 WSL (not docker-desktop).
param(
    [switch]$SetupOnly,
    [switch]$CudaJax
)

$ErrorActionPreference = "Stop"

function Convert-WinToWsl([string]$Path) {
    $full = (Resolve-Path $Path).Path
    $full = $full -replace "\\", "/"
    if ($full -match "^([A-Za-z]):(.*)$") {
        return "/mnt/$($Matches[1].ToLower())$($Matches[2])"
    }
    return $full
}

$distro = "Ubuntu-24.04"
$repoWin = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptUnix = Convert-WinToWsl (Join-Path $PSScriptRoot "oec-wsl.sh")
$rootUnix = Convert-WinToWsl $repoWin

$flags = "export HOME=/root OEC_ROOT='$rootUnix'"
if ($SetupOnly) { $flags += " OEC_WSL_SETUP_ONLY=1" }
if ($CudaJax) { $flags += " OEC_WSL_CUDA=1" }

Write-Host "WSL $distro  OEC_ROOT=$rootUnix"
# Do not leak Windows HOME via WSLENV.
$env:WSLENV = $null
wsl -d $distro -- /bin/bash -lc "$flags; chmod +x '$scriptUnix'; bash '$scriptUnix'"
