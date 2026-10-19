#!/usr/bin/env python3
"""AR-01 mass-placement and stopping-distance screen; standard library only.

The P0 snapshot is guarded against Xacro drift by test_layout_screen.py.
Loads below are worst-case magnitudes, not directional contact simulation.
Run from any directory: python hardware/calculations/layout_screen.py
"""

from dataclasses import dataclass
import json
import math


P0_SOURCE_REVISION = "b44241e5586dca83179f7727edc19ef4aeb58ed6"
GRAVITY_M_S2 = 9.81
# Clockwise point contacts, metres in base_footprint, on the support plane.
SUPPORT_M = ((0.0, 0.155), (0.0, -0.155), (-0.120, 0.0))


@dataclass(frozen=True)
class MassPoint:
    name: str
    mass_kg: float
    x_m: float
    y_m: float
    z_m: float


P0_POINTS = (
    MassPoint("body", 2.530, -0.025, 0.0, 0.100),
    MassPoint("left_wheel", 0.150, 0.0, 0.155, 0.050),
    MassPoint("right_wheel", 0.150, 0.0, -0.155, 0.050),
    MassPoint("caster", 0.050, -0.120, 0.0, 0.025),
    MassPoint("lidar", 0.100, 0.070, 0.0, 0.175),
    MassPoint("imu", 0.020, -0.025, 0.0, 0.100),
)


def _finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def centre_of_mass(parts):
    parts = tuple(parts)
    if not parts:
        raise ValueError("at least one mass point is required")
    for point in parts:
        if _finite(point.mass_kg, "mass") <= 0:
            raise ValueError("mass must be positive")
        for axis in ("x_m", "y_m", "z_m"):
            _finite(getattr(point, axis), axis)
        if point.z_m < 0:
            raise ValueError("height above the support plane must be nonnegative")
    mass = math.fsum(point.mass_kg for point in parts)
    return tuple(
        math.fsum(point.mass_kg * getattr(point, axis) for point in parts) / mass
        for axis in ("x_m", "y_m", "z_m")
    )


def static_margin(point):
    """Minimum inward edge distance in metres; negative is outside support."""
    x, y = (_finite(value, "coordinate") for value in point)
    distances = []
    for a, b in zip(SUPPORT_M, SUPPORT_M[1:] + SUPPORT_M[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        distances.append(-(dx * (y - a[1]) - dy * (x - a[0]))
                         / math.hypot(dx, dy))
    return min(distances)


def screen(parts, acceleration_m_s2=0.5, slope_deg=5.0):
    """Screen the worst independent slope/load orientation.

    Signed acceleration and slope inputs are treated as magnitudes. To study
    a particular direction, use a directional dynamics model instead.
    """
    parts = tuple(parts)
    acceleration = abs(_finite(acceleration_m_s2, "acceleration"))
    slope = abs(_finite(slope_deg, "slope"))
    if slope >= 90:
        raise ValueError("absolute slope must be less than 90 degrees")
    x, y, height = centre_of_mass(parts)
    theta = math.radians(slope)
    shift = height * (math.tan(theta)
                      + acceleration / (GRAVITY_M_S2 * math.cos(theta)))
    margin = static_margin((x, y))
    return {
        "mass_kg": math.fsum(point.mass_kg for point in parts),
        "cog_m": [x, y, height],
        "acceleration_m_s2": acceleration,
        "absolute_slope_deg": slope,
        "static_edge_margin_mm": margin * 1000,
        "worst_load_shift_mm": shift * 1000,
        "worst_edge_margin_mm": (margin - shift) * 1000,
        "inside_under_assumptions": margin > shift,
    }


def stop_distance(speed_m_s, timeout_s, deceleration_m_s2):
    """Travel magnitude: constant speed during timeout, then stated braking.

    This does not model coasting after removing PWM or motor power.
    """
    speed = abs(_finite(speed_m_s, "speed"))
    timeout = _finite(timeout_s, "timeout")
    deceleration = _finite(deceleration_m_s2, "deceleration")
    if timeout < 0 or deceleration <= 0:
        raise ValueError("timeout must be nonnegative and deceleration positive")
    return speed * timeout + speed * speed / (2 * deceleration)


def report():
    return {
        "kind": "AR-01 analytical screening; not Gazebo or hardware results",
        "model": {
            "p0_revision": P0_SOURCE_REVISION,
            "frame": "base_footprint",
            "support_m": SUPPORT_M,
            "source_files": ["src/ar01_description/urdf/ar01_base.xacro",
                             "src/ar01_description/urdf/ar01_sensors.xacro"],
        },
        "cases": {
            "P0_3kg": screen(P0_POINTS),
            "hypothesis_1kg_high_front": screen(P0_POINTS + (
                MassPoint("payload", 1.0, 0.070, 0.0, 0.250),)),
            "hypothesis_1kg_low_rear": screen(P0_POINTS + (
                MassPoint("payload", 1.0, -0.070, 0.0, 0.045),)),
        },
        "timeout_comparison_same_assumptions": {
            "speed_m_s": 0.6,
            "assumed_braking_m_s2": 0.5,
            "timeout_500ms_stop_m": stop_distance(0.6, 0.5, 0.5),
            "timeout_200ms_stop_m": stop_distance(0.6, 0.2, 0.5),
        },
        "limits": [
            "Rigid chassis and three point contacts; no impact or tyre model.",
            "Worst independent load orientations, not directional simulation.",
            "Payload positions and braking are hypotheses, not measurements.",
            "Positive margin alone does not prove physical stability.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, allow_nan=False))
