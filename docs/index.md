<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# First Principles Code

A Python library of engineering calculations, written to teach. Every class
covers one engineering domain, every method takes named arguments, and every
docstring states its formula and the units of each parameter. The **API
reference** in the menu is generated directly from those docstrings.

## Install

```bash
# Work inside this repository
git clone https://github.com/kovirlabs/first-principles-code
cd first-principles-code
uv sync

# Or use the library from your own project
uv add git+https://github.com/kovirlabs/first-principles-code
```

## Ten-second tour

```python
from fpc import Fluids, Properties, Design

props = Properties()
mu = props.water_liquid(temperature_c=37, property="dynamic_viscosity_pa_s")

Fluids().colebrook_friction_factor(reynolds=1e5, relative_roughness=1e-4)  # 0.0185

Design().rectangular_beam_height_for_deflection(
    load=5000,
    length=2.0,
    modulus=200e9,
    width=0.05,
    max_deflection=0.001,
)  # 0.100 m
```

## Where to go next

- **Guides:** [units, floats or Pint?](units.md) and
  [from calculation to tool](building-tools.md).
- **Worked examples:** the
  [`examples/`](https://github.com/kovirlabs/first-principles-code/tree/main/examples)
  folder has one script per realistic problem: pump sizing, beam selection,
  PID tuning, and more.
- **Notebooks:** [`notebooks/`](https://github.com/kovirlabs/first-principles-code/tree/main/notebooks).
- **Which package for my field?** See
  [PACKAGES.md](https://github.com/kovirlabs/first-principles-code/blob/main/PACKAGES.md).
