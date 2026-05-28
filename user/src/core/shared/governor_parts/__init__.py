"""
ZENIC-AGENTS - Resource Governor v16 (Termux/proot-distro)

Monitor y limitador de recursos para que el engine no chupe
todos los recursos del telefono.
"""

from .governor import ResourceGovernor
from .singleton import get_governor, init_governor
from .utils import limit_open_files, set_process_priority_low, tune_gc_for_arm

__all__ = [
    "ResourceGovernor",
    "get_governor",
    "init_governor",
    "limit_open_files",
    "set_process_priority_low",
    "tune_gc_for_arm",
]
