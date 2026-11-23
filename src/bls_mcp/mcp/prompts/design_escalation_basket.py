from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.prompt()
    def design_escalation_basket(
        project_description: str,
        base_period: str = "",
        target_period: str = "",
        locality: str = "",
        archetype_id: str = "",
    ) -> str:
        """Clarify scope, periods, shares and evidence; propose a reviewable
        component table.
        """
        supplied = {
            "Base period": base_period,
            "Target period": target_period,
            "Locality": locality,
            "Archetype": archetype_id,
        }
        lines = [
            "Design a cost escalation basket for this project.",
            "",
            f"Project: {project_description.strip()}",
        ]
        lines += [f"{k}: {v.strip()}" for k, v in supplied.items() if v.strip()]
        lines += [
            "",
            "Read guide://escalation-workflow first and follow it.",
            "1. Ask only for missing scope, periods, cost shares and weight sources.",
            "2. For each component, compare a small candidate set from "
            "search_series and describe_series. Before choosing a series, "
            "call get_series_hierarchy to verify what it includes from its "
            "sub-items; pick the level that matches the component and say "
            "what a parent series includes. If its status is not complete, "
            "say which relationships could not be identified.",
            "3. Allow an explicit no-match. Disclose any proxy and get user approval.",
            "4. Present a draft component table: series ID and title, what "
            "it includes, share, weight source, exclusions, open questions. "
            "Separate user inputs from illustrative assumptions.",
            "5. Once inputs are sufficient, use create_index_spec and "
            "validate_index_spec. Do not save automatically.",
            "A city alone does not authorize a locality factor. Never invent "
            "observations.",
        ]
        return "\n".join(lines)
