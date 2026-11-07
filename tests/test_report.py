# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for calc reports (fpc.report) and the report/uncertainty commands."""

import datetime
import json

import pytest

from fpc.cli import main
from fpc.report import calc_report
from fpc.uncertainty import Normal, monte_carlo

WALL = {"conductivity": 0.72, "area": 12, "delta_temperature": 25, "thickness": 0.2}


def test_sheet_has_method_inputs_with_units_result_and_review():
    text = calc_report(
        "Thermo.conduction_heat_rate",
        WALL,
        title="North wall heat loss",
        checked_by="A. Reviewer",
        date=datetime.date(2026, 11, 7),
    )
    assert text.startswith("# North wall heat loss\n")
    assert "| Checked by | A. Reviewer |" in text
    assert "| Date | 2026-11-07 |" in text
    assert "Q_dot = k * A * dT / L" in text  # the equation, from the docstring
    assert "| `conductivity` | 0.72 | W/(m*K) |" in text
    assert "**Result: 1080**" in text
    assert "- [ ] Method and assumptions suit this case" in text


def test_defaults_are_listed_and_dict_results_become_a_table():
    text = calc_report(
        "Fluids.pipe_flow",
        {
            "flow": 0.012,
            "diameter": 0.1,
            "length": 120,
            "roughness": 4.5e-5,
            "density": 998,
            "viscosity": 1e-3,
        },
    )
    assert "| pressure_drop | 26690.8 |" in text
    projectile = calc_report("Dynamics.projectile_range", {"speed": 20, "angle_deg": 45})
    assert "| `gravity` | 9.80665 (default) |" in projectile  # shown, not hidden


def test_uncertainty_section():
    inputs = {**WALL, "conductivity": Normal(mean=0.72, std=0.05)}
    mc = monte_carlo("Thermo.conduction_heat_rate", inputs, seed=0)
    text = calc_report("Thermo.conduction_heat_rate", WALL, uncertainty=mc)
    assert "## Uncertainty" in text
    assert "- `conductivity`: 100%" in text


def test_bad_inputs_raise_before_writing():
    with pytest.raises(ValueError, match="missing"):
        calc_report("Thermo.conduction_heat_rate", {"area": 1})


def test_cli_report_and_uncertainty(tmp_path, capsys):
    out = tmp_path / "wall.md"
    main(
        [
            "report",
            "Thermo.conduction_heat_rate",
            "conductivity=0.72",
            "area=12",
            "delta_temperature=25",
            "thickness=0.2",
            "--out",
            str(out),
        ]
    )
    assert "**Result: 1080**" in out.read_text()
    capsys.readouterr()

    main(
        [
            "uncertainty",
            "Thermo.conduction_heat_rate",
            "conductivity=normal:0.72,0.05",
            "area=12",
            "delta_temperature=25",
            "thickness=0.2",
            "--seed",
            "1",
            "--samples",
            "2000",
        ]
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["mean"] == pytest.approx(1080, rel=0.01)
    assert summary["samples"] == 2000


def test_cli_uncertainty_tuple_output_index(capsys):
    main(
        [
            "uncertainty",
            "Modal.natural_frequency",
            "stiffness=normal:4000,100",
            "mass=2.5",
            "--output",
            "1",
            "--seed",
            "0",
            "--samples",
            "500",
        ]
    )
    assert json.loads(capsys.readouterr().out)["mean"] == pytest.approx(6.366, rel=0.01)
