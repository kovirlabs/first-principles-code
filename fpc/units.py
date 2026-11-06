# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""units.py - one shared Pint unit registry for the whole project.

Pint attaches physical units to numbers, so ``5 * meter`` knows it is a length,
converts itself (``.to("mm")``), and *refuses* to add a length to a time. This
catches the unit-mismatch mistakes that plain floats silently let through.

IMPORTANT: Pint quantities can only be combined if they come from the SAME
registry. So the project defines exactly one here and everything imports it::

    from fpc.units import ureg, Q_

    length = 2 * ureg.meter          # or:  Q_(2, "meter")
    force = Q_(1000, "newton")
    print((force / length).to("N/mm"))
"""

from pint import UnitRegistry

# The single registry shared across the project. The annotation tells type
# checkers (mypy, your editor) what this object is; UnitRegistry is generic,
# so a bare ``UnitRegistry()`` leaves them guessing.
ureg: UnitRegistry = UnitRegistry()

# ``Q_`` is the conventional short alias for building a quantity from a value
# and a unit string, e.g. ``Q_(200, "GPa")``.
Q_ = ureg.Quantity
