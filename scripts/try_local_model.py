# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""try_local_model.py - ask a local Ollama model engineering questions through fpc-mcp.

The MCP server's tool descriptions and instructions are written *for a model*,
and the only way to know whether they work is to watch a real one use them.
This script plays the part of an AI chat app (LM Studio, Open WebUI, ...):

    1. start the MCP server in-process and read its tool list,
    2. hand those tools to a model running in Ollama,
    3. loop: whenever the model asks for a tool, run it through MCP and send
       back the result, until the model writes a final answer,
    4. check the answer against the number fpc itself computes.

Usage (Ollama must be running; ``ollama pull qwen3:14b`` first)::

    uv run --extra mcp scripts/try_local_model.py --model qwen3:14b
    uv run --extra mcp scripts/try_local_model.py --model qwen2.5:7b --domains fluids,thermo
    uv run --extra mcp scripts/try_local_model.py --model qwen3:14b --only reynolds -v

It prints one line per question (PASS/FAIL, tool calls made, seconds) and,
with ``-v``, the whole conversation. A FAIL is a lead, not a verdict: read the
transcript to see whether the model picked the wrong tool, converted a unit
wrongly, or never called a tool at all, then improve the tool descriptions or
``INSTRUCTIONS`` in ``fpc/mcp_server.py``. Findings so far are in docs/ai.md.

Techniques shown: ``asyncio`` (the MCP client is async), ``urllib`` for a JSON
HTTP API with no extra dependency, and a tool-calling loop, the core of every
"AI agent".
"""

import argparse
import asyncio
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from mcp import Client

from fpc import registry
from fpc.mcp_server import INSTRUCTIONS, build_server

OLLAMA = "http://localhost:11434/api/chat"
MAX_TURNS = 10  # tool calls before we give up on a question


@dataclass(frozen=True)
class Question:
    """One test question and how to get its true answer from fpc.

    :param name: short id for ``--only``
    :param text: what the user asks; units deliberately mixed (mm, kN, L/s,
        mPa*s) because converting them is where models slip
    :param key: the calculation that answers it
    :param arguments: that calculation's inputs in SI
    :param pick: turns the calculation's result into the expected number
    :param scale: multiplies the expected number into the unit the question asks for
    """

    name: str
    text: str
    key: str
    arguments: dict[str, Any]
    pick: str = ""  # dict key or tuple index ("1") into the result, if any
    scale: float = 1.0

    def expected(self) -> float:
        result = registry.calculate(self.key, self.arguments)
        if self.pick:
            result = result[int(self.pick)] if isinstance(result, list) else result[self.pick]
        return float(result) * self.scale


QUESTIONS = [
    Question(
        "reynolds",
        "Water (density 998 kg/m3, dynamic viscosity 1.0 mPa*s) flows at 2 m/s "
        "in a pipe with a 50 mm inside diameter. What is the Reynolds number?",
        "Fluids.reynolds_number",
        {"density": 998, "velocity": 2, "length": 0.05, "viscosity": 1e-3},
    ),
    Question(
        "frequency",
        "A 2.5 kg mass sits on a spring with a stiffness of 4 kN/m. "
        "What is the undamped natural frequency in Hz?",
        "Modal.natural_frequency",
        {"stiffness": 4000, "mass": 2.5},
        pick="1",
    ),
    Question(
        "wall",
        "A brick wall is 200 mm thick and 12 m2 in area, with thermal "
        "conductivity 0.72 W/(m K). It is 20 C inside and -5 C outside. "
        "How many watts of heat flow through it?",
        "Thermo.conduction_heat_rate",
        {"conductivity": 0.72, "area": 12, "delta_temperature": 25, "thickness": 0.2},
    ),
    Question(
        "rc",
        "What is the time constant, in seconds, of a 47 kilohm resistor "
        "in series with a 10 uF capacitor?",
        "Electrical.rc_time_constant",
        {"resistance": 47e3, "capacitance": 10e-6},
    ),
    Question(
        "hvl",
        "A material has a linear attenuation coefficient of 0.5 per cm. "
        "What is its half-value layer in millimetres?",
        "Radiation.half_value_layer",
        {"attenuation_coefficient": 0.5},
        scale=10,  # cm -> mm
    ),
    Question(
        "pipe",
        "12 L/s of water (density 998 kg/m3, viscosity 1.0 mPa*s) flows through "
        "120 m of commercial steel pipe with a 100 mm inside diameter "
        "(roughness 0.045 mm). What is the pressure drop in kPa?",
        "Fluids.pipe_flow",
        {
            "flow": 0.012,
            "diameter": 0.1,
            "length": 120,
            "roughness": 0.045e-3,
            "density": 998,
            "viscosity": 1e-3,
        },
        pick="pressure_drop",
        scale=1e-3,  # Pa -> kPa
    ),
]


def ollama_chat(
    model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> dict[str, Any]:
    """One request to Ollama's chat API; returns the assistant message."""
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0},  # repeatable runs
        }
    ).encode()
    request = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)["message"]


def numbers_in(text: str) -> list[float]:
    """Every number in a piece of text; "99,800" and "9.98e4" both count."""
    found = re.findall(r"-?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?", text)
    return [float(n.replace(",", "")) for n in found if n.replace(",", "").strip("-.")]


async def ask(
    client: Client, model: str, tools: list[dict[str, Any]], question: Question, verbose: bool
) -> tuple[bool, list[str], str]:
    """Run the tool-calling loop for one question.

    :returns: (passed, tool calls made, final answer text)
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": question.text},
    ]
    calls: list[str] = []
    answer = ""
    for _ in range(MAX_TURNS):
        message = await asyncio.to_thread(ollama_chat, model, messages, tools)
        messages.append(message)
        if not message.get("tool_calls"):
            answer = message.get("content", "")
            break
        for call in message["tool_calls"]:
            name, arguments = call["function"]["name"], call["function"]["arguments"]
            calls.append(name)
            result = await client.call_tool(name, arguments)
            text = result.content[0].text if result.content else ""
            if verbose:
                print(f"    -> {name}({json.dumps(arguments)})\n       <- {text[:300]}")
            messages.append({"role": "tool", "tool_name": name, "content": text})
    expected = question.expected()
    passed = any(abs(n - expected) <= 0.02 * abs(expected) for n in numbers_in(answer))
    if verbose:
        print(f"    answer: {answer.strip()[:600]}\n    expected ~{expected:.4g}")
    return passed, calls, answer


async def main_async(args: argparse.Namespace) -> int:
    domains = [d for d in args.domains.split(",") if d]
    questions = [q for q in QUESTIONS if not args.only or q.name in args.only.split(",")]
    async with Client(build_server(domains)) as client:
        # Translate MCP tool definitions into the "function" format Ollama expects.
        tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in (await client.list_tools()).tools
        ]
        print(f"{args.model}: {len(tools)} tools, {len(questions)} questions")
        passed = 0
        for question in questions:
            start = time.perf_counter()
            if args.verbose:
                print(f"\n[{question.name}] {question.text}")
            ok, calls, _ = await ask(client, args.model, tools, question, args.verbose)
            passed += ok
            seconds = time.perf_counter() - start
            verdict = "PASS" if ok else "FAIL"
            trail = " > ".join(calls) or "(no tools)"
            print(f"  {verdict}  {question.name:<10} {seconds:5.0f}s  {trail}")
        print(f"{passed}/{len(questions)} passed")
    return 0 if passed == len(questions) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", default="qwen3:14b", help="an Ollama model with tool calling")
    parser.add_argument("--domains", default="", help="passed to the server, e.g. fluids,thermo")
    parser.add_argument("--only", default="", help="comma-separated question names")
    parser.add_argument("-v", "--verbose", action="store_true", help="print each conversation")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(main_async(args))
    except OSError as error:  # urllib's URLError is an OSError
        sys.exit(f"Could not reach Ollama at {OLLAMA} ({error}). Is `ollama serve` running?")


if __name__ == "__main__":
    sys.exit(main())
