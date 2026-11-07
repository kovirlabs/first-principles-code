# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""material.py - material science and strength of materials.

This class covers how materials deform and fail under load: Hooke's law, the
stress-strain relationship, beam bending, thermal expansion, and column
buckling (Euler for long columns, the Johnson parabola for intermediate
ones, and a method that picks between them). These are the calculations that
decide whether a part is stiff enough, strong enough, and stable enough.
"""

import math


class Material:
    """Strength-of-materials and material-property calculations."""

    def stress(self, *, force: float, area: float) -> float:
        """Engineering stress: sigma = F / A.

        :param force: applied axial force [N]
        :param area: original cross-sectional area [m^2]
        :returns: stress [Pa]
        """
        return force / area

    def strain(self, *, change_in_length: float, original_length: float) -> float:
        """Engineering strain: epsilon = dL / L0 (dimensionless).

        :param change_in_length: change in length dL [m]
        :param original_length: original length L0 [m]
        :returns: strain [-]
        """
        return change_in_length / original_length

    def youngs_modulus(self, *, stress: float, strain: float) -> float:
        """Young's modulus (stiffness) from Hooke's law: E = sigma / strain.

        :param stress: applied stress [Pa]
        :param strain: resulting strain [-]
        :returns: Young's modulus [Pa]
        """
        return stress / strain

    def axial_deformation(
        self, *, force: float, length: float, area: float, modulus: float
    ) -> float:
        """Axial stretch/compression of a bar: dL = F*L / (A*E).

        :param force: axial force [N]
        :param length: original length L [m]
        :param area: cross-sectional area A [m^2]
        :param modulus: Young's modulus E [Pa]
        :returns: change in length [m]
        """
        return force * length / (area * modulus)

    def bending_stress(self, *, moment: float, distance: float, moment_of_inertia: float) -> float:
        """Bending (flexural) stress in a beam: sigma = M*c / I.

        :param moment: bending moment M [N*m]
        :param distance: distance from neutral axis to the fibre c [m]
        :param moment_of_inertia: second moment of area I [m^4]
        :returns: bending stress [Pa]
        """
        return moment * distance / moment_of_inertia

    def thermal_expansion(
        self, *, coefficient: float, original_length: float, delta_temperature: float
    ) -> float:
        """Length change from temperature: dL = alpha * L0 * dT.

        :param coefficient: linear expansion coefficient alpha [1/K]
        :param original_length: original length L0 [m]
        :param delta_temperature: temperature change dT [K]
        :returns: change in length [m]
        """
        return coefficient * original_length * delta_temperature

    def euler_buckling_load(
        self,
        *,
        modulus: float,
        moment_of_inertia: float,
        length: float,
        end_factor: float = 1.0,
    ) -> float:
        """Critical buckling load of a slender column (Euler's formula).

        P_cr = pi^2 * E * I / (K*L)^2.

        Only valid while the column stays elastic, i.e. for slenderness
        ratios KL/r above ``transition_slenderness_ratio``. For shorter
        columns use ``johnson_buckling_load``, or let
        ``critical_buckling_load`` choose.

        :param modulus: Young's modulus E [Pa]
        :param moment_of_inertia: smallest second moment of area I [m^4]
        :param length: unsupported column length L [m]
        :param end_factor: effective-length factor K (1.0 pinned-pinned,
            0.5 fixed-fixed, 2.0 fixed-free), defaults to pinned-pinned [-]
        :returns: critical axial load [N]
        """
        effective_length = end_factor * length
        return math.pi**2 * modulus * moment_of_inertia / effective_length**2

    # --- Column buckling beyond Euler ---------------------------------------
    #
    # Euler's formula assumes the column stays elastic right up to buckling.
    # For a short or medium column the Euler stress P/A would exceed the
    # yield strength, so the column yields (or buckles inelastically) first.
    # The J. B. Johnson parabola covers that "intermediate" range, and the
    # slenderness ratio KL/r decides which formula applies (Shigley's
    # Mechanical Engineering Design, 10th ed., Ch. 4, "Columns with Central
    # Loading" and "Intermediate-Length Columns with Central Loading").
    # These live here, beside Euler, because they are one topic: the
    # automatic chooser below calls both formulas.

    def radius_of_gyration(self, *, moment_of_inertia: float, area: float) -> float:
        """Radius of gyration r = sqrt(I / A).

        The distance from the axis at which the whole area, concentrated in
        a thin ring, would have the same second moment I. Use the *smallest*
        I of the section: a column buckles about its weakest axis.

        :param moment_of_inertia: smallest second moment of area I [m^4]
        :param area: cross-sectional area A [m^2]
        :returns: radius of gyration r [m]
        :raises ValueError: if I or A is not positive
        """
        if moment_of_inertia <= 0 or area <= 0:
            raise ValueError("moment_of_inertia and area must be positive")
        return math.sqrt(moment_of_inertia / area)

    def slenderness_ratio(
        self, *, length: float, radius_of_gyration: float, end_factor: float = 1.0
    ) -> float:
        """Slenderness ratio of a column: KL / r.

        One number that captures how prone a column is to buckling: long,
        thin columns (large KL/r) buckle elastically; stubby ones simply
        crush or yield.

        :param length: unsupported column length L [m]
        :param radius_of_gyration: least radius of gyration r [m]
        :param end_factor: effective-length factor K (1.0 pinned-pinned,
            0.5 fixed-fixed, 2.0 fixed-free) [-]
        :returns: slenderness ratio KL/r [-]
        :raises ValueError: for non-positive inputs
        """
        if length <= 0 or radius_of_gyration <= 0 or end_factor <= 0:
            raise ValueError("length, radius_of_gyration and end_factor must be positive")
        return end_factor * length / radius_of_gyration

    def transition_slenderness_ratio(self, *, modulus: float, yield_strength: float) -> float:
        """Slenderness ratio where Euler hands over to Johnson: sqrt(2*pi^2*E / Sy).

        At this KL/r the Euler critical stress pi^2*E/(KL/r)^2 equals Sy/2,
        and the Johnson parabola is built to meet Euler there with the same
        value and slope. Columns more slender than this are "long" (Euler);
        less slender ones are "intermediate" (Johnson). For structural steel
        (E = 200 GPa, Sy = 250 MPa) it is about 126.

        :param modulus: Young's modulus E [Pa]
        :param yield_strength: yield strength Sy [Pa]
        :returns: transition slenderness ratio (KL/r)_1 [-]
        :raises ValueError: if E or Sy is not positive
        """
        if modulus <= 0 or yield_strength <= 0:
            raise ValueError("modulus and yield_strength must be positive")
        return math.sqrt(2 * math.pi**2 * modulus / yield_strength)

    def johnson_buckling_load(
        self,
        *,
        modulus: float,
        moment_of_inertia: float,
        area: float,
        length: float,
        yield_strength: float,
        end_factor: float = 1.0,
    ) -> float:
        """Critical load of an intermediate column (J. B. Johnson parabola).

            P_cr = A * [ Sy - (Sy * (KL/r) / (2*pi))^2 / E ]

        A parabola in KL/r that starts at the yield load A*Sy for a zero-
        length column and meets the Euler curve tangentially at the
        transition slenderness ratio. Only valid for KL/r up to that ratio;
        ``critical_buckling_load`` picks the right formula for you.

        :param modulus: Young's modulus E [Pa]
        :param moment_of_inertia: smallest second moment of area I [m^4]
        :param area: cross-sectional area A [m^2]
        :param length: unsupported column length L [m]
        :param yield_strength: yield strength Sy [Pa]
        :param end_factor: effective-length factor K, defaults to pinned-pinned [-]
        :returns: critical axial load [N]
        :raises ValueError: for non-positive inputs
        """
        if modulus <= 0 or yield_strength <= 0:
            raise ValueError("modulus and yield_strength must be positive")
        r = self.radius_of_gyration(moment_of_inertia=moment_of_inertia, area=area)
        slenderness = self.slenderness_ratio(
            length=length, radius_of_gyration=r, end_factor=end_factor
        )
        reduction = (yield_strength * slenderness / (2 * math.pi)) ** 2 / modulus
        return area * (yield_strength - reduction)

    def critical_buckling_load(
        self,
        *,
        modulus: float,
        moment_of_inertia: float,
        area: float,
        length: float,
        yield_strength: float,
        end_factor: float = 1.0,
    ) -> dict[str, float | str]:
        """Critical column load, choosing Euler or Johnson from the slenderness ratio.

        Computes KL/r and the transition ratio sqrt(2*pi^2*E/Sy), then uses
        Euler for long columns (KL/r >= transition) and Johnson for
        intermediate ones. The two formulas give the same load at the
        transition (A*Sy/2), so the answer is continuous. Divide the result
        by your design factor to get an allowable load.

        :param modulus: Young's modulus E [Pa]
        :param moment_of_inertia: smallest second moment of area I [m^4]
        :param area: cross-sectional area A [m^2]
        :param length: unsupported column length L [m]
        :param yield_strength: yield strength Sy [Pa]
        :param end_factor: effective-length factor K, defaults to pinned-pinned [-]
        :returns: dict with ``critical_load`` [N], ``formula`` ("euler" or
            "johnson"), ``slenderness_ratio`` [-] and
            ``transition_slenderness_ratio`` [-]
        :raises ValueError: for non-positive inputs
        """
        r = self.radius_of_gyration(moment_of_inertia=moment_of_inertia, area=area)
        slenderness = self.slenderness_ratio(
            length=length, radius_of_gyration=r, end_factor=end_factor
        )
        transition = self.transition_slenderness_ratio(
            modulus=modulus, yield_strength=yield_strength
        )
        if slenderness >= transition:
            formula = "euler"
            load = self.euler_buckling_load(
                modulus=modulus,
                moment_of_inertia=moment_of_inertia,
                length=length,
                end_factor=end_factor,
            )
        else:
            formula = "johnson"
            load = self.johnson_buckling_load(
                modulus=modulus,
                moment_of_inertia=moment_of_inertia,
                area=area,
                length=length,
                yield_strength=yield_strength,
                end_factor=end_factor,
            )
        return {
            "critical_load": load,
            "formula": formula,
            "slenderness_ratio": slenderness,
            "transition_slenderness_ratio": transition,
        }
