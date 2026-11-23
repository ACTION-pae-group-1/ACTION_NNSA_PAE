"""Opt-in, metadata-only OTLP tracing for BLS evaluation episodes.

No prompt, response, tool arguments, result bodies, or credentials are exported.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

_provider: TracerProvider | None = None


def enabled() -> bool:
    return os.getenv("BLS_EVAL_PHOENIX_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def configure() -> None:
    """Configure an independent provider; never replace the global provider."""
    global _provider
    if not enabled() or _provider is not None:
        return
    endpoint = os.getenv("BLS_EVAL_PHOENIX_ENDPOINT", "http://127.0.0.1:6006/v1/traces")
    project = os.getenv("BLS_EVAL_PHOENIX_PROJECT", "bls-mcp-evals")
    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": project, "openinference.project.name": project}
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, timeout=3))
    )
    _provider = provider


def shutdown() -> None:
    global _provider
    if _provider is not None:
        _provider.shutdown()
        _provider = None


@contextmanager
def span(name: str, **attributes: str | int | bool) -> Iterator[Span | None]:
    if _provider is None:
        yield None
        return
    with _provider.get_tracer("eval.bls").start_as_current_span(
        name, attributes=attributes
    ) as current:
        yield current


def trace_id(current: Span | None) -> str | None:
    if current is None:
        return None
    context = current.get_span_context()
    return f"{context.trace_id:032x}" if context.is_valid else None
