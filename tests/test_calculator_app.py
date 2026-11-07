# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the registry-driven Streamlit app (apps/calculator.py).

Streamlit's ``AppTest`` runs the script without a browser and lets a test set
widgets and read what was drawn. Streamlit is an optional dependency group.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "apps" / "calculator.py")


def open_app(key: str) -> AppTest:
    """Start the app and choose one calculation."""
    domain, name = key.split(".")
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.sidebar.selectbox[0].set_value(domain).run()
    app.sidebar.selectbox[1].set_value(key).run()
    return app


def test_every_calculation_form_draws_without_error():
    app = AppTest.from_file(APP, default_timeout=30).run()
    domains = app.sidebar.selectbox[0].options
    assert "Fluids" in domains
    for domain in domains:
        app.sidebar.selectbox[0].set_value(domain).run()
        for key in app.sidebar.selectbox[1].options:
            app.sidebar.selectbox[1].set_value(key).run()
            assert not app.exception, key


def test_form_waits_for_required_inputs_then_calculates():
    app = open_app("Thermo.conduction_heat_rate")
    assert "Enter" in app.info[0].value
    for name, value in {
        "conductivity": 0.72,
        "area": 12,
        "delta_temperature": 25,
        "thickness": 0.2,
    }.items():
        app.number_input(key=f"in:Thermo.conduction_heat_rate:{name}").set_value(value)
    app.run()
    assert not app.exception
    assert app.metric[0].value == "1080"
    assert "## Inputs" in app.markdown[-1].value  # the calc sheet tab


def test_uncertainty_tab_runs_monte_carlo():
    app = open_app("Thermo.conduction_heat_rate")
    for name, value in {
        "conductivity": 0.72,
        "area": 12,
        "delta_temperature": 25,
        "thickness": 0.2,
    }.items():
        app.number_input(key=f"in:Thermo.conduction_heat_rate:{name}").set_value(value)
    app.run()
    app.slider(key="pct:Thermo.conduction_heat_rate:conductivity").set_value(5.0).run()
    assert not app.exception
    labels = [m.label for m in app.metric]
    assert "95 % interval" in labels


def test_search_and_error_message():
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.sidebar.text_input[0].set_value("reynolds").run()
    assert app.sidebar.selectbox[0].value == "Fluids.reynolds_number"
    for name, value in {"density": 998, "velocity": 2, "length": 0.05, "viscosity": 0}.items():
        app.number_input(key=f"in:Fluids.reynolds_number:{name}").set_value(value)
    app.run()
    assert app.error and "Error" in app.error[0].value
