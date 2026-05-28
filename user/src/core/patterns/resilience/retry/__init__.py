"""
ZENIC-AGENTS - Retry Pattern v16

Comprehensive retry with exponential/linear/fixed backoff, jitter,
and on_retry callbacks. Designed for Android/Termux (500MB RAM) — stdlib only.

Backoff strategies:
    exponential : delay = base_delay * (exponential_base ** (attempt - 1))
    linear      : delay = base_delay * attempt
    fixed       : delay = base_delay

Jitter: random.uniform(0, jitter_max * current_delay) added when jitter=True.
"""

from ._config import RetryConfig
from ._programmatic import with_config_retry, with_retry, with_retry_async
from ._scope import RetryScope, retry, retry_async

__all__ = [
    "RetryConfig",
    "RetryScope",
    "retry",
    "retry_async",
    "with_config_retry",
    "with_retry",
    "with_retry_async",
]
