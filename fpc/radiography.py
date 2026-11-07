# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""radiography.py - projection x-ray technique and image geometry.

The "technique chart" arithmetic a radiographer does at the console: setting
mAs, trading kVp for mAs with the 15% rule, compensating for a change in
distance or grid, and predicting magnification and blur from the geometry of
tube, patient, and image receptor (IR).

Abbreviations used throughout:
    SID  source-to-image distance      (tube focal spot -> detector)
    SOD  source-to-object distance     (focal spot -> anatomy)
    OID  object-to-image distance      (anatomy -> detector);  SID = SOD + OID
"""

import math


class Radiography:
    """Exposure-technique and geometric calculations for projection radiography."""

    # Grid conversion factors (Bucky factors): how much the mAs must rise to
    # keep the same IR exposure once a grid is soaking up scatter.
    # Values are the standard textbook set (Bushong / Carlton & Adler).
    GRID_CONVERSION_FACTORS = {
        "none": 1,
        "5:1": 2,
        "6:1": 3,
        "8:1": 4,
        "12:1": 5,
        "16:1": 6,
    }

    # Heat-unit rectification constants per generator type. Texts differ
    # slightly for high-frequency units (1.40 - 1.45); 1.45 follows Bushong.
    GENERATOR_HEAT_FACTORS = {
        "single_phase": 1.00,
        "three_phase_6_pulse": 1.35,
        "three_phase_12_pulse": 1.41,
        "high_frequency": 1.45,
    }

    # ------------------------------------------------------------------
    # Exposure factors
    # ------------------------------------------------------------------
    def mas(self, *, tube_current_ma, exposure_time_s):
        """Tube current-time product mAs = mA * s.

        mAs sets the QUANTITY of x-ray photons. Reciprocity says 200 mA x 0.1 s
        and 400 mA x 0.05 s give the same 20 mAs - but the shorter time freezes
        patient motion better.

        :param tube_current_ma: tube current [mA]
        :param exposure_time_s: exposure time [s]
        :returns: mAs [mA*s]
        """
        return tube_current_ma * exposure_time_s

    def fifteen_percent_rule(self, *, kvp, mas, steps=1):
        """Trade kVp for mAs while keeping the same exposure to the IR.

        Raising kVp by 15% roughly doubles the exposure reaching the detector,
        so mAs can be halved. Each "step" applies the rule once; negative steps
        go the other way (lower kVp 15%, double mAs). Raising kVp this way
        lowers patient dose but also lowers subject contrast.

        :param kvp: starting peak tube voltage [kVp]
        :param mas: starting mAs
        :param steps: number of 15% adjustments (+ raises kVp, - lowers it)
        :returns: tuple (new kVp, new mAs)
        """
        new_kvp = kvp * 1.15**steps
        new_mas = mas / 2**steps
        return new_kvp, new_mas

    def exposure_maintenance_mas(self, *, original_mas, original_sid, new_sid):
        """Density/exposure maintenance formula:  mAs2 = mAs1 * (SID2 / SID1)^2.

        The inverse square law in reverse: moving the tube further away spreads
        the beam out, so the mAs must rise by the square of the distance ratio
        to keep the same detector exposure.

        :param original_mas: mAs used at the original SID
        :param original_sid: original source-to-image distance (any length unit)
        :param new_sid: new SID (same unit)
        :returns: new mAs
        """
        return original_mas * (new_sid / original_sid) ** 2

    def grid_mas(self, *, original_mas, original_grid, new_grid):
        """mAs compensation when adding, removing, or changing a grid.

        mAs2 = mAs1 * GCF2 / GCF1, with GCF from :attr:`GRID_CONVERSION_FACTORS`.

        :param original_mas: mAs used with the original grid
        :param original_grid: grid ratio key, e.g. "none" or "12:1"
        :param new_grid: grid ratio key for the new setup
        :returns: new mAs
        """
        factors = self.GRID_CONVERSION_FACTORS
        for grid in (original_grid, new_grid):
            if grid not in factors:
                raise ValueError(f"unknown grid {grid!r}; use one of: {', '.join(factors)}")
        return original_mas * factors[new_grid] / factors[original_grid]

    def heat_units(
        self, *, kvp, tube_current_ma, exposure_time_s, generator="high_frequency", exposures=1
    ):
        """Anode heat load in heat units:  HU = kVp * mA * s * C * exposures.

        Used with the tube rating chart to check a series of exposures (e.g. a
        fluoro run or CT scan) will not overheat the anode.

        :param kvp: peak tube voltage [kVp]
        :param tube_current_ma: tube current [mA]
        :param exposure_time_s: time per exposure [s]
        :param generator: key of :attr:`GENERATOR_HEAT_FACTORS`
        :param exposures: number of exposures in the series
        :returns: heat units [HU]
        """
        if generator not in self.GENERATOR_HEAT_FACTORS:
            raise ValueError(f"unknown generator {generator!r}")
        factor = self.GENERATOR_HEAT_FACTORS[generator]
        return kvp * tube_current_ma * exposure_time_s * factor * exposures

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def magnification_factor(self, *, sid, sod):
        """Magnification factor MF = SID / SOD  (always >= 1).

        Anatomy far from the detector is projected larger - which is why a PA
        chest makes the heart look smaller than an AP chest.

        :param sid: source-to-image distance (any length unit)
        :param sod: source-to-object distance (same unit)
        :returns: magnification factor [-]
        """
        if sod <= 0 or sod > sid:
            raise ValueError("need 0 < SOD <= SID (the object sits between tube and detector)")
        return sid / sod

    def object_size(self, *, image_size, sid, sod):
        """True anatomical size from a measured image:  object = image / MF.

        :param image_size: size measured on the image (any length unit)
        :param sid: source-to-image distance
        :param sod: source-to-object distance
        :returns: true object size, same unit as ``image_size``
        """
        return image_size / self.magnification_factor(sid=sid, sod=sod)

    def geometric_unsharpness(self, *, focal_spot_size, sid, oid):
        """Penumbra (edge blur) width:  Ug = focal spot * OID / SOD.

        A real focal spot is not a point, so every edge gets a blurred fringe.
        Minimize it with a small focal spot, long SID, and anatomy close to the
        detector (small OID).

        :param focal_spot_size: effective focal spot size [mm]
        :param sid: source-to-image distance (any length unit)
        :param oid: object-to-image distance (same unit as SID)
        :returns: geometric unsharpness [mm]
        """
        sod = sid - oid
        if sod <= 0:
            raise ValueError("OID must be smaller than SID")
        return focal_spot_size * oid / sod

    # ------------------------------------------------------------------
    # Digital detectors
    # ------------------------------------------------------------------
    def nyquist_limit(self, *, pixel_pitch_mm):
        """Highest resolvable spatial frequency of a digital detector.

        One line pair (a dark + a bright line) needs at least two pixels, so
        f_Nyquist = 1 / (2 * pixel pitch). Finer detail than this aliases.

        :param pixel_pitch_mm: detector element spacing [mm]
        :returns: limiting spatial resolution [line pairs / mm]
        """
        return 1.0 / (2.0 * pixel_pitch_mm)

    def exposure_index_deviation(self, *, exposure_index, target_exposure_index):
        """Deviation index DI = 10 * log10(EI / EI_target)  (IEC 62494-1).

        A vendor-neutral check on whether a digital image was over- or
        under-exposed. DI = 0 is on target; +1 is ~26% too much, +3 is double.
        Rule of thumb: |DI| <= 1 is acceptable; DI > +3 is a dose problem.

        :param exposure_index: EI reported by the detector
        :param target_exposure_index: EI_T set for this exam/body part
        :returns: deviation index [-]
        """
        return 10.0 * math.log10(exposure_index / target_exposure_index)
