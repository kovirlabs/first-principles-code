# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Regenerate the notebooks in this folder from code (run from the repo root).

Notebook JSON is awkward to review in a pull request, so the cells live here
as plain Python strings. Edit this file, then run:

    uv run --group notebooks python notebooks/make_notebooks.py
"""

import nbformat as nbf
from nbformat.v4 import new_code_cell as code
from nbformat.v4 import new_markdown_cell as md
from nbformat.v4 import new_notebook

HDR = "<!-- SPDX-License-Identifier: Apache-2.0 -->\n<!-- Copyright 2026 Evan Gress -->\n\n"


def save(name, cells):
    nb = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
        },
    )
    nbf.write(nb, f"notebooks/{name}")


save(
    "01_getting_started.ipynb",
    [
        md(
            HDR
            + "# 01 · Getting started with `fpc`\n\nA notebook mixes code, results, plots, and explanation in one document — ideal for exploring a problem and showing your working.\n\n**Run a cell:** Shift+Enter. Cells share variables, so run them top to bottom.\n\nStart Jupyter from the repo root:\n```bash\nuv sync --group notebooks\nuv run jupyter lab\n```"
        ),
        md(
            "## 1. Import a class and call a method\nEvery method takes **keyword arguments**, so the call says what each number means."
        ),
        code(
            "from fpc import Dynamics, Thermo\n\ndyn = Dynamics()\ndyn.displacement_constant_acceleration(\n    initial_position=0.0, initial_velocity=5.0, acceleration=9.81, time=3.0,\n)"
        ),
        md(
            "The last expression in a cell is displayed automatically. `help()` (or Shift+Tab in Jupyter) shows the docstring, including the units:"
        ),
        code("help(Thermo.carnot_efficiency)"),
        md("## 2. Many cases: lists of dicts and `**` unpacking"),
        code(
            'launches = [{"speed": 20, "angle_deg": a} for a in (15, 30, 45, 60, 75)]\nfor case in launches:\n    print(f"{case[\'angle_deg\']:>3} deg -> {dyn.projectile_range(**case):6.2f} m")'
        ),
        md(
            "## 3. Plot a sweep\nA plot shows the whole trend — here, why 45° is the best launch angle without drag."
        ),
        code(
            'import numpy as np\nimport matplotlib.pyplot as plt\n\nangles = np.linspace(1, 89, 89)\nranges = [dyn.projectile_range(speed=20, angle_deg=a) for a in angles]\n\nfig, ax = plt.subplots(figsize=(6, 3.5))\nax.plot(angles, ranges)\nax.set_xlabel("Launch angle [deg]")\nax.set_ylabel("Range [m]")\nax.grid(alpha=0.3)\nangles[int(np.argmax(ranges))]'
        ),
        md(
            "## 4. Drag changes the answer\n`simulate_projectile_drag` integrates the equations of motion with SciPy. Compare its range with the no-drag formula."
        ),
        code(
            '# A tennis ball: 57 g, 6.7 cm diameter, Cd ~ 0.5\nimport math\nt, x, y = dyn.simulate_projectile_drag(\n    speed=20, angle_deg=45, mass=0.057, drag_coefficient=0.5,\n    frontal_area=math.pi * 0.067**2 / 4,\n)\nno_drag = dyn.projectile_range(speed=20, angle_deg=45)\nprint(f"without drag: {no_drag:.1f} m   with drag: {x[-1]:.1f} m")\n\nfig, ax = plt.subplots(figsize=(6, 3))\nax.plot(x, y, label="with drag")\nxs = np.linspace(0, no_drag, 100)\nax.plot(xs, xs - 9.81 * xs**2 / 20**2, "--", label="no drag")  # y = x*tan(45) - g*x^2/(2 v^2 cos^2 45)\nax.set_xlabel("x [m]")\nax.set_ylabel("y [m]")\nax.legend()\nax.grid(alpha=0.3)'
        ),
        md(
            "## Next\n- `02_pipe_flow_and_data.ipynb` — pandas tables, interpolation, root finding\n- `03_beam_design.ipynb` — units with Pint, sizing and optimization\n- `examples/` — complete worked problems as scripts"
        ),
    ],
)

save(
    "02_pipe_flow_and_data.ipynb",
    [
        md(
            HDR
            + "# 02 · Pipe flow, property tables, and root finding\n\nThree tools you will use constantly:\n1. **pandas** to load and inspect reference tables\n2. **interpolation** to read between table rows\n3. **root finding** to solve equations that have no algebraic solution"
        ),
        md("## 1. Load a table with pandas"),
        code("from fpc import Properties, Fluids\n\nprops = Properties()\nprops.list_tables()"),
        code('water = props.load_table(name="water_liquid_1atm")\nwater.head()'),
        code('water.describe().T[["min", "max"]]'),
        md("Boolean masks select rows — *which temperatures have viscosity below 0.5 mPa·s?*"),
        code(
            'water[water["dynamic_viscosity_pa_s"] < 0.5e-3][["temperature_c", "dynamic_viscosity_pa_s"]]'
        ),
        md(
            '## 2. Interpolate between rows\nThe table jumps in 5–10 °C steps. `water_liquid` interpolates; `method="cubic"` uses a smooth spline instead of straight lines. Outside the table it raises an error rather than guessing.'
        ),
        code('props.water_liquid(temperature_c=37, property="dynamic_viscosity_pa_s")'),
        code(
            'import numpy as np\nimport matplotlib.pyplot as plt\n\nsat = props.load_table(name="water_saturation")\nt = np.linspace(0.01, 200, 400)\nfig, ax = plt.subplots(figsize=(6, 3.5))\nax.plot(sat["temperature_c"], sat["pressure_kpa"], "o", label="table")\nax.plot(t, props.water_saturation(temperature_c=t, property="pressure_kpa"), label="linear")\nax.plot(t, props.water_saturation(temperature_c=t, property="pressure_kpa", method="cubic"), "--", label="cubic")\nax.set_xlabel("Temperature [degC]")\nax.set_ylabel("Saturation pressure [kPa]")\nax.legend()\nax.grid(alpha=0.3)'
        ),
        md(
            "## 3. Root finding: the Colebrook equation\n$$\\frac{1}{\\sqrt f} = -2\\log_{10}\\left(\\frac{\\varepsilon/D}{3.7} + \\frac{2.51}{Re\\sqrt f}\\right)$$\n`f` is on both sides, so we can't rearrange it. `Fluids.colebrook_friction_factor` hands the equation to `scipy.optimize.brentq`. Repeating that solve over a grid draws a Moody chart:"
        ),
        code(
            'fluids = Fluids()\nreynolds = np.logspace(3, 8, 200)\nfig, ax = plt.subplots(figsize=(6, 4))\nfor roughness in (0, 1e-5, 1e-4, 1e-3, 1e-2):\n    f = [fluids.colebrook_friction_factor(reynolds=re, relative_roughness=roughness) for re in reynolds]\n    ax.loglog(reynolds, f, label=f"eps/D = {roughness:g}")\nax.set_xlabel("Reynolds number")\nax.set_ylabel("Darcy friction factor")\nax.legend(fontsize=8)\nax.grid(which="both", alpha=0.3)'
        ),
        md("## 4. Put it together\n`Fluids.pipe_flow` chains all of this for one pipe:"),
        code(
            'rho = props.water_liquid(temperature_c=20, property="density_kg_m3")\nmu = props.water_liquid(temperature_c=20, property="dynamic_viscosity_pa_s")\nfluids.pipe_flow(flow=0.012, diameter=0.1023, length=120, roughness=0.045e-3, density=rho, viscosity=mu)'
        ),
        md(
            "**Try it:** how much does the pressure drop fall if the water is at 80 °C instead of 20 °C? Why?"
        ),
    ],
)

save(
    "03_beam_design.ipynb",
    [
        md(
            HDR
            + "# 03 · Beam design: units, sizing, and optimization\n\nAnalysis asks *how much does this beam deflect?* Design asks *what beam deflects no more than 5 mm?* This notebook does both."
        ),
        md(
            "## 1. Units with Pint\n`Q_(value, unit)` makes a quantity. Arithmetic carries the units and `.to()` converts."
        ),
        code(
            'from fpc import Beam, Q_\n\nbeam = Beam(length=Q_(2.0, "m"), width=Q_(50, "mm"), height=Q_(100, "mm"))\nbeam.max_deflection_point_load(load=Q_(5, "kN")).to("mm")'
        ),
        md("Mixing up units fails loudly instead of giving a wrong number:"),
        code(
            'try:\n    Beam(length=Q_(2.0, "s"), width=Q_(50, "mm"), height=Q_(100, "mm"))\nexcept ValueError as error:\n    print("Caught:", error)'
        ),
        md(
            "## 2. Sizing by root finding\n`Design.rectangular_beam_height_for_deflection` solves *deflection(h) − limit = 0* with `brentq`. Plain SI floats here."
        ),
        code(
            'from fpc import Design\n\ndesign = Design()\nh = design.rectangular_beam_height_for_deflection(\n    load=5000, length=2.0, modulus=200e9, width=0.05, max_deflection=0.001,\n)\nf"required height = {h * 1000:.1f} mm"'
        ),
        md(
            "## 3. Optimization with constraints\nMinimize mass subject to stress, deflection, and a height ≤ 4 × width rule. The constraints that end up at their limits are the ones that *drive* the design."
        ),
        code(
            "design.lightest_rectangular_beam(\n    load=5000, length=2.0, modulus=200e9, density=7850,\n    allowable_stress=150e6, max_deflection=0.005,\n)"
        ),
        md(
            "Sweep the load to see when the governing requirement switches from deflection to stress:"
        ),
        code(
            'import pandas as pd\n\nrows = []\nfor load in (2e3, 5e3, 10e3, 20e3, 40e3):\n    r = design.lightest_rectangular_beam(load=load, length=2.0, modulus=200e9, density=7850,\n                                         allowable_stress=150e6, max_deflection=0.01)\n    rows.append({"load_kN": load / 1e3, "mass_kg": round(r["mass"], 1),\n                 "governs": ", ".join(r["active"])})\npd.DataFrame(rows)'
        ),
        md(
            "## 4. Catalogue selection\nReal beams come from a catalogue. `Properties.lightest_w_shape` filters and sorts the AISC table with pandas; Pint converts the required section modulus to the catalogue's units."
        ),
        code(
            'from fpc import Properties\n\nmoment = Q_(40, "kN") * Q_(6, "m") / 4\nrequired_sx = (moment / (0.66 * Q_(345, "MPa"))).to("in**3")\nprint(f"required Sx = {required_sx:.1f~P}")\nProperties().lightest_w_shape(required_sx_in3=required_sx.magnitude)'
        ),
        md("See `examples/beam_selection.py` for the full version with a deflection check."),
    ],
)
