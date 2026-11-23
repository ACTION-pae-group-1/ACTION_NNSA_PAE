from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.enums import ObservationPolicy
from bls_mcp.models.periods import EconomicPeriod


class EscalationIndexSpec(BaseModel):
    id: str
    schema_version: str = "1.0"
    #: Number of times this id has been saved; 0 means never persisted.
    revision: int = 0
    name: str
    description: str | None = None
    project_description: str | None = None
    base_period: EconomicPeriod
    target_period: EconomicPeriod
    reference_locality: str | None = None
    target_locality: str | None = None
    components: list[EscalationComponent] = Field(default_factory=list)
    observation_policy: ObservationPolicy = ObservationPolicy.EXACT
    assumptions: dict[str, str] = Field(default_factory=dict)
    methodology_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
