# NUCLEO-G431RB board preflight

Status: **document/static review only; CubeMX and board checks NOT PASS**
(2026-09-29). This is a handoff for producing the P1.3B firmware image, not a
wiring authorization.

## Verified from official ST material

- The NUCLEO-G431RB uses STM32G431RBT6. Its STLINK-V3E VCP defaults to target
  LPUART1 on PA2/PA3 through SB17/SB23. This is not target USB CDC.
- UM2505 rev 7 Table 16 lists the proposed Morpho access: PA0/PA1 at CN7
  28/30; PB6/PB7 at CN10 17/CN7 21; PA8/PA9 at CN10 23/21; PA4/PB0/PC0
  at CN7 32/34/38; PC2/PC3 at CN7 35/37; PB5 at CN10 29; PC6/PC7/PC8/PC9
  at CN10 4/19/2/1. The mapping in [P1_CONTROL](P1_CONTROL.md) has no reused
  proposed MCU signal pin and leaves SWD PA13/PA14 free.
- The official STM32CubeG4 v1.6.3 NUCLEO-G431RB example `.ioc` files include
  PA2/PA3 LPUART1 configurations. These demonstrate a manufacturer starting
  point, **not** validation of our combined timer/ADC/PWM pinout.

Sources: [UM2505 rev 7 board manual](https://www.st.com/resource/en/user_manual/um2505-stm32g4-nucleo64-boards-mb1367-stmicroelectronics.pdf),
[STM32G431 datasheet](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf),
[STM32CubeG4 v1.6.3](https://github.com/STMicroelectronics/STM32CubeG4/tree/v1.6.3/Projects/NUCLEO-G431RB),
[CubeMX CLI documentation](https://dev.st.com/stm32cube-docs/stm32cubemx/6.18.0/en/docs/markup/CubeMX_CLI.html).

## CubeMX configuration to generate and review

Start from **NUCLEO-G431RB**, not a bare guessed MCU. Confirm board solder
bridges against the physical revision. Configure TIM2 encoder on PA0/PA1,
TIM4 encoder on PB6/PB7, TIM1 CH1/CH2 PWM on PA8/PA9 at a verified 20 kHz,
LPUART1 PA2/PA3 115200 8N1, ADC inputs PA4/PB0/PC0 with a drive-window
trigger plan, PC2/PC3 DIAG and PB5 E-stop status as digital inputs, PC6–PC9
direction outputs, a 10 ms control timer, and IWDG. Keep SWD enabled. Check
every pin/peripheral/DMA/clock conflict in CubeMX and export both `.ioc` and
generated build files. Review generated reset GPIO states and external PWM
pulldowns before connecting the VNH5019. Generated code alone does not prove
safe PWM edges, ADC scaling or E-stop behavior.

Then compile a complete ELF, inspect the memory map, run logic-only tests over
VCP with **motor supply disconnected**, and record IWDG/reset-cause behavior.
Do not reuse the synthetic host-test PI or current/jam thresholds. Use a
separate, current-limited motor bench only after the schematic and supply
protection review in [P1_RELEASE](P1_RELEASE.md).

## Why this is still open on this computer

STM32CubeMX and STM32CubeIDE are not installed here. ST's official download
flow [requires a myST registration or contact form for some downloads](https://www.st.com/content/st_com/en/about/security-and-privacy/privacy-notices/stm32cube-data-collection-information.html); this
work does not submit another person's identity or use a third-party binary.
No `.ioc` was invented and no firmware ELF, flash or bench PASS is claimed.
The portable service/port boundary in `firmware/ar01_controller/adapter/` can
be integrated once the official tool and board package are available.
