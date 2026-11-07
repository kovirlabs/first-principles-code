# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.utility.Utility.

Demonstrates pytest's ``tmp_path`` fixture: pytest hands each test a unique,
automatically-cleaned temporary directory, so file I/O can be tested without
leaving junk behind or touching the real project files.
"""

from fpc.utility import Utility

utility = Utility()


def test_json_round_trip(tmp_path):
    """Writing a dict and reading it back should give an identical dict."""
    data = {"name": "steel", "modulus_gpa": 200, "ductile": True}
    path = tmp_path / "material.json"

    utility.dict_to_json(data=data, file_path=str(path))
    loaded = utility.json_to_dict(file_path=str(path))

    assert loaded == data


def test_export_csv_writes_header_and_rows(tmp_path):
    """The CSV should contain the header line plus one line per data row."""
    rows = [("steel", 200), ("aluminum", 69)]
    path = tmp_path / "results.csv"

    utility.export_csv(rows=rows, file_path=str(path), header=["material", "E_GPa"])

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "material,E_GPa"
    assert len(lines) == 3  # 1 header + 2 data rows
    assert "steel,200" in lines[1]
