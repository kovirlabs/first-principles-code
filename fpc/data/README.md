<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Reference data

Small, cited tables that `fpc.Properties` loads with pandas, so the library
reads reference values from data instead of hard-coding constants. They live
inside the `fpc` package (not the repo root) so they ship when the package is
installed elsewhere.

> **Teaching data.** Values are typical/nominal. For real design work, use the
> governing standard or your supplier's certified data.

| File | Contents | Source |
| --- | --- | --- |
| `water_saturation.csv` | Saturated water vs temperature: pressure, liquid/vapor density, enthalpies | IAPWS-95 formulation, computed with [CoolProp](http://www.coolprop.org/) 8.0.0 by `generate_water_tables.py`. Matches the saturated-water tables in Çengel & Boles, *Thermodynamics*, Table A-4. |
| `water_liquid_1atm.csv` | Liquid water at 101.325 kPa: density, viscosity, specific heat, conductivity | Same as above (IAPWS-95 / IAPWS 2008 viscosity / IAPWS 2011 conductivity via CoolProp). |
| `materials.csv` | Density, E, yield & ultimate strength, CTE, thermal conductivity for common metals and one polymer | Typical room-temperature values from [MatWeb](https://www.matweb.com/) / ASM International data sheets. Strengths are typical, **not** minimum design allowables. |
| `w_shapes.csv` | A selection of AISC wide-flange (W) beams: weight, area, depth, Ix, Sx (US units) | [AISC Shapes Database v16.0](https://www.aisc.org/publications/steel-construction-manual-resources/16th-ed-steel-construction-manual/aisc-shapes-database-v16.0/). Check `tests/test_properties.py`, which verifies Sx ≈ Ix/(d/2) and weight ≈ 3.4·A for every row. |

To regenerate the water tables: `uv run --with CoolProp python fpc/data/generate_water_tables.py`
(run it from `fpc/data/`).
