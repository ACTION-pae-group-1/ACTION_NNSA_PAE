"""MCP session manager: tools, resources, templates and prompts by server."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Self

import httpx


class MCPConfigurationError(ValueError):
    """Invalid MCP server configuration or tool policy."""


class MCPServerStartError(RuntimeError):
    """A configured MCP server failed while starting or initializing.

    ``server`` is the configured server name; the original exception is chained
    as ``__cause__`` for local diagnostics and is not included in the message.
    """

    def __init__(self, server: str, error_type: str) -> None:
        super().__init__(f"MCP server '{server}' failed to start ({error_type})")
        self.server = server
        self.error_type = error_type


@dataclass(frozen=True)
class ServerConfig:
    transport: str
    allowed_tools: tuple[str, ...]  # Explicit allowlist; '*' opts into all tools.
    command: str | None = None
    args: tuple[str, ...] = ()
    env: Mapping[str, str] | None = None
    url: str | None = None
    headers: Mapping[str, str] | None = None
    # Independent opt-in policies: tool permission does not imply resource or
    # prompt permission. Entries are exact URIs/names, URI templates, or '*'.
    allowed_resources: tuple[str, ...] = ()
    allowed_prompts: tuple[str, ...] = ()


def _expand(value: str, environment: Mapping[str, str]) -> str:
    """Expand only ${VARIABLE} references, refusing undefined secrets."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in environment or not environment[name]:
            raise MCPConfigurationError(f"Missing environment variable: {name}")
        return environment[name]

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)


def load_mcp_servers(
    path: str | Path, *, environment: Mapping[str, str] | None = None
) -> dict[str, ServerConfig]:
    """Load a standalone JSON server manifest (no code execution)."""
    env = os.environ if environment is None else environment
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        servers = document["servers"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise MCPConfigurationError("Cannot read MCP server configuration") from exc
    if not isinstance(servers, dict):
        raise MCPConfigurationError("'servers' must be an object")
    output = {}
    for name, value in servers.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", name):
            raise MCPConfigurationError("Invalid MCP server name")
        if not isinstance(value, dict):
            raise MCPConfigurationError(f"Server {name}: expected object")
        transport = value.get("transport", "stdio")
        if transport not in ("stdio", "streamable_http"):
            raise MCPConfigurationError(f"Server {name}: unsupported transport")
        allowed = value.get("allowed_tools", [])
        if not isinstance(allowed, list) or any(
            not isinstance(x, str) for x in allowed
        ):
            raise MCPConfigurationError(f"Server {name}: allowed_tools must be a list")
        allowed_resources = value.get("allowed_resources", [])
        allowed_prompts = value.get("allowed_prompts", [])
        for label, entries in (
            ("allowed_resources", allowed_resources),
            ("allowed_prompts", allowed_prompts),
        ):
            if not isinstance(entries, list) or any(
                not isinstance(entry, str) or not entry.strip() for entry in entries
            ):
                raise MCPConfigurationError(
                    f"Server {name}: {label} must be a list of nonempty strings"
                )
        command = value.get("command")
        args = value.get("args", [])
        url = value.get("url")
        headers = value.get("headers", {})
        custom_env = value.get("env", {})
        if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
            raise MCPConfigurationError(f"Server {name}: args must be strings")
        if not isinstance(headers, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()
        ):
            raise MCPConfigurationError(f"Server {name}: headers must be strings")
        if not isinstance(custom_env, dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in custom_env.items()
        ):
            raise MCPConfigurationError(f"Server {name}: env must be strings")
        if transport == "stdio" and (not isinstance(command, str) or not command):
            raise MCPConfigurationError(f"Server {name}: command required")
        if transport == "streamable_http" and (
            not isinstance(url, str) or not url.startswith(("http://", "https://"))
        ):
            raise MCPConfigurationError(f"Server {name}: HTTP(S) url required")
        output[name] = ServerConfig(
            transport=transport,
            allowed_tools=tuple(allowed),
            command=_expand(command, env) if command else None,
            args=tuple(_expand(arg, env) for arg in args),
            # None tells the SDK to inherit its own minimal default environment.
            env={k: _expand(v, env) for k, v in custom_env.items()} or None,
            url=_expand(url, env) if url else None,
            headers={k: _expand(v, env) for k, v in headers.items()} or None,
            allowed_resources=tuple(allowed_resources),
            allowed_prompts=tuple(allowed_prompts),
        )
    return output


async def _probe_reachable(name: str, url: str) -> None:
    """Report a refused or unreachable HTTP MCP server as a startup failure.

    A refused connection inside the SDK transport cancels the startup task
    instead of raising a clear error, so the check runs before the session.
    """
    async with httpx.AsyncClient(timeout=5.0) as probe:
        try:
            await probe.get(url)
        except httpx.TransportError as exc:
            raise MCPServerStartError(name, type(exc).__name__) from exc


class MCPHub:
    """Manage MCP connections and explicitly permitted capabilities.

    Tools are model-facing via ``tool_definitions``; resources and prompts are
    accessed through the public async methods below. Calling these methods
    does not automatically place their contents into an LLM conversation.
    A server connection is a trust decision: use only approved servers.
    """

    def __init__(
        self, servers: Mapping[str, ServerConfig], *, max_result_chars: int = 16000
    ):
        if max_result_chars <= 0:
            raise ValueError("max_result_chars must be positive")
        self.servers = dict(servers)
        self.max_result_chars = max_result_chars
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, Any] = {}
        self._registry: dict[str, tuple[str, str, dict[str, Any]]] = {}
        self._capabilities: dict[str, Any] = {}
        # MCP listing results, cached per connected session and capability.
        self._discovery: dict[tuple[str, str], list[dict[str, Any]]] = {}
        # Name of the server currently being started, for startup diagnostics.
        self._starting: str | None = None

    async def __aenter__(self) -> Self:
        if self._stack is not None:
            raise RuntimeError("MCPHub is already open")
        self._stack = AsyncExitStack()
        try:
            await self._connect()
        except BaseException as exc:
            starting = self._starting
            # Cleanup of a failed start must not replace the startup error.
            with suppress(Exception):
                await self._stack.aclose()
            self._stack = None
            self._sessions.clear()
            self._registry.clear()
            self._capabilities.clear()
            self._discovery.clear()
            self._starting = None
            if isinstance(exc, MCPServerStartError):
                raise
            if (
                isinstance(exc, Exception)
                and not isinstance(exc, MCPConfigurationError)
                and starting is not None
            ):
                raise MCPServerStartError(starting, type(exc).__name__) from exc
            raise
        return self

    async def _connect(self) -> None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise MCPConfigurationError(
                "Install this package to obtain the MCP SDK"
            ) from exc
        assert self._stack is not None
        for name, server in self.servers.items():
            self._starting = name
            if server.transport == "stdio":
                if not server.command:
                    raise MCPConfigurationError(f"Server {name}: command required")
                # Do not forward the entire parent env (may contain LLM secrets).
                # Preserve minimal subprocess requirements when custom values exist.
                safe_env = None
                if server.env is not None:
                    inherited = {
                        k: os.environ[k]
                        for k in (
                            "PATH",
                            "HOME",
                            "SYSTEMROOT",
                            "WINDIR",
                            "TEMP",
                            "TMP",
                            "TMPDIR",
                        )
                        if k in os.environ
                    }
                    safe_env = {**inherited, **server.env}
                params = StdioServerParameters(
                    command=server.command, args=list(server.args), env=safe_env
                )
                read, write = await self._stack.enter_async_context(
                    stdio_client(params)
                )
            elif server.transport == "streamable_http":
                if not server.url:
                    raise MCPConfigurationError(f"Server {name}: HTTP(S) url required")
                await _probe_reachable(name, server.url)
                # The SDK configures HTTP headers on the client, not the transport.
                # Keep its standard MCP request/read timeouts for long tool calls.
                http_client = await self._stack.enter_async_context(
                    httpx.AsyncClient(
                        headers=dict(server.headers or {}),
                        timeout=httpx.Timeout(30.0, read=300.0),
                    )
                )
                read, write, _ = await self._stack.enter_async_context(
                    streamable_http_client(server.url, http_client=http_client)
                )
            else:
                raise MCPConfigurationError(f"Server {name}: unsupported transport")
            session = await self._stack.enter_async_context(ClientSession(read, write))
            initialized = await session.initialize()
            self._sessions[name] = session
            self._capabilities[name] = getattr(initialized, "capabilities", None)
            tools = (await session.list_tools()).tools
            for tool in tools:
                if (
                    tool.name not in server.allowed_tools
                    and "*" not in server.allowed_tools
                ):
                    continue
                key = self._qualified_name(name, tool.name)
                if key in self._registry:
                    raise MCPConfigurationError("MCP tool name collision")
                self._registry[key] = (
                    name,
                    tool.name,
                    {
                        "type": "function",
                        "function": {
                            "name": key,
                            "description": (tool.description or "MCP tool")[:1000],
                            "parameters": tool.inputSchema
                            or {"type": "object", "properties": {}},
                        },
                    },
                )
        self._starting = None

    @staticmethod
    def _qualified_name(server: str, tool: str) -> str:
        import hashlib

        raw = f"{server}__{tool}"
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", raw)
        if len(cleaned) > 64:
            cleaned = cleaned[:55] + "_" + hashlib.sha256(raw.encode()).hexdigest()[:8]
        return cleaned

    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-style JSON tool definitions compatible with the adapters."""
        return [record[2] for record in self._registry.values()]

    async def call_tool(
        self,
        qualified_name: str,
        arguments: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        """Invoke an allowed tool; optionally bound the MCP response wait.

        A client-side timeout does not terminate a hung synchronous server
        worker.  Prefer preventing the underlying stall where possible.
        """
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        if timeout_seconds is not None and (
            isinstance(timeout_seconds, bool) or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")
        try:
            server, native_name, _ = self._registry[qualified_name]
        except KeyError as exc:
            raise MCPConfigurationError("Requested MCP tool is not allowed") from exc
        kwargs: dict[str, Any] = {"arguments": arguments}
        if timeout_seconds is not None:
            kwargs["read_timeout_seconds"] = timedelta(seconds=timeout_seconds)
        result = await self._sessions[server].call_tool(native_name, **kwargs)
        items: list[str] = []
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            items.append(json.dumps(structured, ensure_ascii=False, default=str))
        else:
            for block in result.content:
                if getattr(block, "type", None) == "text":
                    items.append(str(block.text))
                else:
                    items.append(
                        f"[non-text MCP content: {getattr(block, 'type', 'unknown')}]"
                    )
        message = "\n".join(items) or "(empty MCP result)"
        if getattr(result, "isError", False):
            message = "MCP tool reported an error: " + message
        if len(message) > self.max_result_chars:
            message = message[: self.max_result_chars] + "\n[tool result truncated]"
        return message

    def _selected_servers(self, server: str | None) -> list[str]:
        if server is not None:
            if server not in self.servers or server not in self._sessions:
                raise MCPConfigurationError("Unknown or disconnected MCP server")
            return [server]
        return list(self._sessions)

    @staticmethod
    def _as_metadata(record: Any) -> dict[str, Any]:
        """Convert MCP SDK metadata to JSON-compatible public dictionaries."""
        if isinstance(record, Mapping):
            return dict(record)
        if hasattr(record, "model_dump"):
            return record.model_dump(mode="json", by_alias=True, exclude_none=True)
        # Also support simple SDK-shaped test doubles without a pydantic base.
        fields = (
            "uri",
            "uriTemplate",
            "name",
            "title",
            "description",
            "mimeType",
            "arguments",
        )
        return {
            field: getattr(record, field) for field in fields if hasattr(record, field)
        }

    @staticmethod
    def _matches_template(uri: str, template: str) -> bool:
        """Match only named, single-path-segment parameters in an advertised URI."""
        if "{" not in template and "}" not in template:
            return uri == template
        tokens = re.split(r"(\{[A-Za-z_][A-Za-z0-9_]*\})", template)
        if not any(re.fullmatch(r"\{[A-Za-z_][A-Za-z0-9_]*\}", t) for t in tokens):
            return False
        pattern = "".join(
            r"[^/?#]+"
            if re.fullmatch(r"\{[A-Za-z_][A-Za-z0-9_]*\}", t)
            else re.escape(t)
            for t in tokens
        )
        return bool(re.fullmatch(pattern, uri))

    @classmethod
    def _resource_permitted(cls, uri: str, permissions: tuple[str, ...]) -> bool:
        return "*" in permissions or any(
            cls._matches_template(uri, rule) for rule in permissions
        )

    async def _discover(self, name: str, kind: str) -> list[dict[str, Any]]:
        key = (name, kind)
        if key in self._discovery:
            return self._discovery[key]
        capabilities = self._capabilities.get(name)
        flag = "resources" if kind != "prompts" else "prompts"
        if capabilities is not None and getattr(capabilities, flag, None) is None:
            self._discovery[key] = []
            return []
        method, attribute = {
            "resources": ("list_resources", "resources"),
            "templates": ("list_resource_templates", "resourceTemplates"),
            "prompts": ("list_prompts", "prompts"),
        }[kind]
        entries: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        cursor: str | None = None
        # A low-level MCP server can paginate. Never silently drop later pages.
        for _ in range(100):
            kwargs = {"cursor": cursor} if cursor is not None else {}
            page = await getattr(self._sessions[name], method)(**kwargs)
            entries.extend(
                self._as_metadata(item) for item in getattr(page, attribute, [])
            )
            if len(entries) > 5000:
                raise MCPConfigurationError(
                    "MCP capability listing exceeds safety limit"
                )
            cursor = getattr(page, "nextCursor", None) or getattr(
                page, "next_cursor", None
            )
            if cursor is None:
                self._discovery[key] = entries
                return entries
            if cursor in seen_cursors:
                raise MCPConfigurationError("MCP capability listing repeated a cursor")
            seen_cursors.add(cursor)
        raise MCPConfigurationError("MCP capability listing exceeded 100 pages")

    async def list_resources(self, server: str | None = None) -> list[dict[str, Any]]:
        """List permitted static resources, annotated with their MCP server."""
        result: list[dict[str, Any]] = []
        for name in self._selected_servers(server):
            allowed = self.servers[name].allowed_resources
            if not allowed:
                continue
            for resource in await self._discover(name, "resources"):
                uri = str(resource.get("uri", ""))
                if self._resource_permitted(uri, allowed):
                    result.append({"server": name, **resource, "uri": uri})
        return result

    async def list_resource_templates(
        self, server: str | None = None
    ) -> list[dict[str, Any]]:
        """List permitted parameterized resource URI templates."""
        result: list[dict[str, Any]] = []
        for name in self._selected_servers(server):
            allowed = self.servers[name].allowed_resources
            if not allowed:
                continue
            for template in await self._discover(name, "templates"):
                uri = str(template.get("uriTemplate", ""))
                if "*" in allowed or uri in allowed:
                    result.append({"server": name, **template, "uriTemplate": uri})
        return result

    async def list_prompts(self, server: str | None = None) -> list[dict[str, Any]]:
        """List permitted MCP prompt definitions, including argument contracts."""
        result: list[dict[str, Any]] = []
        for name in self._selected_servers(server):
            allowed = self.servers[name].allowed_prompts
            if not allowed:
                continue
            for prompt in await self._discover(name, "prompts"):
                if "*" in allowed or prompt.get("name") in allowed:
                    result.append({"server": name, **prompt})
        return result

    @staticmethod
    def _bounded_text(text: str, max_chars: int, label: str) -> str:
        return (
            text[:max_chars] + f"\n[{label} truncated]"
            if len(text) > max_chars
            else text
        )

    async def read_resource(self, server: str, uri: str) -> str:
        """Read an advertised and permitted resource, including template URIs.

        Returns bounded UTF-8 text. Binary blobs are not forwarded to the LLM.
        Listing does not execute tools or fetch resource bodies.
        """
        self._selected_servers(server)
        if not isinstance(uri, str) or not uri or len(uri) > 2048:
            raise MCPConfigurationError("Invalid MCP resource URI")
        allowed = self.servers[server].allowed_resources
        if not self._resource_permitted(uri, allowed):
            raise MCPConfigurationError("Requested MCP resource is not allowed")
        static = await self._discover(server, "resources")
        templates = await self._discover(server, "templates")
        advertised = any(str(r.get("uri")) == uri for r in static) or any(
            self._matches_template(uri, str(t.get("uriTemplate", "")))
            for t in templates
        )
        if not advertised:
            raise MCPConfigurationError("Requested MCP resource is not advertised")
        from pydantic import AnyUrl

        response = await self._sessions[server].read_resource(AnyUrl(uri))
        parts = []
        for content in getattr(response, "contents", []):
            if getattr(content, "text", None) is not None:
                parts.append(str(content.text))
            else:
                mime = getattr(content, "mimeType", "unknown MIME")
                parts.append(f"[binary MCP resource omitted: {mime}]")
        return self._bounded_text(
            "\n".join(parts) or "(empty MCP resource)",
            self.max_result_chars,
            "resource",
        )

    async def get_prompt(
        self, server: str, name: str, arguments: Mapping[str, str] | None = None
    ) -> str:
        """Render a permitted server prompt, without running any tools.

        Roles remain visibly labeled in the returned text; prompt content is
        untrusted server data, not a privileged system instruction.
        """
        self._selected_servers(server)
        if not isinstance(name, str) or not name:
            raise MCPConfigurationError("Invalid MCP prompt name")
        allowed = self.servers[server].allowed_prompts
        if "*" not in allowed and name not in allowed:
            raise MCPConfigurationError("Requested MCP prompt is not allowed")
        args = {} if arguments is None else arguments
        if not isinstance(args, Mapping) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in args.items()
        ):
            raise MCPConfigurationError("MCP prompt arguments must be strings")
        if sum(len(k) + len(v) for k, v in args.items()) > 16000:
            raise MCPConfigurationError("MCP prompt arguments are too large")
        prompts = await self.list_prompts(server)
        prompt = next((p for p in prompts if p.get("name") == name), None)
        if prompt is None:
            raise MCPConfigurationError("Requested MCP prompt is not advertised")
        specs = [self._as_metadata(a) for a in (prompt.get("arguments") or [])]
        required = {a["name"] for a in specs if a.get("required")}
        if not required.issubset(args):
            raise MCPConfigurationError("Required MCP prompt arguments are missing")
        names = {a.get("name") for a in specs}
        if any(k not in names for k in args):
            raise MCPConfigurationError("Unknown MCP prompt argument")
        response = await self._sessions[server].get_prompt(name, arguments=dict(args))
        rendered = []
        for message in getattr(response, "messages", []):
            content = getattr(message, "content", None)
            body = getattr(content, "text", None)
            if body is None:
                body = "[non-text MCP prompt content omitted]"
            rendered.append(f"[{getattr(message, 'role', 'user')}] {body}")
        return self._bounded_text(
            "\n".join(rendered) or "(empty MCP prompt)",
            self.max_result_chars,
            "prompt",
        )

    async def __aexit__(self, *_exc: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._sessions.clear()
        self._registry.clear()
        self._capabilities.clear()
        self._discovery.clear()
