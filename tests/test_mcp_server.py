# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the MCP server (fpc.mcp_server).

``mcp.Client(server)`` connects to the server *in-process*, speaking the real
MCP protocol without starting a subprocess, so these tests check exactly what
an AI app would see. The server is an optional extra, so skip if not installed.
"""

import asyncio

import pytest

pytest.importorskip("mcp")

from mcp import Client  # noqa: E402  (import after the skip check on purpose)

from fpc.mcp_server import build_server  # noqa: E402


def call(tool, arguments=None):
    """Connect, call one tool, and return the CallToolResult."""

    async def go():
        async with Client(build_server()) as client:
            return await client.call_tool(tool, arguments or {})

    return asyncio.run(go())


def test_tool_list_is_small_and_stable():
    async def go():
        async with Client(build_server()) as client:
            return [tool.name for tool in (await client.list_tools()).tools]

    assert sorted(asyncio.run(go())) == [
        "calculate",
        "describe_calculation",
        "list_domains",
        "list_reference_tables",
        "search_calculations",
    ]


def test_search_returns_keys_with_units():
    result = call("search_calculations", {"query": "reynolds"})
    first = result.structured_content["result"][0]
    assert first["key"] == "Fluids.reynolds_number"
    assert "density [kg/m^3]" in first["inputs"]


def test_calculate_returns_value_and_echoes_units():
    args = {"density": 998, "velocity": 2, "length": 0.05, "viscosity": 0.001}
    result = call("calculate", {"key": "Fluids.reynolds_number", "arguments": args})
    assert not result.is_error
    data = result.structured_content
    assert data["result"] == pytest.approx(99800)
    assert data["inputs"]["density"] == {"value": 998, "unit": "kg/m^3"}


def test_bad_input_comes_back_as_a_readable_error():
    result = call("calculate", {"key": "Fluids.reynolds_number", "arguments": {"density": 998}})
    assert result.is_error
    assert "missing required argument" in result.content[0].text


def test_reference_tables_list_columns():
    tables = call("list_reference_tables").structured_content
    assert "density_kg_m3" in tables["water_liquid_1atm"]


# --- --domains: one tool per calculation -------------------------------------


def list_tools(server):
    async def go():
        async with Client(server) as client:
            return {tool.name: tool for tool in (await client.list_tools()).tools}

    return asyncio.run(go())


def test_domains_flag_adds_one_tool_per_calculation_with_the_registry_schema():
    from fpc import registry

    tools = list_tools(build_server(["Fluids"]))
    fluids = [c for c in registry.calculations() if c.domain == "Fluids" and c.json_callable]
    assert len(tools) == 5 + len(fluids)

    tool = tools["fluids_reynolds_number"]
    schema = tool.input_schema
    assert sorted(schema["required"]) == ["density", "length", "velocity", "viscosity"]
    assert schema["properties"]["density"]["type"] == "number"
    assert "kg/m^3" in schema["properties"]["density"]["description"]
    assert "Reynolds" in tool.description


def test_direct_tool_calculates_and_explains_bad_input():
    server = build_server(["fluids"])  # any case

    async def go(arguments):
        async with Client(server) as client:
            return await client.call_tool("fluids_reynolds_number", arguments)

    args = {"density": 998, "velocity": 2, "length": 0.05, "viscosity": 0.001}
    result = asyncio.run(go(args))
    assert not result.is_error
    assert result.structured_content["result"] == pytest.approx(99800)

    bad = asyncio.run(go({**args, "viscosity": 0}))
    assert bad.is_error
    assert "ZeroDivisionError" in bad.content[0].text or "ValueError" in bad.content[0].text


def test_unknown_domain_is_rejected_with_choices():
    with pytest.raises(ValueError, match="Fluids"):
        build_server(["plumbing"])
