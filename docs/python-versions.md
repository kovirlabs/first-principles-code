<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Supported Python versions

**Policy: `fpc` supports every CPython version that has not reached
end-of-life.** As of November 2026 that is **Python 3.11 to 3.15**.

## Why this policy

- Many engineers work on company machines where Python is installed by IT
  and lags a few years behind. Supporting every version that still gets
  security fixes from python.org lets them install `fpc` without a fight.
- Supporting versions past end-of-life would mean the scientific stack
  (NumPy, SciPy, pandas) stops publishing for them anyway, and we would
  test against an unpatched interpreter.
- It is a simple, predictable rule. CPython releases one new version every
  October and retires the oldest after five years
  ([PEP 602](https://peps.python.org/pep-0602/),
  [schedule](https://devguide.python.org/versions/)), so the window slides
  forward one version a year. 3.11 reaches end-of-life in October 2027.

## Where the range is written down

| File | Setting | Holds |
|---|---|---|
| `pyproject.toml` | `requires-python = ">=3.11"` | oldest (what pip enforces) |
| `pyproject.toml` | `Programming Language :: Python :: 3.x` classifiers | every version (shown on PyPI) |
| `pyproject.toml` | `[tool.ruff] target-version`, `[tool.mypy] python_version` | oldest, so newer syntax and stdlib APIs are flagged |
| `.github/workflows/tests.yml` | `python-version: [...]` matrix | every version: the test suite runs on each |
| `.github/workflows/docs.yml`, `release.yml` | `uv python install` / `UV_PYTHON` | newest |
| `pyproject.toml` | `[tool.uv] constraint-dependencies` | lockfile splits for the oldest version (see below) |

Nobody edits these by hand. `scripts/python_support.py` reads and writes
all of them, and CI runs `scripts/python_support.py check` so they can never
drift apart.

## The ratchet

A monthly GitHub Action (`.github/workflows/python-versions.yml`) runs:

```bash
uv run scripts/python_support.py status
```

It compares our range with CPython's published release and end-of-life
dates (from [endoflife.date](https://endoflife.date/python)). When a new
Python is out or the oldest one has retired, it opens an issue titled
**"Update supported Python versions"** containing the exact commands. To act
on it:

1. **Rewrite the range everywhere:**

    ```bash
    uv run scripts/python_support.py set --oldest 3.12 --newest 3.16
    ```

2. **Delete constraints the script reports as stale.** Some dependencies
   drop old Pythons before CPython does (NumPy, SciPy and Pint already need
   3.12+). Lines in `[tool.uv] constraint-dependencies` like
   `"numpy>=2.5; python_version >= '3.12'"` make `uv.lock` use newer
   releases everywhere except the oldest Python. Once the floor reaches the
   marker's version they are always true; `check` lists them for deletion.
3. **Re-lock and test:** `uv lock && uv run pytest`. CI then runs the full
   suite on every version in the new range.
4. **Remove code that existed only for the old version.** Search for its
   number (`3.11`, `py311`). For example, `fpc/hints.py` writes
   `FloatArray: TypeAlias = ...` instead of the 3.12+ `type FloatArray = ...`
   statement only because 3.11 is supported.
5. **Note it in `CHANGELOG.md`.** Dropping a Python version is a breaking
   change for anyone still on it, so bump the minor version (`uv version
   --bump minor`). People on the old Python keep getting the last release
   that supported it, because pip reads `requires-python`.

### Adding a brand-new Python

When a new version comes out, some dependencies may not have published
wheels for it yet, and its CI job will fail while they catch up. That is
useful information, not a reason to wait: add it with `set --newest`, and if
a dependency is not ready, mark the job `continue-on-error` in `tests.yml`
for a few weeks and add a ROADMAP follow-up to remove that.

## Writing code that works on the oldest version

ruff (`target-version`) and mypy (`python_version`) are both set to the
oldest supported Python, so `uv run ruff check .` and `uv run mypy` flag most
too-new features before CI does. Things to avoid until 3.11 retires:

- the `type X = ...` statement and `def f[T](...)` generics (3.12);
- `typing.override`, `itertools.batched`, `Path.walk` (3.12);
- relying on lazily evaluated annotations (3.14): a type hint that names a
  class defined *later* in the file needs quotes, e.g. `-> "Beam"`.
