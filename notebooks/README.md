<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Notebooks

Interactive companions to the library. Each notebook mixes explanation, code,
and plots, so it doubles as a lab handout.

```bash
uv sync --group notebooks     # one-time: installs Jupyter
uv run jupyter lab            # opens in your browser
```

| Notebook | Covers |
| --- | --- |
| `01_getting_started.ipynb` | Calling library methods, `help()`, lists of dicts, plotting a sweep, a SciPy drag simulation |
| `02_pipe_flow_and_data.ipynb` | pandas tables, interpolation (linear vs cubic), root finding, a Moody chart |
| `03_beam_design.ipynb` | Pint units, sizing by root finding, constrained optimization, catalogue selection |

The notebooks are stored **without outputs** so diffs stay readable; run them
to see results. They are generated from `make_notebooks.py`, which is easier
to review than notebook JSON. `tests/test_notebooks.py` executes every
notebook in CI.

Prefer plain-Python notebooks? [marimo](https://marimo.io/) stores notebooks
as `.py` files and reruns dependent cells automatically: `uvx marimo edit`.
