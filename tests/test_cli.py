# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the ``fpc`` command line (fpc.cli) and the argparse tool example.

``main(argv=[...])`` runs the CLI in-process; ``capsys`` captures what it
prints so we can check the output text.
"""

import importlib.util
from pathlib import Path

import pytest

from fpc import cli


def test_pipe_flow_command(capsys):
    cli.main(["pipe-flow", "--flow-l-s", "12", "--diameter-mm", "102.3", "--length-m", "120"])
    output = capsys.readouterr().out
    assert "pressure drop" in output
    assert "kPa" in output


def test_water_command(capsys):
    cli.main(["water", "--temperature-c", "20"])
    assert "998.21" in capsys.readouterr().out


def test_missing_subcommand_exits():
    # argparse reports usage errors by raising SystemExit (exit code 2).
    with pytest.raises(SystemExit):
        cli.main([])


def test_step2_cli_example(capsys):
    """The rung-2 example lives outside the package, so load it by path."""
    path = Path(__file__).resolve().parent.parent / "examples" / "tools" / "step2_cli.py"
    spec = importlib.util.spec_from_file_location("step2_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(["--flow-l-s", "12", "--diameter-mm", "102.3", "--length-m", "120"])
    assert "Reynolds" in capsys.readouterr().out
