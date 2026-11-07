# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""engineering_script.py - a copy-and-adapt starting point for your own calculation.

HOW TO USE THIS TEMPLATE
    1. Copy this file somewhere and rename it after your problem
       (e.g. ``conveyor_motor_check.py``).
    2. Edit the INPUTS dictionary - every number your calculation depends on,
       with its units in the key name.
    3. Replace the body of ``calculate()`` with your engineering.
    4. Run it:  uv run templates/engineering_script.py

The script follows the same five steps every engineering calculation does:

    INPUTS  ->  CALCULATE  ->  REPORT  ->  PLOT  ->  EXPORT

The worked example inside (a cantilever beam's tip deflection along its
length) is only a placeholder - it is there so the template runs out of the
box and you can see each step produce output.

Why this structure?
    * All inputs in one dictionary: anyone reviewing the calc can check every
      assumption in one place, and you can loop over a list of these
      dictionaries to run a parameter study.
    * The calculation is a function with keyword-only arguments: it can be
      imported and tested, and call sites say what each number means.
    * Results are written to files, because a number in a terminal is not a
      deliverable - a CSV and a figure are.
"""

# --- Imports ----------------------------------------------------------------
# Standard library first, then third-party, then this project. Delete the
# ones you do not use.
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from fpc import Utility

# --- 1. INPUTS --------------------------------------------------------------
# Put units in every key. A bare "length" invites someone to type inches.
INPUTS = {
    "length_m": 1.5,  # cantilever length
    "tip_load_n": 800.0,  # point load at the free end
    "modulus_pa": 200e9,  # Young's modulus (steel)
    "width_m": 0.04,  # rectangular section width
    "height_m": 0.06,  # rectangular section height
    "allowable_deflection_m": 0.008,
}

# Where results go: a folder next to this script, whatever directory you run
# it from. ``Path(__file__)`` is the path of this file.
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


# --- 2. CALCULATE -----------------------------------------------------------
def calculate(
    *, length_m, tip_load_n, modulus_pa, width_m, height_m, allowable_deflection_m, points=50
):
    """Deflection along a cantilever with a tip load.

    Replace this with your own calculation. Keep it *pure*: inputs in, results
    out, no printing or file writing - that keeps it easy to test and reuse.

    Deflection at distance x from the wall:
        y(x) = P * x^2 * (3L - x) / (6 * E * I)

    :param length_m: beam length L [m]
    :param tip_load_n: tip load P [N]
    :param modulus_pa: Young's modulus E [Pa]
    :param width_m: section width b [m]
    :param height_m: section height h [m]
    :param allowable_deflection_m: limit on tip deflection [m]
    :param points: number of points along the beam to evaluate
    :returns: dict of results (scalars and arrays)
    """
    moment_of_inertia = width_m * height_m**3 / 12  # [m^4]
    # NumPy evaluates the formula at every x at once (no loop needed).
    x = np.linspace(0.0, length_m, points)  # [m]
    deflection = tip_load_n * x**2 * (3 * length_m - x) / (6 * modulus_pa * moment_of_inertia)

    tip_deflection = deflection[-1]  # last point = the tip
    return {
        "x_m": x,
        "deflection_m": deflection,
        "moment_of_inertia_m4": moment_of_inertia,
        "tip_deflection_m": tip_deflection,
        "utilization": tip_deflection / allowable_deflection_m,
        "passes": tip_deflection <= allowable_deflection_m,
    }


# --- 3. REPORT --------------------------------------------------------------
def report(*, inputs, results):
    """Print a short, readable summary - inputs echoed, then key results."""
    print("Inputs")
    print("-" * 40)
    for name, value in inputs.items():
        # :<26 left-aligns the name in 26 characters; :g picks a tidy format.
        print(f"  {name:<26} {value:g}")

    print("\nResults")
    print("-" * 40)
    print(f"  {'moment_of_inertia_m4':<26} {results['moment_of_inertia_m4']:.4e}")
    print(f"  {'tip_deflection_mm':<26} {results['tip_deflection_m'] * 1000:.3f}")
    print(f"  {'utilization':<26} {results['utilization']:.0%}")
    verdict = "PASS" if results["passes"] else "FAIL"
    print(f"\n  Deflection check: {verdict}")


# --- 4. PLOT ----------------------------------------------------------------
def plot(*, inputs, results, save_path):
    """Save a figure of the result - usually the real deliverable."""
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(results["x_m"], results["deflection_m"] * 1000, label="deflection")
    axis.axhline(
        inputs["allowable_deflection_m"] * 1000, color="red", linestyle="--", label="allowable"
    )
    axis.set_xlabel("Distance from wall [m]")
    axis.set_ylabel("Deflection [mm]")
    axis.set_title("Cantilever deflection")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(save_path, dpi=120)
    plt.close(figure)  # free memory; matters when a loop makes many figures


# --- 5. EXPORT --------------------------------------------------------------
def export(*, inputs, results):
    """Write the inputs (JSON) and the array results (CSV) to OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    utility = Utility()
    utility.dict_to_json(data=inputs, file_path=OUTPUT_DIR / "inputs.json")
    # zip pairs the arrays up row by row: (x0, y0), (x1, y1), ...
    # strict=True raises if the arrays differ in length instead of silently
    # dropping the extra values.
    rows = zip(results["x_m"], results["deflection_m"], strict=True)
    utility.export_csv(
        rows=rows, file_path=OUTPUT_DIR / "results.csv", header=["x_m", "deflection_m"]
    )
    plot(inputs=inputs, results=results, save_path=OUTPUT_DIR / "results.png")
    print(f"\n  Wrote inputs.json, results.csv, results.png to {OUTPUT_DIR}")


# --- Run --------------------------------------------------------------------
# This guard means "only run when executed as a script". Importing this file
# (e.g. from a test or another script) gives you calculate() without
# running the whole thing.
if __name__ == "__main__":
    results = calculate(**INPUTS)  # ** unpacks the dict into keyword arguments
    report(inputs=INPUTS, results=results)
    export(inputs=INPUTS, results=results)
