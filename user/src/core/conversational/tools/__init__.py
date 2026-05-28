"""
Sistema de herramientas del Asistente.

Registro, ejecucion y permisos para las tools
que el asistente puede invocar, con ToolManager
como orquestador unificado de Fase 2.
"""

from .executor import ToolExecutor
from .manager import ToolManager
from .permissions import PermissionManager
from .registry import ToolRegistry

__all__ = [
    "PermissionManager",
    "ToolExecutor",
    "ToolManager",
    "ToolRegistry",
]
