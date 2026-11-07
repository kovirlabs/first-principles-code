# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""ultrasound.py - diagnostic ultrasound (sonography) physics.

An ultrasound scanner sends a short pulse into the body and times the echoes.
It assumes sound always travels at 1540 m/s in soft tissue - that single
assumption explains depth calculation, many artefacts, and the trade-off
between frequency, resolution, and penetration. Doppler adds blood-flow
velocity from the frequency shift of moving red cells.
"""

import math
from typing import Literal

# Names of the media in :attr:`Ultrasound.MEDIA`, as a ``Literal`` type so the
# accepted strings are part of the method signature itself.
Medium = Literal["air", "fat", "water", "soft_tissue", "liver", "muscle", "bone"]


class Ultrasound:
    """Pulse-echo, attenuation, and Doppler calculations for sonography."""

    # Speed of sound every scanner assumes for soft tissue [m/s].
    SOFT_TISSUE_SPEED = 1540.0

    # Typical acoustic properties: density [kg/m^3] and speed of sound [m/s].
    MEDIA = {
        "air": {"density": 1.2, "speed": 330.0},
        "fat": {"density": 925.0, "speed": 1450.0},
        "water": {"density": 1000.0, "speed": 1480.0},
        "soft_tissue": {"density": 1050.0, "speed": 1540.0},
        "liver": {"density": 1060.0, "speed": 1550.0},
        "muscle": {"density": 1075.0, "speed": 1580.0},
        "bone": {"density": 1900.0, "speed": 4080.0},
    }

    def wavelength(self, *, frequency_mhz: float, speed: float = SOFT_TISSUE_SPEED) -> float:
        """Wavelength  lambda = c / f.

        :param frequency_mhz: transducer frequency [MHz]
        :param speed: speed of sound [m/s] (default: soft tissue)
        :returns: wavelength [mm]  (5 MHz in soft tissue -> 0.308 mm)
        """
        # Work in SI (m/s divided by Hz gives metres), then convert m -> mm.
        return speed / (frequency_mhz * 1e6) * 1000.0

    def echo_depth(self, *, round_trip_time_us: float, speed: float = SOFT_TISSUE_SPEED) -> float:
        """Reflector depth from echo time:  d = c * t / 2.

        Divide by two because the pulse travels down AND back. This "13 us per
        cm" rule is hard-wired into every scanner.

        :param round_trip_time_us: time from pulse to echo [us]
        :param speed: speed of sound [m/s]
        :returns: depth [cm]
        """
        return speed * round_trip_time_us * 1e-6 / 2.0 * 100.0

    def acoustic_impedance(self, *, density: float, speed: float) -> float:
        """Acoustic impedance  Z = rho * c  [rayl = kg/(m^2*s)].

        :param density: density [kg/m^3]
        :param speed: speed of sound [m/s]
        :returns: impedance [rayl]
        """
        return density * speed

    def intensity_reflection_coefficient(self, *, impedance_1: float, impedance_2: float) -> float:
        """Fraction of intensity reflected at a boundary:  R = ((Z2-Z1)/(Z2+Z1))^2.

        Soft-tissue/soft-tissue boundaries reflect < 1% (good: the beam carries
        on to deeper structures). Tissue/air reflects ~99.9% - which is why we
        need coupling gel and why bowel gas blocks the view.

        :param impedance_1: Z of the first medium [rayl]
        :param impedance_2: Z of the second medium [rayl]
        :returns: reflected fraction R, 0..1 [-]
        """
        return ((impedance_2 - impedance_1) / (impedance_2 + impedance_1)) ** 2

    def reflection_between(self, *, medium_1: Medium, medium_2: Medium) -> float:
        """Reflection coefficient between two named media from :attr:`MEDIA`.

        A convenience wrapper that chains the two methods above - a small
        example of building higher-level helpers from simple ones.

        :param medium_1: name of the first medium, e.g. "soft_tissue"
        :param medium_2: name of the second medium, e.g. "air"
        :returns: reflected intensity fraction R, 0..1 [-]
        """
        z1 = self.acoustic_impedance(**self.MEDIA[medium_1])
        z2 = self.acoustic_impedance(**self.MEDIA[medium_2])
        return self.intensity_reflection_coefficient(impedance_1=z1, impedance_2=z2)

    def attenuation_db(
        self,
        *,
        frequency_mhz: float,
        path_length_cm: float,
        coefficient_db_per_cm_mhz: float = 0.5,
    ) -> float:
        """Total attenuation  A = alpha * f * L  [dB].

        Soft tissue loses ~0.5 dB per cm per MHz. Higher frequency gives better
        resolution but less penetration - the central trade-off when choosing
        a probe. For a pulse-echo, the path length is TWICE the depth.

        :param frequency_mhz: frequency [MHz]
        :param path_length_cm: distance travelled [cm]
        :param coefficient_db_per_cm_mhz: attenuation coefficient [dB/(cm*MHz)]
        :returns: attenuation [dB]
        """
        return coefficient_db_per_cm_mhz * frequency_mhz * path_length_cm

    def axial_resolution(
        self, *, frequency_mhz: float, cycles_per_pulse: int = 2, speed: float = SOFT_TISSUE_SPEED
    ) -> float:
        """Axial resolution = spatial pulse length / 2 = n * lambda / 2.

        Two reflectors along the beam closer than this blur into one echo.

        :param frequency_mhz: frequency [MHz]
        :param cycles_per_pulse: number of cycles in each pulse [-]
        :param speed: speed of sound [m/s]
        :returns: axial resolution [mm]
        """
        return cycles_per_pulse * self.wavelength(frequency_mhz=frequency_mhz, speed=speed) / 2.0

    def maximum_depth(
        self, *, pulse_repetition_frequency_hz: float, speed: float = SOFT_TISSUE_SPEED
    ) -> float:
        """Deepest unambiguous echo for a given PRF:  d_max = c / (2 * PRF).

        Each echo must return before the next pulse is fired, so imaging deeper
        forces a lower PRF (and lower frame rate).

        :param pulse_repetition_frequency_hz: PRF [Hz]
        :param speed: speed of sound [m/s]
        :returns: maximum depth [cm]
        """
        return speed / (2.0 * pulse_repetition_frequency_hz) * 100.0

    def doppler_shift(
        self,
        *,
        transmitted_frequency_mhz: float,
        velocity: float,
        angle_deg: float,
        speed: float = SOFT_TISSUE_SPEED,
    ) -> float:
        """Doppler frequency shift  df = 2 * f0 * v * cos(theta) / c.

        :param transmitted_frequency_mhz: transmitted frequency f0 [MHz]
        :param velocity: reflector (blood) speed [m/s]
        :param angle_deg: angle between beam and flow [degrees]
        :param speed: speed of sound [m/s]
        :returns: Doppler shift [Hz]  (conveniently in the audible range)
        """
        f0_hz = transmitted_frequency_mhz * 1e6
        return 2.0 * f0_hz * velocity * math.cos(math.radians(angle_deg)) / speed

    def doppler_velocity(
        self,
        *,
        transmitted_frequency_mhz: float,
        doppler_shift_hz: float,
        angle_deg: float,
        speed: float = SOFT_TISSUE_SPEED,
    ) -> float:
        """Blood velocity from a measured Doppler shift (the inverse problem).

        v = df * c / (2 * f0 * cos(theta)). Because cos(theta) sits in the
        denominator, angle errors explode near 90 deg - keep the insonation
        angle at or below 60 deg in clinical practice.

        :param transmitted_frequency_mhz: f0 [MHz]
        :param doppler_shift_hz: measured shift [Hz]
        :param angle_deg: insonation angle [degrees]
        :param speed: speed of sound [m/s]
        :returns: velocity [m/s]
        """
        cosine = math.cos(math.radians(angle_deg))
        if abs(cosine) < 1e-6:
            raise ValueError("at 90 degrees there is no Doppler shift to measure")
        return doppler_shift_hz * speed / (2.0 * transmitted_frequency_mhz * 1e6 * cosine)
