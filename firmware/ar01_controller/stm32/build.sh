#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
  echo "Usage: bash build.sh <arm-toolchain-bin> <STM32CubeG4-v1.6.3>" >&2
  exit 2
fi
toolchain_bin="$1"
cube_g4="$2"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
board_dir="$script_dir/ar01_nucleo_g431rb"
controller_dir="$(dirname "$script_dir")"
drivers="$cube_g4/Drivers"
gcc="$toolchain_bin/arm-none-eabi-gcc"
objcopy="$toolchain_bin/arm-none-eabi-objcopy"
size="$toolchain_bin/arm-none-eabi-size"
for required in "$gcc" "$objcopy" "$size" \
  "$drivers/STM32G4xx_HAL_Driver/Inc/stm32g4xx_hal.h" \
  "$drivers/CMSIS/Include/core_cm4.h"; do
  if [[ ! -f "$required" ]]; then echo "Missing: $required" >&2; exit 1; fi
done

build_dir="$board_dir/build"
mkdir -p "$build_dir"
elf="$build_dir/ar01_p2_mcu_only.elf"
hex="$build_dir/ar01_p2_mcu_only.hex"
bin="$build_dir/ar01_p2_mcu_only.bin"
map="$build_dir/ar01_p2_mcu_only.map"

sources=(
  "$board_dir/Src/main.c"
  "$board_dir/Src/stm32g4xx_it.c"
  "$board_dir/Src/stm32g4xx_hal_msp.c"
  "$board_dir/Src/system_stm32g4xx.c"
  "$board_dir/startup_stm32g431xx.s"
  "$script_dir/ar01_board_app.c"
  "$controller_dir/control/ar01_core.c"
  "$controller_dir/adapter/ar01_service.c"
  "$controller_dir/protocol/ar01_link.c"
  "$controller_dir/protocol/cobs.c"
  "$controller_dir/protocol/crc16.c"
)
hal_names=(
  stm32g4xx_hal_adc.c stm32g4xx_hal_adc_ex.c stm32g4xx_ll_adc.c
  stm32g4xx_hal.c stm32g4xx_hal_rcc.c stm32g4xx_hal_rcc_ex.c
  stm32g4xx_hal_flash.c stm32g4xx_hal_flash_ex.c
  stm32g4xx_hal_flash_ramfunc.c stm32g4xx_hal_gpio.c
  stm32g4xx_hal_exti.c stm32g4xx_hal_dma.c stm32g4xx_hal_dma_ex.c
  stm32g4xx_hal_pwr.c stm32g4xx_hal_pwr_ex.c stm32g4xx_hal_cortex.c
  stm32g4xx_hal_iwdg.c stm32g4xx_hal_uart.c stm32g4xx_hal_uart_ex.c
  stm32g4xx_hal_tim.c stm32g4xx_hal_tim_ex.c
)
for name in "${hal_names[@]}"; do sources+=("$drivers/STM32G4xx_HAL_Driver/Src/$name"); done

"$gcc" -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
  -std=c11 -Os -g -Wall -Wextra -Werror=implicit-function-declaration \
  -ffunction-sections -fdata-sections -DUSE_HAL_DRIVER -DSTM32G431xx \
  -I"$script_dir" -I"$board_dir/Inc" \
  -I"$controller_dir/control" -I"$controller_dir/protocol" \
  -I"$controller_dir/adapter" \
  -I"$drivers/STM32G4xx_HAL_Driver/Inc" \
  -I"$drivers/STM32G4xx_HAL_Driver/Inc/Legacy" \
  -I"$drivers/CMSIS/Device/ST/STM32G4xx/Include" \
  -I"$drivers/CMSIS/Include" \
  "${sources[@]}" -T "$board_dir/STM32G431xx_FLASH.ld" \
  -specs=nano.specs -specs=nosys.specs -Wl,--gc-sections \
  "-Wl,-Map=$map" -o "$elf"
"$objcopy" -O ihex "$elf" "$hex"
"$objcopy" -O binary "$elf" "$bin"
"$size" "$elf"
printf 'Built: %s, %s, %s\n' "$elf" "$hex" "$bin"
