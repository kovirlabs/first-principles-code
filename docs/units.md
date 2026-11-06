<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Units: plain floats or Pint?

Unit mistakes are among the most expensive errors in engineering. The
project uses **two approaches on purpose**, and this page explains when to
use each.

| | Plain floats (SI) | Pint quantities |
| --- | --- | --- |
| Used by | Most classes: `Dynamics`, `Statics`, `Fluids`, `Thermo`, `Design`, `Gear`, ... | `Beam`, and anywhere you build `Q_(...)` yourself |
| Looks like | `fluids.reynolds_number(density=998, velocity=2, length=0.05, viscosity=1e-3)` | `beam.max_deflection_point_load(load=Q_(5, "kN")).to("mm")` |
| Speed | Fastest; works directly with NumPy and SciPy | Slower; some SciPy functions need plain numbers |
| Catches mistakes | No. `length=50` (meant mm) silently gives a wrong answer | Yes. Adding metres to seconds raises an error |
| Best for | Quick formulas, inner loops, solvers, optimization | Mixed unit systems, data from catalogues and drawings, input/output boundaries |

## The rule

> **Plain floats for the math. Pint at the edges.**

1. **Library methods that take floats always expect SI base units**: metres,
   kilograms, seconds, newtons, pascals, kelvin (or °C where the parameter
   name says `_c`). The docstring states the unit of every parameter.
   Exceptions are named in the parameter itself, such as `angle_deg`,
   `motor_rpm`, `energy_kev`, `time_ms`, and the radiology classes, which
   follow clinical conventions (cm, keV, mSv).
2. **When inputs arrive in mixed or non-SI units** (a drawing in inches, a
   catalogue in in³, a datasheet in ksi), wrap them in Pint and convert to SI
   *once*, at the boundary, before calling the library.
3. **When a result leaves your script** (a report, a plot label), convert to
   the unit your reader expects with `.to(...)`.

```python
from fpc import Fluids, Q_

# Inputs as they appear on the drawing / datasheet:
diameter = Q_(4.026, "inch")         # 4" Schedule 40 inner diameter
flow = Q_(190, "gallon/minute")

# Boundary: convert to SI floats once, then use the fast float API.
result = Fluids().pipe_flow(
    flow=flow.to("m**3/s").magnitude,
    diameter=diameter.to("m").magnitude,
    length=Q_(400, "ft").to("m").magnitude,
    roughness=Q_(0.0018, "inch").to("m").magnitude,
    density=998.2, viscosity=1.0e-3,
)

# Boundary out: attach units again and report in the reader's units.
print(Q_(result["pressure_drop"], "Pa").to("psi"))
```

See [`examples/beam_selection.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/beam_selection.py)
for a full example that mixes SI loads with a US-unit steel catalogue.

## Habits that prevent unit bugs (with or without Pint)

- **Put the unit in the name**: `length_m`, `flow_l_s`, `temperature_c`. The
  examples, the template, and the CLI all do this.
- **Convert once, at the boundary.** Never sprinkle `/ 1000` through the math.
- **Absolute vs gauge pressure, and kelvin vs Celsius.** Gas laws and Carnot
  efficiency need absolute values. Pint treats `degC` as an *offset* unit:
  `Q_(20, "degC") * 2` raises an error because "twice 20 °C" is ambiguous.
  Use `delta_degC` for temperature differences.
- **Degrees vs radians.** Python's `math.sin` uses radians. Methods that take
  degrees say so (`angle_deg`) and convert inside.
- **Use one registry.** All Pint quantities must come from `fpc.units.ureg`
  (or `fpc.Q_`). Quantities from different registries cannot be combined.

## Why not Pint everywhere?

Pint everywhere would catch more mistakes. It would also make every method
slower, complicate SciPy calls (solvers and optimizers want plain arrays), and
add noise to examples whose point is the physics. The split keeps the library
fast and readable while still giving you a safety net where unit mistakes
actually happen: at the boundary between your data and your math.
