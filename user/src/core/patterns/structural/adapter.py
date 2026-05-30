"""
ZENIC-AGENTS - Structural Pattern: Adapter

Unified adapter layer for different LLM backends.
Supports local (llama-cpp) and fallback chains.

Designed for resource-constrained environments (Android/Termux, 500MB RAM).
"""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


# ======================================================================
# Abstract base
# ======================================================================


class LLMAdapter(ABC):
    """
    Abstract base class for LLM adapters.

    Every adapter must implement:
      - generate(prompt, **kwargs) -> str
      - is_available() -> bool
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate a completion for *prompt*.

        Args:
            prompt: The input text / prompt.
            **kwargs: Backend-specific options (temperature, max_tokens, …).

        Returns:
            The generated text string.

        Raises:
            RuntimeError: If generation fails.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backing LLM is reachable / loaded."""
        ...


# ======================================================================
# Concrete adapters
# ======================================================================


class LocalLLMAdapter(LLMAdapter):
    """
    Adapter that wraps a :class:`MiniAIEngine` instance's ``_call_llm``
    method for local inference.

    Falls back to a simple echo if MiniAIEngine is unavailable.
    """

    def __init__(self, engine: Any = None) -> None:
        """
        Args:
            engine: A MiniAIEngine instance (or any object with a
                    ``_call_llm(prompt, **kwargs)`` method).
        """
        self._engine = engine

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.is_available():
            raise RuntimeError("LocalLLMAdapter: engine not available")
        try:
            result = self._engine._call_llm(prompt, **kwargs)
            if isinstance(result, str):
                return result
            # Some engines return dicts
            if isinstance(result, dict):
                return result.get("text", result.get("content", str(result)))
            return str(result)
        except Exception as exc:
            logger.error("LocalLLMAdapter: generation failed – %s", exc)
            raise RuntimeError(f"LocalLLMAdapter: generation failed – {exc}") from exc

    def is_available(self) -> bool:
        return self._engine is not None and hasattr(self._engine, "_call_llm")


class FallbackLLMAdapter(LLMAdapter):
    """
    Adapter that tries a *primary* adapter first and falls back to a
    *secondary* adapter on failure or unavailability.
    """

    def __init__(
        self,
        primary: LLMAdapter,
        secondary: LLMAdapter,
        fallback_on_unavailable: bool = True,
    ) -> None:
        """
        Args:
            primary: Preferred adapter.
            secondary: Fallback adapter.
            fallback_on_unavailable: If True, also fall back when primary
                                     reports ``is_available() == False``.
        """
        if not isinstance(primary, LLMAdapter):
            raise ValueError("FallbackLLMAdapter: primary must be an LLMAdapter")
        if not isinstance(secondary, LLMAdapter):
            raise ValueError("FallbackLLMAdapter: secondary must be an LLMAdapter")
        self._primary = primary
        self._secondary = secondary
        self._fallback_on_unavailable = fallback_on_unavailable
        self._primary_calls = 0
        self._secondary_calls = 0

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if self._fallback_on_unavailable and not self._primary.is_available():
            logger.debug("FallbackLLMAdapter: primary unavailable, using secondary")
            self._secondary_calls += 1
            return self._secondary.generate(prompt, **kwargs)

        try:
            self._primary_calls += 1
            return self._primary.generate(prompt, **kwargs)
        except Exception as exc:
            logger.warning("FallbackLLMAdapter: primary failed (%s), using secondary", exc)
            self._secondary_calls += 1
            return self._secondary.generate(prompt, **kwargs)

    def is_available(self) -> bool:
        return self._primary.is_available() or self._secondary.is_available()

    @property
    def stats(self) -> dict[str, int]:
        """Return call counts for primary and secondary adapters."""
        return {
            "primary_calls": self._primary_calls,
            "secondary_calls": self._secondary_calls,
        }


# ======================================================================
# Adapter Registry
# ======================================================================


class AdapterRegistry:
    """
    Thread-safe registry for named :class:`LLMAdapter` instances.

    Usage::

        reg = AdapterRegistry()
        reg.register("local", local_adapter)
        adapter = reg.get("local")
        names = reg.get_available()
    """

    def __init__(self) -> None:
        self._adapters: dict[str, LLMAdapter] = {}
        self._lock = threading.RLock()

    def register(self, name: str, adapter: LLMAdapter) -> None:
        """
        Register an adapter under *name*.

        Args:
            name: Unique identifier.
            adapter: An :class:`LLMAdapter` instance.

        Raises:
            ValueError: If *name* is empty or *adapter* is not an LLMAdapter.
        """
        if not name:
            raise ValueError("AdapterRegistry: name must be a non-empty string")
        if not isinstance(adapter, LLMAdapter):
            raise ValueError("AdapterRegistry: adapter must be an LLMAdapter instance")
        with self._lock:
            self._adapters[name] = adapter
            logger.debug("AdapterRegistry: registered adapter '%s'", name)

    def get(self, name: str) -> LLMAdapter:
        """
        Retrieve an adapter by name.

        Raises:
            KeyError: If *name* is not registered.
        """
        with self._lock:
            adapter = self._adapters.get(name)
        if adapter is None:
            raise KeyError(f"AdapterRegistry: no adapter registered as '{name}'")
        return adapter

    def get_available(self) -> list[str]:
        """Return a sorted list of names whose adapters report ``is_available()``."""
        with self._lock:
            return sorted(name for name, adapter in self._adapters.items() if adapter.is_available())
