<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/) (while the version is `0.x`, minor
releases may still change the API).

## [Unreleased]

### Added

- New domains: `MachineElements` (bolt torque, preload and joint
  stiffness, shaft diameter, spring rate and stress, bearing L10 life,
  fillet welds), `Fatigue` (endurance limit, Marin factors, Goodman,
  Soderberg, Gerber and ASME-elliptic safety factors, S-N curve) and
  `Psychrometrics` (saturation pressure, humidity ratio, relative humidity,
  dew point, enthalpy, specific volume, wet bulb). `Material` gains
  Johnson buckling, slenderness ratios and an Euler/Johnson chooser.
  Tests check published ASHRAE and Shigley table values.
- `fpc-mcp --domains fluids,thermo`: also serve each calculation in those
  domains as its own MCP tool, with the registry's input schema, for
  capable models that do better calling a tool directly.
- `fpc.uncertainty`: Monte Carlo on any calculation. Give inputs as
  `Normal`, `Uniform` or `Triangular` distributions; get the mean,
  standard deviation, percentiles, a 95 % interval and each input's share
  of the spread. Also `fpc uncertainty` (`velocity=normal:2,0.1`).
- `fpc.report` and `fpc report`: a Markdown calc sheet for any calculation
  (method, inputs with units, defaults, result, optional uncertainty,
  review checklist), ready for a design file or `pandoc`.
- `apps/calculator.py`: a Streamlit web form for every calculation,
  generated from the registry, with uncertainty and calc-sheet tabs.
- `scripts/try_local_model.py`: ask an Ollama model engineering questions
  through `fpc-mcp` and check its answers against the library.

### Changed

- The MCP `calculate` tool's `arguments` is optional so that a model
  which puts the inputs beside `key` gets a precise correction instead of
  a validation error it cannot act on.
- mypy now requires every function in `fpc/` to be fully annotated.

## [0.1.0] - first PyPI release

### Added

- Domain classes for dynamics, statics, modal analysis, thermodynamics,
  fluids, materials, gears, electrical, mechatronics, controls, design
  (root finding and optimization), reference-data properties, and radiology
  (radiation, radiography, CT, MRI, ultrasound, DICOM).
- `fpc.registry`: a machine-readable catalogue of every calculation, built
  from type hints and docstring unit tags.
- `fpc search`, `fpc describe`, `fpc run` and `fpc llms-txt` commands.
- `fpc-mcp`: an MCP server so local and hosted AI models can call the
  library (install with the `mcp` extra).
- Type hints on every public method, and a `[unit]` tag on every numeric
  parameter.
- `llms.txt` and `AGENTS.md` for AI coding assistants.
- Supports Python 3.11 to 3.15 (every CPython version not past end-of-life),
  tested on each in CI. `scripts/python_support.py` keeps the range
  consistent and a monthly job opens an issue when it is time to move it.
