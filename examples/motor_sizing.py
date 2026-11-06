# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""motor_sizing.py - size a servo motor for a ball-screw axis.

QUESTION
    A 40 kg carriage on a ball screw (10 mm lead) must move 300 mm in 0.6 s
    with a trapezoidal profile, then dwell 0.4 s, repeatedly. Which motor
    from a short catalogue handles the peak and RMS torque, and keeps the
    load-to-rotor inertia ratio reasonable?

APPROACH
    1. Motion profile -> peak speed and acceleration (1/3 accel, 1/3 cruise,
       1/3 decel - a common starting assumption).
    2. Thrust from friction + inertia; torque via Mechatronics.ballscrew_torque.
    3. Add the torque to spin up rotating inertia (screw + reflected mass).
    4. RMS torque over the cycle - motors heat up on RMS, not peak.
    5. Screen a catalogue (a list of dicts) with if/else checks.

Run it:  uv run examples/motor_sizing.py
"""

import math

from fpc import Mechatronics

mech = Mechatronics()

MASS_KG = 40.0
LEAD_M = 0.010
STROKE_M = 0.300
MOVE_TIME_S = 0.6
DWELL_S = 0.4
FRICTION_COEFF = 0.05  # linear guide
SCREW_INERTIA = 1.2e-4  # kg*m^2 (from screw supplier)
SCREW_EFFICIENCY = 0.9
SAFETY_FACTOR = 1.5

# A tiny catalogue: in practice, export this from the vendor's sizing tool.
MOTORS = [
    {"model": "S-200W", "rated_nm": 0.64, "peak_nm": 1.9, "max_rpm": 5000, "rotor": 0.18e-4},
    {"model": "S-400W", "rated_nm": 1.27, "peak_nm": 3.8, "max_rpm": 5000, "rotor": 0.34e-4},
    {"model": "S-750W", "rated_nm": 2.39, "peak_nm": 7.2, "max_rpm": 4500, "rotor": 1.05e-4},
    {"model": "S-1kW", "rated_nm": 3.18, "peak_nm": 9.5, "max_rpm": 3000, "rotor": 2.6e-4},
]


def main():
    # --- 1. Motion profile ------------------------------------------------
    t_acc = MOVE_TIME_S / 3
    # Area under a 1/3-1/3-1/3 trapezoid: stroke = v_peak * (2/3) * move_time
    v_peak = STROKE_M / (MOVE_TIME_S * 2 / 3)
    accel = v_peak / t_acc
    rpm_peak = v_peak / LEAD_M * 60
    print(f"Peak speed {v_peak:.2f} m/s ({rpm_peak:.0f} rpm), accel {accel:.2f} m/s^2")

    # --- 2-3. Torque in each phase ---------------------------------------
    friction = FRICTION_COEFF * MASS_KG * 9.81
    alpha = accel / LEAD_M * 2 * math.pi  # screw angular accel [rad/s^2]

    def phase_torque(force, rotor_inertia):
        """Torque = ball-screw torque for the linear force + spin-up torque."""
        linear = mech.ballscrew_torque(thrust_force=force, lead=LEAD_M, efficiency=SCREW_EFFICIENCY)
        spin = mech.acceleration_torque(
            inertia=SCREW_INERTIA + rotor_inertia, angular_acceleration=alpha
        )
        return linear, spin

    reflected_mass = MASS_KG * (LEAD_M / (2 * math.pi)) ** 2
    print(f"Load inertia at motor: {SCREW_INERTIA + reflected_mass:.2e} kg*m^2\n")

    # --- 4-5. Screen each motor -----------------------------------------
    for motor in MOTORS:
        lin_acc, spin = phase_torque(friction + MASS_KG * accel, motor["rotor"])
        lin_dec, _ = phase_torque(friction - MASS_KG * accel, motor["rotor"])
        t_accel = lin_acc + spin
        t_cruise = mech.ballscrew_torque(
            thrust_force=friction, lead=LEAD_M, efficiency=SCREW_EFFICIENCY
        )
        t_decel = lin_dec - spin
        cycle = MOVE_TIME_S + DWELL_S
        rms = math.sqrt((t_accel**2 + t_cruise**2 + t_decel**2) * t_acc / cycle)
        ratio = (SCREW_INERTIA + reflected_mass) / motor["rotor"]

        # Each check is a boolean; all() requires every one to pass.
        checks = {
            "peak": abs(t_accel) * SAFETY_FACTOR <= motor["peak_nm"],
            "rms": rms * SAFETY_FACTOR <= motor["rated_nm"],
            "speed": rpm_peak <= motor["max_rpm"],
            "inertia<=10": ratio <= 10,
        }
        verdict = (
            "OK"
            if all(checks.values())
            else "fails " + ", ".join(name for name, ok in checks.items() if not ok)
        )
        print(
            f"{motor['model']:>7}: peak {t_accel:4.2f} N*m, RMS {rms:4.2f} N*m, "
            f"J ratio {ratio:5.1f}  -> {verdict}"
        )


if __name__ == "__main__":
    main()
