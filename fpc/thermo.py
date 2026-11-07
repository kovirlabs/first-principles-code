# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""thermo.py - thermodynamics calculations.

Thermodynamics tracks energy as it moves between heat and work. These helpers
cover the ideal gas law, heat transfer by conduction and convection, sensible
heat, the Carnot efficiency limit on heat engines, and the log-mean
temperature difference used to size heat exchangers.
"""

import math


class Thermo:
    """Thermodynamics helpers."""

    # Universal gas constant [J/(mol*K)].
    R_UNIVERSAL = 8.314462618

    def ideal_gas_pressure(self, *, moles: float, temperature: float, volume: float) -> float:
        """Pressure from the ideal gas law: P = n*R*T / V.

        Temperatures MUST be absolute (kelvin) - a common beginner mistake is
        to pass celsius. Use ``celsius_to_kelvin`` first if needed.

        :param moles: amount of substance n [mol]
        :param temperature: absolute temperature T [K]
        :param volume: volume V [m^3]
        :returns: pressure [Pa]
        """
        return moles * self.R_UNIVERSAL * temperature / volume

    def sensible_heat(
        self, *, mass: float, specific_heat: float, delta_temperature: float
    ) -> float:
        """Heat to change a substance's temperature: Q = m*c*dT.

        :param mass: mass [kg]
        :param specific_heat: specific heat capacity c [J/(kg*K)]
        :param delta_temperature: temperature change dT [K or degC, same size]
        :returns: heat energy [J] (positive = added, negative = removed)
        """
        return mass * specific_heat * delta_temperature

    def conduction_heat_rate(
        self, *, conductivity: float, area: float, delta_temperature: float, thickness: float
    ) -> float:
        """Steady heat conduction through a wall (Fourier's law).

        Q_dot = k * A * dT / L.

        :param conductivity: thermal conductivity k [W/(m*K)]
        :param area: cross-sectional area A [m^2]
        :param delta_temperature: temperature difference across the wall [K]
        :param thickness: wall thickness L [m]
        :returns: heat transfer rate [W]
        """
        return conductivity * area * delta_temperature / thickness

    def convection_heat_rate(
        self, *, coefficient: float, area: float, delta_temperature: float
    ) -> float:
        """Convective heat transfer (Newton's law of cooling).

        Q_dot = h * A * dT.

        :param coefficient: convective heat transfer coefficient h [W/(m^2*K)]
        :param area: surface area A [m^2]
        :param delta_temperature: surface-to-fluid temperature difference [K]
        :returns: heat transfer rate [W]
        """
        return coefficient * area * delta_temperature

    def carnot_efficiency(self, *, hot_temperature: float, cold_temperature: float) -> float:
        """Maximum possible efficiency of a heat engine: 1 - Tc/Th.

        Both temperatures are absolute (kelvin). No real engine can beat this.

        :param hot_temperature: hot reservoir temperature Th [K]
        :param cold_temperature: cold reservoir temperature Tc [K]
        :returns: efficiency as a fraction between 0 and 1 [-]
        """
        return 1 - (cold_temperature / hot_temperature)

    def celsius_to_kelvin(self, *, celsius: float) -> float:
        """Convert temperature from degrees Celsius to kelvin.

        :param celsius: temperature [degC]
        :returns: temperature [K]
        """
        return celsius + 273.15

    def log_mean_temperature_difference(self, *, delta_t_1: float, delta_t_2: float) -> float:
        """Log-mean temperature difference (LMTD) for a heat exchanger.

        LMTD = (dT1 - dT2) / ln(dT1 / dT2), where dT1 and dT2 are the hot-cold
        temperature differences at the two ends of the exchanger. The duty is
        then Q = U * A * LMTD. When dT1 == dT2 the formula is 0/0; its limit
        is simply dT1, which we return directly.

        For counterflow: dT1 = Th_in - Tc_out, dT2 = Th_out - Tc_in.
        For parallel flow: dT1 = Th_in - Tc_in, dT2 = Th_out - Tc_out.

        :param delta_t_1: temperature difference at one end [K]
        :param delta_t_2: temperature difference at the other end [K]
        :returns: log-mean temperature difference [K]
        :raises ValueError: if either difference is not positive (that would
            mean the streams cross, which a simple exchanger cannot do)
        """
        if delta_t_1 <= 0 or delta_t_2 <= 0:
            raise ValueError("both end temperature differences must be positive")
        if math.isclose(delta_t_1, delta_t_2):
            return delta_t_1
        return (delta_t_1 - delta_t_2) / math.log(delta_t_1 / delta_t_2)
