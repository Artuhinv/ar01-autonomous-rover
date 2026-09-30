param(
    [string]$CacheRoot = (Join-Path $env:LOCALAPPDATA 'AR01-P2'),
    [string]$ToolchainBin,
    [string]$CubeG4Path
)

$ErrorActionPreference = 'Stop'
$armVersion = '12.3.rel1'
$armFolder = "arm-gnu-toolchain-$armVersion-mingw-w64-i686-arm-none-eabi"
$armArchive = "$armFolder.zip"
$armUrl = "https://developer.arm.com/-/media/Files/downloads/gnu/$armVersion/binrel/$armArchive"
$armSha256 = 'D52888BF59C5262EBF3E6B19B9F9E6270ECB60FD218CF81A4E793946E805A654'
$cubeCommit = 'd11b194a9f05d1b143d154771f3dbc282c8052a5'
$cubeUrl = 'https://github.com/STMicroelectronics/STM32CubeG4.git'

function Assert-LastExit([string]$action) {
    if ($LASTEXITCODE -ne 0) { throw "$action failed (exit $LASTEXITCODE)" }
}

if (!$ToolchainBin -or !$CubeG4Path) {
    New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
}

if (!$ToolchainBin) {
    $ToolchainBin = Join-Path $CacheRoot "$armFolder\bin"
    $gcc = Join-Path $ToolchainBin 'arm-none-eabi-gcc.exe'
    if (!(Test-Path -LiteralPath $gcc)) {
        $archivePath = Join-Path $CacheRoot $armArchive
        if (!(Test-Path -LiteralPath $archivePath)) {
            Write-Output "Downloading official Arm GNU $armVersion toolchain (~337 MB)..."
            Invoke-WebRequest -Uri $armUrl -OutFile $archivePath -TimeoutSec 1800
        }
        $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
        if ($actualHash -ne $armSha256) {
            throw "Arm archive SHA256 mismatch at $archivePath; expected $armSha256, got $actualHash"
        }
        $installDir = Join-Path $CacheRoot $armFolder
        if (Test-Path -LiteralPath $installDir) {
            throw "Incomplete toolchain directory: $installDir; inspect it before retrying"
        }
        Write-Output 'Extracting Arm GNU toolchain...'
        Expand-Archive -LiteralPath $archivePath -DestinationPath $CacheRoot
    }
}

if (!$CubeG4Path) {
    $CubeG4Path = Join-Path $CacheRoot 'STM32CubeG4-v1.6.3'
    if (!(Test-Path -LiteralPath $CubeG4Path)) {
        Write-Output 'Cloning official STM32CubeG4 v1.6.3 (sparse)...'
        git clone --filter=blob:none --sparse --depth 1 --branch v1.6.3 $cubeUrl $CubeG4Path
        Assert-LastExit 'STM32CubeG4 clone'
    }
    git -C $CubeG4Path sparse-checkout set Drivers
    Assert-LastExit 'STM32CubeG4 sparse checkout'
    git -C $CubeG4Path submodule update --init --depth 1 Drivers/STM32G4xx_HAL_Driver Drivers/CMSIS/Device/ST/STM32G4xx
    Assert-LastExit 'STM32CubeG4 submodules'
}

$gcc = Join-Path $ToolchainBin 'arm-none-eabi-gcc.exe'
if (!(Test-Path -LiteralPath $gcc)) { throw "Missing Arm GCC: $gcc" }
$actualCubeCommit = (git -C $CubeG4Path rev-parse HEAD).Trim()
Assert-LastExit 'STM32CubeG4 revision check'
if ($actualCubeCommit -ne $cubeCommit) {
    throw "STM32CubeG4 revision mismatch: expected $cubeCommit, got $actualCubeCommit"
}

Write-Output "Arm GNU: $gcc"
Write-Output "STM32CubeG4: $CubeG4Path ($cubeCommit)"
& (Join-Path $PSScriptRoot 'build.ps1') -ToolchainBin $ToolchainBin -CubeG4Path $CubeG4Path
Assert-LastExit 'AR-01 firmware build'
