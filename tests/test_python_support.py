# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for scripts/python_support.py, the supported-Python-version ratchet.

The script edits real files, so the round-trip test points it at *copies* in
pytest's ``tmp_path`` using ``monkeypatch`` (which swaps module attributes for
the duration of one test and puts them back afterwards).
"""

import importlib.util
import io
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "python_support", ROOT / "scripts" / "python_support.py"
)
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """Copy the files the script edits into tmp_path and point the script there."""
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    for name in ("tests.yml", "docs.yml", "release.yml"):
        shutil.copy(ROOT / ".github" / "workflows" / name, workflows / name)
    shutil.copy(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    monkeypatch.setattr(ps, "PYPROJECT", tmp_path / "pyproject.toml")
    monkeypatch.setattr(ps, "TESTS_WORKFLOW", workflows / "tests.yml")
    monkeypatch.setattr(
        ps, "SINGLE_VERSION_WORKFLOWS", [workflows / "docs.yml", workflows / "release.yml"]
    )
    return tmp_path


def test_repository_declares_versions_consistently():
    # The same check CI runs: pyproject.toml and the workflows agree.
    assert ps.main(["check"]) == 0


def test_versions_compare_as_numbers_not_text():
    assert ps.parse("3.9") < ps.parse("3.11")  # as strings, "3.9" > "3.11"
    assert ps.span((3, 11), (3, 13)) == [(3, 11), (3, 12), (3, 13)]


def test_set_rewrites_every_file_consistently(scratch_repo):
    ps.main(["set", "--oldest", "3.12", "--newest", "3.16"])
    found = ps.current()
    assert found["requires-python (oldest)"] == [(3, 12)]
    assert found["ruff target-version (oldest)"] == [(3, 12)]
    assert found["tests.yml matrix"] == ps.span((3, 12), (3, 16))
    assert found["release.yml (newest)"] == [(3, 16), (3, 16)]
    # The 3.11-only lockfile constraints are now flagged for deletion.
    assert ps.stale_constraints((3, 12))
    assert ps.main(["check"]) == 1


def fake_eol_api(monkeypatch, cycles):
    """Make urlopen return our own JSON instead of calling endoflife.date."""
    monkeypatch.setattr(
        ps.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(cycles).encode())
    )


CYCLES = [
    {"cycle": f"3.{m}", "releaseDate": f"{2011 + m}-10-01", "eol": f"{2016 + m}-10-31"}
    for m in range(9, 18)
]


def test_status_quiet_when_in_step(scratch_repo, monkeypatch):
    fake_eol_api(monkeypatch, CYCLES)
    ps.main(["set", "--oldest", "3.11", "--newest", "3.15"])
    assert ps.main(["status", "--today", "2026-11-07"]) == 0


def test_status_asks_to_ratchet_after_eol(scratch_repo, monkeypatch, capsys):
    fake_eol_api(monkeypatch, CYCLES)
    ps.main(["set", "--oldest", "3.11", "--newest", "3.15"])
    assert ps.main(["status", "--today", "2027-11-15"]) == 1
    output = capsys.readouterr().out
    assert "--oldest 3.12 --newest 3.16" in output
    assert "end-of-life" in output
