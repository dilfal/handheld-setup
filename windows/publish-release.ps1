<#
.SYNOPSIS
    Pubblica (o aggiorna) la Release windows-v1.0.0 con i 13 archivi driver .zip.
.DESCRIPTION
    Usa GitHub CLI (gh). Il repository dilfal/handheld-setup deve essere pubblico affinche
    `irm ... | iex` possa scaricare lo script e gli asset senza token.
    Gli archivi stanno in windows\drivers\ (cartella ignorata da git).
#>

[CmdletBinding()]
param(
    [string]$RepoName = "dilfal/handheld-setup",
    [string]$ReleaseTag = "windows-v1.0.0",
    [string]$DriversSourceDir = (Join-Path $PSScriptRoot "drivers")
)

$ErrorActionPreference = 'Stop'

$RequiredZips = @(
    "chipset-10.1.18460.8229-public-mup.zip",
    "serialio_30.100.2013.5_pv_tgl-lp_20h1.zip",
    "me_2108.100.0.1053_tgl.zip",
    "intel(r)gna_pvcandidate_02.00.00.1010.zip",
    "intel(r)_dtt_8.7.10400.15556.zip",
    "igfx_win10_100.9616.zip",
    "Audio_2015.6.18_6.0.1.7541.zip",
    "wifi-phwfw01690_21.110.1.1_g.zip",
    "bt-phbtw12144_21.110.0.3g.zip",
    "tbt_dch_1.41.1054.0.zip",
    "9.Cardreader.zip",
    "boschaccelerometer.zip",
    "fingerprint_focaltech_2.0.3.71.zip"
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) non trovato nel PATH."
}

Write-Host "Verifica autenticazione GitHub CLI..." -ForegroundColor Cyan
gh auth status

foreach ($z in $RequiredZips) {
    $full = Join-Path $DriversSourceDir $z
    if (-not (Test-Path -LiteralPath $full)) {
        throw "Archivio driver mancante: $full"
    }
}

$zipPaths = $RequiredZips | ForEach-Object { Join-Path $DriversSourceDir $_ }

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
gh release view $ReleaseTag --repo $RepoName 1>$null 2>$null
$releaseExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap

if (-not $releaseExists) {
    Write-Host "Creazione Release $ReleaseTag e upload dei 13 pacchetti driver (~0,9 GB)..." -ForegroundColor Green
    gh release create $ReleaseTag @zipPaths `
        --repo $RepoName `
        --title "OneXPlayer 1S Drivers ($ReleaseTag)" `
        --notes "Pacchetti driver ufficiali per OneXPlayer 1S (Windows 11) usati da windows/oxp1s.ps1."
    if ($LASTEXITCODE -ne 0) { throw "Errore creazione release $ReleaseTag" }
} else {
    Write-Host "Release $ReleaseTag gia presente. Upload/aggiornamento asset..." -ForegroundColor Green
    gh release upload $ReleaseTag @zipPaths --repo $RepoName --clobber
    if ($LASTEXITCODE -ne 0) { throw "Errore upload asset su $ReleaseTag" }
}

Write-Host ""
Write-Host "Pubblicazione completata!" -ForegroundColor Green
Write-Host "Comando di avvio su Windows 11:" -ForegroundColor Yellow
Write-Host "  irm https://raw.githubusercontent.com/$RepoName/main/windows/oxp1s.ps1 | iex"
