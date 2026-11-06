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

Subcommands (``argparse`` "subparsers") let one program offer several tools,
the way ``git commit`` and ``git push`` share the ``git`` command.
"""

import argparse

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


def build_parser():
    """Build the top-level parser with one subparser per tool."""
    parser = argparse.ArgumentParser(
        prog="fpc", description="First Principles Code engineering calculations.",
    )
    tools = parser.add_subparsers(dest="tool", required=True)

    pipe = tools.add_parser("pipe-flow", help="pressure drop of water in a straight pipe")
    pipe.add_argument("--flow-l-s", type=float, required=True, help="flow rate [L/s]")
    pipe.add_argument("--diameter-mm", type=float, required=True, help="inner diameter [mm]")
    pipe.add_argument("--length-m", type=float, required=True, help="pipe length [m]")
    pipe.add_argument("--roughness-mm", type=float, default=0.045,
                      help="absolute roughness [mm] (default 0.045, commercial steel)")
    pipe.add_argument("--temperature-c", type=float, default=20.0,
                      help="water temperature [degC] (default 20)")
    # set_defaults(handler=...) attaches the function that runs this tool.
    pipe.set_defaults(handler=_pipe_flow)

    water = tools.add_parser("water", help="liquid water properties at 1 atm")
    water.add_argument("--temperature-c", type=float, required=True,
                       help="temperature [degC], 1 to 99")
    water.set_defaults(handler=_water)
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
