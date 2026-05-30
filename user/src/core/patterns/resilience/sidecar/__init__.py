"""sidecar - refactored into sub-modules."""

from ._core import Sidecar, sidecar_decorator
from ._types import _MiddlewareContext

__all__ = ["Sidecar", "_MiddlewareContext", "sidecar_decorator"]
