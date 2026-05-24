"""
ZENIC-AGENTS — Forensic Engine (A1: Enriched Audit + Forensic Audit).

Unifies MerkleLedger + AuditLogger + Tracing into a single query interface
for forensic analysis, chain verification, and evidence export.

This package re-exports every symbol from the original monolithic
``forensic.py`` so that ``from src.core.observability.forensic import X``
continues to work unchanged.
"""

# ── Re-export all public symbols ─────────────────────────────

from ._types import (
    ChainVerificationResult,
    EvidenceBundle,
    ForensicEntry,
    ForensicReport,
)

from ._engine import (
    ForensicEngine,
    get_forensic_engine,
    reset_forensic_engine,
)

# Also expose the internal submodules' public helpers for advanced use
from ._collector import (
    retry as _retry,  # noqa: F401
    RETRY_MAX_ATTEMPTS as _RETRY_MAX_ATTEMPTS,  # noqa: F401
    RETRY_BASE_DELAY as _RETRY_BASE_DELAY,  # noqa: F401
    get_audit_db_path as _get_audit_db_path,  # noqa: F401
    load_audit_events as _load_audit_events,  # noqa: F401
    load_ledger_entries as _load_ledger_entries,  # noqa: F401
    correlate as _correlate,  # noqa: F401
)

from ._analyzer import (
    verify_local_chain as _verify_local_chain,  # noqa: F401
    verify_chain_entries as _verify_chain_entries,  # noqa: F401
    build_merkle_proofs as _build_merkle_proofs,  # noqa: F401
    compute_merkle_root as _compute_merkle_root,  # noqa: F401
)

__all__ = ["ChainVerificationResult", "EvidenceBundle", "ForensicEngine", "ForensicEntry", "ForensicReport", "RETRY_BASE_DELAY", "RETRY_MAX_ATTEMPTS", "build_merkle_proofs", "compute_merkle_root", "correlate", "get_audit_db_path", "get_forensic_engine", "load_audit_events", "load_ledger_entries", "reset_forensic_engine", "retry", "verify_chain_entries", "verify_local_chain"]
