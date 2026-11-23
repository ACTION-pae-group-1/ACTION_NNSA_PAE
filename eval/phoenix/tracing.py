"""Tracing for the PARS eval: Phoenix when available, otherwise a local JSONL file.

Phoenix is used only when all of these hold:
  * tracing is enabled,
  * the Phoenix endpoint is a loopback address (traces carry queries and answers,
    so they are never shipped off the machine),
  * the endpoint answers a short health probe,
  * phoenix.otel imports and register() succeeds.
If any check fails, spans are appended to a JSONL file instead and the reason is
kept on Tracing.fallback_reason, so a run always says where its traces went.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import urlsplit

DEFAULT_PHOENIX_URL = "http://localhost:6006"
PROBE_TIMEOUT_S = 1.0
_LOOPBACK_NAMES = {"localhost"}


def phoenix_base_url() -> str:
    """Phoenix base URL from the environment, defaulting to the local server."""
    url = (
        os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        or os.getenv("PHOENIX_ENDPOINT")
        or DEFAULT_PHOENIX_URL
    )
    return url.rstrip("/")


def is_loopback(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return False
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def default_probe(url: str, timeout: float) -> bool:
    """True if Phoenix answers its health check. Only ever called for loopback URLs."""
    try:
        with urllib.request.urlopen(f"{url}/healthz", timeout=timeout) as resp:
            return resp.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except (OSError, ValueError):
        return False


def _import_register() -> Callable[..., Any]:
    from phoenix.otel import register

    return register


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _otel_value(value: Any) -> Any:
    """Coerce to a type OpenTelemetry accepts as an attribute value."""
    if value is None:
        return ""
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        items = list(value)
        if all(isinstance(v, str) for v in items):
            return items
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in items):
            return items
    return json.dumps(_json_safe(value), sort_keys=True)


class _JsonlSpan:
    def __init__(self, name: str, attributes: Mapping[str, Any] | None) -> None:
        self.name = name
        self.attributes: dict[str, Any] = dict(attributes or {})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, attributes: Mapping[str, Any]) -> None:
        self.attributes.update(attributes)


class _OtelSpan:
    def __init__(self, span: Any) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, _otel_value(value))

    def set_attributes(self, attributes: Mapping[str, Any]) -> None:
        for key, value in attributes.items():
            self.set_attribute(key, value)


@dataclass
class Tracing:
    backend: str  # "phoenix" or "jsonl"
    project: str
    jsonl_path: Path | None = None
    fallback_reason: str = ""
    endpoint: str = ""
    _provider: Any = None
    _tracer: Any = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None
    ) -> Iterator[_JsonlSpan | _OtelSpan]:
        if self.backend == "phoenix":
            with self._phoenix_span(name, attributes) as span:
                yield span
        else:
            with self._jsonl_span(name, attributes) as span:
                yield span

    @contextmanager
    def _phoenix_span(
        self, name: str, attributes: Mapping[str, Any] | None
    ) -> Iterator[_OtelSpan]:
        with self._tracer.start_as_current_span(name) as raw:
            span = _OtelSpan(raw)
            span.set_attributes(attributes or {})
            try:
                yield span
            except BaseException as exc:
                raw.record_exception(exc)
                span.set_attribute("error", f"{type(exc).__name__}: {exc}")
                raise

    @contextmanager
    def _jsonl_span(
        self, name: str, attributes: Mapping[str, Any] | None
    ) -> Iterator[_JsonlSpan]:
        span = _JsonlSpan(name, attributes)
        start_time, started = _now(), time.perf_counter()
        status, error = "ok", ""
        try:
            yield span
        except BaseException as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._write(
                {
                    "trace_id": uuid.uuid4().hex,
                    "span_id": secrets.token_hex(8),
                    "project": self.project,
                    "name": name,
                    "start_time": start_time,
                    "end_time": _now(),
                    "duration_s": round(time.perf_counter() - started, 6),
                    "status": status,
                    "error": error,
                    "attributes": _json_safe(span.attributes),
                }
            )

    def _write(self, record: dict) -> None:
        assert self.jsonl_path is not None
        line = json.dumps(record, ensure_ascii=False, allow_nan=False)
        with self._lock:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def shutdown(self) -> None:
        """Flush Phoenix spans. Never raises: a tracing failure must not fail a run."""
        if self._provider is None:
            return
        try:
            self._provider.shutdown()
        except Exception:
            pass

    @property
    def destination(self) -> str:
        if self.backend == "phoenix":
            return f"phoenix @ {self.endpoint}"
        return f"jsonl @ {self.jsonl_path} ({self.fallback_reason})"


def setup_tracing(
    project_name: str,
    jsonl_path: str | Path,
    *,
    endpoint: str | None = None,
    enabled: bool = True,
    register_fn: Callable[..., Any] | None = None,
    probe_fn: Callable[[str, float], bool] | None = None,
) -> Tracing:
    """Return a Phoenix-backed Tracing if possible, else a JSONL-backed one."""
    path = Path(jsonl_path)
    base = (endpoint or phoenix_base_url()).rstrip("/")

    def fallback(reason: str) -> Tracing:
        return Tracing(
            backend="jsonl",
            project=project_name,
            jsonl_path=path,
            fallback_reason=reason,
            endpoint=base,
        )

    if not enabled:
        return fallback("phoenix disabled")
    if not is_loopback(base):
        return fallback(f"phoenix endpoint {base} is not a loopback address")

    probe = probe_fn or default_probe
    try:
        reachable = probe(base, PROBE_TIMEOUT_S)
    except Exception as exc:
        return fallback(f"phoenix probe failed: {type(exc).__name__}: {exc}")
    if not reachable:
        return fallback(f"phoenix unreachable at {base}")

    try:
        register = register_fn or _import_register()
        provider = register(
            endpoint=f"{base}/v1/traces",
            project_name=project_name,
            set_global_tracer_provider=False,
            batch=True,
            verbose=False,
        )
        tracer = provider.get_tracer("pars_eval")
    except Exception as exc:
        return fallback(f"phoenix setup failed: {type(exc).__name__}: {exc}")

    return Tracing(
        backend="phoenix",
        project=project_name,
        endpoint=base,
        _provider=provider,
        _tracer=tracer,
    )
