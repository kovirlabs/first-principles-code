# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the unit-aware Beam dataclass (fpc.beam.Beam).

Shows how to test code that uses Pint: do the math in known units, then call
``.to(...).magnitude`` to compare the numeric value with ``pytest.approx``.
Also checks that bad inputs raise, and that Pint blocks nonsensical unit math.
"""

import pytest
from pint import DimensionalityError

from fpc.units import Q_
from fpc.beam import Beam


def make_beam():
    """A 2 m steel beam, 50 mm wide x 100 mm tall - reused across tests."""
    return Beam(
        length=Q_(2.0, "m"),
        width=Q_(50, "mm"),
        height=Q_(100, "mm"),
        modulus=Q_(200, "GPa"),
    )


def test_geometry_properties():
    """Area, second moment of area, and mass from the dimensions."""
    beam = make_beam()
    assert beam.area.to("mm**2").magnitude == pytest.approx(5000.0)
    # I = b*h^3/12 = 50 * 100^3 / 12 mm^4
    assert beam.moment_of_inertia.to("mm**4").magnitude == pytest.approx(4_166_666.667, rel=1e-6)
    # steel: 7850 kg/m^3 * 0.005 m^2 * 2 m
    assert beam.mass.to("kg").magnitude == pytest.approx(78.5)


def test_deflection_and_stress_under_central_load():
    """Closed-form results for a simply supported beam, 5 kN at midspan."""
    beam = make_beam()
    load = Q_(5, "kN")
    assert beam.max_deflection_point_load(load=load).to("mm").magnitude == pytest.approx(1.0)
    assert beam.max_bending_stress_point_load(load=load).to("MPa").magnitude == pytest.approx(30.0)


def test_buckling_uses_the_weak_axis():
    """Euler load is governed by the smaller (weak-axis) second moment."""
    beam = make_beam()
    assert beam.euler_buckling_load().to("kN").magnitude == pytest.approx(514.04, rel=1e-4)


def test_results_carry_correct_dimensions():
    """A deflection is a length; a stress is a pressure - Pint enforces this."""
    beam = make_beam()
    assert beam.max_deflection_point_load(load=Q_(5, "kN")).check("[length]")
    assert beam.max_bending_stress_point_load(load=Q_(5, "kN")).check("[pressure]")


def test_default_material_is_steel():
    """Omitting modulus/density falls back to the structural-steel defaults."""
    beam = Beam(length=Q_(1, "m"), width=Q_(20, "mm"), height=Q_(20, "mm"))
    assert beam.modulus.to("GPa").magnitude == pytest.approx(200.0)
    assert beam.density.to("kg/m**3").magnitude == pytest.approx(7850.0)


def test_wrong_units_are_rejected():
    """Passing a time where a length belongs raises a clear error."""
    with pytest.raises(ValueError):
        Beam(length=Q_(2, "s"), width=Q_(50, "mm"), height=Q_(100, "mm"))


def test_negative_dimension_is_rejected():
    with pytest.raises(ValueError):
        Beam(length=Q_(-2, "m"), width=Q_(50, "mm"), height=Q_(100, "mm"))


def test_pint_blocks_incompatible_arithmetic():
    """Adding a length to a time is a DimensionalityError - the whole point."""
    with pytest.raises(DimensionalityError):
        _ = Q_(1, "m") + Q_(1, "s")
