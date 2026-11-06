# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for root finding, interpolation, optimization, and pandas helpers.

Covers fpc.design.Design, fpc.properties.Properties, the Colebrook solver in
fpc.fluids.Fluids, Thermo's LMTD, and Utility's table read/write.
"""

import math

import numpy as np
import pandas as pd
import pytest

from fpc import Design, Fluids, Properties, Thermo, Utility

design = Design()
props = Properties()
fluids = Fluids()


# --- Root finding ----------------------------------------------------------

def test_beam_height_for_deflection_matches_algebra():
    """brentq's answer equals the hand-solved h = (P*L^3*12 / (48*E*b*delta))^(1/3)."""
    load, length, modulus, width, limit = 5000.0, 2.0, 200e9, 0.05, 0.001
    exact = (load * length**3 * 12 / (48 * modulus * width * limit)) ** (1 / 3)
    assert design.rectangular_beam_height_for_deflection(
        load=load, length=length, modulus=modulus, width=width, max_deflection=limit,
    ) == pytest.approx(exact, rel=1e-9)
    assert exact == pytest.approx(0.1)  # same beam as the README Beam example


def test_beam_height_bad_bracket_raises():
    with pytest.raises(ValueError):
        design.rectangular_beam_height_for_deflection(
            load=5000.0, length=2.0, modulus=200e9, width=0.05,
            max_deflection=0.001, min_height=0.5, max_height=1.0,
        )


@pytest.mark.parametrize("reynolds, roughness", [
    (1e4, 0.0), (1e5, 1e-4), (1e6, 1e-3), (1e7, 1e-2),
])
def test_colebrook_satisfies_its_own_equation(reynolds, roughness):
    """Plug the solved f back into Colebrook: both sides must agree."""
    f = fluids.colebrook_friction_factor(reynolds=reynolds, relative_roughness=roughness)
    lhs = 1 / math.sqrt(f)
    rhs = -2 * math.log10(roughness / 3.7 + 2.51 / (reynolds * math.sqrt(f)))
    assert lhs == pytest.approx(rhs, rel=1e-9)
    # Swamee-Jain is an explicit approximation within ~1-2% of Colebrook.
    approx = fluids.swamee_jain_friction_factor(reynolds=reynolds, relative_roughness=roughness)
    assert approx == pytest.approx(f, rel=0.02)


def test_colebrook_known_value_and_laminar():
    """Moody chart: Re = 1e5, eps/D = 1e-4 gives f ~= 0.0185."""
    assert fluids.colebrook_friction_factor(
        reynolds=1e5, relative_roughness=1e-4,
    ) == pytest.approx(0.0185, abs=2e-4)
    assert fluids.colebrook_friction_factor(
        reynolds=1000, relative_roughness=1e-3,
    ) == pytest.approx(0.064)


# --- Optimization ----------------------------------------------------------

def test_lightest_beam_is_feasible_and_on_its_limits():
    limits = dict(allowable_stress=150e6, max_deflection=0.005)
    result = design.lightest_rectangular_beam(
        load=5000.0, length=2.0, modulus=200e9, density=7850.0, **limits,
    )
    assert result["stress"] <= limits["allowable_stress"] * (1 + 1e-6)
    assert result["deflection"] <= limits["max_deflection"] * (1 + 1e-6)
    assert result["height"] <= 4 * result["width"] * (1 + 1e-6)
    # Hand solution: deflection + aspect ratio active -> b*h^3 = 1e-5 with h = 4b.
    width = (1e-5 / 64) ** 0.25
    assert result["width"] == pytest.approx(width, rel=1e-3)
    assert result["height"] == pytest.approx(4 * width, rel=1e-3)
    assert set(result["active"]) == {"deflection", "aspect_ratio"}


def test_lightest_beam_stress_governed_case():
    """A heavy load with a loose deflection limit makes stress govern instead."""
    result = design.lightest_rectangular_beam(
        load=20000.0, length=2.0, modulus=200e9, density=7850.0,
        allowable_stress=150e6, max_deflection=0.05,
    )
    assert "stress" in result["active"]
    assert "deflection" not in result["active"]


# --- Properties: pandas + interpolation ------------------------------------

def test_tables_load_as_dataframes():
    for name in props.list_tables():
        frame = props.load_table(name=name)
        assert isinstance(frame, pd.DataFrame)
        assert not frame.empty
    with pytest.raises(ValueError):
        props.load_table(name="unobtainium")


def test_load_table_returns_independent_copy():
    frame = props.load_table(name="materials")
    frame.loc[0, "density_kg_m3"] = -1
    assert props.load_table(name="materials").loc[0, "density_kg_m3"] > 0


def test_water_saturation_at_table_points():
    """At a tabulated temperature, interpolation returns the table value exactly."""
    assert props.water_saturation(
        temperature_c=100, property="pressure_kpa",
    ) == pytest.approx(101.4)
    assert props.water_saturation(
        temperature_c=100, property="enthalpy_vaporization_kj_kg",
    ) == pytest.approx(2256.4)


def test_linear_interpolation_between_points():
    """Halfway between 20 and 25 degC, linear interpolation gives the average."""
    expected = (998.21 + 997.05) / 2
    assert props.water_liquid(
        temperature_c=22.5, property="density_kg_m3",
    ) == pytest.approx(expected)


def test_cubic_beats_linear_on_curved_data():
    """Saturation pressure is strongly curved: check against a tabulated point
    we deliberately remove, and the cubic spline should land closer."""
    table = props.load_table(name="water_saturation")
    held_out = table[table["temperature_c"] == 90].iloc[0]["pressure_kpa"]
    reduced = table[table["temperature_c"] != 90]
    linear = props.interpolate(table=reduced, x_column="temperature_c",
                               y_column="pressure_kpa", x=90)
    cubic = props.interpolate(table=reduced, x_column="temperature_c",
                              y_column="pressure_kpa", x=90, method="cubic")
    assert abs(cubic - held_out) < abs(linear - held_out)


def test_interpolation_accepts_arrays_and_refuses_extrapolation():
    values = props.water_liquid(temperature_c=np.array([10, 20]), property="density_kg_m3")
    assert values == pytest.approx([999.70, 998.21])
    with pytest.raises(ValueError):
        props.water_liquid(temperature_c=150, property="density_kg_m3")


def test_material_lookup():
    al = props.material(name="aluminum_6061_t6")
    assert al["yield_strength_mpa"] == 276
    with pytest.raises(ValueError):
        props.material(name="unobtainium")


def test_lightest_w_shape():
    assert props.lightest_w_shape(required_sx_in3=30)["designation"] == "W16x26"
    assert props.lightest_w_shape(required_sx_in3=5)["designation"] == "W6x9"
    with pytest.raises(ValueError):
        props.lightest_w_shape(required_sx_in3=1e6)


def test_w_shape_table_is_self_consistent():
    """Catch typos in the steel table with physics: Sx = Ix / (d/2), and
    weight [lb/ft] = area [in^2] * 490 lb/ft^3 / 144 in^2/ft^2 (~3.40 * A)."""
    shapes = props.load_table(name="w_shapes")
    sx_from_ix = shapes["ix_in4"] / (shapes["depth_in"] / 2)
    assert np.allclose(shapes["sx_in3"], sx_from_ix, rtol=0.01)
    assert np.allclose(shapes["weight_lb_ft"], shapes["area_in2"] * 490 / 144, rtol=0.02)


# --- Thermo LMTD ------------------------------------------------------------

def test_lmtd():
    assert Thermo().log_mean_temperature_difference(
        delta_t_1=60.0, delta_t_2=30.0,
    ) == pytest.approx(30 / math.log(2))
    assert Thermo().log_mean_temperature_difference(
        delta_t_1=20.0, delta_t_2=20.0,
    ) == pytest.approx(20.0)
    with pytest.raises(ValueError):
        Thermo().log_mean_temperature_difference(delta_t_1=-5.0, delta_t_2=20.0)


# --- Utility: pandas read/write -------------------------------------------

@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_table_round_trip(tmp_path, suffix):
    utility = Utility()
    frame = pd.DataFrame({"time_s": [0.0, 1.0], "pressure_kpa": [101.3, 99.8]})
    path = utility.write_table(frame=frame, file_path=tmp_path / f"log{suffix}")
    # check_dtype=False: Excel has no int/float distinction, so 0.0 and 1.0
    # come back as integers. The values are identical; only the type differs.
    pd.testing.assert_frame_equal(
        utility.read_table(file_path=path), frame, check_dtype=False,
    )


def test_table_bad_extension(tmp_path):
    with pytest.raises(ValueError):
        Utility().read_table(file_path=tmp_path / "log.txt")
