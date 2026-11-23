"""Synthetic WBS elements store their parent code, so children and lineage work."""

import duckdb

from pars_local_mcp.storage.initialization import initialize_database


def test_every_element_stores_the_code_of_its_parent(tmp_path):
    db = tmp_path / "wbs.duckdb"
    initialize_database(db)
    with duckdb.connect(str(db), read_only=True) as conn:
        rows = conn.execute(
            "SELECT parsid, wbs_code, parent_wbs FROM wbs_elements"
        ).fetchall()
    codes = {(parsid, code) for parsid, code, _ in rows}
    assert rows, "expected synthetic elements to be loaded"
    for parsid, code, parent in rows:
        if "." in code:
            assert parent == code.rsplit(".", 1)[0], (parsid, code, parent)
            assert (parsid, parent) in codes, (parsid, code)
        else:
            assert parent is None, (parsid, code, parent)
