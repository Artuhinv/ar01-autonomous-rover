# P1.4 mechanical integration preflight (open)

Status: **preflight only** (2026-09-29). This is not a chassis CAD or a purchase
release. P0 URDF stays unchanged because its geometry is a simulation envelope,
not a dimensioned production drawing.

## Known geometry and immediate checks

| Item | Known value | Consequence |
| --- | --- | --- |
| P0 body envelope | 320 × 280 × 100 mm | starting envelope only; no wall/plate thickness or fastener features |
| P0 track / wheel | 310 mm / 100 × 25 mm | simulation kinematics, not yet a physical part pair |
| Candidate wheel #1435 | 90 × 10 mm, 3 mm press-fit bore | needs 6 mm shaft hub #1999; wheel radius becomes 45 mm |
| Candidate motor #4754 | Ø37 × 70 mm body, Ø6 × 16 mm D shaft | official STEP available; validate rear encoder and cable space |
| Candidate bracket #1995 | six gearbox M3 holes, three base M3 holes | official drawing available; mounting screws into gearbox max 3 mm |

If the 310 mm track is kept with 280 mm body and 10 mm tire, the **nominal**
gap between each tire's inner sidewall and the body side is `(310-10-280)/2 =
10 mm`. This ignores hub, fastener heads, tire deformation and mounting
tolerances. It is not a clearance pass. With a 90 mm wheel, 0.60 m/s needs
127.32 RPM, leaving only ~18% no-load speed headroom from the 150 RPM motor;
validate loaded speed on the bench before fixing that wheel. The lower radius
also changes axle height, caster geometry, ground clearance, odometry constants
and stall/traction behavior. Do not copy P0's 100 mm radius into physical code.

## CAD completion gate

1. Import the manufacturer STEP for **the encoder-equipped 37D motor** and the
   dimensioned bracket/hub/wheel geometry into a parametric assembly. Preserve
   source links and measured vs assumed dimensions.
2. Model two motor/bracket/hub/wheel stacks, real screw lengths, full wheel
   rotation envelope, rear encoder leads and minimum cable bend clearance.
3. Select a real caster and check three-point floor contact, ground clearance,
   thresholds, wheel sweep, and body tip envelope.
4. Place battery, driver, Nucleo/interface, DC/DC, E-stop, eventual SBC, LiDAR
   and camera using **actual envelope dimensions** and service access. Record a
   mass table and calculated assembled center of mass; aim for a low, centered
   position between drive axle and caster, then check tip margin.
5. Export annotated drawings and interference report. Recalculate wheel track,
   radius and inertias for a future physical ROS description only after geometry
   is fixed. P0 tag is never rewritten.

This gate is **not met**. No CAD tool or assembly was used in this pass, and
caster, battery and upper sensor envelopes are not selected. Claiming a finished
chassis now would turn unknowns into invented dimensions; all related BOM rows
remain `HOLD`.

Sources: [Pololu motor CAD resources](https://www.pololu.com/product/4754/resources),
[Pololu 90 mm wheel](https://www.pololu.com/product/1435),
[Pololu 6 mm M3 hub](https://www.pololu.com/product/1999),
[Pololu 37D bracket](https://www.pololu.com/product/1995).
