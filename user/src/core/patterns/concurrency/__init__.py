"""
ZENIC-AGENTS - Concurrency Patterns Facade

Re-exports the public API of the concurrency pattern sub-package.
"""

from src.core.patterns.concurrency.producer_consumer import ProducerConsumer
from src.core.patterns.concurrency.read_write_lock import ReadWriteLock
from src.core.patterns.concurrency.worker_pool import WorkerPool, WorkerPoolConfig

__all__ = [
    "ProducerConsumer",
    "ReadWriteLock",
    "WorkerPool",
    "WorkerPoolConfig",
]
