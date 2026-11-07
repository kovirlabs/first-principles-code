# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""fatigue.py - high-cycle fatigue of metals (the stress-life method).

Most mechanical failures are fatigue failures: a part that easily survives
its load once cracks after millions of repetitions at a fraction of that
load. The stress-life method estimates how long a part lasts, or how safe it
is, in four steps (Shigley's *Mechanical Engineering Design*, 10th ed.,
Ch. 6):

1. **Estimate the test-specimen endurance limit** Se' from the ultimate
   strength (``endurance_limit_steel``).
2. **Correct it for the real part** with the Marin factors - surface finish,
   size, load type, temperature, reliability - to get Se
   (``surface_factor``, ``size_factor``, ``load_factor``,
   ``reliability_factor``, ``marin_endurance_limit``).
3. **Account for mean stress** with a failure line on the
   alternating-vs-mean stress diagram: Goodman, Soderberg, Gerber, or
   ASME-elliptic (the ``*_safety_factor`` methods).
4. **For finite life**, use the Basquin S-N line between 10^3 and 10^6
   cycles (``sn_curve_coefficients``, ``cycles_to_failure``).

Stresses and strengths are in pascals. The empirical curve fits from the
literature are in MPa; the methods convert internally, so you never have to.
These estimates are for steels; other metals have no true endurance limit.
"""

import math
from typing import Literal

from scipy.stats import norm

# Surface factor ka = a * Sut^b with Sut in MPa (Shigley 10th ed., Table 6-2).
# Rougher finishes have more and deeper surface flaws where cracks start, so
# ka drops - and drops faster for stronger, more notch-sensitive steels.
_SURFACE_COEFFICIENTS: dict[str, tuple[float, float]] = {
    "ground": (1.58, -0.085),
    "machined": (4.51, -0.265),  # machined or cold-drawn
    "cold-drawn": (4.51, -0.265),
    "hot-rolled": (57.7, -0.718),
    "as-forged": (272.0, -0.995),
}

# Load factor kc (Shigley Eq. 6-26): rotating-beam tests are in bending, and
# a part loaded axially or in torsion has a lower endurance limit.
_LOAD_FACTORS = {"bending": 1.0, "axial": 0.85, "torsion": 0.59}

SurfaceFinish = Literal["ground", "machined", "cold-drawn", "hot-rolled", "as-forged"]
LoadType = Literal["bending", "axial", "torsion"]


class Fatigue:
    """Stress-life fatigue: endurance limits, Marin factors, mean-stress criteria."""

    # Pascals per megapascal, for the curve fits that are written in MPa.
    _MPA = 1e6

    # --- Step 1: the test-specimen endurance limit ---------------------------

    def endurance_limit_steel(self, *, ultimate_strength: float) -> float:
        """Rotating-beam endurance limit estimate for steels, Shigley Eq. 6-8.

            Se' = 0.5 * Sut     for Sut <= 1400 MPa
            Se' = 700 MPa       for Sut >  1400 MPa

        This is the endurance limit of a small, polished, rotating test
        specimen - not of your part. Apply the Marin factors next. The
        plateau reflects test data: very strong steels gain no further
        fatigue resistance because tiny inclusions start the cracks.

        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :returns: specimen endurance limit Se' [Pa]
        :raises ValueError: if Sut is not positive
        """
        if ultimate_strength <= 0:
            raise ValueError("ultimate_strength must be positive")
        return min(0.5 * ultimate_strength, 700 * self._MPA)

    # --- Step 2: Marin factors ----------------------------------------------

    def surface_factor(self, *, ultimate_strength: float, finish: SurfaceFinish) -> float:
        """Marin surface factor ka = a * Sut^b, Shigley Eq. 6-19 / Table 6-2.

            finish                  a        b
            ground                 1.58    -0.085
            machined/cold-drawn    4.51    -0.265
            hot-rolled             57.7    -0.718
            as-forged              272     -0.995

        (a for Sut in MPa.) The result is capped at 1: a fit is not allowed
        to make a part *better* than the polished test specimen.

        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :param finish: surface finish of the part
        :returns: surface factor ka [-]
        :raises ValueError: if Sut is not positive
        """
        if ultimate_strength <= 0:
            raise ValueError("ultimate_strength must be positive")
        a, b = _SURFACE_COEFFICIENTS[finish]
        return min(1.0, a * (ultimate_strength / self._MPA) ** b)

    def size_factor(self, *, diameter: float, loading: LoadType = "bending") -> float:
        """Marin size factor kb for a round bar, Shigley Eq. 6-20.

        Bigger parts have more highly stressed material, so more chance of a
        flaw where a crack can start. For rotating round bars in bending or
        torsion, with d in mm:

            kb = 1.24 * d^-0.107     for 2.79 <= d <= 51 mm
            kb = 1.51 * d^-0.157     for 51 <  d <= 254 mm

        Axial loading has no stress gradient, so kb = 1. For a non-rotating
        or non-round section, first convert to an equivalent diameter
        (Shigley Sec. 6-9) and pass that.

        :param diameter: bar diameter d [m]
        :param loading: ``"bending"``, ``"torsion"`` or ``"axial"``
        :returns: size factor kb [-]
        :raises ValueError: for a diameter outside 2.79-254 mm
        """
        if loading == "axial":
            return 1.0
        d_mm = diameter * 1e3
        if not 2.79 <= d_mm <= 254:
            raise ValueError(
                f"size factor fit covers 2.79 to 254 mm; got {d_mm:g} mm (pass metres)"
            )
        if d_mm <= 51:
            return 1.24 * d_mm**-0.107
        return 1.51 * d_mm**-0.157

    def load_factor(self, *, loading: LoadType) -> float:
        """Marin load factor kc, Shigley Eq. 6-26: 1 bending, 0.85 axial, 0.59 torsion.

        The 0.59 for torsion is the distortion-energy ratio 1/sqrt(3) = 0.577,
        rounded up to match test data. Do *not* use kc = 0.59 if you combine
        torsion into a von Mises stress - that already accounts for it.

        :param loading: ``"bending"``, ``"axial"`` or ``"torsion"``
        :returns: load factor kc [-]
        """
        return _LOAD_FACTORS[loading]

    def reliability_factor(self, *, reliability: float) -> float:
        """Marin reliability factor ke = 1 - 0.08 * za, Shigley Table 6-5.

        Endurance-limit data scatter with a standard deviation of about 8 %
        of the mean. Se' is a *mean* value (50 % reliability); to be sure that
        a fraction R of parts survive, step down za standard deviations, where
        za is the standard-normal variate with probability R below it. SciPy's
        ``norm.ppf`` (the inverse normal CDF) gives za directly, so this
        reproduces Table 6-5 without the table: R = 0.99 -> za = 2.326 ->
        ke = 0.814.

        :param reliability: required probability of survival R, e.g. 0.99 [-]
        :returns: reliability factor ke [-]
        :raises ValueError: unless 0.5 <= R < 1
        """
        if not 0.5 <= reliability < 1:
            raise ValueError("reliability must be in [0.5, 1), e.g. 0.99 for 99 %")
        return 1 - 0.08 * float(norm.ppf(reliability))

    def marin_endurance_limit(
        self,
        *,
        specimen_endurance_limit: float,
        surface_factor: float = 1.0,
        size_factor: float = 1.0,
        load_factor: float = 1.0,
        temperature_factor: float = 1.0,
        reliability_factor: float = 1.0,
        miscellaneous_factor: float = 1.0,
    ) -> float:
        """Endurance limit of the real part: Se = ka*kb*kc*kd*ke*kf * Se', Shigley Eq. 6-18.

        Each Marin factor is a multiplier, usually below 1, that corrects the
        laboratory value for one way the real part differs from the test
        specimen. Compute them with the methods above (kd, the temperature
        factor, is about 1 up to ~250 degC for steels).

        :param specimen_endurance_limit: test-specimen endurance limit Se' [Pa]
        :param surface_factor: ka [-]
        :param size_factor: kb [-]
        :param load_factor: kc [-]
        :param temperature_factor: kd [-]
        :param reliability_factor: ke [-]
        :param miscellaneous_factor: kf (corrosion, plating, ...) [-]
        :returns: corrected endurance limit Se [Pa]
        :raises ValueError: if Se' or any factor is not positive
        """
        factors = (
            surface_factor,
            size_factor,
            load_factor,
            temperature_factor,
            reliability_factor,
            miscellaneous_factor,
        )
        if specimen_endurance_limit <= 0 or min(factors) <= 0:
            raise ValueError("endurance limit and Marin factors must be positive")
        return specimen_endurance_limit * math.prod(factors)

    # --- Step 3: mean-stress failure criteria ---------------------------------
    #
    # Each criterion is a line (or curve) on the alternating-vs-mean stress
    # diagram from (0, Se) to the mean-stress axis. The safety factor n scales
    # the load point (sigma_m, sigma_a) until it reaches that line. Goodman is
    # the usual design choice; Soderberg is more conservative; Gerber and
    # ASME-elliptic run through the middle of the test data.

    @staticmethod
    def _check_stresses(alternating_stress: float, mean_stress: float) -> None:
        if alternating_stress <= 0:
            raise ValueError("alternating_stress must be positive")
        if mean_stress < 0:
            # A compressive mean stress does not shorten fatigue life; Shigley
            # then uses n = Se / sigma_a (with a separate yield check).
            raise ValueError("these criteria assume mean_stress >= 0 (tensile)")

    def goodman_safety_factor(
        self,
        *,
        alternating_stress: float,
        mean_stress: float,
        endurance_limit: float,
        ultimate_strength: float,
    ) -> float:
        """Fatigue safety factor, modified Goodman line: 1/n = sa/Se + sm/Sut.

        A straight line from Se on the alternating axis to Sut on the mean
        axis. Simple, slightly conservative, and the most common choice.

        :param alternating_stress: alternating stress amplitude sigma_a [Pa]
        :param mean_stress: mean stress sigma_m (>= 0) [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :returns: fatigue safety factor n [-]
        :raises ValueError: for non-positive sigma_a or negative sigma_m
        """
        self._check_stresses(alternating_stress, mean_stress)
        return 1 / (alternating_stress / endurance_limit + mean_stress / ultimate_strength)

    def soderberg_safety_factor(
        self,
        *,
        alternating_stress: float,
        mean_stress: float,
        endurance_limit: float,
        yield_strength: float,
    ) -> float:
        """Fatigue safety factor, Soderberg line: 1/n = sa/Se + sm/Sy.

        Like Goodman but ending at the yield strength, so it also guards
        against yielding. The most conservative of the four criteria.

        :param alternating_stress: alternating stress amplitude sigma_a [Pa]
        :param mean_stress: mean stress sigma_m (>= 0) [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param yield_strength: yield strength Sy [Pa]
        :returns: fatigue safety factor n [-]
        :raises ValueError: for non-positive sigma_a or negative sigma_m
        """
        self._check_stresses(alternating_stress, mean_stress)
        return 1 / (alternating_stress / endurance_limit + mean_stress / yield_strength)

    def gerber_safety_factor(
        self,
        *,
        alternating_stress: float,
        mean_stress: float,
        endurance_limit: float,
        ultimate_strength: float,
    ) -> float:
        """Fatigue safety factor, Gerber parabola: n*sa/Se + (n*sm/Sut)^2 = 1.

        A parabola through the middle of ductile-steel test data. Solving the
        quadratic for its positive root (Shigley Table 6-7):

            n = 1/2 * (Sut/sm)^2 * (sa/Se) * [ -1 + sqrt(1 + (2*sm*Se/(Sut*sa))^2) ]

        With no mean stress the parabola meets the axis at Se, so n = Se/sa.

        :param alternating_stress: alternating stress amplitude sigma_a [Pa]
        :param mean_stress: mean stress sigma_m (>= 0) [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :returns: fatigue safety factor n [-]
        :raises ValueError: for non-positive sigma_a or negative sigma_m
        """
        self._check_stresses(alternating_stress, mean_stress)
        if mean_stress == 0:
            # The closed form divides by sigma_m; its limit as sigma_m -> 0 is Se/sa.
            return endurance_limit / alternating_stress
        sa, sm, se, sut = alternating_stress, mean_stress, endurance_limit, ultimate_strength
        return (
            0.5
            * (sut / sm) ** 2
            * (sa / se)
            * (-1 + math.sqrt(1 + (2 * sm * se / (sut * sa)) ** 2))
        )

    def asme_elliptic_safety_factor(
        self,
        *,
        alternating_stress: float,
        mean_stress: float,
        endurance_limit: float,
        yield_strength: float,
    ) -> float:
        """Fatigue safety factor, ASME-elliptic: (n*sa/Se)^2 + (n*sm/Sy)^2 = 1.

        A quarter ellipse from Se to Sy; it fits test data well and, ending
        at Sy, includes a yield check. Solving directly:

            n = 1 / sqrt( (sa/Se)^2 + (sm/Sy)^2 )

        :param alternating_stress: alternating stress amplitude sigma_a [Pa]
        :param mean_stress: mean stress sigma_m (>= 0) [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param yield_strength: yield strength Sy [Pa]
        :returns: fatigue safety factor n [-]
        :raises ValueError: for non-positive sigma_a or negative sigma_m
        """
        self._check_stresses(alternating_stress, mean_stress)
        return 1 / math.sqrt(
            (alternating_stress / endurance_limit) ** 2 + (mean_stress / yield_strength) ** 2
        )

    # --- Step 4: finite life (S-N curve) -------------------------------------

    def sn_curve_coefficients(
        self,
        *,
        ultimate_strength: float,
        endurance_limit: float,
        fatigue_strength_fraction: float = 0.9,
    ) -> dict[str, float]:
        """Basquin S-N line Sf = a * N^b through (10^3, f*Sut) and (10^6, Se).

        On log-log axes the high-cycle S-N curve of steel is close to a
        straight line between 10^3 cycles, where the strength is a fraction f
        of Sut, and 10^6 cycles, where it reaches the endurance limit. Fitting
        Sf = a * N^b through those two points gives (Shigley Eqs. 6-14, 6-15)

            a = (f*Sut)^2 / Se          b = -1/3 * log10(f*Sut / Se)

        f is about 0.9 for Sut up to ~490 MPa, falling to ~0.77 at 1400 MPa
        (Shigley Fig. 6-18).

        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param fatigue_strength_fraction: f, the fraction of Sut at 10^3 cycles [-]
        :returns: dict with ``a`` [Pa] and ``b`` [-]
        :raises ValueError: for non-positive strengths or f*Sut <= Se
        """
        if ultimate_strength <= 0 or endurance_limit <= 0:
            raise ValueError("ultimate_strength and endurance_limit must be positive")
        if not 0 < fatigue_strength_fraction <= 1:
            raise ValueError("fatigue_strength_fraction must be in (0, 1]")
        strength_1e3 = fatigue_strength_fraction * ultimate_strength
        if strength_1e3 <= endurance_limit:
            raise ValueError("f*Sut must exceed Se for the S-N line to slope downward")
        return {
            "a": strength_1e3**2 / endurance_limit,
            "b": -math.log10(strength_1e3 / endurance_limit) / 3,
        }

    def cycles_to_failure(
        self,
        *,
        alternating_stress: float,
        ultimate_strength: float,
        endurance_limit: float,
        fatigue_strength_fraction: float = 0.9,
    ) -> float:
        """Cycles to failure under fully reversed stress: N = (sigma_a / a)^(1/b).

        Inverts the Basquin line from ``sn_curve_coefficients``. Below the
        endurance limit the steel is predicted to last indefinitely, so the
        result is ``inf``. For mean stress, first convert to an equivalent
        fully reversed stress, e.g. sigma_rev = sigma_a / (1 - sigma_m/Sut)
        (Goodman).

        :param alternating_stress: fully reversed stress amplitude sigma_a [Pa]
        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :param endurance_limit: corrected endurance limit Se [Pa]
        :param fatigue_strength_fraction: f, the fraction of Sut at 10^3 cycles [-]
        :returns: cycles to failure N (``inf`` below the endurance limit) [cycles]
        :raises ValueError: for sigma_a above f*Sut, the low-cycle region
            (N < 10^3) where the Basquin line does not apply
        """
        if alternating_stress <= 0:
            raise ValueError("alternating_stress must be positive")
        if alternating_stress <= endurance_limit:
            return math.inf
        if alternating_stress > fatigue_strength_fraction * ultimate_strength:
            raise ValueError("stress above f*Sut: low-cycle fatigue (N < 1e3), out of range")
        coefficients = self.sn_curve_coefficients(
            ultimate_strength=ultimate_strength,
            endurance_limit=endurance_limit,
            fatigue_strength_fraction=fatigue_strength_fraction,
        )
        return (alternating_stress / coefficients["a"]) ** (1 / coefficients["b"])
