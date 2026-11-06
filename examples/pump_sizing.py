# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""pump_sizing.py - choose a pipe size and the pump to drive it.

QUESTION
    We need to move 12 L/s of 20 degC water up 15 m through 120 m of
    commercial steel pipe. Which standard pipe size keeps velocity under
    2.5 m/s, and how much head and power must the pump deliver?

APPROACH
    1. Look up water density and viscosity at 20 degC (Properties, interpolated).
    2. For each candidate pipe: velocity -> Reynolds -> Colebrook friction
       factor (a root-finding solve) -> Darcy-Weisbach head loss.
    3. Pick the smallest pipe meeting the velocity limit.
    4. Pump head = static lift + friction + minor losses; shaft power from
       the hydraulic power and an assumed pump efficiency.
    5. Plot the system curve (head vs flow) - the curve a pump vendor will
       ask you for.

Run it:  uv run examples/pump_sizing.py
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from fpc import Fluids, Properties

fluids = Fluids()
props = Properties()

# --- Inputs -------------------------------------------------------------
FLOW_M3_S = 0.012  # 12 L/s design flow
STATIC_LIFT_M = 15.0  # elevation gain
PIPE_LENGTH_M = 120.0
ROUGHNESS_M = 0.045e-3  # commercial steel, eps = 0.045 mm
MINOR_LOSS_K = 6.0  # sum of fittings/valve K factors (estimate)
MAX_VELOCITY_M_S = 2.5
PUMP_EFFICIENCY = 0.70
WATER_TEMPERATURE_C = 20.0

# Nominal size -> inner diameter [m] (Schedule 40 steel pipe).
PIPE_SIZES = {
    '2"': 0.0525,
    '2-1/2"': 0.0627,
    '3"': 0.0779,
    '4"': 0.1023,
    '5"': 0.1282,
}


def friction_head(*, flow, diameter, density, viscosity):
    """Total pipe head loss (major + minor) for a given flow and pipe [m]."""
    area = math.pi * diameter**2 / 4
    velocity = flow / area
    reynolds = fluids.reynolds_number(
        density=density,
        velocity=velocity,
        length=diameter,
        viscosity=viscosity,
    )
    f = fluids.colebrook_friction_factor(
        reynolds=reynolds,
        relative_roughness=ROUGHNESS_M / diameter,
    )
    major = fluids.pipe_head_loss(
        friction_factor=f,
        length=PIPE_LENGTH_M,
        diameter=diameter,
        velocity=velocity,
    )
    # Minor losses scale with velocity head: h = K * v^2 / 2g.
    minor = MINOR_LOSS_K * velocity**2 / (2 * fluids.GRAVITY)
    return {"velocity": velocity, "reynolds": reynolds, "f": f, "head": major + minor}


def main():
    density = props.water_liquid(temperature_c=WATER_TEMPERATURE_C, property="density_kg_m3")
    viscosity = props.water_liquid(
        temperature_c=WATER_TEMPERATURE_C,
        property="dynamic_viscosity_pa_s",
    )
    print(
        f"Water at {WATER_TEMPERATURE_C} degC: rho = {density:.1f} kg/m^3, "
        f"mu = {viscosity:.3e} Pa*s\n"
    )

    # --- Evaluate every candidate and pick the first that passes -------
    print(f"{'Pipe':>7} {'v [m/s]':>8} {'Re':>9} {'f':>7} {'h_loss [m]':>11}  ok?")
    chosen = None
    for name, diameter in PIPE_SIZES.items():  # dicts keep insertion order
        r = friction_head(flow=FLOW_M3_S, diameter=diameter, density=density, viscosity=viscosity)
        ok = r["velocity"] <= MAX_VELOCITY_M_S
        print(
            f"{name:>7} {r['velocity']:8.2f} {r['reynolds']:9.0f} "
            f"{r['f']:7.4f} {r['head']:11.2f}  {'yes' if ok else 'no'}"
        )
        if ok and chosen is None:
            chosen = (name, diameter, r)

    if chosen is None:
        raise SystemExit("No candidate pipe meets the velocity limit - add bigger sizes.")
    name, diameter, r = chosen

    # --- Pump duty --------------------------------------------------------
    total_head = STATIC_LIFT_M + r["head"]
    hydraulic_power = density * fluids.GRAVITY * FLOW_M3_S * total_head  # P = rho*g*Q*H
    shaft_power = hydraulic_power / PUMP_EFFICIENCY
    print(f"\nChosen pipe: {name} (ID {diameter * 1000:.1f} mm)")
    print(f"Pump duty point: {FLOW_M3_S * 1000:.0f} L/s at {total_head:.1f} m head")
    print(f"Shaft power: {shaft_power / 1000:.2f} kW at {PUMP_EFFICIENCY:.0%} efficiency")

    # --- System curve: head required across a range of flows -------------
    flows = np.linspace(0.001, 1.5 * FLOW_M3_S, 40)
    # colebrook_friction_factor works on one number at a time, so we use a
    # list comprehension to evaluate it across the flows.
    heads = [
        STATIC_LIFT_M
        + friction_head(flow=q, diameter=diameter, density=density, viscosity=viscosity)["head"]
        for q in flows
    ]

    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(flows * 1000, heads, label=f"system curve ({name} pipe)")
    axis.plot(FLOW_M3_S * 1000, total_head, "ro", label="design duty point")
    axis.set_xlabel("Flow [L/s]")
    axis.set_ylabel("Head [m]")
    axis.grid(True, alpha=0.3)
    axis.legend()
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)
    figure.savefig(output_dir / "pump_system_curve.png", dpi=120)
    print(f"\nSaved system curve -> {output_dir / 'pump_system_curve.png'}")


if __name__ == "__main__":
    main()
