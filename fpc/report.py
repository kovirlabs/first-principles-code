# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""report.py - file a calculation the way a checked hand calc is filed.

An engineering calculation that goes into a design file needs more than its
answer: a reviewer must see *what* was calculated, *which* equation and
assumptions were used, every input *with its unit*, the result, and where the
method comes from. This module writes all of that as a Markdown "calc sheet"
from any calculation in the registry, because the registry already knows the
formula text, the inputs, and their units from the docstrings.

Markdown is plain text, so the sheet can be committed next to the code,
diffed, and reviewed in a pull request. Turn it into a PDF or Word file with
`pandoc <https://pandoc.org>`_ when one is needed::

    fpc report Fluids.reynolds_number density=998 velocity=2 length=0.05 \\
        viscosity=0.001 --out reynolds.md
    pandoc reynolds.md -o reynolds.pdf

From Python::

    from fpc.report import calc_report

    text = calc_report("Thermo.conduction_heat_rate",
                       {"conductivity": 0.72, "area": 12,
                        "delta_temperature": 25, "thickness": 0.2},
                       title="Heat loss through the north wall")

Techniques shown: building text with f-strings and ``str.join``, Markdown
tables, ``datetime.date`` and ``importlib.metadata`` for the record of *when*
and *with which version* a result was produced.
"""

import datetime
from collections.abc import Mapping
from typing import Any

import fpc
from fpc import registry
from fpc.uncertainty import MonteCarloResult


def _number(value: Any) -> str:
    """Six significant figures for numbers; anything else as written."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return f"`{value}`" if isinstance(value, str) else str(value)
    return f"{value:.6g}"


def _cell(text: str) -> str:
    """Make text safe inside a Markdown table cell (no pipes, one line)."""
    return " ".join(text.replace("|", "\\|").split())


def _result_section(result: Any, returns: str) -> list[str]:
    """Lines describing the result: one value, or a table for several."""
    lines = [f"Returns: {returns}", ""]
    if isinstance(result, dict):
        lines += ["| Quantity | Value |", "|---|---:|"]
        lines += [f"| {name} | {_number(value)} |" for name, value in result.items()]
    elif isinstance(result, list) and all(not isinstance(v, list | dict) for v in result):
        lines += ["| # | Value |", "|---|---:|"]
        lines += [f"| {i} | {_number(value)} |" for i, value in enumerate(result)]
    else:
        lines.append(f"**Result: {_number(result)}**")
    return lines


def calc_report(
    key: str,
    arguments: Mapping[str, Any],
    *,
    title: str | None = None,
    checked_by: str = "",
    date: datetime.date | None = None,
    uncertainty: MonteCarloResult | None = None,
) -> str:
    """Run a calculation and write it up as a Markdown calc sheet.

    :param key: registry key, e.g. ``"Fluids.reynolds_number"``
    :param arguments: the inputs, each in the unit its docstring gives [input units]
    :param title: heading for the sheet; defaults to the calculation's summary
    :param checked_by: name for the "Checked by" line; blank leaves a line to sign
    :param date: date printed on the sheet; defaults to today
    :param uncertainty: optional result of :func:`fpc.uncertainty.monte_carlo`
        for the same calculation, added as an "Uncertainty" section
    :returns: the sheet as Markdown text
    :raises KeyError: for an unknown key
    :raises ValueError: for missing or unknown inputs
    """
    calc = registry.get(key)
    result = registry.calculate(key, arguments)  # validates the inputs first
    date = date or datetime.date.today()
    by_name = {p.name: p for p in calc.parameters}

    lines = [
        f"# {title or calc.summary}",
        "",
        "| | |",
        "|---|---|",
        f"| Calculation | `{calc.key}` |",
        f"| Method source | `{calc.cls.__module__}.{calc.domain}.{calc.name}` "
        f"(first-principles-code {fpc.__version__}) |",
        f"| Date | {date.isoformat()} |",
        f"| Checked by | {checked_by or '_' * 24} |",
        "",
        "## Method",
        "",
        # The docstring's description holds the equation and its assumptions.
        calc.description,
        "",
        "## Inputs",
        "",
        "| Input | Value | Unit | Description |",
        "|---|---:|---|---|",
    ]
    for name, value in arguments.items():
        p = by_name[name]
        lines.append(f"| `{name}` | {_number(value)} | {p.unit or ''} | {_cell(p.description)} |")
    # Defaults the caller did not override are inputs too; a reviewer must see them.
    for p in calc.parameters:
        if p.name not in arguments and not p.required:
            value = f"{_number(p.default)} (default)"
            lines.append(f"| `{p.name}` | {value} | {p.unit or ''} | {_cell(p.description)} |")

    lines += ["", "## Result", ""] + _result_section(result, calc.returns)

    if uncertainty is not None:
        low, high = uncertainty.interval(95)
        lines += [
            "",
            "## Uncertainty",
            "",
            f"Monte Carlo, {len(uncertainty.samples)} samples.",
            "",
            "| Statistic | Value |",
            "|---|---:|",
            f"| Mean | {_number(uncertainty.mean)} |",
            f"| Standard deviation | {_number(uncertainty.std)} |",
            f"| 95 % interval | {_number(low)} to {_number(high)} |",
            "",
            "Share of the variation from each uncertain input:",
            "",
        ]
        lines += [f"- `{name}`: {share:.0%}" for name, share in uncertainty.sensitivity.items()]

    lines += [
        "",
        "## Review",
        "",
        "- [ ] Inputs and units match the design basis",
        "- [ ] Method and assumptions suit this case",
        "- [ ] Result is plausible (order of magnitude, sign)",
        "",
    ]
    return "\n".join(lines)
