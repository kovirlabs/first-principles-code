# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""hints.py - shared type-hint names used across the library.

Type hints (``def area(self, *, width: float, height: float) -> float``) do not
change how Python runs the code. They are documentation that tools can read:

    * **mypy** checks that callers pass the right kinds of values;
    * your **editor** uses them for autocomplete and inline help;
    * ``fpc.registry`` turns them into JSON Schema, which is how an AI model
      (through the MCP server) learns what each calculation expects.

Most methods only need the built-in ``float``, ``int``, ``str`` and ``bool``.
Methods that work on a whole array at once (NumPy "vectorized" maths) use the
two names below, so every module spells "array" the same way.
"""

from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

# Input that may be a single number *or* a sequence of numbers: a float, a list
# of floats, or a NumPy array. NumPy's own ``ArrayLike`` covers all of these,
# so we simply re-export it under this module's roof.
__all__ = ["ArrayLike", "FloatArray"]

# Output that is always a NumPy array of 64-bit floats. Annotating the
# assignment with ``TypeAlias`` tells type checkers this is a type name, not
# an ordinary variable. (Python 3.12 added the shorter ``type FloatArray = ...``
# statement; we use the older spelling because the library supports 3.11.)
FloatArray: TypeAlias = NDArray[np.float64]
