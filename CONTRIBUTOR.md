<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Contributing to First Principles Code

Thanks for your interest in contributing! This project is a **teaching
template**: its goal is to help engineers solve real problems in Python and to
show that the open-source scientific stack can replace tools like MATLAB and
Maplesoft. That goal shapes everything below — here, *clear, well-explained
code is the product*, not a side effect.

## Ways to contribute

- Add a new method to an existing engineering class.
- Add a new domain class (follow the checklist below).
- Add a worked example to `examples/` or a notebook to `notebooks/`.
- Pick up an item from [`ROADMAP.md`](ROADMAP.md).
- Implement an item from the "Python concepts to teach" roadmap in `SPEC.md`.
- Improve docstrings, comments, examples, or the README.
- Add or strengthen tests.
- Fix a bug or a numerical inaccuracy (please include a test that proves it).

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) (see the README for an
install and usage tutorial).

```bash
git clone <your-fork-url>
cd first-principles-code
uv sync --all-groups    # create the environment (runtime + dev, notebooks, docs, apps)
uv run main.py          # confirm the demo runs
uv run pytest           # confirm the test suite is green
uv run pre-commit install   # run ruff + pytest automatically on every commit
```

Before opening a pull request, the same checks CI runs:

```bash
uv run ruff check .          # lint
uv run ruff format .         # auto-format
uv run mypy                  # type-check fpc/
uv run pytest                # tests, examples, notebooks
uv run --group docs mkdocs build --strict   # docs site builds cleanly
```

## Coding conventions

Because the code teaches, these conventions are requirements, not suggestions:

- **Keyword-only arguments.** Methods use `def method(self, *, ...)` so every
  call reads like a sentence (`acceleration=9.81`, not a bare `9.81`).
- **Docstrings on every class and method**, documenting each parameter *and its
  units* and the return value. They double as the project's reference docs.
- **Comment the _why_.** Explain non-obvious math and the reasoning behind a
  step, not just what the line does.
- **One domain per file, one class per file**, matching the existing layout.
- **State the units** for every physical quantity. For anything where unit
  mistakes are likely, prefer modelling it with Pint (see `fpc/units.py`
  and `fpc/beam.py`). Methods taking plain numbers use SI units unless the
  parameter name says otherwise (`angle_deg`, `temperature_c`); see
  [docs/units.md](docs/units.md).
- **Reference data goes in `fpc/data/`**, not hard-coded constants, with its
  source cited in `fpc/data/README.md`.
- **Validate inputs** that can realistically be wrong (negative area, wrong
  units) and `raise ValueError` with a clear message — see `Beam.__post_init__`.
- **Keep methods stateless** where possible, so each one stands alone as a
  worked example.

## Checklist: adding a new domain class

Copy this into your pull request description and tick each box.

- [ ] **Module:** `fpc/<domain>.py` with an SPDX header, a module docstring
      explaining the domain, and one class (`class <Domain>:`).
- [ ] **Methods:** keyword-only (`def method(self, *, ...)`), each with a
      docstring giving the formula, every parameter's units, and the return
      value's units. Comment the *why* of non-obvious steps.
- [ ] **Validation:** `raise ValueError` with a clear message for inputs
      that can realistically be wrong.
- [ ] **Export:** import it in `fpc/__init__.py` and add it to `__all__`.
- [ ] **GUI preload:** add a ready-made instance in `gui.py`'s
      `Session.namespace`.
- [ ] **Tests:** `tests/test_<domain>.py` checking textbook answers with
      `pytest.approx`, plus at least one invalid-input test.
- [ ] **Docs:** `docs/api/<domain>.md` containing `::: fpc.<domain>` and an
      entry under "API reference" in `mkdocs.yml`.
- [ ] **README:** a row or sentence in the relevant section and the
      project-layout tree.
- [ ] **Example (optional, encouraged):** a script in `examples/` answering
      one realistic question with the new class, plus a row in
      `examples/README.md`.
- [ ] **Checks pass:** ruff, mypy, pytest, and the strict docs build.

## Tests

Every new method or class needs a test. The library methods are pure functions
with known textbook answers, which makes them easy to check.

- Put tests in `tests/`, named `test_<topic>.py`.
- Compare floats with `pytest.approx`, not `==`.
- Use `@pytest.mark.parametrize` for tables of known inputs/outputs, and the
  `tmp_path` fixture for any file I/O.
- For simulations, prefer a self-verifying test (e.g. simulate with known
  parameters, then fit/measure and assert you recover them — see
  `tests/test_modal_controls.py`).

```bash
uv run pytest                       # everything
uv run pytest tests/test_xyz.py     # one file
uv run pytest -k keyword            # tests matching a name
```

Please make sure the whole suite passes before opening a pull request.

## Adding a dependency

Use uv so `pyproject.toml` and `uv.lock` stay in sync:

```bash
uv add <package>            # runtime dependency
uv add --dev <package>      # development-only dependency (e.g. a tool)
```

Favor well-maintained, widely-used scientific packages (see
[PACKAGES.md](PACKAGES.md)). If it is something a learner would benefit from
knowing about, add a row to the right section of PACKAGES.md. Optional
tooling belongs in a dependency group (`uv add --group notebooks ...`), not
the runtime dependencies.

## Submitting changes

1. Fork the repo and create a branch off `main`.
2. Make your change with tests and docstrings.
3. Run `uv run pytest` and confirm it is green.
4. Open a pull request describing **what** changed and **why**, and call out any
   formulas or references you used so reviewers can verify the engineering.

## License

This project is licensed under the [Apache License 2.0](LICENSE). By submitting
a contribution, you agree that it will be licensed under the same terms (per
Section 5 of the license).
