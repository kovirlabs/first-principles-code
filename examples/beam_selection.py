# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""beam_selection.py - pick a steel W-beam, with units checked by Pint.

QUESTION
    A 6 m simply supported floor beam carries a 40 kN point load at midspan.
    Which is the lightest AISC W-shape that keeps bending stress under the
    allowable and deflection under L/360?

APPROACH
    1. Work in SI with Pint quantities: M = P*L/4, required Sx = M / Fb.
    2. The steel catalogue is in US units (in^3, in^4). Pint converts
       required Sx to in^3 - no hand-typed conversion factors.
    3. Properties.lightest_w_shape() filters and sorts the table with pandas.
    4. Check deflection with that section's Ix; if it fails, step up to the
       next-lightest section that passes both checks.

This mixes unit systems on purpose: it is exactly the situation where Pint
earns its keep (see docs/units.md).

Simplification: Fb = 0.66*Fy is an allowable-stress shortcut for a laterally
braced compact section. A real design follows AISC 360 in full.

Run it:  uv run examples/beam_selection.py
"""

from fpc import Q_, Properties

props = Properties()

# --- Inputs (each one carries its units) ----------------------------------
span = Q_(6.0, "m")
load = Q_(40.0, "kN")
yield_strength = Q_(345, "MPa")  # ASTM A992 steel, Fy = 50 ksi
modulus = Q_(200, "GPa")
deflection_limit = span / 360  # serviceability limit L/360


def deflection(*, section):
    """Midspan deflection P*L^3 / (48*E*I) for a section from the table."""
    ix = Q_(section["ix_in4"], "in**4")  # attach units to the catalogue value
    return (load * span**3 / (48 * modulus * ix)).to("mm")


def main():
    allowable_stress = 0.66 * yield_strength
    max_moment = load * span / 4
    required_sx = (max_moment / allowable_stress).to("in**3")
    print(f"Max moment          M  = {max_moment.to('kN*m'):.1f~P}")
    print(f"Allowable stress    Fb = {allowable_stress.to('MPa'):.0f~P}")
    print(f"Required modulus    Sx >= {required_sx:.1f~P}")
    print(f"Deflection limit       = {deflection_limit.to('mm'):.1f~P}\n")

    # Strength check: the lightest section with enough Sx.
    section = props.lightest_w_shape(required_sx_in3=required_sx.magnitude)
    print(f"Lightest for strength: {section['designation']} (Sx = {section['sx_in3']} in^3)")

    # Serviceability check: does it also meet the deflection limit?
    # If not, walk up the catalogue until one does. Sort exactly like
    # lightest_w_shape: by weight, and for equal weights the stronger first.
    shapes = props.load_table(name="w_shapes").sort_values(
        ["weight_lb_ft", "sx_in3"],
        ascending=[True, False],
    )
    strong_enough = shapes[shapes["sx_in3"] >= required_sx.magnitude]
    for _, candidate in strong_enough.iterrows():
        delta = deflection(section=candidate)
        status = "OK" if delta <= deflection_limit else "too flexible"
        print(f"  {candidate['designation']:>7}: deflection {delta:.1f~P}  -> {status}")
        if delta <= deflection_limit:
            weight = Q_(candidate["weight_lb_ft"], "lbf/ft").to("kgf/m")
            print(f"\nSelected: {candidate['designation']} ({weight.magnitude:.1f} kg/m)")
            return
    print("\nNo section in the table passes - extend data/w_shapes.csv.")


if __name__ == "__main__":
    main()
