# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""gui.py - a small MATLAB/Maplesoft-style console for this project.

Run it with::

    uv run gui.py

What it gives you (a free, open-source take on the MATLAB command window):

    * A command box where you type a Python expression or statement and press
      Run (or Enter). Results print to a scrolling session log.
    * A "Workspace" table that records every expression result so you can see
      your session at a glance - much like MATLAB's workspace pane.
    * Buttons to open a .py file into the command box, run it, clear the log,
      and EXPORT the recorded results to CSV or JSON (via fpc.Utility).

The interpreter namespace comes preloaded with ``math``, ``numpy as np``, and an
instance of every engineering class in ``fpc`` (lower-cased: ``dyn``,
``statics``, ``thermo``, ...), so you can start computing immediately, e.g.::

    dyn.projectile_range(speed=20, angle_deg=45)
    np.linspace(0, 1, 5)
    x = thermo.carnot_efficiency(hot_temperature=800, cold_temperature=300)

The evaluation engine (the ``Session`` class) is deliberately separated from the
Tk widgets so its logic is plain, testable Python.
"""

import contextlib
import io
import math

import numpy as np

# Pull in the whole engineering library plus the file/export helper.
from fpc import (
    CT,
    MRI,
    Controls,
    Design,
    Dicom,
    Dynamics,
    Electrical,
    Fatigue,
    Fluids,
    Gear,
    MachineElements,
    Material,
    Mechatronics,
    Modal,
    Properties,
    Psychrometrics,
    Radiation,
    Radiography,
    Statics,
    Thermo,
    Ultrasound,
    Utility,
)


class Session:
    """Headless evaluation engine: runs code against a persistent namespace.

    Kept independent of tkinter so the "run a line of code and record the
    result" behaviour can be exercised without a display.
    """

    def __init__(self):
        # The namespace every command runs against. Preload the tools so the
        # user does not have to import anything.
        self.namespace = {
            "math": math,
            "np": np,
            "Utility": Utility,
            # One ready-to-use instance of each domain class.
            "dyn": Dynamics(),
            "statics": Statics(),
            "modal": Modal(),
            "thermo": Thermo(),
            "fluids": Fluids(),
            "material": Material(),
            "gear": Gear(),
            "machine": MachineElements(),
            "fatigue": Fatigue(),
            "psychro": Psychrometrics(),
            "electrical": Electrical(),
            "mechatronics": Mechatronics(),
            "controls": Controls(),
            "design": Design(),
            "props": Properties(),
            # Radiology / medical imaging.
            "radiation": Radiation(),
            "radiography": Radiography(),
            "ct": CT(),
            "mri": MRI(),
            "ultrasound": Ultrasound(),
            "dicom": Dicom(),
        }
        # Recorded (label, command, result-as-text) for the workspace + export.
        self.records = []
        self._counter = 0  # numbers the auto-generated output labels

    def run(self, *, source):
        """Execute one chunk of code and return a result dictionary.

        We try to ``eval`` it first (an expression that produces a value); if
        that raises SyntaxError it is a statement (e.g. an assignment or loop),
        so we ``exec`` it instead. Anything the code prints is captured too.

        :param source: the Python source text to run
        :returns: dict with keys ``label``, ``command``, ``value`` (text or
            None), ``output`` (captured stdout), and ``error`` (text or None)
        """
        source = source.strip()
        if not source:
            return {"label": None, "command": "", "value": None, "output": "", "error": None}

        captured = io.StringIO()
        value_text = None
        error_text = None
        label = None

        try:
            # Redirect print() output so we can show it in the log.
            with contextlib.redirect_stdout(captured):
                try:
                    # Expression path: compile in "eval" mode and capture value.
                    code_obj = compile(source, "<console>", "eval")
                    value = eval(code_obj, self.namespace)
                    if value is not None:
                        self._counter += 1
                        label = f"out{self._counter}"
                        value_text = repr(value)
                        # Store the live value under its label so it can be
                        # reused in later commands, just like MATLAB's ans.
                        self.namespace[label] = value
                except SyntaxError:
                    # Statement path: assignments, loops, defs, imports, ...
                    exec(compile(source, "<console>", "exec"), self.namespace)
        except Exception as exc:  # noqa: BLE001 - surface any runtime error
            # Report the error to the user instead of crashing the GUI.
            error_text = f"{type(exc).__name__}: {exc}"

        result = {
            "label": label,
            "command": source,
            "value": value_text,
            "output": captured.getvalue(),
            "error": error_text,
        }

        # Only record successful, value-producing expressions in the workspace.
        if error_text is None and value_text is not None:
            self.records.append((label, source, value_text))

        return result

    def export_csv(self, *, file_path):
        """Write the recorded results to a CSV file using fpc.Utility.

        :param file_path: destination .csv path
        :returns: the file path written
        """
        utility = Utility()
        return utility.export_csv(
            rows=self.records,
            file_path=file_path,
            header=["label", "command", "result"],
        )

    def export_json(self, *, file_path):
        """Write the recorded results to a JSON file using fpc.Utility.

        :param file_path: destination .json path
        :returns: the file path written
        """
        utility = Utility()
        data = [
            {"label": label, "command": command, "result": result}
            for label, command, result in self.records
        ]
        return utility.dict_to_json(data=data, file_path=file_path)


# ---------------------------------------------------------------------------
# Everything below is the tkinter front-end. It is imported lazily inside
# ``launch`` so that importing this module (e.g. to test ``Session``) does not
# require a display.
# ---------------------------------------------------------------------------


def launch():
    """Build and run the GUI. Returns nothing; blocks until the window closes."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class ConsoleApp:
        """The Tk application window wrapping a :class:`Session`."""

        def __init__(self, root):
            self.root = root
            self.session = Session()
            root.title("First Principles Code - Console")
            root.geometry("900x620")

            self._build_toolbar()
            self._build_log_and_workspace()
            self._build_command_bar()

            self._log(
                "Ready. Preloaded: math, np, and dyn/statics/thermo/... "
                "Type an expression and press Run (or Enter).\n"
                "Example:  dyn.projectile_range(speed=20, angle_deg=45)\n" + "-" * 70 + "\n"
            )

        # --- UI construction ------------------------------------------------
        def _build_toolbar(self):
            """Top row of action buttons."""
            bar = ttk.Frame(self.root, padding=(8, 6))
            bar.pack(side=tk.TOP, fill=tk.X)
            ttk.Button(bar, text="Open Script", command=self.open_script).pack(side=tk.LEFT)
            ttk.Button(bar, text="Run Script", command=self.run_script).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT)
            ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
            ttk.Button(bar, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT)
            ttk.Button(bar, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=4)

        def _build_log_and_workspace(self):
            """Center area: scrolling log on the left, workspace table on the right."""
            middle = ttk.Frame(self.root)
            middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8)

            # Session log (read-only text with a scrollbar).
            log_frame = ttk.LabelFrame(middle, text="Session log")
            log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.log = tk.Text(
                log_frame, wrap=tk.WORD, height=20, font=("monospace", 10), state=tk.DISABLED
            )
            log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
            self.log.configure(yscrollcommand=log_scroll.set)
            log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Workspace table (one row per recorded result).
            ws_frame = ttk.LabelFrame(middle, text="Workspace")
            ws_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
            self.workspace = ttk.Treeview(
                ws_frame,
                columns=("label", "result"),
                show="headings",
                height=20,
            )
            self.workspace.heading("label", text="Name")
            self.workspace.heading("result", text="Result")
            self.workspace.column("label", width=70, anchor=tk.W)
            self.workspace.column("result", width=220, anchor=tk.W)
            self.workspace.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _build_command_bar(self):
            """Bottom row: the command entry and the Run button."""
            bar = ttk.Frame(self.root, padding=(8, 6))
            bar.pack(side=tk.BOTTOM, fill=tk.X)
            ttk.Label(bar, text=">>>").pack(side=tk.LEFT)
            self.command = ttk.Entry(bar, font=("monospace", 11))
            self.command.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
            # Pressing Enter in the box runs the command too.
            self.command.bind("<Return>", lambda event: self.run_command())
            self.command.focus()
            ttk.Button(bar, text="Run", command=self.run_command).pack(side=tk.LEFT)

        # --- Actions --------------------------------------------------------
        def run_command(self):
            """Execute whatever is in the command box and show the result."""
            source = self.command.get()
            if not source.strip():
                return
            self._log(f">>> {source}\n")
            self._show_result(self.session.run(source=source))
            self.command.delete(0, tk.END)

        def run_script(self):
            """Run the entire contents of the command box as a script."""
            source = self.command.get()
            self._log(f"# running script ({len(source)} chars)\n")
            self._show_result(self.session.run(source=source))

        def open_script(self):
            """Load a .py file's text into the command box via a file dialog."""
            path = filedialog.askopenfilename(
                title="Open a Python script",
                filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            )
            if not path:
                return
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.command.delete(0, tk.END)
            self.command.insert(0, text)
            self._log(f"# loaded {path}\n")

        def export_csv(self):
            """Save recorded results to a CSV file chosen by the user."""
            self._export(kind="csv")

        def export_json(self):
            """Save recorded results to a JSON file chosen by the user."""
            self._export(kind="json")

        def clear_log(self):
            """Empty the session log (the workspace table is left intact)."""
            self.log.configure(state=tk.NORMAL)
            self.log.delete("1.0", tk.END)
            self.log.configure(state=tk.DISABLED)

        # --- Helpers --------------------------------------------------------
        def _export(self, *, kind):
            """Shared logic for the two export buttons."""
            if not self.session.records:
                messagebox.showinfo(
                    "Nothing to export", "Run some expressions first - the workspace is empty."
                )
                return
            extension = ".csv" if kind == "csv" else ".json"
            path = filedialog.asksaveasfilename(
                title=f"Export results as {kind.upper()}",
                defaultextension=extension,
                filetypes=[(f"{kind.upper()} files", f"*{extension}")],
            )
            if not path:
                return
            if kind == "csv":
                self.session.export_csv(file_path=path)
            else:
                self.session.export_json(file_path=path)
            self._log(f"# exported {len(self.session.records)} result(s) to {path}\n")

        def _show_result(self, result):
            """Render a Session.run() result dict into the log and workspace."""
            if result["output"]:
                self._log(result["output"])
            if result["error"]:
                self._log(f"!! {result['error']}\n")
            elif result["value"] is not None:
                self._log(f"{result['label']} = {result['value']}\n")
                self.workspace.insert(
                    "",
                    tk.END,
                    values=(result["label"], result["value"]),
                )

        def _log(self, text):
            """Append text to the read-only log and scroll to the bottom."""
            self.log.configure(state=tk.NORMAL)
            self.log.insert(tk.END, text)
            self.log.see(tk.END)
            self.log.configure(state=tk.DISABLED)

    root = tk.Tk()
    ConsoleApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
