@echo off
rem One-time Windows bootstrap for this checkout. Idempotent: safe to rerun.
rem Covers QUICKSTART.md "Before you start" and steps 1-3, plus the
rem one-time config-file copies that step 6 and the dev workflow need.
rem Does not touch certificate trust settings; see scripts\build_ca_bundle.ps1
rem and the "Corporate TLS inspection" item in QUICKSTART.md for that.
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo === 1. Checking for uv ===
where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: uv is not on PATH. Install it first:
    echo     pip install uv
    echo Then open a new terminal and rerun this script.
    exit /b 1
)
uv --version

echo.
echo === 2. Installing dependencies (uv sync --locked) ===
uv sync --locked
if errorlevel 1 (
    echo.
    echo uv sync failed. If the error mentions
    echo "invalid peer certificate: UnknownIssuer", your network inspects
    echo HTTPS traffic. Run this, then rerun this script:
    echo     set "UV_SYSTEM_CERTS=true"
    echo     set "UV_NATIVE_TLS=true"
    exit /b 1
)

echo.
echo === 3. Config files ===
if exist ".env" (
    echo .env already exists, leaving it as is.
) else (
    copy /y .env.example .env >nul
    echo Created .env from .env.example.
)

if exist "src\portable_llm_mcp\.env" (
    echo src\portable_llm_mcp\.env already exists, leaving it as is.
) else (
    copy /y src\portable_llm_mcp\.env.example src\portable_llm_mcp\.env >nul
    echo Created src\portable_llm_mcp\.env from its .env.example.
)

if exist ".vscode\settings.json" (
    echo .vscode\settings.json already exists, leaving it as is.
) else (
    if exist ".vscode\.gitkeep" (
        copy /y .vscode\.gitkeep .vscode\settings.json >nul
        echo Created .vscode\settings.json from the tracked template.
    ) else (
        echo .vscode\.gitkeep not found; skipping VS Code settings.
    )
)

echo.
echo === 4. BLS sample database ===
if exist "data\local\snapshots" (
    echo data\local\snapshots already exists; skipping sample-snapshot build.
    echo To rebuild from scratch, delete data\local and rerun this script.
) else (
    uv run --locked poe sample-snapshot
    if errorlevel 1 (
        echo poe sample-snapshot failed; see the output above.
        exit /b 1
    )
)

echo.
echo === 5. Verifying the BLS server (poe verify) ===
uv run --locked poe verify
if errorlevel 1 (
    echo poe verify failed; see the output above.
    exit /b 1
)

echo.
echo === 6. PARS CAEF reference workbook ===
if exist "src\pars_local_mcp\data\CAEF 2.0 Standard WBS.xlsx" (
    echo CAEF reference workbook found.
) else (
    echo CAEF reference workbook MISSING: src\pars_local_mcp\data\CAEF 2.0 Standard WBS.xlsx
    echo Obtain the authorized local copy before running the PARS WBS modeling steps.
)

echo.
echo === Setup complete ===
echo Next: "uv run --locked bls-server" to run the BLS MCP server, or see
echo QUICKSTART.md for the FastMCP App preview and PARS WBS modeling steps.

endlocal
