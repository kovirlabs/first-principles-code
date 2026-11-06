# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Execute every notebook top to bottom; any cell error fails the test.

Needs the optional notebook tools (``uv sync --group notebooks``; CI installs
all groups). Without them this module is skipped rather than failing.
"""

from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")

NOTEBOOKS = sorted((Path(__file__).resolve().parent.parent / "notebooks").glob("*.ipynb"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_executes(path):
    notebook = nbformat.read(path, as_version=4)
    # Run with the notebooks folder as the working directory, like Jupyter does.
    nbclient.NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    ).execute()
