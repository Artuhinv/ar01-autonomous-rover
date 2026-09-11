import math
from types import SimpleNamespace

import pytest

from ar01_tools.cmd_test import normalize_angle, parse_args, yaw_from_quaternion
from ar01_tools.p0_diagnostics import finite, quaternion_rpy


def quaternion_for_yaw(yaw):
    return SimpleNamespace(
        x=0.0,
        y=0.0,
        z=math.sin(yaw / 2.0),
        w=math.cos(yaw / 2.0),
    )


def test_angle_helpers_handle_wraparound():
    assert normalize_angle(3.0 * math.pi) == pytest.approx(math.pi)
    assert normalize_angle(-3.0 * math.pi) == pytest.approx(-math.pi)


def test_quaternion_helpers_recover_yaw():
    quaternion = quaternion_for_yaw(math.radians(90.0))
    assert yaw_from_quaternion(quaternion) == pytest.approx(math.pi / 2.0)
    roll, pitch, yaw = quaternion_rpy(quaternion)
    assert roll == pytest.approx(0.0)
    assert pitch == pytest.approx(0.0)
    assert yaw == pytest.approx(math.pi / 2.0)


def test_default_course_arguments_match_p0_contract():
    options = parse_args(['cmd_test'])
    assert options.distance == pytest.approx(1.0)
    assert options.turn_degrees == pytest.approx(90.0)
    assert options.cmd_topic == '/cmd_vel'
    assert options.odom_topic == '/odom'


def test_finite_rejects_invalid_sensor_values():
    assert finite(0.0, 1.0, -2.5)
    assert not finite(float('nan'))
    assert not finite(float('inf'))
