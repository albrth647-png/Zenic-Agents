"""
native._bindings — Native Rust extension detection and binding access.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("zenic_agents.core.native")

# ---------------------------------------------------------------------------
# Detect native extension
# ---------------------------------------------------------------------------

HAS_NATIVE: bool = False
_native_module: Any | None = None

try:
    from _zenic_native import (
        aggregate_impact as _rust_aggregate_impact,  # noqa: F401
    )
    from _zenic_native import (  # type: ignore[import-not-found]
        # Crypto
        argon2id_hash as _rust_argon2id_hash,  # noqa: F401
    )
    from _zenic_native import (
        batch_resolve_routes as _rust_batch_resolve_routes,  # noqa: F401
    )
    from _zenic_native import (
        batch_verify_chains as _rust_batch_verify_chains,  # noqa: F401
    )
    from _zenic_native import (
        blake3_hash as _rust_blake3_hash,  # noqa: F401
    )
    from _zenic_native import (
        # Risk (F3)
        calculate_blast_radius as _rust_calculate_blast_radius,  # noqa: F401
    )
    from _zenic_native import (
        chain_hash as _rust_chain_hash,  # noqa: F401
    )
    from _zenic_native import (
        compute_reachability as _rust_compute_reachability,  # noqa: F401
    )
    from _zenic_native import (
        constant_time_compare as _rust_constant_time_compare,  # noqa: F401
    )
    from _zenic_native import (
        deduplicate_events as _rust_deduplicate_events,  # noqa: F401
    )
    from _zenic_native import (
        detect_cycles as _rust_detect_cycles,  # noqa: F401
    )
    from _zenic_native import (
        file_hash as _rust_file_hash,  # noqa: F401
    )
    from _zenic_native import (
        find_critical_path as _rust_find_critical_path,  # noqa: F401
    )
    from _zenic_native import (
        # Forensic (A1)
        forensic_hash as _rust_forensic_hash,  # noqa: F401
    )
    from _zenic_native import (
        merkle_proof as _rust_merkle_proof,  # noqa: F401
    )
    from _zenic_native import (
        merkle_root as _rust_merkle_root,  # noqa: F401
    )
    from _zenic_native import (
        multi_node_blast_radius as _rust_multi_node_blast_radius,  # noqa: F401
    )
    from _zenic_native import (
        pbkdf2_derive_key as _rust_pbkdf2_derive_key,  # noqa: F401
    )
    from _zenic_native import (
        propagate_risks as _rust_propagate_risks,  # noqa: F401
    )
    from _zenic_native import (
        resolve_routes as _rust_resolve_routes,  # noqa: F401
    )
    from _zenic_native import (
        restore_file as _rust_restore_file,  # noqa: F401
    )
    from _zenic_native import (
        simulate_dag as _rust_simulate_dag,  # noqa: F401
    )
    from _zenic_native import (
        # Rollback (A3)
        snapshot_file as _rust_snapshot_file,  # noqa: F401
    )
    from _zenic_native import (
        sort_by_priority as _rust_sort_by_priority,  # noqa: F401
    )
    from _zenic_native import (
        # Simulation (C1)
        topological_sort as _rust_topological_sort,  # noqa: F401
    )
    from _zenic_native import (
        verify_merkle_chain as _rust_verify_merkle_chain,  # noqa: F401
    )
    from _zenic_native import (
        verify_rollback_readiness as _rust_verify_rollback_readiness,  # noqa: F401
    )
    from _zenic_native import (
        # EventBus (B1)
        wildcard_match as _rust_wildcard_match,  # noqa: F401
    )
    from _zenic_native import (
        xxhash64 as _rust_xxhash64,  # noqa: F401
    )

    HAS_NATIVE = True
    _native_module = True
    logger.info("Native Rust extension (_zenic_native) loaded successfully")
except ImportError:
    HAS_NATIVE = False
    _native_module = None
    logger.info("Native Rust extension not available — using pure Python fallbacks")


# ---------------------------------------------------------------------------
# Lazy access to extended PyO3 modules (db, bus, safety_gate, license)
# ---------------------------------------------------------------------------


def get_native_module() -> Any | None:
    """Return the _zenic_native module if available, else None."""
    if not HAS_NATIVE:
        return None
    try:
        import _zenic_native as _mod  # type: ignore[import-not-found]

        return _mod
    except ImportError:
        return None


def get_encrypted_db() -> type | None:
    """Return the EncryptedDb PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "EncryptedDb", None)


def get_shared_memory_bus() -> type | None:
    """Return the SharedMemoryBus PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "SharedMemoryBus", None)


def get_safety_verdict() -> type | None:
    """Return the SafetyVerdict PyO3 enum if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "SafetyVerdict", None)


def get_license_info() -> type | None:
    """Return the LicenseInfo PyO3 class if native extension is available."""
    _mod = get_native_module()
    if _mod is None:
        return None
    return getattr(_mod, "LicenseInfo", None)
