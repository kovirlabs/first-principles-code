# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.machine_elements.MachineElements.

Equations are from Shigley's Mechanical Engineering Design (Budynas & Nisbett,
10th ed.), cited per test. The expected numbers are *independent hand
calculations* (or a different route to the same answer, such as numerically
integrating the pressure cone, or back-substituting a diameter into the stress
formulas) - not values copied from the book's worked examples.
"""

import math

import pytest
from scipy.integrate import quad

from fpc.fatigue import Fatigue
from fpc.machine_elements import MachineElements

me = MachineElements()


# --- Bolted joints -----------------------------------------------------------


def test_tightening_torque():
    """Shigley Eq. 8-27, T = K*Fi*d: 0.2 * 20 kN * 12 mm = 48 N*m."""
    torque = me.bolt_tightening_torque(preload=20e3, nominal_diameter=0.012)
    assert torque == pytest.approx(48.0)


@pytest.mark.parametrize(("connection", "fraction"), [("reusable", 0.75), ("permanent", 0.90)])
def test_preload_is_a_fraction_of_proof_load(connection, fraction):
    """Shigley Sec. 8-9: Fi = 0.75 Fp (reusable) or 0.90 Fp (permanent), Fp = At*Sp."""
    preload = me.bolt_preload(
        proof_strength=600e6, tensile_stress_area=84.3e-6, connection=connection
    )
    assert preload == pytest.approx(fraction * 600e6 * 84.3e-6)


def test_bolt_stiffness_reduces_to_a_plain_bar():
    """Shigley Eq. 8-17. With no thread in the grip it must equal Ad*E/ld,
    and with only thread in the grip At*E/lt (one spring each)."""
    d, at, e = 0.012, 84.3e-6, 207e9
    shank_area = math.pi * d**2 / 4
    all_shank = me.bolt_stiffness(
        modulus=e,
        nominal_diameter=d,
        tensile_stress_area=at,
        unthreaded_length=0.03,
        threaded_length=0.0,
    )
    all_thread = me.bolt_stiffness(
        modulus=e,
        nominal_diameter=d,
        tensile_stress_area=at,
        unthreaded_length=0.0,
        threaded_length=0.03,
    )
    assert all_shank == pytest.approx(shank_area * e / 0.03)
    assert all_thread == pytest.approx(at * e / 0.03)
    # Springs in series: the compliances 1/k add.
    mixed = me.bolt_stiffness(
        modulus=e,
        nominal_diameter=d,
        tensile_stress_area=at,
        unthreaded_length=0.02,
        threaded_length=0.01,
    )
    assert 1 / mixed == pytest.approx(0.02 / (shank_area * e) + 0.01 / (at * e))


def test_member_stiffness_matches_integrating_the_pressure_cones():
    """Shigley Eq. 8-23 vs a direct numerical integration of the two 30-degree
    frusta (washer face 1.5 d) - an independent route to the same answer."""
    d, grip, e = 0.012, 0.04, 207e9
    tan30 = math.tan(math.radians(30))

    def area(x):
        outer_radius = 0.75 * d + x * tan30  # cone grows from the washer face
        return math.pi * (outer_radius**2 - (d / 2) ** 2)

    # Each cone spans half the grip; two identical cones act in series.
    one_cone_compliance, _ = quad(lambda x: 1 / (e * area(x)), 0, grip / 2)
    expected = 1 / (2 * one_cone_compliance)
    assert me.member_stiffness(modulus=e, nominal_diameter=d, grip_length=grip) == pytest.approx(
        expected, rel=1e-6
    )


def test_joint_constant_and_load_sharing():
    """C = kb/(kb+km); Fb = C*P + Fi, Fm = (1-C)*P - Fi, P0 = Fi/(1-C)."""
    c = me.joint_stiffness_constant(bolt_stiffness=1e9, member_stiffness=3e9)
    assert c == pytest.approx(0.25)
    loads = me.bolted_joint_loads(preload=10e3, external_load=4e3, stiffness_constant=c)
    assert loads["bolt_load"] == pytest.approx(11e3)
    assert loads["member_load"] == pytest.approx(-7e3)  # still clamped
    assert loads["separation_load"] == pytest.approx(10e3 / 0.75)
    with pytest.raises(ValueError, match="separates"):
        me.bolted_joint_loads(preload=10e3, external_load=20e3, stiffness_constant=c)


# --- Shafts --------------------------------------------------------------------


def test_static_shaft_diameter_back_substitutes_to_the_safety_factor():
    """Plug the diameter back into sigma = 32M/(pi d^3), tau = 16T/(pi d^3) and
    von Mises sigma' = sqrt(sigma^2 + 3 tau^2): Sy / sigma' must equal n."""
    m, t, sy, n = 150.0, 200.0, 350e6, 2.5
    d = me.shaft_diameter_static(bending_moment=m, torque=t, yield_strength=sy, safety_factor=n)
    sigma = 32 * m / (math.pi * d**3)
    tau = 16 * t / (math.pi * d**3)
    assert sy / math.sqrt(sigma**2 + 3 * tau**2) == pytest.approx(n)


def test_static_shaft_pure_bending_hand_calc():
    """Pure bending: d = (32 n M / (pi Sy))^(1/3) = (32*2*100/(pi*300e6))^(1/3) = 18.937 mm."""
    d = me.shaft_diameter_static(
        bending_moment=100.0, torque=0.0, yield_strength=300e6, safety_factor=2.0
    )
    assert d == pytest.approx(0.018937, rel=1e-4)


def test_de_goodman_diameter_gives_the_design_factor_on_the_goodman_line():
    """Shigley Eq. 7-8. Back-substitute d into the von Mises alternating and mean
    stresses and check the Goodman safety factor (fpc.Fatigue) equals n."""
    ma, tm, kf, kfs = 120.0, 90.0, 1.7, 1.5
    se, sut, n = 200e6, 700e6, 1.8
    d = me.shaft_diameter_de_goodman(
        alternating_moment=ma,
        mean_moment=0.0,
        alternating_torque=0.0,
        mean_torque=tm,
        endurance_limit=se,
        ultimate_strength=sut,
        safety_factor=n,
        fatigue_factor_bending=kf,
        fatigue_factor_torsion=kfs,
    )
    sigma_a = 32 * kf * ma / (math.pi * d**3)  # bending only alternates
    sigma_m = math.sqrt(3) * 16 * kfs * tm / (math.pi * d**3)  # torsion only is steady
    goodman = Fatigue().goodman_safety_factor(
        alternating_stress=sigma_a, mean_stress=sigma_m, endurance_limit=se, ultimate_strength=sut
    )
    assert goodman == pytest.approx(n)


# --- Springs ---------------------------------------------------------------------


def test_spring_rate_hand_calc():
    """Shigley Eq. 10-9: k = d^4 G / (8 D^3 Na) = (2e-3)^4 * 79.3e9 / (8 * 0.02^3 * 10)."""
    k = me.spring_rate(
        wire_diameter=2e-3, mean_coil_diameter=20e-3, active_coils=10, shear_modulus=79.3e9
    )
    assert k == pytest.approx(1982.5)


def test_spring_shear_stress_corrections():
    """C = D/d = 8: Wahl K = 31/28 + 0.615/8 = 1.18402, Bergstrasser (Shigley
    Eq. 10-5) K = 34/29 = 1.17241; plain stress 8FD/(pi d^3)."""
    plain = 8 * 100.0 * 0.016 / (math.pi * 0.002**3)
    wahl = me.spring_shear_stress(force=100.0, wire_diameter=0.002, mean_coil_diameter=0.016)
    berg = me.spring_shear_stress(
        force=100.0, wire_diameter=0.002, mean_coil_diameter=0.016, correction="bergstrasser"
    )
    assert wahl == pytest.approx(1.18402 * plain, rel=1e-5)
    assert berg == pytest.approx(34 / 29 * plain)
    assert wahl == pytest.approx(berg, rel=0.015)  # the two agree within ~1 %


# --- Bearings --------------------------------------------------------------------


def test_bearing_life():
    """L10 = (C/P)^a: C/P = 10 gives 1000 Mrev (ball, a=3) or 10^(10/3) (roller)."""
    assert me.bearing_l10_life(dynamic_load_rating=30e3, equivalent_load=3e3) == pytest.approx(
        1000.0
    )
    roller = me.bearing_l10_life(
        dynamic_load_rating=30e3, equivalent_load=3e3, bearing_type="roller"
    )
    assert roller == pytest.approx(10 ** (10 / 3))
    # 1000e6 rev at 1500 rev/min = 1e9 / 90 000 rev/h = 11 111 h.
    hours = me.bearing_l10_life_hours(dynamic_load_rating=30e3, equivalent_load=3e3, speed_rpm=1500)
    assert hours == pytest.approx(11111.1, rel=1e-5)


def test_required_rating_round_trips_with_life():
    c = me.bearing_required_load_rating(
        equivalent_load=2.5e3, life_hours=20e3, speed_rpm=900, bearing_type="roller"
    )
    life = me.bearing_l10_life_hours(
        dynamic_load_rating=c, equivalent_load=2.5e3, speed_rpm=900, bearing_type="roller"
    )
    assert life == pytest.approx(20e3)


# --- Welds -----------------------------------------------------------------------


def test_fillet_weld_throat_stress():
    """Shigley Sec. 9-3: tau = F / (0.707 h L) = 10 kN / (0.707 * 6 mm * 100 mm) = 23.57 MPa."""
    tau = me.fillet_weld_shear_stress(force=10e3, leg_size=0.006, weld_length=0.1)
    assert tau == pytest.approx(23.57e6, rel=1e-3)


# --- Validation ------------------------------------------------------------------


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        me.bolt_tightening_torque(preload=-1.0, nominal_diameter=0.01)
    with pytest.raises(ValueError, match="D vs d"):
        me.spring_rate(
            wire_diameter=0.02, mean_coil_diameter=0.002, active_coils=5, shear_modulus=79e9
        )
    with pytest.raises(ValueError):
        me.bearing_l10_life_hours(dynamic_load_rating=1e4, equivalent_load=1e3, speed_rpm=0)
    with pytest.raises(ValueError):
        me.shaft_diameter_static(bending_moment=0, torque=0, yield_strength=1e8, safety_factor=2)
    with pytest.raises(ValueError):
        me.joint_stiffness_constant(bolt_stiffness=0.0, member_stiffness=1.0)
