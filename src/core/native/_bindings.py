"""
native._bindings — Native Rust extension detection and binding access.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("zenic_agents.core.native")

# ---------------------------------------------------------------------------
# Detect native extension
# ---------------------------------------------------------------------------

HAS_NATIVE: bool = False
_native_module: Optional[Any] = None

try:
    from _zenic_native import (  # type: ignore[import-not-found]
        # Crypto
        argon2id_hash as _rust_argon2id_hash,  # noqa: F401
        blake3_hash as _rust_blake3_hash,  # noqa: F401
        constant_time_compare as _rust_constant_time_compare,  # noqa: F401
        merkle_root as _rust_merkle_root,  # noqa: F401
        pbkdf2_derive_key as _rust_pbkdf2_derive_key,  # noqa: F401
        xxhash64 as _rust_xxhash64,  # noqa: F401
        # Forensic (A1)
        forensic_hash as _rust_forensic_hash,  # noqa: F401
        chain_hash as _rust_chain_hash,  # noqa: F401
        verify_merkle_chain as _rust_verify_merkle_chain,  # noqa: F401
        merkle_proof as _rust_merkle_proof,  # noqa: F401
        batch_verify_chains as _rust_batch_verify_chains,  # noqa: F401
        # Rollback (A3)
        snapshot_file as _rust_snapshot_file,  # noqa: F401
        restore_file as _rust_restore_file,  # noqa: F401
        verify_rollback_readiness as _rust_verify_rollback_readiness,  # noqa: F401
        file_hash as _rust_file_hash,  # noqa: F401
        # EventBus (B1)
        wildcard_match as _rust_wildcard_match,  # noqa: F401
        resolve_routes as _rust_resolve_routes,  # noqa: F401
        batch_resolve_routes as _rust_batch_resolve_routes,  # noqa: F401
        deduplicate_events as _rust_deduplicate_events,  # noqa: F401
        sort_by_priority as _rust_sort_by_priority,  # noqa: F401
        # Simulation (C1)
        topological_sort as _rust_topological_sort,  # noqa: F401
        detect_cycles as _rust_detect_cycles,  # noqa: F401
        aggregate_impact as _rust_aggregate_impact,  # noqa: F401
        simulate_dag as _rust_simulate_dag,  # noqa: F401
        # Risk (F3)
        calculate_blast_radius as _rust_calculate_blast_radius,  # noqa: F401
        propagate_risks as _rust_propagate_risks,  # noqa: F401
        find_critical_path as _rust_find_critical_path,  # noqa: F401
        compute_reachability as _rust_compute_reachability,  # noqa: F401
        multi_node_blast_radius as _rust_multi_node_blast_radius,  # noqa: F401
    )

    HAS_NATIVE = True
    _native_module = True
    logger.info("Native Rust extension (_zenic_native) loaded successfully")
except ImportError:
    HAS_NATIVE = False
    _native_module = None
    logger.info(
        "Native Rust extension not available — using pure Python fallbacks"
    )


# ---------------------------------------------------------------------------
# Lazy access to extended PyO3 modules (db, bus, safety_gate, license)
# ---------------------------------------------------------------------------

def get_native_module() -> Optional[Any]:
    """Return the _zenic_native module if available, else None."""
    if not HAS_NATIVE:
        return None
    try:
        import _zenic_native as _mod  # type: ignore[import-not-found]
        return _mod
    except ImportError:
        return None


def get_encrypted_db() -> Optional[type]:
    """Return the EncryptedDb PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "EncryptedDb", None)


def get_shared_memory_bus() -> Optional[type]:
    """Return the SharedMemoryBus PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "SharedMemoryBus", None)


def get_safety_verdict() -> Optional[type]:
    """Return the SafetyVerdict PyO3 enum if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "SafetyVerdict", None)


def get_license_info() -> Optional[type]:
    """Return the LicenseInfo PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "LicenseInfo", None)
