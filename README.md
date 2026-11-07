<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# First Principles Code

A template Python project that **teaches engineers to solve real engineering
problems in Python** — and shows that the open-source scientific stack
(`numpy`, `scipy`, and friends) can replace expensive proprietary tools.

📖 **Documentation:** <https://kovirlabs.github.io/first-principles-code/>,
with guides and an API reference generated from the docstrings.

You get:

- **`main.py`** — a worked example that calculates displacement from
  acceleration and velocity three different ways (closed-form, numerical
  integration of constant acceleration, and numerical integration of a
  time-varying acceleration).
- **`fpc/`** — an installable package with one well-documented class per
  engineering domain (dynamics, statics, thermo, fluids, psychrometrics,
  materials, gears, machine elements, fatigue, electrical, mechatronics,
  modal/vibration, controls), a set of radiology /
  medical-imaging classes, `Design` (root finding and optimization),
  `Properties` (cited reference tables with interpolation), and a `Utility`
  class for files, tables, and dialogs.
- **[`examples/`](https://github.com/kovirlabs/first-principles-code/tree/main/examples/)** — one script per realistic problem (pump
  sizing, beam selection, PID tuning, ...), each going from question to answer.
- **[`templates/engineering_script.py`](https://github.com/kovirlabs/first-principles-code/blob/main/templates/engineering_script.py)** —
  a commented skeleton to copy for your own calculation.
- **[`notebooks/`](https://github.com/kovirlabs/first-principles-code/tree/main/notebooks/)** — Jupyter notebooks that walk through the library.
- **Guides:** [from calculation to tool](https://github.com/kovirlabs/first-principles-code/blob/main/docs/building-tools.md) (script ->
  CLI -> GUI -> web app -> installed command) and
  [units: floats or Pint?](https://github.com/kovirlabs/first-principles-code/blob/main/docs/units.md).
- **[`PACKAGES.md`](https://github.com/kovirlabs/first-principles-code/blob/main/PACKAGES.md)** — which Python packages to use, by engineering field.

Every method uses keyword-only arguments and carries a docstring, so the code
itself doubles as a reference you can read and learn from.

---

## Quick start

```bash
# 1. Install dependencies into a project virtual environment
uv sync

# 2. Run the displacement demo (prints results and saves displacement.png)
uv run main.py

# 3. Run the test suite
uv run pytest
```

Expected output:

```
Displacement of an object after 3.0 s
================================================
  x0 = 0.0 m,  v0 = 5.0 m/s,  a = g = 9.81 m/s^2

  1. Analytical formula        :    59.1450 m
  2. scipy (constant a)        :    59.1450 m
  4. Dynamics library class    :    59.1450 m
     -> numerical vs exact err : 2.13e-14 m

  3. scipy (a = g + 2*sin(t))  :    64.8628 m
     (no simple closed form - this is why we integrate numerically)
```

---

## A short tutorial on `uv`

[`uv`](https://docs.astral.sh/uv/) is a fast, all-in-one Python package and
project manager (a modern replacement for `pip` + `venv` + `pip-tools`). It
reads `pyproject.toml`, manages a `.venv` for you, and pins exact versions in a
`uv.lock` file so your environment is reproducible.

### Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### The commands you'll actually use

| Command | What it does |
| --- | --- |
| `uv sync` | Create/update `.venv` to match `pyproject.toml` + `uv.lock` |
| `uv run main.py` | Run a script inside the project environment (auto-syncs first) |
| `uv run python` | Open a Python REPL with the project's packages available |
| `uv add scipy` | Add a dependency (updates `pyproject.toml` and the lockfile) |
| `uv add --dev pytest` | Add a *development-only* dependency (e.g. a test runner) |
| `uv remove scipy` | Remove a dependency |
| `uv lock` | Re-resolve and rewrite `uv.lock` without installing |
| `uv python install 3.11` | Install a specific Python version (fpc supports 3.11–3.15) |

The golden rule: **prefix anything that needs your packages with `uv run`**.
You never have to manually `activate` a virtual environment.

### Typical workflow

```bash
git clone <this-repo>
cd first-principles-code
uv sync                 # one-time setup
uv run main.py          # run the demo
uv add matplotlib       # pull in a new library when you need it
uv run python           # experiment interactively
```

---

## Using the library

Import a class, create an instance, and call its methods with **named
arguments** (this is the project's house style — calls read like sentences):

```python
from fpc.dynamics import Dynamics
from fpc.thermo import Thermo

dyn = Dynamics()
distance = dyn.displacement_constant_acceleration(
    initial_position=0.0,
    initial_velocity=5.0,
    acceleration=9.81,
    time=3.0,
)  # -> 59.145 m

thermo = Thermo()
efficiency = thermo.carnot_efficiency(hot_temperature=800, cold_temperature=300)
# -> 0.625  (the best a heat engine between these temperatures could ever do)
```

You can also import everything at once:

```python
from fpc import Dynamics, Statics, Fluids, Controls
```

### Creating and calling objects from lists and dictionaries

A common pattern: build several objects, store them in a container, then loop
over them. This is how you scale from one calculation to a whole study.

```python
from fpc.dynamics import Dynamics

dyn = Dynamics()

# --- A list of scenarios (each scenario is a dict of keyword arguments) ---
launches = [
    {"speed": 20, "angle_deg": 30},
    {"speed": 20, "angle_deg": 45},
    {"speed": 20, "angle_deg": 60},
]

# The ** operator unpacks a dict straight into keyword arguments.
for case in launches:
    distance = dyn.projectile_range(**case)
    print(f"{case['angle_deg']:>3}deg -> {distance:6.2f} m")

# --- A dictionary that maps a name to a configured object/result ---
materials = {
    "steel": 200e9,  # Young's modulus [Pa]
    "aluminum": 69e9,
    "titanium": 114e9,
}
for name, modulus in materials.items():
    print(f"{name:>9}: E = {modulus / 1e9:.0f} GPa")
```

### Conditional flow control and loops

```python
from fpc.fluids import Fluids

fluids = Fluids()
re = fluids.reynolds_number(density=1000, velocity=2, length=0.05, viscosity=1e-3)

# if / elif / else: classify the flow regime
if re < 2300:
    regime = "laminar"
elif re < 4000:
    regime = "transitional"
else:
    regime = "turbulent"
print(f"Re = {re:.0f} -> {regime}")

# while loop: increase velocity until the flow turns turbulent
velocity = 0.01
while fluids.reynolds_number(density=1000, velocity=velocity, length=0.05, viscosity=1e-3) < 4000:
    velocity += 0.01
print(f"Flow becomes turbulent at about {velocity:.2f} m/s")
```

### Lambda functions

A `lambda` is a small, unnamed function written inline — handy for quick math
and for telling other functions *how* to behave (sorting, mapping, filtering).

```python
# 1. A throwaway formula you can call like any function
kinetic_energy = lambda mass, velocity: 0.5 * mass * velocity**2
print(kinetic_energy(2.0, 3.0))  # -> 9.0

# 2. As a sort key: order parts by stress, highest first
parts = [("bracket", 120e6), ("pin", 240e6), ("plate", 80e6)]
parts.sort(key=lambda part: part[1], reverse=True)

# 3. With map/filter: convert a list of Celsius temps to Kelvin
celsius = [0, 25, 100]
kelvin = list(map(lambda c: c + 273.15, celsius))  # [273.15, 298.15, 373.15]
```

---

## Modelling things with units: the `Beam` dataclass

`fpc/beam.py` shows how to model a real object as a `@dataclass` whose
fields carry **physical units** (via [Pint](https://pint.readthedocs.io/)).
A `Beam` knows its own geometry and computes its structural behaviour — and the
units make the math self-checking.

```python
from fpc.units import Q_  # Q_(value, "unit") builds a quantity
from fpc.beam import Beam

beam = Beam(
    length=Q_(2.0, "m"),
    width=Q_(50, "mm"),
    height=Q_(100, "mm"),
    modulus=Q_(200, "GPa"),  # defaults to structural steel if omitted
)

beam.moment_of_inertia.to("mm**4")  # 4.17e6 mm^4
beam.mass.to("kg")  # 78.5 kg
beam.max_deflection_point_load(load=Q_(5, "kN")).to("mm")  # 1.0 mm
beam.max_bending_stress_point_load(load=Q_(5, "kN")).to("MPa")  # 30 MPa
beam.euler_buckling_load().to("kN")  # 514 kN
```

Why units are worth it:

```python
Q_(1, "m") + Q_(1, "s")          # raises DimensionalityError - caught, not silent
Beam(length=Q_(2, "s"), ...)     # raises ValueError - a time is not a length
```

All quantities must come from the **one shared registry** in
`fpc/units.py` (Pint cannot combine quantities from different registries).

## Simulation & data fitting (SciPy)

Two SciPy workhorses show up where formulas run out:

- **`solve_ivp`** integrates systems that have no closed-form solution.
  `Dynamics.simulate_projectile_drag(...)` flies a projectile *with* air drag
  (and stops itself at ground impact using a solver *event*);
  `Modal.simulate_free_vibration(...)` rings down a spring-mass-damper.
- **`curve_fit`** does the inverse — recover parameters *from* data.
  `Modal.fit_damped_response(time, displacement)` fits a decaying sinusoid to
  measured vibration and returns the natural frequency and damping ratio.

```python
from fpc.modal import Modal

modal = Modal()

# Simulate a known oscillator...
t, x = modal.simulate_free_vibration(
    mass=2.0,
    stiffness=800.0,
    damping=8.0,
    initial_displacement=0.01,
    duration=5.0,
)
# ...then fit the response and recover the inputs (~3.18 Hz, zeta ~0.10).
modal.fit_damped_response(time=t, displacement=x, guess_frequency_hz=3.0)
```

That simulate-then-fit round-trip is checked in the test suite: the fit must
return the parameters the simulation started with.

## Design, reference data & tables

Analysis asks "how much does this beam deflect?"; design asks "what beam
deflects no more than 5 mm?". These pieces answer design questions:

```python
from fpc import Design, Fluids, Properties, Utility

# Root finding (scipy.optimize.brentq): solve equations with no algebraic answer.
Fluids().colebrook_friction_factor(reynolds=1e5, relative_roughness=1e-4)  # 0.0185
Design().rectangular_beam_height_for_deflection(
    load=5000,
    length=2.0,
    modulus=200e9,
    width=0.05,
    max_deflection=0.001,
)  # 0.100 m

# Constrained optimization (scipy.optimize.minimize, SLSQP): lightest beam
# that satisfies stress, deflection, and aspect-ratio limits.
Design().lightest_rectangular_beam(
    load=5000,
    length=2.0,
    modulus=200e9,
    density=7850,
    allowable_stress=150e6,
    max_deflection=0.005,
)  # {'width': 0.0199, 'height': 0.0795, 'mass': 24.8, 'active': ['deflection', 'aspect_ratio'], ...}

# Reference tables (pandas) with interpolation; data and sources in fpc/data/.
props = Properties()
props.water_liquid(temperature_c=37, property="dynamic_viscosity_pa_s")  # linear
props.water_saturation(temperature_c=93, property="pressure_kpa", method="cubic")
props.lightest_w_shape(required_sx_in3=30)["designation"]  # 'W16x26'

# Your own CSV/Excel files
frame = Utility().read_table(file_path="test_log.xlsx")
```

[`examples/sensor_log_analysis.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/sensor_log_analysis.py) shows the
full pandas workflow (clean, group, resample, filter, export to Excel), and
[`examples/vectorization.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/vectorization.py) compares Python loops
with NumPy arrays.

Units: methods that take plain numbers expect **SI units** (the docstring
says so for every parameter); use Pint at the boundaries where units are
mixed. See [docs/units.md](https://github.com/kovirlabs/first-principles-code/blob/main/docs/units.md).

## Machine design, fatigue & HVAC

The everyday sizing checks of a mechanical or HVAC engineer, following
Shigley's *Mechanical Engineering Design* and the *ASHRAE Handbook -
Fundamentals*: bolts, shafts, springs, bearings and welds
(`MachineElements`), stress-life fatigue (`Fatigue`), Euler/Johnson column
buckling (`Material`), and moist-air properties (`Psychrometrics`).

```python
from fpc import Fatigue, MachineElements, Material, Psychrometrics

me = MachineElements()
me.bolt_tightening_torque(preload=37.9e3, nominal_diameter=0.012)  # 91 N*m (K = 0.2)
me.bearing_l10_life_hours(dynamic_load_rating=30e3, equivalent_load=3e3, speed_rpm=1500)  # 11 111 h

# Fatigue: endurance limit -> Marin factors -> mean-stress criterion.
f = Fatigue()
se = f.marin_endurance_limit(
    specimen_endurance_limit=f.endurance_limit_steel(ultimate_strength=690e6),
    surface_factor=f.surface_factor(ultimate_strength=690e6, finish="machined"),
    size_factor=f.size_factor(diameter=0.03),
)  # 237 MPa
f.goodman_safety_factor(
    alternating_stress=120e6, mean_stress=80e6, endurance_limit=se, ultimate_strength=690e6
)  # 1.61

# Column buckling: picks Euler or Johnson from the slenderness ratio.
Material().critical_buckling_load(
    modulus=200e9, moment_of_inertia=1.917e-8, area=4.909e-4, length=0.5, yield_strength=250e6
)  # {'critical_load': 97848.2, 'formula': 'johnson', 'slenderness_ratio': 80.0, ...}

# Psychrometrics (temperatures in degC, RH as a fraction): solved with brentq.
psy = Psychrometrics()
psy.dew_point(temperature_c=25, relative_humidity=0.5)  # 13.9 degC
psy.wet_bulb(temperature_c=25, relative_humidity=0.5)  # 17.9 degC
```

## Radiology & medical imaging

Six classes cover the physics and image handling a radiology student
(radiologic technologist, resident, or medical physics student) works with
every day. Run the guided tour with `uv run examples/radiology_demo.py`. It prints one
worked example per modality and saves `examples/output/radiology.png`, which shows a real CT
slice in abdomen, lung, and bone windows.

| Class | Module | What it covers |
| --- | --- | --- |
| `Radiation` | `fpc/radiation.py` | Inverse square law, attenuation (mu, HVL, TVL, shielding), photon energy, radioactive and effective half-life, equivalent/effective dose with ICRP 103 weighting factors |
| `Radiography` | `fpc/radiography.py` | mAs, 15% rule, exposure-maintenance (SID) formula, grid conversion, heat units, magnification, geometric unsharpness, detector Nyquist limit, deviation index |
| `CT` | `fpc/ct.py` | Hounsfield units, DICOM rescale, window width/level with presets, rough HU tissue lookup, DLP and effective dose estimate |
| `MRI` | `fpc/mri.py` | Larmor frequency, T1 recovery, T2 decay, spin-echo signal, T1/T2/PD weighting from TR/TE |
| `Ultrasound` | `fpc/ultrasound.py` | Wavelength, echo depth, acoustic impedance and reflection, attenuation, axial resolution, PRF depth limit, Doppler shift and velocity |
| `Dicom` | `fpc/dicom.py` | Read DICOM with pydicom, summarize technical tags, pixels in HU, pixel spacing, basic de-identification, PNG export |

```python
from pydicom.data import get_testdata_file  # sample images, no patient data
from fpc import CT, Dicom, Radiography, Radiation

radiation = Radiation()
radiation.effective_dose(organ_equivalent_doses={"thyroid": 10.0})  # -> 0.4 mSv

Radiography().exposure_maintenance_mas(original_mas=10, original_sid=100, new_sid=180)  # 32.4

dicom, ct = Dicom(), CT()
ds = dicom.read(path=get_testdata_file("CT_small.dcm"))
hu = dicom.pixel_array_in_units(dataset=ds)  # stored values -> Hounsfield units
lung = ct.apply_window(hounsfield=hu, preset="lung")  # whole slice windowed in one call
safe = dicom.anonymize(dataset=ds)  # blank PHI before sharing
```

> **Teaching use only.** These are textbook calculations for learning. They
> are not validated for clinical decisions, patient dosimetry, or shielding
> design. Use your department's protocols and a qualified medical physicist
> for those. `Dicom.anonymize` removes common direct identifiers only, which
> is *not* full de-identification under DICOM PS3.15 or HIPAA.

Python packages for medical imaging (SimpleITK, nibabel, MONAI, ...) are
listed in [PACKAGES.md](https://github.com/kovirlabs/first-principles-code/blob/main/PACKAGES.md#medical-imaging).

**Learning resources:** [Radiopaedia](https://radiopaedia.org/) (cases and
physics articles), [pydicom user guide](https://pydicom.github.io/pydicom/stable/tutorials/index.html),
[NIST XCOM attenuation data](https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html),
[ICRP Publication 103](https://www.icrp.org/publication.asp?id=ICRP%20Publication%20103),
[The Cancer Imaging Archive](https://www.cancerimagingarchive.net/) (free
de-identified datasets).

## Tests

The library methods are pure functions with known textbook answers, which makes
them ideal to test. The suite in `tests/` doubles as a pytest tutorial — it
demonstrates `pytest.approx` (comparing floats), `@pytest.mark.parametrize`
(table-driven tests), and the `tmp_path` fixture (temporary files).

```bash
uv run pytest                          # run everything
uv run pytest tests/test_dynamics.py   # run one file
uv run pytest -k projectile            # run tests whose name matches "projectile"
```

## Plotting

`main.py` uses **matplotlib** to plot the acceleration -> velocity -> position
cascade and saves it to `displacement.png`. The pattern — compute arrays with
NumPy/SciPy, then visualize with matplotlib — is the everyday replacement for
MATLAB's figures. See `plot_motion()` in `main.py` for a worked example.

## Python packages for science, engineering & data work

The ten to know first. **[PACKAGES.md](https://github.com/kovirlabs/first-principles-code/blob/main/PACKAGES.md)** has the full list,
organized by engineering field (structural, thermal/fluids, electrical,
controls, CAD, optimization, medical imaging, tool building, performance).

| Package | Use it for |
| --- | --- |
| [NumPy](https://numpy.org/) | Fast N-dimensional arrays and vectorised math — the foundation of everything below |
| [SciPy](https://scipy.org/) | Integration, optimization, root finding, interpolation, signal processing, statistics |
| [Matplotlib](https://matplotlib.org/) | Plotting and figures (the MATLAB-style `pyplot` interface) |
| [pandas](https://pandas.pydata.org/) | Tabular data, time series, CSV/Excel I/O |
| [SymPy](https://www.sympy.org/) | Symbolic math / computer algebra (a free Maple/Mathematica) |
| [Pint](https://pint.readthedocs.io/) | Physical units and automatic unit conversion |
| [Jupyter](https://jupyter.org/) | Notebooks that mix code, math, plots, and prose |
| [CoolProp](http://www.coolprop.org/) | Thermophysical fluid properties for thermo/HVAC work |
| [python-control](https://python-control.readthedocs.io/) | Control-systems design (a free Control System Toolbox) |
| [pytest](https://docs.pytest.org/) | Testing framework to verify your calculations stay correct |

Add any of them with `uv add <package>`.

---

## Learning resources

**Python fundamentals**
- [The Official Python Tutorial](https://docs.python.org/3/tutorial/)
- [Real Python](https://realpython.com/) — practical, well-edited tutorials
- [Automate the Boring Stuff with Python](https://automatetheboringstuff.com/) (free online)

**Scientific & numerical Python**
- [SciPy Lecture Notes](https://scipy-lectures.org/) — a full course in the scientific stack
- [NumPy: the absolute basics for beginners](https://numpy.org/doc/stable/user/absolute_beginners.html)
- [Python Numerical Methods (UC Berkeley)](https://pythonnumericalmethods.berkeley.edu/) — free online textbook
- [Nature: A guide to NumPy](https://www.nature.com/articles/s41586-020-2649-2)

**Engineering & for MATLAB users**
- [NumPy for MATLAB users](https://numpy.org/doc/stable/user/numpy-for-matlab-users.html) — translation cheat sheet
- [python-control Library docs](https://python-control.readthedocs.io/)
- [Engineering with Python](https://www.engineeringwithpython.com/)

**Tooling**
- [uv documentation](https://docs.astral.sh/uv/)
- [Real Python: Python Virtual Environments](https://realpython.com/python-virtual-environments-a-primer/)

---

## Use this library in your own project

`fpc` is an installable package, so your own scripts do not have to live in
this repository.

```bash
# From PyPI (once released; see docs/releasing.md)
pip install first-principles-code          # or: uv add first-principles-code

# Straight from GitHub, in your own uv project
uv add git+https://github.com/kovirlabs/first-principles-code

# Or with pip, from a local clone (editable: your edits take effect immediately)
pip install -e path/to/first-principles-code
```

```python
from fpc import Fluids, Properties
```

Installing also gives you the `fpc` command
(`fpc pipe-flow --flow-l-s 12 --diameter-mm 102.3 --length-m 120`; see
[docs/building-tools.md](https://github.com/kovirlabs/first-principles-code/blob/main/docs/building-tools.md)). To pin a version, add
`@<tag-or-commit>` to the git URL.

Every calculation in the library is also reachable from the terminal,
without writing any code:

```bash
fpc search "pipe pressure drop"           # find a calculation
fpc describe Fluids.pipe_flow             # its inputs, units and formula
fpc run Fluids.reynolds_number density=998 velocity=2 length=0.05 viscosity=0.001

# How sure is the answer? Give inputs a spread and run 10 000 cases (Monte Carlo)
fpc uncertainty Fluids.reynolds_number density=998 velocity=normal:2,0.1 length=0.05 viscosity=0.001

# File it: a Markdown calc sheet with method, inputs and units, result, review checklist
fpc report Fluids.reynolds_number density=998 velocity=2 length=0.05 viscosity=0.001 --out re.md
```

Or use every calculation from a web form, with uncertainty and calc-sheet
tabs: `uv run streamlit run apps/calculator.py`. See
[docs/trusting-results.md](https://github.com/kovirlabs/first-principles-code/blob/main/docs/trusting-results.md).

## Use it with AI assistants (Ollama, LM Studio, Claude, ...)

Small local models are unreliable at arithmetic. The `fpc-mcp` command is an
[MCP](https://modelcontextprotocol.io) server that lets any MCP-capable AI app
use this library as its calculator: the model picks the formula, and tested
Python does the maths. For example, in LM Studio's `mcp.json`:

```json
{
  "mcpServers": {
    "fpc": {
      "command": "uvx",
      "args": ["--from", "first-principles-code[mcp]", "fpc-mcp"]
    }
  }
}
```

Setup for LM Studio, Ollama front ends (Open WebUI, ollmcp, Continue),
Claude Desktop and Claude Code is in
[docs/ai.md](https://github.com/kovirlabs/first-principles-code/blob/main/docs/ai.md). AI *coding* agents should read
[AGENTS.md](https://github.com/kovirlabs/first-principles-code/blob/main/AGENTS.md) and [llms.txt](https://github.com/kovirlabs/first-principles-code/blob/main/llms.txt), a
generated one-line-per-method index of the library.

## Developer tooling

| Command | What it does |
| --- | --- |
| `uv sync --all-groups --all-extras` | Install everything: runtime, dev tools, notebooks, docs, apps, MCP server |
| `uv run pytest` | Tests, including running every example and notebook |
| `uv run ruff check .` / `uv run ruff format .` | Lint / auto-format |
| `uv run mypy` | Type-check the `fpc` package |
| `uv run -p 3.11 pytest` | Run the tests on a specific Python version |
| `uv run scripts/python_support.py check` | Supported Python versions declared consistently ([policy](https://github.com/kovirlabs/first-principles-code/blob/main/docs/python-versions.md)) |
| `uv run pre-commit install` | Run ruff and pytest automatically before each commit |
| `uv run --group docs mkdocs serve` | Preview the API docs site, generated from the docstrings |

CI runs all of these on every pull request; the docs site is published to
GitHub Pages from `main`.

## Project layout

```
first-principles-code/
├── main.py              # displacement demo (start here)
├── gui.py               # MATLAB-style console GUI (uv run gui.py)
├── fpc/                 # the library: one class per engineering domain
│   ├── __init__.py      # re-exports every class
│   ├── units.py         # shared Pint unit registry (ureg, Q_)
│   ├── beam.py          # unit-aware Beam dataclass
│   ├── design.py        # root finding & constrained optimization
│   ├── properties.py    # reference-table lookups with interpolation
│   ├── utility.py       # JSON/CSV/Excel/file-picker helpers
│   ├── cli.py           # the `fpc` terminal command
│   ├── registry.py      # catalogue of every calculation (types, units, schemas)
│   ├── mcp_server.py    # `fpc-mcp`: MCP server for AI apps
│   ├── uncertainty.py   # Monte Carlo on any calculation
│   ├── report.py        # Markdown calc sheets
│   ├── hints.py         # shared type-hint names (ArrayLike, FloatArray)
│   ├── data/            # cited reference tables (CSV) + sources
│   ├── dynamics.py, statics.py, modal.py, thermo.py, fluids.py,
│   ├── material.py, gear.py, electrical.py, mechatronics.py, controls.py,
│   ├── machine_elements.py, fatigue.py, psychrometrics.py
│   └── radiation.py, radiography.py, ct.py, mri.py, ultrasound.py, dicom.py
├── examples/            # worked problems, one script each (+ tools/ ladder)
├── apps/                # Streamlit calculator: a form for every calculation
├── templates/           # copy-and-adapt starting script
├── notebooks/           # Jupyter notebooks
├── docs/                # guides + API docs site sources (mkdocs.yml)
├── tests/               # pytest suite (uv run pytest)
├── scripts/             # maintenance: python_support.py (version ratchet), try_local_model.py (MCP + Ollama)
├── pyproject.toml       # metadata, dependencies, tool config
├── PACKAGES.md          # Python packages by engineering field
├── SPEC.md              # original project design spec
├── ROADMAP.md           # improvement backlog
├── CHANGELOG.md         # release notes
├── AGENTS.md            # guidance for AI coding agents
├── llms.txt             # generated index of every method (uv run fpc llms-txt)
├── CONTRIBUTOR.md       # how to contribute
├── LICENSE              # Apache 2.0
└── README.md            # you are here
```

## The console GUI

`gui.py` is a small tkinter app that mimics the technical computing command
window interface. Launch it with:

```bash
uv run gui.py
```

- Type a Python expression in the command box and press **Enter** (or **Run**).
  The result prints to the **Session log** and is recorded in the **Workspace**
  table — just like MATLAB's `ans`/workspace.
- The interpreter comes preloaded with `math`, `numpy as np`, and a ready
  instance of every library class (`dyn`, `statics`, `thermo`, `fluids`, `design`, `props`, …), so
  you can compute immediately:
  `dyn.projectile_range(speed=20, angle_deg=45)`.
- **Open Script** loads a `.py` file into the command box; **Run Script** runs
  the whole box at once.
- **Export CSV** / **Export JSON** save every recorded result to disk (via
  `fpc.Utility`).

> The GUI needs a graphical display. The evaluation engine (the `Session`
> class) is separated from the Tk widgets, so it can be imported and scripted
> without a window.

---

## Contributing

Contributions are welcome — this is a teaching template, so clear,
well-explained code is the product. See [CONTRIBUTOR.md](https://github.com/kovirlabs/first-principles-code/blob/main/CONTRIBUTOR.md) for the
development setup, coding conventions, and how to submit changes.

Quick version of the conventions:

- Pass arguments **by keyword** (`acceleration=9.81`, not `9.81`). Methods use
  keyword-only signatures (`def method(self, *, ...)`) to enforce this.
- Every class and method gets a **docstring** with parameter units.
- Comment the **why** of non-obvious math, not just the what.
- Keep one engineering domain per file, one class per file.
- Every new method/class needs a test.

## License

Licensed under the [Apache License 2.0](https://github.com/kovirlabs/first-principles-code/blob/main/LICENSE). © 2026 Evan Gress.
