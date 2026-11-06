# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""statics.py - equilibrium and load analysis for bodies at rest.

Statics is dynamics with everything standing still: the sum of forces and the
sum of moments are both zero. These helpers cover the calculations that show up
constantly in structural and machine design - reactions, moments, stress, and
friction.
"""

import math


class Statics:
    """Common statics calculations for bodies in equilibrium."""

    def moment(self, *, force, distance):
        """Moment (torque) of a force about a point: M = F * d.

        ``distance`` is the perpendicular distance (moment arm) from the pivot
        to the force's line of action.

        :param force: applied force [N]
        :param distance: perpendicular moment arm [m]
        :returns: moment [N*m]
        """
        return force * distance

    def resultant_2d(self, *, fx, fy):
        """Combine perpendicular force components into magnitude and direction.

        :param fx: force component along x [N]
        :param fy: force component along y [N]
        :returns: tuple (magnitude [N], angle [degrees] measured from +x axis)
        """
        magnitude = math.hypot(fx, fy)          # sqrt(fx^2 + fy^2)
        angle_deg = math.degrees(math.atan2(fy, fx))
        return magnitude, angle_deg

    def beam_reactions_point_load(self, *, span, load, load_position):
        """Support reactions for a simply supported beam with one point load.

        The beam rests on a pin at the left (A) and a roller at the right (B).
        Summing moments about each support gives the two vertical reactions.

        :param span: distance between supports L [m]
        :param load: downward point load P [N]
        :param load_position: distance of the load from support A [m]
        :returns: tuple (reaction at A [N], reaction at B [N])
        """
        # Sum of moments about A = 0  ->  R_B * L = P * a
        reaction_b = load * load_position / span
        # Sum of vertical forces = 0  ->  R_A + R_B = P
        reaction_a = load - reaction_b
        return reaction_a, reaction_b

    def axial_stress(self, *, force, area):
        """Normal (axial) stress: sigma = F / A.

        :param force: axial force [N]
        :param area: cross-sectional area [m^2]
        :returns: stress [Pa]
        """
        return force / area

    def factor_of_safety(self, *, strength, applied_stress):
        """Factor of safety: FoS = material strength / applied stress.

        A value above 1 means the part can carry more than it currently sees.

        :param strength: allowable or yield strength [Pa]
        :param applied_stress: actual working stress [Pa]
        :returns: dimensionless factor of safety
        """
        return strength / applied_stress

    def friction_force(self, *, coefficient, normal_force):
        """Maximum dry friction force: F = mu * N.

        :param coefficient: coefficient of friction mu [-]
        :param normal_force: normal (perpendicular) force N [N]
        :returns: maximum friction force [N]
        """
        return coefficient * normal_force
