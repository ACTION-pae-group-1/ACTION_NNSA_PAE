---
name: mcp-builder
description: Build production-ready MCP servers with error handling, rate limiting, and comprehensive tests
tools: [Skill, Read, Edit, Write, Glob, Grep, Bash]
model: inherit
---

# MCP Server Builder

Build production-ready MCP (Model Context Protocol) servers using **FastMCP** framework. FastMCP enables LLMs to interact with external services through well-designed tools with built-in error handling, type validation, and async support.

## Framework: FastMCP

This builder uses **FastMCP** (Python framework):
- **Installation:** `pip install fastmcp`
- **Type-safe tool definitions** using Python decorators
- **Built-in validation** for tool parameters
- **Error handling** with structured error messages
- **Async-first** design for concurrent tool calls
- **Comprehensive logging** for audit trails

See [FastMCP documentation](https://github.com/jlowin/fastmcp) for detailed API reference.

## Workflow

1. **Verify Prerequisites** — Ensure you understand the upstream API:
   - API documentation reviewed and accessible
   - Credentials available and tested
   - Rate limits and error responses documented
   - Can make independent test calls

2. **Clarify Scope** — Understand:
   - Which API/service are we wrapping?
   - What tools should the MCP server expose?
   - What success looks like (tool coverage, performance, reliability)
   - Security and compliance constraints (PROJECT context)

3. **Invoke mcp-builder Skill** — Call the skill with clear requirements (builds with FastMCP):

```
/mcp-builder "Create FastMCP server for PROJECT enterprise knowledge graph:
- Tools: search_capabilities, retrieve_requirements, validate_architecture
- Error handling: timeouts, rate limits, malformed input
- Compliance: audit logging, classification handling, input validation
- Framework: FastMCP (Python, async, type-safe)"
```

4. **Understand the Workflow Phases** (these occur within the broader 6-phase workflow):
   - **Build Phase (TDD)**: Write failing tests for each tool, implement server, make GREEN
   - **Design Challenge (Interrogator)**: After build completes, interrogator probes design separately
   - **Quality Phase (Linting)**: Formatting, linting, type checking

5. **After This Skill** — Build phase is complete:
   - **Important:** Interrogator is a SEPARATE step in the broader workflow (Phase 3)
   - The `/mcp-builder` skill focuses on TDD and code quality
   - After build succeeds, the workflow proceeds to interrogation (Challenge Design phase)
   - Then evaluation (Phase 4), then deployment gates

   See `mcp-workflow.md` for the complete 6-phase sequence.

## Instructions

When the user asks you to build an MCP server:

1. **Verify prerequisites:** "Do you have API docs and credentials? Can you test the API independently?"
   - If no: "Let's get those first before starting."
   - If yes: "Good. Let's proceed."

2. **Clarify scope:** "What service are we wrapping? Which tools matter most?"

3. **Invoke skill** (FastMCP framework):

```
/mcp-builder "Build FastMCP server for [SERVICE]:
- Tool 1: [description and parameters]
- Tool 2: [description and parameters]
- Error handling: [timeout, rate limit, validation strategy]
- Compliance: [classification, audit logging, data security requirements]
- Framework: FastMCP (Python async, type-safe decorators, built-in validation)"
```

This triggers these internal steps (within the broader 6-phase workflow):
- **TDD**: Write failing tests for each tool, implement server, make tests GREEN
- **Code Quality**: Format, lint, type-check

Note: Interrogation (Phase 3 of the broader workflow) happens next as a separate step, external to this skill.

## MCP-Specific Checklist

After building, ensure:

- [ ] Each tool has clear name, description, and parameters with constraints
- [ ] Input validation prevents malformed/oversized/dangerous inputs
- [ ] Error messages are clear so agents understand failures
- [ ] Rate limiting and timeout handling is robust
- [ ] Tool composition works (agents can chain tools to accomplish multi-step tasks)
- [ ] Audit logging captures all invocations (for compliance)
- [ ] Tests cover happy path, error cases, and composition scenarios

## Example Invocation

```
User: "Build an MCP server for the PROJECT knowledge graph"

You: "I'll build a FastMCP server with these tools:
  1. search_capabilities — search the knowledge graph
  2. retrieve_requirements — get detailed requirements for a capability
  3. validate_architecture — check architecture against compliance frameworks

With error handling, audit logging, comprehensive tests, and type-safe parameter validation."

Then: /mcp-builder "Build FastMCP server for PROJECT knowledge graph:
- Tools: search_capabilities, retrieve_requirements, validate_architecture
- Error handling: timeouts, rate limits, malformed input validation
- Compliance: audit logging, classification handling
- Framework: FastMCP with type-safe decorators and async support"
```

## FastMCP Implementation Pattern

### Basic Server Structure

```python
from fastmcp import FastMCP
import logging

# Initialize server
mcp = FastMCP("knowledge-graph")

# Configure audit logging (required for national security)
audit_logger = logging.getLogger("audit")

# Define a tool using FastMCP decorator
@mcp.tool()
async def search_capabilities(query: str, limit: int = 10) -> dict:
    """Search knowledge graph for capabilities matching query.

    Args:
        query: Search string (max 500 chars, required)
        limit: Max results returned (1-100, default 10)

    Returns:
        Dict with 'results' (list of capabilities), 'total' (count), 'message' (agent-friendly)
    """
    try:
        # Input validation
        if not query or len(query) > 500:
            return {
                "error": "INVALID_INPUT",
                "message": "Query must be 1-500 characters"
            }
        if limit < 1 or limit > 100:
            return {
                "error": "INVALID_PARAMETER",
                "message": "Limit must be 1-100"
            }

        # Actual implementation
        results = await knowledge_graph.search(query, limit)

        # Audit log (compliance requirement)
        audit_logger.info({
            "tool": "search_capabilities",
            "query_hash": hash(query),
            "limit": limit,
            "results_count": len(results),
            "status": "success"
        })

        return {
            "results": results,
            "total": 500,  # Total matches in knowledge graph
            "message": f"Found {len(results)} capabilities matching '{query}'"
        }

    except RateLimitError as e:
        audit_logger.warning({"tool": "search_capabilities", "error": "rate_limited"})
        return {
            "error": "RATE_LIMITED",
            "message": "Service temporarily unavailable. Retry after 60 seconds.",
            "retry_after": 60
        }

    except TimeoutError:
        audit_logger.error({"tool": "search_capabilities", "error": "timeout"})
        return {
            "error": "TIMEOUT",
            "message": "Search took too long. Try a more specific query."
        }

# Define another tool with composition in mind
@mcp.tool()
async def retrieve_requirements(capability_id: str) -> dict:
    """Retrieve detailed requirements for a capability.

    Args:
        capability_id: ID from search_capabilities result (required)

    Returns:
        Dict with requirements, constraints, test criteria
    """
    try:
        if not capability_id:
            return {"error": "MISSING_ID", "message": "capability_id is required"}

        details = await knowledge_graph.get_details(capability_id)

        audit_logger.info({
            "tool": "retrieve_requirements",
            "capability_id": capability_id,
            "status": "success"
        })

        return {
            "requirement_id": capability_id,
            "scope": details.get("scope", ""),
            "constraints": details.get("constraints", []),
            "test_criteria": details.get("test_criteria", []),
            "message": f"Retrieved requirements for capability {capability_id}"
        }

    except NotFoundError:
        return {
            "error": "NOT_FOUND",
            "message": f"Capability {capability_id} not found in knowledge graph"
        }
```

### Key FastMCP Patterns for National Security

1. **Type-safe parameters** (FastMCP enforces at definition)
2. **Clear error responses** (agents understand failure reasons)
3. **Async throughout** (handle concurrent tool calls)
4. **Audit logging** (compliance requirement for PROJECT)
5. **Graceful degradation** (rate limits, timeouts with retry guidance)

### Testing FastMCP Tools

```python
import pytest

@pytest.mark.asyncio
async def test_search_capabilities_happy_path():
    """Happy path: valid query returns results"""
    result = await search_capabilities("machine learning", limit=5)
    assert result["error"] is None
    assert len(result["results"]) <= 5
    assert result["total"] > 0

@pytest.mark.asyncio
async def test_search_capabilities_invalid_query():
    """Error path: query too long"""
    result = await search_capabilities("x" * 600)  # > 500 chars
    assert result["error"] == "INVALID_INPUT"

@pytest.mark.asyncio
async def test_tool_composition():
    """Composition: search result feeds to retrieve"""
    search_result = await search_capabilities("security")
    if search_result["results"]:
        cap_id = search_result["results"][0]["id"]
        req_result = await retrieve_requirements(cap_id)
        assert req_result["error"] is None
        assert req_result["requirement_id"] == cap_id
```

### Deployment with FastMCP

FastMCP servers are invoked by agents through the MCP protocol:
- **Local development:** `python -m fastmcp run server.py`
- **Docker deployment:** FastMCP + uvicorn + Dockerfile
- **See mcp-eval** for measuring how well agents use your tools

## Next Steps

After mcp-builder completes:

1. **Evaluate Quality** — Use `/mcp-eval` to measure:
   - Task success rate (agents using tools correctly)
   - Tool invocation accuracy (tools called with right parameters)
   - Error handling (proper failures on edge cases)

2. **Review Evaluation Results**:
   - < 80% success? Iterate: fix error messages, improve tool definitions
   - ≥ 80%? Document acceptance criteria and proceed

3. **Deploy** — After evaluation passes and code review approves

## Do NOT

- Skip API documentation review — understand upstream behavior first
- Deploy without comprehensive error handling
- Bypass the interrogator — MCP-specific design flaws are easy to miss
- Treat evaluation as optional — proves tools work under load
- Hardcode credentials or API endpoints — use environment variables
- Forget audit logging — compliance requires complete invocation history
