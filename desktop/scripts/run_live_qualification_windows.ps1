[CmdletBinding()]
param(
    [string]$OutputRoot = "",
    [switch]$SkipSync,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DesktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $DesktopRoot "build\live-qualification-local"
}

$ReportPath = Join-Path $OutputRoot "report.json"
$LogPath = Join-Path $OutputRoot "qualification.log"
$ProbeLogPath = Join-Path $OutputRoot "upstream-probe.log"
$SummaryPath = Join-Path $OutputRoot "summary.txt"
$EvidenceZip = Join-Path $DesktopRoot "build\live-qualification-evidence.zip"

function Test-RequiredCommand {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Write-LogLine {
    param([Parameter(Mandatory = $true)][string]$Message)
    $Message | Tee-Object -FilePath $LogPath -Append
}

if (-not (Test-Path (Join-Path $DesktopRoot "pyproject.toml"))) {
    throw "Desktop project root could not be resolved."
}
if (-not (Test-Path (Join-Path $DesktopRoot "scripts\qualify_live_ytdlp.py"))) {
    throw "Live qualification harness is missing."
}

if ($ValidateOnly) {
    Write-Host "Local live qualification wrapper: OK"
    exit 0
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
Remove-Item $LogPath, $ProbeLogPath, $SummaryPath -Force -ErrorAction SilentlyContinue

$required = @("uv", "deno", "ffmpeg", "ffprobe")
$missing = @($required | Where-Object { -not (Test-RequiredCommand $_) })
if ($missing.Count -gt 0) {
    Write-LogLine "Missing required command(s): $($missing -join ', ')"
    Write-LogLine "Install the missing tools and make sure they are available on PATH."
    Write-LogLine "Required by the qualification: uv, Deno, FFmpeg, ffprobe."
    Write-Host ""
    Write-Host "Qualification cannot start yet."
    Write-Host "Missing: $($missing -join ', ')"
    exit 2
}

Push-Location $DesktopRoot
try {
    Write-LogLine "MeTube-SRT live qualification started."
    Write-LogLine "Desktop root: $DesktopRoot"

    Write-LogLine ""
    Write-LogLine "=== TOOL VERSIONS ==="
    & uv --version 2>&1 | Tee-Object -FilePath $LogPath -Append
    & deno --version 2>&1 | Tee-Object -FilePath $LogPath -Append
    & ffmpeg -version 2>&1 | Select-Object -First 1 | Tee-Object -FilePath $LogPath -Append
    & ffprobe -version 2>&1 | Select-Object -First 1 | Tee-Object -FilePath $LogPath -Append

    if (-not $SkipSync) {
        Write-LogLine ""
        Write-LogLine "=== UV SYNC ==="
        & uv sync --all-groups 2>&1 | Tee-Object -FilePath $LogPath -Append
        if ($LASTEXITCODE -ne 0) {
            throw "uv sync failed with exit code $LASTEXITCODE."
        }
    }

    Write-LogLine ""
    Write-LogLine "=== LIVE QUALIFICATION ==="
    & uv run python scripts/qualify_live_ytdlp.py --output-root $OutputRoot --report $ReportPath 2>&1 |
        Tee-Object -FilePath $LogPath -Append
    $QualificationExit = $LASTEXITCODE

    $ProbeExit = 0
    if ($QualificationExit -ne 0) {
        Write-LogLine ""
        Write-LogLine "=== UPSTREAM YT-DLP PROBE ==="
        $ProbeUrl = $env:METUBE_LIVE_SINGLE_URL
        if (-not $ProbeUrl) {
            $ProbeUrl = "https://www.youtube.com/watch?v=gHKT4uU8Zng"
        }

        & uv run yt-dlp -v --skip-download --no-playlist --list-subs --extractor-args "youtube:skip=translated_subs" $ProbeUrl 2>&1 |
            Tee-Object -FilePath $ProbeLogPath
        $ProbeExit = $LASTEXITCODE
    }

    $Summary = @(
        "MeTube-SRT Slice 10 local live qualification",
        "qualification_exit=$QualificationExit",
        "upstream_probe_exit=$ProbeExit",
        "report=$ReportPath",
        "log=$LogPath",
        "probe_log=$ProbeLogPath"
    )
    $Summary | Set-Content -Encoding UTF8 $SummaryPath

    $EvidenceFiles = @($ReportPath, $LogPath, $ProbeLogPath, $SummaryPath) |
        Where-Object { Test-Path $_ }
    New-Item -ItemType Directory -Force -Path (Split-Path $EvidenceZip -Parent) | Out-Null
    Compress-Archive -Path $EvidenceFiles -DestinationPath $EvidenceZip -Force

    Write-Host ""
    Write-Host "Evidence ZIP: $EvidenceZip"
    if ($QualificationExit -eq 0) {
        Write-Host "LIVE QUALIFICATION: PASS"
        exit 0
    }

    Write-Warning "LIVE QUALIFICATION: FAILED/BLOCKED. Send the evidence ZIP for review."
    exit $QualificationExit
}
finally {
    Pop-Location
}
