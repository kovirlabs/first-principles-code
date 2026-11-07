<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Trusting a result: uncertainty and calc sheets

A number from a calculation is only as good as its inputs, and a result that
goes into a design file has to be checkable by someone else. `fpc` has two
helpers for this, and both work with **every** calculation in the library
because they are driven by the [calculation registry](api/registry.md).

## How sure is the answer? Monte Carlo

Real inputs are uncertain: a measured flow is "12 L/s, give or take 3 %", a
pipe's roughness is "somewhere between 0.02 and 0.09 mm". Monte Carlo
simulation runs the calculation thousands of times with inputs drawn at
random from those ranges and reports the spread of the answers.

```python
from fpc.uncertainty import Normal, Uniform, monte_carlo

result = monte_carlo(
    "Fluids.pipe_flow",
    {
        "flow": Normal(mean=0.012, std=0.0004),          # 12 L/s, 1 sigma = 0.4 L/s
        "diameter": 0.1023,
        "length": 120,
        "roughness": Uniform(low=0.02e-3, high=0.09e-3),
        "density": 998,
        "viscosity": 1.0e-3,
    },
    output="pressure_drop",   # pipe_flow returns a dict; study this entry
    seed=1,                   # same random numbers every run: repeatable
)
result.mean, result.std       # Pa
result.interval(95)           # (low, high) holding 95 % of the runs
result.sensitivity            # {"flow": 0.7, "roughness": 0.3}: what to measure better
```

| Distribution | Use it when you know |
|---|---|
| `Normal(mean, std)` | a measurement or manufacturing variation (one standard deviation) |
| `Uniform(low, high)` | only the bounds (a tolerance band) |
| `Triangular(low, mode, high)` | the bounds and a most likely value (an expert's estimate) |

From the terminal, write an uncertain input as `name=normal:MEAN,STD`,
`name=uniform:LOW,HIGH` or `name=triangular:LOW,MODE,HIGH`:

```bash
fpc uncertainty Fluids.reynolds_number density=998 velocity=normal:2,0.1 \
    length=0.05 viscosity=uniform:0.0009,0.0011 --seed 1
```

Things to know:

- A datasheet's "+/- x" is often two or three standard deviations, not one.
- `sensitivity` assumes the inputs are independent and each one pushes the
  result in one direction; it is a first look, not a full variance analysis.
- 10 000 samples (the default) is plenty for engineering work; the error in
  the mean shrinks like 1/sqrt(samples).

## File it: calc sheets

`fpc report` writes a calculation up the way a checked hand calc is filed:
the method and its assumptions (from the docstring), every input with its
unit (defaults included, so nothing is hidden), the result, the library
version, and a review checklist.

```bash
fpc report Thermo.conduction_heat_rate conductivity=0.72 area=12 \
    delta_temperature=25 thickness=0.2 --title "North wall heat loss" --out wall.md
pandoc wall.md -o wall.pdf     # optional: PDF or Word via pandoc
```

```python
from fpc.report import calc_report

text = calc_report("Thermo.conduction_heat_rate",
                   {"conductivity": 0.72, "area": 12, "delta_temperature": 25, "thickness": 0.2},
                   title="North wall heat loss",
                   uncertainty=result_of_monte_carlo)   # optional extra section
```

The sheet is Markdown, so it can live in the project repository next to the
script that produced it and be reviewed in a pull request.

## Both in a browser

The [calculator app](building-tools.md#a-form-for-every-calculation) puts
every calculation in a web form, with an **Uncertainty** tab (sliders for
+/- % on each input) and a **Calc sheet** tab that downloads the report.
