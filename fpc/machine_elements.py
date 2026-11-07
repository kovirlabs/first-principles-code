# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""machine_elements.py - bolts, shafts, springs, bearings, and welds.

Machine elements are the standard parts every mechanical design is built
from. This class collects the first-pass sizing equations a design engineer
reaches for daily, in the form given in Shigley's *Mechanical Engineering
Design* (Budynas & Nisbett, 10th ed.):

* **Bolted joints** (Ch. 8): tightening torque, recommended preload, bolt and
  member stiffness, the joint constant C, and how an external load is shared
  between the bolt and the clamped members.
* **Shafts** (Ch. 7): the diameter needed for combined bending and torsion,
  both statically (von Mises) and in fatigue (DE-Goodman).
* **Helical compression springs** (Ch. 10): spring rate and the curvature-
  corrected wire shear stress.
* **Rolling bearings** (Ch. 11): L10 rating life and the catalogue rating
  needed for a target life.
* **Fillet welds** (Ch. 9): the conventional throat shear stress.

All inputs and outputs are SI floats (N, m, Pa, N*m) unless the parameter
name says otherwise (``speed_rpm``, ``life_hours``). These are *first-pass*
equations: they size a part quickly and transparently, but a final design
still needs the full code or catalogue check.
"""

import math
from typing import Literal


class MachineElements:
    """Sizing equations for bolts, shafts, springs, bearings, and welds."""

    # --- Bolted joints -----------------------------------------------------

    def bolt_tightening_torque(
        self, *, preload: float, nominal_diameter: float, torque_coefficient: float = 0.2
    ) -> float:
        """Wrench torque needed to reach a bolt preload: T = K * Fi * d.

        Shigley Eq. 8-27. The torque coefficient K lumps together thread and
        under-head friction; almost all of the torque is lost to friction and
        only ~10 % actually stretches the bolt, which is why K matters so
        much. K = 0.2 is the usual value for unlubricated steel bolts of any
        finish; lubricated or cadmium-plated bolts are nearer 0.15-0.16.

        :param preload: target bolt preload Fi [N]
        :param nominal_diameter: bolt nominal (major) diameter d [m]
        :param torque_coefficient: torque (nut) factor K, default 0.2 [-]
        :returns: tightening torque T [N*m]
        :raises ValueError: if any input is not positive
        """
        if preload <= 0 or nominal_diameter <= 0 or torque_coefficient <= 0:
            raise ValueError("preload, nominal_diameter and torque_coefficient must be positive")
        return torque_coefficient * preload * nominal_diameter

    def bolt_preload(
        self,
        *,
        proof_strength: float,
        tensile_stress_area: float,
        connection: Literal["reusable", "permanent"] = "reusable",
    ) -> float:
        """Recommended bolt preload as a fraction of the proof load.

        The proof load is Fp = At * Sp: the largest load the bolt carries with
        no permanent set. Shigley (Sec. 8-9) recommends tightening to

            Fi = 0.75 * Fp   for reusable (removable) connections,
            Fi = 0.90 * Fp   for permanent connections.

        A high preload keeps the joint clamped (so the bolt sees only a small
        share of any fluctuating load - see ``bolted_joint_loads``), which is
        the main reason preloaded bolts survive fatigue.

        :param proof_strength: bolt proof strength Sp (e.g. ISO 8.8: 600 MPa) [Pa]
        :param tensile_stress_area: thread tensile-stress area At [m^2]
        :param connection: ``"reusable"`` (0.75 Fp) or ``"permanent"`` (0.90 Fp)
        :returns: recommended preload Fi [N]
        :raises ValueError: if strength or area is not positive
        """
        if proof_strength <= 0 or tensile_stress_area <= 0:
            raise ValueError("proof_strength and tensile_stress_area must be positive")
        fraction = {"reusable": 0.75, "permanent": 0.90}[connection]
        return fraction * proof_strength * tensile_stress_area

    def bolt_stiffness(
        self,
        *,
        modulus: float,
        nominal_diameter: float,
        tensile_stress_area: float,
        unthreaded_length: float,
        threaded_length: float,
    ) -> float:
        """Axial stiffness of a bolt within the grip: kb = Ad*At*E / (Ad*lt + At*ld).

        Shigley Eq. 8-17. Inside the clamped grip, a bolt is two springs in
        series: the plain shank (area Ad = pi*d^2/4, length ld) and the
        threaded part (tensile-stress area At, length lt). Springs in series
        add their *flexibilities* (L / (A*E)), which gives this formula.

        :param modulus: bolt Young's modulus E (steel ~207e9) [Pa]
        :param nominal_diameter: bolt nominal diameter d [m]
        :param tensile_stress_area: thread tensile-stress area At [m^2]
        :param unthreaded_length: length of plain shank in the grip ld [m]
        :param threaded_length: length of thread in the grip lt [m]
        :returns: bolt stiffness kb [N/m]
        :raises ValueError: for non-positive sizes or a grip of zero length
        """
        if modulus <= 0 or nominal_diameter <= 0 or tensile_stress_area <= 0:
            raise ValueError("modulus, nominal_diameter and tensile_stress_area must be positive")
        if unthreaded_length < 0 or threaded_length < 0:
            raise ValueError("lengths in the grip cannot be negative")
        if unthreaded_length + threaded_length == 0:
            raise ValueError("the grip length (unthreaded + threaded) must be positive")
        shank_area = math.pi * nominal_diameter**2 / 4
        return (
            shank_area
            * tensile_stress_area
            * modulus
            / (shank_area * threaded_length + tensile_stress_area * unthreaded_length)
        )

    def member_stiffness(
        self, *, modulus: float, nominal_diameter: float, grip_length: float
    ) -> float:
        """Stiffness of the clamped members, using 30-degree pressure cones.

        Shigley Eq. 8-23. The clamping pressure spreads out from under the
        bolt head and nut as two cones of half-angle 30 deg. Integrating the
        compliance of those frusta, for members of one material with washer
        face diameter 1.5*d, gives

            km = 0.5774*pi*E*d / (2 * ln( 5*(0.5774*l + 0.5*d) / (0.5774*l + 2.5*d) ))

        (0.5774 = tan 30 deg). The members are usually much stiffer than the
        bolt, which is why the bolt carries only a small share of the load.

        :param modulus: Young's modulus of the members E [Pa]
        :param nominal_diameter: bolt nominal diameter d [m]
        :param grip_length: total thickness of the clamped members l [m]
        :returns: member stiffness km [N/m]
        :raises ValueError: if any input is not positive
        """
        if modulus <= 0 or nominal_diameter <= 0 or grip_length <= 0:
            raise ValueError("modulus, nominal_diameter and grip_length must be positive")
        tan30 = math.tan(math.radians(30.0))
        d, length = nominal_diameter, grip_length
        log_term = math.log(5 * (tan30 * length + 0.5 * d) / (tan30 * length + 2.5 * d))
        return tan30 * math.pi * modulus * d / (2 * log_term)

    def joint_stiffness_constant(self, *, bolt_stiffness: float, member_stiffness: float) -> float:
        """Joint constant C = kb / (kb + km): the bolt's share of an external load.

        Bolt and members are springs in *parallel* under an external load P
        (both stretch by the same amount until the joint separates), so the
        load divides in proportion to stiffness: the bolt takes C*P and the
        members are unloaded by (1 - C)*P. Typical values are 0.15-0.35.

        :param bolt_stiffness: bolt stiffness kb [N/m]
        :param member_stiffness: member stiffness km [N/m]
        :returns: joint stiffness constant C [-]
        :raises ValueError: if either stiffness is not positive
        """
        if bolt_stiffness <= 0 or member_stiffness <= 0:
            raise ValueError("stiffnesses must be positive")
        return bolt_stiffness / (bolt_stiffness + member_stiffness)

    def bolted_joint_loads(
        self, *, preload: float, external_load: float, stiffness_constant: float
    ) -> dict[str, float]:
        """Bolt and member forces in a preloaded joint under an external tensile load.

        From Shigley Sec. 8-7 (valid while the joint stays clamped):

            Fb = C*P + Fi          (bolt tension)
            Fm = (1 - C)*P - Fi    (member force; negative = still compressed)
            P0 = Fi / (1 - C)      (external load that separates the joint)

        :param preload: bolt preload Fi [N]
        :param external_load: external tensile load per bolt P [N]
        :param stiffness_constant: joint constant C from ``joint_stiffness_constant`` [-]
        :returns: dict with ``bolt_load`` [N], ``member_load`` [N],
            ``separation_load`` [N], and ``separation_factor`` P0/P [-]
        :raises ValueError: for C outside (0, 1), a negative load, or a joint
            that has already separated (P >= P0)
        """
        if not 0 < stiffness_constant < 1:
            raise ValueError("stiffness_constant must be between 0 and 1")
        if preload < 0 or external_load < 0:
            raise ValueError("preload and external_load cannot be negative")
        separation_load = preload / (1 - stiffness_constant)
        if external_load >= separation_load:
            # Past separation the members carry nothing and the bolt carries
            # all of P; the linear spring model above no longer applies.
            raise ValueError(
                f"joint separates: external_load {external_load:g} N >= "
                f"separation load {separation_load:g} N"
            )
        return {
            "bolt_load": stiffness_constant * external_load + preload,
            "member_load": (1 - stiffness_constant) * external_load - preload,
            "separation_load": separation_load,
            "separation_factor": (
                separation_load / external_load if external_load > 0 else math.inf
            ),
        }

    # --- Shafts ------------------------------------------------------------

    def shaft_diameter_static(
        self, *, bending_moment: float, torque: float, yield_strength: float, safety_factor: float
    ) -> float:
        """Solid shaft diameter for steady bending + torsion (von Mises yield).

        A solid round shaft has bending stress sigma = 32*M/(pi*d^3) and
        torsional shear tau = 16*T/(pi*d^3). Their von Mises equivalent is

            sigma' = sqrt(sigma^2 + 3*tau^2) = 16/(pi*d^3) * sqrt(4*M^2 + 3*T^2).

        Setting sigma' = Sy / n and solving for d:

            d = ( 16*n / (pi*Sy) * sqrt(4*M^2 + 3*T^2) )^(1/3)

        Use this for loads that do not fluctuate (or as a first-cycle yield
        check). A rotating shaft under a steady moment sees *fully reversed*
        bending, so it also needs the fatigue check in
        ``shaft_diameter_de_goodman``.

        :param bending_moment: bending moment M [N*m]
        :param torque: torque T [N*m]
        :param yield_strength: shaft material yield strength Sy [Pa]
        :param safety_factor: design factor n [-]
        :returns: minimum shaft diameter d [m]
        :raises ValueError: for non-positive strength/safety factor or no load
        """
        if yield_strength <= 0 or safety_factor <= 0:
            raise ValueError("yield_strength and safety_factor must be positive")
        load_term = math.sqrt(4 * bending_moment**2 + 3 * torque**2)
        if load_term == 0:
            raise ValueError("bending_moment and torque cannot both be zero")
        return (16 * safety_factor / (math.pi * yield_strength) * load_term) ** (1 / 3)

    def shaft_diameter_de_goodman(
        self,
        *,
        alternating_moment: float,
        mean_moment: float,
        alternating_torque: float,
        mean_torque: float,
        endurance_limit: float,
        ultimate_strength: float,
        safety_factor: float,
        fatigue_factor_bending: float = 1.0,
        fatigue_factor_torsion: float = 1.0,
    ) -> float:
        """Solid shaft diameter for fatigue (DE-Goodman criterion), Shigley Eq. 7-8.

        Combines distortion-energy (von Mises) stresses with the modified
        Goodman line. The alternating and mean von Mises stresses are each
        built from bending (x 4) and torsion (x 3) exactly as in the static
        case, then weighted by the endurance limit and ultimate strength:

            d = { 16*n/pi * [ sqrt(4*(Kf*Ma)^2 + 3*(Kfs*Ta)^2) / Se
                            + sqrt(4*(Kf*Mm)^2 + 3*(Kfs*Tm)^2) / Sut ] }^(1/3)

        A typical rotating shaft with steady torque has Mm = 0 and Ta = 0.
        The endurance limit Se must already include the Marin factors (see
        ``Fatigue.marin_endurance_limit``); the size factor depends on d, so
        size iteratively: guess d, find Se, solve, repeat. Goodman does not
        guard against first-cycle yield - check that separately.

        :param alternating_moment: alternating bending moment Ma [N*m]
        :param mean_moment: mean bending moment Mm [N*m]
        :param alternating_torque: alternating torque Ta [N*m]
        :param mean_torque: mean torque Tm [N*m]
        :param endurance_limit: fully corrected endurance limit Se [Pa]
        :param ultimate_strength: ultimate tensile strength Sut [Pa]
        :param safety_factor: design factor n [-]
        :param fatigue_factor_bending: fatigue stress-concentration factor Kf [-]
        :param fatigue_factor_torsion: fatigue stress-concentration factor Kfs [-]
        :returns: minimum shaft diameter d [m]
        :raises ValueError: for non-positive strengths, factors, or no load
        """
        if endurance_limit <= 0 or ultimate_strength <= 0 or safety_factor <= 0:
            raise ValueError("strengths and safety_factor must be positive")
        if fatigue_factor_bending < 1 or fatigue_factor_torsion < 1:
            raise ValueError("stress-concentration factors are >= 1 (use 1 for none)")
        kf, kfs = fatigue_factor_bending, fatigue_factor_torsion
        alternating = math.sqrt(
            4 * (kf * alternating_moment) ** 2 + 3 * (kfs * alternating_torque) ** 2
        )
        mean = math.sqrt(4 * (kf * mean_moment) ** 2 + 3 * (kfs * mean_torque) ** 2)
        if alternating == 0 and mean == 0:
            raise ValueError("at least one moment or torque must be non-zero")
        bracket = alternating / endurance_limit + mean / ultimate_strength
        return (16 * safety_factor / math.pi * bracket) ** (1 / 3)

    # --- Helical compression springs ----------------------------------------

    def spring_rate(
        self,
        *,
        wire_diameter: float,
        mean_coil_diameter: float,
        active_coils: float,
        shear_modulus: float,
    ) -> float:
        """Rate of a helical compression spring: k = d^4 * G / (8 * D^3 * Na).

        Shigley Eq. 10-9. The wire is a long torsion bar wound into a helix,
        so the rate comes from torsional strain energy. Note the powers: wire
        diameter to the 4th, coil diameter to the 3rd - small changes in d or
        D swing the rate a lot.

        :param wire_diameter: wire diameter d [m]
        :param mean_coil_diameter: mean coil diameter D (outer minus d) [m]
        :param active_coils: number of active coils Na (may be fractional) [-]
        :param shear_modulus: wire shear modulus G (music wire ~81.7e9) [Pa]
        :returns: spring rate k [N/m]
        :raises ValueError: for non-positive inputs or D <= d
        """
        if min(wire_diameter, mean_coil_diameter, active_coils, shear_modulus) <= 0:
            raise ValueError("all spring inputs must be positive")
        if mean_coil_diameter <= wire_diameter:
            raise ValueError("mean_coil_diameter must exceed wire_diameter (check D vs d)")
        return wire_diameter**4 * shear_modulus / (8 * mean_coil_diameter**3 * active_coils)

    def spring_shear_stress(
        self,
        *,
        force: float,
        wire_diameter: float,
        mean_coil_diameter: float,
        correction: Literal["wahl", "bergstrasser"] = "wahl",
    ) -> float:
        """Maximum wire shear stress in a helical spring: tau = K * 8*F*D / (pi*d^3).

        8*F*D/(pi*d^3) is the plain torsion stress in the wire. The factor K
        corrects for direct shear and for wire curvature, which concentrates
        stress on the inside of the coil. With spring index C = D/d:

            Wahl:          K_W = (4C - 1)/(4C - 4) + 0.615/C
            Bergstrasser:  K_B = (4C + 2)/(4C - 3)          (Shigley Eq. 10-5)

        The two agree within about 1 %. Practical springs have 4 <= C <= 12.

        :param force: axial spring force F [N]
        :param wire_diameter: wire diameter d [m]
        :param mean_coil_diameter: mean coil diameter D [m]
        :param correction: stress-correction factor, ``"wahl"`` or ``"bergstrasser"``
        :returns: maximum shear stress tau [Pa]
        :raises ValueError: for non-positive sizes or a spring index C <= 1
        """
        if wire_diameter <= 0 or mean_coil_diameter <= 0:
            raise ValueError("wire_diameter and mean_coil_diameter must be positive")
        index = mean_coil_diameter / wire_diameter
        if index <= 1:
            raise ValueError("spring index D/d must be greater than 1 (check D vs d)")
        if correction == "wahl":
            factor = (4 * index - 1) / (4 * index - 4) + 0.615 / index
        else:
            factor = (4 * index + 2) / (4 * index - 3)
        return factor * 8 * force * mean_coil_diameter / (math.pi * wire_diameter**3)

    # --- Rolling bearings ----------------------------------------------------

    # Load-life exponent a in L10 = (C/P)^a: 3 for ball bearings (point
    # contact), 10/3 for roller bearings (line contact).
    _LIFE_EXPONENT = {"ball": 3.0, "roller": 10.0 / 3.0}

    def bearing_l10_life(
        self,
        *,
        dynamic_load_rating: float,
        equivalent_load: float,
        bearing_type: Literal["ball", "roller"] = "ball",
    ) -> float:
        """Bearing rating life L10 = (C / P)^a, in millions of revolutions.

        L10 is the life that 90 % of a large group of identical bearings
        reach or exceed. The catalogue dynamic load rating C is, by
        definition, the load giving an L10 of one million revolutions, so the
        load-life relation (Shigley Ch. 11) normalises to (C/P)^a with
        a = 3 for ball bearings and a = 10/3 for roller bearings. Doubling
        the load cuts a ball bearing's life by 2^3 = 8.

        :param dynamic_load_rating: catalogue basic dynamic load rating C [N]
        :param equivalent_load: equivalent dynamic bearing load P [N]
        :param bearing_type: ``"ball"`` (a = 3) or ``"roller"`` (a = 10/3)
        :returns: L10 life [million rev]
        :raises ValueError: if either load is not positive
        """
        if dynamic_load_rating <= 0 or equivalent_load <= 0:
            raise ValueError("dynamic_load_rating and equivalent_load must be positive")
        exponent = self._LIFE_EXPONENT[bearing_type]
        return (dynamic_load_rating / equivalent_load) ** exponent

    def bearing_l10_life_hours(
        self,
        *,
        dynamic_load_rating: float,
        equivalent_load: float,
        speed_rpm: float,
        bearing_type: Literal["ball", "roller"] = "ball",
    ) -> float:
        """Bearing rating life in operating hours: L10h = L10 * 1e6 / (60 * n).

        Converts the revolution life from ``bearing_l10_life`` to hours at a
        constant shaft speed n (rev/min, so 60*n revolutions per hour).

        :param dynamic_load_rating: catalogue basic dynamic load rating C [N]
        :param equivalent_load: equivalent dynamic bearing load P [N]
        :param speed_rpm: shaft speed n [rev/min]
        :param bearing_type: ``"ball"`` or ``"roller"``
        :returns: L10 life [h]
        :raises ValueError: for non-positive loads or speed
        """
        if speed_rpm <= 0:
            raise ValueError("speed_rpm must be positive")
        revolutions = self.bearing_l10_life(
            dynamic_load_rating=dynamic_load_rating,
            equivalent_load=equivalent_load,
            bearing_type=bearing_type,
        )
        return revolutions * 1e6 / (60 * speed_rpm)

    def bearing_required_load_rating(
        self,
        *,
        equivalent_load: float,
        life_hours: float,
        speed_rpm: float,
        bearing_type: Literal["ball", "roller"] = "ball",
    ) -> float:
        """Catalogue rating C needed to reach a target L10 life: C = P * L10^(1/a).

        The load-life relation turned around for selection: work out the
        design life in millions of revolutions, L10 = 60 * n * Lh / 1e6, then
        pick a bearing whose catalogue C is at least this value.

        :param equivalent_load: equivalent dynamic bearing load P [N]
        :param life_hours: required L10 life Lh [h]
        :param speed_rpm: shaft speed n [rev/min]
        :param bearing_type: ``"ball"`` or ``"roller"``
        :returns: minimum basic dynamic load rating C [N]
        :raises ValueError: for non-positive inputs
        """
        if equivalent_load <= 0 or life_hours <= 0 or speed_rpm <= 0:
            raise ValueError("equivalent_load, life_hours and speed_rpm must be positive")
        life_million_rev = 60 * speed_rpm * life_hours / 1e6
        return equivalent_load * life_million_rev ** (1 / self._LIFE_EXPONENT[bearing_type])

    # --- Welds ---------------------------------------------------------------

    def fillet_weld_shear_stress(
        self, *, force: float, leg_size: float, weld_length: float
    ) -> float:
        """Average shear stress on a fillet weld throat: tau = F / (0.707 * h * L).

        The throat is the smallest section of a 45-degree fillet: t = h *
        cos 45 = 0.707*h for leg size h. The conventional design rule
        (Shigley Sec. 9-3, and the AWS/AISC codes) treats the load on the
        throat area 0.707*h*L as pure shear for *both* parallel (load along
        the weld) and transverse (load across the weld) fillets. That is
        exact enough for parallel welds and conservative for transverse ones,
        which are in fact about a third stronger.

        :param force: load carried by the weld group F [N]
        :param leg_size: fillet leg size h [m]
        :param weld_length: total effective length of weld L [m]
            (add up every bead that shares the load)
        :returns: throat shear stress tau [Pa]
        :raises ValueError: if leg size or length is not positive
        """
        if leg_size <= 0 or weld_length <= 0:
            raise ValueError("leg_size and weld_length must be positive")
        throat = leg_size * math.cos(math.radians(45.0))
        return force / (throat * weld_length)
