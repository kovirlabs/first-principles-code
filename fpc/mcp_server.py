# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""mcp_server.py - let an AI model use ``fpc`` as its engineering calculator.

The **Model Context Protocol (MCP)** is a standard way for an AI application
(LM Studio, an Ollama front end, Claude Desktop, an IDE assistant, ...) to call
tools that run on your own computer. This module is an MCP server: a small
program the AI app starts in the background and talks to over stdin/stdout.

Why bother? Language models, and especially the small ones you can run
locally, are unreliable at arithmetic and at writing numerical code. They
are good at reading a question and picking the right formula. So we let the
model do the picking and let tested Python do the maths.

Design choices:

    * **Few tools, not 120.** Small models choose badly from a long tool list,
      so the server offers five general tools: browse domains, search,
      describe, calculate, and list reference tables. The model searches the
      catalogue built by :mod:`fpc.registry` instead of reading every schema.
    * **No code execution, no file access.** Only the registry's calculations
      can run (file and DICOM helpers are excluded there), so a confused or
      manipulated model cannot touch your disk.
    * **Errors are explanations.** A bad argument comes back as a readable
      message (missing ``viscosity``, unknown table, ...) the model can act on.

Run it::

    fpc-mcp                       # stdio, what desktop AI apps expect
    fpc-mcp --transport streamable-http --port 8765   # HTTP, for web front ends

Setup for LM Studio, Ollama front ends, and Claude is in ``docs/ai.md``.
Requires the optional ``mcp`` extra: ``pip install "first-principles-code[mcp]"``.
"""

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError as error:  # give a fix, not just a traceback
    raise SystemExit(
        "The MCP server needs the optional 'mcp' package. Install it with:\n"
        '    pip install "first-principles-code[mcp]"\n'
        "or, inside this repository:  uv sync --extra mcp"
    ) from error

from fpc import registry
from fpc.properties import Properties

# Sent to the AI app when it connects; most apps add it to the model's system
# prompt. It teaches the model the workflow in a few lines.
INSTRUCTIONS = """\
First Principles Code: tested engineering calculations (fluids, thermo,
statics, dynamics, vibration, controls, gears, electrical, materials,
radiology, ...). Use these tools instead of doing arithmetic yourself.

Workflow:
1. search_calculations("pipe pressure drop") to find candidates.
2. describe_calculation("Fluids.pipe_flow") to see inputs and their units.
3. calculate("Fluids.pipe_flow", {...}) with every value in the unit shown in
   square brackets (SI unless stated, e.g. metres not millimetres).
4. Report the result with its unit and state the inputs you assumed.
For fluid or material properties, use the Properties calculations; call
list_reference_tables to see the available tables and column names.
"""


def _label(param: registry.Parameter) -> str:
    """``"density [kg/m^3]"``, plus ``" (optional)"`` when it has a default."""
    unit = f" [{param.unit}]" if param.unit else ""
    return param.name + unit + ("" if param.required else " (optional)")


@contextmanager
def _explain_errors() -> Iterator[None]:
    """Pass input mistakes back to the model as readable tool errors.

    The MCP library treats any ordinary exception as a crash and hides its
    message from the model ("Error executing tool"). A ``ToolError`` is shown
    in full, so the model can read "missing argument viscosity" and retry.
    Only the error *types* that mean "bad input" are converted; a genuine bug
    still surfaces as a crash in the server log.
    """
    try:
        yield
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as error:
        message = error.args[0] if isinstance(error, KeyError) and error.args else error
        raise ToolError(f"{type(error).__name__}: {message}") from error


def build_server() -> MCPServer:
    """Create the MCP server and register its tools.

    Kept separate from :func:`main` so tests can connect to the server
    in-process (``mcp.Client(build_server())``) without starting a subprocess.

    :returns: a configured ``MCPServer``
    """
    server = MCPServer("first-principles-code", instructions=INSTRUCTIONS)

    # Each decorated function becomes one tool. The MCP library reads the type
    # hints and docstring to build the tool's JSON Schema and description, so
    # the docstrings below are written *for the model*.

    @server.tool()
    def list_domains() -> dict[str, str]:
        """List the engineering domains (classes) and what each covers."""
        return registry.domains()

    @server.tool()
    def search_calculations(
        query: str, domain: str | None = None, limit: int = 8
    ) -> list[dict[str, Any]]:
        """Find calculations by keywords, e.g. "reynolds", "beam deflection", "half-value layer".

        Returns each match's key (pass it to describe_calculation or calculate),
        a one-line summary, and its inputs as "name [unit]".
        """
        return [
            {
                "key": calc.key,
                "summary": calc.summary,
                "inputs": [
                    p.name
                    + (f" [{p.unit}]" if p.unit else "")
                    + ("" if p.required else " (optional)")
                    for p in calc.parameters
                ],
            }
            for calc in registry.search(query, limit=limit, domain=domain)
        ]

    @server.tool()
    def describe_calculation(key: str) -> dict[str, Any]:
        """Full description of one calculation: the formula and assumptions,
        every input with its unit and default, what it returns, and its JSON Schema.

        key: "Domain.method", e.g. "Fluids.reynolds_number".
        """
        with _explain_errors():
            return registry.get(key).to_dict()

    @server.tool()
    def calculate(key: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run a calculation and return its exact result.

        key: "Domain.method", e.g. "Fluids.reynolds_number".
        arguments: keyword arguments, each in the unit given by
        describe_calculation, e.g. {"density": 998, "velocity": 2,
        "length": 0.05, "viscosity": 0.001}.
        """
        with _explain_errors():
            calc = registry.get(key)
            result = registry.calculate(key, arguments)
        units = {p.name: p.unit for p in calc.parameters}
        return {
            "key": key,
            # Echo the inputs with units so the model (and the person reading
            # its answer) can check what was actually computed.
            "inputs": {
                name: {"value": value, "unit": units.get(name)} for name, value in arguments.items()
            },
            "result": result,
            "returns": calc.returns,
        }

    @server.tool()
    def list_reference_tables() -> dict[str, list[str]]:
        """List the cited reference tables (water, materials, steel W-shapes) and
        their column names; column names include units, e.g. "density_kg_m3".
        Use them with Properties calculations such as Properties.water_liquid."""
        props = Properties()
        return {name: list(props.load_table(name=name).columns) for name in props.list_tables()}

    return server


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``fpc-mcp`` command.

    :param argv: command-line arguments (defaults to the real command line)
    """
    parser = argparse.ArgumentParser(
        prog="fpc-mcp", description="Serve fpc calculations to AI apps over MCP."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio (default) for desktop apps; streamable-http for web front ends",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    args = parser.parse_args(argv)

    server = build_server()
    if args.transport == "stdio":
        server.run("stdio")
    else:
        # Bound to localhost by default: this server is meant for your machine.
        server.run("streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
