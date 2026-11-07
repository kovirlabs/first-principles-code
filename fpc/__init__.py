# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""First Principles Code engineering library.

Each module in this package holds one class for one engineering domain. Import
the class you need, create an instance, and call its methods::

    from fpc.dynamics import Dynamics
    from fpc.statics import Statics

    dyn = Dynamics()
    x = dyn.displacement_constant_acceleration(
        initial_position=0.0, initial_velocity=5.0,
        acceleration=9.81, time=3.0,
    )

The classes are intentionally lightweight (no shared state) so that each method
reads as a self-contained, well-documented worked example.
"""

from importlib.metadata import PackageNotFoundError, version

# The version number lives in one place, pyproject.toml. Installed packages
# carry it as metadata, so read it from there instead of repeating it here.
try:
    __version__ = version("first-principles-code")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0+unknown"

# Re-export the domain classes so callers can also write
# ``from fpc import Dynamics``. Keeping this list in one place documents
# everything the library currently offers.
from fpc.beam import Beam
from fpc.controls import Controls
from fpc.ct import CT

# Design (root finding / optimization) and reference-data lookups.
from fpc.design import Design
from fpc.dicom import Dicom
from fpc.dynamics import Dynamics
from fpc.electrical import Electrical
from fpc.fluids import Fluids
from fpc.gear import Gear
from fpc.material import Material
from fpc.mechatronics import Mechatronics
from fpc.modal import Modal
from fpc.mri import MRI
from fpc.properties import Properties

# Medical imaging / radiology classes.
from fpc.radiation import Radiation
from fpc.radiography import Radiography
from fpc.statics import Statics
from fpc.thermo import Thermo
from fpc.ultrasound import Ultrasound

# Unit-aware modelling: the shared Pint registry and the Beam dataclass.
from fpc.units import Q_, ureg
from fpc.utility import Utility

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
    "Design",
    "Properties",
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
