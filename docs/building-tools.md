<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# From calculation to tool

You have a calculation that works. Other people want to use it. This guide
takes **one calculation**, the pressure drop of water in a pipe, up five rungs
of a ladder. Each rung is a working file you can run.

| Rung | File | Who can use it | Effort |
| --- | --- | --- | --- |
| 1. Script | [`examples/tools/step1_script.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/tools/step1_script.py) | You | Minutes |
| 2. Command line | [`examples/tools/step2_cli.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/tools/step2_cli.py) | Anyone with a terminal, other programs | + 20 lines |
| 3. Desktop GUI | [`examples/tools/step3_gui.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/tools/step3_gui.py) | Colleagues who avoid terminals | + 60 lines |
| 4. Web app | [`examples/tools/step4_web_app.py`](https://github.com/kovirlabs/first-principles-code/blob/main/examples/tools/step4_web_app.py) | Anyone with a link | + 50 lines and a server |
| 5. Installed command | [`fpc/cli.py`](https://github.com/kovirlabs/first-principles-code/blob/main/fpc/cli.py) + `[project.scripts]` | Anyone who installs the package | + 5 lines of config |

**The rule that makes the ladder cheap:** the engineering lives in the library
(`Fluids.pipe_flow`), and every rung is a thin front end that collects inputs,
converts units, calls the library, and displays results. When the math changes,
you fix it in one place and every front end gets the fix, and the library tests
in `tests/` protect all five front ends at once.

---

## Rung 1: script

```bash
uv run examples/tools/step1_script.py
```

Inputs are constants at the top of the file. This is the right tool for a
one-off answer and for exploring. You have outgrown it when you catch yourself
editing the file to run a second case, or copying it to make `_v2`.

For a fuller starting point (inputs dict, report, plot, CSV export), copy
[`templates/engineering_script.py`](https://github.com/kovirlabs/first-principles-code/blob/main/templates/engineering_script.py).

## Rung 2: command-line tool (`argparse`)

```bash
uv run examples/tools/step2_cli.py --help
uv run examples/tools/step2_cli.py --flow-l-s 12 --diameter-mm 102.3 --length-m 120
```

`argparse` is in the standard library. You declare each input once (name, type,
default, help text) and you get validation, error messages, and `--help` for
free. Key habits shown in the file:

- **Units in flag names** (`--diameter-mm`). Convert to SI immediately after parsing.
- **`main(argv=None)`**: passing a list instead of the real command line makes
  the tool testable without a subprocess (see `tests/test_cli.py`).
- A CLI can be **scripted**: a shell loop or a batch file can run 200 cases.

When the CLI grows many subcommands, [Typer](https://typer.tiangolo.com/)
builds the same thing from type hints with less code.

## Rung 3: desktop GUI (`tkinter`)

```bash
uv run examples/tools/step3_gui.py
```

`tkinter` ships with Python, so there is nothing to install. The form is built
from a `FIELDS` dict: adding an input is one line. The essential GUI habit is
**handling bad input**. Typed text might be `"abc"`, so the button handler
catches `ValueError` and shows a message instead of crashing.

The project's [`gui.py`](https://github.com/kovirlabs/first-principles-code/blob/main/gui.py) is the open-ended version: a MATLAB-style
console where you type any expression. Use a form like this one when users
need one specific calculation.

## Rung 4: web app (Streamlit)

```bash
uv sync --group apps                                 # one-time: installs streamlit
uv run streamlit run examples/tools/step4_web_app.py
```

[Streamlit](https://streamlit.io/) reruns your script every time a widget
changes, so the app reads like a plain script where widgets return values. It
also makes it natural to show a curve (pressure drop across a range of flows)
instead of one number.

To share it, deploy to [Streamlit Community Cloud](https://streamlit.io/cloud)
or an internal server. Check your organization's data policy before putting
engineering data on a public host.

## Rung 5: installed command (`[project.scripts]`)

The final step turns the tool into a command that installs with the package.
[`fpc/cli.py`](https://github.com/kovirlabs/first-principles-code/blob/main/fpc/cli.py) is rung 2 moved *inside* the package and extended
with subcommands. One table in `pyproject.toml` registers it:

```toml
[project.scripts]
fpc = "fpc.cli:main"
```

```bash
uv sync                      # in this repo: the `fpc` command is now available
uv run fpc --help
uv run fpc pipe-flow --flow-l-s 12 --diameter-mm 102.3 --length-m 120
uv run fpc water --temperature-c 37

# Anywhere else: install it as a standalone tool
uv tool install git+https://github.com/kovirlabs/first-principles-code
fpc water --temperature-c 37
```

### Beyond the ladder

- **A single `.exe` for people without Python:**
  [PyInstaller](https://pyinstaller.org/) bundles a script and its
  dependencies (`uvx pyinstaller --onefile examples/tools/step3_gui.py`).
  Expect large files and test on the target operating system.
- **Notebooks** ([`notebooks/`](https://github.com/kovirlabs/first-principles-code/tree/main/notebooks)) are a different kind of tool:
  a calculation and its explanation in one shareable document.
- **Reuse in another project:** see "Use this library in your own project" in
  the README.
