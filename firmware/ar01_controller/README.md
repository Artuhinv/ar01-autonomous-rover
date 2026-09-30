# AR-01 controller firmware baseline

This directory contains portable C protocol, control-core and service code,
plus a **buildable, motor-disabled P2.0 STM32 image** in `stm32/`. The image
has CubeMX-generated startup/HAL initialization and a minimal UART/timer/encoder
port; it is not a calibrated motor controller or a verified safety system.
Do not connect motor power or treat this ELF as a release-to-drive image.

`protocol/` implements the P1.3 COBS + CRC16-CCITT-FALSE serial frame contract.
`control/` implements DISARMED/ARMED/FAULT transitions, 200 ms command timeout,
modular 32/16-bit encoder deltas, cumulative ticks, bounded PI, current/jam/
DIAG/E-stop/bus fault latching and STATUS serialization. No-motion detection
works even when the current sample is unavailable; its longer timeout and the
high-current jam timeout are both bench-calibrated configuration fields.
Configuration zeros block ARM. Unit-test values are synthetic; **they are not
motor calibration**.
The MCU port must call `ar01_service_tick` from a 10 ms timer, use the returned
signed PWM only after enforcing the physical driver's safe direction sequence,
and force hardware PWM low independently on reset, fault and watchdog reset.
`adapter/ar01_service.c` provides bounded serial frame reception, immediate
DISARM output, 50 Hz STATUS scheduling and a 20 ms control-deadline fault.
It deliberately leaves TIM/ADC/UART/GPIO/IWDG calls to a board-specific port.

Host verification with a C11 compiler (replace `cc` with a compiler path):

```bash
cd firmware/ar01_controller
cc -std=c11 -Wall -Wextra -Werror -Iprotocol -Icontrol \
  protocol/crc16.c protocol/cobs.c protocol/ar01_link.c \
  control/ar01_core.c tests/test_core.c -o test_core
./test_core
cc -std=c11 -Wall -Wextra -Werror -Iprotocol \
  protocol/crc16.c protocol/cobs.c protocol/ar01_link.c \
  tests/interop_cli.c -o interop_cli
python3 tests/test_interop.py ./interop_cli
cc -std=c11 -Wall -Wextra -Werror -Iprotocol -Icontrol -Iadapter \
  protocol/crc16.c protocol/cobs.c protocol/ar01_link.c \
  control/ar01_core.c adapter/ar01_service.c tests/test_service.c -o test_service
./test_service
```

The three output binaries should be built outside the repository or deleted
after testing. Cross-compiling these C files to Cortex-M4 **objects** verifies
syntax/target compatibility only, not linking, timing or board operation.

The checked-in `.ioc`, generated board sources and reproducible ARM build are
documented in [P2 bring-up](../../docs/P2_BRINGUP.md). Remaining before any
drive-enabled image: correct ADC sequencing/scaling, DIAG/E-stop conditioning,
reset-cause reporting, calibrated encoder signs/current thresholds, connector
schematic, external PWM pulldowns, and oscilloscope/bench verification.
