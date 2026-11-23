> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# vendor_providers

# `fastmcp.server.providers.skills.vendor_providers`

Vendor-specific skills providers for various AI coding platforms.

## Classes

### `CursorSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L11](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L11)</sup>

Cursor skills from \~/.cursor/skills/.

### `VSCodeSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L29](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L29)</sup>

VS Code skills from \~/.copilot/skills/.

### `CodexSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L47](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L47)</sup>

Codex skills from /etc/codex/skills/ and \~/.codex/skills/.

Scans both system-level and user-level directories. System skills take
precedence if duplicates exist.

### `GeminiSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L73](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L73)</sup>

Gemini skills from \~/.gemini/skills/.

### `GooseSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L91](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L91)</sup>

Goose skills from \~/.config/agents/skills/.

### `CopilotSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L109](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L109)</sup>

GitHub Copilot skills from \~/.copilot/skills/.

### `OpenCodeSkillsProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/vendor\_providers.py#L127](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/vendor_providers.py#L127)</sup>

OpenCode skills from \~/.config/opencode/skills/.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.