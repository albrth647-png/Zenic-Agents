"""
ZENIC-AGENTS - Structural Pattern: Bridge

Decouples agent LLM usage from the concrete provider implementation.
Supports hot-swapping providers at runtime.

Designed for resource-constrained environments (Android/Termux, 500MB RAM).
"""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


# ======================================================================
# Provider ABC
# ======================================================================

class LLMProvider(ABC):
    """
    Abstract base for LLM providers.

    Concrete providers implement:
      - complete(prompt, **kwargs) -> str
      - embed(text) -> List[float]
      - is_ready() -> bool
    """

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion for *prompt*."""
        ...

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text*."""
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if the provider is ready for requests."""
        ...


# ======================================================================
# Concrete providers
# ======================================================================

class LocalProvider(LLMProvider):
    """
    Provider backed by a local llama-cpp-python engine.

    Wraps any object that exposes:
      - ``generate(prompt, **kwargs) -> str``
      - ``embed(text) -> List[float]``   (optional)
      - ``is_loaded -> bool``
    """

    def __init__(self, engine: Any = None) -> None:
        self._engine = engine

    def complete(self, prompt: str, **kwargs: Any) -> str:
        if not self.is_ready():
            raise RuntimeError("LocalProvider: engine not loaded")
        try:
            result = self._engine.generate(prompt, **kwargs)
            return result if isinstance(result, str) else str(result)
        except AttributeError:
            # Fallback: try __call__ or _call_llm
            if hasattr(self._engine, "_call_llm"):
                result = self._engine._call_llm(prompt, **kwargs)
                return result if isinstance(result, str) else str(result)
            raise RuntimeError("LocalProvider: engine has no generate/_call_llm method")

    def embed(self, text: str) -> list[float]:
        if not self.is_ready():
            raise RuntimeError("LocalProvider: engine not loaded")
        if hasattr(self._engine, "embed"):
            return self._engine.embed(text)
        # Fallback: simple hash-based pseudo-embedding (deterministic)
        logger.warning("LocalProvider: engine has no embed(), using hash fallback")
        return self._pseudo_embed(text)

    def is_ready(self) -> bool:
        if self._engine is None:
            return False
        if hasattr(self._engine, "is_loaded"):
            return bool(self._engine.is_loaded)
        return True

    @staticmethod
    def _pseudo_embed(text: str, dim: int = 64) -> list[float]:
        """Deterministic hash-based pseudo-embedding (not for semantic use)."""
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        vec = []
        for i in range(0, min(len(h), dim * 2), 2):
            vec.append(int(h[i:i + 2], 16) / 255.0)
        # Pad or truncate
        while len(vec) < dim:
            vec.append(0.0)
        return vec[:dim]


class AgentLLMBridge:
    """
    Bridge that decouples an agent from its LLM provider.

    Supports hot-swapping the provider at runtime so agents can switch
    between providers without restart.

    Usage::

        bridge = AgentLLMBridge(LocalProvider(engine))
        result = bridge.complete("Hello")
        bridge.switch_provider(LocalProvider(another_engine))
        result2 = bridge.complete("Hello again")
    """

    def __init__(self, provider: LLMProvider) -> None:
        if not isinstance(provider, LLMProvider):
            raise ValueError("AgentLLMBridge: provider must be an LLMProvider")
        self._provider = provider
        self._lock = threading.Lock()
        self._switch_count = 0

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate a completion via the current provider.

        Args:
            prompt: Input text.
            **kwargs: Provider-specific options.

        Returns:
            Generated text.

        Raises:
            RuntimeError: If the current provider fails.
        """
        with self._lock:
            provider = self._provider
        return provider.complete(prompt, **kwargs)

    def embed(self, text: str) -> list[float]:
        """Generate an embedding via the current provider."""
        with self._lock:
            provider = self._provider
        return provider.embed(text)

    # ------------------------------------------------------------------
    # Hot-swap
    # ------------------------------------------------------------------

    def switch_provider(self, new_provider: LLMProvider) -> None:
        """
        Hot-swap the underlying provider.

        The switch is atomic — concurrent calls will see either the old
        or the new provider, never an inconsistent state.

        Args:
            new_provider: The replacement :class:`LLMProvider`.

        Raises:
            ValueError: If *new_provider* is not an LLMProvider.
        """
        if not isinstance(new_provider, LLMProvider):
            raise ValueError("AgentLLMBridge: new_provider must be an LLMProvider")
        with self._lock:
            old_name = type(self._provider).__name__
            self._provider = new_provider
            self._switch_count += 1
        logger.info(
            "AgentLLMBridge: switched provider %s → %s (switch #%d)",
            old_name,
            type(new_provider).__name__,
            self._switch_count,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def current_provider(self) -> LLMProvider:
        """Return the currently active provider."""
        with self._lock:
            return self._provider

    @property
    def stats(self) -> dict[str, Any]:
        """Return bridge statistics."""
        with self._lock:
            return {
                "provider": type(self._provider).__name__,
                "provider_ready": self._provider.is_ready(),
                "switch_count": self._switch_count,
            }
