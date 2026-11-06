# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""First Principles Code engineering library.

Each module in this package holds one class for one engineering domain. Import
the class you need, create an instance, and call its methods::

    from library.dynamics import Dynamics
    from library.statics import Statics

    dyn = Dynamics()
    x = dyn.displacement_constant_acceleration(
        initial_position=0.0, initial_velocity=5.0,
        acceleration=9.81, time=3.0,
    )

The classes are intentionally lightweight (no shared state) so that each method
reads as a self-contained, well-documented worked example.
"""

# Re-export the domain classes so callers can also write
# ``from library import Dynamics``. Keeping this list in one place documents
# everything the library currently offers.
from library.dynamics import Dynamics
from library.statics import Statics
from library.modal import Modal
from library.thermo import Thermo
from library.fluids import Fluids
from library.material import Material
from library.gear import Gear
from library.electrical import Electrical
from library.mechatronics import Mechatronics
from library.controls import Controls
from library.utility import Utility

# Medical imaging / radiology classes.
from library.radiation import Radiation
from library.radiography import Radiography
from library.ct import CT
from library.mri import MRI
from library.ultrasound import Ultrasound
from library.dicom import Dicom

# Unit-aware modelling: the shared Pint registry and the Beam dataclass.
from library.units import ureg, Q_
from library.beam import Beam

__all__ = [
    "Dynamics",
    "Statics",
    "Modal",
    "Thermo",
    "Fluids",
    "Material",
    "Gear",
    "Electrical",
    "Mechatronics",
    "Controls",
    "Utility",
    "Radiation",
    "Radiography",
    "CT",
    "MRI",
    "Ultrasound",
    "Dicom",
    "Beam",
    "ureg",
    "Q_",
]
