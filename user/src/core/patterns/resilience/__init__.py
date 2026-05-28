"""
ZENIC-AGENTS - Resilience Patterns v16

Facade module — re-exports all resilience pattern components
from sub-modules for convenient single-point imports.

Usage::

    from src.core.patterns.resilience import (
        CircuitBreaker, CircuitState, CircuitOpenError,
        RetryConfig, retry, retry_async, with_retry,
        Bulkhead, BulkheadFullError,
        Sidecar, sidecar_decorator,
    )

Designed for Android/Termux (500MB RAM) — stdlib only.
"""

from .bulkhead import Bulkhead, BulkheadFullError
from .circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from .retry import RetryConfig, RetryScope, retry, retry_async, with_retry, with_retry_async
from .sidecar import Sidecar, sidecar_decorator

__all__ = [
    # Bulkhead
    "Bulkhead",
    "BulkheadFullError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    # Retry
    "RetryConfig",
    "RetryScope",
    # Sidecar
    "Sidecar",
    "retry",
    "retry_async",
    "sidecar_decorator",
    "with_retry",
    "with_retry_async",
]
