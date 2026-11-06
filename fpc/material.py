# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""material.py - material science and strength of materials.

This class covers how materials deform and fail under load: Hooke's law, the
stress-strain relationship, beam bending, thermal expansion, and column
buckling. These are the calculations that decide whether a part is stiff
enough, strong enough, and stable enough.
"""

import math


class Material:
    """Strength-of-materials and material-property calculations."""

    def stress(self, *, force, area):
        """Engineering stress: sigma = F / A.

        :param force: applied axial force [N]
        :param area: original cross-sectional area [m^2]
        :returns: stress [Pa]
        """
        return force / area

    def strain(self, *, change_in_length, original_length):
        """Engineering strain: epsilon = dL / L0 (dimensionless).

        :param change_in_length: change in length dL [m]
        :param original_length: original length L0 [m]
        :returns: strain [-]
        """
        return change_in_length / original_length

    def youngs_modulus(self, *, stress, strain):
        """Young's modulus (stiffness) from Hooke's law: E = sigma / strain.

        :param stress: applied stress [Pa]
        :param strain: resulting strain [-]
        :returns: Young's modulus [Pa]
        """
        return stress / strain

    def axial_deformation(self, *, force, length, area, modulus):
        """Axial stretch/compression of a bar: dL = F*L / (A*E).

        :param force: axial force [N]
        :param length: original length L [m]
        :param area: cross-sectional area A [m^2]
        :param modulus: Young's modulus E [Pa]
        :returns: change in length [m]
        """
        return force * length / (area * modulus)

    def bending_stress(self, *, moment, distance, moment_of_inertia):
        """Bending (flexural) stress in a beam: sigma = M*c / I.

        :param moment: bending moment M [N*m]
        :param distance: distance from neutral axis to the fibre c [m]
        :param moment_of_inertia: second moment of area I [m^4]
        :returns: bending stress [Pa]
        """
        return moment * distance / moment_of_inertia

    def thermal_expansion(self, *, coefficient, original_length, delta_temperature):
        """Length change from temperature: dL = alpha * L0 * dT.

        :param coefficient: linear expansion coefficient alpha [1/K]
        :param original_length: original length L0 [m]
        :param delta_temperature: temperature change dT [K]
        :returns: change in length [m]
        """
        return coefficient * original_length * delta_temperature

    def euler_buckling_load(self, *, modulus, moment_of_inertia, length, end_factor=1.0):
        """Critical buckling load of a slender column (Euler's formula).

        P_cr = pi^2 * E * I / (K*L)^2.

        :param modulus: Young's modulus E [Pa]
        :param moment_of_inertia: smallest second moment of area I [m^4]
        :param length: unsupported column length L [m]
        :param end_factor: effective-length factor K (1.0 pinned-pinned,
            0.5 fixed-fixed, 2.0 fixed-free), defaults to pinned-pinned
        :returns: critical axial load [N]
        """
        effective_length = end_factor * length
        return math.pi ** 2 * modulus * moment_of_inertia / effective_length ** 2
