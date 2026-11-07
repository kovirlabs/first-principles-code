# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""main.py - First Principles Code: displacement from acceleration & velocity.

This script is the "hello world" of engineering kinematics. It answers a
question every engineer meets early: *given how something accelerates, where
does it end up?*  We solve it three ways so you can see how Python replaces the
tools you might reach for in MATLAB or Maplesoft:

    1. The closed-form (analytical) equation of motion - pure ``math``.
    2. Numerical integration of a CONSTANT acceleration      - ``scipy``.
    3. Numerical integration of a TIME-VARYING acceleration  - ``scipy``.

The numerical approach is the payoff: once you can integrate a()->v()->x()
with code, you are no longer limited to problems that have a tidy formula.

Run it with:

    uv run main.py
"""

# --- Standard library -------------------------------------------------------
# ``math`` ships with Python and covers scalar math (sqrt, sin, pi, ...).

# --- Third-party scientific stack ------------------------------------------
# ``numpy`` gives us fast array math; ``scipy`` adds the heavy machinery -
# here we use its numerical integration routines. Both are installed via
# ``uv add numpy scipy`` and pinned in pyproject.toml.
# ``matplotlib`` turns result arrays into figures - the engineering deliverable.
# pyplot is its MATLAB-style interface; if no screen is available it quietly
# falls back to a file-only backend, so saving a PNG always works.
import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate

# --- Project library --------------------------------------------------------
# Our own dynamics helpers live in ./fpc. This is how you import a class
# you wrote yourself and reuse it across scripts.
from fpc.dynamics import Dynamics


def analytical_displacement(*, initial_position, initial_velocity, acceleration, time):
    """Return displacement under CONSTANT acceleration, the textbook way.

    Uses the kinematic equation  x = x0 + v0*t + 1/2*a*t^2.

    Note the ``*`` in the signature: every argument after it must be passed
    *by keyword* (e.g. ``acceleration=9.81``). We use this style throughout the
    project so call sites read like sentences - this is the "verbose variable
    passing" the README talks about.

    :param initial_position: starting position x0 [m]
    :param initial_velocity: starting velocity v0 [m/s]
    :param acceleration: constant acceleration a [m/s^2]
    :param time: elapsed time t [s]
    :returns: position x at time t [m]
    """
    return initial_position + initial_velocity * time + 0.5 * acceleration * time**2


def plot_motion(*, time, acceleration, velocity, position, save_path="displacement.png"):
    """Plot the acceleration -> velocity -> position cascade and save a figure.

    Three stacked subplots make the core idea visible: integrating acceleration
    gives velocity, and integrating velocity gives position. This is the kind of
    figure you would produce in MATLAB, done here with matplotlib.

    :param time: time array t [s]
    :param acceleration: acceleration array a(t) [m/s^2]
    :param velocity: velocity array v(t) [m/s]
    :param position: position array x(t) [m]
    :param save_path: file to write the figure to, defaults to displacement.png
    :returns: the path the figure was saved to
    """
    # One figure, three rows that share the same x-axis (time).
    figure, (ax_a, ax_v, ax_x) = plt.subplots(3, 1, sharex=True, figsize=(8, 7))

    ax_a.plot(time, acceleration, color="tab:red")
    ax_a.set_ylabel("a(t) [m/s$^2$]")
    ax_a.set_title("Integrating acceleration -> velocity -> position")

    ax_v.plot(time, velocity, color="tab:green")
    ax_v.set_ylabel("v(t) [m/s]")

    ax_x.plot(time, position, color="tab:blue")
    ax_x.set_ylabel("x(t) [m]")
    ax_x.set_xlabel("time [s]")

    # A light grid on every panel makes values easier to read off.
    for axis in (ax_a, ax_v, ax_x):
        axis.grid(True, alpha=0.3)

    figure.tight_layout()
    figure.savefig(save_path, dpi=120)
    plt.close(figure)  # free the figure's memory; we only needed the file
    return save_path


def main():
    """Run the three displacement demonstrations and print a comparison."""

    # ----------------------------------------------------------------------
    # Scenario: an object launched upward at 5 m/s, then pulled by gravity.
    # We use the sign convention "down is positive" so gravity is +9.81.
    # ----------------------------------------------------------------------
    x0 = 0.0  # initial position [m]
    v0 = 5.0  # initial velocity [m/s]
    g = 9.81  # gravitational acceleration [m/s^2]
    t_final = 3.0  # how long we observe [s]

    # === 1. Closed-form answer ===========================================
    # When acceleration is constant, a formula exists. This is our "truth"
    # that the numerical methods below should reproduce.
    x_exact = analytical_displacement(
        initial_position=x0,
        initial_velocity=v0,
        acceleration=g,
        time=t_final,
    )

    # === 2. Numerical integration of constant acceleration ===============
    # The fundamental relationships are:  v(t) = integral(a dt),
    # and  x(t) = integral(v dt).  scipy can do both for us.
    #
    # Build a fine time grid from 0 to t_final. More points -> more accuracy.
    t = np.linspace(0.0, t_final, num=1001)

    # Acceleration is the same value at every instant here.
    a_const = np.full_like(t, g)

    # Integrate acceleration to get velocity. ``cumulative_trapezoid`` returns
    # the running integral; ``initial=0`` makes the array start at 0 so we can
    # add our real starting velocity v0 afterward.
    v_from_a = v0 + integrate.cumulative_trapezoid(a_const, t, initial=0.0)

    # Integrate velocity to get position, then add the starting position.
    x_from_v = x0 + integrate.cumulative_trapezoid(v_from_a, t, initial=0.0)

    # The last element is the displacement at t_final.
    x_numeric_const = x_from_v[-1]

    # === 3. Numerical integration of TIME-VARYING acceleration ===========
    # Real systems rarely have constant acceleration. Suppose a thruster adds
    # a sinusoidal acceleration on top of gravity:  a(t) = g + 2*sin(t).
    # There is no clean schoolbook formula, but code does not care.
    a_varying = g + 2.0 * np.sin(t)
    v_varying = v0 + integrate.cumulative_trapezoid(a_varying, t, initial=0.0)
    x_varying = x0 + integrate.cumulative_trapezoid(v_varying, t, initial=0.0)
    x_numeric_varying = x_varying[-1]

    # === 4. Same answer via our own library class ========================
    # Everything above is reusable engineering math, so it belongs in a class.
    # Here we call the project's Dynamics helper to show the intended workflow.
    dyn = Dynamics()
    x_library = dyn.displacement_constant_acceleration(
        initial_position=x0,
        initial_velocity=v0,
        acceleration=g,
        time=t_final,
    )

    # ----------------------------------------------------------------------
    # Report. f-strings (the f"..." literals) format numbers inline;
    # the ``:10.4f`` means "10-wide field, 4 decimal places".
    # ----------------------------------------------------------------------
    print("Displacement of an object after 3.0 s")
    print("=" * 48)
    print(f"  x0 = {x0} m,  v0 = {v0} m/s,  a = g = {g} m/s^2\n")
    print(f"  1. Analytical formula        : {x_exact:10.4f} m")
    print(f"  2. scipy (constant a)        : {x_numeric_const:10.4f} m")
    print(f"  4. Dynamics library class    : {x_library:10.4f} m")
    print(f"     -> numerical vs exact err : {abs(x_numeric_const - x_exact):.2e} m\n")
    print(f"  3. scipy (a = g + 2*sin(t))  : {x_numeric_varying:10.4f} m")
    print("     (no simple closed form - this is why we integrate numerically)")

    # Visualize the time-varying case: plot how a, v, and x evolve together.
    figure_path = plot_motion(
        time=t,
        acceleration=a_varying,
        velocity=v_varying,
        position=x_varying,
    )
    print(f"\n  Saved motion plot to: {figure_path}")


# This guard means main() runs when you execute the file directly, but NOT
# when another module imports it. It is the standard Python entry-point idiom.
if __name__ == "__main__":
    main()
