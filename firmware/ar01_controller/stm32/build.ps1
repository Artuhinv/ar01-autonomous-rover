param(
    [Parameter(Mandatory = $true)][string]$ToolchainBin,
    [string]$CubeG4Path
)

$ErrorActionPreference = 'Stop'
$boardRoot = Join-Path $PSScriptRoot 'ar01_nucleo_g431rb'
$controllerRoot = Split-Path $PSScriptRoot -Parent
$driverRoot = if ($CubeG4Path) { Join-Path $CubeG4Path 'Drivers' } else { Join-Path $boardRoot 'Drivers' }
$gcc = Join-Path $ToolchainBin 'arm-none-eabi-gcc.exe'
$objcopy = Join-Path $ToolchainBin 'arm-none-eabi-objcopy.exe'
$size = Join-Path $ToolchainBin 'arm-none-eabi-size.exe'
foreach ($required in @($gcc, $objcopy, $size,
        (Join-Path $driverRoot 'STM32G4xx_HAL_Driver\Inc\stm32g4xx_hal.h'),
        (Join-Path $driverRoot 'CMSIS\Include\core_cm4.h'))) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing: $required" }
}

$buildRoot = Join-Path $boardRoot 'build'
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
$elf = Join-Path $buildRoot 'ar01_p2_mcu_only.elf'
$hex = Join-Path $buildRoot 'ar01_p2_mcu_only.hex'
$bin = Join-Path $buildRoot 'ar01_p2_mcu_only.bin'
$map = Join-Path $buildRoot 'ar01_p2_mcu_only.map'

$halNames = @(
    'stm32g4xx_hal_adc.c', 'stm32g4xx_hal_adc_ex.c', 'stm32g4xx_ll_adc.c',
    'stm32g4xx_hal.c', 'stm32g4xx_hal_rcc.c', 'stm32g4xx_hal_rcc_ex.c',
    'stm32g4xx_hal_flash.c', 'stm32g4xx_hal_flash_ex.c',
    'stm32g4xx_hal_flash_ramfunc.c', 'stm32g4xx_hal_gpio.c',
    'stm32g4xx_hal_exti.c', 'stm32g4xx_hal_dma.c', 'stm32g4xx_hal_dma_ex.c',
    'stm32g4xx_hal_pwr.c', 'stm32g4xx_hal_pwr_ex.c',
    'stm32g4xx_hal_cortex.c', 'stm32g4xx_hal_iwdg.c',
    'stm32g4xx_hal_uart.c', 'stm32g4xx_hal_uart_ex.c',
    'stm32g4xx_hal_tim.c', 'stm32g4xx_hal_tim_ex.c'
)
$sources = @(
    (Join-Path $boardRoot 'Src\main.c'),
    (Join-Path $boardRoot 'Src\stm32g4xx_it.c'),
    (Join-Path $boardRoot 'Src\stm32g4xx_hal_msp.c'),
    (Join-Path $boardRoot 'Src\system_stm32g4xx.c'),
    (Join-Path $boardRoot 'startup_stm32g431xx.s'),
    (Join-Path $PSScriptRoot 'ar01_board_app.c'),
    (Join-Path $controllerRoot 'control\ar01_core.c'),
    (Join-Path $controllerRoot 'adapter\ar01_service.c'),
    (Join-Path $controllerRoot 'protocol\ar01_link.c'),
    (Join-Path $controllerRoot 'protocol\cobs.c'),
    (Join-Path $controllerRoot 'protocol\crc16.c')
)
foreach ($name in $halNames) { $sources += Join-Path $driverRoot "STM32G4xx_HAL_Driver\Src\$name" }

$includes = @(
    $PSScriptRoot, (Join-Path $boardRoot 'Inc'),
    (Join-Path $controllerRoot 'control'),
    (Join-Path $controllerRoot 'protocol'),
    (Join-Path $controllerRoot 'adapter'),
    (Join-Path $driverRoot 'STM32G4xx_HAL_Driver\Inc'),
    (Join-Path $driverRoot 'STM32G4xx_HAL_Driver\Inc\Legacy'),
    (Join-Path $driverRoot 'CMSIS\Device\ST\STM32G4xx\Include'),
    (Join-Path $driverRoot 'CMSIS\Include')
)
$args = @('-mcpu=cortex-m4', '-mthumb', '-mfpu=fpv4-sp-d16',
    '-mfloat-abi=hard', '-std=c11', '-Os', '-g', '-Wall', '-Wextra',
    '-Werror=implicit-function-declaration', '-ffunction-sections',
    '-fdata-sections', '-DUSE_HAL_DRIVER', '-DSTM32G431xx')
foreach ($include in $includes) { $args += "-I$include" }
$args += $sources
$args += @('-T', (Join-Path $boardRoot 'STM32G431xx_FLASH.ld'),
    '-specs=nano.specs', '-specs=nosys.specs',
    '-Wl,--gc-sections', "-Wl,-Map=$map", '-o', $elf)
& $gcc @args
if ($LASTEXITCODE -ne 0) { throw "ARM link failed: $LASTEXITCODE" }
& $objcopy -O ihex $elf $hex
if ($LASTEXITCODE -ne 0) { throw 'HEX conversion failed' }
& $objcopy -O binary $elf $bin
if ($LASTEXITCODE -ne 0) { throw 'BIN conversion failed' }
& $size $elf
if ($LASTEXITCODE -ne 0) { throw 'Size inspection failed' }
Write-Output "Built: $elf, $hex, $bin"
