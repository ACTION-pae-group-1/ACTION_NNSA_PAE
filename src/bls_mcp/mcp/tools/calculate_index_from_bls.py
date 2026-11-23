from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.calculations import EscalationCalculationResult
from bls_mcp.models.provenance import CalculationLedger


class SourceBackedCalculationResponse(BaseModel):
    """Combined result from calculate_index_from_bls."""

    result: EscalationCalculationResult
    ledger: CalculationLedger


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def calculate_index_from_bls(
        spec_id: str,
        ctx: Context,
    ) -> SourceBackedCalculationResponse:
        """Calculate a saved index spec sourced from the BLS snapshot.

        Loads the saved specification by *spec_id*, resolves the base and target
        observations for every component from the DuckDB snapshot, and computes
        the composite escalation factor.  Returns both the calculation result and
        a ledger recording which series IDs, periods, and raw values were used —
        no caller-supplied floats, no hallucinated index values.

        Quarterly programs (such as the Employment Cost Index) publish no annual
        average. When a component's series has no annual-average row for a
        requested spec year, the calculation resolves it from that series'
        fourth-quarter observation (year-end quarter) and discloses the
        substitution: the component's result periods become the actual quarters
        used, and the ledger warnings state the alignment per series. Quote the
        quarter to the user (for example "2014-Q04"); do not imply an annual
        average the program never published. Monthly spec periods against a
        quarterly-only series behave the same way: the value comes from the
        published quarter containing the requested month, with the same
        disclosure (for example "2024-Q02" for a 2024-M05 request).

        Raises ToolError when:
        - spec_id is not found
        - the spec has ERROR-level validation findings
        - a component series is absent from the snapshot
        - a required observation is absent from the snapshot
        - a base observation value is zero
        """
        with domain_errors():
            services = get_services(ctx)
            spec = services.specifications.get(spec_id)
            if spec is None:
                raise ToolError(f"Specification '{spec_id}' not found.")
            composite, ledger = services.source_calculations.calculate(spec)
            return SourceBackedCalculationResponse(result=composite, ledger=ledger)
