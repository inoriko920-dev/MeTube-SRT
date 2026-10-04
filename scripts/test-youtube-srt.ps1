param(
    [string]$Url = "https://www.youtube.com/watch?v=aircAruvnKk",
    [int]$ClipSeconds = 3,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Fail([string]$Message, [int]$Code = 1) {
    Write-Host ""
    Write-Host "GAGAL: $Message" -ForegroundColor Red
    exit $Code
}

function Wait-ForMeTube([string]$BaseUrl, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri "$BaseUrl/version" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    Fail "MeTube-SRT tidak merespons di $BaseUrl. Jalankan 'docker compose logs' untuk melihat penyebabnya."
}

if ($ClipSeconds -lt 1) {
    Fail "ClipSeconds minimal 1 detik."
}

Write-Host "=== MeTube-SRT: tes YouTube + SRT lokal ===" -ForegroundColor Cyan
Write-Host "URL: $Url"
Write-Host "Cuplikan: $ClipSeconds detik"

try {
    docker info *> $null
} catch {
    Fail "Docker Desktop belum aktif atau perintah docker tidak tersedia."
}

Write-Host "[1/5] Menyalakan MeTube-SRT..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Fail "docker compose up gagal."
}

$baseUrl = "http://127.0.0.1:8081"
Wait-ForMeTube -BaseUrl $baseUrl -Seconds 90
Write-Host "      Aplikasi siap."

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$testFolder = "_smoke_srt_$stamp"
$downloadRoot = Join-Path (Get-Location) "downloads"
$expectedRoot = Join-Path $downloadRoot $testFolder

$payload = @{
    url                    = $Url
    download_type          = "video"
    codec                  = "auto"
    format                 = "any"
    quality                = "worst"
    folder                 = $testFolder
    playlist_item_limit    = 1
    auto_start             = $true
    split_by_chapters      = $false
    subtitle_language      = "en"
    subtitle_mode          = "prefer_manual"
    download_subtitles     = $true
    ytdl_options_presets   = @()
    ytdl_options_overrides = ""
    clip_start             = "0"
    clip_end               = [string]$ClipSeconds
} | ConvertTo-Json -Depth 5

Write-Host "[2/5] Mengirim download video + SRT..."
try {
    $add = Invoke-RestMethod -Method Post -Uri "$baseUrl/add" -ContentType "application/json" -Body $payload -TimeoutSec 30
} catch {
    Fail "API /add gagal: $($_.Exception.Message)"
}
if ($add.status -ne "ok") {
    Fail "MeTube-SRT menolak request: $($add | ConvertTo-Json -Compress)"
}

Write-Host "[3/5] Menunggu download selesai..."
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$item = $null
while ((Get-Date) -lt $deadline) {
    try {
        $history = Invoke-RestMethod -Uri "$baseUrl/history" -TimeoutSec 10
    } catch {
        Start-Sleep -Seconds 2
        continue
    }

    $item = @($history.done) | Where-Object { $_.folder -eq $testFolder } | Select-Object -First 1
    if ($null -ne $item) {
        break
    }
    Start-Sleep -Seconds 2
}

if ($null -eq $item) {
    Fail "Download belum selesai setelah $TimeoutSeconds detik."
}

if ([string]$item.status -eq "error") {
    $message = [string]$item.msg
    if ($message -match "confirm you.*not a bot|Sign in to confirm") {
        Fail "YouTube meminta verifikasi/cookie pada koneksi ini. Aplikasi sudah menerima request, tetapi YouTube memblokir ekstraksi. Tambahkan cookies YouTube lewat fitur cookie MeTube lalu ulangi tes." 2
    }
    Fail "Download gagal dari yt-dlp: $message"
}

Write-Host "[4/5] Memeriksa file hasil..."
if (-not (Test-Path $expectedRoot)) {
    Fail "Folder hasil tidak ditemukan: $expectedRoot"
}

$files = Get-ChildItem -Path $expectedRoot -File -Recurse
$srtFiles = @($files | Where-Object { $_.Extension -ieq ".srt" })
$mediaExtensions = @(".mp4", ".webm", ".mkv", ".mov")
$mediaFiles = @($files | Where-Object { $mediaExtensions -contains $_.Extension.ToLowerInvariant() })

if ($mediaFiles.Count -lt 1) {
    Fail "Tidak ditemukan file video di $expectedRoot"
}
if ($srtFiles.Count -lt 1) {
    Fail "Video berhasil di-download, tetapi tidak ditemukan file .srt. Pastikan video uji memang memiliki subtitle/caption asli."
}

Write-Host "[5/5] LULUS" -ForegroundColor Green
Write-Host "Video:"
$mediaFiles | ForEach-Object { Write-Host "  $($_.FullName)" }
Write-Host "SRT:"
$srtFiles | ForEach-Object { Write-Host "  $($_.FullName)" }
Write-Host ""
Write-Host "Tes end-to-end berhasil: MeTube-SRT menghasilkan video + SRT dari YouTube." -ForegroundColor Green
