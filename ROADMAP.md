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

_Last reviewed: 2026-11-06_

---

## 0. Housekeeping (quick, low risk)

- [ ] **Update `CLAUDE.md`.** It still says `fpc/` is empty, `main.py` is
  hello-world, and there are no tests or README. Rewrite "Current state" to
  match reality (14 domain classes + 6 radiology classes, 109 tests, CI, GUI).
- [ ] **Stop tracking `.idea/`.** `git rm -r --cached .idea` and add `.idea/`
  to `.gitignore` (PyCharm settings are per-user).
- [ ] **Fix stale README numbers.** "40+ tests" -> current count (109), or
  drop the number so it can't go stale.

## 1. Package discovery: `PACKAGES.md`

- [ ] Create `PACKAGES.md`, a curated list of Python packages **organized by
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
- [ ] End with links to existing curated lists:
  [awesome-scientific-python](https://github.com/rossant/awesome-scientific-python),
  [awesome-scientific-computing](https://github.com/nschloe/awesome-scientific-computing),
  [awesome-python: Science](https://github.com/vinta/awesome-python#science),
  [awesome-python-chemistry](https://github.com/lmmentel/awesome-python-chemistry).
- [ ] Shrink the README package table to the top ~10 and link to `PACKAGES.md`.
- [ ] Verify every package is maintained and the link resolves before
  merging (check last release date on PyPI).

## 2. Starting points for users' own work

- [ ] **Script template.** Add `templates/engineering_script.py`: a skeleton
  with an inputs dict, calculation, results printout, plot, and CSV export,
  heavily commented, meant to be copied and adapted.
- [ ] **`examples/` folder of worked problems.** One short, self-contained
  script per realistic problem, each going from question to answer. Candidates:
  pump sizing, beam selection, PID tuning, heat-exchanger estimate, motor
  sizing, shielding-thickness check. Move `radiology_demo.py` here (update the
  README and GUI references).
- [ ] **"From calculation to tool" guide.** A doc (e.g. `docs/building-tools.md`)
  walking one calculation up the ladder: script -> command line (`argparse`)
  -> the existing tkinter GUI -> web app (Streamlit) -> installable package.
- [ ] **Notebooks.** Add `notebooks/` with a few Jupyter (or marimo) notebooks
  that call the library. Add `jupyter` / `marimo` as an optional dependency
  group.

## 3. Make the library reusable outside this repo

- [ ] **(decision needed) Rename the `fpc` package.** The name is generic
  and collides with other code. Candidate: `fpc` (first-principles-code).
  This breaks every existing import, so do it in one PR that updates all
  imports, tests, README, GUI, and demos.
- [ ] Add a `[build-system]` section to `pyproject.toml` so the package can
  be installed with `uv add git+https://github.com/kovirlabs/first-principles-code`
  or `pip install -e .`.
- [ ] Document "use this library in your own project" in the README.

## 4. Finish the SPEC roadmap items real tools depend on

Tracked in detail in [SPEC.md](SPEC.md) under "Python concepts to teach".

- [ ] **pandas data handling.** Read a sensor log / property table from
  CSV and Excel, filter, group, export. Add `pandas` (and `openpyxl`).
- [ ] **Root finding.** `scipy.optimize.brentq` / `fsolve`, e.g. solve
  Colebrook for friction factor or find a beam size that meets a deflection
  limit.
- [ ] **Interpolation.** `scipy.interpolate` / `np.interp` on a property table
  (steam tables, material data).
- [ ] **Optimization for design.** `scipy.optimize.minimize` with bounds and
  constraints, e.g. lightest beam that meets stress and deflection limits.
- [ ] **NumPy vectorization lesson.** A side-by-side loop vs. vectorized
  example with timing, plus boolean masking.

## 5. Units consistency

- [ ] **(decision needed)** Pint is used in `Beam` and partly in `Thermo`;
  every other class takes plain floats. Either extend Pint support across the
  library or document clearly when to use each approach (plain floats for
  quick formulas, Pint for anything with mixed or error-prone units).

## 6. Tooling and professional habits

- [ ] **Ruff** for linting and formatting: add to the dev group, configure in
  `pyproject.toml`, run in CI.
- [ ] **Type checking** (mypy or pyright) on `fpc/`, starting non-strict.
- [ ] **API docs site** generated from the docstrings (mkdocs-material +
  mkdocstrings), published with GitHub Pages.
- [ ] **pre-commit** hooks so ruff and tests run before each commit.

## 7. Reference data

- [ ] Add a `data/` folder with CSV/JSON tables (material properties, standard
  steel sections, fluid properties) and load them through `Utility` or pandas
  instead of hard-coding constants. Cite the source of every table.

## 8. Contributor experience

- [ ] "Add a new domain class" checklist in `CONTRIBUTOR.md` (module, class,
  `__init__` export, GUI preload, tests, README row).
- [ ] GitHub issue templates: bug report, new domain request, new example.

---

## Done

_Move items here with their PR number when merged._

- [x] Radiology / medical-imaging classes: `Radiation`, `Radiography`, `CT`,
  `MRI`, `Ultrasound`, `Dicom` (#4)
