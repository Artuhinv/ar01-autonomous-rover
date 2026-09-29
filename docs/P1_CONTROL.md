# P1.3 low-level controller and host contract

Status: **development-board baseline plus host-tested portable C core; STM32
integration and purchase release open** (2026-09-29). The controller is
deliberately independent of Gazebo and ROS: the host presents the existing
`/cmd_vel`, `/odom`, and
`/joint_states` contract; the MCU controls wheels and reports raw feedback.

## Development controller

Use **ST NUCLEO-G431RB** as the P1.3 development baseline (`HOLD`). Its
STM32G431RB has hardware quadrature-capable TIM2 and TIM4, PWM-capable TIM1,
ADCs, watchdogs, and a ST-LINK Virtual COM port. This is a **bench board**, not
the final onboard PCB. It should not be stacked directly onto the Pololu driver
as an Arduino shield; connect named signals with a purpose-built harness.

### Proposed pin allocation

| Function | MCU pin / peripheral | Nucleo morpho header | External interface |
| --- | --- | --- | --- |
| Left encoder A/B | PA0/PA1, TIM2 CH1/CH2 | CN7 28/30 | via 5→3.3 V conditioning |
| Right encoder A/B | PB6/PB7, TIM4 CH1/CH2 | CN10 17 / CN7 21 | via 5→3.3 V conditioning |
| Left/right PWM | PA8/PA9, TIM1 CH1/CH2 | CN10 23/21 | M1PWM/M2PWM; external pulldown |
| Left direction A/B | PC6/PC7, GPIO | CN10 4/19 | M1INA/M1INB |
| Right direction A/B | PC8/PC9, GPIO | CN10 2/1 | M2INA/M2INB |
| Left/right fault | PC2/PC3, digital input | CN7 35/37 | M1EN/DIAG/M2EN/DIAG, 3.3 V pull-ups |
| Left/right current | PA4 ADC2 / PB0 ADC1 | CN7 32/34 | M1CS/M2CS, scaled/protected analog inputs |
| Motor-bus voltage | PC0 ADC1/2 | CN7 38 | fused high-impedance divider + filter |
| E-stop loop status | PB5 digital input | CN10 29 | isolated/conditioned status only; not the E-stop actuator |
| ST-LINK Virtual COM | PA2/PA3 LPUART1 | default internal bridge | USB to ROS host during development |

The board manual and MCU datasheet support these peripheral/pin mappings. The
mapping still needs a CubeMX `.ioc` collision review, connector pin-1 drawing,
and oscilloscope verification before wiring. Keep SWD PA13/PA14 free.

**Non-obvious voltage issue:** Pololu 4754 Hall encoders require 3.5–20 V,
produce 0-to-Vcc square waves, and draw up to 10 mA each. Power them from a
regulated 5 V logic rail; do not feed their A/B outputs directly into 3.3 V
STM32 pins. A 3.3 V-powered TI SN74LVC14A is a candidate six-channel Schmitt
buffer with 5.5 V-tolerant inputs. Four channels condition the A/B signals;
both A and B are inverted so relative quadrature order is preserved. Verify
the exact footprint, input thresholds, power sequencing and noise margin in the
harness schematic. Do not derive encoder power from noisy motor VIN.

At 150 wheel RPM, 4480 counts/output revolution produce ~11,200 x4 counts/s.
At the proposed 100 Hz control rate this is ~112 counts/sample. TIM4 is 16-bit:
compute signed modular deltas every cycle; never treat its counter as an
unbounded absolute position. Accumulate both wheels into signed 64-bit totals.
Determine forward encoder sign on the physical bench, not from wire colors.

## Timing and state machine

| Task | Initial rate / rule | Why |
| --- | --- | --- |
| Driver PWM | 20 kHz | within VNH5019 limit, above audible band |
| Encoder/velocity PI loop | 100 Hz, monotonic timer | enough counts/sample, clear 10 ms budget |
| Current and bus ADC | synchronized to PWM drive window | VNH current sense is invalid in coast/brake |
| Telemetry | 50 Hz | count/current/fault feedback to ROS host |
| Host wheel command | 50 Hz recommended | <200 ms firmware command timeout |
| Independent MCU watchdog | enabled; exact window TBD | reset on hung control loop |

Boot → `DISARMED` with PWM hardware-low. The host may request `ARMED` only if
E-stop loop is closed, bus and logic rails are valid, sensors are healthy, and
no fault is latched. A valid speed command does **not** auto-arm. Missing valid
command for 200 ms, stale sequence, bad CRC, encoder plausibility failure,
driver DIAG fault, overcurrent/jam, undervoltage, or watchdog reset causes
`FAULT`/`DISARMED` with both PWMs zero. `CLEAR_FAULT` succeeds only at zero
requested velocity after the cause is removed; no automatic restart. The
hardware E-stop still removes motor supply independently of this state machine.

Initial PI gains, current/jam thresholds, acceleration limits and actual
watchdog period are **TBD bench measurements**, not safe values inferred from
motor datasheets. Windup protection and bounded PWM must be present. Current
sense is a supporting diagnostic, not the sole stall detector: compare commanded
motion with encoder delta and current, and fault on sustained mismatch.

## Wire protocol v1 (C/Python implementation, no MCU transport yet)

Transport: 115200 baud, 8N1 over the Nucleo ST-LINK VCP during development.
The VCP is connected by default to target **LPUART1 on PA2/PA3**; it is not
native target USB-CDC. No ROS or Gazebo messages go into the MCU directly.
Long-term SBC transport may use a dedicated USB-UART adapter without changing
payload semantics. Production connector, ESD and galvanic isolation are TBD.

Each frame is COBS-encoded and terminated by `0x00` (maximum decoded frame
64 bytes). Decoded bytes, all little-endian:

```text
magic u8 = 0xA1 | version u8 = 1 | type u8 | flags u8 = 0 |
sequence u16 | payload_length u8 | payload | CRC16-CCITT-FALSE u16
```

CRC covers header and payload, not CRC or COBS delimiter; polynomial 0x1021,
initial value 0xFFFF, no reflection or final XOR. Unknown version/type/length,
CRC error, or repeated/out-of-order command sequence is rejected without
refreshing the 200 ms watchdog. Sequence wraps modulo 65536; the host starts a
new session with `DISARM` then `ARM`, and MCU clears the accepted sequence at
that boundary. This prevents a stale speed packet from arming motion.

`hardware/protocol/ar01_link.py` is a Python reference encoder/decoder and
test oracle for this frame definition. `firmware/ar01_controller/protocol/` now
implements the same contract in C, with host interoperability tests. Neither
is running on the robot: UART receive framing, error counters and MCU-side
transport are still unimplemented.

| Type | Direction | Payload | Meaning |
| --- | --- | --- | --- |
| `0x01` SET_WHEEL_SPEED | host→MCU | `left_mrad_s i32, right_mrad_s i32` | signed wheel angular velocity, periodic while armed |
| `0x02` ARM | host→MCU | empty | explicit arm request; rejected unless healthy and zero target |
| `0x03` DISARM | host→MCU | empty | always accepted; PWM=0 |
| `0x04` CLEAR_FAULT | host→MCU | empty | only after cause removed and target=0 |
| `0x81` STATUS | MCU→host | `uptime_ms u32, left_ticks i64, right_ticks i64, left_current_mA u16, right_current_mA u16, bus_mV u16, fault_bits u16, state u8, accepted_seq u16` | 50 Hz observation and command acknowledgement |

`mrad_s` is milliradians/second, `ticks` are cumulative signed x4 encoder
counts, currents are nonnegative **drive-window estimates**, and `0xFFFF` means
current unavailable (coast, brake, no valid sample). State codes: 0 DISARMED,
1 ARMED, 2 FAULT. Fault bits: 0 E-stop open, 1 driver fault, 2 left jam/current,
3 right jam/current, 4 bus undervoltage, 5 encoder/plausibility, 6 command
timeout, 7 MCU watchdog-reset latched; other bits reserved. Host must treat
missing STATUS for 200 ms as disconnected, stop publishing fresh odometry and
issue DISARM on reconnection. MCU reports raw counts; ROS host owns wheel radius,
wheel separation, odometry and TF, preserving the P0 interface contract.

## P1.3 exit checks

This document closes **interface selection and portable host-code checks**, not
STM32 or hardware control validation. The C core has host tests for protocol,
encoder wrap, timeout, E-stop and jam fault transitions. The 200 ms timeout is
implemented in the core, but the hardware 10 ms tick and independent watchdog
are not. The C files compile to Cortex-M4 objects; no linked/flashed firmware
is claimed. Before the electrical design is released, provide an `.ioc` or
equivalent checked pin
configuration and a schematic. Before motors are fitted to the chassis, verify
two encoders, 20 kHz PWM, VCP framing/CRC, command timeout, each driver fault,
E-stop with a dead MCU, current-sense calibration, and forward-sign convention
on a current-limited bench supply. No bench result is claimed here. See
[`firmware/ar01_controller/README.md`](../firmware/ar01_controller/README.md)
and [staged release](P1_RELEASE.md).

Sources: [ST NUCLEO-G431RB](https://www.st.com/en/evaluation-tools/nucleo-g431rb.html),
[UM2505 board manual](https://www.st.com/resource/en/user_manual/dm00556337.pdf),
[STM32G431 datasheet](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf),
[Pololu 4754 encoder](https://www.pololu.com/product/4754),
[TI SN74LVC14A](https://www.ti.com/product/SN74LVC14A),
[Pololu VNH5019 guide](https://www.pololu.com/docs/0J49/all).
