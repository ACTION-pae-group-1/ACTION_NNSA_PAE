> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# mcp_server_config

# `fastmcp.utilities.mcp_server_config.v1.mcp_server_config`

FastMCP Configuration File Support.

This module provides support for fastmcp.json configuration files that allow
users to specify server settings in a declarative format instead of using
command-line arguments.

## Functions

### `generate_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L416](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L416)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_schema(output_path: Path | str | None = None) -> dict[str, Any] | None
```

Generate JSON schema for fastmcp.json files.

This is used to create the schema file that IDEs can use for
validation and auto-completion.

**Args:**

* `output_path`: Optional path to write the schema to. If provided,
  writes the schema and returns None. If not provided,
  returns the schema as a dictionary.

**Returns:**

* JSON schema as a dictionary if output\_path is None, otherwise None

## Classes

### `Deployment` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L36](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L36)</sup>

Configuration for server deployment and runtime settings.

**Methods:**

#### `apply_runtime_settings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L85](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L85)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
apply_runtime_settings(self, config_path: Path | None = None) -> None
```

Apply runtime settings like environment variables and working directory.

**Args:**

* `config_path`: Path to config file for resolving relative paths

Environment variables support interpolation with ${VAR_NAME} syntax.
For example: "API_URL": "https://api.${ENVIRONMENT}.example.com"
will substitute the value of the ENVIRONMENT variable at runtime.

### `MCPServerConfig` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L134](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L134)</sup>

Configuration for a FastMCP server.

This configuration file allows you to specify all settings needed to run
a FastMCP server in a declarative format.

**Methods:**

#### `validate_source` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L183](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L183)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_source(cls, v: dict | Source) -> SourceType
```

Validate and convert source to proper format.

Supports:

* Dict format: `{"path": "server.py", "entrypoint": "app"}`
* FileSystemSource instance (passed through)

No string parsing happens here - that's only at CLI boundaries.
MCPServerConfig works only with properly typed objects.

#### `validate_environment` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L199](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L199)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_environment(cls, v: dict | Any) -> EnvironmentType
```

Ensure environment has a type field for discrimination.

For backward compatibility, if no type is specified, default to "uv".

#### `validate_deployment` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L210](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L210)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_deployment(cls, v: dict | Deployment) -> Deployment
```

Validate and convert deployment to Deployment.

Accepts:

* Deployment instance
* dict that can be converted to Deployment

#### `from_file` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L223](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L223)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_file(cls, file_path: Path) -> MCPServerConfig
```

Load configuration from a JSON file.

**Args:**

* `file_path`: Path to the configuration file

**Returns:**

* MCPServerConfig instance

**Raises:**

* `FileNotFoundError`: If the file doesn't exist
* `json.JSONDecodeError`: If the file is not valid JSON
* `pydantic.ValidationError`: If the configuration is invalid

#### `from_cli_args` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L246](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L246)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_cli_args(cls, source: FileSystemSource, transport: Literal['stdio', 'http', 'sse', 'streamable-http'] | None = None, host: str | None = None, port: int | None = None, path: str | None = None, log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] | None = None, python: str | None = None, dependencies: list[str] | None = None, requirements: str | None = None, project: str | None = None, editable: str | None = None, env: dict[str, str] | None = None, cwd: str | None = None, args: list[str] | None = None) -> MCPServerConfig
```

Create a config from CLI arguments.

This allows us to have a single code path where everything
goes through a config object.

**Args:**

* `source`: Server source (FileSystemSource instance)
* `transport`: Transport protocol
* `host`: Host for HTTP transport
* `port`: Port for HTTP transport
* `path`: URL path for server
* `log_level`: Logging level
* `python`: Python version
* `dependencies`: Python packages to install
* `requirements`: Path to requirements file
* `project`: Path to project directory
* `editable`: Path to install in editable mode
* `env`: Environment variables
* `cwd`: Working directory
* `args`: Server arguments

**Returns:**

* MCPServerConfig instance

#### `find_config` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L323](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L323)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
find_config(cls, start_path: Path | None = None) -> Path | None
```

Find a fastmcp.json file in the specified directory.

**Args:**

* `start_path`: Directory to look in (defaults to current directory)

**Returns:**

* Path to the configuration file, or None if not found

#### `prepare` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L342](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L342)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prepare(self, skip_source: bool = False, output_dir: Path | None = None) -> None
```

Prepare environment and source for execution.

When output\_dir is provided, creates a persistent uv project.
When output\_dir is None, does ephemeral caching (for backwards compatibility).

**Args:**

* `skip_source`: Skip source preparation if True
* `output_dir`: Directory to create the persistent uv project in (optional)

#### `prepare_environment` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L363](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L363)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prepare_environment(self, output_dir: Path | None = None) -> None
```

Prepare the Python environment.

**Args:**

* `output_dir`: If provided, creates a persistent uv project in this directory.
  If None, just populates uv's cache for ephemeral use.

Delegates to the environment's prepare() method

#### `prepare_source` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L374](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L374)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prepare_source(self) -> None
```

Prepare the source for loading.

Delegates to the source's prepare() method.

#### `run_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/mcp\_server\_config.py#L381](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py#L381)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run_server(self, **kwargs: Any) -> None
```

Load and run the server with this configuration.

**Args:**

* `**kwargs`: Additional arguments to pass to server.run\_async()
  These override config settings


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.