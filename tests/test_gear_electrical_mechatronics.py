# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the Gear, Electrical, and Mechatronics classes."""

import math

import pytest

from library.gear import Gear
from library.electrical import Electrical
from library.mechatronics import Mechatronics

gear = Gear()
electrical = Electrical()
mechatronics = Mechatronics()


# --- Gear ------------------------------------------------------------------

def test_gear_ratio_reduces_speed_and_multiplies_torque():
    ratio = gear.gear_ratio(driver_teeth=10, driven_teeth=40)
    assert ratio == pytest.approx(4.0)
    # A 4:1 reduction quarters the output speed...
    assert gear.output_speed(input_speed=1000.0, gear_ratio=ratio) == pytest.approx(250.0)
    # ...and (ideally) quadruples the torque.
    assert gear.output_torque(
        input_torque=10.0, gear_ratio=ratio,
    ) == pytest.approx(40.0)


def test_powertrain_ratio_is_the_product_of_stages():
    assert gear.powertrain_ratio(stage_ratios=[3.0, 2.0, 1.5]) == pytest.approx(9.0)


# --- Electrical ------------------------------------------------------------

def test_parallel_resistance_is_below_the_smallest_resistor():
    total = electrical.parallel_resistance(resistances=[100.0, 100.0])
    assert total == pytest.approx(50.0)
    assert total < 100.0


def test_series_resistance_adds():
    assert electrical.series_resistance(
        resistances=[100.0, 200.0, 300.0],
    ) == pytest.approx(600.0)


def test_rc_time_constant_and_power():
    assert electrical.rc_time_constant(
        resistance=1000.0, capacitance=1e-6,
    ) == pytest.approx(1e-3)
    assert electrical.power(voltage=10.0, current=2.0) == pytest.approx(20.0)


# --- Mechatronics ----------------------------------------------------------

def test_ballscrew_linear_speed():
    """600 rpm on a 5 mm lead -> 50 mm/s."""
    assert mechatronics.ballscrew_linear_speed(
        motor_rpm=600.0, lead=5.0,
    ) == pytest.approx(50.0)


def test_reflected_inertia_falls_with_square_of_ratio():
    """A 2:1 reduction makes the load look 1/4 as heavy to the motor."""
    assert mechatronics.reflected_inertia(
        load_inertia=0.04, gear_ratio=2.0,
    ) == pytest.approx(0.01)


def test_motor_power_from_torque_and_speed():
    """P = T*omega, with omega = rpm*2*pi/60."""
    expected = 2.0 * (3000.0 * 2 * math.pi / 60.0)
    assert mechatronics.motor_power(
        torque=2.0, speed_rpm=3000.0,
    ) == pytest.approx(expected)


def test_calculate_inertia_ratio():
    """Test inertia ratio calculation with example values."""
    results = mechatronics.calculate_inertia_ratio(
        j_motor=0.00005,
        mass=50.0,
        pitch=0.01,
        teeth_motor_pulley=20,
        teeth_screw_pulley=40,
        j_screw=0.0001,
        j_pulley_motor=0.00001,
        j_pulley_screw=0.00004,
    )
    assert results["reduction_ratio"] == pytest.approx(2.0)
    # j_mass = 50.0 * (0.01 / (2 * math.pi))**2 = 0.000126651...
    # j_ballscrew_total = 0.00004 + 0.0001 + 0.000126651 = 0.000266651...
    # j_reflected_to_motor = 0.000266651 / 4.0 = 0.000066662...
    # j_load_total = 0.00001 + 0.000066662 = 0.000076662...
    assert results["j_load_total"] == pytest.approx(0.0000766628, rel=1e-3)
    # inertia_ratio = 0.000076662 / 0.00005 = 1.5332...
    assert results["inertia_ratio"] == pytest.approx(1.53325, rel=1e-3)


def test__calculate_acceleration_torque():
    """Test required motor acceleration torque calculation with example values."""
    # Reusing the total load inertia from the previous test result
    j_load_total = 0.0000766627
    j_motor = 0.00005
    target_acceleration_m_s2 = 2.0
    reduction_ratio = 2.0
    pitch = 0.01

    req_torque = mechatronics._calculate_acceleration_torque(
        j_total=j_load_total,
        j_motor=j_motor,
        linear_acceleration=target_acceleration_m_s2,
        pitch=pitch,
        reduction_ratio=reduction_ratio,
    )
    # Total system inertia = 0.0000766627 + 0.00005 = 0.0001266627
    # alpha_screw = 2.0 * (2 * math.pi / 0.01) = 1256.637...
    # alpha_motor = 1256.637... * 2.0 = 2513.274...
    # req_torque = 0.0001266627 * 2513.274... = 0.3183...
    assert req_torque == pytest.approx(0.318338, rel=1e-3)
