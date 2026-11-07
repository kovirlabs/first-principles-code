# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""cli.py - the ``fpc`` command: library calculations from the terminal.

Rung 5 of docs/building-tools.md: a command that is *installed with the
package*. ``pyproject.toml`` maps the name to this module's ``main``::

    [project.scripts]
    fpc = "fpc.cli:main"

so after installing (``uv sync`` here, or ``uv tool install
git+https://github.com/kovirlabs/first-principles-code`` anywhere) you can run::

    fpc --help
    fpc pipe-flow --flow-l-s 12 --diameter-mm 102.3 --length-m 120
    fpc water --temperature-c 37
    fpc search "pipe pressure drop"          # find any calculation in the library
    fpc describe Fluids.reynolds_number      # its inputs, units and formula
    fpc run Fluids.reynolds_number density=998 velocity=2 length=0.05 viscosity=0.001

The last three are generic: they work for *every* method, because they are
driven by ``fpc.registry`` (a catalogue built from the code's own signatures
and docstrings) instead of hand-written argument lists.

Subcommands (``argparse`` "subparsers") let one program offer several tools,
the way ``git commit`` and ``git push`` share the ``git`` command.
"""

import argparse
import json

from fpc import registry
from fpc.fluids import Fluids
from fpc.properties import Properties


def _pipe_flow(args):
    """Handle ``fpc pipe-flow``."""
    props = Properties()
    t = args.temperature_c
    result = Fluids().pipe_flow(
        flow=args.flow_l_s / 1000,
        diameter=args.diameter_mm / 1000,
        length=args.length_m,
        roughness=args.roughness_mm / 1000,
        density=props.water_liquid(temperature_c=t, property="density_kg_m3"),
        viscosity=props.water_liquid(temperature_c=t, property="dynamic_viscosity_pa_s"),
    )
    print(f"velocity        {result['velocity']:.3f} m/s")
    print(f"Reynolds        {result['reynolds']:.0f}")
    print(f"friction factor {result['friction_factor']:.4f}")
    print(f"head loss       {result['head_loss']:.3f} m")
    print(f"pressure drop   {result['pressure_drop'] / 1000:.2f} kPa")


def _water(args):
    """Handle ``fpc water``: print every liquid-water property at a temperature."""
    props = Properties()
    columns = props.load_table(name="water_liquid_1atm").columns.drop("temperature_c")
    print(f"Liquid water at {args.temperature_c} degC, 1 atm")
    for column in columns:
        value = props.water_liquid(temperature_c=args.temperature_c, property=column)
        print(f"  {column:<28} {value:.5g}")


def _search(args):
    """Handle ``fpc search``: list calculations matching some keywords."""
    for calc in registry.search(args.query, limit=args.limit, domain=args.domain):
        print(f"{calc.key:<45} {calc.summary}")


def _describe(args):
    """Handle ``fpc describe``: show one calculation's inputs and units."""
    try:
        calc = registry.get(args.key)
    except KeyError as error:
        raise SystemExit(f"error: {error.args[0]}") from error
    print(calc.key)
    print()
    print(calc.description)
    print()
    print("Inputs:")
    for p in calc.parameters:
        default = "" if p.required else f"  (default {p.default!r})"
        print(f"  {p.name:<24} {p.description}{default}")
    print()
    print(f"Returns: {calc.returns}")


def _parse_value(text):
    """Turn ``"998"`` into 998, ``"[1, 2]"`` into a list, and leave words as strings.

    JSON already knows how to read numbers, lists and true/false, so we try
    it first and fall back to the raw text (e.g. ``property=density_kg_m3``).
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _run(args):
    """Handle ``fpc run``: call any calculation with ``name=value`` pairs."""
    arguments = {}
    for pair in args.arguments:
        name, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"expected name=value, got {pair!r}")
        arguments[name] = _parse_value(value)
    try:
        result = registry.calculate(args.key, arguments)
    except (KeyError, ValueError, TypeError) as error:
        raise SystemExit(f"error: {error}") from error
    print(json.dumps(result, indent=2))


def _llms_txt(args):
    """Handle ``fpc llms-txt``: print the AI-assistant index of the library."""
    print(registry.llms_txt(), end="")


def build_parser():
    """Build the top-level parser with one subparser per tool."""
    parser = argparse.ArgumentParser(
        prog="fpc",
        description="First Principles Code engineering calculations.",
    )
    tools = parser.add_subparsers(dest="tool", required=True)

    pipe = tools.add_parser("pipe-flow", help="pressure drop of water in a straight pipe")
    pipe.add_argument("--flow-l-s", type=float, required=True, help="flow rate [L/s]")
    pipe.add_argument("--diameter-mm", type=float, required=True, help="inner diameter [mm]")
    pipe.add_argument("--length-m", type=float, required=True, help="pipe length [m]")
    pipe.add_argument(
        "--roughness-mm",
        type=float,
        default=0.045,
        help="absolute roughness [mm] (default 0.045, commercial steel)",
    )
    pipe.add_argument(
        "--temperature-c", type=float, default=20.0, help="water temperature [degC] (default 20)"
    )
    # set_defaults(handler=...) attaches the function that runs this tool.
    pipe.set_defaults(handler=_pipe_flow)

    water = tools.add_parser("water", help="liquid water properties at 1 atm")
    water.add_argument(
        "--temperature-c", type=float, required=True, help="temperature [degC], 1 to 99"
    )
    water.set_defaults(handler=_water)

    search = tools.add_parser("search", help="find calculations by keyword")
    search.add_argument("query", help='words to look for, e.g. "beam deflection"')
    search.add_argument("--domain", help="only search one class, e.g. Fluids")
    search.add_argument("--limit", type=int, default=10, help="maximum results (default 10)")
    search.set_defaults(handler=_search)

    describe = tools.add_parser("describe", help="show a calculation's inputs and units")
    describe.add_argument("key", help="Domain.method, e.g. Fluids.reynolds_number")
    describe.set_defaults(handler=_describe)

    run = tools.add_parser("run", help="run any calculation with name=value arguments")
    run.add_argument("key", help="Domain.method, e.g. Fluids.reynolds_number")
    run.add_argument("arguments", nargs="*", help="inputs as name=value (SI units unless stated)")
    run.set_defaults(handler=_run)

    llms = tools.add_parser("llms-txt", help="print a compact index of the library for AI tools")
    llms.set_defaults(handler=_llms_txt)
    return parser


def main(argv=None):
    """Entry point for the ``fpc`` command.

    :param argv: list of arguments (defaults to the real command line);
        tests pass a list so they do not need a subprocess
    """
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
