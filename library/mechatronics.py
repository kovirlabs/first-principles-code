# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""mechatronics.py - mechatronics and motion-system calculations.

Mechatronics blends mechanical, electrical, and control engineering. These
helpers size the components of a motion system: ball screws (turning rotation
into linear travel), servo motors (torque, speed, and reflected inertia), and
the gearboxes between them.
"""

import math


class Mechatronics:
    """Motion-system sizing calculations: ball screws, servos, drives."""

    def ballscrew_linear_speed(self, *, motor_rpm, lead):
        """Linear speed of a ball-screw nut from motor speed.

        v = (rpm / 60) * lead.  Each revolution advances the nut by one lead.

        :param motor_rpm: screw rotational speed [rev/min]
        :param lead: screw lead - linear travel per revolution [mm]
        :returns: linear speed [mm/s]
        """
        revolutions_per_second = motor_rpm / 60.0
        return revolutions_per_second * lead

    def ballscrew_torque(self, *, thrust_force, lead, efficiency=0.9):
        """Motor torque needed to drive a thrust load through a ball screw.

        T = F * lead / (2*pi*eta).  The 2*pi converts linear lead to angular
        motion; efficiency accounts for friction in the screw.

        :param thrust_force: required axial thrust force [N]
        :param lead: screw lead [m] (note: metres here, not mm)
        :param efficiency: screw efficiency 0..1, defaults to 0.9
        :returns: required torque [N*m]
        """
        return thrust_force * lead / (2 * math.pi * efficiency)

    def motor_power(self, *, torque, speed_rpm):
        """Mechanical power from torque and rotational speed.

        P = T * omega, where omega = rpm * 2*pi / 60.

        :param torque: shaft torque [N*m]
        :param speed_rpm: shaft speed [rev/min]
        :returns: mechanical power [W]
        """
        angular_velocity = speed_rpm * 2 * math.pi / 60.0
        return torque * angular_velocity

    def reflected_inertia(self, *, load_inertia, gear_ratio):
        """Load inertia as the motor "sees" it through a gearbox.

        J_reflected = J_load / ratio^2.  A reduction dramatically shrinks the
        inertia the motor must accelerate - key to matching motor to load.

        :param load_inertia: inertia at the load [kg*m^2]
        :param gear_ratio: gear reduction ratio [-]
        :returns: reflected inertia at the motor shaft [kg*m^2]
        """
        return load_inertia / gear_ratio ** 2

    def acceleration_torque(self, *, inertia, angular_acceleration):
        """Torque to angularly accelerate an inertia: T = J * alpha.

        The rotational analogue of F = m*a.

        :param inertia: rotational inertia J [kg*m^2]
        :param angular_acceleration: angular acceleration alpha [rad/s^2]
        :returns: torque [N*m]
        """
        return inertia * angular_acceleration

    def calculate_inertia_ratio(self, *, j_motor, mass, pitch, teeth_motor_pulley, teeth_screw_pulley, j_screw, j_pulley_motor, j_pulley_screw):
        """
        Calculates the inertia ratio of a servomotor driving a ballscrew via a timing belt.

        :param j_motor: motor rotor inertia [kg*m^2]
        :param mass: linear mass [kg]
        :param pitch: ballscrew pitch [m/rev]
        :param teeth_motor_pulley: number of teeth on the motor pulley
        :param teeth_screw_pulley: number of teeth on the ballscrew pulley
        :param j_screw: ballscrew inertia [kg*m^2]
        :param j_pulley_motor: motor pulley inertia [kg*m^2]
        :param j_pulley_screw: ballscrew pulley inertia [kg*m^2]
        :returns: dictionary containing inertia ratio, total load inertia, and reduction ratio
        """
        # 1. Calculate the mechanical reduction ratio of the timing belt
        reduction_ratio = teeth_screw_pulley / teeth_motor_pulley

        # 2. Calculate the inertia of the linear mass reflected to the ballscrew shaft
        j_mass = mass * (pitch / (2 * math.pi)) ** 2

        # 3. Sum the inertias on the ballscrew shaft
        j_ballscrew_total = j_pulley_screw + j_screw + j_mass

        # 4. Reflect the ballscrew shaft inertia through the timing belt to the motor
        j_reflected_to_motor = self.reflected_inertia(
            load_inertia=j_ballscrew_total, gear_ratio=reduction_ratio
        )

        # 5. Add the motor pulley inertia to get the total load inertia
        j_load_total = j_pulley_motor + j_reflected_to_motor

        # 6. Calculate the inertia ratio
        inertia_ratio = j_load_total / j_motor

        return {
            "inertia_ratio": inertia_ratio,
            "j_load_total": j_load_total,
            "reduction_ratio": reduction_ratio,
        }

    def _calculate_acceleration_torque(self, *, j_total, j_motor, linear_acceleration, pitch, reduction_ratio):
        """
        Uses linear acceleration to find the required motor acceleration torque.

        :param j_total: total reflected load inertia [kg*m^2]
        :param j_motor: motor rotor inertia [kg*m^2]
        :param linear_acceleration: linear acceleration [m/s^2]
        :param pitch: ballscrew pitch [m/rev]
        :param reduction_ratio: mechanical reduction ratio
        :returns: required acceleration torque [N*m]
        """
        total_system_inertia = j_total + j_motor

        # Convert linear acceleration to angular acceleration at the ballscrew (rad/s^2)
        alpha_screw = linear_acceleration * (2 * math.pi / pitch)

        # Convert angular acceleration at the ballscrew to the motor shaft
        alpha_motor = alpha_screw * reduction_ratio

        # Calculate Required Torque (T = J * alpha)
        return self.acceleration_torque(
            inertia=total_system_inertia, angular_acceleration=alpha_motor
        )
