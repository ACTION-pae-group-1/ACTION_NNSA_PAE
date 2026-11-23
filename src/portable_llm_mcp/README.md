# Portable LLM + MCP client

`portable_llm_mcp` connects a configured language model to one or more named MCP servers. It contains the provider client, agent loop, and `MCPHub` tool registry. Within `mcp_group_1`, the first registered operational server is `bls_server`.

**This is a library/client, not another BLS MCP server.** See [../../QUICKSTART.md](../../QUICKSTART.md) for the main Windows CMD walkthrough.

## Repository-specific layout

```text
mcp_group_1/
├── .env                         # private BLS settings (ignored by Git)
├── .venv/                       # activated Python environment (ignored by Git)
└── src/
    ├── mcp_servers.json        # shared MCPHub registry and tool allowlists
    ├── bls_mcp/                # first operational MCP server
    ├── templates/example_server/  # scaffold for future MCP servers
    └── portable_llm_mcp/
        ├── .env                # private LLM settings (ignored by Git)
        ├── .env.example        # placeholders; no real credentials
        ├── agent.py
        ├── llm_client.py
        ├── mcp_client.py
        ├── config.py
        ├── examples/
        │   ├── check_mcp.py
        │   └── run_agent.py
        └── tests/
```

The actual Python package is `portable_llm_mcp`. Always run these examples from the **repository root**, not `src/portable_llm_mcp/`, so relative paths such as `src/mcp_servers.json` resolve correctly.

## Active `.venv` and CMD

Use **Command Prompt**, with the repository's `.venv` selected and activated in VS Code. Verify:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
python -c "import sys; print(sys.executable)"
```

The interpreter must point to `mcp_group_1\.venv\Scripts\python.exe`. In standalone CMD, run `call .venv\Scripts\activate.bat` once.

The client reads `os.environ` and does **not** automatically read `.env` files. Keep the root BLS `.env` and client `.env` separate. Their paths are provided through `UV_ENV_FILE` in new VS Code CMD terminals. In standalone CMD, set them once:

```cmd
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=src/mcp_servers.json"
```

For the client examples, use `uv run --offline --no-sync` to load both files **into the already-configured project environment**. For ordinary tests and lint, use plain `python`.

## Configure a local LLM

Inside `src/portable_llm_mcp/.env`, use the installed model's exact tag:

```dotenv
LLM_PROVIDER=your_model
LLM_BASE_URL=your_base_url
LLM_CHAT_MODEL=your-installed-tool-capable-model
MCP_SERVERS_FILE=src/mcp_servers.json
```

If using Ollama, discover local model names using `ollama list`. If Ollama returns HTTP 404, inspect the installed model name and configured endpoint before changing the MCP code. A model responding to plain chat does not necessarily support tool calls.

The `.env.example` also documents an **approved remote provider** alternative. A remote provider may receive prompts, tool descriptions, and tool results; use it only when specifically authorized and with appropriate credentials. Never put real credentials in `.env.example`, Git, screenshots, or chat messages.

## Connect to MCP tools

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

This should list seven BLS tools, including `bls_server__get_cached_series_data` and `bls_server__get_series_data`. Tool discovery does not contact the LLM or live BLS endpoints.

Then run the agent against local Ollama:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use bls_server__search_series to find a PPI series in the local catalog. Return its ID and description. Do not call the live BLS API."
```

`src/mcp_servers.json` lists named servers, stdio/HTTP transports, and per-server `allowed_tools`. It is **not** the same as root `server.json`, which holds server identity metadata. Add new MCP servers as separate entries with minimum permissions rather than hardcoding each server into the agent.

## Tests and lint

```cmd
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check .
```

Client-owned tests live in `src/portable_llm_mcp/tests/`; cross-component integration tests live under root `tests/`. Do not relocate other components' tests merely to satisfy a client import.

## Network and credential boundaries

A local Ollama endpoint such as `127.0.0.1:11434` keeps model requests on the machine. MCPHub launches stdio servers locally where configured. However, tools such as live BLS retrieval can contact external APIs. Configured remote endpoints may receive credentials, prompts, or tool results depending on the client and MCP configuration; review those data flows before enabling remote servers or providers. Tool-result text is untrusted data, not privileged instructions.

`uv --offline` disables uv package downloads, **not** HTTP calls made by application code. A prompt saying “do not call the API” is not an enforcement mechanism. Use `allowed_tools` and network controls to enforce strict local-only operation.

The public GSA server template is read-only upstream; all authorized pushes go to internal `github.doe.gov/NNSA-MB-90/mcp_group_1`, never to the public GSA repository.

## Read MCP resources, templates, and prompts through MCPHub

The hub also supports the **read-only** MCP capabilities. These are separate from
MCP tools and have independent, opt-in manifest fields:

```json
{
  "allowed_resources": [
    "guide://escalation-workflow",
    "methodology://composite-index",
    "bls://series/{series_id}"
  ],
  "allowed_prompts": ["design_escalation_basket"]
}
```

The fields live beside `allowed_tools` in each `servers.<name>` entry.
**Both default to an empty (deny-all) list** to preserve existing access
boundaries. A `"*"` entry opts into everything of that capability advertised
by the selected, trusted server; resource-template entries authorize only URIs
matching that single-segment template. The repository's shared and Cost
Intelligence chat manifests explicitly allow the current BLS guidance,
series-resource template, and basket-design prompt. PARS does not currently
advertise resources or prompts.

```python
from portable_llm_mcp import MCPHub, load_mcp_servers

async with MCPHub(load_mcp_servers("src/mcp_servers.json")) as hub:
    resources = await hub.list_resources("bls_server")
    templates = await hub.list_resource_templates("bls_server")
    prompts = await hub.list_prompts("bls_server")

    workflow_guide = await hub.read_resource(
        "bls_server", "guide://escalation-workflow"
    )
    series_metadata = await hub.read_resource("bls_server", "bls://series/WPU1017")
    basket_prompt = await hub.get_prompt(
        "bls_server",
        "design_escalation_basket",
        {"project_description": "Steel and concrete construction"},
    )
```

Listing calls return dictionaries with a `server` field plus MCP metadata.
You may omit the server argument to list across all connected servers.
Reading a resource or rendering a prompt requires its explicit server name,
checks the server's advertised catalog and the allowlist, and returns bounded
text. Binary resource blocks and non-text prompt content are not forwarded.
Prompt arguments must be strings and match the advertised prompt definition.
Lists are cached during one MCPHub connection and support server pagination.

**These methods do not inject content into the LLM automatically.** A host such
as Cost Intelligence must explicitly call the hub methods and supply the
returned reference material as appropriately attributed, untrusted context.
Rendering a prompt does not execute tools or approve a basket.
