"""Shared PARS project identifier validation and lookup."""

from __future__ import annotations

from pathlib import Path

from pars_local_mcp.mcp.errors import PublicError
from pars_local_mcp.storage.queries import PARSStore

BLANK_PROJECT_ID_ERROR = "project_id is required and must not be blank."


def _require_project_id(project_id: str) -> str:
    """Return project_id, or raise PublicError if it is empty or whitespace-only.

    Without a project the store search would match every project's rows.
    """
    if not project_id or not project_id.strip():
        raise PublicError(BLANK_PROJECT_ID_ERROR)
    return project_id


def _resolve_project(db_path: Path, project_id: str) -> str:
    """Return the stored project ID that project_id names, ignoring case.

    An exact match wins. Otherwise exactly one stored ID must match when case is
    ignored. An unknown ID is refused rather than returning an empty result.
    """
    with PARSStore(db_path) as store:
        stored = [p.parsid for p in store.list_projects()]
    if project_id in stored:
        return project_id
    matches = [p for p in stored if p.casefold() == project_id.casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise PublicError(
            f"Project {project_id} is ambiguous; use the exact ID from list_projects"
        )
    raise PublicError(f"Project {project_id} not found")
