# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Rung 4: a web app with Streamlit - share a link instead of a file.

Streamlit reruns this whole script top to bottom every time a widget
changes, so the code reads like a plain script: widgets *return* values.
Install the optional dependency group first.

Run it:
    uv sync --group apps
    uv run streamlit run examples/tools/step4_web_app.py
"""

import numpy as np
import pandas as pd
import streamlit as st

from fpc import Fluids, Properties

fluids, props = Fluids(), Properties()

st.title("Pipe pressure drop")
st.caption("Darcy-Weisbach with the Colebrook friction factor - water at 1 atm.")

# Sidebar inputs: each widget returns its current value.
with st.sidebar:
    flow_l_s = st.number_input("Flow [L/s]", min_value=0.1, value=12.0)
    diameter_mm = st.number_input("Inner diameter [mm]", min_value=1.0, value=102.3)
    length_m = st.number_input("Length [m]", min_value=0.1, value=120.0)
    roughness_mm = st.number_input("Roughness [mm]", min_value=0.0, value=0.045, format="%.4f")
    temperature_c = st.slider("Water temperature [degC]", 1, 99, 20)

density = props.water_liquid(temperature_c=temperature_c, property="density_kg_m3")
viscosity = props.water_liquid(temperature_c=temperature_c, property="dynamic_viscosity_pa_s")


def run(flow_l_s):
    return fluids.pipe_flow(
        flow=flow_l_s / 1000,
        diameter=diameter_mm / 1000,
        length=length_m,
        roughness=roughness_mm / 1000,
        density=density,
        viscosity=viscosity,
    )


result = run(flow_l_s)
left, middle, right = st.columns(3)
left.metric("Velocity", f"{result['velocity']:.2f} m/s")
middle.metric("Reynolds", f"{result['reynolds']:,.0f}")
right.metric("Pressure drop", f"{result['pressure_drop'] / 1000:.2f} kPa")

# A curve is more useful than one number: dp across a range of flows.
flows = np.linspace(0.1 * flow_l_s, 2 * flow_l_s, 40)
curve = pd.DataFrame(
    {
        "flow [L/s]": flows,
        "pressure drop [kPa]": [run(q)["pressure_drop"] / 1000 for q in flows],
    }
).set_index("flow [L/s]")
st.line_chart(curve)
