# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Rung 3: a desktop form with tkinter (ships with Python).

Labelled entry boxes and a Calculate button - usable by people who will
never open a terminal. For an open-ended calculator, see the project's
gui.py console instead; this is the "single-purpose app" version.

Run it:  uv run examples/tools/step3_gui.py
"""

import tkinter as tk
from tkinter import ttk

from fpc import Fluids, Properties

# (label, default) for each input - adding a field is one line here.
FIELDS = {
    "flow_l_s": ("Flow [L/s]", 12.0),
    "diameter_mm": ("Inner diameter [mm]", 102.3),
    "length_m": ("Length [m]", 120.0),
    "roughness_mm": ("Roughness [mm]", 0.045),
    "temperature_c": ("Water temperature [degC]", 20.0),
}


def calculate(values):
    """Same calculation as rungs 1 and 2: the GUI is only a new front end."""
    props = Properties()
    t = values["temperature_c"]
    return Fluids().pipe_flow(
        flow=values["flow_l_s"] / 1000,
        diameter=values["diameter_mm"] / 1000,
        length=values["length_m"],
        roughness=values["roughness_mm"] / 1000,
        density=props.water_liquid(temperature_c=t, property="density_kg_m3"),
        viscosity=props.water_liquid(temperature_c=t, property="dynamic_viscosity_pa_s"),
    )


def main():
    root = tk.Tk()
    root.title("Pipe pressure drop")
    frame = ttk.Frame(root, padding=12)
    frame.grid()

    entries = {}
    for row, (key, (label, default)) in enumerate(FIELDS.items()):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(frame, width=12)
        entry.insert(0, str(default))
        entry.grid(row=row, column=1, pady=2)
        entries[key] = entry

    output = tk.StringVar(value="Press Calculate")
    ttk.Label(frame, textvariable=output, justify="left").grid(
        row=len(FIELDS) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0)
    )

    def on_calculate():
        # Never trust typed input: a GUI must handle "abc" gracefully.
        try:
            values = {key: float(entry.get()) for key, entry in entries.items()}
            r = calculate(values)
        except ValueError as error:
            output.set(f"Input error: {error}")
            return
        output.set(
            f"Velocity: {r['velocity']:.2f} m/s\n"
            f"Reynolds: {r['reynolds']:.0f}\n"
            f"Friction factor: {r['friction_factor']:.4f}\n"
            f"Pressure drop: {r['pressure_drop'] / 1000:.2f} kPa"
        )

    ttk.Button(frame, text="Calculate", command=on_calculate).grid(
        row=len(FIELDS), column=0, columnspan=2, pady=(8, 0)
    )
    root.mainloop()


if __name__ == "__main__":
    main()
