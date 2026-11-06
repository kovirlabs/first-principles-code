# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""beam.py - a unit-aware Beam dataclass.

This module shows two ideas working together:

    * ``@dataclass`` models a real-world *thing* (a rectangular beam) as an
      object with named fields, instead of passing a fistful of loose floats to
      every function.
    * Pint quantities give every field and result physical units, so the math
      is self-checking and the answers come back in whatever unit you ask for.

Build one like this::

    from fpc.units import Q_
    from fpc.beam import Beam

    beam = Beam(
        length=Q_(2.0, "m"),
        width=Q_(50, "mm"),
        height=Q_(100, "mm"),
        modulus=Q_(200, "GPa"),
    )
    print(beam.moment_of_inertia.to("mm**4"))
    print(beam.max_deflection_point_load(load=Q_(5, "kN")).to("mm"))

The properties (area, moment of inertia, mass) are computed on demand from the
dimensions, so they always stay consistent with the beam's geometry.
"""

import math
from dataclasses import dataclass, field

from pint import Quantity

from fpc.units import Q_

# A sensible default material so a beam can be created with just its geometry.
STEEL_MODULUS = Q_(200, "GPa")  # Young's modulus of structural steel
STEEL_DENSITY = Q_(7850, "kg/m**3")  # density of structural steel


@dataclass
class Beam:
    """A straight beam with a rectangular cross-section, in physical units.

    :param length: span of the beam (a ``[length]`` quantity)
    :param width: cross-section width b (``[length]``)
    :param height: cross-section height h (``[length]``), measured in the
        direction the bending load is applied
    :param modulus: Young's modulus E (a ``[pressure]`` quantity),
        defaults to structural steel
    :param density: material density (``[mass]/[volume]``), defaults to steel
    """

    length: Quantity
    width: Quantity
    height: Quantity
    # ``field(default_factory=...)`` is how dataclasses give a default that is
    # an object rather than a literal - here, our default material properties.
    modulus: Quantity = field(default_factory=lambda: STEEL_MODULUS)
    density: Quantity = field(default_factory=lambda: STEEL_DENSITY)

    def __post_init__(self):
        """Validate units and signs right after the object is created.

        Catching a bad input here (e.g. a time passed where a length belongs,
        or a negative width) gives a clear error instead of a wrong number
        later on.
        """
        self._require(self.length, "[length]", "length")
        self._require(self.width, "[length]", "width")
        self._require(self.height, "[length]", "height")
        self._require(self.modulus, "[pressure]", "modulus")
        self._require(self.density, "[mass] / [length] ** 3", "density")

    @staticmethod
    def _require(quantity, dimensionality, name):
        """Raise a helpful error unless ``quantity`` is positive with the right units."""
        # ``.check()`` confirms the quantity has the expected dimensionality.
        if not hasattr(quantity, "check") or not quantity.check(dimensionality):
            raise ValueError(f"{name} must be a Pint quantity with dimensionality {dimensionality}")
        if quantity.magnitude <= 0:
            raise ValueError(f"{name} must be positive, got {quantity}")

    # --- Geometry (computed on demand) ------------------------------------
    @property
    def area(self):
        """Cross-sectional area A = width * height."""
        return self.width * self.height

    @property
    def moment_of_inertia(self):
        """Second moment of area about the bending (strong) axis: I = b*h^3/12.

        This is the property that resists bending; a taller section (bigger h)
        is dramatically stiffer because h is cubed.
        """
        return self.width * self.height**3 / 12

    @property
    def mass(self):
        """Total mass = density * volume = density * area * length."""
        return self.density * self.area * self.length

    # --- Structural behaviour ---------------------------------------------
    def max_deflection_point_load(self, *, load):
        """Maximum deflection of a simply supported beam with a central load.

        delta = P * L^3 / (48 * E * I).  The result carries length units, so
        call ``.to("mm")`` on it to read it off in millimetres.

        :param load: central point load P (a ``[force]`` quantity)
        :returns: maximum deflection (a ``[length]`` quantity)
        """
        self._require(load, "[force]", "load")
        deflection = load * self.length**3 / (48 * self.modulus * self.moment_of_inertia)
        # Reduce to base units so the result reads cleanly as metres.
        return deflection.to_base_units()

    def max_bending_stress_point_load(self, *, load):
        """Peak bending stress for a simply supported beam, central point load.

        The maximum bending moment is M = P*L/4 at midspan; the peak stress is
        sigma = M*c/I with c = h/2 (distance to the outer fibre).

        :param load: central point load P (a ``[force]`` quantity)
        :returns: maximum bending stress (a ``[pressure]`` quantity)
        """
        self._require(load, "[force]", "load")
        max_moment = load * self.length / 4
        distance_to_fibre = self.height / 2
        stress = max_moment * distance_to_fibre / self.moment_of_inertia
        return stress.to_base_units()

    def euler_buckling_load(self, *, end_factor=1.0):
        """Critical axial buckling load (Euler), about the weakest axis.

        P_cr = pi^2 * E * I_min / (K*L)^2.  A column buckles about whichever
        axis has the smaller second moment of area, so we use the minimum here.

        :param end_factor: effective-length factor K (1.0 pinned-pinned,
            0.5 fixed-fixed, 2.0 fixed-free), defaults to pinned-pinned
        :returns: critical axial load (a ``[force]`` quantity)
        """
        # Second moments about both axes; buckling follows the smaller one.
        inertia_strong = self.width * self.height**3 / 12
        inertia_weak = self.height * self.width**3 / 12
        inertia_min = min(inertia_strong, inertia_weak)

        effective_length = end_factor * self.length
        load = math.pi**2 * self.modulus * inertia_min / effective_length**2
        return load.to_base_units()
