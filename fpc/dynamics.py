# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""dynamics.py - kinematics and rigid-body dynamics calculations.

Dynamics is the study of motion and the forces that cause it. This class
collects the everyday formulas an engineer reaches for: kinematic equations,
projectile motion, Newton's second law, and momentum/energy relations. It also
includes a ``solve_ivp`` example - projectile flight WITH air drag, which has
no closed-form solution and so must be integrated numerically.

Every method takes keyword-only arguments (note the leading ``*``) so that
calls are self-documenting, and every method returns a plain number or tuple so
results compose easily with numpy and scipy.
"""

import math

import numpy as np
from scipy.integrate import solve_ivp


class Dynamics:
    """Kinematics and rigid-body dynamics helpers.

    The methods are stateless, so one shared instance is fine::

        dyn = Dynamics()
        v = dyn.final_velocity(initial_velocity=0.0, acceleration=9.81, time=2.0)
    """

    # Standard gravity near Earth's surface [m/s^2]. Exposed as a class
    # attribute so callers can reuse it: ``Dynamics.GRAVITY``.
    GRAVITY = 9.80665

    def displacement_constant_acceleration(
        self, *, initial_position, initial_velocity, acceleration, time
    ):
        """Displacement under constant acceleration: x = x0 + v0*t + 1/2*a*t^2.

        :param initial_position: starting position x0 [m]
        :param initial_velocity: starting velocity v0 [m/s]
        :param acceleration: constant acceleration a [m/s^2]
        :param time: elapsed time t [s]
        :returns: position x at time t [m]
        """
        return (
            initial_position
            + initial_velocity * time
            + 0.5 * acceleration * time ** 2
        )

    def final_velocity(self, *, initial_velocity, acceleration, time):
        """Velocity after constant acceleration: v = v0 + a*t.

        :param initial_velocity: starting velocity v0 [m/s]
        :param acceleration: constant acceleration a [m/s^2]
        :param time: elapsed time t [s]
        :returns: velocity v at time t [m/s]
        """
        return initial_velocity + acceleration * time

    def velocity_from_distance(self, *, initial_velocity, acceleration, distance):
        """Velocity after travelling a distance: v^2 = v0^2 + 2*a*d.

        Useful when you know how far something moved but not how long it took.

        :param initial_velocity: starting velocity v0 [m/s]
        :param acceleration: constant acceleration a [m/s^2]
        :param distance: distance travelled d [m]
        :returns: final speed v [m/s] (always non-negative)
        """
        # max(..., 0.0) guards against tiny negative values from rounding.
        return math.sqrt(max(initial_velocity ** 2 + 2 * acceleration * distance, 0.0))

    def projectile_range(self, *, speed, angle_deg, gravity=GRAVITY):
        """Horizontal range of a projectile launched over flat ground.

        R = v^2 * sin(2*theta) / g.

        :param speed: launch speed [m/s]
        :param angle_deg: launch angle above horizontal [degrees]
        :param gravity: gravitational acceleration [m/s^2], defaults to Earth
        :returns: horizontal range [m]
        """
        # Trig functions in ``math`` expect radians, so convert first.
        angle_rad = math.radians(angle_deg)
        return speed ** 2 * math.sin(2 * angle_rad) / gravity

    def projectile_time_of_flight(self, *, speed, angle_deg, gravity=GRAVITY):
        """Time a projectile spends in the air over flat ground.

        t = 2 * v * sin(theta) / g.

        :param speed: launch speed [m/s]
        :param angle_deg: launch angle above horizontal [degrees]
        :param gravity: gravitational acceleration [m/s^2]
        :returns: time of flight [s]
        """
        angle_rad = math.radians(angle_deg)
        return 2 * speed * math.sin(angle_rad) / gravity

    def newtons_second_law(self, *, mass, acceleration):
        """Net force from Newton's second law: F = m*a.

        :param mass: mass [kg]
        :param acceleration: acceleration [m/s^2]
        :returns: force [N]
        """
        return mass * acceleration

    def kinetic_energy(self, *, mass, velocity):
        """Translational kinetic energy: KE = 1/2 * m * v^2.

        :param mass: mass [kg]
        :param velocity: speed [m/s]
        :returns: kinetic energy [J]
        """
        return 0.5 * mass * velocity ** 2

    def momentum(self, *, mass, velocity):
        """Linear momentum: p = m*v.

        :param mass: mass [kg]
        :param velocity: velocity [m/s]
        :returns: momentum [kg*m/s]
        """
        return mass * velocity

    def centripetal_acceleration(self, *, speed, radius):
        """Centripetal acceleration for circular motion: a = v^2 / r.

        :param speed: tangential speed [m/s]
        :param radius: radius of the circular path [m]
        :returns: centripetal acceleration [m/s^2]
        """
        return speed ** 2 / radius

    def simulate_projectile_drag(
        self, *, speed, angle_deg, mass, drag_coefficient, frontal_area,
        air_density=1.225, gravity=GRAVITY, max_time=60.0,
    ):
        """Simulate 2-D projectile flight WITH quadratic air drag.

        Without drag, ``projectile_range`` has a tidy formula. Add air
        resistance - drag force = 1/2 * rho * Cd * A * v^2 opposing the motion -
        and the equations couple the x and y motion in a way no formula solves.
        This is exactly what ``scipy.integrate.solve_ivp`` is for: give it the
        derivatives, the start state, and a time span, and it marches the system
        forward adaptively.

        We also attach an *event* so the integration stops the instant the
        projectile returns to the ground (y crosses zero going down).

        :param speed: launch speed [m/s]
        :param angle_deg: launch angle above horizontal [degrees]
        :param mass: projectile mass [kg]
        :param drag_coefficient: dimensionless drag coefficient Cd [-]
        :param frontal_area: cross-sectional area facing the flow [m^2]
        :param air_density: air density rho [kg/m^3], defaults to sea level
        :param gravity: gravitational acceleration [m/s^2]
        :param max_time: safety cap on simulated time [s]
        :returns: tuple of numpy arrays (time [s], x [m], y [m]) ending at impact
        """
        # Resolve the launch velocity into horizontal and vertical parts.
        angle_rad = math.radians(angle_deg)
        vx0 = speed * math.cos(angle_rad)
        vy0 = speed * math.sin(angle_rad)

        # Lump the drag constants together: F_drag = drag_k * v^2.
        drag_k = 0.5 * air_density * drag_coefficient * frontal_area

        def equations_of_motion(t, state):
            """Return d/dt of [x, y, vx, vy] - what solve_ivp integrates."""
            x, y, vx, vy = state
            speed_now = math.hypot(vx, vy)
            # Drag acceleration opposes the velocity vector; gravity pulls -y.
            ax = -(drag_k / mass) * speed_now * vx
            ay = -gravity - (drag_k / mass) * speed_now * vy
            return [vx, vy, ax, ay]

        def hit_ground(t, state):
            """Event function: zero when the height y returns to ground level."""
            return state[1]

        # terminal=True stops the solver at the event; direction=-1 means only
        # trigger when y is decreasing (landing, not launch).
        hit_ground.terminal = True
        hit_ground.direction = -1

        solution = solve_ivp(
            equations_of_motion,
            t_span=(0.0, max_time),
            y0=[0.0, 0.0, vx0, vy0],
            events=hit_ground,
            max_step=0.01,          # small steps keep the trajectory smooth
            dense_output=False,
        )

        # solution.y rows are [x, y, vx, vy]; return the parts a caller wants.
        return solution.t, solution.y[0], solution.y[1]
