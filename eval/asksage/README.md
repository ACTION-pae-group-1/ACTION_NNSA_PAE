# Ask Sage MCP evaluations

Run from the repository root. The scripts use `src/portable_llm_mcp/.env`
for Ask Sage settings, `eval/asksage/mcp_servers_test.json` for the read-only
BLS MCP tool allowlist, and `MCP_PYTHON` for the stdio child interpreter.
The root `.env` configures the BLS server's snapshot registry and transport.
The default MCP registry is resolved relative to the evaluation scripts, not
the shell working directory. `MCP_SERVERS_FILE` is optional and overrides the
default when set. The multi-model runner also accepts `--server-config`, which
takes precedence over `MCP_SERVERS_FILE`. A missing selected registry causes
an immediate error with the attempted path.

The scripts **do not load `.env` automatically**. Launching them directly with
`.venv\Scripts\python.exe` can silently select the default Ollama provider.
Both scripts now fail before starting MCP or writing results unless the provider
is `asksage` and the endpoint hostname is `api.nnsa.asksage.ai`.

PowerShell setup (run from the repository root):

```powershell
$env:MCP_PYTHON = (uv run python -c "import sys; print(sys.executable)")
Remove-Item Env:PORT,Env:DATABRICKS_APP_PORT -ErrorAction SilentlyContinue
uv run --env-file src/portable_llm_mcp/.env --with truststore --with httpx python eval/asksage/test_asksage_mcp.py
uv run --env-file src/portable_llm_mcp/.env --with truststore --with httpx python eval/asksage/eval_asksage_mcp.py --models gpt-5.4-gov gpt-5.6-luna-gov --cases steel
```

If a previous session still points to the old root-level registry, clear it:

```powershell
Remove-Item Env:MCP_SERVERS_FILE -ErrorAction SilentlyContinue
```

To use a custom registry instead, set `MCP_SERVERS_FILE` to an existing JSON
file or pass `--server-config path/to/registry.json` to the evaluation runner.
Relative override paths are resolved from the current working directory; the
bundled default is always resolved from `eval/asksage/`.

The runner writes CSV summaries and JSONL tool traces to `eval/asksage/results/`.
Those traces may contain internal catalog metadata. They are ignored by git.
The runner records observational metrics, not verified correctness scores.

Windows TLS: `truststore.inject_into_ssl()` runs before creating the HTTP client.
This uses trusted Windows CAs, including an approved enterprise CA if installed.
Never disable TLS verification. `LLM_API_KEY` must have OpenAI-compatible
passthrough authorization. `LLM_CHAT_MODEL` selects the single-model smoke test;
`--models` selects the evaluation models. The test MCP registry is separate from
`src/mcp_servers.json` and limits tool exposure to catalog lookup tools.

If startup hangs, verify that the root `.env` does not request HTTP transport,
that `MCP_PYTHON` points to the correct environment, and that `PORT` and
`DATABRICKS_APP_PORT` are unset. A standalone stdio server should not need a port.

Before running the evaluation, confirm the active provider without printing secrets:

```powershell
uv run --env-file src/portable_llm_mcp/.env python -c "import os; print(os.getenv('LLM_PROVIDER'), os.getenv('LLM_CHAT_MODEL'))"
```

Expected provider: `asksage`. If you see `ollama`, check the `.env` path and
use the `uv run --env-file ...` commands above. The model list supplied through
`--models` does **not** change the provider or load credentials. Discard any
results collected under the wrong provider.
