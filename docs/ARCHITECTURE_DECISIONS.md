# AR-01 architecture decisions

Status: working decision register, 2026-09-29. This document records **what is
stable and what can change**; it does not approve a part purchase or claim a
hardware test. A decision is revised when evidence changes, not defended for
its own sake.

| Class | Meaning | Change rule |
| --- | --- | --- |
| Goal | Indoor autonomous rover that senses, estimates state, plans/acts, moves and reacts to feedback | Revisit only if the project's purpose changes. |
| Invariant | Safety and software-boundary property | Change only through an explicit safety/architecture review. |
| Baseline | Current engineering choice used for calculations or implementation | Replace when measurements, availability or integration evidence favors another choice. |
| Candidate | Possible part or method awaiting comparison | Compare freely; no purchase implied. |

## Invariants

- A physical, normally-off emergency-stop path can remove motor torque without
  Linux, ROS, MCU firmware or a live serial link. Software DISARM is additional.
- Motor control is closed-loop on measured wheel feedback; missing feedback and
  stale commands cannot silently sustain motion.
- High-level autonomy sends bounded motion intentions, never raw PWM. A hardware
  adapter owns motor electrical behavior and a low-level controller owns wheel
  speed/fault handling.
- Simulation and hardware expose the same ROS command/feedback semantics where
  practical. Changes to `/cmd_vel`, `/odom`, `/joint_states`, `/scan`, IMU or TF
  require an explicit compatibility check rather than accidental drift.
- A sensor or motor driver can be replaced without rewriting the autonomy
  layer. Message meaning is separate from the UART/COBS/CRC transport.
- A fault leads to safe zero drive and requires deliberate recovery; no
  automatic restart after E-stop, watchdog, driver fault or command timeout.

## Revisable baselines and review triggers

| Baseline | Why it is used now | Revisit when |
| --- | --- | --- |
| 2WD differential drive + caster | P0 kinematics and simple indoor base | Tip, traction, threshold or maneuvering tests violate requirements; expect significant sim/ROS changes. |
| Pololu 4754, 12 V, two motors | P1.1 torque/speed and documented encoder data | Loaded RPM, turn current, thermal behavior, cost or supply fails P1 acceptance. |
| Dual VNH5019 #2507 | P1.2 channel current, 3.3 V control and telemetry baseline | Bench shows overheating, current sense or fault behavior insufficient; a properly protected driver has better evidence; voltage changes. |
| NUCLEO-G431RB | Development MCU with proposed timer/ADC/UART resources | Pin/clock/ADC conflict, loop latency or support burden; final PCB is a separate decision. |
| 100 mm wheel diameter | P1.4 analytical speed/torque screen | Measured load/surface data support a different diameter; selected wheel/hub geometry changes track and odometry. |
| ROS 2 Jazzy + Gazebo Harmonic | Completed P0 interface and simulation | Supported-platform lifecycle or integration constraints warrant a planned migration. P0 tag remains immutable. |
| UART 115200 + COBS/CRC16 v1 | Simple development transport and tested message format | Error rate, latency, topology or cable length requires USB CDC, CAN or RS-485; preserve message semantics where useful. |

SN74LVC14A encoder conditioning, exact wheel/hub/caster, battery, SBC, LiDAR,
camera, localization method, behavior system and control-center technology are
**candidates or open choices**, not selected architectures. Compare them only
against written needs and measurements; do not default to a familiar brand or
framework.

## Evidence rule

Every later decision should record: requirement affected, alternatives,
source/measurement, uncertainty, outcome, and what would reverse the outcome.
An analytical calculation is not a bench measurement; host tests are not
STM32 hardware validation. See [P1 staged release](P1_RELEASE.md) for the
current gate toward physical testing and P2.
