"""
Internal split modules for ``src.core.native``.

This package is not part of the public API — all symbols are re-exported
by the parent ``native/__init__.py``.
"""

from ._crypto import (
    argon2id_hash,
    blake3_hash,
    constant_time_compare,
    merkle_root,
    pbkdf2_derive_key,
    xxhash64,
)
from ._eventbus import (
    batch_resolve_routes,
    deduplicate_events,
    resolve_routes,
    sort_by_priority,
    wildcard_match,
)
from ._forensic import (
    batch_verify_chains,
    chain_hash,
    forensic_hash,
    merkle_proof,
    verify_merkle_chain,
)
from ._loader import (
    HAS_NATIVE,
    get_encrypted_db,
    get_license_info,
    get_native_module,
    get_safety_verdict,
    get_shared_memory_bus,
)
from ._risk import (
    calculate_blast_radius,
    compute_reachability,
    find_critical_path,
    multi_node_blast_radius,
    propagate_risks,
)
from ._rollback import (
    file_hash,
    restore_file,
    snapshot_file,
    verify_rollback_readiness,
)
from ._simulation import (
    aggregate_impact,
    detect_cycles,
    simulate_dag,
    topological_sort,
)

__all__ = [
    "HAS_NATIVE",
    "aggregate_impact",
    "argon2id_hash",
    "batch_resolve_routes",
    "batch_verify_chains",
    "blake3_hash",
    "calculate_blast_radius",
    "chain_hash",
    "compute_reachability",
    "constant_time_compare",
    "deduplicate_events",
    "detect_cycles",
    "file_hash",
    "find_critical_path",
    "forensic_hash",
    "get_encrypted_db",
    "get_license_info",
    "get_native_module",
    "get_safety_verdict",
    "get_shared_memory_bus",
    "merkle_proof",
    "merkle_root",
    "multi_node_blast_radius",
    "pbkdf2_derive_key",
    "propagate_risks",
    "resolve_routes",
    "restore_file",
    "simulate_dag",
    "snapshot_file",
    "sort_by_priority",
    "topological_sort",
    "verify_merkle_chain",
    "verify_rollback_readiness",
    "wildcard_match",
    "xxhash64",
]
