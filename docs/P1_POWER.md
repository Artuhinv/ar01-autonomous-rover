# P1.2 motor driver and power architecture

Status: **engineering baseline, not purchase release** (2026-09-29). P0 remains
frozen. All physical parts currently stay `HOLD`; a limited development-sample
release can precede bench measurements only under [Gate A](P1_RELEASE.md).
Full robot parts remain gated on bench and mechanical evidence.

## Motor current envelope

The P1.1 12 V Pololu 4754 motor has 0.20 A no-load and **5.5 A extrapolated
stall** current. Interpolating current against the P1.1 torque model gives:

| Case | Torque / motor | Estimated A / motor | Pair A | Interpretation |
| --- | ---: | ---: | ---: | --- |
| No load | ~0 | 0.20 | 0.40 | datasheet point, not driving load |
| Working sizing case | 0.184 N m | 0.57 | 1.14 | model; 4 kg, slope + acceleration |
| ×2.5 design point | 0.461 N m | 1.12 | 2.25 | margin case, not measured duty |
| Both motors stalled | — | 5.5 | 11.0 | fault envelope, never continuous operation |

The simple interpolation is useful for first sizing, **not** a measured current
trace. Starts, carpet turns, wheel jams and regenerative braking need bench
tests. Pololu warns that stall can damage the motor within seconds and generally
recommends no more than 25% of stall current in continuous use. At 12 V, 11 A is
therefore a supply/transient *capability* check, not a 132 W runtime budget.

Run `python hardware/calculations/power_sizing.py` to reproduce the figures.

## Driver decision

| Candidate | Relevant manufacturer data | Decision |
| --- | --- | --- |
| **Pololu Dual VNH5019 #2507** | 5.5–24 V, 12 A continuous/channel, 30 A brief/channel, 20 kHz PWM, 3.3 V logic, ~140 mV/A current sense, combined EN/DIAG, reverse-voltage protection to -16 V | **P1.2 baseline**, `HOLD` |
| Cytron MDD10A | 5–30 V, 10 A continuous/channel, 3.3 V controls; no reverse-polarity protection | alternative if external current monitoring and protection are designed |
| Pololu Dual G2 18v18 #3751 | 6.5–30 V, 18 A continuous/channel, ~20 mV/A sense, ~50 A default current limit; Raspberry Pi form factor | over-sized and default limit does not protect 5.5 A-stall motors |

The VNH5019 covers each motor's 5.5 A stall envelope with thermal headroom and
gives current and fault telemetry. Its **current sense is not a precise hardware
current limiter**. Firmware must detect overcurrent / low encoder motion and
disable both channels promptly; the driver's thermal/short protections are last
resorts, not a normal control strategy. Current sense is valid only while an
H-bridge is driving, not during coast/brake; sample in the PWM drive window and
calibrate on the bench. The board's EN/DIAG pins require 2.5–5 V `VDD` to power
their pull-ups (use 3.3 V); set both PWM inputs low at boot/reset. Do **not**
fit the optional Arduino-power jumper when connecting a Nucleo board.

### Fault response contract (to be verified on hardware)

| Event | Required response |
| --- | --- |
| One wheel stalls / overcurrent | firmware latches fault, PWM=0 both channels, reports offending side and current; no auto-restart |
| Both wheels stall | same; battery/BMS and branch wiring must tolerate the initial 11 A nominal-voltage transient until trip |
| Reverse battery | keyed connector and system-level reverse-polarity protection upstream of **both** branches; VNH5019 board protection is only local and rated to -16 V |
| Motor output short / driver thermal fault | VNH5019 protection operates; MCU sees EN/DIAG low, latches fault, inhibits restart |
| Battery/branch short | appropriately rated fuse close to battery; final rating depends on pack, BMS, wire and connector selection |
| Emergency stop | latching, normally-closed physical switch opens motor-power contactor/switch; software command alone is insufficient |
| Logic brownout / communication timeout | MCU outputs default disabled; external motor-power cut remains independently operable |

Do not use the fuse or BMS as a routine stall limiter. A short-circuit interrupt
rating, fuse curve, contactor DC rating, and wiring temperature rise must be
checked together after the battery and cable lengths are selected.

## Power topology

```text
BATTERY (chemistry / voltage range / BMS TBD)
  -> main DC fuse near pack -> reverse-polarity protection -> distribution
       |-> separately protected LOGIC branch -> regulated 5 V / 3.3 V
       |      -> STM32, encoder 5 V, later SBC and sensors
       |-> MOTOR branch fuse -> latching E-stop -> DC-rated contactor/switch
              -> VNH5019 VIN -> left/right 12 V motors
common reference at planned star/return point; no motor current through MCU GND
```

The **motor branch alone** is interrupted by E-stop so the MCU can report the
fault. The contactor requires a defined normally-off state and a series hardware
loop independent of ROS/firmware. Driver PWM must be disabled on E-stop; opening
a motor supply during regeneration can raise bus voltage, so characterize this
with a scope and choose adequate suppression/bulk capacitance/contact sequence.
No exact TVS/fuse/contactor part is approved yet. E-stop is not a substitute for
unplugging the pack when servicing.

12 V is a motor **nominal** target, not an approved pack chemistry. The driver
operates from 5.5–24 V but a 24 V battery is explicitly discouraged, and a 12 V
motor must not simply be fed from any higher-voltage pack. Check fully charged,
loaded-minimum, regenerative maximum, and controller brownout voltages before
fixing a pack. The battery/BMS must sustain normal loads and tolerate at least
the 11 A **motor-only** simultaneous-stall transient at a nominal 12 V, plus
logic peak and design margin, until electronic shutdown. A battery choice and
firmware threshold require bench validation; these numbers do not authorize a
particular cell chemistry or pack.

## Power-budget worksheet (unfilled inputs are intentional)

| Load | Nominal/average electrical input W | Peak electrical input W | Evidence |
| --- | ---: | ---: | --- |
| Two motors | TBD from duty-cycle measurement | up to 132 W at nominal 12 V and extrapolated simultaneous stall, transient only | Pololu 4754 / P1.1 |
| STM32 + interface board | TBD | TBD | board power measurement |
| Encoder 5 V supply | TBD | TBD | <=10 mA per encoder sensor from motor datasheet, plus conversion loss |
| SBC or development laptop | TBD / external if laptop | TBD | chosen platform |
| LiDAR | TBD | TBD | chosen part |
| IMU | TBD | TBD | chosen part |
| Camera | TBD | TBD | chosen part |
| DC/DC losses | TBD | TBD | selected converter efficiency at load |

After measuring/sourcing every row, calculate `P_system_average` **at the pack
terminals**. For 1 h required runtime, `nominal Wh >= P_system_average × 1 h ×
(1 + reserve_fraction) / usable_fraction`. The script accepts an optional
`--system-average-w` to evaluate this only when data exists; its default 20%
reserve and 80% usable fraction are illustrative, not battery approvals.

## Gate before full-robot purchase / P2 wiring

- Select pack and BMS with documented full/empty voltage and peak-current curve.
- Measure motor start, hard turn, stall trip time/current, and driver temperature.
- Pick fuse, wiring, connector, reverse-polarity element, DC/DC, contactor and
  suppression from those measurements and manufacturer's DC ratings.
- Test E-stop with MCU disconnected; verify motor torque removed but logic alive.
- Verify current-sense ADC scaling and fault detection with injected faults.
- Confirm logic rail under worst motor transient and regenerative bus maximum.

Sources: [Pololu 4754](https://www.pololu.com/product/4754),
[VNH5019 #2507](https://www.pololu.com/product/2507),
[VNH5019 guide](https://www.pololu.com/docs/0J49/all),
[Cytron MDD10A](https://my.cytron.io/education-motor-driver),
[Cytron polarity note](https://my.cytron.io/tutorial/using-mdd10a-arduino-uno),
[Pololu G2 #3751](https://www.pololu.com/product/3751).
