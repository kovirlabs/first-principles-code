# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Rung 1: a script. Inputs are edited in the file; results print.

Perfect for a one-off answer. The limitation: to try another case you edit
the code. See docs/building-tools.md for the whole ladder.

Run it:  uv run examples/tools/step1_script.py
"""

from fpc import Fluids, Properties

fluids, props = Fluids(), Properties()

TEMPERATURE_C = 20.0
result = fluids.pipe_flow(
    flow=0.012,  # m^3/s
    diameter=0.1023,  # m
    length=120.0,  # m
    roughness=0.045e-3,  # m, commercial steel
    density=props.water_liquid(temperature_c=TEMPERATURE_C, property="density_kg_m3"),
    viscosity=props.water_liquid(temperature_c=TEMPERATURE_C, property="dynamic_viscosity_pa_s"),
)
for name, value in result.items():
    print(f"{name:>16}: {value:.4g}")
