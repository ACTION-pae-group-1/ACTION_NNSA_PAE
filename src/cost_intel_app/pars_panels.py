"""PARS MCP panel state builders for the cost-intelligence UI.

Contract: docs/PARS_UI_WIRING_SPEC.md. Each builder returns a plain dict with a
``state`` of "loaded", "empty", or "error" so the view binds one shape. Error
text is a fixed UI message; exception text never reaches the view. Validation
problems and the data-origin label are shown as PARS reports them. Builders
take only a GuardedClient, so only READ_ONLY_TOOLS can be called. Starting the
PARS server is not done here.
"""

from __future__ import annotations

from typing import Any, Protocol

READ_ONLY_TOOLS = frozenset(
    {
        "list_projects",
        "get_project_info",
        "get_wbs_hierarchy",
        "get_leaf_nodes",
        "get_wbs_by_level",
        "search_wbs",
        "get_wbs_lineage",
        "validate_wbs_inputs",
        "get_wbs_run_status",
        "get_wbs_project_descriptions",
        "get_wbs_rows",
    }
)

# Origins the UI may show as "synthetic" and use for read-only views. Other
# origins (for example labeled_test_fixture) hide those views.
SYNTHETIC_ORIGINS = frozenset({"synthetic_mock"})

FAILED_PROJECT = "PARS could not load this project."
FAILED_LINEAGE = "PARS could not load this element's lineage."
FAILED_EVIDENCE = "PARS could not check this data source."
CHOOSE_PROJECT = "Choose a project."
CHOOSE_ELEMENT = "Choose an element."
CHOOSE_SEARCH = "Choose a search term."


class ToolNotAllowed(PermissionError):
    """Raised when a caller asks for a tool outside the read-only allowlist."""


class ParsCall(Protocol):
    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class GuardedClient:
    """Refuses any tool outside READ_ONLY_TOOLS before it reaches PARS."""

    def __init__(self, inner: ParsCall) -> None:
        self._inner = inner

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool not in READ_ONLY_TOOLS:
            raise ToolNotAllowed(f"{tool} is not on the read-only allowlist")
        return self._inner.call(tool, arguments)


def _require_guard(client: object) -> GuardedClient:
    if not isinstance(client, GuardedClient):
        raise TypeError("PARS panels must be given a GuardedClient")
    return client


def _ask(
    client: GuardedClient, tool: str, arguments: dict[str, Any], failure: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Call one read tool. Returns (response, None) or (None, fixed failure)."""
    try:
        response = client.call(tool, arguments)
    except ToolNotAllowed:
        raise  # a refused tool is a programming error; it must not be hidden
    except Exception:  # transport or protocol failure: never show its text
        return None, failure
    if not isinstance(response, dict) or "error" in response:
        return None, failure
    return response, None


def _error(message: str, **fields: Any) -> dict[str, Any]:
    return {"state": "error", "message": message, **fields}


def project_header(client: GuardedClient, project_id: str) -> dict[str, Any]:
    guard = _require_guard(client)
    pid = project_id.strip()
    blank = {"name": "", "summary": "", "total_elements": 0, "hierarchy_depth": 0}
    if not pid:
        return _error(CHOOSE_PROJECT, **blank)
    response, failure = _ask(
        guard, "get_project_info", {"project_id": pid}, FAILED_PROJECT
    )
    if failure is not None or response is None:
        return _error(failure or FAILED_PROJECT, **blank)
    try:
        total = response["total_elements"]
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise TypeError("total_elements must be a non-negative int")
        depth = response["hierarchy_depth"]
        return {
            "state": "loaded" if total else "empty",
            "message": "",
            "project_id": response.get("parsid", pid),
            "name": response["project_name"],
            "summary": f"{total} elements, {depth} levels deep",
            "total_elements": total,
            "hierarchy_depth": depth,
        }
    except (KeyError, TypeError):
        return _error(FAILED_PROJECT, **blank)


def lineage(client: GuardedClient, project_id: str, wbs_code: str) -> dict[str, Any]:
    guard = _require_guard(client)
    pid, code = project_id.strip(), wbs_code.strip()
    if not pid:
        return _error(CHOOSE_PROJECT, rows=[])
    if not code:
        return _error(CHOOSE_ELEMENT, rows=[])
    response, failure = _ask(
        guard,
        "get_wbs_lineage",
        {"project_id": pid, "wbs_code": code},
        FAILED_LINEAGE,
    )
    if failure is not None or response is None:
        return _error(failure or FAILED_LINEAGE, rows=[])
    try:
        rows = [
            {"wbs_code": r["wbs_code"], "title": r["title"], "level": r["level"]}
            for r in response["lineage"]
        ]
    except (KeyError, TypeError):
        return _error(FAILED_LINEAGE, rows=[])
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


def evidence(client: GuardedClient) -> dict[str, Any]:
    guard = _require_guard(client)
    hidden = {
        "label": "",
        "origin": "",
        "read_only_views": False,
        "ok": False,
        "detail": "",
    }
    response, failure = _ask(guard, "validate_wbs_inputs", {}, FAILED_EVIDENCE)
    if failure is not None or response is None:
        return _error(failure or FAILED_EVIDENCE, problems=[], **hidden)
    try:
        origin = response["data_origin"]
        ok = bool(response["ok"])
        problems = list(response["problems"])
        tables = list(response["tables"])
        is_synthetic = origin in SYNTHETIC_ORIGINS
    except (KeyError, TypeError):
        return _error(FAILED_EVIDENCE, problems=[], **hidden)
    return {
        "state": "empty" if (not tables and ok) else "loaded",
        "message": "",
        "ok": ok,
        "problems": problems,
        "origin": origin,
        "label": "synthetic" if is_synthetic else origin,
        "read_only_views": is_synthetic,
        "detail": "" if (ok or problems) else "No details were returned.",
    }


FAILED_HIERARCHY = "PARS could not load this part of the WBS."
FAILED_SEARCH = "PARS could not run this search."
SEARCH_CODES_ONLY = "Search with WBS codes. The characters % and _ are not allowed."


def _element(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "wbs_code": raw["wbs_code"],
        "title": raw["title"],
        "level": raw["level"],
        "leaf_node": raw["leaf_node"],
    }


def hierarchy(client: GuardedClient, project_id: str, wbs_code: str) -> dict[str, Any]:
    """One element and its direct children, as PARS returns them (depth 1)."""
    guard = _require_guard(client)
    pid, code = project_id.strip(), wbs_code.strip()
    blank: dict[str, Any] = {"element": None, "children": []}
    if not pid:
        return _error(CHOOSE_PROJECT, **blank)
    if not code:
        return _error(CHOOSE_ELEMENT, **blank)
    response, failure = _ask(
        guard,
        "get_wbs_hierarchy",
        {"project_id": pid, "wbs_code": code},
        FAILED_HIERARCHY,
    )
    if failure is not None or response is None:
        return _error(failure or FAILED_HIERARCHY, **blank)
    try:
        element = _element(response["element"])
        children = [_element(c["element"]) for c in response["children"]]
    except (KeyError, TypeError):
        return _error(FAILED_HIERARCHY, **blank)
    state = "loaded" if children else "empty"
    return {"state": state, "message": "", "element": element, "children": children}


def _same_branch(code: str, text: str) -> bool:
    """True for the code itself or a descendant, so 1.1 does not match 1.10."""
    return code == text or code.startswith(text + ".")


def search(
    client: GuardedClient,
    project_id: str,
    pattern: str = "",
    min_level: int | None = None,
    max_level: int | None = None,
) -> dict[str, Any]:
    """Elements whose WBS code matches, as PARS does. PARS does not match titles.

    Only the filters that were given are sent.
    """
    guard = _require_guard(client)
    pid = project_id.strip()
    if not pid:
        return _error(CHOOSE_PROJECT, rows=[])
    arguments: dict[str, Any] = {"project_id": pid}
    text = pattern.strip()
    if "%" in text or "_" in text:
        return _error(SEARCH_CODES_ONLY, rows=[])
    if text:
        # PARS runs wbs_code LIKE ?; a trailing % makes this a code-prefix search.
        arguments["wbs_pattern"] = text + "%"
    if min_level is not None:
        arguments["min_level"] = min_level
    if max_level is not None:
        arguments["max_level"] = max_level
    response, failure = _ask(guard, "search_wbs", arguments, FAILED_SEARCH)
    if failure is not None or response is None:
        return _error(failure or FAILED_SEARCH, rows=[])
    try:
        rows = [
            {
                "wbs_code": r["wbs_code"],
                "title": r["title"],
                "level": r["level"],
                "parent_wbs": r["parent_wbs"],
                "leaf_node": r["leaf_node"],
            }
            for r in response["elements"]
        ]
    except (KeyError, TypeError):
        return _error(FAILED_SEARCH, rows=[])
    if text:
        rows = [r for r in rows if _same_branch(r["wbs_code"], text)]
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


FAILED_PROJECTS = "PARS could not list projects."
FAILED_RUN = "PARS could not load this run."
FAILED_DATA = "PARS could not load these rows."
CHOOSE_RUN = "Choose a run."
CHOOSE_LEVEL = "Choose a level from 1 to 8."
MAX_ROWS = 500
_READ_SOURCES = {
    "descriptions": "get_wbs_project_descriptions",
    "rows": "get_wbs_rows",
}


def project_list(client: GuardedClient) -> dict[str, Any]:
    """Every PARS project, for the project picker."""
    guard = _require_guard(client)
    response, failure = _ask(guard, "list_projects", {}, FAILED_PROJECTS)
    if failure is not None or response is None:
        return _error(failure or FAILED_PROJECTS, rows=[])
    try:
        rows = [
            {
                "parsid": p["parsid"],
                "project_name": p["project_name"],
                "total_elements": p["total_elements"],
                "hierarchy_depth": p["hierarchy_depth"],
            }
            for p in response["projects"]
        ]
    except (KeyError, TypeError):
        return _error(FAILED_PROJECTS, rows=[])
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


def run_status(client: GuardedClient, run_id: str) -> dict[str, Any]:
    """Stages and data origin of one run, for the classification evidence."""
    guard = _require_guard(client)
    rid = run_id.strip()
    blank: dict[str, Any] = {"run_id": "", "created_at": "", "label": "", "stages": []}
    if not rid:
        return _error(CHOOSE_RUN, **blank)
    response, failure = _ask(guard, "get_wbs_run_status", {"run_id": rid}, FAILED_RUN)
    if failure is not None or response is None:
        return _error(failure or FAILED_RUN, **blank)
    try:
        origin = response["data_origin"]
        label = "synthetic" if origin in SYNTHETIC_ORIGINS else origin
        stages = [
            {"stage": name, "status": info["status"]}
            for name, info in response["stages"].items()
        ]
        created = response["created_at"]
    except (KeyError, TypeError, AttributeError):
        return _error(FAILED_RUN, **blank)
    return {
        "state": "loaded" if stages else "empty",
        "message": "",
        "run_id": rid,
        "created_at": created,
        "label": label,
        "stages": stages,
    }


def read_only_data(
    client: GuardedClient,
    which: str,
    read_only_views: bool,
    limit: int = 20,
) -> dict[str, Any]:
    """Source descriptions or rows. Hidden unless the evidence says synthetic."""
    guard = _require_guard(client)
    if which not in _READ_SOURCES:
        raise ValueError(f"unknown read-only source: {which}")
    if read_only_views is not True:
        return {
            "state": "hidden",
            "message": "",
            "summary": "",
            "columns": [],
            "rows": [],
            "total_rows": 0,
        }
    if isinstance(limit, bool) or not isinstance(limit, int):
        return _error(
            f"Choose between 1 and {MAX_ROWS} rows.",
            summary="",
            columns=[],
            rows=[],
            total_rows=0,
        )
    if not 1 <= limit <= MAX_ROWS:
        return _error(
            f"Choose between 1 and {MAX_ROWS} rows.",
            summary="",
            columns=[],
            rows=[],
            total_rows=0,
        )
    response, failure = _ask(guard, _READ_SOURCES[which], {"limit": limit}, FAILED_DATA)
    if failure is not None or response is None:
        return _error(
            failure or FAILED_DATA, summary="", columns=[], rows=[], total_rows=0
        )
    try:
        columns = list(response["columns"])
        raw_rows = response["rows"]
        if not all(isinstance(r, dict) for r in raw_rows):
            raise TypeError("rows must be mappings")
        rows = [dict(r) for r in raw_rows]
        total = response["total_rows"]
    except (KeyError, TypeError, ValueError):
        return _error(FAILED_DATA, summary="", columns=[], rows=[], total_rows=0)
    return {
        "state": "loaded" if rows else "empty",
        "message": "",
        "summary": f"Showing {len(rows)} of {total} rows from all projects.",
        "columns": columns,
        "rows": rows,
        "total_rows": total,
    }


FAILED_LEAVES = "PARS could not load the leaf elements."
FAILED_LEVEL = "PARS could not load this level."
WRITE_BACK_NOTE = "Draft only. Nothing is written to PARS."


def leaf_nodes(client: GuardedClient, project_id: str) -> dict[str, Any]:
    """Leaf elements of a project, for the hierarchy view."""
    guard = _require_guard(client)
    pid = project_id.strip()
    if not pid:
        return _error(CHOOSE_PROJECT, rows=[])
    response, failure = _ask(
        guard, "get_leaf_nodes", {"project_id": pid}, FAILED_LEAVES
    )
    if failure is not None or response is None:
        return _error(failure or FAILED_LEAVES, rows=[])
    try:
        rows = [
            {"wbs_code": r["wbs_code"], "title": r["title"], "level": r["level"]}
            for r in response["leaf_nodes"]
        ]
    except (KeyError, TypeError):
        return _error(FAILED_LEAVES, rows=[])
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


def by_level(client: GuardedClient, project_id: str, level: int) -> dict[str, Any]:
    """Elements at one reported WBS level (1 to 8). A bad level is a caller error."""
    guard = _require_guard(client)
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 8:
        raise ValueError("level must be an integer from 1 to 8")
    pid = project_id.strip()
    if not pid:
        return _error(CHOOSE_PROJECT, rows=[])
    response, failure = _ask(
        guard,
        "get_wbs_by_level",
        {"project_id": pid, "level": level},
        FAILED_LEVEL,
    )
    if failure is not None or response is None:
        return _error(failure or FAILED_LEVEL, rows=[])
    try:
        rows = [
            {
                "wbs_code": r["wbs_code"],
                "title": r["title"],
                "parent_wbs": r["parent_wbs"],
            }
            for r in response["elements"]
        ]
    except (KeyError, TypeError):
        return _error(FAILED_LEVEL, rows=[])
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


class LoggedClient(GuardedClient):
    """A guarded client that keeps one entry per call: ok, error, or refused."""

    def __init__(self, inner: ParsCall) -> None:
        super().__init__(inner)
        self.entries: list[dict[str, str]] = []

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            response = super().call(tool, arguments)
        except ToolNotAllowed:
            self.entries.append({"tool": tool, "status": "refused"})
            raise
        except Exception:
            self.entries.append({"tool": tool, "status": "error"})
            raise
        failed = not isinstance(response, dict) or "error" in response
        self.entries.append({"tool": tool, "status": "error" if failed else "ok"})
        return response


def chat_log(entries: list[dict[str, str]]) -> dict[str, Any]:
    """The tool calls the assistant made, one row each, in order."""
    rows = [{"tool": e["tool"], "status": e["status"]} for e in entries]
    return {"state": "loaded" if rows else "empty", "message": "", "rows": rows}


def write_back_preview(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """A draft of proposed WBS changes. It is built locally and sent nowhere."""
    rows = [dict(line) for line in lines]
    return {
        "state": "draft" if rows else "empty",
        "message": "",
        "rows": rows,
        "note": WRITE_BACK_NOTE,
    }


def project_roots(client: GuardedClient, project_id: str) -> dict[str, Any]:
    """The top WBS level of a project, for the hierarchy view's first screen."""
    return by_level(client, project_id, 1)
