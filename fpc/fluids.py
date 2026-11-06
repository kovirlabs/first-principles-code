# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""fluids.py - fluid dynamics calculations.

Fluid mechanics governs anything that flows: pipes, pumps, wings, and weather.
These helpers cover the core dimensionless groups and conservation laws -
Reynolds number, the continuity equation, Bernoulli's equation, dynamic
pressure, and pipe friction losses.

``colebrook_friction_factor`` is also the project's root-finding lesson: the
Colebrook equation cannot be rearranged for f, so we hand it to
``scipy.optimize.brentq`` and let the computer find the f that satisfies it.
"""

import math

from scipy.optimize import brentq


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

    def swamee_jain_friction_factor(self, *, reynolds, relative_roughness):
        """Explicit approximation to the Colebrook friction factor (Swamee-Jain).

        f = 0.25 / [log10(eps/(3.7*D) + 5.74/Re^0.9)]^2, within about 1% of
        Colebrook for 5e3 < Re < 1e8 and 1e-6 < eps/D < 1e-2. Handy as a quick
        estimate, and as the starting guess for the exact solve below.

        :param reynolds: Reynolds number Re [-] (turbulent flow)
        :param relative_roughness: pipe roughness / diameter, eps/D [-]
        :returns: Darcy friction factor f [-]
        """
        return 0.25 / math.log10(relative_roughness / 3.7 + 5.74 / reynolds ** 0.9) ** 2

    def colebrook_friction_factor(self, *, reynolds, relative_roughness):
        """Darcy friction factor from the Colebrook equation, solved numerically.

        Colebrook (turbulent pipe flow) is *implicit* - f appears on both sides:

            1/sqrt(f) = -2 * log10( (eps/D)/3.7 + 2.51 / (Re * sqrt(f)) )

        There is no algebra that isolates f, so we turn it into a root-finding
        problem: define residual(f) = left side - right side and ask
        ``scipy.optimize.brentq`` for the f where residual(f) = 0. Brent's
        method needs a bracket [a, b] where the residual changes sign; every
        turbulent pipe has 0.001 < f < 0.2, so that bracket always works.

        For laminar flow (Re < 2300) the exact answer is simply f = 64/Re.

        :param reynolds: Reynolds number Re [-]
        :param relative_roughness: pipe roughness / diameter, eps/D [-]
            (e.g. commercial steel eps = 0.045 mm)
        :returns: Darcy friction factor f [-]
        :raises ValueError: for non-positive Re or negative roughness
        """
        if reynolds <= 0:
            raise ValueError("reynolds must be positive")
        if relative_roughness < 0:
            raise ValueError("relative_roughness cannot be negative")
        if reynolds < 2300:
            # Laminar: Hagen-Poiseuille gives an exact closed form.
            return 64.0 / reynolds

        def residual(f):
            """Colebrook rearranged so the correct f makes this zero."""
            return 1 / math.sqrt(f) + 2 * math.log10(
                relative_roughness / 3.7 + 2.51 / (reynolds * math.sqrt(f))
            )

        # brentq is guaranteed to converge once the root is bracketed, which
        # is why it is the default choice for "solve this one equation".
        return brentq(residual, 0.001, 0.2, xtol=1e-12)

    def pipe_flow(self, *, flow, diameter, length, roughness, density, viscosity):
        """Everything about steady flow through one straight pipe, in one call.

        Chains the methods above: velocity from continuity, Reynolds number,
        Colebrook friction factor, Darcy-Weisbach head loss, and the pressure
        drop dp = rho * g * h_f. Returning a dict (instead of a single number)
        is handy when a report, CLI, or web app wants to show all of it.

        :param flow: volumetric flow rate Q [m^3/s]
        :param diameter: pipe inner diameter D [m]
        :param length: pipe length L [m]
        :param roughness: absolute pipe roughness eps [m]
            (commercial steel ~0.045e-3, drawn tubing ~0.0015e-3)
        :param density: fluid density rho [kg/m^3]
        :param viscosity: dynamic viscosity mu [Pa*s]
        :returns: dict with ``velocity`` [m/s], ``reynolds`` [-],
            ``friction_factor`` [-], ``head_loss`` [m], ``pressure_drop`` [Pa]
        """
        if flow <= 0 or diameter <= 0 or length <= 0:
            raise ValueError("flow, diameter, and length must be positive")
        velocity = flow / (math.pi * diameter**2 / 4)
        reynolds = self.reynolds_number(
            density=density, velocity=velocity, length=diameter, viscosity=viscosity,
        )
        friction_factor = self.colebrook_friction_factor(
            reynolds=reynolds, relative_roughness=roughness / diameter,
        )
        head_loss = self.pipe_head_loss(
            friction_factor=friction_factor, length=length, diameter=diameter,
            velocity=velocity,
        )
        return {
            "velocity": velocity,
            "reynolds": reynolds,
            "friction_factor": friction_factor,
            "head_loss": head_loss,
            "pressure_drop": density * self.GRAVITY * head_loss,
        }
