# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Smoke tests: every example script and the template run without errors.

Examples are documentation, and documentation that crashes teaches the wrong
lesson. Each script runs in a fresh Python process, exactly as a user would
run it, with a non-interactive matplotlib backend so no windows open.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((ROOT / "examples").glob("*.py")) + [
    ROOT / "templates" / "engineering_script.py",
]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_script_runs(script):
    environment = {**os.environ, "MPLBACKEND": "Agg"}
    completed = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
