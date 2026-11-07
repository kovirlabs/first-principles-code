# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""design.py - turn "analyze this part" into "find the part that works".

Most library methods answer *analysis* questions: given a beam, how much does
it deflect? Real engineering usually asks the reverse *design* question: what
size beam deflects no more than 5 mm? This class shows the two SciPy tools
that answer design questions:

    * **Root finding** (``scipy.optimize.brentq``) - solve one equation for one
      unknown: "find h so that deflection(h) - limit = 0".
    * **Constrained optimization** (``scipy.optimize.minimize``) - choose
      several variables to minimize a goal (mass) while satisfying limits
      (stress, deflection) and staying inside bounds (sizes you can buy).

Both work on any function you can write in Python, so the same pattern scales
from a textbook beam to a full simulation.

All inputs are plain SI floats (m, N, Pa, kg/m^3). The beam is simply supported
with a central point load and a solid rectangular cross-section, matching
``fpc.Beam``.
"""

from typing import Any

import numpy as np
from scipy.optimize import brentq, minimize


class Design:
    """Design-by-calculation helpers: size and optimize simple parts."""

    # --- Formulas the design methods search over -------------------------
    @staticmethod
    def _deflection(
        *, load: float, length: float, modulus: float, width: float, height: float
    ) -> float:
        """Midspan deflection of a simply supported beam: P*L^3 / (48*E*I)."""
        moment_of_inertia = width * height**3 / 12
        return load * length**3 / (48 * modulus * moment_of_inertia)

    @staticmethod
    def _bending_stress(*, load: float, length: float, width: float, height: float) -> float:
        """Peak bending stress: M*c/I with M = P*L/4, c = h/2  ->  1.5*P*L/(b*h^2)."""
        return 1.5 * load * length / (width * height**2)

    # --- Root finding -----------------------------------------------------
    def rectangular_beam_height_for_deflection(
        self,
        *,
        load: float,
        length: float,
        modulus: float,
        width: float,
        max_deflection: float,
        min_height: float = 1e-3,
        max_height: float = 10.0,
    ) -> float:
        """Find the beam height that gives exactly the allowed deflection.

        We write the requirement as a function that is zero at the answer::

            residual(h) = deflection(h) - max_deflection

        A short beam deflects too much (residual > 0); a very tall one barely
        deflects (residual < 0). Because the sign changes between
        ``min_height`` and ``max_height``, ``brentq`` is guaranteed to find the
        crossing. (This particular equation *can* be solved by hand, which is
        exactly why it is a good first example - the test suite checks the
        numerical answer against the algebra.)

        :param load: central point load P [N]
        :param length: span L [m]
        :param modulus: Young's modulus E [Pa]
        :param width: section width b [m]
        :param max_deflection: allowed midspan deflection [m]
        :param min_height: lower end of the search bracket [m]
        :param max_height: upper end of the search bracket [m]
        :returns: the minimum section height h [m]
        :raises ValueError: if the answer is not inside the bracket
        """

        def residual(height: float) -> float:
            return (
                self._deflection(
                    load=load,
                    length=length,
                    modulus=modulus,
                    width=width,
                    height=height,
                )
                - max_deflection
            )

        if residual(min_height) * residual(max_height) > 0:
            raise ValueError("no sign change between min_height and max_height; widen the bracket")
        return float(brentq(residual, min_height, max_height, xtol=1e-12))

    # --- Constrained optimization ----------------------------------------
    def lightest_rectangular_beam(
        self,
        *,
        load: float,
        length: float,
        modulus: float,
        density: float,
        allowable_stress: float,
        max_deflection: float,
        width_bounds: tuple[float, float] = (0.01, 0.5),
        height_bounds: tuple[float, float] = (0.01, 1.0),
        max_aspect_ratio: float = 4.0,
    ) -> dict[str, Any]:
        """Find the lightest rectangular beam that is strong and stiff enough.

        Optimization problem (the vocabulary is worth learning):

        * **Design variables** x = [width b, height h].
        * **Objective** (minimize): mass = density * b * h * L.
        * **Constraints** (must hold): bending stress <= allowable_stress,
          deflection <= max_deflection, and height <= max_aspect_ratio * width.
          SciPy's convention is that each
          ``"ineq"`` constraint function must be **>= 0** when satisfied, so
          we write them as ``limit - actual``.
        * **Bounds**: the sizes you are willing to consider.

        SLSQP (Sequential Least SQuares Programming) is the SciPy method that
        handles bounds plus inequality constraints. We divide each constraint
        by its limit so both are "fractions of the limit" - optimizers behave
        far better when numbers are of similar size.

        Why the aspect-ratio limit? Without it the "best" beam is an infinitely
        thin, infinitely tall plank - mathematically optimal, physically
        useless (it would buckle sideways). Optimizers exploit every gap in
        your problem statement, so constraints must capture what you really
        mean. Constraints that end up exactly at their limit are reported as
        ``active``: those are the requirements that drive the design.

        :param load: central point load P [N]
        :param length: span L [m]
        :param modulus: Young's modulus E [Pa]
        :param density: material density [kg/m^3]
        :param allowable_stress: maximum allowed bending stress [Pa]
        :param max_deflection: maximum allowed midspan deflection [m]
        :param width_bounds: (min, max) section width [m]
        :param height_bounds: (min, max) section height [m]
        :param max_aspect_ratio: largest allowed height / width, defaults to 4
            (a common rule of thumb against lateral-torsional buckling) [-]
        :returns: dict with ``width`` [m], ``height`` [m], ``mass`` [kg],
            ``stress`` [Pa], ``deflection`` [m], and which constraints are
            ``active`` (list of names)
        :raises RuntimeError: if the optimizer fails to find a feasible design
        """

        def mass(x):
            width, height = x
            return density * width * height * length

        # Scale the objective to "about 1" by dividing by the starting mass.
        # Gradient-based optimizers converge far more reliably on well-scaled
        # numbers than on raw values that may be 1e-3 or 1e4.
        start = [np.mean(width_bounds), np.mean(height_bounds)]
        reference_mass = mass(start)

        def scaled_mass(x):
            return mass(x) / reference_mass

        def stress_margin(x):
            width, height = x
            stress = self._bending_stress(load=load, length=length, width=width, height=height)
            return 1 - stress / allowable_stress

        def deflection_margin(x):
            width, height = x
            deflection = self._deflection(
                load=load,
                length=length,
                modulus=modulus,
                width=width,
                height=height,
            )
            return 1 - deflection / max_deflection

        def aspect_margin(x):
            width, height = x
            return 1 - height / (max_aspect_ratio * width)

        # Start in the middle of the allowed box; the optimizer walks from here.
        result = minimize(
            scaled_mass,
            x0=start,
            method="SLSQP",
            bounds=[width_bounds, height_bounds],
            constraints=[
                {"type": "ineq", "fun": stress_margin},
                {"type": "ineq", "fun": deflection_margin},
                {"type": "ineq", "fun": aspect_margin},
            ],
            options={"ftol": 1e-12, "maxiter": 500},
        )
        # Always check .success - a "result" from a failed solve is garbage.
        if not result.success:
            raise RuntimeError(f"optimization failed: {result.message}")

        width, height = result.x
        active = [
            name
            for name, margin in (
                ("stress", stress_margin(result.x)),
                ("deflection", deflection_margin(result.x)),
                ("aspect_ratio", aspect_margin(result.x)),
            )
            if margin < 1e-4  # within 0.01% of the limit -> this limit governs
        ]
        return {
            "width": float(width),
            "height": float(height),
            "mass": float(mass(result.x)),
            "stress": float(
                self._bending_stress(load=load, length=length, width=width, height=height)
            ),
            "deflection": float(
                self._deflection(
                    load=load,
                    length=length,
                    modulus=modulus,
                    width=width,
                    height=height,
                )
            ),
            "active": active,
        }
