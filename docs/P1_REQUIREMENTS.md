# P1 physical AR-01 requirements

Status: P1.1 engineering baseline, 2026-09-11. This document defines the
numbers used to size the drivetrain. It is not a purchase authorization.

## Scope

P1 defines a buildable indoor AR-01 v1 while preserving the P0 ROS contract.
The first physical tests may use the development laptop over USB instead of an
onboard Linux computer.

The architecture remains:

```text
ROS 2 computer -> USB/UART -> STM32 -> motor driver -> two motors
                                      ^               |
                                      +--- encoders --+
```

The higher-level interfaces remain `/cmd_vel`, `/odom`, `/joint_states`,
`/scan`, `/imu/data`, `/tf`, and `/tf_static`.

## Quantitative requirements

| ID | Requirement | P1.1 value |
| --- | --- | ---: |
| PHY-01 | Operating environment | apartment / indoor rooms |
| PHY-02 | Drive topology | 2WD differential + passive caster |
| PHY-03 | P0 modeled mass | 3.0 kg |
| PHY-04 | Expected physical mass | 3.2 kg |
| PHY-05 | Drivetrain sizing mass | 4.0 kg |
| PHY-06 | Nominal wheel diameter | 100 mm |
| MOT-01 | Nominal speed | 0.30 m/s |
| MOT-02 | Maximum level-floor speed | 0.60 m/s |
| MOT-03 | Target linear acceleration | 0.50 m/s² |
| MOT-04 | Continuous design slope | 5 degrees / 8.7% grade |
| MOT-05 | Floor types | laminate, linoleum, low-pile carpet |
| MOT-06 | Provisional rolling coefficient for sizing | 0.05 |
| MOT-07 | Drivetrain torque safety factor | 2.5 |
| PWR-01 | Motor bus baseline | 12 V DC |
| PWR-02 | Minimum target runtime | 60 minutes |
| SYS-01 | Low-level wheel feedback | quadrature encoders |
| SYS-02 | Initial ROS computer | development laptop allowed |
| SYS-03 | Onboard SBC | deferred until its compute load is known |

The 4.0 kg sizing mass includes 25% growth over the expected 3.2 kg physical
mass. The rolling coefficient is deliberately conservative for a small wheel on
carpet, but it is still an assumption rather than a measured property.

Maximum speed is required on level flooring. The sizing force combines the
4.0 kg mass, 0.50 m/s² acceleration, rolling resistance, and a 5 degree slope to
avoid selecting a motor from a best-case calculation.

## Drivetrain acceptance criteria

A selected drive motor must satisfy all of the following:

1. Operate from the 12 V motor bus.
2. Provide enough output speed for 0.60 m/s with a wheel near 100 mm, including
   useful speed reserve above the theoretical 115 RPM minimum.
3. Provide at least 0.461 N·m permissible continuous output torque per wheel,
   or have a manufacturer curve plus thermal test proving an equivalent duty.
4. Include a quadrature encoder with a documented output-shaft resolution.
5. Publish a trustworthy stall current so the driver and protection can be
   selected from data rather than guesswork.
6. Have a drawing or CAD model suitable for designing the motor mount.
7. Fit two motors, mounts, wheels, and wiring within the planned chassis.

## Items deliberately not fixed in P1.1

- final wheel and hub;
- confirmed wheel track and chassis width;
- motor driver and current limiting;
- battery chemistry, capacity, fuse, emergency stop, and DC/DC converters;
- exact STM32 board and serial protocol;
- physical LiDAR, IMU, and onboard Linux computer;
- final CAD.

These are controlled follow-on decisions, not missing assumptions. Hardware in
`hardware/BOM.csv` stays in `HOLD` state until the dependent calculations and
CAD checks are complete.

## Measurements required before purchase release

- weigh the planned payload or confirm the 3.2 kg estimate;
- measure the tallest floor transition and carpet pile;
- confirm the desired 5 degree continuous slope;
- verify that 0.60 m/s is acceptable indoors;
- check local availability and delivered price of the selected motor pair;
- validate wheel traction and in-place turning on the real floor.
