"""Isolated, deterministic evaluation of all 16 registered PARS MCP tools.

This closes the gap left by the original harness (agent.py READ_ONLY_TOOLS), which
exposed 7 of 16 tools. Each run:

  * builds an isolated environment under C:/tmp/pars_eval_gap/runs/<run_id>/:
    a copy of the synthetic mock source, a fresh synthetic PARS database, the run
    directory, the model directory, and the signing key. No path points into the
    repository data directories.
  * calls every tool through the MCP interface (fastmcp in-process client on the
    real create_server() registration), not by importing tool functions.
  * checks each case against deterministic expectations and, for read tools, against
    direct read-only SQL oracles on the same isolated database.
  * snapshots protected file hashes before and after the run, and per case checks
    that the synthetic database and the source copy are unchanged.
  * traces each case through eval/phoenix/tracing.py. Phoenix is used only if a
    loopback Phoenix answers; otherwise spans go to <run_dir>/traces.jsonl and the
    reason is recorded in the summary.

Usage (from the repository root):
    .venv\\Scripts\\python.exe eval\\phoenix\\run_pars_gap_eval.py --run-id <id>

No LLM judge is used. Every check here is deterministic.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # keep repository __pycache__ untouched

import argparse  # noqa: E402
import asyncio  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Awaitable, Callable  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(EVAL_DIR))

import duckdb  # noqa: E402
from fastmcp import Client, FastMCP  # noqa: E402
from tracing import setup_tracing  # noqa: E402

from pars_local_mcp.config import Settings  # noqa: E402
from pars_local_mcp.mcp.server import create_server  # noqa: E402
from pars_local_mcp.mcp.tools import register_tools  # noqa: E402

GAP_ROOT = Path("C:/tmp/pars_eval_gap")
CASES_PATH = EVAL_DIR / "datasets" / "pars-eval-gap" / "cases.json"
MOCK_SOURCE = REPO_ROOT / "src" / "pars_local_mcp" / "data" / "mock_pars_full.duckdb"
PROTECTED_FILES = [
    "src/pars_local_mcp/data/wbs.duckdb",
    "src/pars_local_mcp/data/mock_pars_full.duckdb",
    "src/pars_local_mcp/data/caef_synthetic_labeled.duckdb",
    "data/local/snapshots/active-snapshot.json",
    "data/local/snapshots/bls-sample_pc_ci.duckdb",
    "data/local/snapshots/bls-sample_pc_ci.duckdb.validation.json",
    "data/local/snapshots/pars-eval-2026-11-19.duckdb",
    "data/local/snapshots/pars-eval-2026-11-19.manifest.json",
]
SNAPSHOT_PATH = (
    REPO_ROOT / "data" / "local" / "snapshots" / "pars-eval-2026-11-19.duckdb"
)
SNAPSHOT_MANIFEST_PATH = SNAPSHOT_PATH.with_name("pars-eval-2026-11-19.manifest.json")
# The checksum is read from the snapshot manifest, not hard-coded here.
SNAPSHOT_SHA256 = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))[
    "snapshot_sha256"
]
CAEF_SOURCE_SHA256 = "7d645ce0361bfb8caa07b551d8b91edfd8443015c00edc7f730b7a75185dd57d"
PROTECTED_TREES = ["eval", "src/cost_intel_app/demo_assets/caef"]
FORBIDDEN_PREFIXES = [
    REPO_ROOT / "src" / "pars_local_mcp" / "data",
    REPO_ROOT / "data",
]
PARS_SETTING_NAMES = (
    "database_path",
    "model_dir",
    "model_signing_key_path",
    "wbs_runs_dir",
    "wbs_source_db",
)
PARS_ENV_KEYS = {
    "DATABASE_PATH": "database_path",
    "MODEL_DIR": "model_dir",
    "MODEL_SIGNING_KEY_PATH": "model_signing_key_path",
    "WBS_RUNS_DIR": "wbs_runs_dir",
    "WBS_SOURCE_DB": "wbs_source_db",
}
ALL_TOOLS = (
    "list_projects",
    "search_wbs",
    "get_wbs_hierarchy",
    "get_wbs_lineage",
    "get_project_info",
    "get_leaf_nodes",
    "get_wbs_by_level",
    "validate_wbs_inputs",
    "clean_wbs_data",
    "tune_and_train_wbs",
    "predict_wbs",
    "write_back_wbs",
    "run_wbs_pipeline",
    "get_wbs_run_status",
    "get_wbs_project_descriptions",
    "get_wbs_rows",
)


# ----------------------------------------------------------------- hashing
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_protected() -> dict[str, str]:
    """SHA-256 of protected files and of every file in the protected trees."""
    out: dict[str, str] = {}
    for rel in PROTECTED_FILES:
        p = REPO_ROOT / rel
        out[rel] = sha256_file(p) if p.is_file() else "MISSING"
    for tree in PROTECTED_TREES:
        for p in sorted((REPO_ROOT / tree).rglob("*")):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            # This evaluation's own new files are not historical evidence.
            if rel == "eval/phoenix/run_pars_gap_eval.py" or rel.startswith(
                "eval/phoenix/datasets/pars-eval-gap/"
            ):
                continue
            out[rel] = sha256_file(p)
    return out


def diff_snapshots(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    removed = sorted(k for k in before if k not in after)
    added = sorted(k for k in after if k not in before)
    return {"changed": changed, "removed": removed, "added": added}


# --------------------------------------------------------------- isolation
def assert_isolated(settings: Settings, run_root: Path) -> None:
    """Refuse any path outside run_root or inside a repository data directory."""
    root = str(run_root.resolve()).lower()
    for name in PARS_SETTING_NAMES:
        value = str(getattr(settings, name).resolve()).lower()
        if not value.startswith(root):
            raise RuntimeError(f"isolation: {name} is outside the run directory")
        for forbidden in FORBIDDEN_PREFIXES:
            if value.startswith(str(forbidden.resolve()).lower()):
                raise RuntimeError(f"isolation: {name} points into repository data")


def isolated_settings(
    variant_dir: Path,
    run_root: Path,
    source_db: Path,
    *,
    model_dir: Path | None = None,
    key_path: Path | None = None,
    runs_dir: Path | None = None,
) -> Settings:
    for sub in ("db", "models", "keys", "wbs_runs"):
        (variant_dir / sub).mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_path=variant_dir / "db" / "pars_gap_synthetic.duckdb",
        model_dir=model_dir or variant_dir / "models",
        model_signing_key_path=key_path or variant_dir / "keys" / "model_signing.key",
        wbs_runs_dir=runs_dir or variant_dir / "wbs_runs",
        wbs_source_db=source_db,
    )
    assert_isolated(settings, run_root)
    return settings


# ------------------------------------------------------------ MCP session
def register_only(settings: Settings) -> FastMCP:
    """The tool registration of create_server(), without initialize_database().

    create_server() drops and regenerates the PARS tables of the database it is
    given. Snapshot mode serves a disposable copy of the frozen snapshot, so it uses
    this path and the copy keeps the snapshot's contents.
    """
    mcp = FastMCP(
        "PARS WBS Classification and Hierarchy (gap evaluation)",
        mask_error_details=True,
    )
    register_tools(mcp, settings)
    return mcp


class Session:
    """One server instance reached through an in-process MCP client."""

    def __init__(self, settings: Settings, *, initialize: bool = True) -> None:
        self.settings = settings
        self.mcp = create_server(settings) if initialize else register_only(settings)
        self._client: Client | None = None

    async def __aenter__(self) -> "Session":
        self._client = Client(self.mcp)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        assert self._client is not None
        await self._client.__aexit__(*exc)

    async def tools(self) -> list[Any]:
        assert self._client is not None
        return await self._client.list_tools()

    async def call(self, tool: str, args: dict[str, Any]) -> tuple[dict, bool]:
        """Return (payload, is_error). Errors are payloads, never raised."""
        assert self._client is not None
        try:
            res = await self._client.call_tool(tool, args, raise_on_error=False)
        except Exception as exc:  # transport or validation failure
            return {"__exception__": f"{type(exc).__name__}: {exc}"}, True
        if res.structured_content is not None:
            payload = dict(res.structured_content)
        else:
            text = res.content[0].text if res.content else ""
            payload = {"__text__": text}
        return payload, bool(res.is_error)


def error_text(payload: dict) -> str:
    for key in ("error", "__text__", "__exception__"):
        if payload.get(key):
            return str(payload[key])
    return ""


# ------------------------------------------------------------- oracles
def _resolve_params(params: list[Any], args: dict[str, Any]) -> list[Any]:
    out = []
    for p in params or []:
        if isinstance(p, str) and p.startswith("$"):
            out.append(args[p[1:]])
        else:
            out.append(p)
    return out


def _query(db: Path, sql: str, params: list[Any]) -> list[tuple]:
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def _items(payload: dict, path: str | None) -> list[dict]:
    if path is None:
        return [payload]
    node: Any = payload
    for part in path.split("."):
        node = node[part]
    return [node] if isinstance(node, dict) else list(node)


def _dotted(payload: dict, path: str) -> Any:
    node: Any = payload
    for part in path.split("."):
        node = node[part]
    return node


def run_check(
    check: dict[str, Any],
    payload: dict,
    is_error: bool,
    args: dict[str, Any],
    dbs: dict[str, Path],
) -> dict[str, Any]:
    """Evaluate one deterministic check. Returns {name, pass, detail}."""
    kind = check["check"]
    name = check.get("name", kind)
    try:
        if kind == "ok":
            ok = not is_error and "error" not in payload
            return {"name": name, "pass": ok, "detail": error_text(payload)[:200]}
        if kind == "error_contains":
            text = error_text(payload)
            ok = check["text"] in text
            return {"name": name, "pass": ok, "detail": text[:200]}
        if kind == "has_error_key":
            ok = "error" in payload or is_error
            return {"name": name, "pass": ok, "detail": error_text(payload)[:200]}
        if kind == "keys_present":
            missing = [k for k in check["keys"] if k not in payload]
            return {"name": name, "pass": not missing, "detail": f"missing={missing}"}
        if kind == "field_equals":
            actual = _dotted(payload, check["path"])
            return {
                "name": name,
                "pass": actual == check["value"],
                "detail": f"actual={actual!r} expected={check['value']!r}",
            }
        if kind == "rows_match_sql":
            items = _items(payload, check.get("path"))
            cols = check["columns"]
            actual = sorted(tuple(str(i[c]) for c in cols) for i in items)
            rows = _query(
                dbs[check.get("db", "synthetic")],
                check["sql"],
                _resolve_params(check.get("params", []), args),
            )
            expected = sorted(tuple(str(v) for v in r) for r in rows)
            ok = actual == expected
            detail = f"returned={len(actual)} oracle={len(expected)}"
            return {"name": name, "pass": ok, "detail": detail}
        if kind == "count_equals_sql":
            items = _items(payload, check.get("path"))
            rows = _query(
                dbs[check.get("db", "synthetic")],
                check["sql"],
                _resolve_params(check.get("params", []), args),
            )
            expected = int(rows[0][0])
            return {
                "name": name,
                "pass": len(items) == expected,
                "detail": f"returned={len(items)} oracle={expected}",
            }
        if kind == "value_equals_sql":
            actual = _dotted(payload, check["path"])
            rows = _query(
                dbs[check.get("db", "synthetic")],
                check["sql"],
                _resolve_params(check.get("params", []), args),
            )
            expected = rows[0][0]
            return {
                "name": name,
                "pass": str(actual) == str(expected),
                "detail": f"actual={actual!r} oracle={expected!r}",
            }
        if kind == "children_codes_match_sql":
            actual = sorted(c["element"]["wbs_code"] for c in payload["children"])
            rows = _query(
                dbs[check.get("db", "synthetic")],
                check["sql"],
                _resolve_params(check.get("params", []), args),
            )
            expected = sorted(r[0] for r in rows)
            return {
                "name": name,
                "pass": actual == expected,
                "detail": f"returned={len(actual)} oracle={len(expected)}",
            }
        if kind == "lineage_is_root_path":
            # Expected: element first, then each dot-prefix ancestor down to the root.
            code = args["wbs_code"]
            segs = code.split(".")
            expected = [".".join(segs[: i + 1]) for i in range(len(segs))][::-1]
            actual = [e["wbs_code"] for e in payload.get("lineage", [])]
            levels = [e["level"] for e in payload.get("lineage", [])]
            ok = actual == expected and levels == list(range(len(segs), 0, -1))
            return {
                "name": name,
                "pass": ok,
                "detail": f"actual={actual} expected={expected}",
            }
        if kind == "lineage_empty_or_error":
            ok = is_error or "error" in payload or payload.get("lineage") == []
            return {"name": name, "pass": ok, "detail": error_text(payload)[:200]}
        if kind == "observe":
            # Recorded for the report; never gates a case.
            return {
                "name": name,
                "pass": True,
                "observe_only": True,
                "detail": json_short(payload),
            }
        raise ValueError(f"unknown check kind: {kind}")
    except Exception as exc:
        return {"name": name, "pass": False, "detail": f"check error: {exc!r}"}


def json_short(obj: Any, limit: int = 400) -> str:
    text = json.dumps(obj, default=str)
    return text[:limit]


# ----------------------------------------------------- per-case invariants
def dir_listing(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.stat().st_size
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


class CaseContext:
    """Shared state for one run. Holds the isolated paths and the case recorder."""

    def __init__(self, run_dir: Path, tracing: Any) -> None:
        self.run_dir = run_dir
        self.tracing = tracing
        self.results: list[dict[str, Any]] = []
        self.dbs: dict[str, Path] = {}
        self.main: Session | None = None

    def record(self, row: dict[str, Any]) -> None:
        self.results.append(row)
        with self.tracing.span(
            "pars_gap.case",
            {
                "case_id": row["case_id"],
                "tool": row["tool"],
                "status": row["status"],
            },
        ) as span:
            span.set_attributes({"checks": len(row["checks"])})
        with (self.run_dir / "results.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")


def gated(checks: list[dict]) -> list[dict]:
    return [c for c in checks if not c.get("observe_only")]


def status_of(checks: list[dict]) -> str:
    return "pass" if all(c["pass"] for c in gated(checks)) else "fail"


async def run_json_case(
    ctx: CaseContext, case: dict[str, Any], session: Session
) -> dict[str, Any]:
    dbs = {"synthetic": session.settings.database_path, **ctx.dbs}
    args = dict(case.get("args", {}))
    for key, spec in case.get("args_sql", {}).items():
        rows = _query(
            dbs[spec.get("db", "synthetic")],
            spec["sql"],
            _resolve_params(spec.get("params", []), args),
        )
        args[key] = rows[0][0]
    before_db = {k: sha256_file(v) for k, v in dbs.items()}
    started = time.perf_counter()
    payload, is_error = await session.call(case["tool"], args)
    duration = round(time.perf_counter() - started, 4)
    checks = [
        run_check(c, payload, is_error, args, dbs) for c in case.get("checks", [])
    ]
    after_db = {k: sha256_file(v) for k, v in dbs.items()}
    checks.append(
        {
            "name": "no_db_write",
            "pass": before_db == after_db,
            "detail": "synthetic and source database hashes unchanged",
        }
    )
    return {
        "case_id": case["id"],
        "tool": case["tool"],
        "kind": "json",
        "objective": case.get("objective", ""),
        "args": args,
        "status": status_of(checks),
        "checks": checks,
        "is_error": is_error,
        "response_preview": json_short(payload, 300),
        "duration_s": duration,
    }


ScenarioFn = Callable[[CaseContext], Awaitable[list[dict[str, Any]]]]


async def run_scenario(
    ctx: CaseContext, scenario_id: str, fn: ScenarioFn
) -> list[dict[str, Any]]:
    """Run a scripted scenario. Each scenario returns its own case rows."""
    dbs_before = {
        "synthetic": ctx.main.settings.database_path if ctx.main else None,
        "source": ctx.dbs["source"],
    }
    before = {k: sha256_file(v) for k, v in dbs_before.items() if v and v.exists()}
    listing_before = dir_listing(ctx.run_dir)
    started = time.perf_counter()
    rows = await fn(ctx)
    duration = round(time.perf_counter() - started, 3)
    after = {k: sha256_file(v) for k, v in dbs_before.items() if v and v.exists()}
    unchanged = before == after
    for row in rows:
        row["checks"].append(
            {
                "name": "scenario_db_unchanged",
                "pass": unchanged,
                "detail": f"{scenario_id}: synthetic and source databases unchanged",
            }
        )
        row["status"] = status_of(row["checks"])
        row["scenario_duration_s"] = duration
        row["run_dir_files_created"] = sorted(
            set(dir_listing(ctx.run_dir)) - set(listing_before)
        )[:200]
    return rows


# --------------------------------------------------------- scenario helpers
def check(name: str, ok: bool, detail: str = "", observe: bool = False) -> dict:
    row: dict[str, Any] = {"name": name, "pass": bool(ok), "detail": detail[:300]}
    if observe:
        row["observe_only"] = True
    return row


def scenario_case(
    case_id: str, tool: str, objective: str, payload: dict, is_error: bool, checks: list
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "tool": tool,
        "kind": "scenario",
        "objective": objective,
        "is_error": is_error,
        "response_preview": json_short(payload, 300),
        "checks": checks,
    }


def make_fixture(ctx: CaseContext, name: str, mutate: Callable[[Any], None]) -> Path:
    """Copy the source, then mutate the COPY only.

    The mock itself is never opened rw.
    """
    dest = ctx.run_dir / "fixtures" / f"{name}.duckdb"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ctx.dbs["source"], dest)
    con = duckdb.connect(str(dest))
    try:
        mutate(con)
    finally:
        con.close()
    return dest


# ================================================================ scenarios
def _wbs_runs(ctx: CaseContext) -> Path:
    return Path(ctx.main.settings.wbs_runs_dir)


def _sha(path: Path) -> str:
    return sha256_file(path)


async def s_chain(ctx: CaseContext) -> list[dict[str, Any]]:
    """clean -> tune_and_train -> predict (untuned, tuned) -> write_back -> status."""
    import polars as pl

    rows: list[dict[str, Any]] = []
    s = ctx.main
    assert s is not None
    runs = _wbs_runs(ctx)

    payload, err = await s.call("clean_wbs_data", {})
    rid = payload.get("run_id", "")
    ctx.state["chain_rid"] = rid
    rdir = runs / rid
    rows.append(
        scenario_case(
            "WC-CHAIN-01",
            "clean_wbs_data",
            "New run: clean stage on the synthetic mock copy.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check("stage_clean", payload.get("stage") == "clean"),
                check(
                    "origin_synthetic_mock",
                    payload.get("data_origin") == "synthetic_mock",
                    str(payload.get("data_origin")),
                ),
                check(
                    "working_copy_written_in_run_dir",
                    (rdir / "working.duckdb").is_file()
                    and (rdir / "run_manifest.json").is_file(),
                ),
                check("cleaned_rows_positive", payload.get("cleaned_spae_rows", 0) > 0),
            ],
        )
    )

    payload, err = await s.call(
        "tune_and_train_wbs",
        {
            "run_id": rid,
            "n_iter": 2,
            "cv_folds": 2,
            "n_jobs": 1,
            "search_seed": 7,
            "split_seed": 7,
        },
    )
    ctx.state["chain_tune"] = payload
    rel_dirs = payload.get("bundle_dirs") or {}
    bundles_ok = len(rel_dirs) == 2 and all(
        (rdir / p / "model_manifest.json").is_file() for p in rel_dirs.values()
    )
    rows.append(
        scenario_case(
            "WC-CHAIN-02",
            "tune_and_train_wbs",
            "Bounded real training (n_iter=2, cv_folds=2, n_jobs=1, seeds 7/7) on the "
            "run.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check(
                    "args_echoed",
                    payload.get("n_iter") == 2
                    and payload.get("cv_folds") == 2
                    and payload.get("n_jobs") == 1
                    and payload.get("search_seed") == 7
                    and payload.get("split_seed") == 7,
                ),
                check(
                    "f1_in_range",
                    0 <= float(payload.get("untuned_test_f1", -1)) <= 1
                    and 0 <= float(payload.get("tuned_test_f1", -1)) <= 1,
                ),
                check(
                    "best_params_present",
                    isinstance(payload.get("best_params"), dict)
                    and len(payload.get("best_params", {})) > 0,
                ),
                check("signed_bundles_on_disk", bundles_ok),
                check(
                    "untuned_scorer_observed",
                    True,
                    f"untuned_scorer_f1={payload.get('untuned_f1_scorer')}",
                    observe=True,
                ),
            ],
        )
    )

    payload, err = await s.call(
        "predict_wbs", {"run_id": rid, "model_variant": "untuned"}
    )
    pred_file = rdir / "predictions" / "predicted_levels.parquet"
    schema_ok = False
    if pred_file.is_file():
        cols = pl.read_parquet(pred_file).columns
        schema_ok = cols == [
            "parsid",
            "wbs",
            "original_title",
            "cleaned_title",
            "parent_wbs",
            "level_2",
            "level_3",
            "level_4",
            "level_5",
            "level_6",
            "level_7",
            "level_8",
        ]
    rows.append(
        scenario_case(
            "WC-CHAIN-03",
            "predict_wbs",
            "Inference with the untuned signed bundle; output parquet schema check.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check(
                    "predicted_rows_positive",
                    payload.get("predicted_rows", 0) > 0,
                    str(payload.get("predicted_rows")),
                ),
                check("parquet_schema", schema_ok),
                check(
                    "labels_per_level_observed",
                    True,
                    json_short(payload.get("distinct_labels_per_level")),
                    observe=True,
                ),
            ],
        )
    )

    payload, err = await s.call("write_back_wbs", {"run_id": rid})
    export = rdir / "predictions" / Path(str(payload.get("export_file", "x"))).name
    rows.append(
        scenario_case(
            "WC-CHAIN-04",
            "write_back_wbs",
            "Write-back into run working DB and parquet export; read-back verified.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check("read_back_verified", payload.get("read_back_verified") is True),
                check(
                    "all_read_back_checks_true",
                    bool(payload.get("read_back_checks"))
                    and all(payload.get("read_back_checks", {}).values()),
                ),
                check(
                    "export_present_and_hash_matches",
                    export.is_file() and _sha(export) == payload.get("export_sha256"),
                ),
                check("mapped_rows_positive", payload.get("mapped_rows", 0) > 0),
            ],
        )
    )

    payload, err = await s.call("get_wbs_run_status", {"run_id": rid})
    stages = payload.get("stages", {})
    rows.append(
        scenario_case(
            "WC-CHAIN-05",
            "get_wbs_run_status",
            "Manifest after the chain: all four stages recorded ok.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check(
                    "all_stages_ok",
                    all(
                        stages.get(k, {}).get("status") == "ok"
                        for k in ("clean", "tune_train", "predict", "write_back")
                    ),
                ),
                check("run_id_matches", payload.get("run_id") == rid),
            ],
        )
    )

    payload, err = await s.call(
        "predict_wbs", {"run_id": rid, "model_variant": "tuned"}
    )
    rows.append(
        scenario_case(
            "WC-CHAIN-06",
            "predict_wbs",
            "Inference with the tuned signed bundle (variant switch).",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check("variant_tuned", payload.get("model_variant") == "tuned"),
            ],
        )
    )
    payload, err = await s.call("write_back_wbs", {"run_id": rid})
    rows.append(
        scenario_case(
            "WC-CHAIN-07",
            "write_back_wbs",
            "Write-back after the tuned prediction re-verifies the new export.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check("read_back_verified", payload.get("read_back_verified") is True),
            ],
        )
    )
    return rows


async def s_pipeline(ctx: CaseContext) -> list[dict[str, Any]]:
    """run_wbs_pipeline end to end with the same bounded seeds as the chain."""
    s = ctx.main
    assert s is not None
    payload, err = await s.call(
        "run_wbs_pipeline",
        {
            "n_iter": 2,
            "cv_folds": 2,
            "n_jobs": 1,
            "search_seed": 7,
            "split_seed": 7,
            "model_variant": "untuned",
        },
    )
    stages = payload.get("stages", {})
    chain = ctx.state.get("chain_tune", {})
    pipe_tune = stages.get("tune_train", {})
    rid = payload.get("run_id", "")
    rows = [
        scenario_case(
            "WC-PIPE-01",
            "run_wbs_pipeline",
            "Full chain through the orchestrator with bounded training and fixed "
            "seeds.",
            payload,
            err,
            [
                check("ok", not err and "error" not in payload, error_text(payload)),
                check(
                    "four_stages",
                    set(stages) == {"clean", "tune_train", "predict", "write_back"},
                ),
                check(
                    "write_back_verified",
                    stages.get("write_back", {}).get("read_back_verified") is True,
                ),
                check(
                    "artifacts_dir_under_runs_root",
                    str(payload.get("artifacts_dir", ""))
                    .replace("\\", "/")
                    .startswith(str(_wbs_runs(ctx)).replace("\\", "/")),
                ),
            ],
        ),
        scenario_case(
            "WC-PIPE-02",
            "run_wbs_pipeline",
            "Same seeds as the direct chain give the same tuning results "
            "(reproducibility).",
            pipe_tune,
            err,
            [
                check("chain_tune_available", bool(chain)),
                check(
                    "best_params_equal_chain",
                    pipe_tune.get("best_params") == chain.get("best_params"),
                ),
                check(
                    "untuned_f1_equal_chain",
                    pipe_tune.get("untuned_test_f1") == chain.get("untuned_test_f1"),
                ),
                check(
                    "tuned_f1_equal_chain",
                    pipe_tune.get("tuned_test_f1") == chain.get("tuned_test_f1"),
                ),
            ],
        ),
    ]
    payload2, err2 = await s.call("get_wbs_run_status", {"run_id": rid})
    rows.append(
        scenario_case(
            "WC-PIPE-03",
            "get_wbs_run_status",
            "Status of the orchestrated run's manifest.",
            payload2,
            err2,
            [
                check("ok", not err2 and "error" not in payload2, error_text(payload2)),
                check(
                    "all_stages_ok",
                    all(
                        payload2.get("stages", {}).get(k, {}).get("status") == "ok"
                        for k in ("clean", "tune_train", "predict", "write_back")
                    ),
                ),
            ],
        )
    )
    return rows


async def s_refusals(ctx: CaseContext) -> list[dict[str, Any]]:
    """Invalid input is refused with a controlled error and writes no run files."""
    s = ctx.main
    assert s is not None
    runs = _wbs_runs(ctx)
    rows: list[dict[str, Any]] = []

    # A clean-only run, used for stage-order refusals.
    clean_payload, _ = await s.call("clean_wbs_data", {})
    clean_rid = clean_payload.get("run_id", "")

    cases: list[tuple[str, str, dict, str]] = [
        (
            "WC-REF-01",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "n_iter": 0},
            "n_iter must be >= 1",
        ),
        (
            "WC-REF-02",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "cv_folds": 1},
            "cv_folds must be >= 2",
        ),
        (
            "WC-REF-03",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "n_iter": 101},
            "n_iter must be <= 100",
        ),
        (
            "WC-REF-04",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "n_jobs": 0},
            "n_jobs must be -1 or between 1 and 8",
        ),
        (
            "WC-REF-05",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "n_jobs": 9},
            "n_jobs must be between -1 and 8",
        ),
        (
            "WC-REF-06",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "search_seed": -1},
            "search_seed must be between 0",
        ),
        (
            "WC-REF-07",
            "tune_and_train_wbs",
            {"run_id": "r000000000000", "split_seed": 2**32},
            "split_seed must be between 0",
        ),
        (
            "WC-REF-08",
            "tune_and_train_wbs",
            {"run_id": "r000000000000"},
            "Run not found",
        ),
        (
            "WC-REF-09",
            "tune_and_train_wbs",
            {"run_id": "../x"},
            "run_id must look like",
        ),
        ("WC-REF-10", "run_wbs_pipeline", {"n_iter": 0}, "n_iter must be >= 1"),
        (
            "WC-REF-11",
            "run_wbs_pipeline",
            {"n_jobs": 0},
            "n_jobs must be -1 or between 1 and 8",
        ),
        (
            "WC-REF-12",
            "predict_wbs",
            {"run_id": clean_rid},
            "Stage 'tune_train' has not completed",
        ),
        (
            "WC-REF-13",
            "predict_wbs",
            {"run_id": clean_rid, "model_variant": "bogus"},
            "model_variant must be one of",
        ),
        (
            "WC-REF-14",
            "write_back_wbs",
            {"run_id": clean_rid},
            "Stage 'predict' has not completed",
        ),
        ("WC-REF-15", "clean_wbs_data", {"run_id": "../x"}, "run_id must look like"),
        (
            "WC-REF-16",
            "get_wbs_run_status",
            {"run_id": "r000000000000"},
            "Run not found",
        ),
        (
            "WC-REF-17",
            "get_wbs_run_status",
            {"run_id": "../../etc"},
            "run_id must look like",
        ),
    ]
    for case_id, tool, args, expect in cases:
        before = dir_listing(runs)
        payload, err = await s.call(tool, args)
        after = dir_listing(runs)
        rows.append(
            scenario_case(
                case_id,
                tool,
                f"Refusal: {json_short(args, 120)}",
                payload,
                err,
                [
                    check(
                        "controlled_error",
                        bool(error_text(payload)) and expect in error_text(payload),
                        error_text(payload),
                    ),
                    check(
                        "no_run_files_written",
                        before == after,
                        f"files_added={sorted(set(after) - set(before))[:5]}",
                    ),
                ],
            )
        )
    return rows


async def s_tamper_and_keys(ctx: CaseContext) -> list[dict[str, Any]]:
    """Signed bundles: tampering, wrong key, and a key inside model_dir must refuse."""
    rows: list[dict[str, Any]] = []
    chain_rid = ctx.state.get("chain_rid", "")
    runs = _wbs_runs(ctx)
    chain_dir = runs / chain_rid
    pred_file = chain_dir / "predictions" / "predicted_levels.parquet"
    pred_before = _sha(pred_file) if pred_file.is_file() else "MISSING"

    # 1) Tampered bundle in a copied run: predict must refuse.
    tamp_rid = "rdeadbeef0001"
    tamp_dir = runs / tamp_rid
    if chain_dir.is_dir() and not tamp_dir.exists():
        shutil.copytree(chain_dir, tamp_dir)
        bundle = tamp_dir / "bundles" / "untuned" / "fitted_pipeline_sgd.joblib"
        with bundle.open("ab") as fh:
            fh.write(b"\x00tampered")
    tamp_pred = tamp_dir / "predictions" / "predicted_levels.parquet"
    # The copied run already holds the chain's predictions, so the check is that the
    # refused call leaves that file byte-identical, not that it is absent.
    tamp_pred_before = _sha(tamp_pred) if tamp_pred.is_file() else "MISSING"
    async with Session(
        isolated_settings(
            ctx.run_dir / "variants" / "tamper",
            ctx.run_dir,
            ctx.dbs["source"],
            runs_dir=runs,
        )
    ) as s_same:
        payload, err = await s_same.call(
            "predict_wbs", {"run_id": tamp_rid, "model_variant": "untuned"}
        )
        rows.append(
            scenario_case(
                "WC-SIG-01",
                "predict_wbs",
                "Tampered untuned bundle (bytes appended after signing) is refused.",
                payload,
                err,
                [
                    check(
                        "refused",
                        bool(error_text(payload)) and "predicted_rows" not in payload,
                        error_text(payload),
                    ),
                    check(
                        "predictions_file_unchanged_by_refused_call",
                        (_sha(tamp_pred) if tamp_pred.is_file() else "MISSING")
                        == tamp_pred_before,
                    ),
                ],
            )
        )

    # 2) Wrong key: the chain run was signed with the main key, not this one.
    async with Session(
        isolated_settings(
            ctx.run_dir / "variants" / "wrong_key",
            ctx.run_dir,
            ctx.dbs["source"],
            runs_dir=runs,
        )
    ) as s_wrong:
        payload, err = await s_wrong.call(
            "predict_wbs", {"run_id": chain_rid, "model_variant": "untuned"}
        )
        rows.append(
            scenario_case(
                "WC-SIG-02",
                "predict_wbs",
                "Bundle signed with a different key (fresh key file) is refused.",
                payload,
                err,
                [
                    check(
                        "refused",
                        bool(error_text(payload)) and "predicted_rows" not in payload,
                        error_text(payload),
                    ),
                    check(
                        "chain_predictions_unchanged",
                        (_sha(pred_file) if pred_file.is_file() else "MISSING")
                        == pred_before,
                    ),
                ],
            )
        )

    # 3) Key path inside model_dir: the server's guard must refuse before any work.
    variant = ctx.run_dir / "variants" / "key_in_models"
    models = variant / "models"
    key_in = models / "model_signing.key"
    async with Session(
        isolated_settings(
            variant,
            ctx.run_dir,
            ctx.dbs["source"],
            model_dir=models,
            key_path=key_in,
            runs_dir=runs,
        )
    ) as s_guard:
        payload, err = await s_guard.call(
            "predict_wbs", {"run_id": chain_rid, "model_variant": "untuned"}
        )
        rows.append(
            scenario_case(
                "WC-SIG-03",
                "predict_wbs",
                "Signing key inside model_dir is refused by the server guard.",
                payload,
                err,
                [
                    check(
                        "refused",
                        bool(error_text(payload)) and "predicted_rows" not in payload,
                        error_text(payload),
                    ),
                    check("no_key_created_in_model_dir", not key_in.exists()),
                ],
            )
        )
    return rows


async def s_fixtures(ctx: CaseContext) -> list[dict[str, Any]]:
    """Contract violations and non-synthetic origins, on fixture COPIES only."""
    rows: list[dict[str, Any]] = []

    def drop_gold(con):
        con.execute("DROP TABLE gold_corrections")

    def bad_level(con):
        con.execute(
            "UPDATE silver_spae_data SET wbs_level = 'x' "
            "WHERE parsid IN (SELECT parsid FROM silver_spae_data LIMIT 1)"
        )

    def no_marker(con):
        con.execute("DROP TABLE _mock_marker")

    fx_missing = make_fixture(ctx, "missing_table", drop_gold)
    fx_level = make_fixture(ctx, "bad_wbs_level", bad_level)
    fx_origin = make_fixture(ctx, "unknown_origin", no_marker)

    async with Session(
        isolated_settings(
            ctx.run_dir / "variants" / "fx_missing", ctx.run_dir, fx_missing
        )
    ) as session:
        payload, err = await session.call("validate_wbs_inputs", {})
        rows.append(
            scenario_case(
                "FX-01",
                "validate_wbs_inputs",
                "Source missing gold_corrections: validation reports a contract "
                "violation.",
                payload,
                err,
                [
                    check("ok_false", payload.get("ok") is False),
                    check(
                        "names_missing_table",
                        "missing table: gold_corrections"
                        in payload.get("problems", []),
                        json_short(payload.get("problems")),
                    ),
                ],
            )
        )
        runs_dir = Path(session.settings.wbs_runs_dir)
        before_runs = dir_listing(runs_dir)
        payload, err = await session.call("clean_wbs_data", {})
        after_runs = dir_listing(runs_dir)
        rows.append(
            scenario_case(
                "FX-02",
                "clean_wbs_data",
                "Clean refuses a source that fails the input contract (no manifest "
                "written).",
                payload,
                err,
                [
                    check(
                        "refused",
                        "fails the WBS input contract" in error_text(payload),
                        error_text(payload),
                    ),
                    check(
                        "no_manifest_written",
                        not any(k.endswith("run_manifest.json") for k in after_runs),
                    ),
                    check(
                        "observe_run_dir_created_before_contract_check",
                        True,
                        f"new_files={sorted(set(after_runs) - set(before_runs))[:4]}",
                        observe=True,
                    ),
                ],
            )
        )
        payload, err = await session.call("get_wbs_rows", {"limit": 2})
        rows.append(
            scenario_case(
                "FX-03",
                "get_wbs_rows",
                "Source missing gold_corrections: origin still synthetic, read tool is "
                "not blocked by contract.",
                payload,
                err,
                [
                    check(
                        "observe_only",
                        True,
                        error_text(payload) or json_short(payload, 120),
                        observe=True,
                    )
                ],
            )
        )

    async with Session(
        isolated_settings(
            ctx.run_dir / "variants" / "fx_bad_level", ctx.run_dir, fx_level
        )
    ) as session:
        payload, err = await session.call("validate_wbs_inputs", {})
        rows.append(
            scenario_case(
                "FX-04",
                "validate_wbs_inputs",
                "Non-integer wbs_level values: validation reports a contract "
                "violation.",
                payload,
                err,
                [
                    check("ok_false", payload.get("ok") is False),
                    check(
                        "reports_wbs_level",
                        any(
                            "wbs_level" in p and "not integers" in p
                            for p in payload.get("problems", [])
                        ),
                        json_short(payload.get("problems"), 200),
                    ),
                ],
            )
        )

    async with Session(
        isolated_settings(
            ctx.run_dir / "variants" / "fx_unknown_origin", ctx.run_dir, fx_origin
        )
    ) as session:
        payload, err = await session.call("get_wbs_rows", {"limit": 2})
        rows.append(
            scenario_case(
                "FX-05",
                "get_wbs_rows",
                "Source without a synthetic marker: rows must be refused.",
                payload,
                err,
                [
                    check(
                        "refused",
                        "documented synthetic data" in error_text(payload),
                        error_text(payload),
                    ),
                    check("no_rows_returned", "rows" not in payload),
                ],
            )
        )
        payload, err = await session.call("get_wbs_project_descriptions", {"limit": 2})
        rows.append(
            scenario_case(
                "FX-06",
                "get_wbs_project_descriptions",
                "Source without a synthetic marker: descriptions must be refused.",
                payload,
                err,
                [
                    check(
                        "refused",
                        "documented synthetic data" in error_text(payload),
                        error_text(payload),
                    ),
                    check("no_rows_returned", "rows" not in payload),
                ],
            )
        )
        payload, err = await session.call("validate_wbs_inputs", {})
        rows.append(
            scenario_case(
                "FX-07",
                "validate_wbs_inputs",
                "Unknown origin is reported as data_origin=unknown.",
                payload,
                err,
                [
                    check(
                        "origin_unknown",
                        payload.get("data_origin") == "unknown",
                        str(payload.get("data_origin")),
                    )
                ],
            )
        )
    return rows


async def s_caef_fixture(ctx: CaseContext) -> list[dict[str, Any]]:
    """CAEF-compatible labeled test fixture (wbs_port.contract_fixture), built from
    verified copies.

    The CAEF file is copied and hash-checked first, so the protected CAEF file is never
    passed to the builder. The fixture is a separate origin ("labeled_test_fixture"),
    not the synthetic mock. Results are reported as PARS tool behaviour on that fixture.
    """
    from pars_local_mcp.wbs_port.contract_fixture import build_contract_fixture

    rows: list[dict[str, Any]] = []
    caef_src = (
        REPO_ROOT / "src" / "pars_local_mcp" / "data" / "caef_synthetic_labeled.duckdb"
    )
    caef_copy = ctx.run_dir / "caef_src" / "caef_synthetic_labeled.duckdb"
    caef_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(caef_src, caef_copy)
    copy_ok = sha256_file(caef_copy) == CAEF_SOURCE_SHA256
    fixture = ctx.run_dir / "fixtures" / "caef_labeled_test_fixture.duckdb"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    if fixture.exists():
        fixture.unlink()
    build_contract_fixture(fixture, caef_db=caef_copy, mock_db=ctx.dbs["source"])
    built = fixture.is_file()
    rows.append(
        scenario_case(
            "CAEF-00",
            "contract_fixture (builder)",
            "Build the CAEF-compatible labeled fixture from a hash-verified copy of "
            "the CAEF file.",
            {},
            False,
            [
                check("caef_copy_hash_matches_recorded", copy_ok),
                check("fixture_built", built, str(fixture.name)),
            ],
        )
    )

    variant = ctx.run_dir / "variants" / "caef_fixture"
    async with Session(isolated_settings(variant, ctx.run_dir, fixture)) as s:
        payload, err = await s.call("validate_wbs_inputs", {})
        rows.append(
            scenario_case(
                "CAEF-01",
                "validate_wbs_inputs",
                "Labeled fixture passes the input contract and reports its own origin.",
                payload,
                err,
                [
                    check(
                        "ok",
                        payload.get("ok") is True,
                        json_short(payload.get("problems")),
                    ),
                    check(
                        "origin_labeled_fixture",
                        payload.get("data_origin") == "labeled_test_fixture",
                        str(payload.get("data_origin")),
                    ),
                ],
            )
        )
        payload, err = await s.call("get_wbs_rows", {"limit": 2})
        rows.append(
            scenario_case(
                "CAEF-02",
                "get_wbs_rows",
                "Origin labeled_test_fixture is one of the documented synthetic "
                "origins.",
                payload,
                err,
                [
                    check(
                        "returned_two",
                        payload.get("returned") == 2,
                        error_text(payload) or str(payload.get("returned")),
                    )
                ],
            )
        )
        payload, err = await s.call("clean_wbs_data", {})
        rid = payload.get("run_id", "")
        rows.append(
            scenario_case(
                "CAEF-03",
                "clean_wbs_data",
                "Clean stage on the labeled fixture.",
                payload,
                err,
                [
                    check(
                        "ok", not err and "error" not in payload, error_text(payload)
                    ),
                    check(
                        "origin_labeled_fixture",
                        payload.get("data_origin") == "labeled_test_fixture",
                    ),
                    check(
                        "cleaned_rows_positive",
                        payload.get("cleaned_sample_rows", 0) > 0,
                    ),
                ],
            )
        )
        payload, err = await s.call(
            "tune_and_train_wbs",
            {
                "run_id": rid,
                "n_iter": 2,
                "cv_folds": 2,
                "n_jobs": 1,
                "search_seed": 7,
                "split_seed": 7,
            },
        )
        bdirs = payload.get("bundle_dirs") or {}
        rdir = Path(s.settings.wbs_runs_dir) / rid
        rows.append(
            scenario_case(
                "CAEF-04",
                "tune_and_train_wbs",
                "Bounded training on the labeled fixture (n_iter=2, cv_folds=2, "
                "n_jobs=1).",
                payload,
                err,
                [
                    check(
                        "ok", not err and "error" not in payload, error_text(payload)
                    ),
                    check(
                        "f1_in_range",
                        0 <= float(payload.get("untuned_test_f1", -1)) <= 1
                        and 0 <= float(payload.get("tuned_test_f1", -1)) <= 1,
                    ),
                    check(
                        "signed_bundles_on_disk",
                        len(bdirs) == 2
                        and all(
                            (rdir / p / "model_manifest.json").is_file()
                            for p in bdirs.values()
                        ),
                    ),
                ],
            )
        )
        payload, err = await s.call(
            "predict_wbs", {"run_id": rid, "model_variant": "untuned"}
        )
        rows.append(
            scenario_case(
                "CAEF-05",
                "predict_wbs",
                "Inference with the untuned bundle trained on the labeled fixture.",
                payload,
                err,
                [
                    check(
                        "ok", not err and "error" not in payload, error_text(payload)
                    ),
                    check(
                        "predicted_rows_positive", payload.get("predicted_rows", 0) > 0
                    ),
                ],
            )
        )
        payload, err = await s.call("write_back_wbs", {"run_id": rid})
        rows.append(
            scenario_case(
                "CAEF-06",
                "write_back_wbs",
                "Write-back on the labeled fixture run, read-back verified.",
                payload,
                err,
                [
                    check(
                        "ok", not err and "error" not in payload, error_text(payload)
                    ),
                    check(
                        "read_back_verified", payload.get("read_back_verified") is True
                    ),
                ],
            )
        )
        payload, err = await s.call("get_wbs_run_status", {"run_id": rid})
        stages = payload.get("stages", {})
        rows.append(
            scenario_case(
                "CAEF-07",
                "get_wbs_run_status",
                "Manifest of the labeled-fixture run.",
                payload,
                err,
                [
                    check(
                        "all_stages_ok",
                        all(
                            stages.get(k, {}).get("status") == "ok"
                            for k in ("clean", "tune_train", "predict", "write_back")
                        ),
                    )
                ],
            )
        )
    return rows


# ================================================================ main
def _load_cases() -> list[dict[str, Any]]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return data["cases"]


async def amain(args: argparse.Namespace) -> int:
    run_id = args.run_id or "pars-gap-" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    run_dir = GAP_ROOT / "runs" / run_id
    if run_dir.exists():
        raise SystemExit(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    started_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    tracing = setup_tracing(
        "pars-eval-gap", run_dir / "traces.jsonl", enabled=not args.no_phoenix
    )
    ctx = CaseContext(run_dir, tracing)
    ctx.state = {}

    before = snapshot_protected()
    (run_dir / "integrity_before.json").write_text(
        json.dumps(before, indent=1), encoding="utf-8"
    )

    source = run_dir / "source" / "mock_pars_full_copy.duckdb"
    source.parent.mkdir(parents=True)
    shutil.copyfile(MOCK_SOURCE, source)
    if sha256_file(source) != before["src/pars_local_mcp/data/mock_pars_full.duckdb"]:
        raise SystemExit("source copy hash does not match the protected mock")
    ctx.dbs["source"] = source

    cases = _load_cases()
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["tool"] in wanted]

    main_settings = isolated_settings(run_dir / "main", run_dir, source)
    if args.mode == "snapshot":
        # Serve a disposable copy of the frozen snapshot; oracles read the snapshot
        # itself.
        if sha256_file(SNAPSHOT_PATH) != SNAPSHOT_SHA256:
            raise SystemExit(
                "snapshot hash does not match the recorded snapshot checksum"
            )
        served = main_settings.database_path
        served.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SNAPSHOT_PATH, served)
        ctx.dbs["synthetic"] = SNAPSHOT_PATH
        ctx.dbs["served"] = served
        init = False
    else:
        ctx.dbs["synthetic"] = main_settings.database_path
        init = True
    # Belt and braces: export the isolated paths so any child process inherits them.
    # The Settings above already pass every path explicitly, which takes precedence.
    env_guard = {}
    for env_key, field in PARS_ENV_KEYS.items():
        value = str(getattr(main_settings, field))
        if not value.lower().startswith(str(run_dir.resolve()).lower()):
            raise SystemExit(f"isolation: {env_key} is outside the run directory")
        os.environ[env_key] = value
        env_guard[env_key] = value
    run_meta = {
        "mode": args.mode,
        "snapshot_sha256": SNAPSHOT_SHA256 if args.mode == "snapshot" else None,
        "pars_env": env_guard,
    }
    (run_dir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=1), encoding="utf-8"
    )
    async with Session(main_settings, initialize=init) as session:
        ctx.main = session
        tools = await session.tools()
        names = sorted(t.name for t in tools)
        inventory = [
            {
                "name": t.name,
                "description": ((t.description or "").strip().splitlines() or [""])[0][
                    :200
                ],
                "input_schema": t.inputSchema,
            }
            for t in sorted(tools, key=lambda t: t.name)
        ]
        (run_dir / "tool_inventory.json").write_text(
            json.dumps(inventory, indent=1), encoding="utf-8"
        )
        allowed = json.loads(
            (REPO_ROOT / "src" / "mcp_servers.json").read_text(encoding="utf-8")
        )["servers"]["pars_mcp"]["allowed_tools"]
        reg_row = {
            "case_id": "REG-01",
            "tool": "registry",
            "kind": "registry",
            "objective": "Registered tools equal mcp_servers.json allowed_tools; 16 "
            "tools in total.",
            "checks": [
                check("16_registered", len(names) == 16, str(len(names))),
                check(
                    "matches_allowed_tools",
                    names == sorted(allowed),
                    f"allowed={len(allowed)}",
                ),
                check("matches_expected_names", names == sorted(ALL_TOOLS)),
            ],
        }
        reg_row["status"] = status_of(reg_row["checks"])
        ctx.record(reg_row)

        for case in cases:
            ctx.record(await run_json_case(ctx, case, session))

        if not args.skip_scenarios:
            for sid, fn in [
                ("refusals", s_refusals),
                ("chain", s_chain),
                ("pipeline", s_pipeline),
                ("tamper_and_keys", s_tamper_and_keys),
                ("fixtures", s_fixtures),
                ("caef_labeled_fixture", s_caef_fixture),
            ]:
                for row in await run_scenario(ctx, sid, fn):
                    ctx.record(row)

    after = snapshot_protected()
    (run_dir / "integrity_after.json").write_text(
        json.dumps(after, indent=1), encoding="utf-8"
    )
    diff = diff_snapshots(before, after)
    protected_ok = not diff["changed"] and not diff["removed"]

    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    summary = {
        "run_id": run_id,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": len(results),
        "status_counts": by_status,
        "protected_files_unchanged": protected_ok,
        "protected_diff": diff,
        "trace_destination": tracing.destination,
        "phoenix_reachable": tracing.backend == "phoenix",
        "run_dir": str(run_dir),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    return 0 if protected_ok and by_status.get("fail", 0) == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="PARS 16-tool isolated evaluation")
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--only", default="", help="comma-separated tool names for JSON cases"
    )
    parser.add_argument(
        "--mode",
        choices=["snapshot", "generated"],
        default="snapshot",
        help="snapshot: serve a disposable copy of the frozen snapshot (default); "
        "generated: create_server() initializes a fresh synthetic database",
    )
    parser.add_argument("--skip-scenarios", action="store_true")
    parser.add_argument("--no-phoenix", action="store_true", help="force JSONL tracing")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(amain(args)))


if __name__ == "__main__":
    main()
