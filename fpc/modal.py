# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""modal.py - classical vibration and modal analysis.

Vibration analysis predicts how structures and machines oscillate. These
helpers cover the single-degree-of-freedom (SDOF) spring-mass-damper - the
building block of all vibration theory - plus a multi-DOF eigenvalue solver
that finds natural frequencies and mode shapes using numpy's linear algebra.

It also pairs two SciPy workhorses: ``solve_ivp`` to SIMULATE a damped
oscillator's ring-down, and ``curve_fit`` to do the inverse - recover the
natural frequency and damping ratio FROM measured response data.
"""

import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit


class Modal:
    """Vibration and modal-analysis calculations."""

    def natural_frequency(self, *, stiffness, mass):
        """Undamped natural frequency of an SDOF system.

        Returns both the angular frequency omega_n = sqrt(k/m) [rad/s] and the
        ordinary frequency f_n = omega_n / (2*pi) [Hz], because engineers quote
        both.

        :param stiffness: spring stiffness k [N/m]
        :param mass: mass m [kg]
        :returns: tuple (omega_n [rad/s], f_n [Hz])
        """
        omega_n = math.sqrt(stiffness / mass)
        f_n = omega_n / (2 * math.pi)
        return omega_n, f_n

    def damping_ratio(self, *, damping, mass, stiffness):
        """Dimensionless damping ratio zeta = c / (2*sqrt(k*m)).

        zeta < 1 underdamped (oscillates), = 1 critically damped, > 1 overdamped.

        :param damping: viscous damping coefficient c [N*s/m]
        :param mass: mass m [kg]
        :param stiffness: stiffness k [N/m]
        :returns: damping ratio zeta [-]
        """
        critical_damping = 2 * math.sqrt(stiffness * mass)
        return damping / critical_damping

    def damped_natural_frequency(self, *, stiffness, mass, damping):
        """Damped natural frequency omega_d = omega_n * sqrt(1 - zeta^2).

        This is the frequency a real (lightly damped) system actually rings at.

        :param stiffness: stiffness k [N/m]
        :param mass: mass m [kg]
        :param damping: damping coefficient c [N*s/m]
        :returns: damped angular frequency [rad/s]
        """
        omega_n, _ = self.natural_frequency(stiffness=stiffness, mass=mass)
        zeta = self.damping_ratio(damping=damping, mass=mass, stiffness=stiffness)
        return omega_n * math.sqrt(1 - zeta ** 2)

    def mode_shapes(self, *, mass_matrix, stiffness_matrix):
        """Natural frequencies and mode shapes of a multi-DOF system.

        Solves the generalized eigenvalue problem  K*phi = omega^2 * M*phi.
        Each eigenvalue is omega^2; each eigenvector is a mode shape describing
        the relative motion of every degree of freedom at that frequency.

        :param mass_matrix: mass matrix M, shape (n, n) [kg]
        :param stiffness_matrix: stiffness matrix K, shape (n, n) [N/m]
        :returns: tuple (natural_frequencies [Hz] sorted ascending,
                  mode_shapes as columns of an array)
        """
        # Convert inputs to numpy arrays so this works with plain Python lists.
        M = np.asarray(mass_matrix, dtype=float)
        K = np.asarray(stiffness_matrix, dtype=float)

        # M^-1 * K turns the generalized problem into a standard eigenproblem.
        eigenvalues, eigenvectors = np.linalg.eig(np.linalg.solve(M, K))

        # Eigenvalues are omega^2; take the root and convert rad/s -> Hz.
        omega = np.sqrt(np.abs(eigenvalues))
        frequencies_hz = omega / (2 * math.pi)

        # Sort modes from lowest to highest frequency for a tidy result.
        order = np.argsort(frequencies_hz)
        return frequencies_hz[order], eigenvectors[:, order]

    def simulate_free_vibration(
        self, *, mass, stiffness, damping, initial_displacement,
        initial_velocity=0.0, duration, num_points=500,
    ):
        """Simulate the free ring-down of an SDOF spring-mass-damper.

        Integrates  m*x'' + c*x' + k*x = 0  with ``scipy.integrate.solve_ivp``.
        We rewrite the second-order equation as two first-order ones using the
        state [x, v] (position and velocity), which is the standard trick for
        feeding any ODE to a numerical solver.

        :param mass: mass m [kg]
        :param stiffness: stiffness k [N/m]
        :param damping: damping coefficient c [N*s/m]
        :param initial_displacement: starting position x(0) [m]
        :param initial_velocity: starting velocity x'(0) [m/s], defaults to 0
        :param duration: how long to simulate [s]
        :param num_points: number of evenly spaced output samples
        :returns: tuple of numpy arrays (time [s], displacement [m])
        """
        def equations_of_motion(t, state):
            """d/dt of [x, v] for  x' = v,  v' = -(c*v + k*x)/m."""
            x, v = state
            acceleration = -(damping * v + stiffness * x) / mass
            return [v, acceleration]

        # Ask the solver to report the answer at these evenly spaced times.
        time = np.linspace(0.0, duration, num_points)
        solution = solve_ivp(
            equations_of_motion,
            t_span=(0.0, duration),
            y0=[initial_displacement, initial_velocity],
            t_eval=time,
        )
        # Row 0 of solution.y is displacement; row 1 is velocity.
        return solution.t, solution.y[0]

    def fit_damped_response(self, *, time, displacement, guess_frequency_hz=1.0):
        """Recover natural frequency and damping ratio from measured ring-down.

        Given (time, displacement) samples of a decaying oscillation - say from
        an accelerometer - fit the underdamped free-vibration model

            x(t) = A * exp(-zeta*omega_n*t) * cos(omega_d*t + phi)

        where omega_d = omega_n*sqrt(1 - zeta^2). ``scipy.optimize.curve_fit``
        adjusts the four parameters (A, zeta, omega_n, phi) to best match the
        data. This is the inverse of :meth:`simulate_free_vibration`, so feeding
        it that method's output should return the parameters you started with.

        :param time: sample times [s] (1-D array-like)
        :param displacement: measured displacement at each time [m]
        :param guess_frequency_hz: rough starting guess for the frequency [Hz],
            which helps curve_fit converge
        :returns: dict with ``amplitude``, ``damping_ratio``, ``natural_frequency_hz``
        """
        time = np.asarray(time, dtype=float)
        displacement = np.asarray(displacement, dtype=float)

        def model(t, amplitude, zeta, omega_n, phase):
            omega_d = omega_n * np.sqrt(1 - zeta ** 2)
            return amplitude * np.exp(-zeta * omega_n * t) * np.cos(omega_d * t + phase)

        # A good initial guess (p0) is what makes nonlinear fitting converge.
        initial_guess = [
            float(np.max(np.abs(displacement))),   # amplitude
            0.05,                                   # lightly damped
            2 * math.pi * guess_frequency_hz,       # angular frequency
            0.0,                                    # phase
        ]
        params, _covariance = curve_fit(model, time, displacement, p0=initial_guess)
        amplitude, zeta, omega_n, _phase = params

        # The fit can return negative amplitude/zeta/omega that describe the same
        # curve; take magnitudes so the reported physics is unambiguous.
        return {
            "amplitude": abs(amplitude),
            "damping_ratio": abs(zeta),
            "natural_frequency_hz": abs(omega_n) / (2 * math.pi),
        }
