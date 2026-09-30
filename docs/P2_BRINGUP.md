# P2 physical bring-up record

Status (2026-09-30): **P2.0a cross-build PASS; board bring-up NOT STARTED**.
P0 remains frozen. P1 part choices are engineering baselines, not measured
facts. No purchase, flash, motor connection or physical safety test is claimed.

## What exists now

- STM32CubeMX 6.18.1 `.ioc` for STM32G431R(B)Tx, using the NUCLEO-G431RB
  Morpho/ST-LINK VCP pin plan in [P1 control](P1_CONTROL.md). CubeMX and ST's
  own NUCLEO example use generic `Mcu.CPN=STM32G431RBT3`; the physical Nucleo
  board is STM32G431RBT6. Recheck exact board marking and solder bridges.
- CubeMX-generated startup, linker, HAL init and interrupt vector for Cortex-M4.
  TIM2/TIM4 are quadrature TI12; TIM1 is configured for 20 kHz at the current
  16 MHz clock, but **PWM is not started**. TIM6 is 100 Hz, UART is 115200.
- A separate board adapter compiles the portable COBS/CRC protocol, controller
  core and service into a real ARM ELF. UART RX uses a bounded interrupt ring,
  the 10 ms timer drives the service, and STATUS is scheduled at 50 Hz.
  An IWDG reset is latched into the controller fault status at startup.
- This image is deliberately **motor-disabled**: ARM configuration is zero,
  ADC-to-volts/current conversion is absent, E-stop/DIAG are treated unsafe,
  PA8/PA9 are reclaimed as driven-low GPIO after initialization and PC6–PC9
  remain low. Reset pins are still high-impedance until firmware runs; external
  PWM pulldowns and independent E-stop torque removal are mandatory later.

## Reproduce on another computer

On Windows, install Git, open PowerShell and run:

```powershell
git clone https://github.com/Artuhinv/ar01-autonomous-rover.git
cd ar01-autonomous-rover
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\firmware\ar01_controller\stm32\bootstrap.ps1
```

On Ubuntu 24.04 x86-64, ensure `git`, `curl`, `tar` and `python3` are available:

```bash
git clone https://github.com/Artuhinv/ar01-autonomous-rover.git
cd ar01-autonomous-rover
bash firmware/ar01_controller/stm32/bootstrap.sh
```

Both scripts download the pinned official
[Arm GNU Toolchain 12.3.Rel1](https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain)
and [STM32CubeG4 v1.6.3](https://github.com/STMicroelectronics/STM32CubeG4/tree/v1.6.3)
with its two required HAL/CMSIS submodules, verify the toolchain archive SHA-256
and CubeG4 commit, and then build. Windows uses `%LOCALAPPDATA%\AR01-P2`;
Linux uses `~/.cache/ar01-p2` unless `XDG_CACHE_HOME` is set. The downloads
remain outside the repository. Running the command again reuses the cache.
No administrator privileges or STM32CubeMX installation are needed **to build**.
Install [STM32CubeMX 6.18.1](https://www.st.com/en/development-tools/stm32cubemx.html)
only if you need to inspect or regenerate the `.ioc` and HAL initialization.

The build does not depend on the original computer's files or include a
vendored 50+ MB HAL tree. Output is
`firmware/ar01_controller/stm32/ar01_nucleo_g431rb/build/` with `.elf`, `.hex`,
`.bin` and `.map`; build artifacts are ignored by Git. Reopening the `.ioc` in
CubeMX may require selecting the local G4 firmware package again. Preserve
the `USER CODE` calls in generated `main.c` when regenerating. CubeMX's
generated Windows Makefile contained duplicated absolute source paths here,
so the repository build scripts are authoritative.

To run just the pin/clock guard, use `python` on Windows or `python3` on Linux
with `firmware/ar01_controller/stm32/verify_ioc.py`. To use existing local
dependencies rather than downloading, pass `-ToolchainBin` and `-CubeG4Path`
to `bootstrap.ps1`, or set `AR01_TOOLCHAIN_BIN` and `AR01_CUBEG4_PATH` before
`bootstrap.sh`. Neither script flashes hardware or enables motor drive.

## Evidence on this computer

| Check | Result |
| --- | --- |
| CubeMX 6.18.1 generation | Startup/linker/HAL sources generated; no board attached |
| CubeMX CLI pinout check | `pinout check keep user placement`: OK; hardware routing still unchecked |
| Static `.ioc` guard | 20 assigned pins, 20 kHz TIM1, 100 Hz TIM6, TI12 encoder modes: PASS |
| Arm GNU 12.3.1 cross-build | ELF/BIN/HEX created; 19,192 B text, 12 B data, 2,824 B BSS |
| Fresh Git clone + external CubeG4 | Same image builds without ignored local HAL files: PASS |
| Windows bootstrap | Sparse CubeG4 clone and verified Arm archive extraction: PASS |
| Ubuntu 24.04 x86-64 bootstrap | Verified Arm archive, sparse CubeG4 clone and ARM build: PASS |
| Linked portable functions | `ar01_core_command`, `ar01_service_tick`, COBS/CRC and IRQ handlers present |
| Host regression | Core, service, C/Python protocol interoperability: PASS |
| ST-LINK flash / VCP / GPIO waveform | NOT RUN: board not available |

The linker emits the normal `nosys.specs` warnings for unused console/file
syscalls. There are no build errors. Windows and Linux outputs have the same
memory footprint but are not byte-for-byte identical; compare behavior on
hardware, not a cross-host binary hash. The static guard is not a substitute for
CubeMX visual conflict review or a measured pin-level reset test.

## Next gates — still closed

1. Complete ADC1 sequencing for PB0 current and PC0 VIN (only PB0 is now in
   ADC1's regular conversion rank), analog scaling, DIAG polarity, E-stop
   interface and connector-level schematic. Re-check pin conflicts after edits.
2. On a NUCLEO board **without motor supply**, flash the MCU-only image via
   ST-LINK. Check VCP framing/CRC and 50 Hz STATUS, timeout/watchdog behavior,
   reset cause and scope-measured PWM LOW at boot/reset. Avoid attaching a
   driver until external pulldowns and E-stop torque cut are independently
   verified. No remote flash is attempted without the hardware.
3. Only after a verified drive-capable image and owner purchasing decision,
   release the small engineering-sample set. Battery, LiDAR, SBC, camera,
   custom PCB and full chassis remain HOLD. Then proceed one current-limited
   motor at a time as described in [P1 release](P1_RELEASE.md).

P2.3–P2.8 cannot be closed by compilation or simulation: they require real
parts, metrology and signed-off safety evidence. Do not infer calibrated PID,
encoder counts/rev, current limits or E-stop behavior from this image.
