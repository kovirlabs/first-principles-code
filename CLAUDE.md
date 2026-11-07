<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A teaching template: a Python script + class library meant to functionally teach engineers Python techniques and empower them to solve real-world engineering problems. Because it's a teaching artifact, code clarity, docstrings, and explanatory comments are first-class deliverables — not afterthoughts. See "Authoring conventions" below.

The original design lives in [SPEC.md](SPEC.md); the improvement backlog lives in [ROADMAP.md](ROADMAP.md). Read both before starting new work.

## Current state

- `main.py` — displacement demo (closed form, `scipy` integration, library call) that prints results and saves a plot.
- `fpc/` — the installable package (import name `fpc`, distribution name `first-principles-code`). One class per engineering domain (Dynamics, Statics, Modal, Thermo, Fluids, Psychrometrics, Material, Gear, MachineElements, Fatigue, Electrical, Mechatronics, Controls, Utility, Design, Properties, plus the radiology set Radiation, Radiography, CT, MRI, Ultrasound, Dicom), the shared Pint registry in `fpc/units.py`, and the unit-aware `Beam` dataclass.
- `fpc/registry.py` — introspects every domain method (type hints + `[unit]` docstring tags) into a catalogue with JSON Schemas; drives `fpc search/describe/run`, the MCP server (`fpc/mcp_server.py`, command `fpc-mcp`, optional `mcp` extra) and the generated `llms.txt`. See `docs/ai.md`.
- `fpc/uncertainty.py` (Monte Carlo on any calculation, `fpc uncertainty`) and `fpc/report.py` (Markdown calc sheets, `fpc report`) — both built on the registry. See `docs/trusting-results.md`.
- `apps/calculator.py` — Streamlit form for every calculation, generated from the registry (`uv run streamlit run apps/calculator.py`).
- `gui.py` — tkinter MATLAB-style console; the `Session` class is GUI-free and tested.
- `tests/` — pytest suite, run in CI (`.github/workflows/tests.yml`).
- `examples/` — one self-contained worked problem per script; `templates/` — copy-and-adapt starting scripts; `notebooks/` — Jupyter notebooks; `fpc/data/` — cited reference tables (CSV); `docs/` — mkdocs site sources and guides.
- `PACKAGES.md` — curated package list by engineering field.

## Tooling & commands

Python **3.11–3.15** (every CPython version not past end-of-life; see `docs/python-versions.md`), managed with **uv**. Write code that runs on the oldest supported version; ruff and mypy target it. Change the range only with `uv run scripts/python_support.py set --oldest X.Y --newest X.Y`.

```bash
uv sync --all-groups --all-extras  # install runtime + dev + notebook deps + mcp extra
uv run main.py           # run the main demo
uv run pytest            # run tests (single test: uv run pytest path::test_name)
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy fpc          # type-check the package
uv run mkdocs serve      # preview the API docs site
uv run pre-commit install  # enable git hooks (ruff + pytest)
uv run fpc llms-txt > llms.txt  # regenerate after changing public methods (a test checks it)
uv build                 # build sdist + wheel; releasing steps are in docs/releasing.md
uv run scripts/python_support.py check   # supported Python versions consistent everywhere
uv run --extra mcp scripts/try_local_model.py --model qwen3:14b --think off  # MCP server vs a local Ollama model
uv run -p 3.11 pytest    # run the tests on a specific Python (CI runs every supported one)
```

## Library architecture

`fpc/` holds one class per engineering domain, each grouping related calculation methods. When adding a domain, follow the checklist in [CONTRIBUTOR.md](CONTRIBUTOR.md) (module, class, `__init__` export, GUI preload, tests, README row, docs page).

Units: plain floats in SI units for quick formulas; Pint quantities (`fpc.units.Q_`) where units are mixed or error-prone. See `docs/units.md`.

## Authoring conventions

These exist to make the code itself a teaching tool — follow them in all new code:

- Use keyword-only arguments (`def method(self, *, ...)`) to demonstrate verbose, explicit variable passing.
- Every class and method gets a docstring with parameter units — they double as documentation examples. Write units as a `[unit]` tag on each `:param`/`:returns:` line (`[-]` for dimensionless); the registry parses them and a test enforces them.
- Type-hint every public method (`float`, `int`, `str`, `Literal[...]`, and `ArrayLike` / `FloatArray` from `fpc.hints` for arrays); the registry turns hints into JSON Schema.
- Comment significant code sections explaining the *why*, not just the *what*.
