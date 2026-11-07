# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.psychrometrics.Psychrometrics.

Equations: ASHRAE Handbook - Fundamentals (2017), Ch. 1 "Psychrometrics".

Published reference values asserted here:

* Saturation pressure of water vapour - ASHRAE Handbook - Fundamentals 2017,
  Ch. 1, Table 3 (Thermodynamic Properties of Water at Saturation).
* Dew point and humidity ratio at 25 degC / 50 % RH, sea level - standard
  psychrometric chart values (e.g. ASHRAE Psychrometric Chart No. 1), read to
  chart precision, so the tolerances are loose.

Everything else is checked by hand calculation or by internal consistency
(substituting an answer back into the equation it should satisfy).
"""

import pytest

from fpc.psychrometrics import Psychrometrics

psy = Psychrometrics()


@pytest.mark.parametrize(
    ("temperature_c", "phase", "published_kpa"),
    [
        (-20.0, "ice", 0.10326),
        (0.0, "water", 0.6112),
        (20.0, "water", 2.3392),
        (25.0, "water", 3.1699),
        (100.0, "water", 101.42),
    ],
)
def test_saturation_pressure_matches_ashrae_table(temperature_c, phase, published_kpa):
    """ASHRAE Handbook - Fundamentals 2017, Ch. 1, Table 3."""
    pws = psy.saturation_vapor_pressure(temperature_c=temperature_c, phase=phase)
    assert pws / 1e3 == pytest.approx(published_kpa, rel=1e-3)


def test_auto_phase_uses_ice_below_freezing():
    auto = psy.saturation_vapor_pressure(temperature_c=-10.0)
    ice = psy.saturation_vapor_pressure(temperature_c=-10.0, phase="ice")
    water = psy.saturation_vapor_pressure(temperature_c=-10.0, phase="water")
    assert auto == ice
    assert ice < water  # supercooled water has the higher vapour pressure


def test_standard_pressure_at_altitude():
    """ASHRAE 2017 Ch. 1 Eq. 3 by hand: 101.325 * (1 - 2.25577e-5 * 1500)^5.2559 = 84.556 kPa."""
    assert psy.standard_pressure(altitude=0.0) == pytest.approx(101325.0)
    assert psy.standard_pressure(altitude=1500.0) == pytest.approx(84556, rel=1e-4)


def test_humidity_ratio_hand_calc_and_inverse():
    """ASHRAE 2017 Ch. 1 Eq. 20: W = 0.621945 * 2000 / (101325 - 2000) = 0.012523."""
    w = psy.humidity_ratio(vapor_pressure=2000.0)
    assert w == pytest.approx(0.012523, rel=1e-4)
    assert psy.vapor_pressure(humidity_ratio=w) == pytest.approx(2000.0)


def test_relative_humidity_round_trip():
    pw = 0.4 * psy.saturation_vapor_pressure(temperature_c=30.0)
    assert psy.relative_humidity(temperature_c=30.0, vapor_pressure=pw) == pytest.approx(0.4)


def test_chart_point_25c_50_percent():
    """Psychrometric chart (sea level), 25 degC / 50 % RH: W ~ 9.9 g/kg and
    dew point ~ 13.9 degC."""
    w = psy.humidity_ratio_from_relative_humidity(temperature_c=25.0, relative_humidity=0.5)
    assert w == pytest.approx(0.0099, abs=1e-4)
    assert psy.dew_point(temperature_c=25.0, relative_humidity=0.5) == pytest.approx(13.9, abs=0.1)


def test_dew_point_is_where_the_air_saturates():
    """At the dew point, pws(td) equals the air's actual vapour pressure."""
    td = psy.dew_point(temperature_c=30.0, relative_humidity=0.6)
    actual_pw = 0.6 * psy.saturation_vapor_pressure(temperature_c=30.0)
    assert psy.saturation_vapor_pressure(temperature_c=td) == pytest.approx(actual_pw, rel=1e-8)
    assert psy.dew_point(temperature_c=30.0, relative_humidity=1.0) == 30.0


def test_enthalpy_hand_calc():
    """ASHRAE 2017 Ch. 1 Eq. 32: h = 1.006 t + W (2501 + 1.86 t)."""
    assert psy.moist_air_enthalpy(temperature_c=20.0, humidity_ratio=0.0) == pytest.approx(20.12)
    # 1.006*25 + 0.01*(2501 + 46.5) = 25.15 + 25.475 = 50.625 kJ/kg
    assert psy.moist_air_enthalpy(temperature_c=25.0, humidity_ratio=0.01) == pytest.approx(50.625)


def test_specific_volume_of_dry_air():
    """Ideal gas: v = 287.042 * 293.15 / 101325 = 0.83045 m^3/kg at 20 degC."""
    v = psy.specific_volume(temperature_c=20.0, humidity_ratio=0.0)
    assert v == pytest.approx(0.83045, rel=1e-4)
    # Water vapour is lighter than air, so moist air takes more room per kg dry air.
    assert psy.specific_volume(temperature_c=20.0, humidity_ratio=0.01) > v


def test_wet_bulb_satisfies_the_adiabatic_saturation_balance():
    """Substitute t* back into ASHRAE 2017 Ch. 1 Eq. 33 and recover the air's W."""
    t, rh = 35.0, 0.3
    t_star = psy.wet_bulb(temperature_c=t, relative_humidity=rh)
    ws_star = psy.humidity_ratio(vapor_pressure=psy.saturation_vapor_pressure(temperature_c=t_star))
    w_from_eq33 = ((2501 - 2.326 * t_star) * ws_star - 1.006 * (t - t_star)) / (
        2501 + 1.86 * t - 4.186 * t_star
    )
    w = psy.humidity_ratio_from_relative_humidity(temperature_c=t, relative_humidity=rh)
    assert w_from_eq33 == pytest.approx(w, rel=1e-6)
    # The wet bulb always lies between the dew point and the dry bulb.
    assert psy.dew_point(temperature_c=t, relative_humidity=rh) < t_star < t


def test_wet_bulb_chart_value_and_limits():
    """Chart reading at 25 degC / 50 % RH: wet bulb ~ 17.9 degC."""
    assert psy.wet_bulb(temperature_c=25.0, relative_humidity=0.5) == pytest.approx(17.9, abs=0.2)
    assert psy.wet_bulb(temperature_c=30.0, relative_humidity=1.0) == pytest.approx(30.0)
    # Below freezing the ice form of the balance is used; still bracketed.
    t_star = psy.wet_bulb(temperature_c=-5.0, relative_humidity=0.5)
    assert psy.dew_point(temperature_c=-5.0, relative_humidity=0.5) < t_star < -5.0


def test_invalid_inputs_raise():
    with pytest.raises(ValueError, match="fraction"):
        psy.dew_point(temperature_c=25.0, relative_humidity=50.0)  # percent, not fraction
    with pytest.raises(ValueError):
        psy.humidity_ratio(vapor_pressure=2e5, pressure=101325.0)
    with pytest.raises(ValueError, match="ice"):
        psy.saturation_vapor_pressure(temperature_c=10.0, phase="ice")
    with pytest.raises(ValueError):
        psy.saturation_vapor_pressure(temperature_c=250.0)
    with pytest.raises(ValueError):
        psy.dew_point(temperature_c=25.0, relative_humidity=0.0)
