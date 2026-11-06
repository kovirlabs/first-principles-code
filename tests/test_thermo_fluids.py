# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.thermo.Thermo and fpc.fluids.Fluids."""

import pytest

from fpc.fluids import Fluids
from fpc.thermo import Thermo

thermo = Thermo()
fluids = Fluids()


# --- Thermo ----------------------------------------------------------------


def test_carnot_efficiency():
    """1 - Tc/Th for an 800 K / 300 K engine is 0.625."""
    assert thermo.carnot_efficiency(
        hot_temperature=800.0,
        cold_temperature=300.0,
    ) == pytest.approx(0.625)


def test_celsius_to_kelvin():
    assert thermo.celsius_to_kelvin(celsius=25.0) == pytest.approx(298.15)


def test_conduction_and_convection_rates():
    assert thermo.conduction_heat_rate(
        conductivity=0.5,
        area=2.0,
        delta_temperature=20.0,
        thickness=0.1,
    ) == pytest.approx(200.0)
    assert thermo.convection_heat_rate(
        coefficient=25.0,
        area=2.0,
        delta_temperature=20.0,
    ) == pytest.approx(1000.0)


# --- Fluids ----------------------------------------------------------------


def test_reynolds_number():
    assert fluids.reynolds_number(
        density=1000.0,
        velocity=2.0,
        length=0.05,
        viscosity=1e-3,
    ) == pytest.approx(1e5)


def test_continuity_speeds_flow_in_a_narrower_pipe():
    """Halving the area doubles the velocity (A1*v1 = A2*v2)."""
    v_out = fluids.continuity_velocity(
        area_in=0.1,
        velocity_in=2.0,
        area_out=0.05,
    )
    assert v_out == pytest.approx(4.0)


def test_bernoulli_trades_velocity_for_pressure():
    """Speeding the fluid up (0 -> 10 m/s) must drop the static pressure."""
    p2 = fluids.bernoulli_pressure(
        density=1000.0,
        velocity_1=0.0,
        height_1=0.0,
        pressure_1=200000.0,
        velocity_2=10.0,
        height_2=0.0,
    )
    assert p2 == pytest.approx(150000.0)
    assert p2 < 200000.0
