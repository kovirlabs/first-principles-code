# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.statics.Statics and fpc.material.Material."""

import pytest

from fpc.statics import Statics
from fpc.material import Material

statics = Statics()
material = Material()


# --- Statics ---------------------------------------------------------------

def test_beam_reactions_sum_to_the_load():
    """A simply supported beam's two reactions must carry the whole load."""
    reaction_a, reaction_b = statics.beam_reactions_point_load(
        span=10.0, load=1000.0, load_position=3.0,
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
        strength=250e6, applied_stress=125e6,
    ) == pytest.approx(2.0)
    assert statics.friction_force(
        coefficient=0.3, normal_force=100.0,
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
        modulus=200e9, moment_of_inertia=4e-8, length=2.0,
    )
    assert load == pytest.approx(19739.2, rel=1e-4)


def test_thermal_expansion_scales_with_temperature():
    """dL is proportional to the temperature change."""
    small = material.thermal_expansion(
        coefficient=12e-6, original_length=1.0, delta_temperature=50.0,
    )
    big = material.thermal_expansion(
        coefficient=12e-6, original_length=1.0, delta_temperature=100.0,
    )
    assert big == pytest.approx(2 * small)
