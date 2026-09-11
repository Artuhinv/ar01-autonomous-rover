# P1.1 drivetrain sizing

Status: calculated baseline, 2026-09-11. Source values and product availability
must be rechecked immediately before ordering.

## Wheel speed

For wheel diameter `d = 0.100 m`:

```text
wheel_rpm = linear_speed / (pi * wheel_diameter) * 60
```

| Linear speed | Required wheel speed |
| ---: | ---: |
| 0.30 m/s | 57.30 RPM |
| 0.60 m/s | 114.59 RPM |

A 1000 RPM output motor is therefore inappropriate. A practical direct-drive
target is approximately 140-170 no-load RPM, giving control and load reserve
above the 114.59 RPM theoretical minimum.

## Force and torque

The sizing model is:

```text
F_accel   = m * a
F_rolling = Crr * m * g * cos(slope)
F_slope   = m * g * sin(slope)
F_total   = F_accel + F_rolling + F_slope
torque_per_motor = F_total * wheel_radius / 2
design_torque = torque_per_motor * safety_factor
```

Inputs: `g=9.81 m/s²`, `a=0.50 m/s²`, `Crr=0.05`, slope `5 degrees`, wheel
radius `0.050 m`, and two equally loaded drive motors.

| Quantity | 3.2 kg expected mass | 4.0 kg sizing mass |
| --- | ---: | ---: |
| Acceleration force | 1.600 N | 2.000 N |
| Rolling force | 1.564 N | 1.955 N |
| Slope force | 2.736 N | 3.420 N |
| Total tractive force | 5.900 N | 7.375 N |
| Working torque per motor | 0.147 N·m | 0.184 N·m |
| Torque with ×2.5 factor | 0.369 N·m | **0.461 N·m** |

The motor selection target is therefore at least `0.461 N·m` permissible
continuous output torque per motor. This model does not accurately predict tire
scrub during an in-place turn; that can dominate on high-grip carpet and must be
validated on the physical base.

## Exact motor candidates

All three candidates are 12 V brushed gearmotors with integrated quadrature
encoders. Speeds below are manufacturer no-load values; stall torque is not a
safe operating torque.

| Candidate | RPM | Free speed with 100 mm wheel | Stall torque | Stall current | Encoder at output | Mass | Continuous rating |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Pololu 37D 70:1, item 4754** | 150 | 0.785 m/s | 2.648 N·m | 5.5 A | 4480 counts/rev | 205 g | 0.981 N·m recommended max |
| REV Core Hex, REV-41-1300 | 125 | 0.654 m/s | 3.2 N·m | 4.4 A | 288 counts/rev | 198 g | not published |
| goBILDA Yellow Jacket 50.9:1, 5203-2402-0051 | 117 | 0.613 m/s | 6.708 N·m | 9.2 A | 1425.1 pulses/rev | 481 g | not published |

Manufacturer sources:

- [Pololu item 4754](https://www.pololu.com/product/4754): 150 RPM, 5.5 A
  stall, 27 kg·cm extrapolated stall torque, 4480 output counts, 37 x 70 mm,
  and a 10 kg·cm recommended maximum continuous load.
- [REV Core Hex REV-41-1300](https://www.revrobotics.com/rev-41-1300/):
  125 RPM, 4.4 A stall, 3.2 N·m stall torque, and 288 output counts.
- [goBILDA 5203-2402-0051](https://www.gobilda.com/5203-series-yellow-jacket-planetary-gear-motor-50-9-1-ratio-24mm-length-8mm-rex-shaft-117-rpm-3-3-5v-encoder/):
  117 RPM, 9.2 A stall, 68.4 kg·cm stall torque, and 1425.1 output pulses.

Official-site price snapshots on 2026-09-11 were USD 60.95, USD 32.00, and
USD 54.99 per motor respectively, before tax and delivery. They are comparison
data only; local availability can reverse the economic decision.

## Decision

**P1 drivetrain baseline: Pololu item 4754, quantity 2.**

Reasons:

- 150 RPM gives 31% no-load speed headroom over the 100 mm / 0.60 m/s target;
- the documented 0.981 N·m recommended continuous limit is 2.13 times the
  already safety-factored 0.461 N·m requirement;
- 4480 output counts/rev gives about 0.070 mm of ideal wheel travel per count;
- the 37 x 70 mm body and 205 g mass are compatible with the current chassis
  scale, and the manufacturer supplies drawings and STEP models;
- current and torque data are explicit enough to size the next-stage driver.

Using the simple linear DC motor approximation, the motor can provide about
0.625 N·m at the 114.59 RPM needed for 0.60 m/s with a 100 mm wheel. That is
3.39 times the unfactored 0.184 N·m worst-case working torque. At 0.184 N·m,
estimated current is about 0.57 A per motor; this is an estimate, not a battery
or driver rating.

The REV motor remains the lighter-cost alternative, but its 9% speed reserve
and missing continuous-duty rating require a thermal test. The goBILDA motor is
strong but has almost no speed reserve, doubles the motor-pair mass to 962 g,
and raises simultaneous stall current to 18.4 A. Neither is the P1 baseline.

## Mechanical candidate around the selected motor

Pololu's [90 x 10 mm silicone wheel, item 1435](https://www.pololu.com/product/1435/)
can mount to the 6 mm motor shaft through the
[M3 hub pair, item 1999](https://www.pololu.com/product/1999). A
[37D machined bracket, item 1995](https://www.pololu.com/product/1995) is also
available. These exact parts are recorded as candidates in the BOM, not selected
parts: the 90 mm wheel changes required maximum speed to 127.32 RPM and must pass
traction, load, clearance, and CAD checks first.

The existing 310 mm wheel track remains provisional. With a 90 x 10 mm wheel it
would leave approximately 10 mm nominal clearance from each side of the 280 mm
chassis, but the hub and bracket stack must be modeled before this is accepted.

## Boundary passed to P1.2

For the selected motor pair, the motor driver and power protection must be sized
from at least:

```text
nominal motor voltage:       12 V
stall current per channel:   5.5 A
simultaneous pair stall:    11.0 A
encoder resolution:       4480 counts/output revolution
```

The driver should either tolerate the stall current per channel or enforce a
documented current limit below it. No motor driver is selected in P1.1.

## Reproduce the calculation

```bash
python3 hardware/calculations/drivetrain_sizing.py
```
