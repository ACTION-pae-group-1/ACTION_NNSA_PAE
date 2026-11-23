# Claude Code Agents

Custom agents that automate common tasks. Agents are defined in `.md` files with frontmatter.

## Available Agents

This directory contains reusable agents for common development tasks. All agents below are generic and work with any project structure.

### Complete List of Available Agents

**Implementation & TDD**
- **tdd-enforcer.md** — Enforce test-driven development with red-green-refactor cycle and testing pyramid discipline
- **feature-builder.md** — Guide feature implementation from plan through code to merge readiness
- **slice-orchestrator.md** — Orchestrate vertical-slice implementation across backend/frontend

**Code Review & Quality**
- **interrogator.md** — Rigorous design challenge and risk interrogation before merge; probe assumptions and dependencies
- **code-reviewer.md** — Comprehensive code review for bugs, security, performance, and maintainability

**Architecture & Design**
- **ontologist.md** — Domain modeling and semantic alignment using formal ontology principles
- **git-safety-constraint-agent.md** — Validate and enforce git safety constraints in workflows

**Operations & Governance**
- **agentic-minimum-cd-guru.md** — Audit for continuous delivery compliance (trunk discipline, determinism, rollback)
- **token-minimizer.md** — Fast, token-efficient lookups for code navigation and factual queries

**MCP Integration**
- **mcp-builder.md** — Build high-quality MCP (Model Context Protocol) servers for external API integration
- **mcp-eval.md** — Create LLM-as-judge evaluation harnesses for MCP server capability testing
- **mcp-workflow.md** — Orchestrate multi-agent workflows for complex tasks

### All Agents are Generic

All agents in this directory are generic and reusable across projects. They do not require project-specific configuration or access to project-specific files.

Custom project-specific agents can be added to `.claude/agents/` by creating new `.md` files with the same format—these will be available via `@agent-name` invocation.

## How to Invoke an Agent

Invoke any agent in this directory with:

```
@agent-name "Your prompt"
```

Example:
```
@tdd-enforcer "Implement user authentication"
@interrogator "Challenge this design for security risks"
```

## Creating a New Agent

To add a project-specific agent:

## Agent Frontmatter Format

Each agent `.md` file starts with YAML frontmatter:

```markdown
---
name: agent-name
description: What this agent does (shown in UI)
tools: [Read, Edit, Write, Bash, Agent]  # tools agent can use
model: claude-opus-5-5  # optional; defaults to session model
---

# Agent Instructions

Clear instructions for the agent...
```

## Creating a New Agent

1. Create `.claude/agents/my-agent.md`
2. Add frontmatter (name, description, tools)
3. Write agent instructions
4. Invoke with `@my-agent "prompt"`

## Agents That Trigger Skills

If you want an agent to invoke a specific skill, include skill invocation in the instructions:

```markdown
---
name: feature-implementer
description: Implement a feature using TDD and quality gates
tools: [Read, Edit, Write, Glob, Grep, Bash]
---

# Feature Implementation

Use the `feature-implementation` skill to implement this:

1. Invoke: Skill({"skill": "feature-implementation", "args": "..."})
2. Let TDD flow run
3. Monitor quality gates
```

See the template examples below for working implementations.
