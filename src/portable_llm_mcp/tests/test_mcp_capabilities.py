"""Public MCPHub resources, templates and prompts: policies and SDK contracts."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import AnyUrl, BaseModel, Field

from portable_llm_mcp.mcp_client import (
    MCPConfigurationError,
    MCPHub,
    ServerConfig,
    load_mcp_servers,
)


class Resource(BaseModel):
    uri: AnyUrl
    name: str
    mime_type: str = Field(alias="mimeType")


class FakeSession:
    """Mimic the MCP 1.x ClientSession responses, including paginated listings."""

    def __init__(self) -> None:
        self.resources_calls: list[str | None] = []
        self.template_calls: list[str | None] = []
        self.prompt_calls: list[str | None] = []
        self.resource_reads: list[str] = []
        self.rendered_prompts: list[tuple[str, dict[str, str]]] = []

    async def list_resources(self, cursor: str | None = None):
        self.resources_calls.append(cursor)
        if cursor is None:
            return SimpleNamespace(
                resources=[
                    Resource(
                        uri=AnyUrl("guide://escalation-workflow"),
                        name="Workflow",
                        mimeType="text/markdown",
                    )
                ],
                nextCursor="page2",
            )
        assert cursor == "page2"
        return SimpleNamespace(
            resources=[
                Resource(
                    uri=AnyUrl("setup://bls-api"),
                    name="API setup",
                    mimeType="text/markdown",
                )
            ],
            nextCursor=None,
        )

    async def list_resource_templates(self, cursor: str | None = None):
        self.template_calls.append(cursor)
        return SimpleNamespace(
            resourceTemplates=[
                {"uriTemplate": "bls://series/{series_id}", "name": "Series"}
            ],
            nextCursor=None,
        )

    async def list_prompts(self, cursor: str | None = None):
        self.prompt_calls.append(cursor)
        return SimpleNamespace(
            prompts=[
                {
                    "name": "design_escalation_basket",
                    "arguments": [
                        {"name": "project_description", "required": True},
                        {"name": "base_period", "required": False},
                    ],
                },
                {"name": "not_approved", "arguments": []},
            ],
            nextCursor=None,
        )

    async def read_resource(self, uri: AnyUrl):
        self.resource_reads.append(str(uri))
        return SimpleNamespace(
            contents=[
                SimpleNamespace(text=f"REFERENCE: {uri}"),
                SimpleNamespace(mimeType="image/png", blob="aVeryLargeBase64Blob"),
            ]
        )

    async def get_prompt(self, name: str, arguments: dict[str, str]):
        self.rendered_prompts.append((name, arguments))
        return SimpleNamespace(
            messages=[
                SimpleNamespace(
                    role="user",
                    content=SimpleNamespace(
                        text=f"Design basket: {arguments['project_description']}"
                    ),
                ),
                SimpleNamespace(
                    role="assistant",
                    content=SimpleNamespace(type="image", data="base64secret"),
                ),
            ]
        )


def make_hub(
    *,
    resources: tuple[str, ...] = (),
    prompts: tuple[str, ...] = (),
    capabilities: SimpleNamespace | None = None,
    max_chars: int = 16000,
) -> tuple[MCPHub, FakeSession]:
    hub = MCPHub(
        {
            "bls_server": ServerConfig(
                "streamable_http",
                ("search_series",),
                url="http://127.0.0.1:8821/mcp",
                allowed_resources=resources,
                allowed_prompts=prompts,
            )
        },
        max_result_chars=max_chars,
    )
    session = FakeSession()
    hub._sessions["bls_server"] = session
    if capabilities is not None:
        hub._capabilities["bls_server"] = capabilities
    return hub, session


def test_manifest_defaults_to_no_resource_or_prompt_access(tmp_path) -> None:
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            {
                "servers": {
                    "bls_server": {
                        "transport": "streamable_http",
                        "url": "http://localhost:8821/mcp",
                        "allowed_tools": ["search_series"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = load_mcp_servers(path)["bls_server"]
    assert config.allowed_resources == ()
    assert config.allowed_prompts == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("allowed_resources", "*"),
        ("allowed_resources", [""]),
        ("allowed_prompts", [1]),
        ("allowed_prompts", None),
    ],
)
def test_invalid_capability_allowlists_are_refused(tmp_path, field, value) -> None:
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            {
                "servers": {
                    "bls_server": {
                        "transport": "streamable_http",
                        "url": "http://localhost:8821/mcp",
                        field: value,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(MCPConfigurationError, match=field):
        load_mcp_servers(path)


@pytest.mark.asyncio
async def test_default_denial_does_not_contact_server_capabilities() -> None:
    hub, session = make_hub()
    assert await hub.list_resources() == []
    assert await hub.list_resource_templates() == []
    assert await hub.list_prompts() == []
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.read_resource("bls_server", "guide://escalation-workflow")
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.get_prompt("bls_server", "design_escalation_basket")
    assert session.resources_calls == []
    assert session.template_calls == []
    assert session.prompt_calls == []


@pytest.mark.asyncio
async def test_lists_filter_unauthorized_resources_and_prompts_with_pagination() -> (
    None
):
    hub, session = make_hub(
        resources=("guide://escalation-workflow", "bls://series/{series_id}"),
        prompts=("design_escalation_basket",),
    )
    resources = await hub.list_resources()
    assert resources == [
        {
            "server": "bls_server",
            "uri": "guide://escalation-workflow",
            "name": "Workflow",
            "mimeType": "text/markdown",
        }
    ]
    assert session.resources_calls == [None, "page2"]
    templates = await hub.list_resource_templates("bls_server")
    assert templates == [
        {
            "server": "bls_server",
            "uriTemplate": "bls://series/{series_id}",
            "name": "Series",
        }
    ]
    assert (await hub.list_prompts())[0]["name"] == "design_escalation_basket"
    assert len(await hub.list_prompts()) == 1
    assert session.prompt_calls == [None]
    # Listing results remain cached; repeated reads do not refetch page 1.
    assert await hub.list_resources() == resources
    assert session.resources_calls == [None, "page2"]


@pytest.mark.asyncio
async def test_read_resource_validates_discovery_permissions_and_template_expansion() -> (
    None
):
    hub, session = make_hub(
        resources=("guide://escalation-workflow", "bls://series/{series_id}"),
    )
    guide = await hub.read_resource("bls_server", "guide://escalation-workflow")
    assert "REFERENCE: guide://escalation-workflow" in guide
    assert "binary MCP resource omitted: image/png" in guide
    assert "aVeryLargeBase64Blob" not in guide
    series = await hub.read_resource("bls_server", "bls://series/WPU1017")
    assert "WPU1017" in series
    assert session.resource_reads == [
        "guide://escalation-workflow",
        "bls://series/WPU1017",
    ]
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.read_resource("bls_server", "setup://bls-api")
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.read_resource("bls_server", "bls://series/WPU1017/other")
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.read_resource("bls_server", "guide://not-registered")
    assert len(session.resource_reads) == 2


@pytest.mark.asyncio
async def test_wildcard_still_requires_server_advertisement() -> None:
    hub, session = make_hub(resources=("*",), prompts=("*",))
    assert len(await hub.list_resources()) == 2
    assert len(await hub.list_resource_templates()) == 1
    assert len(await hub.list_prompts()) == 2
    with pytest.raises(MCPConfigurationError, match="not advertised"):
        await hub.read_resource("bls_server", "http://example.com/secret")
    with pytest.raises(MCPConfigurationError, match="not advertised"):
        await hub.get_prompt("bls_server", "unknown", {})
    assert not session.resource_reads
    assert not session.rendered_prompts


@pytest.mark.asyncio
async def test_render_prompt_validates_arguments_and_preserves_roles() -> None:
    hub, session = make_hub(prompts=("design_escalation_basket",))
    for args, pattern in [
        ({}, "Required"),
        ({"project_description": 5}, "strings"),
        ({"project_description": "steel", "fake": "value"}, "Unknown"),
    ]:
        with pytest.raises(MCPConfigurationError, match=pattern):
            await hub.get_prompt("bls_server", "design_escalation_basket", args)
    assert not session.rendered_prompts
    answer = await hub.get_prompt(
        "bls_server", "design_escalation_basket", {"project_description": "steel"}
    )
    assert "[user] Design basket: steel" in answer
    assert "[assistant] [non-text MCP prompt content omitted]" in answer
    assert "base64secret" not in answer
    assert session.rendered_prompts == [
        ("design_escalation_basket", {"project_description": "steel"})
    ]


@pytest.mark.asyncio
async def test_unsupported_pars_capabilities_are_empty_and_not_called() -> None:
    hub, session = make_hub(
        resources=("*",),
        prompts=("*",),
        capabilities=SimpleNamespace(resources=None, prompts=None),
    )
    assert await hub.list_resources() == []
    assert await hub.list_resource_templates() == []
    assert await hub.list_prompts() == []
    assert not session.resources_calls
    assert not session.template_calls
    assert not session.prompt_calls


@pytest.mark.asyncio
async def test_output_is_bounded_and_unknown_server_is_rejected() -> None:
    hub, _ = make_hub(resources=("*",), prompts=("*",), max_chars=35)
    text = await hub.read_resource("bls_server", "guide://escalation-workflow")
    assert text.endswith("[resource truncated]")
    assert len(text.split("\n[resource truncated]")[0]) == 35
    prompt = await hub.get_prompt(
        "bls_server", "design_escalation_basket", {"project_description": "steel"}
    )
    assert prompt.endswith("[prompt truncated]")
    with pytest.raises(MCPConfigurationError, match="Unknown or disconnected"):
        await hub.list_prompts("nonexistent")
    with pytest.raises(MCPConfigurationError, match="Unknown or disconnected"):
        await hub.read_resource("nonexistent", "guide://escalation-workflow")


@pytest.mark.asyncio
async def test_session_cleanup_clears_capability_metadata() -> None:
    hub, _ = make_hub(resources=("*",), prompts=("*",))
    await hub.list_resources()
    assert hub._discovery
    await hub.__aexit__()
    assert hub._sessions == {}
    assert hub._discovery == {}
    assert hub._capabilities == {}


@pytest.mark.asyncio
async def test_asksage_cli_bridge_uses_public_hub_capabilities(monkeypatch) -> None:
    """CLI commands must not rely on MCPHub's internal SDK sessions."""
    import importlib
    import sys
    from types import ModuleType

    # The production script injects the OS certificate store; tests need not.
    fake_truststore = ModuleType("truststore")
    fake_truststore.inject_into_ssl = lambda: None
    monkeypatch.setitem(sys.modules, "truststore", fake_truststore)
    cli = importlib.import_module("portable_llm_mcp.examples.asksage_chat")

    hub, session = make_hub(
        resources=("guide://escalation-workflow", "bls://series/{series_id}"),
        prompts=("design_escalation_basket",),
    )
    bridge = cli.ResourcePromptBridge(hub)
    await bridge.discover()
    assert "guide://escalation-workflow" in bridge.resource_inventory()
    assert "bls://series/{series_id}" in bridge.resource_inventory()
    assert "design_escalation_basket" in bridge.prompt_inventory()
    assert "WPU1017" in await bridge.read_resource("bls_server", "bls://series/WPU1017")
    assert "Design basket: steel" in await bridge.get_prompt(
        "bls_server", "design_escalation_basket", {"project_description": "steel"}
    )
    assert session.resource_reads == ["bls://series/WPU1017"]
