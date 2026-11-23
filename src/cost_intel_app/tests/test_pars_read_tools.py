"""Drift checks for the read-only PARS tools the UI may call.

The manifest is committed beside this file. The allowlist and live checks run
only when PARS_REPO points at a PARS checkout.
"""

import json
import os
from pathlib import Path

import pytest

from cost_intel_app import pars_live
from cost_intel_app import pars_panels as pp

MANIFEST = Path(__file__).with_name("pars_read_tools.json")
PARS_REPO = os.environ.get("PARS_REPO", "").strip()
NEVER_READ_ONLY = frozenset(
    {
        "write_back_wbs",
        "clean_wbs_data",
        "tune_and_train_wbs",
        "predict_wbs",
        "run_wbs_pipeline",
    }
)
needs_pars = pytest.mark.skipif(
    not PARS_REPO, reason="set PARS_REPO to a PARS checkout"
)


def test_read_only_tools_match_the_committed_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert pp.READ_ONLY_TOOLS == frozenset(manifest)


def test_no_write_or_compute_tool_is_read_only():
    assert not (pp.READ_ONLY_TOOLS & NEVER_READ_ONLY)


@needs_pars
def test_read_only_tools_are_on_the_pars_allowlist():
    config = Path(PARS_REPO, "src", "mcp_servers.json")
    entry = json.loads(config.read_text(encoding="utf-8"))["servers"]["pars_mcp"]
    assert pp.READ_ONLY_TOOLS <= set(entry["allowed_tools"])


@needs_pars
def test_the_launch_command_is_the_allowlist_entry_plus_no_sync():
    config = Path(PARS_REPO, "src", "mcp_servers.json")
    entry = json.loads(config.read_text(encoding="utf-8"))["servers"]["pars_mcp"]
    command = list(pars_live.PARS_COMMAND)
    assert command[0] == entry["command"]
    assert command[1:] == entry["args"]
    assert command.count("--no-sync") == 1
    assert command[1:3] == ["run", "--no-sync"]


@needs_pars
def test_live_server_offers_every_read_only_tool():
    with pars_live.live_session(PARS_REPO) as session:
        assert pp.READ_ONLY_TOOLS <= session.tool_names()
