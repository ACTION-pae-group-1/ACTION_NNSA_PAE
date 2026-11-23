# Deploying an MCP server from this repository

Local development runs a server over **stdio** (how Claude Desktop and Claude
Code launch it). To share one with an agent platform, deploy it to a host that
serves it over **streamable-HTTP**, then register it.

## Current status

The deployment kits here come from the upstream template, and they still target
the template's `example_server`, which now lives in
`src/templates/example_server/`. As shipped, the root `Dockerfile`, the root
`manifest.yaml` (cloud.gov) and `ibm/local-mcp-toolkit/` look for
`example_server` directly under `src/`, so each needs its path updated before it
works. **None of them deploys the BLS server (`bls_mcp`) yet**; see
[Deploying the BLS server](#deploying-the-bls-server) for what that takes.

The upstream template also had a Databricks kit. It is not included in this
repository.

## Kits in this repository

| Target | Kits | Transport | When to use |
|---|---|---|---|
| **IBM watsonx Orchestrate** | [`ibm/`](ibm/) (3 kits) | stdio (local) **or** streamable-HTTP (Code Engine) | You're building agents in watsonx Orchestrate |
| **cloud.gov** | root `manifest.yaml` (not a full kit) | streamable-HTTP | Cloud Foundry, with `cf push` after `cf login` and `cf target` |

### IBM (three options, lowest to highest overhead)

See [`ibm/README.md`](ibm/README.md) for the full chooser. In short:

1. **[`ibm/local-mcp-toolkit/`](ibm/local-mcp-toolkit/)**: ship the code and run
   it over stdio **inside** Orchestrate. No HTTP, no container, no registry.
   **Lowest overhead.** Its register script copies `src/${PACKAGE_NAME}`;
   `PACKAGE_NAME` defaults to `example_server`.
2. **[`ibm/code-engine-git-build/`](ibm/code-engine-git-build/)**: Code Engine
   builds the root `Dockerfile` from your Git repo and pushes to your Container
   Registry. Needs registry authority.
3. **[`ibm/prebuilt-image/`](ibm/prebuilt-image/)**: deploy a prebuilt public
   image to Code Engine. Lowest cloud authority.

## How transport is chosen

Both the template server and `bls_mcp` (`src/bls_mcp/app.py`) pick their
transport the same way:

- a platform port (`DATABRICKS_APP_PORT` or `PORT`): **HTTP** on `0.0.0.0` at
  that port;
- `MCP_TRANSPORT=streamable-http`: HTTP on `MCP_HOST:MCP_PORT`;
- otherwise: **stdio**.

Hosts that inject a port (IBM Code Engine, the `Dockerfile`'s `PORT=8080`) get
HTTP with `/mcp` and `/health`. `bls_mcp` also serves `/version` and `/ui`.

## Deploying the BLS server

`bls_mcp` needs more than the template server, because its tools read a
published DuckDB snapshot:

- **Entry point:** `python -m bls_mcp.app` (or the `bls-server` script).
- **A published, active snapshot** in the directory named by
  `BLS_SNAPSHOT_REGISTRY_DIR`. Build it with `uv run --locked poe
  sample-snapshot` or the full pipeline in `docs/bls/OPERATIONS.md`, then bake
  it into the image or mount it as a volume. The server won't start without it.
- **`BLS_SPECS_DB_PATH`:** a writable location for saved index specifications.
- **Optional `BLS_API_KEY`:** only for the opt-in live tool `get_series_data`.
  Pass it as a secret, never in the image.

Check a running HTTP server with `uv run --locked poe smoke`, which makes no
BLS requests. `.env.example` lists the common settings, and
`src/bls_mcp/config.py` has the rest.

---

## Security reminder

The kits expose the MCP endpoint with **no authentication** by default. That
matches a public-data hackathon posture. For anything beyond a hackathon, put
the endpoint behind authentication and review your agency's ATO requirements.
Never commit secrets: each kit's `.env` is git-ignored and holds coordinates only.
