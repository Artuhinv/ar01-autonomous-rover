#!/usr/bin/env python3
"""Quasi-static screening, not contact simulation or hardware certification.

P0 point masses/contact centres are taken from ar01_base/sensors.xacro.
Payload cases are hypotheses, not measured physical robot properties.
Run from any directory; writes JSON to stdout only.
"""
import json
import math

# Clockwise support vertices, metres in base_footprint.
SUPPORT = [(0.0, 0.155), (0.0, -0.155), (-0.120, 0.0)]
P0 = [(2.530, -.025, 0., .100), (.150, 0., .155, .050),
      (.150, 0., -.155, .050), (.050, -.120, 0., .025),
      (.100, .070, 0., .175), (.020, -.025, 0., .100)]


def cog(parts):
    mass = sum(p[0] for p in parts)
    return [sum(p[0] * p[i] for p in parts) / mass for i in (1, 2, 3)]


def margin(point):
    """Minimum inward perpendicular distance to the support edges."""
    values = []
    for a, b in zip(SUPPORT, SUPPORT[1:] + SUPPORT[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        values.append(-(dx * (point[1] - a[1]) - dy * (point[0] - a[0]))
                      / math.hypot(dx, dy))
    return min(values)


def screen(parts, acceleration=.5, slope_deg=5.):
    x, y, h = cog(parts)
    # Worst independent slope + inertial-load orientation. Conservative
    # point-load model: neglects suspension, tyre patches, impact and slip.
    shift = h * (math.tan(math.radians(slope_deg))
                 + acceleration / (9.81 * math.cos(math.radians(slope_deg))))
    static = margin((x, y))
    return {'mass_kg': sum(p[0] for p in parts), 'cog_m': [x, y, h],
            'static_edge_margin_mm': static * 1000,
            'worst_load_shift_mm': shift * 1000,
            'worst_edge_margin_mm': (static - shift) * 1000,
            'inside_under_assumptions': static > shift}


def stop_distance(speed, timeout, deceleration):
    # Constant speed during timeout, then constant braking. Actual coasting
    # after motor-power removal needs measurements and may be much longer.
    return speed * timeout + speed ** 2 / (2 * deceleration)


def main():
    print(json.dumps({
        'kind': 'analytical screening, NOT Gazebo results',
        'cases': {
            'P0_3kg': screen(P0),
            'hypothesis_1kg_high_front': screen(P0 + [(1., .070, 0., .250)]),
            'hypothesis_1kg_low_rear': screen(P0 + [(1., -.070, 0., .045)]),
        },
        'timeout_comparison_same_assumptions': {
            'speed_m_s': .6, 'assumed_braking_m_s2': .5,
            'timeout_500ms_stop_m': stop_distance(.6, .5, .5),
            'timeout_200ms_stop_m': stop_distance(.6, .2, .5),
        },
        'limits': ['Point contact support triangle; flat rigid chassis.',
                   'No tyre contact, obstacle, traction or dynamic tip validation.',
                   'Payload locations and braking are hypothetical.',
                   'JGB37-520 torque-speed and encoder calibration remain unknown.'],
    }, indent=2))


if __name__ == '__main__':
    main()
