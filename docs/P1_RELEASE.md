# P1.5 staged release and P2 handoff

Status: **engineering-sample plan defined; no purchase released** (2026-09-29).
P2.0 now has a motor-disabled ARM image, but the purchase gate remains closed;
see [P2 bring-up](P2_BRINGUP.md). The table below is the historical P1 snapshot.
This resolves a circular gate: motor/driver/MCU bench measurements cannot exist
until a small set of engineering samples exists. It does **not** approve a full
robot build, battery, chassis or custom PCB.

## Gate A evidence snapshot

| Item | State | Evidence / missing work |
| --- | --- | --- |
| Host protocol/control/service | PASS on host only | C unit tests and C↔Python interoperability; see firmware README. |
| Pin map | PAPER REVIEW | Board/VCP and Morpho mapping checked against ST UM2505; combined configuration must still pass CubeMX. |
| CubeMX `.ioc` and complete STM32 ELF | OPEN | Official tool not installed; no generated startup, HAL port, linker or image. |
| Connector schematic and reset-low PWM proof | OPEN | External pull-downs, direction sequence, signal conditioning and E-stop loop need review. |
| Current-limited fixture and actual parts | OPEN | No fixture, samples or measurements recorded in the repository. |
| Owner purchase decision | HOLD | No budget/seller/availability approval recorded. |

**Gate A remains CLOSED.** See [board preflight](P1_BOARD_PREFLIGHT.md).

## Gate A — development samples only

Candidate minimum set: two Pololu 4754 motors, one Pololu Dual VNH5019 #2507,
one NUCLEO-G431RB, a suitable SN74LVC14A encoder-interface implementation,
and the explicitly designed harness/protection parts. Confirm current stock,
seller, delivery, exact suffixes, local tax and total cost immediately before
any order. All BOM rows remain `HOLD`; a purchasing decision belongs to the
owner, not to this document.

Before Gate A is released, complete the CubeMX `.ioc` pin/peripheral collision
review, connector-level schematic, PWM-low reset design review, independent
E-stop bench-wiring plan and parts, and a **buildable** STM32 firmware image with watchdog, UART,
encoders, ADC and PWM adapter. Host-compiled control code alone is not that
image. The board may be powered first by USB for logic tests. Motor tests use
an adjustable current-limited bench supply with appropriate protection and a
secured free-wheel fixture; **no battery is required** for Gate A. Set limits
from a written test procedure and observe actual current/temperature.

## Gate B — full physical robot, still closed

Release battery/BMS, DC/DC, fuses, contactor/E-stop hardware, wiring, wheels,
caster, chassis, upper computing/sensors and any custom PCB only after:

1. Two-channel encoder sign/count and PWM/DIAG/ADC calibration on the bench.
2. Start, turn, stall and jam time/current/temperature measurements, including
   both-wheel fault response and recovery without automatic restart.
3. E-stop torque removal with MCU disconnected, plus supply/transient and
   brownout measurements.
4. A dimensioned CAD assembly and mass/center-of-gravity/tip analysis for
   selected wheel and all chosen payloads.
5. Pack/BMS, fuse, cable, connector, DC/DC and contactor coordination based on
   those loads and manufacturer ratings.
6. Hardware ROS adapter demonstrating the P0 `/cmd_vel`, `/odom`,
   `/joint_states` contract using real feedback; P0 simulation remains frozen.

## Evidence still missing for P2

P1.3 host logic is testable, but STM32 peripheral integration and hardware
fault tests are absent. P1.4 has wheel-size screening, not CAD. P1.5 has a
two-stage release rule, not released purchases. Therefore **P2 is not yet a
safe implementation start**. The next concrete work is CubeMX configuration
and a flashable firmware adapter, then owner-approved development samples and
bench evidence. Do not infer test PASS from an unfilled checklist.
