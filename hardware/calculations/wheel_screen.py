#!/usr/bin/env python3
"""P1.4A wheel-diameter screen using the unchanged P1.1 sizing assumptions."""

from drivetrain_sizing import (
    MAX_SPEED_M_S,
    SELECTED_MOTOR_NO_LOAD_RPM,
    SIZING_MASS_KG,
    TORQUE_SAFETY_FACTOR,
    linear_motor_torque_at_speed,
    sizing_result,
    wheel_rpm,
)


def screen(diameter_m):
    if diameter_m <= 0:
        raise ValueError("wheel diameter must be positive")
    force_n = sizing_result(SIZING_MASS_KG)["total_force"]
    required_rpm = wheel_rpm(MAX_SPEED_M_S, diameter_m)
    working_torque_nm = force_n * diameter_m / 4.0
    available_torque_nm = linear_motor_torque_at_speed(required_rpm)
    return {
        "diameter_m": diameter_m,
        "required_rpm": required_rpm,
        "working_torque_nm": working_torque_nm,
        "available_torque_nm": available_torque_nm,
        "design_margin": available_torque_nm
        / (working_torque_nm * TORQUE_SAFETY_FACTOR),
        "no_load_rpm": SELECTED_MOTOR_NO_LOAD_RPM,
    }


if __name__ == "__main__":
    for diameter in (0.09, 0.10):
        result = screen(diameter)
        print(
            f'{diameter * 1000:.0f} mm: '
            f'{result["required_rpm"]:.2f} RPM required; '
            f'{result["working_torque_nm"]:.3f} N m working; '
            f'{result["available_torque_nm"]:.3f} N m available; '
            f'{result["design_margin"]:.2f}x margin'
        )
