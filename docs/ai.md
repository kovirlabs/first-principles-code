<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Using fpc with AI assistants

There are two ways an AI model can use this library, and they suit different
models:

| You are using... | Best approach | Why |
|---|---|---|
| A **local model** in a chat app (LM Studio, Ollama + Open WebUI, ...) | The **MCP server** (`fpc-mcp`) | Small models are unreliable at arithmetic and at writing numerical code. With MCP the model picks the formula; tested Python does the maths. |
| A **coding agent** (Claude Code, Cursor, Aider, Continue, ...) | Let it **read and write code** with `fpc` directly. Point it at [`AGENTS.md`](https://github.com/kovirlabs/first-principles-code/blob/main/AGENTS.md) and [`llms.txt`](https://github.com/kovirlabs/first-principles-code/blob/main/llms.txt). | It can chain calculations, sweep parameters and plot, which tool calls alone cannot. |

You can use both: a coding agent that also has the MCP server will use it for
quick one-off numbers.

## What the MCP server offers

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) is a
standard way for AI apps to call tools on your computer. `fpc-mcp` exposes
five tools, deliberately few so that small models choose well:

| Tool | What it does |
|---|---|
| `list_domains` | The engineering areas covered (Fluids, Thermo, CT, ...) |
| `search_calculations` | Keyword search, e.g. `"pipe pressure drop"` → `Fluids.pipe_flow` |
| `describe_calculation` | Formula, assumptions, every input with its **unit** |
| `calculate` | Runs it and returns the exact result, echoing inputs with units |
| `list_reference_tables` | The cited water / material / steel-section tables and their columns |

It **cannot** run arbitrary code or read and write files: only the
calculations catalogued by `fpc.registry` are callable.

## Install

The server needs the optional `mcp` extra.

=== "From PyPI (once released)"

    Nothing to install up front. `uvx` downloads and runs it on demand:

    ```bash
    uvx --from "first-principles-code[mcp]" fpc-mcp --help
    ```

=== "From a clone of this repo"

    ```bash
    uv sync --extra mcp
    uv run fpc-mcp --help
    ```

In the configs below, the *command* is either `uvx` with
`["--from", "first-principles-code[mcp]", "fpc-mcp"]`, or, for a local clone,
`uv` with `["run", "--directory", "/absolute/path/to/first-principles-code",
"--extra", "mcp", "fpc-mcp"]`. Use the absolute path; AI apps do not start in
your project folder.

## LM Studio

LM Studio is an MCP client itself. In the **Program** tab choose
**Install → Edit mcp.json** and add:

```json
{
  "mcpServers": {
    "fpc": {
      "command": "uvx",
      "args": ["--from", "first-principles-code[mcp]", "fpc-mcp"]
    }
  }
}
```

Load a model that supports **tool use** (LM Studio marks these with a
hammer icon; recent Qwen, Llama, Mistral and gpt-oss models work), enable the
`fpc` integration in the chat, and ask e.g. *"What is the pressure drop for
12 L/s of 20 °C water through 120 m of 4-inch steel pipe?"*

## Ollama

Ollama runs models but is not an MCP client itself, so pair it with a front
end that is:

- **Open WebUI**: under **Settings → External Tools / MCP** add a
  *Streamable HTTP* server. Start ours in HTTP mode:

    ```bash
    uvx --from "first-principles-code[mcp]" fpc-mcp --transport streamable-http --port 8765
    ```

    and use the URL `http://127.0.0.1:8765/mcp`. Older Open WebUI versions
    need the [`mcpo`](https://github.com/open-webui/mcpo) proxy instead:
    `uvx mcpo --port 8000 -- uvx --from "first-principles-code[mcp]" fpc-mcp`.
- **[ollmcp](https://github.com/jonigl/mcp-client-for-ollama)**, a
  terminal chat client: `uvx ollmcp --mcp-server-url http://127.0.0.1:8765/mcp`
  (with the HTTP server above running), or point it at a JSON config like
  the LM Studio one.
- **Continue** or **Cline** in VS Code: both accept the same
  `command` / `args` server definition as above and can use Ollama models.

Pick a model trained for tool calling (`ollama pull qwen3`, `llama3.1`,
`mistral-small`, ...). Very small models (under ~7B parameters) often call
tools poorly; that is a model limit, not a server one.

## Claude Desktop and Claude Code

Claude Desktop: add the same `"fpc"` block to
`claude_desktop_config.json` (**Settings → Developer → Edit Config**).

Claude Code:

```bash
claude mcp add fpc -- uvx --from "first-principles-code[mcp]" fpc-mcp
```

## Testing the server yourself

The MCP Inspector is a web page for poking at a server by hand:

```bash
npx @modelcontextprotocol/inspector uv run --extra mcp fpc-mcp
```

The same catalogue is available without any AI from the terminal:

```bash
fpc search "half value layer"
fpc describe Radiation.half_value_layer
fpc run Radiation.half_value_layer attenuation_coefficient=0.2
```

## How it works

`fpc/registry.py` walks every domain class with Python's `inspect` module,
reads each method's type hints and its docstring's `:param name: text [unit]`
lines, and builds a JSON Schema per calculation. The MCP server, the
`fpc search/describe/run` commands and `llms.txt` are all thin layers on that
one catalogue, so a newly written method appears in all of them
automatically, as long as its docstring tags every number with a unit (a
test enforces this).
