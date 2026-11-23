> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Apps

> Give your tools interactive UIs rendered directly in the conversation.

New in version `3.0.0`

A FastMCP app is a tool that returns an interactive UI instead of text. When the host calls it, the user sees a chart, a table, a form, or a whole dashboard rendered right inside the conversation, with working sort, search, tooltips, and state.

**Prefab showcase demo**

The dashboard above is a [Prefab](https://prefab.prefect.io) showcase — a taste of what you can deliver from a FastMCP tool. Every card, chart, slider, dialog, and carousel is a Python component. Build a composition like this, add `@mcp.tool(app=True)`, and the host renders it inside the conversation.

Under the hood, FastMCP builds on the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) and uses Prefab to describe UIs in Python.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install "fastmcp[apps]"
```

> [!TIP]
>
> [Prefab](https://prefab.prefect.io) is under active development with frequent breaking changes. FastMCP sets a minimum `prefab-ui` version but does not pin an upper bound — **pin `prefab-ui` to a specific version in your own dependencies** before deploying.

## Pick your path

Four patterns cover almost everything you'd want to build. Most apps start with Interactive Tools; you only reach for the others when you've hit a specific limit.

### [Interactive Tools](https://gofastmcp.com/apps/prefab.md) — start here

Add `app=True` to a tool and return a Prefab component. Charts, tables, dashboards, and client-side interactivity (toggles, tabs, filtering) all work without any server round-trips.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@mcp.tool(app=True)
def team_directory() -> DataTable:
    return DataTable(columns=[...], rows=employees, search=True)
```

### [FastMCPApp](https://gofastmcp.com/apps/fastmcp-app.md) — when the UI calls back to the server

Forms that save data, buttons that trigger backend work, search that hits a database. `FastMCPApp` manages the wiring between UI actions and backend tools, with stable tool identifiers that survive server composition.

### [Generative UI](https://gofastmcp.com/apps/generative.md) — when the LLM writes the UI

Register one provider and the model can write Prefab code tailored to the current data and request. The user watches the UI build up as the model generates it.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
mcp.add_provider(GenerativeUI())
```

### [Custom HTML](https://gofastmcp.com/apps/low-level.md) — when you need full control

Write your own HTML, CSS, and JavaScript. Use a specific framework, drop in a map or 3D viewer, embed video. You're talking to the MCP Apps protocol directly.

## What's next

* **[Quickstart](https://gofastmcp.com/apps/quickstart.md)** — build a working app in a minute
* **[Examples](https://gofastmcp.com/apps/examples.md)** — complete working servers you can run today
* **[Providers](https://gofastmcp.com/apps/providers/approval.md)** — ready-made capabilities (approvals, choice pickers, file upload, forms) you add with one line
* **[Development](https://gofastmcp.com/apps/development.md)** — preview app tools locally with `fastmcp dev apps`


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.