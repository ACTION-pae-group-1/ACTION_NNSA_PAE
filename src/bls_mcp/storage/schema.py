"""Versioned DuckDB schema for offline-built BLS analytical snapshots.

The observations table has no PRIMARY KEY and starts without an ART index.
Milestones 3 and 4 load PC and CU observations into the same table. The first
program loader creates a single-column ART index on series_id AFTER its bulk
load; subsequent loaders retain it. Schema version 3 retains the published
CU area selectability field. Schema version 4 adds the Employment Cost Index
(CI) classification tables. Snapshot validation still precedes publication.
"""

from __future__ import annotations

from duckdb import DuckDBPyConnection

SCHEMA_VERSION = 5

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS snapshot_info (
        singleton SMALLINT PRIMARY KEY DEFAULT 1 CHECK (singleton = 1),
        snapshot_id VARCHAR NOT NULL,
        schema_version INTEGER NOT NULL,
        built_at TIMESTAMPTZ NOT NULL,
        build_commit VARCHAR,
        programs VARCHAR NOT NULL,
        lifecycle_state VARCHAR NOT NULL CHECK (
            lifecycle_state IN ('BUILDING', 'VALIDATING', 'READY', 'PUBLISHED')
        ),
        validation_status VARCHAR NOT NULL CHECK (
            validation_status IN ('NOT_RUN', 'PASSED', 'FAILED')
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_files (
        source_file_id BIGINT PRIMARY KEY,
        program_code VARCHAR NOT NULL,
        filename VARCHAR NOT NULL,
        source_url VARCHAR,
        sha256 VARCHAR NOT NULL,
        size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
        retrieved_at TIMESTAMPTZ,
        etag VARCHAR,
        last_modified VARCHAR,
        selection_role VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS series_catalog (
        series_id VARCHAR PRIMARY KEY,
        program_code VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        description VARCHAR,
        seasonal_adjustment BOOLEAN,
        first_year SMALLINT,
        first_period VARCHAR,
        last_year SMALLINT,
        last_period VARCHAR,
        units VARCHAR,
        original_reference_base VARCHAR,
        active BOOLEAN
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS observations (
        series_id VARCHAR NOT NULL,
        year SMALLINT NOT NULL,
        period VARCHAR NOT NULL,
        value DOUBLE NOT NULL CHECK (isfinite(value)),
        footnote_codes VARCHAR,
        source_file_id BIGINT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pc_industry (
        industry_code VARCHAR PRIMARY KEY,
        industry_name VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pc_product (
        industry_code VARCHAR NOT NULL,
        product_code VARCHAR NOT NULL,
        product_name VARCHAR NOT NULL,
        PRIMARY KEY (industry_code, product_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pc_series (
        series_id VARCHAR PRIMARY KEY,
        industry_code VARCHAR NOT NULL,
        product_code VARCHAR,
        seasonal_code VARCHAR NOT NULL,
        base_date VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cu_area (
        area_code VARCHAR PRIMARY KEY,
        area_name VARCHAR NOT NULL,
        display_level INTEGER NOT NULL,
        selectable BOOLEAN NOT NULL,
        sort_sequence INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cu_item (
        item_code VARCHAR PRIMARY KEY,
        item_name VARCHAR NOT NULL,
        display_level INTEGER NOT NULL,
        selectable BOOLEAN NOT NULL,
        sort_sequence INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cu_series (
        series_id VARCHAR PRIMARY KEY,
        area_code VARCHAR NOT NULL,
        item_code VARCHAR NOT NULL,
        seasonal_code VARCHAR NOT NULL,
        periodicity_code VARCHAR NOT NULL,
        base_code VARCHAR NOT NULL,
        base_period VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wp_group (
        group_code VARCHAR PRIMARY KEY,
        group_name VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wp_item (
        group_code VARCHAR NOT NULL, 
        item_code VARCHAR NOT NULL, 
        item_name VARCHAR NOT NULL, 
        PRIMARY KEY(group_code,item_code
    )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wp_series (
        series_id VARCHAR PRIMARY KEY, 
        group_code VARCHAR NOT NULL, 
        item_code VARCHAR NOT NULL, 
        seasonal_code VARCHAR NOT NULL, 
        base_date VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ci_dimension (
        dimension VARCHAR NOT NULL CHECK (
            dimension IN (
                'owner', 'industry', 'occupation', 'subcell', 'area', 'estimate'
            )
        ),
        code VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        display_level INTEGER NOT NULL,
        selectable BOOLEAN NOT NULL,
        sort_sequence INTEGER NOT NULL,
        PRIMARY KEY (dimension, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ci_series (
        series_id VARCHAR PRIMARY KEY,
        seasonal_code VARCHAR NOT NULL,
        owner_code VARCHAR NOT NULL,
        industry_code VARCHAR NOT NULL,
        occupation_code VARCHAR NOT NULL,
        subcell_code VARCHAR NOT NULL,
        area_code VARCHAR NOT NULL,
        estimate_code VARCHAR NOT NULL,
        periodicity_code VARCHAR NOT NULL CHECK (periodicity_code = 'I')
    )
    """,
)


def initialize_schema(conn: DuckDBPyConnection) -> None:
    """Create empty tables as one transaction on an offline builder connection.

    Safe to call again on an otherwise unchanged schema. Existing schemas are
    not migrated; consumers reject unsupported schema versions on read.
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
