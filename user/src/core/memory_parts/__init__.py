"""
ZENIC-AGENTS - SmartMemory Sub-package

Re-exports all public symbols from the modularized SmartMemory components.
"""

from .cache import CacheMixin
from .database import DatabaseMixin
from .episodes import EpisodesMixin
from .longterm import LongTermMixin
from .memory import SmartMemory
from .types import (
    DB_DIR,
    DB_PATH,
    HAS_NUMPY,
    IMPORTANCE_THRESHOLD,
    MAX_COMPRESSED_TOKENS,
    MAX_EPISODIC_ENTRIES,
    MAX_LONG_TERM_ENTRIES,
    MAX_PROCEDURAL_ENTRIES,
    MAX_PROJECT_ENTRIES,
    MAX_WORKING_ENTRIES,
    SEMANTIC_CACHE_THRESHOLD,
    MemoryEntry,
    logger,
)

__all__ = [
    # Constants
    "DB_DIR",
    "DB_PATH",
    # Module-level flags
    "HAS_NUMPY",
    "IMPORTANCE_THRESHOLD",
    "MAX_COMPRESSED_TOKENS",
    "MAX_EPISODIC_ENTRIES",
    "MAX_LONG_TERM_ENTRIES",
    "MAX_PROCEDURAL_ENTRIES",
    "MAX_PROJECT_ENTRIES",
    "MAX_WORKING_ENTRIES",
    "SEMANTIC_CACHE_THRESHOLD",
    "CacheMixin",
    # Mixins
    "DatabaseMixin",
    "EpisodesMixin",
    "LongTermMixin",
    # Data types
    "MemoryEntry",
    # Main class
    "SmartMemory",
    # Logger
    "logger",
]
