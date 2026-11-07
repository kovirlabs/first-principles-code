# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""psychrometrics.py - properties of moist air for HVAC and drying.

Psychrometrics is the thermodynamics of air-water vapour mixtures: how much
water the air holds, when it condenses, and how much energy it carries. It
sizes every air conditioner, cooling tower, dryer, and clean room.

Everything here follows the ideal-gas formulation in the *ASHRAE
Handbook - Fundamentals* (2017, Ch. 1, "Psychrometrics"), which is accurate
to a fraction of a percent at ordinary pressures:

* saturation vapour pressure from the Hyland-Wexler equations (Eqs. 5-6);
* humidity ratio W = 0.621945 * pw / (p - pw) (Eq. 20);
* moist-air enthalpy h = 1.006*t + W*(2501 + 1.86*t) (Eq. 32);
* specific volume from the ideal-gas law;
* wet-bulb temperature from the energy balance of an adiabatic saturator
  (Eq. 33, and its ice form below 0 degC).

**Units.** Pressures are in pascals and humidity ratio in kg of water per kg
of *dry* air - the "per kg dry air" basis is what makes the mass balances
work, because the dry air flow does not change as water is added or removed.
Following the HVAC convention (and ``docs/units.md``), temperatures are in
degC and named ``temperature_c``; enthalpy is in kJ/kg dry air. Relative
humidity is a fraction from 0 to 1, not a percentage.

Dew point and wet bulb have no closed form, so - like
``Fluids.colebrook_friction_factor`` - they are solved with
``scipy.optimize.brentq``.
"""

import math
from typing import Literal

from scipy.optimize import brentq

# Hyland-Wexler coefficients for ln(pws) with pws in Pa and T in K
# (ASHRAE Handbook - Fundamentals 2017, Ch. 1, Eqs. 5 and 6).
# Over ice, -100 to 0 degC:
_ICE = (
    -5.6745359e03,
    6.3925247e00,
    -9.6778430e-03,
    6.2215701e-07,
    2.0747825e-09,
    -9.4840240e-13,
    4.1635019e00,
)
# Over liquid water, 0 to 200 degC:
_WATER = (
    -5.8002206e03,
    1.3914993e00,
    -4.8640239e-02,
    4.1764768e-05,
    -1.4452093e-08,
    6.5459673e00,
)

# Ratio of the molar masses of water and dry air, 18.015268 / 28.966.
_MOLAR_MASS_RATIO = 0.621945
# Gas constant of dry air [J/(kg*K)], used for the specific volume.
_R_DRY_AIR = 287.042

Phase = Literal["auto", "water", "ice"]


class Psychrometrics:
    """Moist-air properties (ASHRAE ideal-gas psychrometrics, SI)."""

    # Standard sea-level atmospheric pressure [Pa].
    STANDARD_PRESSURE = 101325.0

    def standard_pressure(self, *, altitude: float) -> float:
        """Standard-atmosphere pressure at an altitude, ASHRAE 2017 Ch. 1 Eq. 3.

            p = 101.325 * (1 - 2.25577e-5 * Z)^5.2559   kPa

        Psychrometric charts are drawn for sea level; in Denver (~1600 m) the
        pressure is ~17 % lower, so the same air holds noticeably more water
        per kg. Pass this result as ``pressure`` to the other methods.

        :param altitude: altitude above sea level Z [m]
        :returns: atmospheric pressure [Pa]
        :raises ValueError: for altitudes outside -5000 to 11000 m
        """
        if not -5000 <= altitude <= 11000:
            raise ValueError("altitude must be between -5000 and 11000 m (troposphere)")
        return self.STANDARD_PRESSURE * (1 - 2.25577e-5 * altitude) ** 5.2559

    def saturation_vapor_pressure(self, *, temperature_c: float, phase: Phase = "auto") -> float:
        """Saturation pressure of water vapour (Hyland-Wexler), ASHRAE 2017 Ch. 1 Eqs. 5-6.

        Over ice (-100 to 0 degC):
            ln pws = C1/T + C2 + C3*T + C4*T^2 + C5*T^3 + C6*T^4 + C7*ln T
        Over liquid water (0 to 200 degC):
            ln pws = C8/T + C9 + C10*T + C11*T^2 + C12*T^3 + C13*ln T

        with T in kelvin and pws in pascals. This is the most-used number in
        psychrometrics: the most water vapour air can hold at a temperature.
        It roughly doubles every 10 degC, which is why warm air holds so
        much more moisture. ``"auto"`` uses ice below 0 degC, as ASHRAE's
        tables do; ``"water"`` below 0 gives supercooled liquid.

        :param temperature_c: temperature t [degC], -100 to 200
        :param phase: ``"auto"``, ``"water"`` or ``"ice"``
        :returns: saturation vapour pressure pws [Pa]
        :raises ValueError: for a temperature outside -100 to 200 degC, or
            ice above 0 degC
        """
        if not -100 <= temperature_c <= 200:
            raise ValueError("temperature_c must be between -100 and 200 degC")
        if phase == "auto":
            phase = "ice" if temperature_c < 0 else "water"
        if phase == "ice" and temperature_c > 0.01:
            raise ValueError("ice does not exist above 0.01 degC (the triple point)")
        t = temperature_c + 273.15
        if phase == "ice":
            c1, c2, c3, c4, c5, c6, c7 = _ICE
            ln_p = c1 / t + c2 + c3 * t + c4 * t**2 + c5 * t**3 + c6 * t**4 + c7 * math.log(t)
        else:
            c8, c9, c10, c11, c12, c13 = _WATER
            ln_p = c8 / t + c9 + c10 * t + c11 * t**2 + c12 * t**3 + c13 * math.log(t)
        return math.exp(ln_p)

    def humidity_ratio(
        self, *, vapor_pressure: float, pressure: float = STANDARD_PRESSURE
    ) -> float:
        """Humidity ratio W = 0.621945 * pw / (p - pw), ASHRAE 2017 Ch. 1 Eq. 20.

        Dalton's law: the vapour and the dry air share the total pressure,
        p = pw + pa. Each behaves as an ideal gas, so the mass ratio is the
        ratio of partial pressures times the ratio of molar masses
        (18.015 / 28.966 = 0.621945).

        :param vapor_pressure: partial pressure of water vapour pw [Pa]
        :param pressure: total (barometric) pressure p, default sea level [Pa]
        :returns: humidity ratio W [kg/kg dry air]
        :raises ValueError: unless 0 <= pw < p
        """
        if not 0 <= vapor_pressure < pressure:
            raise ValueError("vapor_pressure must be >= 0 and below the total pressure")
        return _MOLAR_MASS_RATIO * vapor_pressure / (pressure - vapor_pressure)

    def vapor_pressure(
        self, *, humidity_ratio: float, pressure: float = STANDARD_PRESSURE
    ) -> float:
        """Vapour partial pressure from humidity ratio: pw = p * W / (0.621945 + W).

        The inverse of ``humidity_ratio``.

        :param humidity_ratio: humidity ratio W [kg/kg dry air]
        :param pressure: total (barometric) pressure p, default sea level [Pa]
        :returns: partial pressure of water vapour pw [Pa]
        :raises ValueError: for a negative humidity ratio or pressure
        """
        if humidity_ratio < 0 or pressure <= 0:
            raise ValueError("humidity_ratio cannot be negative and pressure must be positive")
        return pressure * humidity_ratio / (_MOLAR_MASS_RATIO + humidity_ratio)

    def relative_humidity(self, *, temperature_c: float, vapor_pressure: float) -> float:
        """Relative humidity phi = pw / pws(t).

        How close the air is to saturation at its own temperature. Cooling
        air raises phi without changing its water content, until phi = 1 at
        the dew point.

        :param temperature_c: dry-bulb temperature t [degC]
        :param vapor_pressure: partial pressure of water vapour pw [Pa]
        :returns: relative humidity phi, 0 to 1 [-]
        :raises ValueError: for a negative vapour pressure
        """
        if vapor_pressure < 0:
            raise ValueError("vapor_pressure cannot be negative")
        return vapor_pressure / self.saturation_vapor_pressure(temperature_c=temperature_c)

    def humidity_ratio_from_relative_humidity(
        self,
        *,
        temperature_c: float,
        relative_humidity: float,
        pressure: float = STANDARD_PRESSURE,
    ) -> float:
        """Humidity ratio from dry bulb and relative humidity: W(phi * pws(t), p).

        The everyday entry point: a thermostat or weather report gives you
        temperature and RH, and nearly every HVAC calculation then needs W.

        :param temperature_c: dry-bulb temperature t [degC]
        :param relative_humidity: relative humidity phi as a fraction, 0 to 1 [-]
        :param pressure: total (barometric) pressure p, default sea level [Pa]
        :returns: humidity ratio W [kg/kg dry air]
        :raises ValueError: for RH outside 0-1
        """
        self._check_rh(relative_humidity)
        pws = self.saturation_vapor_pressure(temperature_c=temperature_c)
        return self.humidity_ratio(vapor_pressure=relative_humidity * pws, pressure=pressure)

    def dew_point(self, *, temperature_c: float, relative_humidity: float) -> float:
        """Dew-point temperature: the t_d where pws(t_d) equals the actual pw.

        Cool the air at constant water content and condensation starts at
        the dew point - the temperature of a cold-water pipe that will start
        to "sweat". There is no closed-form inverse of the Hyland-Wexler
        equation, so solve pws(t_d) - pw = 0 with ``scipy.optimize.brentq``.
        The dew point cannot exceed the dry bulb and is above -100 degC, so
        [-100, t] always brackets the root. Below 0 degC this is the frost
        point (saturation over ice).

        :param temperature_c: dry-bulb temperature t [degC]
        :param relative_humidity: relative humidity phi as a fraction, 0 to 1 [-]
        :returns: dew-point temperature t_d [degC]
        :raises ValueError: for RH not in (0, 1]
        """
        self._check_rh(relative_humidity)
        if relative_humidity == 0:
            raise ValueError("bone-dry air (RH = 0) has no dew point")
        if relative_humidity == 1:
            return temperature_c  # already saturated
        vapor_pressure = relative_humidity * self.saturation_vapor_pressure(
            temperature_c=temperature_c
        )

        def residual(t: float) -> float:
            return self.saturation_vapor_pressure(temperature_c=t) - vapor_pressure

        return brentq(residual, -100.0, temperature_c, xtol=1e-9)

    def moist_air_enthalpy(self, *, temperature_c: float, humidity_ratio: float) -> float:
        """Specific enthalpy of moist air, ASHRAE 2017 Ch. 1 Eq. 32.

            h = 1.006*t + W*(2501 + 1.86*t)      kJ/kg dry air

        Dry-air sensible heat (cp = 1.006 kJ/(kg K)) plus the water vapour's
        latent heat (2501 kJ/kg at 0 degC) and its sensible heat (cp = 1.86).
        Zero is dry air at 0 degC. Multiply the change in h by the dry-air
        mass flow to get a coil load in kW.

        :param temperature_c: dry-bulb temperature t [degC]
        :param humidity_ratio: humidity ratio W [kg/kg dry air]
        :returns: enthalpy h [kJ/kg dry air]
        :raises ValueError: for a negative humidity ratio
        """
        if humidity_ratio < 0:
            raise ValueError("humidity_ratio cannot be negative")
        return 1.006 * temperature_c + humidity_ratio * (2501 + 1.86 * temperature_c)

    def specific_volume(
        self, *, temperature_c: float, humidity_ratio: float, pressure: float = STANDARD_PRESSURE
    ) -> float:
        """Moist-air specific volume, v = Ra * T * (1 + 1.607858*W) / p.

        The ideal-gas law for the mixture, per kg of dry air (ASHRAE 2017
        Ch. 1): 1.607858 is 1/0.621945, the ratio of the gas constants of
        water vapour and dry air. Fans move volume, coils move mass - this
        converts between them (dry-air mass flow = volume flow / v).

        :param temperature_c: dry-bulb temperature t [degC]
        :param humidity_ratio: humidity ratio W [kg/kg dry air]
        :param pressure: total (barometric) pressure p, default sea level [Pa]
        :returns: specific volume v [m^3/kg dry air]
        :raises ValueError: for a negative humidity ratio or non-positive pressure
        """
        if humidity_ratio < 0 or pressure <= 0:
            raise ValueError("humidity_ratio cannot be negative and pressure must be positive")
        t_kelvin = temperature_c + 273.15
        return _R_DRY_AIR * t_kelvin * (1 + 1.607858 * humidity_ratio) / pressure

    def wet_bulb(
        self,
        *,
        temperature_c: float,
        relative_humidity: float,
        pressure: float = STANDARD_PRESSURE,
    ) -> float:
        """Thermodynamic wet-bulb temperature from dry bulb and RH (iterative).

        The wet bulb t* is the temperature water evaporating into the air
        cools to - the limit for an evaporative cooler or cooling tower. An
        energy balance on an adiabatic saturator gives the humidity ratio
        that produces a given t* (ASHRAE 2017 Ch. 1 Eq. 33, for t* >= 0):

            W = ((2501 - 2.326*t*) * Ws* - 1.006*(t - t*))
                / (2501 + 1.86*t - 4.186*t*)

        and, below freezing (ice surface, Eq. 35):

            W = ((2830 - 0.24*t*) * Ws* - 1.006*(t - t*))
                / (2830 + 1.86*t - 2.1*t*)

        where Ws* is the saturation humidity ratio at t*. We know W and want
        t*, so ``brentq`` finds the t* in [-100, t] where the W predicted by
        the balance equals the actual W.

        :param temperature_c: dry-bulb temperature t [degC]
        :param relative_humidity: relative humidity phi as a fraction, 0 to 1 [-]
        :param pressure: total (barometric) pressure p, default sea level [Pa]
        :returns: thermodynamic wet-bulb temperature t* [degC]
        :raises ValueError: for RH outside 0-1
        """
        actual_w = self.humidity_ratio_from_relative_humidity(
            temperature_c=temperature_c, relative_humidity=relative_humidity, pressure=pressure
        )
        t = temperature_c

        def residual(t_star: float) -> float:
            pws_star = self.saturation_vapor_pressure(temperature_c=t_star)
            ws_star = self.humidity_ratio(vapor_pressure=pws_star, pressure=pressure)
            if t_star >= 0:
                numerator = (2501 - 2.326 * t_star) * ws_star - 1.006 * (t - t_star)
                predicted = numerator / (2501 + 1.86 * t - 4.186 * t_star)
            else:
                numerator = (2830 - 0.24 * t_star) * ws_star - 1.006 * (t - t_star)
                predicted = numerator / (2830 + 1.86 * t - 2.1 * t_star)
            return predicted - actual_w

        # Saturated air: wet bulb = dry bulb (the balance is already met at t).
        if abs(residual(t)) < 1e-12:
            return t
        return brentq(residual, -100.0, t, xtol=1e-9)

    @staticmethod
    def _check_rh(relative_humidity: float) -> None:
        if not 0 <= relative_humidity <= 1:
            raise ValueError("relative_humidity must be a fraction from 0 to 1 (pass 0.5, not 50)")
