> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Installation

> Install FastMCP and verify your setup

## Install FastMCP

We recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) to install and manage FastMCP.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
uv add fastmcp
```

Or with pip:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install fastmcp
```

### Optional Dependencies

FastMCP provides optional extras for specific features. For example, to install the background tasks extra:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install "fastmcp[tasks]"
```

See [Background Tasks](https://gofastmcp.com/docs/servers/tasks.md) for details on the task system.

### Verify Installation

To verify that FastMCP is installed correctly, you can run the following command:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp version
```

You should see output like the following:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
$ fastmcp version

FastMCP version:                           4.0.0
MCP version:                                2.0.0
Python version:                            3.12.2
Platform:            macOS-15.3.1-arm64-arm-64bit
FastMCP root path:            ~/Developer/fastmcp
```

### Dependency Licensing

> [!NOTE]
>
> FastMCP depends on Cyclopts for its CLI. Older Cyclopts installs pull in docutils through rich-rst 1.x, and docutils has licensing that can trigger compliance reviews. rich-rst 2 no longer depends on docutils, and a fresh install resolves to rich-rst 2. If a scan flags docutils in an existing environment, upgrade both packages:
>
> ```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
> pip install -U cyclopts rich-rst
> ```
>
> See [this issue](https://github.com/BrianPugh/cyclopts/issues/672) for background.

## Upgrading

### From FastMCP 3.0

Most FastMCP 3 servers run on 4 without changes. See [Upgrading from FastMCP 3](https://gofastmcp.com/docs/getting-started/upgrading/from-fastmcp-3.md) for the breaks that do exist, and [What's New](https://gofastmcp.com/docs/getting-started/whats-new.md) for what the new version adds.

### From FastMCP 2.0

See the [Upgrade Guide](https://gofastmcp.com/docs/getting-started/upgrading/from-fastmcp-2.md) for a complete list of breaking changes and migration steps.

### From the MCP SDK

Which guide you want depends on which `mcp` version you're on and which of its two server APIs you used.

#### From the high-level server

If you're using FastMCP 1.0 via SDK v1 (meaning you import FastMCP as `from mcp.server.fastmcp import FastMCP`), upgrading is straightforward — for most servers it's a single import change. See [Upgrading from MCP SDK v1](https://gofastmcp.com/docs/getting-started/upgrading/from-mcp-sdk-v1.md), which also explains why that route is usually easier than moving to MCP SDK v2.

If you already moved to SDK v2 and write against `MCPServer`, see [Upgrading from MCP SDK v2](https://gofastmcp.com/docs/getting-started/upgrading/from-mcp-sdk-v2.md) — that migration is mostly renaming.

#### From the low-level server

If you built your server directly on the `mcp` package's `Server` class, the guide you want depends on how its handlers are registered. Decorators like `@server.list_tools()` mean SDK v1 — see [Upgrading from the Low-Level SDK v1](https://gofastmcp.com/docs/getting-started/upgrading/from-low-level-sdk-v1.md). Handlers passed to the constructor as `on_list_tools=` mean SDK v2 — see [Upgrading from the Low-Level SDK v2](https://gofastmcp.com/docs/getting-started/upgrading/from-low-level-sdk-v2.md).

## Troubleshooting

### `import fastmcp` fails after a pip upgrade

This affects one specific case: upgrading to FastMCP 3.3 or later from FastMCP 3.2 or earlier with `pip`. Fresh installs and `uv` upgrades are unaffected, so you can skip this unless you did exactly that.

If `import fastmcp` raises `ModuleNotFoundError`, or `from fastmcp import FastMCP` raises `ImportError`, immediately after the upgrade, your install is in a half-removed state. Reinstall in a single step:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install --force-reinstall fastmcp
```

If that doesn't resolve it, remove both distributions and reinstall from a clean state:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip uninstall -y fastmcp fastmcp-slim
pip install fastmcp
```

FastMCP 3.3 moved the importable code from the `fastmcp` distribution into `fastmcp-slim`. During a single-command `pip` upgrade, pip can install the new files and then delete them while uninstalling the old `fastmcp` distribution, whose file manifest still lists those paths. `uv` uninstalls before it installs, so it is unaffected.

## Versioning Policy

FastMCP follows semantic versioning with pragmatic adaptations for the rapidly evolving MCP ecosystem. Breaking changes may occur in minor versions (e.g., 4.1.x to 4.2.0) when necessary to stay current with the MCP Protocol.

For production use, use a lockfile or pin an exact version:

```text theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp==4.0.5    # Good - an exact version
fastmcp>=4.0.0    # Bad - may install breaking changes
```

See the full [versioning and release policy](https://gofastmcp.com/docs/development/releases.md#versioning-policy) for details on our public API, deprecation practices, and breaking change philosophy.

## Contributing to FastMCP

The [Contributing Guide](https://gofastmcp.com/docs/development/contributing.md) covers setting up a development environment, running the test suite and pre-commit hooks, and the standards we hold contributed code to.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.