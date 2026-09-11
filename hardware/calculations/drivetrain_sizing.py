#!/usr/bin/env python3

import math


GRAVITY_M_S2 = 9.81
EXPECTED_MASS_KG = 3.2
SIZING_MASS_KG = 4.0
WHEEL_DIAMETER_M = 0.100
NOMINAL_SPEED_M_S = 0.30
MAX_SPEED_M_S = 0.60
ACCELERATION_M_S2 = 0.50
ROLLING_COEFFICIENT = 0.05
SLOPE_DEGREES = 5.0
TORQUE_SAFETY_FACTOR = 2.5
KG_CM_TO_N_M = 0.0980665

SELECTED_MOTOR_NO_LOAD_RPM = 150.0
SELECTED_MOTOR_NO_LOAD_CURRENT_A = 0.2
SELECTED_MOTOR_STALL_CURRENT_A = 5.5
SELECTED_MOTOR_STALL_TORQUE_N_M = 27.0 * KG_CM_TO_N_M
SELECTED_MOTOR_CONTINUOUS_LIMIT_N_M = 10.0 * KG_CM_TO_N_M


def wheel_rpm(linear_speed, wheel_diameter):
    return linear_speed / (math.pi * wheel_diameter) * 60.0


def sizing_result(mass):
    slope = math.radians(SLOPE_DEGREES)
    acceleration_force = mass * ACCELERATION_M_S2
    rolling_force = (
        ROLLING_COEFFICIENT * mass * GRAVITY_M_S2 * math.cos(slope)
    )
    slope_force = mass * GRAVITY_M_S2 * math.sin(slope)
    total_force = acceleration_force + rolling_force + slope_force
    wheel_torque = total_force * (WHEEL_DIAMETER_M / 2.0) / 2.0
    return {
        'acceleration_force': acceleration_force,
        'rolling_force': rolling_force,
        'slope_force': slope_force,
        'total_force': total_force,
        'wheel_torque': wheel_torque,
        'design_torque': wheel_torque * TORQUE_SAFETY_FACTOR,
    }


def linear_motor_torque_at_speed(speed_rpm):
    speed_fraction = speed_rpm / SELECTED_MOTOR_NO_LOAD_RPM
    return SELECTED_MOTOR_STALL_TORQUE_N_M * max(0.0, 1.0 - speed_fraction)


def linear_motor_current_at_torque(torque):
    torque_fraction = torque / SELECTED_MOTOR_STALL_TORQUE_N_M
    current_span = (
        SELECTED_MOTOR_STALL_CURRENT_A - SELECTED_MOTOR_NO_LOAD_CURRENT_A
    )
    return SELECTED_MOTOR_NO_LOAD_CURRENT_A + current_span * torque_fraction


def main():
    print('AR-01 P1.1 DRIVETRAIN SIZING')
    print(
        f'nominal wheel speed: '
        f'{wheel_rpm(NOMINAL_SPEED_M_S, WHEEL_DIAMETER_M):.2f} RPM'
    )
    print(
        f'maximum wheel speed: '
        f'{wheel_rpm(MAX_SPEED_M_S, WHEEL_DIAMETER_M):.2f} RPM'
    )

    for mass in (EXPECTED_MASS_KG, SIZING_MASS_KG):
        result = sizing_result(mass)
        print(f'\nmass: {mass:.1f} kg')
        print(f'  acceleration force: {result["acceleration_force"]:.3f} N')
        print(f'  rolling force:      {result["rolling_force"]:.3f} N')
        print(f'  slope force:        {result["slope_force"]:.3f} N')
        print(f'  total force:        {result["total_force"]:.3f} N')
        print(f'  wheel torque:       {result["wheel_torque"]:.3f} N m')
        print(f'  design torque:      {result["design_torque"]:.3f} N m')

    maximum_rpm = wheel_rpm(MAX_SPEED_M_S, WHEEL_DIAMETER_M)
    sizing = sizing_result(SIZING_MASS_KG)
    available_at_maximum_speed = linear_motor_torque_at_speed(maximum_rpm)
    estimated_working_current = linear_motor_current_at_torque(
        sizing['wheel_torque']
    )
    print('\nselected motor: Pololu 4754')
    print(
        f'  continuous torque margin: '
        f'{SELECTED_MOTOR_CONTINUOUS_LIMIT_N_M / sizing["design_torque"]:.2f}x'
    )
    print(
        f'  torque available at {maximum_rpm:.2f} RPM: '
        f'{available_at_maximum_speed:.3f} N m'
    )
    print(
        f'  speed-point torque margin: '
        f'{available_at_maximum_speed / sizing["wheel_torque"]:.2f}x'
    )
    print(f'  estimated current at working torque: {estimated_working_current:.2f} A')


if __name__ == '__main__':
    main()
