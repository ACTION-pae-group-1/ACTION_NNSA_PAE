"""Tests for the parity harness helpers.

The parity sequence itself runs in test_functions.py. These tests cover the harness's
own contracts: the source loader names a missing function in its error, compute_outputs
checks ``side`` before touching any file, the legacy and local table maps are exact
inverses, and parity_golden.json sits next to the harness with the expected keys.
"""

import json
import sys
from pathlib import Path

import pytest

from pars_local_mcp.wbs_port import parity_harness as harness

pytestmark = pytest.mark.slow

# Output keys that test_functions.py expects in the golden file
# (see test_golden_covers_every_live_function).
EXPECTED_GOLDEN_KEYS = {
    "transform",
    "concatenate_sample",
    "clean_sample",
    "concatenate_spae",
    "clean_spae",
    "stratify",
    "f1_scorer",
    "safe_f1",
    "batch_predict",
    "load_tables",
    "label_encoder",
}


def test_load_source_namespace_raises_key_error_naming_missing_function(
    tmp_path, monkeypatch
):
    source = tmp_path / "functions_stub.py"
    source.write_text("def transform(df):\n    return df\n", encoding="utf-8")
    # The loader registers a module entry before its name check; monkeypatch
    # removes that entry again after the test.
    monkeypatch.setitem(sys.modules, "wbs_source_functions", None)
    # The stub defines only "transform", so the first missing name in
    # FUNCTION_NAMES is reported (currently "load_tables").
    missing = next(n for n in harness.FUNCTION_NAMES if n != "transform")
    with pytest.raises(KeyError, match=missing):
        harness.load_source_namespace(source)


def test_compute_outputs_rejects_unknown_side_before_any_file_access(tmp_path):
    ns: dict = {}
    workdir = tmp_path / "work"
    with pytest.raises(ValueError, match="side must be 'port' or 'source'"):
        # The fixture path does not exist; it must never be read or copied.
        harness.compute_outputs(
            ns, tmp_path / "never_read.duckdb", workdir, side="both"
        )
    assert ns == {}
    assert not workdir.exists()


def test_legacy_and_local_table_maps_are_exact_inverses():
    legacy_to_local = {
        legacy: local for local, legacy in harness.LEGACY_TABLE_NAMES.items()
    }
    # A shared legacy name would collapse entries in the inverse mapping.
    assert len(legacy_to_local) == len(harness.LEGACY_TABLE_NAMES)
    assert harness.LOCAL_OF_LEGACY == legacy_to_local
    assert {v: k for k, v in harness.LOCAL_OF_LEGACY.items()} == (
        harness.LEGACY_TABLE_NAMES
    )


def test_golden_file_exists_with_provenance_and_expected_outputs():
    golden = Path(harness.GOLDEN_PATH)
    assert golden.is_file()
    payload = json.loads(golden.read_text(encoding="utf-8"))
    assert {"provenance", "outputs"} <= set(payload)
    missing = EXPECTED_GOLDEN_KEYS - set(payload["outputs"])
    assert not missing, f"golden outputs lack keys used by tests: {sorted(missing)}"


def test_golden_path_points_to_file_next_to_harness():
    expected = Path(harness.__file__).resolve().with_name("parity_golden.json")
    assert Path(harness.GOLDEN_PATH).resolve() == expected
