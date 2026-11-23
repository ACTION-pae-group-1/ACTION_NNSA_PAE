"""HTTP routes served alongside /mcp.

``/health`` and ``/version`` are dependency-free probes; they do not check BLS
or database health. ``/ui`` serves the bundled results explorer, and the
``/api`` routes give that page the same validated index visualization the
``get_index_visualization`` tool returns. The API is read-only: it never
writes a specification and never contacts BLS.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from bls_mcp import __version__
from bls_mcp.exceptions import BLSEscalationError
from bls_mcp.lifespan import ServiceHolder, Services
from bls_mcp.models.visualization import IndexVisualizationPacket

#: The page is one self-contained file; nothing may load from another origin.
UI_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)
MAX_BODY_BYTES = 64 * 1024


class BodyTooLargeError(ValueError):
    """The request body exceeded MAX_BODY_BYTES while streaming it in."""


class VisualizationRequest(BaseModel):
    """Query or JSON body of the index visualization endpoint."""

    model_config = ConfigDict(extra="forbid")

    spec_id: str
    start_year: int | None = None
    end_year: int | None = None
    source_year: int | None = None
    weights: dict[str, float | str] | None = None


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status)


def register_routes(mcp: FastMCP, holder: ServiceHolder | None = None) -> None:
    """Register infrastructure and UI routes alongside /mcp."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy", "service": "bls-escalation-mcp"})

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request: Request) -> JSONResponse:
        return JSONResponse({"version": __version__})

    if holder is None:
        return

    def services() -> Services | None:
        return holder.services

    @mcp.custom_route("/ui", methods=["GET"])
    async def ui(request: Request) -> Response:
        page = resources.files("bls_mcp.web").joinpath("index.html")
        return HTMLResponse(
            page.read_text(encoding="utf-8"),
            headers={
                "Content-Security-Policy": UI_CONTENT_SECURITY_POLICY,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-cache",
            },
        )

    @mcp.custom_route("/api/specs", methods=["GET"])
    async def list_specs(request: Request) -> JSONResponse:
        active = services()
        if active is None:
            return _error(503, "not_ready", "The server is still starting.")
        specs = await run_in_threadpool(active.specifications.list)
        return JSONResponse(
            {
                "specs": [
                    {
                        "id": spec.id,
                        "name": spec.name,
                        "description": spec.description,
                        "project_description": spec.project_description,
                        "revision": spec.revision,
                        "base_year": spec.base_period.year,
                        "target_year": spec.target_period.year,
                        "component_count": len(spec.components),
                        "components": [
                            {
                                "id": component.id,
                                "name": component.name,
                                "component_type": component.component_type.value,
                                "series_id": component.series_id,
                                "weight": component.weight,
                            }
                            for component in spec.components
                        ],
                        "updated_at": spec.updated_at.isoformat(),
                    }
                    for spec in specs
                ]
            }
        )

    @mcp.custom_route("/api/index-visualization", methods=["GET", "POST"])
    async def index_visualization(request: Request) -> JSONResponse:
        active = services()
        if active is None:
            return _error(503, "not_ready", "The server is still starting.")
        try:
            params = await _visualization_request(request)
        except ValidationError as exc:
            return _error(400, "invalid_request", _first_message(exc))
        except BodyTooLargeError as exc:
            return _error(413, "request_too_large", str(exc))
        except ValueError as exc:
            return _error(400, "invalid_request", _first_message(exc))

        def build() -> IndexVisualizationPacket | None:
            spec = active.specifications.get(params.spec_id)
            if spec is None:
                return None
            return active.visualization.build(
                spec,
                start_year=params.start_year,
                end_year=params.end_year,
                source_year=params.source_year,
                weights=params.weights,
            )

        try:
            packet = await run_in_threadpool(build)
        except BLSEscalationError as exc:
            return _error(422, type(exc).__name__, str(exc))
        if packet is None:
            return _error(
                404, "spec_not_found", f"Specification '{params.spec_id}' not found."
            )
        return JSONResponse(
            packet.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )


async def _visualization_request(request: Request) -> VisualizationRequest:
    if request.method == "GET":
        return VisualizationRequest.model_validate(dict(request.query_params))
    # Read the body as a stream and stop as soon as the limit is exceeded, so
    # MAX_BODY_BYTES bounds this endpoint's memory even for a large upload.
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            raise BodyTooLargeError("Request body is too large.")
    payload: Any = json.loads(body or b"{}")
    return VisualizationRequest.model_validate(payload)


def _first_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        error = exc.errors()[0]
        location = ".".join(str(part) for part in error["loc"])
        return f"{location}: {error['msg']}" if location else str(error["msg"])
    return str(exc) or "Request could not be read."
