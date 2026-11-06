# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""gear.py - gear, gear-pair, and powertrain calculations.

Gears trade speed for torque (and back). These helpers cover the geometry of a
single gear, the ratio of a meshing pair, how speed and torque transform across
a ratio, and how to combine stages into an overall powertrain ratio.
"""

import math


class Gear:
    """Gear and powertrain calculations."""

    def pitch_diameter(self, *, teeth, module):
        """Pitch diameter of a spur gear (metric): d = module * teeth.

        The ``module`` (mm of pitch diameter per tooth) is the metric measure
        of tooth size; meshing gears must share the same module.

        :param teeth: number of teeth N [-]
        :param module: gear module m [mm]
        :returns: pitch diameter [mm]
        """
        return module * teeth

    def gear_ratio(self, *, driver_teeth, driven_teeth):
        """Gear ratio of a meshing pair: ratio = driven / driver.

        A ratio > 1 reduces speed and multiplies torque (a reduction).

        :param driver_teeth: teeth on the input (driving) gear [-]
        :param driven_teeth: teeth on the output (driven) gear [-]
        :returns: gear ratio [-]
        """
        return driven_teeth / driver_teeth

    def output_speed(self, *, input_speed, gear_ratio):
        """Output shaft speed after a ratio: n_out = n_in / ratio.

        :param input_speed: input speed (rpm or rad/s) [-]
        :param gear_ratio: gear ratio [-]
        :returns: output speed in the same units as input_speed
        """
        return input_speed / gear_ratio

    def output_torque(self, *, input_torque, gear_ratio, efficiency=1.0):
        """Output torque after a ratio: T_out = T_in * ratio * efficiency.

        :param input_torque: input torque [N*m]
        :param gear_ratio: gear ratio [-]
        :param efficiency: mechanical efficiency 0..1, defaults to ideal (1.0)
        :returns: output torque [N*m]
        """
        return input_torque * gear_ratio * efficiency

    def powertrain_ratio(self, *, stage_ratios):
        """Overall ratio of gear stages in series (the product of each ratio).

        :param stage_ratios: iterable of individual stage ratios [-]
        :returns: total powertrain ratio [-]
        """
        total = 1.0
        # Multiply every stage ratio together. ``math.prod`` would also work,
        # but the explicit loop makes the "ratios multiply in series" idea clear.
        for ratio in stage_ratios:
            total *= ratio
        return total

    def center_distance(self, *, module, driver_teeth, driven_teeth):
        """Center distance between two meshing spur gears.

        C = module * (N1 + N2) / 2.

        :param module: shared gear module m [mm]
        :param driver_teeth: teeth on gear 1 [-]
        :param driven_teeth: teeth on gear 2 [-]
        :returns: center-to-center distance [mm]
        """
        return module * (driver_teeth + driven_teeth) / 2
