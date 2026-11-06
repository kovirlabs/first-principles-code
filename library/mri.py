# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""mri.py - magnetic resonance imaging signal physics.

MRI contrast comes from how fast hydrogen nuclei (protons) recover after an RF
pulse: T1 is longitudinal recovery, T2 is transverse decay. By choosing the
repetition time (TR) and echo time (TE) the operator decides which of these
differences dominates the image - T1-weighted, T2-weighted, or proton-density
(PD) weighted. These methods let you compute that contrast instead of just
memorizing "fat is bright on T1".
"""

import math


class MRI:
    """MRI precession, relaxation, and spin-echo contrast calculations."""

    # Gyromagnetic ratio over 2*pi, in MHz per tesla.
    GYROMAGNETIC_RATIO_MHZ_PER_T = {
        "1H": 42.577,
        "13C": 10.708,
        "19F": 40.078,
        "23Na": 11.262,
        "31P": 17.235,
    }

    # Approximate relaxation times at 1.5 T in milliseconds (T1, T2), plus a
    # relative proton density. Literature values vary by +/- 20% or more with
    # field strength and measurement method - use them to compare tissues,
    # not as reference standards.
    TISSUE_PROPERTIES_1_5T = {
        "fat": {"t1": 260, "t2": 80, "proton_density": 0.9},
        "white_matter": {"t1": 790, "t2": 90, "proton_density": 0.7},
        "grey_matter": {"t1": 920, "t2": 100, "proton_density": 0.8},
        "csf": {"t1": 4000, "t2": 2000, "proton_density": 1.0},
        "muscle": {"t1": 870, "t2": 50, "proton_density": 0.75},
        "liver": {"t1": 500, "t2": 40, "proton_density": 0.7},
    }

    def larmor_frequency(self, *, field_strength_t, nucleus="1H"):
        """Precession (Larmor) frequency  f = gamma_bar * B0.

        The RF coil must transmit and receive at exactly this frequency; the
        scanner's gradients make it vary with position, which is how MRI knows
        WHERE the signal came from.

        :param field_strength_t: main magnetic field B0 [T]
        :param nucleus: key of :attr:`GYROMAGNETIC_RATIO_MHZ_PER_T`
        :returns: frequency [MHz]  (1H at 1.5 T -> ~63.9 MHz)
        """
        if nucleus not in self.GYROMAGNETIC_RATIO_MHZ_PER_T:
            raise ValueError(f"unknown nucleus {nucleus!r}")
        return self.GYROMAGNETIC_RATIO_MHZ_PER_T[nucleus] * field_strength_t

    def t1_recovery(self, *, time_ms, t1_ms, equilibrium_magnetization=1.0):
        """Longitudinal recovery after a 90 deg pulse:  Mz = M0 * (1 - exp(-t/T1)).

        After one T1, magnetization is back to ~63% of equilibrium.

        :param time_ms: time since the 90 deg pulse [ms]
        :param t1_ms: tissue T1 [ms]
        :param equilibrium_magnetization: M0 (defaults to 1, i.e. a fraction)
        :returns: Mz, same unit as M0
        """
        return equilibrium_magnetization * (1.0 - math.exp(-time_ms / t1_ms))

    def t2_decay(self, *, time_ms, t2_ms, initial_magnetization=1.0):
        """Transverse decay:  Mxy = M0 * exp(-t/T2).

        After one T2, only ~37% of the transverse signal remains.

        :param time_ms: time since excitation [ms]
        :param t2_ms: tissue T2 [ms]
        :param initial_magnetization: Mxy at t = 0 (defaults to 1)
        :returns: Mxy, same unit as the initial magnetization
        """
        return initial_magnetization * math.exp(-time_ms / t2_ms)

    def spin_echo_signal(self, *, repetition_time_ms, echo_time_ms, t1_ms=None, t2_ms=None,
                         proton_density=1.0, tissue=None):
        """Relative spin-echo signal  S = PD * (1 - exp(-TR/T1)) * exp(-TE/T2).

        TR controls how much T1 recovery happens between pulses; TE controls
        how much T2 decay happens before the echo is read. Pass explicit
        T1/T2/PD, or a ``tissue`` name from :attr:`TISSUE_PROPERTIES_1_5T`.

        :param repetition_time_ms: TR [ms]
        :param echo_time_ms: TE [ms]
        :param t1_ms: tissue T1 [ms]
        :param t2_ms: tissue T2 [ms]
        :param proton_density: relative proton density [-]
        :param tissue: optional tissue name that supplies T1, T2, and PD
        :returns: relative signal intensity [-]
        """
        if tissue is not None:
            props = self.TISSUE_PROPERTIES_1_5T[tissue]
            t1_ms, t2_ms, proton_density = props["t1"], props["t2"], props["proton_density"]
        if t1_ms is None or t2_ms is None:
            raise ValueError("give t1_ms and t2_ms, or a tissue name")
        recovered = 1.0 - math.exp(-repetition_time_ms / t1_ms)
        decayed = math.exp(-echo_time_ms / t2_ms)
        return proton_density * recovered * decayed

    def sequence_weighting(self, *, repetition_time_ms, echo_time_ms):
        """Classify a spin-echo TR/TE pair as T1-, T2-, or PD-weighted.

        Rule of thumb at 1.5 T:
            short TR (< 800 ms)  + short TE (< 30 ms) -> T1-weighted
            long TR (> 2000 ms)  + long TE  (> 80 ms) -> T2-weighted
            long TR              + short TE           -> PD-weighted

        :param repetition_time_ms: TR [ms]
        :param echo_time_ms: TE [ms]
        :returns: "T1-weighted", "T2-weighted", "PD-weighted", or "mixed"
        """
        short_tr = repetition_time_ms < 800
        long_tr = repetition_time_ms > 2000
        short_te = echo_time_ms < 30
        long_te = echo_time_ms > 80

        if short_tr and short_te:
            return "T1-weighted"
        if long_tr and long_te:
            return "T2-weighted"
        if long_tr and short_te:
            return "PD-weighted"
        # Short TR + long TE gives little signal and poor contrast; anything
        # in the in-between zone mixes several contrast mechanisms.
        return "mixed"
