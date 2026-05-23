"""
ZENIC-AGENTS - Structural Patterns Facade

Re-exports the public API of the structural pattern sub-package.
"""

from src.core.patterns.structural.adapter import (
    LLMAdapter,
    LocalLLMAdapter,
    FallbackLLMAdapter,
    AdapterRegistry,
)
from src.core.patterns.structural.bridge import (
    LLMProvider,
    LocalProvider,
    AgentLLMBridge,
)
from src.core.patterns.structural.proxy import LazyProxy, CacheProxy
from src.core.patterns.structural.decorator import (
    agent_decorator,
    AgentCapability,
    AgentDecorator,
)

__all__ = [
    # Adapter
    "LLMAdapter",
    "LocalLLMAdapter",
    "FallbackLLMAdapter",
    "AdapterRegistry",
    # Bridge
    "LLMProvider",
    "LocalProvider",
    "AgentLLMBridge",
    # Proxy
    "LazyProxy",
    "CacheProxy",
    # Decorator
    "agent_decorator",
    "AgentCapability",
    "AgentDecorator",
]
