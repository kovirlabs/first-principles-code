<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Releasing to PyPI

[PyPI](https://pypi.org) (the Python Package Index) is where `pip install` and
`uv add` download packages from. Once `first-principles-code` is there,
anyone can run:

```bash
pip install first-principles-code            # the library + `fpc` command
pip install "first-principles-code[mcp]"     # + the `fpc-mcp` AI server
uvx --from first-principles-code fpc --help  # run without installing
```

The distribution name (`first-principles-code`) is what you install; the
import name (`fpc`) is what you `import`. They do not have to match.

Releases are automated by `.github/workflows/release.yml` using **Trusted
Publishing**: PyPI is told to trust that one workflow in this one repository,
so there is no API token to create, store, leak or rotate.

## One-time setup

1. **Create accounts** on [pypi.org](https://pypi.org/account/register/) and
   [test.pypi.org](https://test.pypi.org/account/register/) (separate
   sites, separate accounts) and turn on two-factor authentication; PyPI
   requires it.
2. **Register a "pending publisher"** on each site. This reserves the name
   and trusts the workflow before the first upload.
   On PyPI: **Your account → Publishing → Add a new pending publisher →
   GitHub**, then fill in:

    | Field | Value |
    |---|---|
    | PyPI project name | `first-principles-code` |
    | Owner | `kovirlabs` |
    | Repository name | `first-principles-code` |
    | Workflow name | `release.yml` |
    | Environment name | `pypi` |

    Repeat on TestPyPI with environment name `testpypi`.
3. **Create the two GitHub environments** the workflow names:
   repository **Settings → Environments → New environment**: `pypi` and
   `testpypi`. On `pypi`, add yourself under **Required reviewers** so
   every real upload waits for your click.

## Every release

1. **Bump the version** and update the changelog:

    ```bash
    uv version --bump minor     # 0.1.0 -> 0.2.0 (or: patch, major)
    ```

    Move the `[Unreleased]` notes in `CHANGELOG.md` under the new version.
    PyPI never lets you re-upload a version number, so every upload needs a
    new one.
2. **Check locally**:

    ```bash
    uv run pytest
    uv build                        # writes dist/*.tar.gz and dist/*.whl
    uvx twine check --strict dist/* # will the README render on PyPI?
    ```

3. **Dry run on TestPyPI** (recommended the first time): merge to `main`,
   then **Actions → release → Run workflow**. Install from it in a scratch
   folder to prove the package works. `--extra-index-url` lets the
   dependencies (numpy, ...) still come from real PyPI:

    ```bash
    uv venv /tmp/fpc-try && uv pip install -p /tmp/fpc-try \
      --index-url https://test.pypi.org/simple/ \
      --extra-index-url https://pypi.org/simple/ \
      --index-strategy unsafe-best-match first-principles-code
    /tmp/fpc-try/bin/fpc search reynolds
    ```

4. **Publish**: on GitHub, **Releases → Draft a new release**, create the
   tag `v0.1.0` (matching `pyproject.toml`; the workflow refuses a mismatch),
   paste the changelog notes, and **Publish release**. The workflow tests,
   builds, and (after your approval on the `pypi` environment) uploads.
5. **Verify** at <https://pypi.org/project/first-principles-code/> and with
   `uvx --from first-principles-code fpc --help`.

## Uploading by hand (fallback)

If you ever need to publish without GitHub Actions, create an API token at
**PyPI → Account settings → API tokens** (scope it to this project) and run:

```bash
uv build
uv publish --token pypi-XXXXXXXX    # or set UV_PUBLISH_TOKEN
```

## What gets shipped

- **Wheel** (`.whl`, what `pip` installs): the `fpc/` package, including the
  reference tables in `fpc/data/` and `py.typed` (which tells type checkers
  the package has type hints).
- **sdist** (`.tar.gz`, the source download): `fpc/`, `README.md`,
  `LICENSE`, `CHANGELOG.md`, `llms.txt`.

The examples, notebooks, GUI and templates stay in the GitHub repository:
they are meant to be cloned and edited, not installed.
