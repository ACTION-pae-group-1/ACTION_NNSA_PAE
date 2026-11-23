
@echo off
setlocal
cd /d "%~dp0.."

set "PATH=%CD%\.venv\Scripts;%PATH%"
set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "FASTMCP=%CD%\.venv\Scripts\fastmcp.exe"

if not exist "%PYTHON%" (
    echo ERROR: Project virtual environment not found.
    echo Run: uv sync
    exit /b 1
)

if not exist "%FASTMCP%" (
    echo ERROR: FastMCP is not installed in the project environment.
    echo Check the project dependencies and run: uv sync
    exit /b 1
)

echo Starting Cost Intelligence FastMCP App...
echo MCP server: http://127.0.0.1:8000
echo App preview: http://127.0.0.1:8080

"%FASTMCP%" dev apps src/cost_intel_app/server.py:mcp --reload --host 127.0.0.1

endlocal
