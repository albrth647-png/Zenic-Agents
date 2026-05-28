"""
Native extension loader — DELEGATES to canonical _bindings module.

H-84 FIX: This file was a duplicate of ``_bindings.py``. Both tried
to import ``_zenic_native`` independently, which could cause:
  1. Double import attempt of the Rust extension
  2. Inconsistent HAS_NATIVE flags if one succeeds and the other fails
  3. Maintenance burden (any new Rust function must be added in two places)

Now this module simply re-exports everything from the canonical
``src.core.native._bindings``, ensuring a single source of truth.
"""

from src.core.native._bindings import (  # noqa: F401
    # Flag
    HAS_NATIVE,
    _native_module,
    _rust_aggregate_impact,
    # Rust function references
    _rust_argon2id_hash,
    _rust_batch_resolve_routes,
    _rust_batch_verify_chains,
    _rust_blake3_hash,
    _rust_calculate_blast_radius,
    _rust_chain_hash,
    _rust_compute_reachability,
    _rust_constant_time_compare,
    _rust_deduplicate_events,
    _rust_detect_cycles,
    _rust_file_hash,
    _rust_find_critical_path,
    _rust_forensic_hash,
    _rust_merkle_proof,
    _rust_merkle_root,
    _rust_multi_node_blast_radius,
    _rust_pbkdf2_derive_key,
    _rust_propagate_risks,
    _rust_resolve_routes,
    _rust_restore_file,
    _rust_simulate_dag,
    _rust_snapshot_file,
    _rust_sort_by_priority,
    _rust_topological_sort,
    _rust_verify_merkle_chain,
    _rust_verify_rollback_readiness,
    _rust_wildcard_match,
    _rust_xxhash64,
    get_encrypted_db,
    get_license_info,
    # Lazy accessors
    get_native_module,
    get_safety_verdict,
    get_shared_memory_bus,
)
