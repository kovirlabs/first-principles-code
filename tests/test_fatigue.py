# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.fatigue.Fatigue.

Source for every equation: Shigley's Mechanical Engineering Design
(Budynas & Nisbett, 10th ed.), Ch. 6. ``test_reliability_factor_matches_table``
asserts *published* table values (Table 6-5); the other expected numbers are
independent hand calculations of the cited equations.
"""

import math

import pytest

from fpc.fatigue import Fatigue

fatigue = Fatigue()
MPA = 1e6


def test_endurance_limit_steel():
    """Shigley Eq. 6-8: Se' = 0.5 Sut up to 1400 MPa, then a 700 MPa plateau."""
    assert fatigue.endurance_limit_steel(ultimate_strength=600 * MPA) == pytest.approx(300 * MPA)
    assert fatigue.endurance_limit_steel(ultimate_strength=1400 * MPA) == pytest.approx(700 * MPA)
    assert fatigue.endurance_limit_steel(ultimate_strength=1800 * MPA) == pytest.approx(700 * MPA)


def test_surface_factor_hand_calc():
    """Shigley Eq. 6-19 with Table 6-2: machined, Sut = 520 MPa ->
    ka = 4.51 * 520^-0.265 = 0.860 (hand calculation)."""
    ka = fatigue.surface_factor(ultimate_strength=520 * MPA, finish="machined")
    assert ka == pytest.approx(0.860, abs=5e-4)


@pytest.mark.parametrize(
    ("finish", "a", "b"),
    [
        ("ground", 1.58, -0.085),
        ("machined", 4.51, -0.265),
        ("cold-drawn", 4.51, -0.265),
        ("hot-rolled", 57.7, -0.718),
        ("as-forged", 272.0, -0.995),
    ],
)
def test_surface_factor_uses_table_6_2_coefficients(finish, a, b):
    """Shigley Table 6-2 coefficients (Sut in MPa), evaluated at Sut = 1000 MPa."""
    assert fatigue.surface_factor(ultimate_strength=1000 * MPA, finish=finish) == pytest.approx(
        a * 1000**b
    )


def test_rougher_finish_lowers_the_surface_factor():
    factors = [
        fatigue.surface_factor(ultimate_strength=800 * MPA, finish=f)
        for f in ("ground", "machined", "hot-rolled", "as-forged")
    ]
    assert factors == sorted(factors, reverse=True)


def test_size_factor_hand_calc():
    """Shigley Eq. 6-20: kb = 1.24 d^-0.107 (d <= 51 mm), 1.51 d^-0.157 above."""
    assert fatigue.size_factor(diameter=0.032) == pytest.approx(1.24 * 32**-0.107)
    assert fatigue.size_factor(diameter=0.032) == pytest.approx(0.856, abs=5e-4)
    assert fatigue.size_factor(diameter=0.100) == pytest.approx(1.51 * 100**-0.157)
    assert fatigue.size_factor(diameter=0.100, loading="axial") == 1.0
    with pytest.raises(ValueError, match="metres"):
        fatigue.size_factor(diameter=32.0)  # millimetres passed by mistake


def test_load_factor():
    """Shigley Eq. 6-26: kc = 1 bending, 0.85 axial, 0.59 torsion."""
    assert fatigue.load_factor(loading="bending") == 1.0
    assert fatigue.load_factor(loading="axial") == 0.85
    assert fatigue.load_factor(loading="torsion") == 0.59


@pytest.mark.parametrize(
    ("reliability", "published_ke"),
    [(0.50, 1.000), (0.90, 0.897), (0.95, 0.868), (0.99, 0.814), (0.999, 0.753), (0.9999, 0.702)],
)
def test_reliability_factor_matches_table(reliability, published_ke):
    """Published values: Shigley 10th ed., Table 6-5 (ke = 1 - 0.08 za)."""
    ke = fatigue.reliability_factor(reliability=reliability)
    assert ke == pytest.approx(published_ke, abs=1e-3)


def test_marin_endurance_limit_multiplies_the_factors():
    se = fatigue.marin_endurance_limit(
        specimen_endurance_limit=300 * MPA,
        surface_factor=0.8,
        size_factor=0.9,
        reliability_factor=0.814,
    )
    assert se == pytest.approx(300 * MPA * 0.8 * 0.9 * 0.814)


# Load point used for the mean-stress criteria (all MPa, hand calculations):
# sa = 100, sm = 100, Se = 200, Sut = 500, Sy = 400.
_POINT = {"alternating_stress": 100 * MPA, "mean_stress": 100 * MPA, "endurance_limit": 200 * MPA}


def test_goodman_and_soderberg_hand_calc():
    """1/n = sa/Se + sm/Sut = 0.5 + 0.2 -> 1.4286; Soderberg 0.5 + 0.25 -> 1.3333."""
    goodman = fatigue.goodman_safety_factor(**_POINT, ultimate_strength=500 * MPA)
    soderberg = fatigue.soderberg_safety_factor(**_POINT, yield_strength=400 * MPA)
    assert goodman == pytest.approx(1 / 0.7)
    assert soderberg == pytest.approx(1 / 0.75)


def test_asme_elliptic_hand_calc():
    """n = 1/sqrt(0.5^2 + 0.25^2) = 1.78885."""
    n = fatigue.asme_elliptic_safety_factor(**_POINT, yield_strength=400 * MPA)
    assert n == pytest.approx(1 / math.sqrt(0.25 + 0.0625))


def test_gerber_satisfies_its_parabola():
    """Shigley Table 6-7: the Gerber n must satisfy n sa/Se + (n sm/Sut)^2 = 1."""
    n = fatigue.gerber_safety_factor(**_POINT, ultimate_strength=500 * MPA)
    assert n * 100 / 200 + (n * 100 / 500) ** 2 == pytest.approx(1.0)
    # Gerber lies above Goodman, which lies above Soderberg.
    goodman = fatigue.goodman_safety_factor(**_POINT, ultimate_strength=500 * MPA)
    soderberg = fatigue.soderberg_safety_factor(**_POINT, yield_strength=400 * MPA)
    assert soderberg < goodman < n


def test_gerber_with_no_mean_stress_is_se_over_sa():
    n = fatigue.gerber_safety_factor(
        alternating_stress=100 * MPA,
        mean_stress=0.0,
        endurance_limit=250 * MPA,
        ultimate_strength=600 * MPA,
    )
    assert n == pytest.approx(2.5)


def test_mean_stress_criteria_reject_compressive_mean():
    with pytest.raises(ValueError, match="mean_stress"):
        fatigue.goodman_safety_factor(
            alternating_stress=1.0, mean_stress=-1.0, endurance_limit=1.0, ultimate_strength=2.0
        )


def test_sn_curve_coefficients_hand_calc():
    """Shigley Eqs. 6-14, 6-15 with Sut = 700, Se = 350 MPa, f = 0.9:
    a = 630^2/350 = 1134 MPa, b = -log10(630/350)/3 = -0.085091."""
    coeffs = fatigue.sn_curve_coefficients(ultimate_strength=700 * MPA, endurance_limit=350 * MPA)
    assert coeffs["a"] == pytest.approx(1134 * MPA)
    assert coeffs["b"] == pytest.approx(-0.085091, rel=1e-4)


def test_cycles_to_failure_spans_1e3_to_1e6():
    """The Basquin line passes through (1e3, f*Sut) and (1e6, Se)."""
    common = {"ultimate_strength": 700 * MPA, "endurance_limit": 350 * MPA}
    assert fatigue.cycles_to_failure(alternating_stress=630 * MPA, **common) == pytest.approx(1e3)
    just_above_se = fatigue.cycles_to_failure(alternating_stress=350.0001 * MPA, **common)
    assert just_above_se == pytest.approx(1e6, rel=1e-4)
    # Hand calc at 500 MPa: N = (500/1134)^(1/-0.085091) = 1.512e4 cycles.
    assert fatigue.cycles_to_failure(alternating_stress=500 * MPA, **common) == pytest.approx(
        1.512e4, rel=1e-3
    )
    # Below the endurance limit: infinite life.
    assert fatigue.cycles_to_failure(alternating_stress=300 * MPA, **common) == math.inf
    with pytest.raises(ValueError, match="low-cycle"):
        fatigue.cycles_to_failure(alternating_stress=650 * MPA, **common)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        fatigue.endurance_limit_steel(ultimate_strength=0.0)
    with pytest.raises(ValueError):
        fatigue.reliability_factor(reliability=99.0)  # percent instead of a fraction
    with pytest.raises(ValueError):
        fatigue.marin_endurance_limit(specimen_endurance_limit=300 * MPA, size_factor=0.0)
