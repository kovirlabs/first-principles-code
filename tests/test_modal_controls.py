"""Tests for library.modal.Modal and library.controls.Controls.

Shows how to test code that returns numpy arrays (check the shape and a few
values) and how to test a simulation (check it converges to the right answer).
"""

import math

import numpy as np
import pytest

from library.modal import Modal
from library.controls import Controls

modal = Modal()
controls = Controls()


# --- Modal -----------------------------------------------------------------

def test_natural_frequency():
    """omega_n = sqrt(k/m); f_n = omega_n/(2*pi)."""
    omega_n, f_n = modal.natural_frequency(stiffness=1000.0, mass=2.0)
    assert omega_n == pytest.approx(math.sqrt(500.0))
    assert f_n == pytest.approx(omega_n / (2 * math.pi))


def test_damping_ratio_is_dimensionless_fraction():
    zeta = modal.damping_ratio(damping=10.0, mass=2.0, stiffness=1000.0)
    assert 0.0 < zeta < 1.0  # an underdamped system


def test_simulate_then_fit_recovers_parameters():
    """solve_ivp + curve_fit round-trip: fit the simulation, get the inputs back.

    Simulate a known damped oscillator, then fit the response. The recovered
    natural frequency and damping ratio should match what we put in - the
    strongest possible check that both numerical methods are wired up right.
    """
    mass, stiffness, damping = 2.0, 800.0, 8.0
    _, true_f_n = modal.natural_frequency(stiffness=stiffness, mass=mass)
    true_zeta = modal.damping_ratio(damping=damping, mass=mass, stiffness=stiffness)

    time, displacement = modal.simulate_free_vibration(
        mass=mass, stiffness=stiffness, damping=damping,
        initial_displacement=0.01, duration=5.0, num_points=600,
    )
    # The response should start at the release point and decay toward zero.
    assert displacement[0] == pytest.approx(0.01)
    assert abs(displacement[-1]) < abs(displacement[0])

    fit = modal.fit_damped_response(
        time=time, displacement=displacement, guess_frequency_hz=3.0,
    )
    assert fit["natural_frequency_hz"] == pytest.approx(true_f_n, rel=1e-2)
    assert fit["damping_ratio"] == pytest.approx(true_zeta, rel=5e-2)


def test_mode_shapes_returns_sorted_frequencies():
    """A 2-DOF system yields 2 natural frequencies, lowest first."""
    frequencies, shapes = modal.mode_shapes(
        mass_matrix=[[2.0, 0.0], [0.0, 1.0]],
        stiffness_matrix=[[3.0, -1.0], [-1.0, 1.0]],
    )
    assert frequencies.shape == (2,)
    assert shapes.shape == (2, 2)
    # np.diff being non-negative proves the result is sorted ascending.
    assert np.all(np.diff(frequencies) >= 0)


# --- Controls --------------------------------------------------------------

def test_pid_output_sums_three_terms():
    """u = Kp*e + Ki*integral + Kd*derivative."""
    u = controls.pid_output(
        error=2.0, integral=1.0, derivative=0.5, kp=3.0, ki=2.0, kd=1.0,
    )
    assert u == pytest.approx(3 * 2 + 2 * 1 + 1 * 0.5)


def test_damping_from_overshoot_inverts_correctly():
    """Feeding the derived zeta back through the overshoot formula returns 5%."""
    zeta = controls.damping_from_overshoot(percent_overshoot=5.0)
    overshoot = math.exp(-zeta * math.pi / math.sqrt(1 - zeta ** 2)) * 100
    assert overshoot == pytest.approx(5.0)


def test_pid_simulation_converges_to_setpoint():
    """A PI controller should drive a first-order plant to its target."""
    time, output = controls.simulate_pid_first_order(
        setpoint=1.0, time_constant=0.5, gain=1.0,
        kp=4.0, ki=2.0, duration=15.0,
    )
    # The time and output arrays line up...
    assert time.shape == output.shape
    # ...and the loop settles within 2% of the setpoint by the end.
    assert output[-1] == pytest.approx(1.0, abs=0.02)
