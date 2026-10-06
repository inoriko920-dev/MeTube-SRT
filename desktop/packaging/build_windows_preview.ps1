[CmdletBinding()]
param(
    [string]$OutputRoot = "build\windows-preview"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DesktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoRoot = (Resolve-Path (Join-Path $DesktopRoot "..")).Path
$OutputRoot = Join-Path $DesktopRoot $OutputRoot
$StageRoot = Join-Path $OutputRoot "MeTube-SRT-Windows-x64-Preview"
$MainDist = Join-Path $OutputRoot "dist-main"
$WorkerDist = Join-Path $OutputRoot "dist-worker"
$WorkRoot = Join-Path $OutputRoot "work"
$SpecRoot = Join-Path $OutputRoot "spec"
$ZipPath = Join-Path $OutputRoot "MeTube-SRT-Windows-x64-Preview.zip"

function Assert-LastExitCode {
    param([Parameter(Mandatory = $true)][string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Resolve-Executable {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string]$Override = ""
    )
    if ($Override -and (Test-Path $Override)) {
        return (Resolve-Path $Override).Path
    }
    $resolved = Get-Command $Command -ErrorAction Stop
    return $resolved.Source
}

Push-Location $DesktopRoot
try {
    Remove-Item $OutputRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $OutputRoot, $WorkRoot, $SpecRoot | Out-Null

    Write-Host "=== Build worker EXE ==="
    & uv run pyinstaller --noconfirm --clean --onedir --console `
        --name "MeTube-SRT-Worker" `
        --distpath $WorkerDist `
        --workpath (Join-Path $WorkRoot "worker") `
        --specpath $SpecRoot `
        --collect-all yt_dlp `
        --collect-all yt_dlp_ejs `
        --collect-all curl_cffi `
        --collect-all certifi `
        "src\metube_srt_desktop\worker\__main__.py"
    Assert-LastExitCode "Worker PyInstaller build"

    Write-Host "=== Build desktop EXE folder ==="
    & uv run pyinstaller --noconfirm --clean --onedir --windowed `
        --name "MeTube-SRT" `
        --distpath $MainDist `
        --workpath (Join-Path $WorkRoot "main") `
        --specpath $SpecRoot `
        --collect-all google.genai `
        --collect-all keyring `
        --collect-submodules keyring.backends `
        "src\metube_srt_desktop\__main__.py"
    Assert-LastExitCode "Desktop PyInstaller build"

    Copy-Item (Join-Path $MainDist "MeTube-SRT") $StageRoot -Recurse -Force
    $WorkerStage = Join-Path $StageRoot "worker"
    Copy-Item (Join-Path $WorkerDist "MeTube-SRT-Worker") $WorkerStage -Recurse -Force

    $ToolsRoot = Join-Path $StageRoot "tools"
    New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null

    $DenoPath = Resolve-Executable "deno" $env:METUBE_BUILD_DENO
    $FfmpegPath = Resolve-Executable "ffmpeg" $env:METUBE_BUILD_FFMPEG
    $FfprobePath = Resolve-Executable "ffprobe" $env:METUBE_BUILD_FFPROBE

    Copy-Item $DenoPath (Join-Path $ToolsRoot "deno.exe") -Force
    Copy-Item $FfmpegPath (Join-Path $ToolsRoot "ffmpeg.exe") -Force
    Copy-Item $FfprobePath (Join-Path $ToolsRoot "ffprobe.exe") -Force
    Copy-Item (Join-Path $RepoRoot "LICENSE") (Join-Path $StageRoot "LICENSE") -Force
    Set-Content -Path (Join-Path $StageRoot "portable.flag") -Value "portable" -Encoding ASCII

    $PreviewReadme = @"
MeTube-SRT Windows x64 Preview
==============================

Cara menjalankan:
1. Ekstrak seluruh folder ZIP.
2. Jalankan MeTube-SRT.exe.
3. Tempel URL YouTube di halaman Unduh.
4. Pilih kualitas, opsi SRT, folder tujuan, lalu tambahkan ke antrian.

Isi portable:
- MeTube-SRT.exe            : aplikasi Windows
- worker\MeTube-SRT-Worker.exe : worker yt-dlp terisolasi (runtime folder stabil)
- tools\deno.exe            : JavaScript runtime untuk extractor YouTube
- tools\ffmpeg.exe          : media processing
- tools\ffprobe.exe         : media probe
- portable.flag             : simpan app.db/metadata di folder data selama writable
- data\                     : dibuat otomatis saat aplikasi pertama dijalankan

STATUS: PREVIEW BUILD
- Core/CI sudah hijau.
- Live YouTube dari GitHub datacenter diblokir anti-bot, sehingga build ini
  sengaja diberikan untuk pengujian langsung pada jaringan Windows biasa.
- AI Agent Gemini aktif setelah Anda menambahkan API key di menu API Gemini.
- API key disimpan melalui penyimpanan credential Windows, bukan di app.db/log.
- Jika YouTube meminta login/anti-bot, itu akan terlihat sebagai error resolve/download.

Jangan memindahkan hanya file EXE. Pertahankan seluruh isi folder portable.
"@
    Set-Content -Path (Join-Path $StageRoot "BACA_DULU.txt") -Value $PreviewReadme -Encoding UTF8

    $BuildInfo = [ordered]@{
        name = "MeTube-SRT Windows x64 Preview"
        source_commit = $env:GITHUB_SHA
        built_utc = [DateTime]::UtcNow.ToString("o")
        python = (& uv run python --version 2>&1 | Out-String).Trim()
        pyinstaller = (& uv run pyinstaller --version 2>&1 | Out-String).Trim()
        deno = (& (Join-Path $ToolsRoot "deno.exe") --version 2>&1 | Select-Object -First 1 | Out-String).Trim()
        ffmpeg = (& (Join-Path $ToolsRoot "ffmpeg.exe") -version 2>&1 | Select-Object -First 1 | Out-String).Trim()
    }
    $BuildInfo | ConvertTo-Json | Set-Content -Path (Join-Path $StageRoot "BUILD_INFO.json") -Encoding UTF8

    Write-Host "=== Smoke packaged worker ==="
    $CancelCommand = '{"schema_version":1,"command_type":"cancel","job_id":"package-smoke","worker_run_id":"package-smoke-run","payload":{}}'
    $WorkerOutput = @($CancelCommand | & (Join-Path $StageRoot "worker\MeTube-SRT-Worker.exe"))
    Assert-LastExitCode "Packaged worker smoke"
    $WorkerText = $WorkerOutput -join "`n"
    if ($WorkerText -notmatch '"event_type":"ready"' -or $WorkerText -notmatch '"event_type":"cancelled"') {
        throw "Packaged worker smoke did not emit READY + CANCELLED."
    }

    Write-Host "=== Smoke desktop EXE ==="
    $Process = Start-Process -FilePath (Join-Path $StageRoot "MeTube-SRT.exe") `
        -ArgumentList "--self-check" -Wait -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "Packaged desktop self-check failed with exit code $($Process.ExitCode)."
    }

    Write-Host "=== Smoke Windows credential backend ==="
    $CredentialProcess = Start-Process -FilePath (Join-Path $StageRoot "MeTube-SRT.exe") `
        -ArgumentList "--credential-self-check" -Wait -PassThru
    if ($CredentialProcess.ExitCode -ne 0) {
        throw "Packaged credential self-check failed with exit code $($CredentialProcess.ExitCode)."
    }

    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
    }
    Compress-Archive -Path $StageRoot -DestinationPath $ZipPath -CompressionLevel Optimal

    Write-Host "=== Verify ZIP archive after extraction ==="
    $ArchiveProbeRoot = Join-Path $OutputRoot "archive-probe"
    Remove-Item $ArchiveProbeRoot -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path $ZipPath -DestinationPath $ArchiveProbeRoot -Force
    $ArchiveStage = Join-Path $ArchiveProbeRoot "MeTube-SRT-Windows-x64-Preview"
    $RequiredArchivePaths = @(
        "MeTube-SRT.exe",
        "worker\MeTube-SRT-Worker.exe",
        "tools\deno.exe",
        "tools\ffmpeg.exe",
        "tools\ffprobe.exe",
        "portable.flag",
        "BACA_DULU.txt",
        "BUILD_INFO.json",
        "LICENSE"
    )
    foreach ($RelativePath in $RequiredArchivePaths) {
        $Candidate = Join-Path $ArchiveStage $RelativePath
        if (-not (Test-Path $Candidate)) {
            throw "ZIP verification missing required path: $RelativePath"
        }
    }

    $ArchiveSelfCheck = Start-Process -FilePath (Join-Path $ArchiveStage "MeTube-SRT.exe") `
        -ArgumentList "--self-check" -Wait -PassThru
    if ($ArchiveSelfCheck.ExitCode -ne 0) {
        throw "Extracted ZIP desktop self-check failed with exit code $($ArchiveSelfCheck.ExitCode)."
    }

    $ArchiveCancelCommand = '{"schema_version":1,"command_type":"cancel","job_id":"archive-smoke","worker_run_id":"archive-smoke-run","payload":{}}'
    $ArchiveWorkerOutput = @($ArchiveCancelCommand | & (Join-Path $ArchiveStage "worker\MeTube-SRT-Worker.exe"))
    Assert-LastExitCode "Extracted ZIP worker smoke"
    $ArchiveWorkerText = $ArchiveWorkerOutput -join "`n"
    if ($ArchiveWorkerText -notmatch '"event_type":"ready"' -or $ArchiveWorkerText -notmatch '"event_type":"cancelled"') {
        throw "Extracted ZIP worker smoke did not emit READY + CANCELLED."
    }

    Remove-Item $ArchiveProbeRoot -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "Windows preview build: OK"
    Write-Host "ZIP: $ZipPath"
}
finally {
    Pop-Location
}
