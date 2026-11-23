from __future__ import annotations

import httpx
from fastmcp import FastMCP

from bls_mcp.config import Settings, get_settings
from bls_mcp.lifespan import ServiceHolder, create_lifespan
from bls_mcp.mcp.prompts import register_prompts
from bls_mcp.mcp.resources import register_resources
from bls_mcp.mcp.tools import register_tools
from bls_mcp.routes import register_routes


def create_server(
    settings: Settings | None = None,
    *,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> FastMCP:
    """Assemble a server; open dependencies only at startup."""
    settings = settings if settings is not None else get_settings()
    holder = ServiceHolder()
    mcp = FastMCP(
        "BLS Cost Escalation",
        instructions=(
            "For a project-to-index task, read guide://escalation-workflow "
            "or use the design_escalation_basket prompt. Before live BLS "
            "retrieval, call get_bls_access_status. If setup "
            "is required, read setup://bls-api and guide the user through "
            "registration and local configuration. Never request keys in "
            "chat or tool arguments. Ask the user to confirm configuration, "
            "restart/reconnect, and recheck status. Configured keys are "
            "unverified, not authenticated. Catalog exploration and "
            "supplied-value calculations can continue during setup. "
            "Retrieval supports at most 50 series and 20 inclusive calendar "
            "years per call; automatic batching and quota tracking are "
            "not implemented. Do not claim missing data is zero. Before "
            "choosing a series for a component, call get_series_hierarchy: "
            "seeing the narrower sub-items nested beneath a parent code is the "
            "primary way to verify what an index includes. Pick the level "
            "whose sub-items match the component, and tell the user what a "
            "chosen parent series includes. To chart a "
            "saved specification's annual history, call "
            "get_index_visualization; when the server runs over HTTP the same "
            "result is browsable at /ui."
        ),
        lifespan=create_lifespan(settings, http_transport, holder),
        mask_error_details=True,
    )
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)
    register_routes(mcp, holder)
    return mcp


if __name__ == "__main__":
    create_server().run(show_banner=False)
