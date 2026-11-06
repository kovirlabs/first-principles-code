# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""properties.py - look up reference data from cited tables.

Engineers spend a lot of time reading values off tables: steam tables,
material data sheets, steel-section catalogues. This class loads those tables
from the CSV files in ``fpc/data/`` with **pandas** and answers questions about
them. It teaches three things:

    * **pandas basics** - read a CSV into a DataFrame, select rows with a
      boolean mask, sort, and turn a row into a plain dict.
    * **Interpolation** - a table only lists some temperatures; to get a value
      in between you interpolate. ``np.interp`` does straight-line (linear)
      interpolation; ``scipy.interpolate.CubicSpline`` fits a smooth curve.
    * **Data, not constants** - keeping numbers in cited data files (see
      ``fpc/data/README.md``) instead of buried in code makes them easy to
      check, update, and trust.

Example::

    from fpc import Properties

    props = Properties()
    props.water_liquid(temperature_c=37, property="dynamic_viscosity_pa_s")
    props.material(name="aluminum_6061_t6")["yield_strength_mpa"]   # 276
    props.lightest_w_shape(required_sx_in3=30)["designation"]        # 'W16x26'
"""

from functools import cache
from importlib import resources

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline


class Properties:
    """Reference-table lookups (water, materials, steel sections) with interpolation."""

    # The tables shipped in fpc/data/, keyed by a short name.
    TABLES = {
        "water_saturation": "water_saturation.csv",
        "water_liquid_1atm": "water_liquid_1atm.csv",
        "materials": "materials.csv",
        "w_shapes": "w_shapes.csv",
    }

    def list_tables(self):
        """Return the names of the available reference tables.

        :returns: list of table names you can pass to :meth:`load_table`
        """
        return list(self.TABLES)

    def load_table(self, *, name):
        """Load one reference table as a pandas DataFrame.

        A DataFrame is a spreadsheet-like table: named columns, numbered rows.
        Try ``frame.head()``, ``frame.describe()``, or ``frame["column"]``.

        :param name: a table name from :meth:`list_tables`
        :returns: a fresh ``pandas.DataFrame`` (safe to modify)
        :raises ValueError: if the table name is unknown
        """
        if name not in self.TABLES:
            raise ValueError(f"unknown table {name!r}; choose from {self.list_tables()}")
        # Return a copy so a caller editing their DataFrame cannot corrupt the
        # cached original that every other call shares.
        return _read_table(self.TABLES[name]).copy()

    # --- Interpolation ----------------------------------------------------
    def interpolate(self, *, table, x_column, y_column, x, method="linear"):
        """Interpolate ``y_column`` at ``x`` using any loaded table.

        This is the general tool the water lookups below are built on.

        :param table: a table name (str) or a DataFrame you loaded yourself
        :param x_column: the column to look up by (must be increasing)
        :param y_column: the column whose value you want
        :param x: the lookup value - a number or a NumPy array of numbers
        :param method: ``"linear"`` (np.interp, like reading a printed table by
            hand) or ``"cubic"`` (scipy CubicSpline, smoother for curved data)
        :returns: the interpolated value(s), same shape as ``x``
        :raises ValueError: if ``x`` is outside the table (we refuse to
            extrapolate, because guessing beyond the data is a common source
            of silently wrong answers)
        """
        frame = self.load_table(name=table) if isinstance(table, str) else table
        xs = frame[x_column].to_numpy(dtype=float)
        ys = frame[y_column].to_numpy(dtype=float)

        # Guard against extrapolation: np.interp would quietly clamp to the
        # end values, and a spline would happily invent numbers.
        x_array = np.asarray(x, dtype=float)
        if np.any(x_array < xs.min()) or np.any(x_array > xs.max()):
            raise ValueError(
                f"{x_column}={x} is outside the table range "
                f"[{xs.min()}, {xs.max()}]; refusing to extrapolate"
            )

        if method == "linear":
            result = np.interp(x_array, xs, ys)
        elif method == "cubic":
            result = CubicSpline(xs, ys)(x_array)
        else:
            raise ValueError("method must be 'linear' or 'cubic'")
        # Hand back a plain float for a scalar input, an array otherwise.
        return float(result) if result.ndim == 0 else result

    def water_saturation(self, *, temperature_c, property, method="linear"):
        """Saturated-water property at a temperature (a steam-table lookup).

        Columns: ``pressure_kpa``, ``density_liquid_kg_m3``,
        ``density_vapor_kg_m3``, ``enthalpy_liquid_kj_kg``,
        ``enthalpy_vaporization_kj_kg``, ``enthalpy_vapor_kj_kg``.

        :param temperature_c: temperature [degC], 0.01 to 200
        :param property: one of the column names above
        :param method: ``"linear"`` or ``"cubic"``
        :returns: the property value in the units named by the column
        """
        return self.interpolate(
            table="water_saturation",
            x_column="temperature_c",
            y_column=property,
            x=temperature_c,
            method=method,
        )

    def water_liquid(self, *, temperature_c, property, method="linear"):
        """Liquid water property at 1 atm and a given temperature.

        Columns: ``density_kg_m3``, ``dynamic_viscosity_pa_s``,
        ``specific_heat_j_kg_k``, ``thermal_conductivity_w_m_k``.

        :param temperature_c: temperature [degC], 1 to 99
        :param property: one of the column names above
        :param method: ``"linear"`` or ``"cubic"``
        :returns: the property value in the units named by the column
        """
        return self.interpolate(
            table="water_liquid_1atm",
            x_column="temperature_c",
            y_column=property,
            x=temperature_c,
            method=method,
        )

    # --- Row lookups ------------------------------------------------------
    def material(self, *, name):
        """Return one material's properties as a plain dictionary.

        :param name: the ``name`` column value, e.g. ``"steel_a36"``
        :returns: dict of column -> value (units are in the column names)
        :raises ValueError: if no material has that name
        """
        frame = self.load_table(name="materials")
        # A boolean mask: a True/False Series, one entry per row. Indexing the
        # DataFrame with it keeps only the True rows.
        match = frame[frame["name"] == name]
        if match.empty:
            raise ValueError(f"unknown material {name!r}; choose from {list(frame['name'])}")
        return match.iloc[0].to_dict()

    def lightest_w_shape(self, *, required_sx_in3):
        """Pick the lightest AISC W-shape with enough section modulus.

        Beam selection in one pandas chain: filter to sections that are strong
        enough, sort by weight, take the first row.

        :param required_sx_in3: minimum elastic section modulus Sx [in^3]
        :returns: dict describing the chosen section
        :raises ValueError: if nothing in the table is strong enough
        """
        shapes = self.load_table(name="w_shapes")
        candidates = shapes[shapes["sx_in3"] >= required_sx_in3]
        if candidates.empty:
            raise ValueError(f"no W-shape in the table has Sx >= {required_sx_in3} in^3")
        # Sort by weight, then by Sx (descending) so ties go to the stronger beam.
        best = candidates.sort_values(["weight_lb_ft", "sx_in3"], ascending=[True, False]).iloc[0]
        return best.to_dict()


@cache
def _read_table(file_name):
    """Read a CSV from the package's data folder (cached after the first read).

    ``importlib.resources`` finds files *inside an installed package*, so this
    works whether fpc is run from this repo or installed into another project.
    ``functools.cache`` remembers the result so each file is parsed only once.
    """
    path = resources.files("fpc").joinpath("data", file_name)
    with path.open("r", encoding="utf-8") as handle:
        return pd.read_csv(handle)
