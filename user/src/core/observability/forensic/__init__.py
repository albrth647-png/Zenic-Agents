"""
ZENIC-AGENTS — Forensic Engine (A1: Enriched Audit + Forensic Audit).

Unifies MerkleLedger + AuditLogger + Tracing into a single query interface
for forensic analysis, chain verification, and evidence export.

This package re-exports every symbol from the original monolithic
``forensic.py`` so that ``from src.core.observability.forensic import X``
continues to work unchanged.
"""

# ── Re-export all public symbols ─────────────────────────────

from ._analyzer import (
    build_merkle_proofs as _build_merkle_proofs,
)
from ._analyzer import (
    compute_merkle_root as _compute_merkle_root,
)
from ._analyzer import (
    verify_chain_entries as _verify_chain_entries,
)
from ._analyzer import (
    verify_local_chain as _verify_local_chain,
)
from ._collector import (
    RETRY_BASE_DELAY as _RETRY_BASE_DELAY,
)
from ._collector import (
    RETRY_MAX_ATTEMPTS as _RETRY_MAX_ATTEMPTS,
)
from ._collector import (
    correlate as _correlate,
)
from ._collector import (
    get_audit_db_path as _get_audit_db_path,
)
from ._collector import (
    load_audit_events as _load_audit_events,
)
from ._collector import (
    load_ledger_entries as _load_ledger_entries,
)

# Also expose the internal submodules' public helpers for advanced use
from ._collector import (
    retry as _retry,
)
from ._engine import (
    ForensicEngine,
    get_forensic_engine,
    reset_forensic_engine,
)
from ._types import (
    ChainVerificationResult,
    EvidenceBundle,
    ForensicEntry,
    ForensicReport,
)

__all__ = [
    "RETRY_BASE_DELAY",
    "RETRY_MAX_ATTEMPTS",
    "ChainVerificationResult",
    "EvidenceBundle",
    "ForensicEngine",
    "ForensicEntry",
    "ForensicReport",
    "build_merkle_proofs",
    "compute_merkle_root",
    "correlate",
    "get_audit_db_path",
    "get_forensic_engine",
    "load_audit_events",
    "load_ledger_entries",
    "reset_forensic_engine",
    "retry",
    "verify_chain_entries",
    "verify_local_chain",
]
