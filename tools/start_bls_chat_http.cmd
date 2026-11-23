@echo off
rem Start the BLS MCP service for NNSA Search on loopback HTTP only.
rem
rem This runs the unmodified bls_mcp code. It is a separate application-level
rem service for chat (src\cost_intel_app\chat_mcp_servers.json). It does not
rem change the evaluated stdio launch in src\mcp_servers.json.
rem
rem Run from any folder. Stop with Ctrl+C in this window.

setlocal
cd /d "%~dp0.."

rem Keep bytecode out of the protected source directories.
set PYTHONDONTWRITEBYTECODE=1

rem Loopback HTTP on a fixed port; the chat manifest expects this URL.
set MCP_TRANSPORT=streamable-http
set MCP_HOST=127.0.0.1
set MCP_PORT=8821

rem Platform port variables override the transport settings; clear them.
set PORT=
set DATABRICKS_APP_PORT=

rem Keep the specs database under data\local, not in the repository root.
set BLS_SPECS_DB_PATH=data\local\bls_specs_chat.duckdb

rem The packaged sample snapshot registry. Set here so a fresh checkout does not
rem depend on a local .env file (the root .env is not tracked).
set BLS_SNAPSHOT_REGISTRY_DIR=data\local\snapshots

if not exist ".venv\Scripts\python.exe" (
  echo The project virtual environment is missing. See docs\CHAT_COMPETITION_QUICKSTART.md for setup.
  exit /b 1
)

if not exist "data\local\snapshots\active-snapshot.json" (
  echo The BLS sample snapshot registry is missing: data\local\snapshots\active-snapshot.json
  echo It is packaged with the repository. Check that the file is present in your checkout.
  exit /b 1
)

echo Starting BLS chat service at http://127.0.0.1:8821/mcp
".venv\Scripts\python.exe" -m bls_mcp.app
