# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""radiation.py - radiation physics and radiation protection.

The physics every radiology student meets in the first semester: how x-ray
intensity falls off with distance, how a beam is attenuated by tissue and
shielding, how a radionuclide decays, and how absorbed dose [Gy] is turned
into the protection quantities equivalent dose and effective dose [Sv].

All the protection weighting factors come from ICRP Publication 103 (2007),
which is the basis of current regulations in most countries.

These are teaching calculations. They are NOT a substitute for a qualified
medical physicist, a validated dosimetry system, or your local regulations.
"""

import math
from typing import Literal

# The radiation types with a fixed ICRP 103 weighting factor. A ``Literal``
# type lists the only strings a parameter accepts, so mypy (and the JSON
# Schema built by fpc.registry) can reject a typo like "gama" up front.
# A plain assignment (not a ``type`` statement) keeps the alias transparent
# to ``typing.get_type_hints``, which then sees the Literal itself.
RadiationType = Literal["photon", "electron", "proton", "alpha"]


class Radiation:
    """Radiation physics, attenuation, decay, and dosimetry calculations."""

    # ICRP 103 radiation weighting factors w_R (dimensionless). Neutrons are
    # missing on purpose: their w_R depends on energy, so they get a method of
    # their own (see :meth:`neutron_weighting_factor`).
    RADIATION_WEIGHTING_FACTORS = {
        "photon": 1.0,  # x-rays and gamma rays
        "electron": 1.0,  # beta particles, muons
        "proton": 2.0,
        "alpha": 20.0,  # also fission fragments and heavy ions
    }

    # ICRP 103 tissue weighting factors w_T. They describe what fraction of the
    # whole-body stochastic risk each organ carries, so they sum to exactly 1.
    TISSUE_WEIGHTING_FACTORS = {
        "red_bone_marrow": 0.12,
        "colon": 0.12,
        "lung": 0.12,
        "stomach": 0.12,
        "breast": 0.12,
        "remainder": 0.12,  # 13 remaining tissues, averaged together
        "gonads": 0.08,
        "bladder": 0.04,
        "oesophagus": 0.04,
        "liver": 0.04,
        "thyroid": 0.04,
        "bone_surface": 0.01,
        "brain": 0.01,
        "salivary_glands": 0.01,
        "skin": 0.01,
    }

    # Planck constant times speed of light, expressed in keV * nm. Lets us go
    # between photon energy and wavelength without carrying SI exponents.
    HC_KEV_NM = 1.239842

    # ------------------------------------------------------------------
    # Distance
    # ------------------------------------------------------------------
    def inverse_square_law(
        self, *, initial_intensity: float, initial_distance: float, new_distance: float
    ) -> float:
        """Intensity at a new distance from a point source.

        Radiation spreads over a sphere whose area grows with r^2, so intensity
        falls as 1/r^2:  I2 = I1 * (d1 / d2)^2.  Doubling your distance from the
        tube cuts your exposure to one quarter - the cheapest protection there is.

        :param initial_intensity: intensity (or exposure / dose rate) at d1 [any unit]
        :param initial_distance: original distance d1 [any length unit]
        :param new_distance: new distance d2 [same unit as d1]
        :returns: intensity at d2 [same unit as initial_intensity]
        """
        if initial_distance <= 0 or new_distance <= 0:
            raise ValueError("distances must be positive")
        return initial_intensity * (initial_distance / new_distance) ** 2

    # ------------------------------------------------------------------
    # Attenuation and shielding
    # ------------------------------------------------------------------
    def transmitted_intensity(
        self, *, initial_intensity: float, attenuation_coefficient: float, thickness: float
    ) -> float:
        """Narrow-beam (Beer-Lambert) attenuation:  I = I0 * exp(-mu * x).

        Each thin slab of material removes the same FRACTION of the photons
        that reach it, which is why the curve is exponential, not linear.

        :param initial_intensity: incident intensity I0 [any unit]
        :param attenuation_coefficient: linear attenuation coefficient mu [1/cm]
        :param thickness: material thickness x [cm]
        :returns: transmitted intensity [same unit as I0]
        """
        return initial_intensity * math.exp(-attenuation_coefficient * thickness)

    def linear_attenuation_coefficient(
        self, *, mass_attenuation_coefficient: float, density: float
    ) -> float:
        """Linear coefficient mu [1/cm] from mass coefficient mu/rho [cm^2/g].

        Tables (e.g. NIST XCOM) list mu/rho because it does not depend on the
        material's physical state; multiply by density to get mu.

        :param mass_attenuation_coefficient: mu/rho [cm^2/g]
        :param density: rho [g/cm^3]
        :returns: mu [1/cm]
        """
        return mass_attenuation_coefficient * density

    def half_value_layer(self, *, attenuation_coefficient: float) -> float:
        """Half-value layer HVL = ln(2) / mu.

        The thickness that cuts the beam intensity in half. Clinically the HVL
        (in mm of aluminium) is how beam QUALITY is specified.

        :param attenuation_coefficient: mu [1/cm]
        :returns: HVL [cm]
        """
        return math.log(2) / attenuation_coefficient

    def tenth_value_layer(self, *, attenuation_coefficient: float) -> float:
        """Tenth-value layer TVL = ln(10) / mu  (~3.32 HVLs).

        Shielding designers prefer TVLs: each one cuts intensity by 10x.

        :param attenuation_coefficient: mu [1/cm]
        :returns: TVL [cm]
        """
        return math.log(10) / attenuation_coefficient

    def shielding_thickness(self, *, attenuation_coefficient: float, transmission: float) -> float:
        """Thickness needed to let only a given fraction of the beam through.

        Solve I/I0 = exp(-mu*x) for x:  x = -ln(T) / mu.

        Note: real shielding has scatter "build-up", so true broad-beam barriers
        must be thicker than this narrow-beam estimate (see NCRP Report 147).

        :param attenuation_coefficient: mu [1/cm]
        :param transmission: desired transmitted fraction T, 0 < T <= 1 [-]
        :returns: required thickness [cm]
        """
        if not 0 < transmission <= 1:
            raise ValueError("transmission must be in (0, 1]")
        return -math.log(transmission) / attenuation_coefficient

    # ------------------------------------------------------------------
    # Photon energy
    # ------------------------------------------------------------------
    def photon_wavelength(self, *, energy_kev: float) -> float:
        """Photon wavelength from energy:  lambda = h*c / E.

        Applied to the tube voltage this gives the Duane-Hunt minimum
        wavelength: a 100 kVp beam contains no photon above 100 keV, so no
        wavelength shorter than ~0.0124 nm.

        :param energy_kev: photon energy [keV]
        :returns: wavelength [nm]
        """
        return self.HC_KEV_NM / energy_kev

    # ------------------------------------------------------------------
    # Radioactive decay (nuclear medicine)
    # ------------------------------------------------------------------
    def decay_constant(self, *, half_life: float) -> float:
        """Decay constant lambda = ln(2) / T_half.

        :param half_life: physical half-life [any time unit]
        :returns: decay constant [1 / that time unit]
        """
        return math.log(2) / half_life

    def remaining_activity(
        self, *, initial_activity: float, half_life: float, elapsed_time: float
    ) -> float:
        """Activity left after decay:  A = A0 * exp(-lambda * t).

        Used daily in nuclear medicine to work out how much of a dose is left
        at injection time (e.g. Tc-99m, T_half = 6.01 h).

        :param initial_activity: A0 [MBq, mCi, ... any activity unit]
        :param half_life: half-life [any time unit]
        :param elapsed_time: elapsed time [same unit as half_life]
        :returns: remaining activity [same unit as A0]
        """
        decay = self.decay_constant(half_life=half_life)
        return initial_activity * math.exp(-decay * elapsed_time)

    def effective_half_life(
        self, *, physical_half_life: float, biological_half_life: float
    ) -> float:
        """Effective half-life in the body:  1/Te = 1/Tp + 1/Tb.

        A radiopharmaceutical leaves the patient two ways at once - it decays
        (physical) AND is excreted (biological) - so the rates add, and the
        effective half-life is always shorter than either one.

        :param physical_half_life: Tp [any time unit]
        :param biological_half_life: Tb [same unit as Tp]
        :returns: effective half-life Te [same unit as Tp]
        """
        return (physical_half_life * biological_half_life) / (
            physical_half_life + biological_half_life
        )

    # ------------------------------------------------------------------
    # Dosimetry: Gy -> Sv
    # ------------------------------------------------------------------
    def neutron_weighting_factor(self, *, energy_mev: float) -> float:
        """ICRP 103 continuous radiation weighting factor for neutrons.

        :param energy_mev: neutron energy [MeV]
        :returns: w_R [-] (peaks at ~20 around 1 MeV)
        """
        if energy_mev <= 0:
            raise ValueError("neutron energy must be positive")
        # Three branches straight from ICRP 103, eq. (4.3).
        if energy_mev < 1.0:
            return 2.5 + 18.2 * math.exp(-(math.log(energy_mev) ** 2) / 6)
        if energy_mev <= 50.0:
            return 5.0 + 17.0 * math.exp(-(math.log(2 * energy_mev) ** 2) / 6)
        return 2.5 + 3.25 * math.exp(-(math.log(0.04 * energy_mev) ** 2) / 6)

    def equivalent_dose(self, *, absorbed_dose: float, radiation_type: RadiationType) -> float:
        """Equivalent dose H_T = w_R * D_T.

        Absorbed dose (Gy = J/kg) says how much energy was deposited; the
        weighting factor accounts for how biologically damaging that type of
        radiation is. 1 Gy of alpha harms tissue ~20x more than 1 Gy of x-rays.

        :param absorbed_dose: absorbed dose D [Gy]
        :param radiation_type: key of :attr:`RADIATION_WEIGHTING_FACTORS`
        :returns: equivalent dose [Sv]
        """
        try:
            weight = self.RADIATION_WEIGHTING_FACTORS[radiation_type]
        except KeyError:
            valid = ", ".join(self.RADIATION_WEIGHTING_FACTORS)
            # "from None" hides the internal KeyError: the ValueError says it all.
            raise ValueError(
                f"unknown radiation_type {radiation_type!r}; use one of: {valid}"
            ) from None
        return weight * absorbed_dose

    def effective_dose(self, *, organ_equivalent_doses: dict[str, float]) -> float:
        """Effective dose E = sum over organs of w_T * H_T.

        Lets you compare a chest x-ray with a head CT on one risk-related
        scale. It is a POPULATION protection quantity - not an individual
        patient's risk estimate.

        Organs you leave out contribute nothing, so this naturally handles a
        partial-body exposure.

        :param organ_equivalent_doses: dict {organ: H_T [Sv]}, organs named as
            in :attr:`TISSUE_WEIGHTING_FACTORS`
        :returns: effective dose [Sv]
        """
        unknown = set(organ_equivalent_doses) - set(self.TISSUE_WEIGHTING_FACTORS)
        if unknown:
            raise ValueError(f"unknown organ(s): {sorted(unknown)}")
        # A generator expression inside sum(): weight each organ, then add.
        return sum(
            self.TISSUE_WEIGHTING_FACTORS[organ] * dose
            for organ, dose in organ_equivalent_doses.items()
        )
