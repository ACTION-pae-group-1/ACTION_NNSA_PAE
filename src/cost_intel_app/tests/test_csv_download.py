"""Download tests: the HTTP route, the CSV bytes, and the stale-download guards.

PARS is never started here. Every PARS session is replaced by an unavailable one
before any tool runs, so these tests cannot touch the PARS checkout.
"""

import contextlib
import csv
import io
import json
import re
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastmcp.server.dependencies import get_http_request as real_get_http_request
from starlette.testclient import TestClient

from cost_intel_app import pars_live
from cost_intel_app import server as srv
from cost_intel_ui.formatting import percent_of_fraction

BASE = "http://testserver"
PRESET = "recommended"
EXPECTED_HEADER = [
    "Illustrative project",
    "Scenario",
    "Data source",
    "Period",
    "Component",
    "Weight",
    "Normalized factor",
    "Composite factor",
]


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    @contextlib.contextmanager
    def unavailable(*_args, **_kwargs):
        yield pars_live.LiveParsSession.unavailable(pars_live.NOT_SET)

    monkeypatch.setattr(srv, "_pars_session", unavailable)
    monkeypatch.setattr(
        srv, "get_http_request", lambda: SimpleNamespace(base_url=BASE + "/")
    )
    srv._EXPORTS.clear()
    yield
    srv._EXPORTS.clear()


def _approved():
    pre = srv.choose_preset("y12", PRESET, "review")
    rows = [
        srv.BasketRowInput(enabled=r["enabled"], weight=r["weight"])
        for r in pre["rows"]
    ]
    approved = srv.approve_basket("y12", rows, "review", scenario=pre["scenario"])
    return rows, approved


def _export(rows, scenario=PRESET):
    return srv.export_analysis_csv("y12", rows, "approved", scenario=scenario)


def _fetch(url):
    with TestClient(srv.mcp.http_app()) as http:
        return http.get(url[len(BASE) :])


def test_export_is_served_as_an_attachment_with_the_planned_name():
    rows, _ = _approved()
    exp = _export(rows)
    assert exp["state"] == "ready"
    assert re.fullmatch(r"nnsa_escalation_basket_y12_\d{8}-\d{4}\.csv", exp["filename"])
    response = _fetch(exp["url"])
    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{exp["filename"]}"'
    )
    assert response.headers["content-type"].startswith("text/csv")
    assert "charset=utf-8" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store"


def test_downloaded_file_matches_the_approved_table_row_for_row():
    rows, approved = _approved()
    exp = _export(rows)
    body = _fetch(exp["url"]).content
    assert body.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM for spreadsheet apps"
    text = body.decode("utf-8-sig")
    assert "\n" not in text.replace("\r\n", ""), "CRLF line endings only"
    table_rows = list(csv.reader(io.StringIO(text), strict=True))
    assert table_rows[0] == EXPECTED_HEADER
    ui_rows = approved["results"]["table"]["rows"]
    assert len(table_rows) - 1 == len(ui_rows) == 24
    for csv_row, ui_row in zip(table_rows[1:], ui_rows, strict=True):
        assert csv_row == [
            "y12",
            PRESET,
            "Synthetic demo (PPI fixtures)",
            ui_row["period"],
            ui_row["component_name"],
            ui_row["allocation_weight"],
            ui_row["normalized_factor"],
            ui_row["composite_factor"],
        ]


def test_exported_weights_are_the_approved_preset_weights():
    rows, _ = _approved()
    exp = _export(rows)
    table_rows = list(
        csv.reader(io.StringIO(_fetch(exp["url"]).content.decode("utf-8-sig")))
    )[1:]
    # Preset weights are percent units (45 means 45%); the table shows percents.
    preset = srv._source.scenario_weights("y12")[PRESET]
    assert {row[5] for row in table_rows} == {
        f"{percent_of_fraction(Decimal(w) / 100)}%" for w in preset
    }
    assert sum(Decimal(w) for w in preset) == Decimal(100)


def test_export_requires_an_approved_basket():
    rows, _ = _approved()
    review = srv.export_analysis_csv("y12", rows, "review", scenario=PRESET)
    assert review == {
        "state": "error",
        "message": "Approve the allocation first.",
        "filename": "",
        "url": "",
    }
    assert srv._EXPORTS == {}


def test_changed_weights_after_approval_are_refused_not_exported():
    rows, _ = _approved()
    changed = [
        srv.BasketRowInput(enabled=r.enabled, weight=("99" if r.enabled else r.weight))
        for r in rows
    ]
    stale = _export(changed)
    assert stale["state"] == "error"
    assert stale["url"] == ""
    assert srv._EXPORTS == {}


def test_missing_http_request_gives_a_clear_error(monkeypatch):
    def no_request():
        raise RuntimeError("No active HTTP request found.")

    monkeypatch.setattr(srv, "get_http_request", no_request)
    rows, _ = _approved()
    result = _export(rows)
    assert result["state"] == "error"
    assert "HTTP server" in result["message"]
    assert result["url"] == ""
    assert srv._EXPORTS == {}


def test_outside_an_http_request_the_real_lookup_reports_no_server(monkeypatch):
    monkeypatch.setattr(srv, "get_http_request", real_get_http_request)
    assert srv._request_base_url() is None


def test_unknown_export_token_is_not_found():
    with TestClient(srv.mcp.http_app()) as http:
        assert http.get("/exports/not-a-real-token").status_code == 404


def test_export_store_keeps_only_the_most_recent_exports(monkeypatch):
    monkeypatch.setattr(srv, "EXPORT_LIMIT", 2)
    rows, _ = _approved()
    urls = [_export(rows)["url"] for _ in range(3)]
    assert len(srv._EXPORTS) == 2
    assert _fetch(urls[0]).status_code == 404
    assert _fetch(urls[2]).status_code == 200


def test_text_cells_that_look_like_formulas_are_neutralized():
    assert srv._csv_text('=HYPERLINK("x")') == '\'=HYPERLINK("x")'
    assert srv._csv_text("+1") == "'+1"
    assert srv._csv_text("Steel mill products") == "Steel mill products"
    assert srv._csv_text(None) == ""


def _walk(tree):
    if isinstance(tree, dict):
        yield tree
        for value in tree.values():
            yield from _walk(value)
    elif isinstance(tree, list):
        for item in tree:
            yield from _walk(item)


def _download_buttons(tree, conditions=()):
    """Yield each Download CSV button with the Prefab conditions around it."""
    if isinstance(tree, dict):
        if tree.get("type") == "Condition":
            for case in tree.get("cases", []):
                yield from _download_buttons(
                    case.get("children", []), (*conditions, case.get("when"))
                )
            yield from _download_buttons(tree.get("else", []), (*conditions, "else"))
            return
        if tree.get("type") == "Button" and tree.get("label") == "Download CSV":
            yield tree, conditions
        for value in tree.values():
            yield from _download_buttons(value, conditions)
    elif isinstance(tree, list):
        for item in tree:
            yield from _download_buttons(item, conditions)


def test_download_control_is_disabled_before_approval_and_shown_only_when_ready():
    view = json.loads(json.dumps(srv.ppi_basket("y12").to_json()))
    prepare = next(
        n
        for n in _walk(view)
        if n.get("type") == "Button" and n.get("label") == "Prepare CSV"
    )
    assert "phase" in json.dumps(prepare["disabled"])
    buttons = list(_download_buttons(view))
    # Before approval: a disabled Download CSV, with the reason on screen.
    placeholder = [
        b for b, conds in buttons if not any("csv_export" in str(c) for c in conds)
    ]
    assert len(placeholder) == 1 and placeholder[0]["disabled"] is True
    assert "Download CSV is unavailable until the allocation is approved" in json.dumps(
        view
    )
    # Once a result is prepared, Download is gated on the ready state.
    ready = [
        b
        for b, conds in buttons
        if any("csv_export.state == 'ready'" in str(c) for c in conds)
    ]
    assert len(ready) == 1
    assert "openLink" in json.dumps(ready[0])
    assert "Download prepared CSV" not in json.dumps(view)
