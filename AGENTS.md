<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Aider, Codex, Continue, ...)
that write code **using** or **contributing to** this library.

## Using the library

- Import the domain classes from `fpc` and call methods on an instance:
  `from fpc import Fluids; Fluids().reynolds_number(density=998, velocity=2, length=0.05, viscosity=1e-3)`.
- **Every argument is keyword-only.** Positional calls raise `TypeError`.
- **Units:** plain floats in SI unless the docstring's `[unit]` tag says
  otherwise (e.g. `[degC]`, `[mm]`, `[mGy]`). Convert inputs before calling.
  Pint quantities (`fpc.Q_`) are used only by `fpc.Beam`; see `docs/units.md`.
- **Find the right method** without reading every file:
  - `llms.txt`: one line per method with parameter units;
  - `uv run fpc search "keywords"` and `uv run fpc describe Domain.method`;
  - `from fpc import registry; registry.search("...")` in Python.
- **Reference data** (water properties, materials, steel W-shapes) lives in
  `fpc/data/*.csv` and is read with `fpc.Properties`; do not hard-code values
  that are already in a table.
- Prefer calling an existing method over re-deriving a formula. If one is
  missing, say so (and consider adding it; see below).

## Contributing to the library

Read `CLAUDE.md`, `CONTRIBUTOR.md` and `ROADMAP.md` first. House rules:

- Keyword-only arguments (`def method(self, *, ...)`), full type hints, and a
  docstring with `:param name: description [unit]` for every parameter
  (`[-]` for dimensionless) and a `:returns:` line with its unit.
  `tests/test_registry.py` fails if a numeric parameter lacks a unit tag.
- Comment the *why*: this is a teaching codebase.
- After adding or renaming a public method, regenerate the index:
  `uv run fpc llms-txt > llms.txt`.
- Checks before you finish: `uv run ruff check .`, `uv run ruff format .`,
  `uv run mypy`, `uv run pytest`.
