# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""thermo.py - thermodynamics calculations.

Thermodynamics tracks energy as it moves between heat and work. These helpers
cover the ideal gas law, heat transfer by conduction and convection, sensible
heat, and the Carnot efficiency limit on heat engines.
"""


class Thermo:
    """Thermodynamics helpers."""

    # Universal gas constant [J/(mol*K)].
    R_UNIVERSAL = 8.314462618

    def ideal_gas_pressure(self, *, moles, temperature, volume):
        """Pressure from the ideal gas law: P = n*R*T / V.

        Temperatures MUST be absolute (kelvin) - a common beginner mistake is
        to pass celsius. Use ``celsius_to_kelvin`` first if needed.

        :param moles: amount of substance n [mol]
        :param temperature: absolute temperature T [K]
        :param volume: volume V [m^3]
        :returns: pressure [Pa]
        """
        return moles * self.R_UNIVERSAL * temperature / volume

    def sensible_heat(self, *, mass, specific_heat, delta_temperature):
        """Heat to change a substance's temperature: Q = m*c*dT.

        :param mass: mass [kg]
        :param specific_heat: specific heat capacity c [J/(kg*K)]
        :param delta_temperature: temperature change dT [K or degC, same size]
        :returns: heat energy [J] (positive = added, negative = removed)
        """
        return mass * specific_heat * delta_temperature

    def conduction_heat_rate(self, *, conductivity, area, delta_temperature, thickness):
        """Steady heat conduction through a wall (Fourier's law).

        Q_dot = k * A * dT / L.

        :param conductivity: thermal conductivity k [W/(m*K)]
        :param area: cross-sectional area A [m^2]
        :param delta_temperature: temperature difference across the wall [K]
        :param thickness: wall thickness L [m]
        :returns: heat transfer rate [W]
        """
        return conductivity * area * delta_temperature / thickness

    def convection_heat_rate(self, *, coefficient, area, delta_temperature):
        """Convective heat transfer (Newton's law of cooling).

        Q_dot = h * A * dT.

        :param coefficient: convective heat transfer coefficient h [W/(m^2*K)]
        :param area: surface area A [m^2]
        :param delta_temperature: surface-to-fluid temperature difference [K]
        :returns: heat transfer rate [W]
        """
        return coefficient * area * delta_temperature

    def carnot_efficiency(self, *, hot_temperature, cold_temperature):
        """Maximum possible efficiency of a heat engine: 1 - Tc/Th.

        Both temperatures are absolute (kelvin). No real engine can beat this.

        :param hot_temperature: hot reservoir temperature Th [K]
        :param cold_temperature: cold reservoir temperature Tc [K]
        :returns: efficiency as a fraction between 0 and 1
        """
        return 1 - (cold_temperature / hot_temperature)

    def celsius_to_kelvin(self, *, celsius):
        """Convert temperature from degrees Celsius to kelvin.

        :param celsius: temperature [degC]
        :returns: temperature [K]
        """
        return celsius + 273.15
