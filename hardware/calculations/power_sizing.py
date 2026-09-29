#!/usr/bin/env python3
"""P1.2 motor-current envelope; battery capacity needs measured system power."""

import argparse

from drivetrain_sizing import (
    SELECTED_MOTOR_NO_LOAD_CURRENT_A,
    SELECTED_MOTOR_STALL_CURRENT_A,
    SIZING_MASS_KG,
    linear_motor_current_at_torque,
    sizing_result,
)

MOTOR_BUS_V = 12.0
MOTOR_COUNT = 2


def current_cases():
    sizing = sizing_result(SIZING_MASS_KG)
    return {
        "no_load": SELECTED_MOTOR_NO_LOAD_CURRENT_A,
        "working_estimate": linear_motor_current_at_torque(sizing["wheel_torque"]),
        "design_estimate": linear_motor_current_at_torque(sizing["design_torque"]),
        "stall_extrapolation": SELECTED_MOTOR_STALL_CURRENT_A,
    }


def required_nominal_wh(system_average_w, runtime_h, usable_fraction, reserve_fraction):
    """Nominal pack energy, not a battery or BMS selection."""
    if system_average_w <= 0 or runtime_h <= 0:
        raise ValueError("system average power and runtime must be positive")
    if not 0 < usable_fraction <= 1 or reserve_fraction < 0:
        raise ValueError("usable fraction must be (0, 1], reserve must be >= 0")
    return system_average_w * runtime_h * (1 + reserve_fraction) / usable_fraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-average-w", type=float)
    parser.add_argument("--runtime-h", type=float, default=1.0)
    parser.add_argument("--usable-fraction", type=float, default=0.8)
    parser.add_argument("--reserve-fraction", type=float, default=0.2)
    args = parser.parse_args()

    print("AR-01 P1.2 POWER SIZING (12 V motor baseline)")
    for name, per_motor_a in current_cases().items():
        pair_a = MOTOR_COUNT * per_motor_a
        print(f"{name:20s} {per_motor_a:5.2f} A/motor  {pair_a:5.2f} A/pair")
    print("Stall is a fault envelope, NOT a continuous duty or battery energy estimate.")
    if args.system_average_w is None:
        print("Battery Wh: TBD; measure/enter total average electrical input power.")
    else:
        wh = required_nominal_wh(
            args.system_average_w,
            args.runtime_h,
            args.usable_fraction,
            args.reserve_fraction,
        )
        print(f"Minimum nominal pack energy under supplied assumptions: {wh:.1f} Wh")
        print("Still verify pack voltage range, BMS pulse current, wiring, and fuse.")


if __name__ == "__main__":
    main()
