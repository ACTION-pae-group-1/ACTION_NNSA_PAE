"""Verify the Poe check runner's reporting without running the checks."""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_checks.py"
SPEC = importlib.util.spec_from_file_location("run_checks", SCRIPT)
assert SPEC is not None and SPEC.loader is not None

runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_check_runner_reports_each_success() -> None:
    output = io.StringIO()
    total = len(runner.CHECKS)

    run_results = [subprocess.CompletedProcess([], 0) for _ in runner.CHECKS]

    with patch.object(
        runner.subprocess,
        "run",
        side_effect=run_results,
    ) as invoked:
        with redirect_stdout(output):
            assert runner.main() == 0

    assert invoked.call_count == total

    for number, task in enumerate(runner.CHECKS, start=1):
        assert f"[check {number}/{total}] PASS {task}" in output.getvalue()

    assert f"PASS: all {total} checks completed" in output.getvalue()

    for call, task in zip(
        invoked.call_args_list,
        runner.CHECKS,
        strict=True,
    ):
        assert call.args[0] == [
            sys.executable,
            "-m",
            "poethepoet",
            task,
        ]
        assert call.kwargs["cwd"] == runner.PROJECT_ROOT


def test_check_runner_identifies_formatting_failure() -> None:
    output = io.StringIO()
    errors = io.StringIO()

    total = len(runner.CHECKS)
    failure_index = runner.CHECKS.index("format-check")

    results = [
        subprocess.CompletedProcess(
            [],
            1 if index == failure_index else 0,
        )
        for index in range(failure_index + 1)
    ]

    with patch.object(
        runner.subprocess,
        "run",
        side_effect=results,
    ) as invoked:
        with redirect_stdout(output), redirect_stderr(errors):
            assert runner.main() == 1

    assert invoked.call_count == failure_index + 1

    for index, task in enumerate(runner.CHECKS[:failure_index]):
        assert f"[check {index + 1}/{total}] PASS {task}" in output.getvalue()

    assert (
        f"[check {failure_index + 1}/{total}] FAILED format-check (exit code 1)"
    ) in errors.getvalue()

    assert "uv run --locked poe format" in errors.getvalue()
    assert "Remaining checks were not run" in errors.getvalue()


def test_check_runner_preserves_failed_step_exit_code() -> None:
    errors = io.StringIO()

    total = len(runner.CHECKS)
    failure_index = runner.CHECKS.index("test")

    results = [
        subprocess.CompletedProcess(
            [],
            2 if index == failure_index else 0,
        )
        for index in range(failure_index + 1)
    ]

    with patch.object(
        runner.subprocess,
        "run",
        side_effect=results,
    ) as invoked:
        with redirect_stdout(io.StringIO()), redirect_stderr(errors):
            assert runner.main() == 2

    assert invoked.call_count == failure_index + 1

    assert (
        f"[check {failure_index + 1}/{total}] FAILED test (exit code 2)"
    ) in errors.getvalue()

    assert "Remaining checks were not run" in errors.getvalue()


def test_check_runner_reports_launch_errors() -> None:
    errors = io.StringIO()

    first_task = runner.CHECKS[0]

    with patch.object(
        runner.subprocess,
        "run",
        side_effect=OSError("not found"),
    ) as invoked:
        with redirect_stdout(io.StringIO()), redirect_stderr(errors):
            assert runner.main() == 1

    assert invoked.call_count == 1
    assert (f"FAILED {first_task}: could not launch: not found") in errors.getvalue()


@pytest.mark.parametrize("failed_task", runner.CHECKS)
def test_check_runner_stops_at_each_failed_stage(
    failed_task: str,
) -> None:
    """Every stage must stop execution and preserve its failure code."""
    output = io.StringIO()
    errors = io.StringIO()

    total = len(runner.CHECKS)
    failure_index = runner.CHECKS.index(failed_task)

    results = [
        subprocess.CompletedProcess(
            [],
            3 if index == failure_index else 0,
        )
        for index in range(failure_index + 1)
    ]

    with patch.object(
        runner.subprocess,
        "run",
        side_effect=results,
    ) as invoked:
        with redirect_stdout(output), redirect_stderr(errors):
            assert runner.main() == 3

    assert invoked.call_count == failure_index + 1

    assert (
        f"[check {failure_index + 1}/{total}] FAILED {failed_task} (exit code 3)"
    ) in errors.getvalue()

    assert "Remaining checks were not run" in errors.getvalue()
