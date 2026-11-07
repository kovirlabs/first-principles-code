# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Regenerate the water property CSVs in this folder from CoolProp (IAPWS-95).

Run from this folder:  uv run --with CoolProp python generate_water_tables.py

CoolProp is not a project dependency; it is only needed to rebuild the tables.
Keeping the generator next to the data documents exactly where every number
came from.
"""

import CoolProp
from CoolProp.CoolProp import PropsSI

print("CoolProp", CoolProp.__version__)

# Saturated water: both phases coexist, so temperature alone fixes the state.
temps = [0.01, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200]
with open("water_saturation.csv", "w") as f:
    f.write(
        "temperature_c,pressure_kpa,density_liquid_kg_m3,density_vapor_kg_m3,"
        "enthalpy_liquid_kj_kg,enthalpy_vaporization_kj_kg,enthalpy_vapor_kj_kg\n"
    )
    for t in temps:
        T = t + 273.15
        # "Q" is vapor quality: 0 = saturated liquid, 1 = saturated vapor.
        p = PropsSI("P", "T", T, "Q", 0, "Water") / 1e3
        rl = PropsSI("D", "T", T, "Q", 0, "Water")
        rv = PropsSI("D", "T", T, "Q", 1, "Water")
        hl = PropsSI("H", "T", T, "Q", 0, "Water") / 1e3
        hv = PropsSI("H", "T", T, "Q", 1, "Water") / 1e3
        f.write(f"{t},{p:.4g},{rl:.2f},{rv:.5g},{hl:.2f},{hv - hl:.1f},{hv:.1f}\n")

# Compressed liquid at 1 atm: what you need for everyday pipe-flow problems.
with open("water_liquid_1atm.csv", "w") as f:
    f.write(
        "temperature_c,density_kg_m3,dynamic_viscosity_pa_s,"
        "specific_heat_j_kg_k,thermal_conductivity_w_m_k\n"
    )
    for t in [1, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 99]:
        T, P = t + 273.15, 101325
        f.write(
            f"{t},{PropsSI('D', 'T', T, 'P', P, 'Water'):.2f},"
            f"{PropsSI('V', 'T', T, 'P', P, 'Water'):.4e},"
            f"{PropsSI('C', 'T', T, 'P', P, 'Water'):.1f},"
            f"{PropsSI('L', 'T', T, 'P', P, 'Water'):.4f}\n"
        )
