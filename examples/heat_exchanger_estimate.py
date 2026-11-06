# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""heat_exchanger_estimate.py - first-pass size of a water-to-water exchanger.

QUESTION
    Hot water (2 kg/s) must be cooled from 80 to 50 degC using cooling water
    (3 kg/s) entering at 20 degC. What is the duty, the cooling-water outlet
    temperature, and roughly how much area does a counterflow exchanger need?

APPROACH
    1. Specific heats from the property table at each stream's mean temperature.
    2. Energy balance: Q = m*cp*dT on the hot side; the cold side absorbs it.
    3. LMTD for counterflow; area A = Q / (U * LMTD) with an assumed U.
    4. Compare with parallel flow to show why counterflow is preferred.

Run it:  uv run examples/heat_exchanger_estimate.py
"""

from fpc import Properties, Thermo

props, thermo = Properties(), Thermo()

HOT = {"mass_flow_kg_s": 2.0, "t_in_c": 80.0, "t_out_c": 50.0}
COLD = {"mass_flow_kg_s": 3.0, "t_in_c": 20.0}
OVERALL_U = 1500.0   # W/(m^2*K), typical for clean water-water plate/shell (assumed)


def main():
    cp_hot = props.water_liquid(temperature_c=(HOT["t_in_c"] + HOT["t_out_c"]) / 2,
                                property="specific_heat_j_kg_k")
    duty = HOT["mass_flow_kg_s"] * cp_hot * (HOT["t_in_c"] - HOT["t_out_c"])   # [W]

    # Cold outlet from the energy balance. cp depends on the (unknown) outlet,
    # so iterate: guess, update cp, recompute - converges in a few passes.
    t_cold_out = COLD["t_in_c"] + 10.0
    for _ in range(5):
        cp_cold = props.water_liquid(temperature_c=(COLD["t_in_c"] + t_cold_out) / 2,
                                     property="specific_heat_j_kg_k")
        t_cold_out = COLD["t_in_c"] + duty / (COLD["mass_flow_kg_s"] * cp_cold)

    print(f"Duty:              Q = {duty / 1000:.1f} kW")
    print(f"Cold-water outlet:     {t_cold_out:.1f} degC\n")

    arrangements = {
        "counterflow": (HOT["t_in_c"] - t_cold_out, HOT["t_out_c"] - COLD["t_in_c"]),
        "parallel flow": (HOT["t_in_c"] - COLD["t_in_c"], HOT["t_out_c"] - t_cold_out),
    }
    for name, (dt1, dt2) in arrangements.items():
        lmtd = thermo.log_mean_temperature_difference(delta_t_1=dt1, delta_t_2=dt2)
        area = duty / (OVERALL_U * lmtd)
        print(f"{name:>14}: LMTD = {lmtd:5.1f} K  ->  area = {area:5.2f} m^2")
    print("\nCounterflow needs less area for the same duty - a larger average "
          "driving temperature difference.")


if __name__ == "__main__":
    main()
