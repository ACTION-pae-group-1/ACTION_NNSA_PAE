"""Windows stdio startup must initialize native numeric modules first."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bls_mcp import app


def test_windows_preload_imports_native_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []
    monkeypatch.setattr(app.sys, "platform", "win32")
    monkeypatch.setattr(app, "import_module", imported.append)
    app._preload_windows_stdio_numeric_libraries()
    assert imported == ["numpy.core.multiarray", "scipy.sparse.linalg"]


def test_non_windows_preload_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.sys, "platform", "linux")
    monkeypatch.setattr(
        app,
        "import_module",
        lambda _name: pytest.fail("numeric import on non-Windows"),
    )
    app._preload_windows_stdio_numeric_libraries()


def test_stdio_preloads_before_starting_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("DATABRICKS_APP_PORT", raising=False)
    monkeypatch.setattr(
        app,
        "LaunchSettings",
        lambda: SimpleNamespace(mcp_transport="stdio"),
    )
    monkeypatch.setattr(
        app,
        "_preload_windows_stdio_numeric_libraries",
        lambda: events.append("preload"),
    )

    class FakeServer:
        def run(self, *, transport: str) -> None:
            assert transport == "stdio"
            events.append("run")

    def create() -> FakeServer:
        events.append("create")
        return FakeServer()

    monkeypatch.setattr(app, "create_server", create)
    app.main()
    assert events == ["preload", "create", "run"]


def test_http_does_not_preload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("DATABRICKS_APP_PORT", raising=False)
    monkeypatch.setattr(
        app,
        "LaunchSettings",
        lambda: SimpleNamespace(
            mcp_transport="streamable-http",
            mcp_host="127.0.0.1",
            mcp_port=8000,
        ),
    )
    monkeypatch.setattr(
        app,
        "_preload_windows_stdio_numeric_libraries",
        lambda: pytest.fail("preload should only run for stdio"),
    )
    monkeypatch.setattr(
        app,
        "create_server",
        lambda: SimpleNamespace(run=lambda **_kwargs: None),
    )
    app.main()
