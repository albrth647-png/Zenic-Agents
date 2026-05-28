"""
ZENIC-AGENTS - Architectural Patterns Facade

Re-exports the public API of the architectural pattern sub-package.
"""

from src.core.patterns.architectural.cqrs import (
    Command,
    CommandHandler,
    CQRSBus,
    Query,
    QueryHandler,
)

__all__ = [
    "CQRSBus",
    "Command",
    "CommandHandler",
    "Query",
    "QueryHandler",
]
