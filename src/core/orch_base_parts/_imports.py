"""
Shared imports and constants for orch_base_parts sub-modules.
"""

import logging


# Level 5 & 6 modules removed in v3.0.0 integrity sweep
try:
    from src.core.level5_structural_swarm.scrap_agent import GitHubScrapAgent  # type: ignore[import-unresolved]
    from src.core.level5_structural_swarm.ast_surgeon import ASTSurgeon  # type: ignore[import-unresolved]
except ImportError:
    GitHubScrapAgent = None  # type: ignore[misc,assignment]
    ASTSurgeon = None  # type: ignore[misc,assignment]

try:
    from src.core.level6_reflexion_sandbox.executor import ReflexionSandbox  # type: ignore[import-unresolved]
except ImportError:
    ReflexionSandbox = None  # type: ignore[misc,assignment]


# Decomposed modules

# AbortiveProtocol — module doesn't exist yet in v3.0.0
try:
    from src.core.abortive_protocol import AbortiveProtocol  # type: ignore[import-unresolved]
except ImportError:
    AbortiveProtocol = None  # type: ignore[misc,assignment]

# PartialReasoningManager — restored import with safe fallback
try:
    from src.core.partial_reasoning import PartialReasoningManager
except ImportError:
    PartialReasoningManager = None  # type: ignore[misc,assignment]

# CodeGenerator and CodeTransformer removed — Zenic is an assistant agent, not a code generator

# Extended AI Architecture

# Phase 7: Real Engines

# Phase 8: Intelligence

# Agent Framework (F1-F5) — migrated to agents with compat adapters

logger = logging.getLogger(__name__)
