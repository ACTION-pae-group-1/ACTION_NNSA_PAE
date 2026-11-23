> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# dependencies

# `fastmcp.dependencies`

Dependency injection exports for FastMCP.

This module re-exports dependency injection symbols to provide a clean,
centralized import location for all dependency-related functionality.

DI features (Depends, CurrentContext, CurrentFastMCP) work without pydocket
using the uncalled-for DI engine. The docket-specific dependencies
(`CurrentDocket`, `CurrentWorker`) live in the `fastmcp-tasks` package
(`fastmcp_tasks.dependencies`).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.