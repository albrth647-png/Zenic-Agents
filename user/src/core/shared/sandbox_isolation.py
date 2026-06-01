"""
Zenic-Agents — Sandbox Isolation (Facade) [DEPRECATED]

⚠️ DEPRECATED: El sandbox esta deprecado desde Fase 6.
sandbox_parts/ no existe en disco y no se va a implementar.

Esta fachada solo retorna stubs y emite advertencias.
Se mantiene por compatibilidad con imports existentes.
En una version futura se eliminara por completo.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

logger = logging.getLogger(__name__)

warnings.warn(
    "Sandbox isolation is deprecated. "
    "sandbox_parts/ is not available and will not be implemented. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from .sandbox_parts import (  # type: ignore[import-unresolved]
        SandboxIsolationManager,
        SandboxWorkspace,
        create_sandbox_builtins,
        create_sandbox_globals,
        get_isolation_manager,
        shutdown_isolation,
    )
except ImportError:
    logger.warning("sandbox_parts not available — using stub implementations")

    class SandboxWorkspace:  # type: ignore[no-redef]
        """Stub SandboxWorkspace when sandbox_parts is not available."""

        def __init__(self, **kwargs: Any) -> None: ...
        def isolate(self, *args: Any, **kwargs: Any) -> Any:
            return {}

    class SandboxIsolationManager:  # type: ignore[no-redef]
        """Stub SandboxIsolationManager when sandbox_parts is not available."""

        def __init__(self, **kwargs: Any) -> None: ...
        def create_workspace(self, *args: Any, **kwargs: Any) -> SandboxWorkspace:
            return SandboxWorkspace()

    def get_isolation_manager() -> SandboxIsolationManager:  # type: ignore[misc]
        return SandboxIsolationManager()

    def shutdown_isolation() -> None:  # type: ignore[misc]
        pass

    def create_sandbox_builtins() -> dict[str, Any]:  # type: ignore[misc]
        return {}

    def create_sandbox_globals() -> dict[str, Any]:  # type: ignore[misc]
        return {}


__all__ = [
    "SandboxIsolationManager",
    "SandboxWorkspace",
    "create_sandbox_builtins",
    "create_sandbox_globals",
    "get_isolation_manager",
    "shutdown_isolation",
]
