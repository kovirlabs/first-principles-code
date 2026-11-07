<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Roadmap

Planned improvements to make this project a launching point for engineers to
write their own scripts and tools. It complements the "Python concepts to
teach" list in [SPEC.md](SPEC.md). Work items here are about the project as a
whole: structure, tooling, docs, and discoverability.

**How to use this file:** check a box when an item is merged, and add the PR
number next to it. Items marked **(decision needed)** wait on the maintainer's
call before work starts. Keep items in priority order within each section.

_Last reviewed: 2026-11-07. Sections 0-8 were built in #6 (branch
`feat/roadmap-buildout`); see "Follow-ups" for what remains._

---

## 0. Housekeeping (quick, low risk)

- [x] **Update `CLAUDE.md`.** It still says `fpc/` is empty, `main.py` is
  hello-world, and there are no tests or README. Rewrite "Current state" to
  match reality (14 domain classes + 6 radiology classes, 109 tests, CI, GUI).
- [x] **Stop tracking `.idea/`.** `git rm -r --cached .idea` and add `.idea/`
  to `.gitignore` (PyCharm settings are per-user).
- [x] **Fix stale README numbers.** "40+ tests" -> current count (109), or
  drop the number so it can't go stale.

## 1. Package discovery: `PACKAGES.md`

- [x] Create `PACKAGES.md`, a curated list of Python packages **organized by
  engineering field**, one line each saying *when* to use it:
  - Core stack (NumPy, SciPy, pandas, Matplotlib, SymPy, Pint, Jupyter)
  - Mechanical and structural (e.g. sectionproperties, anastruct, PyNite,
    OpenSeesPy, FEniCSx / scikit-fem)
  - Thermal and fluids (CoolProp, Cantera, fluids, ht)
  - Electrical and signals (scipy.signal, PySpice, scikit-rf, lcapy)
  - Controls and robotics (python-control, harold, roboticstoolbox-python)
  - CAD, geometry, and meshing (CadQuery, build123d, trimesh, gmsh, PyVista)
  - Optimization and uncertainty (scipy.optimize, Pyomo, CVXPY, SALib, pymoo)
  - Data and ML (scikit-learn, statsmodels, PyTorch)
  - Medical imaging (move the README table here: pydicom, SimpleITK, ...)
  - Tool building (argparse, Typer, Streamlit, tkinter, PyInstaller)
  - Performance (Numba, Cython, JAX)
- [x] End with links to existing curated lists:
  [awesome-scientific-python](https://github.com/rossant/awesome-scientific-python),
  [awesome-scientific-computing](https://github.com/nschloe/awesome-scientific-computing),
  [awesome-python: Science](https://github.com/vinta/awesome-python#science),
  [awesome-python-chemistry](https://github.com/lmmentel/awesome-python-chemistry).
- [x] Shrink the README package table to the top ~10 and link to `PACKAGES.md`.
- [x] Verify every package is maintained and the link resolves before
  merging (check last release date on PyPI).

## 2. Starting points for users' own work

- [x] **Script template.** Add `templates/engineering_script.py`: a skeleton
  with an inputs dict, calculation, results printout, plot, and CSV export,
  heavily commented, meant to be copied and adapted.
- [x] **`examples/` folder of worked problems.** One short, self-contained
  script per realistic problem, each going from question to answer. Candidates:
  pump sizing, beam selection, PID tuning, heat-exchanger estimate, motor
  sizing, shielding-thickness check. Move `radiology_demo.py` here (update the
  README and GUI references).
- [x] **"From calculation to tool" guide.** A doc (e.g. `docs/building-tools.md`)
  walking one calculation up the ladder: script -> command line (`argparse`)
  -> the existing tkinter GUI -> web app (Streamlit) -> installable package.
- [x] **Notebooks.** Add `notebooks/` with a few Jupyter (or marimo) notebooks
  that call the library. Add `jupyter` / `marimo` as an optional dependency
  group.

## 3. Make the library reusable outside this repo

- [x] **Rename the `library` package to `fpc`.** (Decided: `fpc`.) The name is generic
  and collides with other code. Candidate: `fpc` (first-principles-code).
  This breaks every existing import, so do it in one PR that updates all
  imports, tests, README, GUI, and demos.
- [x] Add a `[build-system]` section to `pyproject.toml` so the package can
  be installed with `uv add git+https://github.com/kovirlabs/first-principles-code`
  or `pip install -e .`.
- [x] Document "use this library in your own project" in the README.

## 4. Finish the SPEC roadmap items real tools depend on

Tracked in detail in [SPEC.md](SPEC.md) under "Python concepts to teach".

- [x] **pandas data handling.** Read a sensor log / property table from
  CSV and Excel, filter, group, export. Add `pandas` (and `openpyxl`).
- [x] **Root finding.** `scipy.optimize.brentq` / `fsolve`, e.g. solve
  Colebrook for friction factor or find a beam size that meets a deflection
  limit.
- [x] **Interpolation.** `scipy.interpolate` / `np.interp` on a property table
  (steam tables, material data).
- [x] **Optimization for design.** `scipy.optimize.minimize` with bounds and
  constraints, e.g. lightest beam that meets stress and deflection limits.
- [x] **NumPy vectorization lesson.** A side-by-side loop vs. vectorized
  example with timing, plus boolean masking.

## 5. Units consistency

- [x] **Decided: document the split** (`docs/units.md`): plain SI floats
  for the math, Pint at the boundaries. Pint is used in `Beam` and partly in `Thermo`;
  every other class takes plain floats. Either extend Pint support across the
  library or document clearly when to use each approach (plain floats for
  quick formulas, Pint for anything with mixed or error-prone units).

## 6. Tooling and professional habits

- [x] **Ruff** for linting and formatting: add to the dev group, configure in
  `pyproject.toml`, run in CI.
- [x] **Type checking** (mypy or pyright) on `fpc/`, starting non-strict.
- [x] **API docs site** generated from the docstrings (mkdocs-material +
  mkdocstrings), published with GitHub Pages.
- [x] **pre-commit** hooks so ruff and tests run before each commit.

## 7. Reference data

- [x] (Placed in `fpc/data/` so the tables ship with the installed package.)
  Add a `data/` folder with CSV/JSON tables (material properties, standard
  steel sections, fluid properties) and load them through `Utility` or pandas
  instead of hard-coding constants. Cite the source of every table.

## 8. Contributor experience

- [x] "Add a new domain class" checklist in `CONTRIBUTOR.md` (module, class,
  `__init__` export, GUI preload, tests, README row).
- [x] GitHub issue templates: bug report, new domain request, new example.

## 9. AI integration: one registry, many front ends

Goal: let both local LLMs (Ollama, LM Studio) and coding agents (Claude Code,
Cursor, Aider) use the library correctly. Small local models are poor at
arithmetic and at writing numerical code, so for them the library becomes a
*calculator they call*. Capable coding agents are better served by reading and
composing the code directly, so for them we document the API compactly.

- [x] **Calculation registry (`fpc/registry.py`).** Walk every domain class
  with `inspect`, parse each docstring (`:param name: text [unit]`), and
  build a JSON-Schema description of every method. This one module is the
  source of truth for the MCP server, the CLI search, `llms.txt`, and future
  GUI autocomplete / web forms.
- [x] **MCP server (`fpc/mcp_server.py`, command `fpc-mcp`).** A small,
  fixed tool surface so small models are not swamped by 130+ tools:
  `list_domains`, `search_calculations`, `describe_calculation`,
  `calculate`, `list_reference_tables`. Never expose arbitrary code
  execution. Ships as the `mcp` extra: `pip install "first-principles-code[mcp]"`.
- [ ] **MCP: optional direct tools.** A `--domains fluids,thermo` flag that
  also exposes those methods as individual tools with their own schemas
  (better for capable models; the SDK builds schemas from signatures, so
  this needs a registry-schema -> tool adapter).
- [ ] **Try the MCP server with real local models** (LM Studio + a Qwen /
  Llama / Mistral tool-calling model, Open WebUI + Ollama) and tune the tool
  descriptions and `INSTRUCTIONS` from what goes wrong.
- [x] **`fpc search` / `fpc describe` / `fpc run` CLI subcommands**, driven
  by the registry, so every method is reachable from the terminal.
- [x] **`llms.txt` + `AGENTS.md`** for coding agents: a generated, compact
  index of every method with parameters and units, plus the house rules
  (keyword-only args, SI floats, where reference data lives).
- [x] **`docs/ai.md`**: setup for LM Studio (`mcp.json`), Ollama front ends
  (Open WebUI via `mcpo`, `ollmcp`, Continue, Cline), and Claude Desktop/Code.
- [x] **Type hints on every public method** (`float`, `int`, `str`, arrays).
  The registry reads them to build accurate schemas; also unlocks the
  "Tighten mypy" follow-up. (0 of ~137 methods are annotated today.)
- [x] **A `[unit]` tag on every numeric `:param` and `:returns:` line**
  (use `[-]` for dimensionless). About 100 parameter lines lack one; the
  registry reports them so a test can enforce this once they are fixed.
- [ ] **Consistent result objects.** Decide whether methods return plain
  floats/dicts (today) or a small `Result(value, unit, inputs)` type.
  **(decision needed)**

## 10. Distribution and reach

- [x] **PyPI release.** Package metadata (authors, URLs, classifiers,
  keywords), `scipy-stubs` moved out of the runtime dependencies, a
  release workflow using PyPI Trusted Publishing, and `docs/releasing.md`.
- [ ] **First upload.** Maintainer steps in `docs/releasing.md`: PyPI and
  TestPyPI accounts, pending publishers, GitHub environments, then a release.
- [ ] **`uvx` one-liners** once on PyPI: `uvx --from first-principles-code fpc ...`
  and `uvx --from "first-principles-code[mcp]" fpc-mcp`.
- [x] **Lower the Python floor** to 3.11 (decided: support every CPython
  version not past end-of-life, currently 3.11-3.15), with a CI matrix
  across all of them and a ratchet: `scripts/python_support.py`
  (`check` / `status` / `set`) plus a monthly workflow that opens an issue
  when a version is released or retired. See `docs/python-versions.md`.
- [ ] **Streamlit app generated from the registry**: one form per method,
  for free, using the existing `apps` dependency group.

## 11. Trust and day-to-day usefulness

- [ ] **Calc reports.** Export a calculation to Markdown/PDF with the
  equation, inputs with units, result, and source citation, the way a
  checked hand calc is filed for review (compare `handcalcs`).
- [ ] **Worked-example tests with citations.** Tests that reproduce
  published textbook examples (e.g. "Shigley Ex. 4-7") so users can trust
  the numbers. Pairs with the data-verification follow-ups below.
- [ ] **Domain gaps engineers hit daily:** machine elements (bolts, shafts,
  springs, bearings, welds), fatigue (Goodman/Soderberg), column buckling,
  psychrometrics/HVAC.
- [ ] **Uncertainty on any calculation:** a Monte Carlo helper that wraps a
  registry method and samples its inputs.

---

## Follow-ups

Items found while building sections 0-8.

- [ ] **Enable GitHub Pages:** Settings -> Pages -> Source: "GitHub Actions",
  so `.github/workflows/docs.yml` can publish the docs site.
- [ ] **Verify `fpc/data/materials.csv` against MatWeb/ASM data sheets.** The
  values are typical published figures but were entered from reference
  knowledge, not copied from a fetched source.
- [ ] **Verify `fpc/data/w_shapes.csv` against the AISC Shapes Database v16
  spreadsheet.** A test confirms every row is physically self-consistent
  (Sx = Ix/(d/2), weight = 3.4 x A), which catches typos but not a
  consistently wrong row. Extend the table while doing this.
- [ ] **Plan the move off Material for MkDocs**, which reaches end of life on
  2027-05-05. Its successor, Zensical, reads the existing `mkdocs.yml`.
- [ ] **Tighten mypy** module by module as type hints are added
  (`disallow_untyped_defs` per module).
- [ ] Consider an InSpice row in place of PySpice in `PACKAGES.md` once
  InSpice has a longer release history.

## Done

_Move items here with their PR number when merged._

- [x] Radiology / medical-imaging classes: `Radiation`, `Radiography`, `CT`,
  `MRI`, `Ultrasound`, `Dicom` (#4)
