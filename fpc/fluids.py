# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""fluids.py - fluid dynamics calculations.

Fluid mechanics governs anything that flows: pipes, pumps, wings, and weather.
These helpers cover the core dimensionless groups and conservation laws -
Reynolds number, the continuity equation, Bernoulli's equation, dynamic
pressure, and pipe friction losses.
"""

import math


class Fluids:
    """Fluid dynamics helpers."""

    # Acceleration due to gravity [m/s^2], used by head/pressure relations.
    GRAVITY = 9.80665

    def reynolds_number(self, *, density, velocity, length, viscosity):
        """Reynolds number: Re = rho*v*L / mu.

        Re is the ratio of inertial to viscous forces and tells you whether
        flow is laminar (Re < ~2300 in a pipe) or turbulent (Re > ~4000).

        :param density: fluid density rho [kg/m^3]
        :param velocity: flow velocity v [m/s]
        :param length: characteristic length L (e.g. pipe diameter) [m]
        :param viscosity: dynamic viscosity mu [Pa*s]
        :returns: Reynolds number [-]
        """
        return density * velocity * length / viscosity

    def continuity_velocity(self, *, area_in, velocity_in, area_out):
        """Outlet velocity from conservation of mass: A1*v1 = A2*v2.

        For an incompressible fluid, narrowing the pipe speeds the flow up.

        :param area_in: inlet cross-sectional area A1 [m^2]
        :param velocity_in: inlet velocity v1 [m/s]
        :param area_out: outlet cross-sectional area A2 [m^2]
        :returns: outlet velocity v2 [m/s]
        """
        return area_in * velocity_in / area_out

    def dynamic_pressure(self, *, density, velocity):
        """Dynamic pressure of a moving fluid: q = 1/2 * rho * v^2.

        :param density: fluid density rho [kg/m^3]
        :param velocity: flow velocity v [m/s]
        :returns: dynamic pressure [Pa]
        """
        return 0.5 * density * velocity ** 2

    def bernoulli_pressure(
        self, *, density, velocity_1, height_1, pressure_1, velocity_2, height_2,
        gravity=GRAVITY,
    ):
        """Downstream static pressure from Bernoulli's equation.

        Along a streamline (no friction, incompressible):
            P + 1/2*rho*v^2 + rho*g*h = constant.
        Given state 1 fully and the velocity/height at state 2, solve for P2.

        :param density: fluid density rho [kg/m^3]
        :param velocity_1: velocity at point 1 [m/s]
        :param height_1: elevation at point 1 [m]
        :param pressure_1: static pressure at point 1 [Pa]
        :param velocity_2: velocity at point 2 [m/s]
        :param height_2: elevation at point 2 [m]
        :param gravity: gravitational acceleration [m/s^2]
        :returns: static pressure at point 2 [Pa]
        """
        total_head = (
            pressure_1
            + 0.5 * density * velocity_1 ** 2
            + density * gravity * height_1
        )
        return total_head - 0.5 * density * velocity_2 ** 2 - density * gravity * height_2

    def pipe_head_loss(self, *, friction_factor, length, diameter, velocity, gravity=GRAVITY):
        """Major head loss in a pipe (Darcy-Weisbach equation).

        h_f = f * (L/D) * v^2 / (2*g).

        :param friction_factor: Darcy friction factor f [-]
        :param length: pipe length L [m]
        :param diameter: pipe inner diameter D [m]
        :param velocity: average flow velocity v [m/s]
        :param gravity: gravitational acceleration [m/s^2]
        :returns: head loss [m of fluid]
        """
        return friction_factor * (length / diameter) * velocity ** 2 / (2 * gravity)
