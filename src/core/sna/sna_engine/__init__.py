"""Re-exports for sna_engine package."""

import asyncio
import logging
import time

__all__ = ["asyncio", "logging", "time"]


def get_sna_engine() -> SNAEngine:  # noqa: F821  # TODO: verify import
    """Get or create the global SNAEngine instance."""  # TODO: verify import
    global _default_engine
    if _default_engine is None:
        _default_engine = SNAEngine()  # noqa: F821  # TODO: Phase3 - verify import
    return _default_engine


def reset_sna_engine() -> None:
    """Reset the global SNAEngine (for testing)."""  # TODO: verify import
    global _default_engine
    _default_engine = None
