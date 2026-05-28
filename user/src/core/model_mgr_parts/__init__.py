"""
ZENIC-AGENTS - Model Manager v16 (Hybrid Lazy Loading + Auto-Unload)

Gestor de modelos que maximiza el rendimiento en el Redmi 12R Pro:
- Lazy Loading: Los modelos solo se cargan cuando se necesitan
- Auto-Unload: Los modelos se descargan tras N minutos de inactividad
- RAM Budget: Control estricto de memoria para no quemar el telefono
- Model Swap: Carga/descarga dinamica segun demanda
"""

from ._imports import ENABLE_AUTO_UNLOAD, ENABLE_LAZY_LOAD, IDLE_TIMEOUT_S, RAM_BUDGET_MB
from .manager import ModelManager
from .singleton import get_model_manager, init_model_manager

__all__ = [
    "ENABLE_AUTO_UNLOAD",
    "ENABLE_LAZY_LOAD",
    "IDLE_TIMEOUT_S",
    "RAM_BUDGET_MB",
    "ModelManager",
    "get_model_manager",
    "init_model_manager",
]
