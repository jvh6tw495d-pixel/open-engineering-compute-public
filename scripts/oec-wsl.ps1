# Launch the OEC Linux shell in Ubuntu-24.04 WSL (not docker-desktop).
param(
    [switch]$SetupOnly,
    [switch]$CudaJax,
    [switch]$CpuJax,
    [switch]$ForceSync,
    [string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgCommand
)

$ErrorActionPreference = "Stop"

if ($CudaJax -and $CpuJax) {
    throw "Specify only one of -CudaJax and -CpuJax."
}

function Convert-WinToWsl([string]$Path) {
    $full = (Resolve-Path $Path).Path
    $full = $full -replace "\\", "/"
    if ($full -match "^([A-Za-z]):(.*)$") {
        return "/mnt/$($Matches[1].ToLower())$($Matches[2])"
    }
    return $full
}

function ConvertTo-BashSingleQuoted([string]$Value) {
    if ($null -eq $Value) { return "''" }
    return "'" + ($Value -replace "'", "'\''") + "'"
}

$distro = "Ubuntu-24.04"
$repoWin = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptUnix = Convert-WinToWsl (Join-Path $PSScriptRoot "oec-wsl.sh")
$rootUnix = Convert-WinToWsl $repoWin
$scriptQuoted = ConvertTo-BashSingleQuoted $scriptUnix
$rootQuoted = ConvertTo-BashSingleQuoted $rootUnix

$assignments = @(
    "HOME=/root",
    "OEC_ROOT=$rootQuoted"
)
if ($SetupOnly) { $assignments += "OEC_WSL_SETUP_ONLY=1" }
if ($CudaJax) { $assignments += "OEC_WSL_CUDA=1" }
if ($CpuJax) { $assignments += "OEC_WSL_CPU_JAX=1" }
if ($ForceSync) { $assignments += "OEC_WSL_FORCE_SYNC=1" }

$cmd = $Command
if (-not $cmd -and $ArgCommand -and $ArgCommand.Count -gt 0) {
    $cmd = ($ArgCommand -join " ")
}
if ($cmd) {
    $assignments += "OEC_WSL_COMMAND=$(ConvertTo-BashSingleQuoted $cmd)"
}

$prefix = "export " + ($assignments -join " ")
$lc = "$prefix; chmod +x $scriptQuoted; bash $scriptQuoted"

Write-Host "WSL $distro  OEC_ROOT=$rootUnix"
# Do not leak Windows HOME via WSLENV. Do not pass the command via WSLENV.
$env:WSLENV = $null
wsl -d $distro -- /bin/bash -lc "$lc"
exit $LASTEXITCODE
