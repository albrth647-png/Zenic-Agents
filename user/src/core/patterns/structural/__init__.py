"""
ZENIC-AGENTS - Structural Patterns Facade

Re-exports the public API of the structural pattern sub-package.
"""

from src.core.patterns.structural.adapter import (
    AdapterRegistry,
    FallbackLLMAdapter,
    LLMAdapter,
    LocalLLMAdapter,
)
from src.core.patterns.structural.bridge import (
    AgentLLMBridge,
    LLMProvider,
    LocalProvider,
)
from src.core.patterns.structural.decorator import (
    AgentCapability,
    AgentDecorator,
    agent_decorator,
)
from src.core.patterns.structural.proxy import CacheProxy, LazyProxy

__all__ = [
    "AdapterRegistry",
    "AgentCapability",
    "AgentDecorator",
    "AgentLLMBridge",
    "CacheProxy",
    "FallbackLLMAdapter",
    # Adapter
    "LLMAdapter",
    # Bridge
    "LLMProvider",
    # Proxy
    "LazyProxy",
    "LocalLLMAdapter",
    "LocalProvider",
    # Decorator
    "agent_decorator",
]
