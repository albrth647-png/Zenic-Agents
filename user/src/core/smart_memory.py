"""
ZENIC-AGENTS - SmartMemory (Intelligent Memory for Qwen)

Thin facade that re-exports from the modularized memory_parts sub-package.
All implementation has been moved to:
  - memory_parts/types.py      — MemoryEntry dataclass + constants
  - memory_parts/database.py   — DB initialization, migration, connections mixin
  - memory_parts/cache.py      — Semantic cache + working memory mixin
  - memory_parts/longterm.py   — Long-term memory + similarity search mixin
  - memory_parts/episodes.py   — Episodes, patterns, projects mixin
  - memory_parts/memory.py     — SmartMemory class (combines all mixins)
"""

from .memory_parts import (
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
    SmartMemory,
    logger,
)

__all__ = [
    "DB_DIR",
    "DB_PATH",
    "HAS_NUMPY",
    "IMPORTANCE_THRESHOLD",
    "MAX_COMPRESSED_TOKENS",
    "MAX_EPISODIC_ENTRIES",
    "MAX_LONG_TERM_ENTRIES",
    "MAX_PROCEDURAL_ENTRIES",
    "MAX_PROJECT_ENTRIES",
    "MAX_WORKING_ENTRIES",
    "SEMANTIC_CACHE_THRESHOLD",
    "MemoryEntry",
    "SmartMemory",
    "logger",
]
