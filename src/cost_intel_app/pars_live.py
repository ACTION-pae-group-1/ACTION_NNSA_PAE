"""Live connection to the PARS MCP server, for the PARS workspace.

The server runs over stdio from the PARS checkout named by the PARS_REPO
environment variable, with the fixed command PARS_COMMAND, which includes
--no-sync, so starting the server never syncs the checkout's environment.
Each workspace render or panel request opens one session and closes it after.
Failures raise exceptions; the panel builders turn them into fixed messages, so
exception text never reaches the view.

Three rules keep the PARS checkout untouched:

- Each session gets its own temporary database through DATABASE_PATH, so PARS
  startup never rebuilds a database in the checkout and two renders never share
  a DuckDB file. The checkout's synthetic source database is opened read-only,
  by the evidence check and the read-only data views.
- The PARS process receives only the environment it needs, not the app's.
- A call or start that times out is cancelled, and the session stops answering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# --no-sync: starting the server must not change the PARS checkout's environment.
PARS_COMMAND = (sys.executable, "-m", "src.pars_local_mcp.server")
OPEN_TIMEOUT_SECONDS = 120.0
CALL_TIMEOUT_SECONDS = 60.0
CLOSE_TIMEOUT_SECONDS = 30.0
NOT_SET = "PARS_REPO is not set, so PARS is not connected."
NOT_STARTED = "PARS did not start."
START_MISSING = "PARS startup failed: Python executable was not found."
START_TIMEOUT = "PARS startup timed out."
STOPPED = "PARS stopped answering."
# The only variables the PARS process inherits from the app. PARS also reads
# settings from its own environment and .env file, so nothing else is passed.
CHILD_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "COMSPEC",
    "WINDIR",
    "USERPROFILE",
    "USERNAME",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMDATA",
    "TEMP",
    "TMP",
)


def decode(result: Any) -> dict[str, Any]:
    """A tool result as a dict: its structured content, else its JSON text."""
    data = getattr(result, "structured_content", None)
    if data is None:
        texts = [c.text for c in getattr(result, "content", []) if hasattr(c, "text")]
        data = json.loads(texts[0]) if texts else None
    if not isinstance(data, dict):
        raise ValueError("PARS returned something other than an object")
    return data


def _submit(loop: asyncio.AbstractEventLoop, awaitable: Any) -> Future:
    return asyncio.run_coroutine_threadsafe(awaitable, loop)


class LiveParsSession:
    """Synchronous ParsCall over one open MCP client on a background event loop."""

    def __init__(
        self,
        client: Any,
        loop: asyncio.AbstractEventLoop | None,
        problem: str,
    ) -> None:
        self._client = client
        self._loop = loop
        self._problem = problem
        self._stopped = False

    @classmethod
    def unavailable(cls, problem: str) -> LiveParsSession:
        return cls(None, None, problem)

    def _run(self, make_awaitable: Callable[[], Any]) -> Any:
        if self._client is None:
            raise ConnectionError(self._problem)
        if self._stopped:
            raise ConnectionError(STOPPED)
        future = _submit(self._loop, make_awaitable())
        try:
            return future.result(CALL_TIMEOUT_SECONDS)
        except TimeoutError:
            future.cancel()
            self._stopped = True
            raise ConnectionError(STOPPED) from None

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return decode(self._run(lambda: self._client.call_tool(tool, arguments)))

    @property
    def problem(self) -> str:
        """Safe, fixed startup category for UI diagnostics."""
        return self._problem

    def tool_names(self) -> set[str]:
        return {tool.name for tool in self._run(lambda: self._client.list_tools())}


def _child_env(database_path: str) -> dict[str, str]:
    env = {key: os.environ[key] for key in CHILD_ENV_KEYS if key in os.environ}
    env["DATABASE_PATH"] = database_path
    return env


# When COST_INTEL_PARS_STADIUM_DB names a prepopulated database, the app starts the
# non-destructive launcher on it instead of the default server. The launcher never
# calls initialize_database(), so the named database is not regenerated.
STADIUM_DB_ENV = "COST_INTEL_PARS_STADIUM_DB"
STADIUM_COMMAND = (sys.executable, "-m", "src.cost_intel_app.pars_launcher")


def _stdio_client(repo: str, database_path: str) -> Any:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    stadium = os.environ.get(STADIUM_DB_ENV, "").strip()
    command = STADIUM_COMMAND if stadium else PARS_COMMAND
    env = _child_env(database_path)
    if stadium:
        env["PARS_STADIUM_DB"] = stadium
    transport = StdioTransport(
        command=command[0],
        args=list(command[1:]),
        cwd=repo,
        env=env,
        keep_alive=False,
    )
    return Client(transport)


async def _cancel_pending() -> None:
    current = asyncio.current_task()
    pending = [task for task in asyncio.all_tasks() if task is not current]
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


def _close(
    client: Any,
    loop: asyncio.AbstractEventLoop,
    thread: threading.Thread,
    workdir: Path,
) -> None:
    try:
        if client is not None:
            _submit(loop, client.__aexit__(None, None, None)).result(
                CLOSE_TIMEOUT_SECONDS
            )
    except Exception as exc:
        logger.warning("PARS session did not close cleanly: %s", type(exc).__name__)
    finally:
        try:
            # Cancels a start that timed out, and any call still in flight.
            _submit(loop, _cancel_pending()).result(CLOSE_TIMEOUT_SECONDS)
        except Exception as exc:
            logger.warning("PARS session left work behind: %s", type(exc).__name__)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(CLOSE_TIMEOUT_SECONDS)
        if not thread.is_alive():
            loop.close()
        shutil.rmtree(workdir, ignore_errors=True)


@contextmanager
def live_session(
    repo: str | None,
    client_factory: Callable[[str], Any] | None = None,
) -> Iterator[LiveParsSession]:
    """Open the PARS server from ``repo`` for the duration of the block.

    ``client_factory`` receives the session's database path and returns a client;
    tests use it to replace the stdio server. Without a repo, or when the server
    does not start, the session is unavailable and calls raise ConnectionError.
    """
    if not repo or not repo.strip():
        yield LiveParsSession.unavailable(NOT_SET)
        return
    workdir = Path(tempfile.mkdtemp(prefix="pars-ui-"))
    database_path = str(workdir / "pars.duckdb")
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, name="pars-live", daemon=True)
    thread.start()
    client = None
    try:
        make = client_factory or (lambda db: _stdio_client(repo.strip(), db))
        candidate = make(database_path)
        _submit(loop, candidate.__aenter__()).result(OPEN_TIMEOUT_SECONDS)
        client = candidate
        session = LiveParsSession(client, loop, NOT_STARTED)
    except FileNotFoundError:
        session = LiveParsSession.unavailable(START_MISSING)
    except TimeoutError:
        session = LiveParsSession.unavailable(START_TIMEOUT)
    except Exception:
        session = LiveParsSession.unavailable(NOT_STARTED)
    try:
        yield session
    finally:
        _close(client, loop, thread, workdir)
