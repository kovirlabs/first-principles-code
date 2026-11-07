<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/) (while the version is `0.x`, minor
releases may still change the API).

## [Unreleased]

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
