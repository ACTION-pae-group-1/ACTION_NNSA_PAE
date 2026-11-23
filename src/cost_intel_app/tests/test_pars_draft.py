"""The write-back draft: local lines only. Nothing is sent to PARS.

The draft is a backend tool (``pars_draft``) that the basket does not bind, so
these tests call the tool function directly. Its declared input limits are
checked against the signature, because a direct call skips request validation.
"""

import contextlib
import typing

import pytest
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from cost_intel_app import pars_panels as pp
from cost_intel_app import server as server_module
from cost_intel_app.server import MAX_DRAFT_LINES, DraftLine, pars_draft
from cost_intel_app.tests.fake_pars import FakeParsMock


@pytest.fixture(autouse=True)
def synthetic_fake(monkeypatch):
    @contextlib.contextmanager
    def session():
        yield FakeParsMock()

    monkeypatch.setattr(server_module, "_pars_session", session)


def _lines(rows):
    return [DraftLine(**row) for row in rows]


def test_adding_a_line_builds_a_draft_without_contacting_pars(monkeypatch):
    opened = []

    @contextlib.contextmanager
    def refusing_session():
        opened.append(True)
        yield FakeParsMock()

    monkeypatch.setattr(server_module, "_pars_session", refusing_session)
    state = pars_draft(lines=[], wbs_code="1.1", title="Foundations")
    assert state["state"] == "draft"
    assert state["rows"] == [{"wbs_code": "1.1", "title": "Foundations"}]
    assert state["note"] == pp.WRITE_BACK_NOTE
    assert opened == []


def test_a_blank_code_adds_nothing():
    lines = [{"wbs_code": "1.1", "title": "Foundations"}]
    state = pars_draft(lines=_lines(lines), wbs_code="   ", title="Ignored")
    assert state["rows"] == lines


def test_the_draft_is_capped_at_fifty_lines():
    lines = [{"wbs_code": f"1.{i}", "title": ""} for i in range(MAX_DRAFT_LINES)]
    with pytest.raises(ToolError, match="50 lines"):
        pars_draft(lines=_lines(lines), wbs_code="2.1", title="Too many")


def test_clearing_the_draft_empties_it():
    state = pars_draft(lines=[], wbs_code="", title="")
    assert state["state"] == "empty"
    assert state["rows"] == []


def test_the_schema_caps_incoming_lines_at_fifty():
    hints = typing.get_type_hints(pars_draft, include_extras=True)
    # Field(max_length=...) keeps the limit in FieldInfo.metadata as MaxLen.
    limits = [
        getattr(constraint, "max_length", None)
        for info in hints["lines"].__metadata__
        for constraint in getattr(info, "metadata", [])
    ]
    assert MAX_DRAFT_LINES in limits


def test_an_incoming_line_must_have_a_real_code():
    with pytest.raises(ValidationError):
        DraftLine(wbs_code="   ", title="")


def test_an_overlong_code_is_refused_with_a_message():
    with pytest.raises(ToolError, match="64 characters"):
        pars_draft(lines=[], wbs_code="x" * 65, title="")


def test_the_basket_never_offers_write_back():
    import asyncio
    import json

    from fastmcp import Client

    from cost_intel_app.server import mcp

    async def open_basket():
        async with Client(mcp) as client:
            result = await client.call_tool("ppi_basket", {})
            return result.structured_content

    dump = json.dumps(asyncio.run(open_basket())["view"])
    assert "write_back_wbs" not in dump
    assert "pars_draft" not in dump


def test_the_workspace_starts_with_an_empty_draft():
    from cost_intel_app.pars_workspace import workspace_state

    state = workspace_state(pp.LoggedClient(FakeParsMock()), "100")
    assert state["draft"]["state"] == "empty"
    assert state["draft"]["note"] == pp.WRITE_BACK_NOTE
    assert {"draft_code", "draft_title"} <= set(state["inputs"])
