"""Live PARS session: the stdio bridge, its failures, and the fixed messages."""

import asyncio
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from cost_intel_app import pars_live
from cost_intel_app import pars_panels as pp
from cost_intel_app.pars_workspace import workspace_state

PARS_REPO = os.environ.get("PARS_REPO", "").strip()


class FakeClient:
    """Stands in for a fastmcp Client: records calls, answers from a table.

    ``hang_open`` and ``hang_call`` make the start or a call wait forever, so the
    timeout paths run. ``cancelled`` records that the pending work was cancelled.
    """

    def __init__(
        self,
        answers=None,
        open_error=None,
        close_error=None,
        hang_open=False,
        hang_call=False,
    ):
        self.answers = answers or {}
        self.open_error = open_error
        self.close_error = close_error
        self.hang_open = hang_open
        self.hang_call = hang_call
        self.calls = []
        self.closed = False
        self.cancelled = False

    async def _wait_forever(self):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def __aenter__(self):
        if self.open_error is not None:
            raise self.open_error
        if self.hang_open:
            await self._wait_forever()
        return self

    async def __aexit__(self, *exc):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if self.hang_call:
            await self._wait_forever()
        return SimpleNamespace(structured_content=self.answers[name], content=[])


def test_structured_content_is_the_tool_result():
    fake = FakeClient({"list_projects": {"projects": []}})
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        assert session.call("list_projects", {}) == {"projects": []}
    assert fake.calls == [("list_projects", {})]
    assert fake.closed


def test_text_content_is_decoded_when_there_is_no_structured_content():
    result = SimpleNamespace(
        structured_content=None,
        content=[SimpleNamespace(text=json.dumps({"ok": True}))],
    )
    assert pars_live.decode(result) == {"ok": True}


def test_text_that_is_not_an_object_is_refused():
    result = SimpleNamespace(
        structured_content=None, content=[SimpleNamespace(text="[1, 2]")]
    )
    with pytest.raises(ValueError):
        pars_live.decode(result)


def test_a_server_that_will_not_start_is_reported_on_call():
    fake = FakeClient(open_error=RuntimeError("uv not found"))
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        with pytest.raises(ConnectionError):
            session.call("list_projects", {})
    assert fake.calls == []


def test_an_unset_repo_is_not_connected():
    with pars_live.live_session(None) as session:
        with pytest.raises(ConnectionError):
            session.call("list_projects", {})


def test_an_unset_repo_gives_the_fixed_failure_messages_in_the_workspace():
    with pars_live.live_session(None) as session:
        header = workspace_state(pp.LoggedClient(session), "proj_001")["header"]
    assert header["state"] == "error"
    assert header["message"] == pp.FAILED_PROJECT


def test_project_context_uses_local_pars_fallback_when_env_is_unset(monkeypatch):
    from cost_intel_app.server import load_pars_context

    monkeypatch.delenv("PARS_REPO", raising=False)
    assert load_pars_context("proj_001")["state"] == "loaded"


@pytest.mark.skipif(not PARS_REPO, reason="set PARS_REPO to a PARS checkout")
def test_live_pars_server_lists_projects():
    with pars_live.live_session(PARS_REPO) as session:
        projects = session.call("list_projects", {})["projects"]
    assert projects and all("parsid" in p for p in projects)


def test_the_server_process_stops_when_the_session_closes():
    client = pars_live._stdio_client("unused", "unused.duckdb")
    assert client.transport.keep_alive is False


def test_the_child_gets_only_the_settings_it_needs(monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "not-for-pars")
    monkeypatch.setenv("DATABASE_PATH", "/elsewhere.duckdb")
    monkeypatch.setenv("PYTHONPATH", "src")
    client = pars_live._stdio_client("unused", "/tmp/pars-ui/pars.duckdb")
    env = client.transport.env
    assert env["DATABASE_PATH"] == "/tmp/pars-ui/pars.duckdb"
    assert "SECRET_TOKEN" not in env
    assert "PYTHONPATH" not in env
    assert "PATH" in env


def test_each_session_gets_its_own_database_outside_the_repo(tmp_path):
    repo = str(tmp_path / "pars_checkout")
    seen = []

    def factory(db):
        seen.append(Path(db))
        return FakeClient({"list_projects": {"projects": []}})

    for _ in range(2):
        with pars_live.live_session(repo, client_factory=factory) as session:
            session.call("list_projects", {})
    first, second = seen
    assert first != second
    for db in (first, second):
        assert Path(repo) not in db.parents
        assert not db.parent.exists(), "the session's work directory is removed"


def test_an_open_that_times_out_is_cancelled(monkeypatch):
    monkeypatch.setattr(pars_live, "OPEN_TIMEOUT_SECONDS", 0.2)
    fake = FakeClient(hang_open=True)
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        with pytest.raises(ConnectionError):
            session.call("list_projects", {})
    assert fake.cancelled is True


def test_a_call_that_times_out_is_cancelled_and_the_session_stops(monkeypatch):
    monkeypatch.setattr(pars_live, "CALL_TIMEOUT_SECONDS", 0.2)
    fake = FakeClient({"list_projects": {}}, hang_call=True)
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        with pytest.raises(ConnectionError):
            session.call("list_projects", {})
        with pytest.raises(ConnectionError):
            session.call("list_projects", {})
    assert len(fake.calls) == 1, "a stopped session does not send another call"
    assert fake.cancelled is True


def test_a_failed_close_is_logged_and_not_raised(caplog):
    fake = FakeClient({"list_projects": {}}, close_error=RuntimeError("secret detail"))
    with caplog.at_level(logging.WARNING, logger="cost_intel_app.pars_live"):
        with pars_live.live_session("unused", client_factory=lambda _db: fake):
            pass
    assert "did not close cleanly" in caplog.text
    assert "secret detail" not in caplog.text


def test_the_server_starts_without_syncing_the_checkout():
    import sys

    assert pars_live.PARS_COMMAND == (sys.executable, "-m", "src.pars_local_mcp.server")


def test_missing_python_executable_has_safe_startup_message():
    fake = FakeClient(open_error=FileNotFoundError("private local filename"))
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        assert session.problem == pars_live.START_MISSING
        with pytest.raises(ConnectionError, match="Python executable was not found"):
            session.call("list_projects", {})
        assert "private local filename" not in session.problem


def test_unknown_startup_failure_is_redacted():
    fake = FakeClient(open_error=RuntimeError("secret token and local path"))
    with pars_live.live_session("unused", client_factory=lambda _db: fake) as session:
        assert session.problem == pars_live.NOT_STARTED
        assert "secret" not in session.problem
