"""Structural Patterns — AgentLLMBridge, AgentCapability, AgentDecorator archived (unused).
Files preserved in _archived/agents/patterns/.
"""

from .adapter import (
    AdapterRegistry,
    FallbackLLMAdapter,
    LLMAdapter,
    LocalLLMAdapter,
)
from .proxy import CacheProxy, LazyProxy

__all__ = [
    "AdapterRegistry",
    "CacheProxy",
    "FallbackLLMAdapter",
    "LLMAdapter",
    "LazyProxy",
    "LocalLLMAdapter",
]
