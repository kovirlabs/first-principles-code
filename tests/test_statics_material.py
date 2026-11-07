# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.statics.Statics and fpc.material.Material."""

import math

import pytest

from fpc.material import Material
from fpc.statics import Statics

statics = Statics()
material = Material()


# --- Statics ---------------------------------------------------------------


def test_beam_reactions_sum_to_the_load():
    """A simply supported beam's two reactions must carry the whole load."""
    reaction_a, reaction_b = statics.beam_reactions_point_load(
        span=10.0,
        load=1000.0,
        load_position=3.0,
    )
    assert reaction_a == pytest.approx(700.0)
    assert reaction_b == pytest.approx(300.0)
    # Vertical equilibrium: the reactions add up to the applied load.
    assert reaction_a + reaction_b == pytest.approx(1000.0)


def test_resultant_of_3_4_5_triangle():
    """Components (3, 4) resolve to magnitude 5 at ~53.13 degrees."""
    magnitude, angle_deg = statics.resultant_2d(fx=3.0, fy=4.0)
    assert magnitude == pytest.approx(5.0)
    assert angle_deg == pytest.approx(53.1301, rel=1e-4)


def test_factor_of_safety_and_friction():
    assert statics.factor_of_safety(
        strength=250e6,
        applied_stress=125e6,
    ) == pytest.approx(2.0)
    assert statics.friction_force(
        coefficient=0.3,
        normal_force=100.0,
    ) == pytest.approx(30.0)


# --- Material --------------------------------------------------------------


def test_hookes_law_round_trip():
    """stress/strain should recover Young's modulus."""
    stress = material.stress(force=1000.0, area=0.01)
    strain = material.strain(change_in_length=0.001, original_length=2.0)
    modulus = material.youngs_modulus(stress=stress, strain=strain)
    assert stress == pytest.approx(1e5)
    assert modulus == pytest.approx(stress / strain)


def test_euler_buckling_load():
    """Critical load of a pinned-pinned column matches pi^2*E*I/L^2."""
    load = material.euler_buckling_load(
        modulus=200e9,
        moment_of_inertia=4e-8,
        length=2.0,
    )
    assert load == pytest.approx(19739.2, rel=1e-4)


def test_thermal_expansion_scales_with_temperature():
    """dL is proportional to the temperature change."""
    small = material.thermal_expansion(
        coefficient=12e-6,
        original_length=1.0,
        delta_temperature=50.0,
    )
    big = material.thermal_expansion(
        coefficient=12e-6,
        original_length=1.0,
        delta_temperature=100.0,
    )
    assert big == pytest.approx(2 * small)


# --- Column buckling: Euler vs Johnson ---------------------------------------
# Formulas: Shigley's Mechanical Engineering Design, 10th ed., Ch. 4,
# "Columns with Central Loading" (Euler) and "Intermediate-Length Columns with
# Central Loading" (J. B. Johnson parabola). The numbers below are independent
# hand calculations, not values copied from the book.

# A 25 mm solid round steel bar: A = pi d^2/4, I = pi d^4/64, so r = d/4.
_D = 0.025
_AREA = math.pi * _D**2 / 4
_I = math.pi * _D**4 / 64
_E = 200e9
_SY = 250e6


def test_radius_of_gyration_of_a_round_bar_is_quarter_diameter():
    assert material.radius_of_gyration(moment_of_inertia=_I, area=_AREA) == pytest.approx(_D / 4)


def test_slenderness_ratios():
    # KL/r for a 1 m pinned column with r = 6.25 mm: 1 / 0.00625 = 160.
    assert material.slenderness_ratio(length=1.0, radius_of_gyration=_D / 4) == pytest.approx(160.0)
    # Hand calc: sqrt(2 pi^2 * 200e9 / 250e6) = pi * sqrt(1600) = 40 pi = 125.66.
    transition = material.transition_slenderness_ratio(modulus=_E, yield_strength=_SY)
    assert transition == pytest.approx(40 * math.pi)


def test_johnson_meets_euler_at_the_transition_with_half_the_yield_load():
    """At (KL/r)_1 both formulas give P = A*Sy/2, so the combined curve is continuous."""
    transition = material.transition_slenderness_ratio(modulus=_E, yield_strength=_SY)
    common = {"modulus": _E, "moment_of_inertia": _I, "length": transition * _D / 4}
    euler = material.euler_buckling_load(**common)
    johnson = material.johnson_buckling_load(**common, area=_AREA, yield_strength=_SY)
    assert euler == pytest.approx(_AREA * _SY / 2)
    assert johnson == pytest.approx(_AREA * _SY / 2)


def test_johnson_hand_calculation():
    """L = 0.5 m pinned: KL/r = 80, Pcr/A = 250e6 - (250e6 * 80 / (2 pi))^2 / 200e9."""
    load = material.johnson_buckling_load(
        modulus=_E, moment_of_inertia=_I, area=_AREA, length=0.5, yield_strength=_SY
    )
    # (250e6 * 80 / 2pi)^2 / 200e9 = (3.1831e9)^2 / 200e9 = 50.66 MPa -> 199.34 MPa
    assert load / _AREA == pytest.approx(199.34e6, rel=1e-4)


@pytest.mark.parametrize(("length", "formula"), [(0.5, "johnson"), (1.0, "euler")])
def test_critical_buckling_load_picks_the_right_formula(length, formula):
    result = material.critical_buckling_load(
        modulus=_E, moment_of_inertia=_I, area=_AREA, length=length, yield_strength=_SY
    )
    assert result["formula"] == formula
    if formula == "euler":
        expected = material.euler_buckling_load(modulus=_E, moment_of_inertia=_I, length=length)
    else:
        expected = material.johnson_buckling_load(
            modulus=_E, moment_of_inertia=_I, area=_AREA, length=length, yield_strength=_SY
        )
    assert result["critical_load"] == pytest.approx(expected)
    # Neither formula may exceed the squash load A*Sy.
    assert result["critical_load"] < _AREA * _SY


def test_buckling_rejects_bad_inputs():
    with pytest.raises(ValueError):
        material.radius_of_gyration(moment_of_inertia=-1.0, area=1.0)
    with pytest.raises(ValueError):
        material.transition_slenderness_ratio(modulus=_E, yield_strength=0.0)
    with pytest.raises(ValueError):
        material.slenderness_ratio(length=0.0, radius_of_gyration=0.01)
