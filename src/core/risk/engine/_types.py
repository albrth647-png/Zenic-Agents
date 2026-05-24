"""Types and constants for engine."""

from __future__ import annotations

import logging

try:
    from ...native._risk import (  # noqa: F401
        calculate_blast_radius,
        find_critical_path,
        multi_node_blast_radius,
        propagate_risks,
    )

    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

logger = logging.getLogger("zenic_agents.core.risk.engine")
__all__ = ["logger"]
