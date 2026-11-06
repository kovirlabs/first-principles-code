# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""ct.py - computed tomography: Hounsfield units, windowing, and dose metrics.

A CT scanner measures linear attenuation coefficients; the Hounsfield scale
re-expresses them relative to water so that water = 0 HU and air = -1000 HU.
A CT image spans ~4000 HU, but a monitor shows ~256 grey levels and the eye
far fewer, so radiologists choose a WINDOW (a slice of the HU range) to
display. This module does both steps with NumPy, so it works on a single
number or on a whole 512 x 512 image in one call (vectorization).
"""

import numpy as np


class CT:
    """Computed-tomography image and dose calculations."""

    # Common window presets as (width, level) in HU. Values follow widely
    # taught defaults (e.g. Radiopaedia); departments tweak these locally.
    WINDOW_PRESETS = {
        "brain": (80, 40),
        "subdural": (200, 75),
        "stroke": (40, 40),
        "lung": (1500, -600),
        "mediastinum": (350, 50),
        "abdomen": (400, 50),
        "liver": (150, 30),
        "bone": (1800, 400),
    }

    # Coarse teaching ranges as (upper bound in HU, label), checked in order.
    # Real tissues overlap, and contrast, beam hardening, and partial-volume
    # effects all shift values - treat these as a study aid, not a diagnosis.
    HU_REFERENCE_RANGES = [
        (-900, "air"),
        (-200, "lung / aerated tissue"),
        (-20, "fat"),
        (20, "water / simple fluid"),
        (100, "soft tissue / blood"),
        (300, "contrast-enhanced tissue"),
        (float("inf"), "bone / calcification / metal"),
    ]

    def hounsfield_units(self, *, attenuation_coefficient, water_attenuation, air_attenuation=0.0):
        """Convert a linear attenuation coefficient to Hounsfield units.

            HU = 1000 * (mu - mu_water) / (mu_water - mu_air)

        Works element-wise on NumPy arrays as well as single numbers.

        :param attenuation_coefficient: tissue mu [1/cm] (number or array)
        :param water_attenuation: mu of water at the same beam energy [1/cm]
        :param air_attenuation: mu of air [1/cm]; ~0 so it defaults to 0
        :returns: CT number [HU]
        """
        mu = np.asarray(attenuation_coefficient, dtype=float)
        return 1000.0 * (mu - water_attenuation) / (water_attenuation - air_attenuation)

    def rescale_to_hounsfield(self, *, stored_values, rescale_slope=1.0, rescale_intercept=-1024.0):
        """Convert raw stored pixel values to HU:  HU = value * slope + intercept.

        DICOM files usually store unsigned integers; the RescaleSlope and
        RescaleIntercept tags (0028,1053 / 0028,1052) say how to recover HU.
        Forgetting this step is a classic beginner bug: every value is off by
        ~1024. See :class:`fpc.dicom.Dicom` for reading these from a file.

        :param stored_values: raw pixel values (number or array)
        :param rescale_slope: DICOM RescaleSlope
        :param rescale_intercept: DICOM RescaleIntercept
        :returns: values in HU (float array)
        """
        return np.asarray(stored_values, dtype=float) * rescale_slope + rescale_intercept

    def window_bounds(self, *, window_width=None, window_level=None, preset=None):
        """Lowest and highest HU shown by a window.

        Anything below ``level - width/2`` displays black, anything above
        ``level + width/2`` displays white. Pass either width AND level, or a
        ``preset`` name from :attr:`WINDOW_PRESETS`.

        :param window_width: window width W [HU]
        :param window_level: window level / centre L [HU]
        :param preset: optional preset name, e.g. "lung"
        :returns: tuple (lower HU, upper HU)
        """
        width, level = self._resolve_window(window_width, window_level, preset)
        return level - width / 2.0, level + width / 2.0

    def apply_window(
        self, *, hounsfield, window_width=None, window_level=None, preset=None, output_max=255
    ):
        """Map HU values to display grey levels for a chosen window.

        Values are clipped to the window, then scaled linearly to 0..output_max.
        A narrow window (brain, W=80) spreads a small HU range over all grey
        levels -> high contrast; a wide window (bone, W=1800) shows everything
        but with low contrast.

        :param hounsfield: HU value or array (e.g. a full CT slice)
        :param window_width: window width W [HU]
        :param window_level: window level L [HU]
        :param preset: optional preset name instead of width/level
        :param output_max: brightest grey level (255 for 8-bit display)
        :returns: numpy array of grey levels (uint8 when output_max == 255)
        """
        lower, upper = self.window_bounds(
            window_width=window_width,
            window_level=window_level,
            preset=preset,
        )
        hu = np.asarray(hounsfield, dtype=float)
        # np.clip and the arithmetic below run over the whole image at once -
        # no Python loop over pixels needed.
        scaled = (np.clip(hu, lower, upper) - lower) / (upper - lower) * output_max
        if output_max == 255:
            return np.round(scaled).astype(np.uint8)
        return scaled

    def classify_hounsfield(self, *, hounsfield):
        """Return a rough tissue label for a single HU value (teaching aid).

        :param hounsfield: CT number [HU]
        :returns: label string from :attr:`HU_REFERENCE_RANGES`
        """
        for upper_bound, label in self.HU_REFERENCE_RANGES:
            if hounsfield < upper_bound:
                return label
        return self.HU_REFERENCE_RANGES[-1][1]

    def dose_length_product(self, *, ctdi_vol_mgy, scan_length_cm):
        """Dose-length product DLP = CTDIvol * scan length  [mGy*cm].

        CTDIvol is the average dose within one slice of a standard phantom;
        DLP multiplies by how much of the patient was scanned. Both appear on
        every scanner's dose report.

        :param ctdi_vol_mgy: volume CT dose index [mGy]
        :param scan_length_cm: irradiated scan length [cm]
        :returns: DLP [mGy*cm]
        """
        return ctdi_vol_mgy * scan_length_cm

    # Adult conversion coefficients k [mSv / (mGy*cm)] from AAPM Report 96 /
    # the European Guidelines (EUR 16262). They turn DLP into an estimate of
    # effective dose for a "standard" adult.
    DLP_TO_EFFECTIVE_DOSE = {
        "head": 0.0021,
        "neck": 0.0059,
        "chest": 0.014,
        "abdomen_pelvis": 0.015,
        "chest_abdomen_pelvis": 0.015,
    }

    def effective_dose_from_dlp(self, *, dlp_mgy_cm, region):
        """Estimate adult effective dose:  E ~= k * DLP.

        Example: a routine head CT with DLP ~ 1000 mGy*cm gives ~2 mSv.

        :param dlp_mgy_cm: dose-length product [mGy*cm]
        :param region: key of :attr:`DLP_TO_EFFECTIVE_DOSE`
        :returns: effective dose estimate [mSv]
        """
        if region not in self.DLP_TO_EFFECTIVE_DOSE:
            raise ValueError(
                f"unknown region {region!r}; use one of: {', '.join(self.DLP_TO_EFFECTIVE_DOSE)}"
            )
        return self.DLP_TO_EFFECTIVE_DOSE[region] * dlp_mgy_cm

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_window(self, width, level, preset):
        """Return (width, level) from either a preset name or explicit values.

        The leading underscore marks this as an internal helper - a Python
        convention meaning "not part of the public API".
        """
        if preset is not None:
            if preset not in self.WINDOW_PRESETS:
                raise ValueError(
                    f"unknown preset {preset!r}; use one of: {', '.join(self.WINDOW_PRESETS)}"
                )
            return self.WINDOW_PRESETS[preset]
        if width is None or level is None:
            raise ValueError("give window_width and window_level, or a preset")
        if width <= 0:
            raise ValueError("window_width must be positive")
        return width, level
