//! Phase 5: Determinism Verification Tests — zenic-memory crate
//!
//! Reproducibility and idempotency tests for MerkleSeal, MemoryCache,
//! and SubscriptionGate.

use crate::cache::MemoryCache;
use crate::merkle_seal::MerkleSeal;
use crate::subscription_gate::SubscriptionGate;
use crate::types::{LearningMechanism, SemanticMapping, SubscriptionTier};

fn make_mapping(id: &str, origin: &str, dest: &str) -> SemanticMapping {
    SemanticMapping::new(
        id.to_string(),
        origin.to_string(),
        "synonym_of".to_string(),
        dest.to_string(),
        LearningMechanism::SchemaDrift,
    )
}

// ═══════════════════════════════════════════════════════════════════════════
// 5.3 REPRODUCIBILITY TESTS
// ═══════════════════════════════════════════════════════════════════════════

// ── Reproducibility: Merkle seal ─────────────────────────────────────────

#[test]
fn repro_merkle_seal_same_mapping_n100() {
    let mapping = make_mapping("map-001", "cobro", "factura");

    let mut seal1 = MerkleSeal::new();
    let hash1 = seal1.seal_mapping(&mapping).expect("seal1");

    // Seal the same mapping 99 more times in fresh seals — all must produce same hash
    for i in 1..100 {
        let mut seal = MerkleSeal::new();
        let hash = seal.seal_mapping(&mapping).expect("seal");
        assert_eq!(
            hash1, hash,
            "Merkle seal diverged at iteration {} for same mapping",
            i
        );
    }
}

#[test]
fn repro_merkle_seal_compute_n100() {
    let m1 = make_mapping("a", "x", "y");
    let m2 = make_mapping("b", "p", "q");

    let leaves: Vec<Vec<u8>> = vec![
        bincode::serialize(&m1).expect("ser1"),
        bincode::serialize(&m2).expect("ser2"),
    ];

    let mut first_root = String::new();
    for i in 0..100 {
        let mut seal = MerkleSeal::new();
        seal.compute(&leaves);
        let root = seal.root_hash_hex();
        if i == 0 {
            first_root = root;
        } else {
            assert_eq!(
                first_root, root,
                "Merkle compute diverged at iteration {}",
                i
            );
        }
    }
}

#[test]
fn repro_merkle_verify_n100() {
    let mapping = make_mapping("v-001", "alpha", "beta");
    let mut seal = MerkleSeal::new();
    let hash = seal.seal_mapping(&mapping).expect("seal");

    for i in 0..100 {
        let ok = seal.verify_mapping(&mapping, &hash).expect("verify");
        assert!(ok, "Verification failed at iteration {}", i);
    }
}

// ── Reproducibility: SubscriptionGate ────────────────────────────────────

#[test]
fn repro_subscription_gate_mechanism_n100() {
    let gate = SubscriptionGate::enterprise();
    for _ in 0..100 {
        assert!(gate.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        assert!(gate.check_mechanism(LearningMechanism::IntentRouting).is_ok());
        assert!(gate.check_ontology_access().is_ok());
    }
}

#[test]
fn repro_subscription_gate_starter_restrictions_n100() {
    let gate = SubscriptionGate::starter();
    for _ in 0..100 {
        assert!(gate.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        // IntentRouting should be restricted for Starter
        assert!(gate.check_mechanism(LearningMechanism::IntentRouting).is_err());
        assert!(gate.check_ontology_access().is_err());
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// 5.4 IDEMPOTENCY TESTS
// ═══════════════════════════════════════════════════════════════════════════

// ── Idempotency: Merkle seal ─────────────────────────────────────────────

#[test]
fn idempotent_merkle_seal_same_mapping() {
    let mapping = make_mapping("idem-1", "cobro", "factura");

    let mut seal1 = MerkleSeal::new();
    let hash1 = seal1.seal_mapping(&mapping).expect("seal1");

    let mut seal2 = MerkleSeal::new();
    let hash2 = seal2.seal_mapping(&mapping).expect("seal2");

    // Same input → same hash
    assert_eq!(hash1, hash2, "Merkle seal diverged for same mapping");
}

#[test]
fn idempotent_merkle_seal_verify() {
    let mapping = make_mapping("idem-2", "pago", "payment");
    let mut seal = MerkleSeal::new();
    let hash = seal.seal_mapping(&mapping).expect("seal");

    // Verify the same mapping N times — must always succeed
    for _ in 0..100 {
        assert!(
            seal.verify_mapping(&mapping, &hash).expect("verify"),
            "Merkle verification failed on repeated check"
        );
    }
}

#[test]
fn idempotent_merkle_seal_compute_vs_incremental() {
    let m1 = make_mapping("inc-a", "a", "b");
    let m2 = make_mapping("inc-b", "c", "d");

    // Incremental sealing
    let mut seal_inc = MerkleSeal::new();
    seal_inc.seal_mapping(&m1).expect("seal1");
    seal_inc.seal_mapping(&m2).expect("seal2");
    let root_inc = seal_inc.root_hash_hex();

    // Batch compute
    let mut seal_batch = MerkleSeal::new();
    let leaves: Vec<Vec<u8>> = vec![
        bincode::serialize(&m1).expect("ser1"),
        bincode::serialize(&m2).expect("ser2"),
    ];
    seal_batch.compute(&leaves);
    let root_batch = seal_batch.root_hash_hex();

    // Both approaches must produce the same root hash
    assert_eq!(
        root_inc, root_batch,
        "Incremental and batch Merkle roots diverged: inc={} batch={}",
        root_inc, root_batch
    );
}

#[test]
fn idempotent_merkle_batch_verify() {
    let mappings: Vec<SemanticMapping> = (0..5)
        .map(|i| make_mapping(&format!("batch-{}", i), &format!("origin_{}", i), &format!("dest_{}", i)))
        .collect();

    let mut seal = MerkleSeal::new();
    let mut hashes: Vec<(SemanticMapping, String)> = Vec::new();
    for m in &mappings {
        let h = seal.seal_mapping(m).expect("seal");
        hashes.push((m.clone(), h));
    }

    // Verify batch N times
    for _ in 0..100 {
        let results = seal.verify_batch(&hashes);
        assert!(results.iter().all(|&ok| ok), "Batch verification failed");
    }
}

#[test]
fn idempotent_merkle_seal_repeated_seal_same_mapping() {
    // Sealing the same mapping twice should produce the same hash each time
    // (the root will differ because update_root chains, but the individual hash should be same)
    let mapping = make_mapping("repeat-1", "test", "value");

    let hash1 = {
        let mut seal = MerkleSeal::new();
        seal.seal_mapping(&mapping).expect("seal")
    };

    let hash2 = {
        let mut seal = MerkleSeal::new();
        seal.seal_mapping(&mapping).expect("seal")
    };

    assert_eq!(hash1, hash2, "Repeated seal of same mapping produced different hashes");
}

// ── Idempotency: MemoryCache ─────────────────────────────────────────────

#[test]
fn idempotent_cache_insert_lookup() {
    let cache = MemoryCache::new(100);
    let mapping = make_mapping("cache-1", "test_origin", "test_dest");

    cache.insert("test_origin", &mapping, "tenant-1").expect("insert");

    // Lookup N times — must always return the same mapping
    for _ in 0..100 {
        let result = cache.lookup("test_origin", "tenant-1");
        assert!(result.is_some(), "Cache lookup failed after insert");
        let found = result.unwrap();
        assert_eq!(found.mapping_id, "cache-1");
        assert_eq!(found.origin, "test_origin");
        assert_eq!(found.destination, "test_dest");
    }
}

#[test]
fn idempotent_cache_same_key_overwrite() {
    let cache = MemoryCache::new(100);
    let mapping1 = make_mapping("cache-v1", "key", "dest_v1");
    let mapping2 = make_mapping("cache-v2", "key", "dest_v2");

    cache.insert("key", &mapping1, "t1").expect("insert1");
    cache.insert("key", &mapping2, "t1").expect("insert2");

    // Second insert should overwrite — the latest value must be returned consistently
    for _ in 0..100 {
        let result = cache.lookup("key", "t1");
        assert!(result.is_some());
        assert_eq!(result.unwrap().mapping_id, "cache-v2");
    }
}

#[test]
fn idempotent_cache_remove() {
    let cache = MemoryCache::new(100);
    let mapping = make_mapping("cache-rm", "rm_key", "rm_dest");

    cache.insert("rm_key", &mapping, "t1").expect("insert");
    cache.remove("rm_key", "t1");

    // After removal, lookups must consistently return None
    for _ in 0..100 {
        assert!(cache.lookup("rm_key", "t1").is_none());
    }
}

#[test]
fn idempotent_cache_clear() {
    let cache = MemoryCache::new(100);

    for i in 0..5 {
        let m = make_mapping(&format!("clear-{}", i), &format!("key-{}", i), &format!("dest-{}", i));
        cache.insert(&format!("key-{}", i), &m, "t1").expect("insert");
    }

    cache.clear();
    assert_eq!(cache.len(), 0);

    // After clear, all lookups must consistently return None
    for i in 0..5 {
        assert!(cache.lookup(&format!("key-{}", i), "t1").is_none());
    }
}

#[test]
fn idempotent_cache_eviction_deterministic() {
    let cache = MemoryCache::new(5); // Tiny cache

    // Insert 5 entries
    for i in 0..5 {
        let m = make_mapping(&format!("evict-{}", i), &format!("key-{}", i), &format!("dest-{}", i));
        cache.insert(&format!("key-{}", i), &m, "t1").expect("insert");
    }

    // Access key-0 and key-1 multiple times to boost their access count
    for _ in 0..10 {
        cache.lookup("key-0", "t1");
        cache.lookup("key-1", "t1");
    }

    // Insert one more — should trigger eviction of least-accessed entries
    let m6 = make_mapping("evict-5", "key-5", "dest-5");
    cache.insert("key-5", &m6, "t1").expect("insert6");

    // key-0 and key-1 should still be present (high access count)
    assert!(cache.lookup("key-0", "t1").is_some(), "key-0 should survive eviction");
    assert!(cache.lookup("key-1", "t1").is_some(), "key-1 should survive eviction");
    // key-5 should be present
    assert!(cache.lookup("key-5", "t1").is_some(), "key-5 should be present");
}

#[test]
fn idempotent_cache_multi_tenant_isolation() {
    let cache = MemoryCache::new(100);
    let m1 = make_mapping("t1-map", "shared_key", "dest_t1");
    let m2 = make_mapping("t2-map", "shared_key", "dest_t2");

    cache.insert("shared_key", &m1, "tenant-1").expect("insert t1");
    cache.insert("shared_key", &m2, "tenant-2").expect("insert t2");

    // Each tenant must see its own mapping
    for _ in 0..100 {
        let r1 = cache.lookup("shared_key", "tenant-1");
        let r2 = cache.lookup("shared_key", "tenant-2");
        assert_eq!(r1.unwrap().mapping_id, "t1-map");
        assert_eq!(r2.unwrap().mapping_id, "t2-map");
    }
}

// ── Idempotency: SubscriptionGate ────────────────────────────────────────

#[test]
fn idempotent_subscription_gate() {
    let gate = SubscriptionGate::enterprise();

    // Same check twice must produce same result
    for _ in 0..100 {
        assert!(gate.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        assert!(gate.check_mapping_quota(0).is_ok());
        assert!(gate.check_ontology_access().is_ok());
    }
}

#[test]
fn idempotent_subscription_gate_tier_differences() {
    let starter = SubscriptionGate::starter();
    let business = SubscriptionGate::business();
    let enterprise = SubscriptionGate::enterprise();

    for _ in 0..100 {
        // Starter: SchemaDrift only
        assert!(starter.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        assert!(starter.check_mechanism(LearningMechanism::IntentRouting).is_err());

        // Business: SchemaDrift + IntentRouting
        assert!(business.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        assert!(business.check_mechanism(LearningMechanism::IntentRouting).is_ok());
        assert!(business.check_ontology_access().is_err());

        // Enterprise: all
        assert!(enterprise.check_mechanism(LearningMechanism::SchemaDrift).is_ok());
        assert!(enterprise.check_mechanism(LearningMechanism::IntentRouting).is_ok());
        assert!(enterprise.check_ontology_access().is_ok());
    }
}
