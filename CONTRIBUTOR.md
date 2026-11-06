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
- Add a new domain class (see the planned list in [`SPEC.md`](SPEC.md)).
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
uv sync                 # create the environment from pyproject.toml + uv.lock
uv run main.py          # confirm the demo runs
uv run pytest           # confirm the test suite is green
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
  and `fpc/beam.py`).
- **Validate inputs** that can realistically be wrong (negative area, wrong
  units) and `raise ValueError` with a clear message — see `Beam.__post_init__`.
- **Keep methods stateless** where possible, so each one stands alone as a
  worked example.

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

Favor well-maintained, widely-used scientific packages (see the package table
in the README), and add a one-line note in the README table if it is something
a learner would benefit from knowing about.

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
