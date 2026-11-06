# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Rung 2: a command-line tool. Inputs come from arguments, not code edits.

argparse (standard library) turns flags into Python values, checks their
types, and writes the --help text for you. Now anyone can run new cases, and
you can call it from batch files or other programs.

Run it:
    uv run examples/tools/step2_cli.py --help
    uv run examples/tools/step2_cli.py --flow-l-s 12 --diameter-mm 102.3 --length-m 120
"""

import argparse

from fpc import Fluids, Properties


def build_parser():
    """Describe the inputs: name, type, default, and help text for each."""
    parser = argparse.ArgumentParser(
        description="Pressure drop of water flowing through a straight pipe.",
    )
    # Units go in the flag names, so nobody has to guess.
    parser.add_argument("--flow-l-s", type=float, required=True, help="flow rate [L/s]")
    parser.add_argument("--diameter-mm", type=float, required=True, help="inner diameter [mm]")
    parser.add_argument("--length-m", type=float, required=True, help="pipe length [m]")
    parser.add_argument("--roughness-mm", type=float, default=0.045,
                        help="absolute roughness [mm] (default: commercial steel 0.045)")
    parser.add_argument("--temperature-c", type=float, default=20.0,
                        help="water temperature [degC] (default: 20)")
    return parser


def main(argv=None):
    """Parse arguments, convert to SI, calculate, print.

    ``argv=None`` means "use the real command line"; tests can pass a list.
    """
    args = build_parser().parse_args(argv)
    props = Properties()
    result = Fluids().pipe_flow(
        flow=args.flow_l_s / 1000,
        diameter=args.diameter_mm / 1000,
        length=args.length_m,
        roughness=args.roughness_mm / 1000,
        density=props.water_liquid(temperature_c=args.temperature_c,
                                   property="density_kg_m3"),
        viscosity=props.water_liquid(temperature_c=args.temperature_c,
                                     property="dynamic_viscosity_pa_s"),
    )
    print(f"velocity        {result['velocity']:.3f} m/s")
    print(f"Reynolds        {result['reynolds']:.0f}")
    print(f"friction factor {result['friction_factor']:.4f}")
    print(f"head loss       {result['head_loss']:.3f} m")
    print(f"pressure drop   {result['pressure_drop'] / 1000:.2f} kPa")


if __name__ == "__main__":
    main()
