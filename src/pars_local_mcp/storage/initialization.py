"""Database initialization with synthetic WBS data for PARS MCP server.

This module initializes the DuckDB database at server startup with:
1. WBS schema (tables, indexes, constraints)
2. Synthetic WBS element data (in-memory generation, no stored files)
3. Project metadata

All data is synthetic/fake (suitable for testing and demos).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from faker import Faker

from pars_local_mcp.mcp.errors import PublicError

SYNTHETIC_MARKER_TABLE = "pars_synthetic_marker"
PARS_TABLES = ("labeled_wbs", "wbs_elements", "projects")
DEFAULT_SYNTHETIC_ROOT = Path(__file__).resolve().parents[1] / "data"

STADIUM_WBS_ASSETS = (
    "Stadium Bowl Foundations",
    "Structural Steel and Upper Deck",
    "Retractable Roof and Weather Enclosure",
    "Field-Level Drainage and Turf",
    "Premium Seating and Hospitality Suites",
    "Concourse Circulation and Accessibility",
    "Crowd Safety and Security Screening",
    "Broadcast and Digital Signage Network",
    "High-Capacity Electrical Distribution",
    "Transportation Plaza and Parking",
    "Stadium Mechanical and Fire Protection",
    "Team Facilities and Player Access",
)
STADIUM_WBS_ACTIVITIES = (
    "Engineering Design",
    "Procurement",
    "Site Preparation",
    "Structural Construction",
    "Systems Integration",
    "Commissioning",
    "Quality Inspection",
    "Construction Coordination",
)


def stadium_wbs_title(parsid: str, wbs_code: str) -> str:
    """Stable Faker-generated stadium work package title for a project/WBS key."""
    fake = Faker()
    key = f"{parsid}:{wbs_code}"
    fake.seed_instance(sum(index * ord(char) for index, char in enumerate(key, 1)))
    return (
        f"{fake.random_element(STADIUM_WBS_ACTIVITIES)} - "
        f"{fake.random_element(STADIUM_WBS_ASSETS)}"
    )


def _reset_allowed(
    conn: duckdb.DuckDBPyConnection, db_path: Path, synthetic_root: Path
) -> bool:
    """Startup may drop PARS tables only in a database known to be synthetic.

    A database is known to be synthetic if it carries the marker table, or if it
    sits under the synthetic data directory. A database with no PARS tables has
    nothing to drop, so it is always allowed.
    """
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if SYNTHETIC_MARKER_TABLE in tables or not tables.intersection(PARS_TABLES):
        return True
    try:
        db_path.resolve().relative_to(synthetic_root.resolve())
    except ValueError:
        return False
    return True


def generate_labeled_wbs_training_data() -> list[
    tuple[str, str, str, str, str, str, str, str, str, str]
]:
    """Generate synthetic labeled WBS training data with CAEF hierarchy codes.

    Returns:
        List of (parsid, wbs_code, title, caef_L2-L8) tuples for training.
    """
    labeled_data = [
        # Project 1: Program Management
        ("proj_001", "01", "Program", "E1", "E1.1", "", "", "", "", ""),
        ("proj_001", "01.01", "Planning", "E1", "E1.1", "E1.1.1", "", "", "", ""),
        (
            "proj_001",
            "01.01.01",
            "Requirements",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "",
            "",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01",
            "Functional Requirements",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01.01",
            "Core Features",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.1",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01.01.01",
            "User Management",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.1",
            "E1.1.1.1.A.1.a",
        ),
        (
            "proj_001",
            "01.01.01.01.01.01.01",
            "Authentication",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.1",
            "E1.1.1.1.A.1.a",
        ),
        (
            "proj_001",
            "01.01.01.01.01.01.02",
            "Authorization",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.1",
            "E1.1.1.1.A.1.b",
        ),
        (
            "proj_001",
            "01.01.01.01.01.02",
            "Data Storage",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.2",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01.01.02.01",
            "Database Design",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.A",
            "E1.1.1.1.A.2",
            "E1.1.1.1.A.2.a",
        ),
        (
            "proj_001",
            "01.01.01.01.02",
            "Non-Functional",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.B",
            "",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01.02.01",
            "Performance",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.B",
            "E1.1.1.1.B.1",
            "",
        ),
        (
            "proj_001",
            "01.01.01.01.02.01.01",
            "Latency Goals",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.1",
            "E1.1.1.1.B",
            "E1.1.1.1.B.1",
            "E1.1.1.1.B.1.a",
        ),
        (
            "proj_001",
            "01.01.01.02",
            "Non-Functional Requirements",
            "E1",
            "E1.1",
            "E1.1.1",
            "E1.1.1.2",
            "",
            "",
            "",
        ),
        ("proj_001", "01.02", "Design", "E1", "E1.2", "", "", "", "", ""),
        (
            "proj_001",
            "01.02.01",
            "Architecture",
            "E1",
            "E1.2",
            "E1.2.1",
            "",
            "",
            "",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01",
            "System Architecture",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "",
            "",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.01",
            "Microservices",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.A",
            "",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.01.01",
            "API Gateway",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.A",
            "E1.2.1.1.A.1",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.01.01.01",
            "Request Routing",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.A",
            "E1.2.1.1.A.1",
            "E1.2.1.1.A.1.a",
        ),
        (
            "proj_001",
            "01.02.01.01.01.02",
            "Service Mesh",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.A",
            "E1.2.1.1.A.2",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.02",
            "Data Layer",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.B",
            "",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.02.01",
            "ORM Framework",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.B",
            "E1.2.1.1.B.1",
            "",
        ),
        (
            "proj_001",
            "01.02.01.01.02.01.01",
            "Query Optimization",
            "E1",
            "E1.2",
            "E1.2.1",
            "E1.2.1.1",
            "E1.2.1.1.B",
            "E1.2.1.1.B.1",
            "E1.2.1.1.B.1.a",
        ),
        ("proj_001", "01.03", "Implementation", "E1", "E1.3", "", "", "", "", ""),
        ("proj_001", "01.03.01", "Coding", "E1", "E1.3", "E1.3.1", "", "", "", ""),
        (
            "proj_001",
            "01.03.01.01",
            "Backend Development",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "",
            "",
            "",
        ),
        (
            "proj_001",
            "01.03.01.01.01",
            "API Implementation",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.A",
            "",
            "",
        ),
        (
            "proj_001",
            "01.03.01.01.01.01",
            "REST Endpoints",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.A",
            "E1.3.1.1.A.1",
            "",
        ),
        (
            "proj_001",
            "01.03.01.01.01.01.01",
            "User Endpoints",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.A",
            "E1.3.1.1.A.1",
            "E1.3.1.1.A.1.a",
        ),
        (
            "proj_001",
            "01.03.01.01.01.01.02",
            "Data Endpoints",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.A",
            "E1.3.1.1.A.1",
            "E1.3.1.1.A.1.b",
        ),
        (
            "proj_001",
            "01.03.01.01.02",
            "Database Migration",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.B",
            "",
            "",
        ),
        (
            "proj_001",
            "01.03.01.01.02.01",
            "Schema Creation",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.B",
            "E1.3.1.1.B.1",
            "",
        ),
        (
            "proj_001",
            "01.03.01.01.02.01.01",
            "Table Definition",
            "E1",
            "E1.3",
            "E1.3.1",
            "E1.3.1.1",
            "E1.3.1.1.B",
            "E1.3.1.1.B.1",
            "E1.3.1.1.B.1.a",
        ),
        # Project 2: Platform Development
        ("proj_002", "01", "Platform", "E2", "E2.1", "", "", "", "", ""),
        ("proj_002", "01.01", "Infrastructure", "E2", "E2.1", "E2.1.1", "", "", "", ""),
        (
            "proj_002",
            "01.01.01",
            "Cloud Setup",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "",
            "",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01",
            "AWS Configuration",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01.01",
            "Network Setup",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.1",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01.01.01",
            "VPC Configuration",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.1",
            "E2.1.1.1.A.1.a",
        ),
        (
            "proj_002",
            "01.01.01.01.01.01.01",
            "Subnets",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.1",
            "E2.1.1.1.A.1.a",
        ),
        (
            "proj_002",
            "01.01.01.01.01.01.02",
            "Security Groups",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.1",
            "E2.1.1.1.A.1.b",
        ),
        (
            "proj_002",
            "01.01.01.01.01.02",
            "Load Balancing",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.2",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01.01.02.01",
            "ALB Setup",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.A",
            "E2.1.1.1.A.2",
            "E2.1.1.1.A.2.a",
        ),
        (
            "proj_002",
            "01.01.01.01.02",
            "Storage Setup",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.B",
            "",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01.02.01",
            "S3 Buckets",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.B",
            "E2.1.1.1.B.1",
            "",
        ),
        (
            "proj_002",
            "01.01.01.01.02.01.01",
            "Bucket Policies",
            "E2",
            "E2.1",
            "E2.1.1",
            "E2.1.1.1",
            "E2.1.1.1.B",
            "E2.1.1.1.B.1",
            "E2.1.1.1.B.1.a",
        ),
        ("proj_002", "01.02", "Services", "E2", "E2.2", "", "", "", "", ""),
        (
            "proj_002",
            "01.02.01",
            "API Development",
            "E2",
            "E2.2",
            "E2.2.1",
            "",
            "",
            "",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01",
            "RESTful Endpoints",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "",
            "",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.01",
            "Authentication API",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.01.01",
            "Token Service",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "E2.2.1.1.A.1",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.01.01.01",
            "JWT Generation",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "E2.2.1.1.A.1",
            "E2.2.1.1.A.1.a",
        ),
        (
            "proj_002",
            "01.02.01.01.01.01.02",
            "Token Validation",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "E2.2.1.1.A.1",
            "E2.2.1.1.A.1.b",
        ),
        (
            "proj_002",
            "01.02.01.01.01.02",
            "User Service",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "E2.2.1.1.A.2",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.01.02.01",
            "User Registration",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.A",
            "E2.2.1.1.A.2",
            "E2.2.1.1.A.2.a",
        ),
        (
            "proj_002",
            "01.02.01.01.02",
            "Data API",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.B",
            "",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.02.01",
            "Query Service",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.B",
            "E2.2.1.1.B.1",
            "",
        ),
        (
            "proj_002",
            "01.02.01.01.02.01.01",
            "Query Builder",
            "E2",
            "E2.2",
            "E2.2.1",
            "E2.2.1.1",
            "E2.2.1.1.B",
            "E2.2.1.1.B.1",
            "E2.2.1.1.B.1.a",
        ),
    ]
    return [
        (row[0], row[1], stadium_wbs_title(row[0], row[1]), *row[3:])
        for row in labeled_data
    ]


def generate_synthetic_wbs_elements() -> list[tuple[str, str, str, int]]:
    """Generate synthetic WBS elements for testing (7-level deep hierarchy).

    Returns:
        List of tuples: (parsid, wbs_code, title, level)
    """
    elements = [
        # Project 1: Program Management (7-level deep)
        ("proj_001", "01", "Program", 1),
        ("proj_001", "01.01", "Planning", 2),
        ("proj_001", "01.01.01", "Requirements", 3),
        ("proj_001", "01.01.01.01", "Functional Requirements", 4),
        ("proj_001", "01.01.01.01.01", "Core Features", 5),
        ("proj_001", "01.01.01.01.01.01", "User Management", 6),
        ("proj_001", "01.01.01.01.01.01.01", "Authentication", 7),
        ("proj_001", "01.01.01.01.01.01.02", "Authorization", 7),
        ("proj_001", "01.01.01.01.01.02", "Data Storage", 6),
        ("proj_001", "01.01.01.01.01.02.01", "Database Design", 7),
        ("proj_001", "01.01.01.01.02", "Non-Functional", 5),
        ("proj_001", "01.01.01.01.02.01", "Performance", 6),
        ("proj_001", "01.01.01.01.02.01.01", "Latency Goals", 7),
        ("proj_001", "01.01.01.02", "Non-Functional Requirements", 4),
        ("proj_001", "01.02", "Design", 2),
        ("proj_001", "01.02.01", "Architecture", 3),
        ("proj_001", "01.02.01.01", "System Architecture", 4),
        ("proj_001", "01.02.01.01.01", "Microservices", 5),
        ("proj_001", "01.02.01.01.01.01", "API Gateway", 6),
        ("proj_001", "01.02.01.01.01.01.01", "Request Routing", 7),
        ("proj_001", "01.02.01.01.01.02", "Service Mesh", 6),
        ("proj_001", "01.02.01.01.02", "Data Layer", 5),
        ("proj_001", "01.02.01.01.02.01", "ORM Framework", 6),
        ("proj_001", "01.02.01.01.02.01.01", "Query Optimization", 7),
        ("proj_001", "01.03", "Implementation", 2),
        ("proj_001", "01.03.01", "Coding", 3),
        ("proj_001", "01.03.01.01", "Backend Development", 4),
        ("proj_001", "01.03.01.01.01", "API Implementation", 5),
        ("proj_001", "01.03.01.01.01.01", "REST Endpoints", 6),
        ("proj_001", "01.03.01.01.01.01.01", "User Endpoints", 7),
        ("proj_001", "01.03.01.01.01.01.02", "Data Endpoints", 7),
        ("proj_001", "01.03.01.01.02", "Database Migration", 5),
        ("proj_001", "01.03.01.01.02.01", "Schema Creation", 6),
        ("proj_001", "01.03.01.01.02.01.01", "Table Definition", 7),
        # Project 2: Platform Development (7-level deep)
        ("proj_002", "01", "Platform", 1),
        ("proj_002", "01.01", "Infrastructure", 2),
        ("proj_002", "01.01.01", "Cloud Setup", 3),
        ("proj_002", "01.01.01.01", "AWS Configuration", 4),
        ("proj_002", "01.01.01.01.01", "Network Setup", 5),
        ("proj_002", "01.01.01.01.01.01", "VPC Configuration", 6),
        ("proj_002", "01.01.01.01.01.01.01", "Subnets", 7),
        ("proj_002", "01.01.01.01.01.01.02", "Security Groups", 7),
        ("proj_002", "01.01.01.01.01.02", "Load Balancing", 6),
        ("proj_002", "01.01.01.01.01.02.01", "ALB Setup", 7),
        ("proj_002", "01.01.01.01.02", "Storage Setup", 5),
        ("proj_002", "01.01.01.01.02.01", "S3 Buckets", 6),
        ("proj_002", "01.01.01.01.02.01.01", "Bucket Policies", 7),
        ("proj_002", "01.02", "Services", 2),
        ("proj_002", "01.02.01", "API Development", 3),
        ("proj_002", "01.02.01.01", "RESTful Endpoints", 4),
        ("proj_002", "01.02.01.01.01", "Authentication API", 5),
        ("proj_002", "01.02.01.01.01.01", "Token Service", 6),
        ("proj_002", "01.02.01.01.01.01.01", "JWT Generation", 7),
        ("proj_002", "01.02.01.01.01.01.02", "Token Validation", 7),
        ("proj_002", "01.02.01.01.01.02", "User Service", 6),
        ("proj_002", "01.02.01.01.01.02.01", "User Registration", 7),
        ("proj_002", "01.02.01.01.02", "Data API", 5),
        ("proj_002", "01.02.01.01.02.01", "Query Service", 6),
        ("proj_002", "01.02.01.01.02.01.01", "Query Builder", 7),
    ]
    return [
        (parsid, code, stadium_wbs_title(parsid, code), level)
        for parsid, code, _, level in elements
    ]


def initialize_database(
    db_path: str | Path, *, synthetic_root: Path | None = None
) -> None:
    """Initialize DuckDB with WBS schema and synthetic data.

    Called during server startup to set up the database for MCP tools.
    Regenerates fresh synthetic data each server session, but refuses to drop
    tables in a database that is neither marked synthetic nor under the
    synthetic data directory.

    Args:
        db_path: Path to DuckDB database file
        synthetic_root: Directory whose databases are known to be synthetic
    """
    path = Path(db_path)
    root = synthetic_root if synthetic_root is not None else DEFAULT_SYNTHETIC_ROOT
    conn = duckdb.connect(str(path))

    try:
        if not _reset_allowed(conn, path, root):
            raise PublicError(
                "Refusing to reset a database that is not marked as synthetic"
            )
        conn.execute(
            f"CREATE OR REPLACE TABLE {SYNTHETIC_MARKER_TABLE} "
            "AS SELECT 'synthetic' AS marker"
        )

        # Drop existing tables to ensure schema consistency. labeled_wbs references
        # projects, so it must go first; it is regenerated below.
        conn.execute("DROP TABLE IF EXISTS labeled_wbs")
        conn.execute("DROP TABLE IF EXISTS wbs_elements")
        conn.execute("DROP TABLE IF EXISTS projects")

        # Create projects table
        conn.execute(
            """
            CREATE TABLE projects (
                parsid VARCHAR PRIMARY KEY,
                project_name VARCHAR NOT NULL
            )
        """
        )

        # Create WBS elements table
        conn.execute(
            """
            CREATE TABLE wbs_elements (
                parsid VARCHAR NOT NULL,
                wbs_code VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                level INTEGER NOT NULL,
                parent_wbs VARCHAR,
                leaf_node BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (parsid, wbs_code),
                FOREIGN KEY (parsid) REFERENCES projects(parsid)
            )
        """
        )

        # Create labeled WBS table (training data with CAEF codes)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labeled_wbs (
                parsid VARCHAR NOT NULL,
                wbs_code VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                caef_level_2 VARCHAR,
                caef_level_3 VARCHAR,
                caef_level_4 VARCHAR,
                caef_level_5 VARCHAR,
                caef_level_6 VARCHAR,
                caef_level_7 VARCHAR,
                caef_level_8 VARCHAR,
                PRIMARY KEY (parsid, wbs_code),
                FOREIGN KEY (parsid) REFERENCES projects(parsid)
            )
        """
        )

        # Insert project metadata
        conn.execute(
            "INSERT OR IGNORE INTO projects VALUES (?, ?)",
            ["proj_001", "Crescent Bay Football Stadium Construction"],
        )
        conn.execute(
            "INSERT OR IGNORE INTO projects VALUES (?, ?)",
            ["proj_002", "Northpoint Retractable Roof Stadium Expansion"],
        )

        # Insert synthetic WBS elements
        elements = generate_synthetic_wbs_elements()
        # Build a set of all parent codes to identify leaf nodes
        parent_codes = set()
        for parsid, wbs_code, title, level in elements:
            # Extract parent code (remove last segment after last dot)
            if "." in wbs_code:
                parent = ".".join(wbs_code.rsplit(".", 1)[:-1])
                parent_codes.add((parsid, parent))

        for parsid, wbs_code, title, level in elements:
            is_leaf = (parsid, wbs_code) not in parent_codes
            parent = wbs_code.rsplit(".", 1)[0] if "." in wbs_code else None
            conn.execute(
                """
                INSERT OR IGNORE INTO wbs_elements
                (parsid, wbs_code, title, level, parent_wbs, leaf_node)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                [parsid, wbs_code, title, level, parent, is_leaf],
            )

        # Insert labeled WBS training data (WBS titles with CAEF hierarchy codes)
        labeled_elements = generate_labeled_wbs_training_data()
        for (
            parsid,
            wbs_code,
            title,
            caef_l2,
            caef_l3,
            caef_l4,
            caef_l5,
            caef_l6,
            caef_l7,
            caef_l8,
        ) in labeled_elements:
            conn.execute(
                """
                INSERT OR IGNORE INTO labeled_wbs
                (parsid, wbs_code, title, caef_level_2, caef_level_3, caef_level_4,
                 caef_level_5, caef_level_6, caef_level_7, caef_level_8)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    parsid,
                    wbs_code,
                    title,
                    caef_l2,
                    caef_l3,
                    caef_l4,
                    caef_l5,
                    caef_l6,
                    caef_l7,
                    caef_l8,
                ],
            )

        conn.close()

    except PublicError:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise RuntimeError("Failed to initialize the PARS database") from e
