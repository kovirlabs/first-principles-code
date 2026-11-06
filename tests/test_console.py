# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the GUI's evaluation engine (gui.Session).

The console's logic is deliberately separated from its tkinter widgets, so we
can test "run a line of code and record the result" with no display attached.
"""

from pathlib import Path

from gui import Session


def test_expression_is_evaluated_and_recorded():
    """An expression returns a value, labels it, and stores it in records."""
    session = Session()
    result = session.run(source="dyn.projectile_range(speed=20, angle_deg=45)")
    assert result["error"] is None
    assert result["label"] == "out1"
    assert float(result["value"]) > 0
    assert len(session.records) == 1


def test_assignment_persists_and_is_reusable():
    """A statement (assignment) runs, then its variable can be used later."""
    session = Session()
    session.run(source="x = thermo.carnot_efficiency(hot_temperature=800, cold_temperature=300)")
    result = session.run(source="x")
    assert result["value"] == "0.625"
    # The assignment itself produced no value, so only 'x' was recorded.
    assert len(session.records) == 1


def test_print_output_is_captured_not_recorded():
    """print() text is captured for display but is not a workspace result."""
    session = Session()
    result = session.run(source="print('hello')")
    assert result["output"] == "hello\n"
    assert len(session.records) == 0


def test_runtime_error_is_reported_without_crashing():
    """A bad command surfaces an error string instead of raising."""
    session = Session()
    result = session.run(source="1 / 0")
    assert "ZeroDivisionError" in result["error"]
    assert len(session.records) == 0


def test_export_csv_and_json(tmp_path):
    """Recorded results export to both formats via fpc.Utility."""
    session = Session()
    session.run(source="dyn.kinetic_energy(mass=2, velocity=3)")

    csv_path = session.export_csv(file_path=str(tmp_path / "out.csv"))
    json_path = session.export_json(file_path=str(tmp_path / "out.json"))

    assert "label,command,result" in Path(csv_path).read_text(encoding="utf-8")
    assert "out1" in Path(json_path).read_text(encoding="utf-8")
