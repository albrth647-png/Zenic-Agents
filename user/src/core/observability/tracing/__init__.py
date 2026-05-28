"""
ZENIC-AGENTS v16 - Distributed Tracing (Phase 5)

OpenTelemetry-compatible tracing with Jaeger/OTLP export.
Provides request-level and operation-level tracing with
correlation IDs that flow through the entire pipeline.
"""

from ._config import TracingConfig, get_tracer, init_tracing
from ._context import (
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    inject_trace_context,
    trace_span,
)

__all__ = [
    "TracingConfig",
    "extract_trace_context",
    "get_current_span_id",
    "get_current_trace_id",
    "get_tracer",
    "init_tracing",
    "inject_trace_context",
    "trace_span",
]
