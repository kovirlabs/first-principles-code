# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""utility.py - cross-cutting helper methods.

The Utility class collects the "plumbing" every engineering script needs but
that does not belong to any single physics domain: reading and writing JSON,
exporting results to CSV (so you can open them in a spreadsheet), reading and
writing tables with pandas (CSV or Excel), and popping up
a native file-picker dialog with tkinter.

These methods demonstrate working with the file system, the ``json`` and
``csv`` standard-library modules, and optional GUI dialogs that degrade
gracefully when no display is available (e.g. on a server).
"""

import csv
import json
from pathlib import Path


class Utility:
    """File, data, and dialog helpers for engineering scripts."""

    def json_to_dict(self, *, file_path):
        """Read a JSON file from disk and return it as a Python dictionary.

        :param file_path: path to the .json file
        :returns: parsed data as a dict (or list, matching the JSON's top level)
        """
        # ``with`` guarantees the file is closed even if parsing raises.
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def dict_to_json(self, *, data, file_path, indent=2):
        """Write a dictionary to a JSON file (pretty-printed by default).

        :param data: the dict (or list) to serialise
        :param file_path: destination .json path
        :param indent: spaces of indentation for readability, defaults to 2
        :returns: the file_path that was written, for convenience
        """
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=indent)
        return file_path

    def export_csv(self, *, rows, file_path, header=None):
        """Write a list of rows to a CSV file for use in Excel/Sheets.

        :param rows: iterable of rows, where each row is a list/tuple of values
        :param file_path: destination .csv path
        :param header: optional list of column names written as the first row
        :returns: the file_path that was written
        """
        # newline="" is the documented way to avoid blank lines on Windows.
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if header is not None:
                writer.writerow(header)
            writer.writerows(rows)
        return file_path

    def read_table(self, *, file_path, sheet_name=0):
        """Read a CSV or Excel file into a pandas DataFrame.

        pandas is the standard tool for tabular data (sensor logs, test
        results, property tables). This picks the right reader from the file
        extension so scripts can accept either format.

        :param file_path: path to a ``.csv``, ``.xlsx``, or ``.xls`` file
        :param sheet_name: Excel sheet name or 0-based index, defaults to the
            first sheet (ignored for CSV)
        :returns: a ``pandas.DataFrame``
        :raises ValueError: for an unsupported file extension
        """
        # Import here so `from fpc import Utility` stays fast for scripts that
        # never touch tables.
        import pandas as pd

        suffix = Path(file_path).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file_path)
        if suffix in (".xlsx", ".xls"):
            # Excel support comes from the openpyxl package (a dependency).
            return pd.read_excel(file_path, sheet_name=sheet_name)
        raise ValueError(f"unsupported table format {suffix!r}; use .csv or .xlsx")

    def write_table(self, *, frame, file_path):
        """Write a pandas DataFrame to CSV or Excel, chosen by file extension.

        :param frame: the ``pandas.DataFrame`` to save
        :param file_path: destination ``.csv`` or ``.xlsx`` path
        :returns: the file_path that was written
        :raises ValueError: for an unsupported file extension
        """
        suffix = Path(file_path).suffix.lower()
        # index=False: the row numbers are pandas bookkeeping, not data.
        if suffix == ".csv":
            frame.to_csv(file_path, index=False)
        elif suffix == ".xlsx":
            frame.to_excel(file_path, index=False)
        else:
            raise ValueError(f"unsupported table format {suffix!r}; use .csv or .xlsx")
        return file_path

    def pick_file(self, *, title="Select a file", file_types=(("All files", "*.*"),)):
        """Open a native "open file" dialog and return the chosen path.

        Uses tkinter, which ships with Python. On a headless machine (no
        display) tkinter cannot start, so we catch that and return ``None``
        instead of crashing - the caller can then fall back to a typed path.

        :param title: dialog window title
        :param file_types: list of (label, pattern) tuples to filter by
        :returns: the selected file path as a string, or None if cancelled
        """
        try:
            # Import inside the method so merely importing Utility does not
            # require a GUI toolkit to be available.
            import tkinter as tk
            from tkinter import filedialog
        except ImportError:
            return None

        try:
            root = tk.Tk()
            root.withdraw()  # hide the empty root window; show only the dialog
            path = filedialog.askopenfilename(title=title, filetypes=list(file_types))
            root.destroy()
            # askopenfilename returns "" when the user cancels; normalise to None.
            return path or None
        except tk.TclError:
            # Raised when there is no display available.
            return None
