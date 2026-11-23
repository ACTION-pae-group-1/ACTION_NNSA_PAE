from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass

import httpx
from fastmcp import FastMCP

from bls_mcp.clients.bls import BLSClient
from bls_mcp.config import Settings
from bls_mcp.ingestion.publish import current_snapshot_path
from bls_mcp.repositories.specifications import (
    SpecificationRepository,
)
from bls_mcp.services.access import BLSAccessService
from bls_mcp.services.calculations import (
    EscalationCalculationService,
)
from bls_mcp.services.locality import LocalityService
from bls_mcp.services.observations import ObservationService
from bls_mcp.services.series_catalog import SeriesCatalogService
from bls_mcp.services.source_calculation import SourceBackedCalculationService
from bls_mcp.services.specifications import SpecificationService
from bls_mcp.services.validation import ValidationService
from bls_mcp.services.visualization import IndexVisualizationService
from bls_mcp.storage.store import BLSStore


@dataclass(frozen=True)
class Services:
    """Dependencies owned by one running server, never a module singleton."""

    access: BLSAccessService
    catalog: SeriesCatalogService
    observations: ObservationService
    specifications: SpecificationService
    calculations: EscalationCalculationService
    source_calculations: SourceBackedCalculationService
    locality: LocalityService
    validation: ValidationService
    visualization: IndexVisualizationService


class ServiceHolder:
    """Lets one server's HTTP routes reach the services its lifespan opened.

    Custom routes receive a Starlette request, not an MCP context, so the
    lifespan publishes its services here for the routes of the same server.
    """

    def __init__(self) -> None:
        self.services: Services | None = None


def create_lifespan(
    settings: Settings,
    http_transport: httpx.AsyncBaseTransport | None = None,
    holder: ServiceHolder | None = None,
) -> Callable[[FastMCP], AbstractAsyncContextManager[dict[str, Services]]]:
    """Initialize once per server run and close HTTP on every exit path."""

    @asynccontextmanager
    async def app_lifespan(
        server: FastMCP,
    ) -> AsyncIterator[dict[str, Services]]:
        snapshot_path = current_snapshot_path(settings.snapshot_registry_dir)
        store = BLSStore(snapshot_path)
        async with httpx.AsyncClient(
            timeout=settings.http_timeout_seconds, transport=http_transport
        ) as http_client:
            access = BLSAccessService(settings.bls_api_key)
            calc_service = EscalationCalculationService(
                weight_tolerance=settings.weight_tolerance
            )
            validation_service = ValidationService(
                settings.weight_tolerance, store=store
            )
            services = Services(
                access=access,
                catalog=SeriesCatalogService(store),
                observations=ObservationService(
                    BLSClient(
                        api_key=settings.bls_api_key,
                        http_client=http_client,
                    ),
                    access,
                    store,
                ),
                specifications=SpecificationService(
                    SpecificationRepository(settings.specs_db_path)
                ),
                calculations=calc_service,
                source_calculations=SourceBackedCalculationService(
                    store=store,
                    calculations=calc_service,
                    validation=validation_service,
                ),
                locality=LocalityService(),
                validation=validation_service,
                visualization=IndexVisualizationService(store, validation_service),
            )
            if holder is not None:
                holder.services = services
            try:
                yield {"services": services}
            finally:
                if holder is not None and holder.services is services:
                    holder.services = None

    return app_lifespan
