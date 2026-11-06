# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""shielding_check.py - narrow-beam lead vs concrete shielding estimate.

QUESTION
    A 100 keV photon beam must be cut to 0.1% (transmission 1e-3). How thick
    must a lead or a concrete barrier be, and how much does moving the
    workstation from 2 m to 4 m help?

APPROACH
    1. Linear attenuation mu = (mu/rho) * rho from NIST mass attenuation data.
    2. Thickness from I/I0 = exp(-mu*x)  ->  x = -ln(T)/mu.
    3. Half- and tenth-value layers for a quick mental check.
    4. Inverse-square law for the distance option.

Data: mass attenuation coefficients at 100 keV from NIST X-Ray Mass
Attenuation Coefficients (Hubbell & Seltzer), https://physics.nist.gov/xaamdi

TEACHING USE ONLY. Real barriers need broad-beam data with build-up, workload
and occupancy factors (NCRP Report 147) and a qualified medical physicist.

Run it:  uv run examples/shielding_check.py
"""

import math

from fpc import Radiation

radiation = Radiation()

TARGET_TRANSMISSION = 1e-3
MATERIALS = {
    # name: (mass attenuation coefficient [cm^2/g] at 100 keV, density [g/cm^3])
    "lead": (5.549, 11.35),
    "ordinary concrete": (0.1710, 2.30),
}


def main():
    print(f"Target transmission: {TARGET_TRANSMISSION:g} at 100 keV\n")
    for name, (mass_mu, density) in MATERIALS.items():
        mu = radiation.linear_attenuation_coefficient(
            mass_attenuation_coefficient=mass_mu,
            density=density,
        )
        thickness = radiation.shielding_thickness(
            attenuation_coefficient=mu,
            transmission=TARGET_TRANSMISSION,
        )
        hvl = radiation.half_value_layer(attenuation_coefficient=mu)
        tvl = radiation.tenth_value_layer(attenuation_coefficient=mu)
        print(
            f"{name:>18}: mu = {mu:6.2f} /cm, HVL = {hvl * 10:6.2f} mm, "
            f"TVL = {tvl * 10:6.2f} mm -> {thickness * 10:7.1f} mm needed"
        )

    # Distance is free shielding: doubling it cuts intensity to a quarter.
    relative = radiation.inverse_square_law(
        initial_intensity=1.0,
        initial_distance=2.0,
        new_distance=4.0,
    )
    # Each HVL halves the intensity, so a factor of 1/relative is log2 of it HVLs.
    equivalent_hvls = math.log2(1 / relative)
    print(
        f"\nMoving from 2 m to 4 m leaves {relative:.0%} of the intensity "
        f"- the same as adding {equivalent_hvls:.0f} HVLs of shielding."
    )


if __name__ == "__main__":
    main()
