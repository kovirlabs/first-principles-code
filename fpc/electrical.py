# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""electrical.py - electrical engineering calculations.

Covers the fundamentals of circuits: Ohm's law, electrical power, series and
parallel resistance, the reactance of capacitors and inductors, and the time
constant of an RC circuit.
"""

import math


class Electrical:
    """Electrical engineering helpers."""

    def ohms_law_voltage(self, *, current, resistance):
        """Voltage from Ohm's law: V = I * R.

        :param current: current I [A]
        :param resistance: resistance R [ohm]
        :returns: voltage [V]
        """
        return current * resistance

    def power(self, *, voltage, current):
        """Electrical power: P = V * I.

        :param voltage: voltage V [V]
        :param current: current I [A]
        :returns: power [W]
        """
        return voltage * current

    def series_resistance(self, *, resistances):
        """Total resistance of resistors in series (they simply add).

        :param resistances: iterable of resistances [ohm]
        :returns: total series resistance [ohm]
        """
        return sum(resistances)

    def parallel_resistance(self, *, resistances):
        """Total resistance of resistors in parallel.

        1/R_total = sum(1/R_i). The result is always smaller than the smallest
        individual resistor.

        :param resistances: iterable of resistances [ohm]
        :returns: total parallel resistance [ohm]
        """
        # Sum the reciprocals (conductances), then invert.
        reciprocal_sum = sum(1.0 / r for r in resistances)
        return 1.0 / reciprocal_sum

    def capacitive_reactance(self, *, frequency, capacitance):
        """Reactance of a capacitor: Xc = 1 / (2*pi*f*C).

        Reactance is the AC equivalent of resistance; it falls as frequency rises.

        :param frequency: signal frequency f [Hz]
        :param capacitance: capacitance C [F]
        :returns: capacitive reactance [ohm]
        """
        return 1.0 / (2 * math.pi * frequency * capacitance)

    def inductive_reactance(self, *, frequency, inductance):
        """Reactance of an inductor: Xl = 2*pi*f*L.

        :param frequency: signal frequency f [Hz]
        :param inductance: inductance L [H]
        :returns: inductive reactance [ohm]
        """
        return 2 * math.pi * frequency * inductance

    def rc_time_constant(self, *, resistance, capacitance):
        """Time constant of an RC circuit: tau = R * C.

        After one tau the capacitor reaches ~63% of its final voltage; after
        ~5 tau it is essentially fully charged.

        :param resistance: resistance R [ohm]
        :param capacitance: capacitance C [F]
        :returns: time constant [s]
        """
        return resistance * capacitance
