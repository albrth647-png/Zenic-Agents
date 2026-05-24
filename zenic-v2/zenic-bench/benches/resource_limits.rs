//! Resource limit testing — What happens under constrained resources?
//!
//! Measures:
//! - Memory: MemoryCache at extreme sizes (10K, 100K, 1M entries)
//! - Memory: HashMap growth patterns for unbounded state
//! - CPU: Sustained safety gate evaluation under high iteration
//! - CPU: Merkle seal computation under sustained load
//! - Database: SQLite connection overhead under concurrent access
//! - Memory Chip: Scaling with 10K, 100K entries
//! - SemanticGraph: INSERT throughput at scale (10K, 50K rows)
//! - SubscriptionGate: Quota check overhead

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use std::sync::{Arc, Mutex};
use std::thread;

use zenic_memory::{
    LearningMechanism, MemoryCache, MerkleSeal, SemanticGraph, SemanticMapping, SubscriptionGate,
    SubscriptionTier,
};
use zenic_safety::categories::NicheCategory;
use zenic_safety::engine::DomainSafetyGate;
use zenic_safety::sensitivity::DataSensitivity;
use serde_json::json;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_mapping(id: usize, tenant: &str) -> SemanticMapping {
    let mut mapping = SemanticMapping::new(
        format!("map-{id}"),
        format!("origin-{id}"),
        "synonym_of".to_string(),
        format!("dest-{id}"),
        LearningMechanism::SchemaDrift,
    );
    mapping.tenant_id = tenant.to_string();
    mapping
}

// ---------------------------------------------------------------------------
// 6.3.1: Memory — MemoryCache at extreme sizes
// ---------------------------------------------------------------------------

fn bench_memory_cache_extreme(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/memory_cache_extreme");
    group.sample_size(10);

    // 10K entries
    let cache = MemoryCache::new(10_100);
    let tenant = "tenant-extreme";
    for i in 0..10_000 {
        let mapping = make_mapping(i, tenant);
        let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
    }
    group.throughput(Throughput::Elements(1));
    group.bench_function("lookup_at_10k", |b| {
        let mut idx = 0;
        b.iter(|| {
            let key = format!("origin-{}", idx % 10_000);
            let _ = cache.lookup(black_box(&key), black_box(tenant));
            idx += 1;
        });
    });

    // 100K entries
    let cache = MemoryCache::new(100_100);
    for i in 0..100_000 {
        let mapping = make_mapping(i, tenant);
        let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
    }
    group.bench_function("lookup_at_100k", |b| {
        let mut idx = 0;
        b.iter(|| {
            let key = format!("origin-{}", idx % 100_000);
            let _ = cache.lookup(black_box(&key), black_box(tenant));
            idx += 1;
        });
    });

    // Eviction at 10K: measuring eviction cost when at capacity
    group.throughput(Throughput::Elements(1));
    group.bench_function("insert_with_eviction_10k", |b| {
        let mut idx = 0;
        b.iter(|| {
            let cache = MemoryCache::new(10_000);
            for i in 0..10_000 {
                let mapping = make_mapping(i, tenant);
                let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
            }
            // This insert triggers eviction
            let mapping = make_mapping(10_000 + idx, tenant);
            let _ = cache.insert(
                black_box(&format!("origin-{}", 10_000 + idx)),
                black_box(&mapping),
                black_box(tenant),
            );
            idx += 1;
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.1b: Memory — HashMap unbounded growth
// ---------------------------------------------------------------------------

fn bench_unbounded_hashmap(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/unbounded_hashmap");
    group.sample_size(10);

    for &entry_count in &[1_000usize, 10_000, 100_000, 1_000_000] {
        let map: Arc<Mutex<std::collections::HashMap<String, f64>>> = Arc::new(
            Mutex::new(
                (0..entry_count)
                    .map(|i| (format!("key_{}", i), i as f64))
                    .collect()
            )
        );

        group.throughput(Throughput::Elements(1000));
        group.bench_with_input(
            BenchmarkId::new("lookup", entry_count),
            &map,
            |b, map| {
                b.iter(|| {
                    for i in 0..1000 {
                        let key = format!("key_{}", i % entry_count);
                        let m = map.lock().unwrap();
                        let _ = black_box(m.contains_key(&key));
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.2: CPU — Sustained safety gate evaluation
// ---------------------------------------------------------------------------

fn bench_sustained_safety_gate(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/sustained_safety_gate");
    group.sample_size(10);

    let gate = DomainSafetyGate::new();
    let config = json!({"action": "view_dashboard"});

    // 10K iterations sustained
    for &iters in &[1_000usize, 10_000, 100_000] {
        group.throughput(Throughput::Elements(iters as u64));
        group.bench_with_input(
            BenchmarkId::new("iterations", iters),
            &iters,
            |b, &iters| {
                b.iter(|| {
                    for i in 0..iters {
                        let niche = NicheCategory::ALL[i % 7];
                        let sensitivity = DataSensitivity::ALL[i % 4];
                        let _ = gate.check(
                            black_box("notification"),
                            black_box(&config),
                            black_box(niche),
                            black_box(sensitivity),
                        );
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.2b: CPU — Sustained Merkle seal computation
// ---------------------------------------------------------------------------

fn bench_sustained_merkle_seal(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/sustained_merkle_seal");
    group.sample_size(10);

    for &seal_count in &[100usize, 1000, 10000] {
        group.throughput(Throughput::Elements(seal_count as u64));
        group.bench_with_input(
            BenchmarkId::new("seal_count", seal_count),
            &seal_count,
            |b, &seal_count| {
                b.iter(|| {
                    let mut seal = MerkleSeal::new();
                    for i in 0..seal_count {
                        let mapping = make_mapping(i, "tenant-seal");
                        let _ = seal.seal_mapping(black_box(&mapping));
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.3: Database — SQLite concurrent connection overhead
// ---------------------------------------------------------------------------

fn bench_concurrent_db_connections(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/concurrent_db_connections");
    group.sample_size(10);

    let tmp_dir = tempfile::tempdir().unwrap();
    let db_path = tmp_dir.path().join("bench_concurrent.db");
    let db_path_str = db_path.to_str().unwrap().to_string();

    // Pre-populate
    {
        let graph = SemanticGraph::new(&db_path_str).unwrap();
        for i in 0..1000 {
            let mapping = make_mapping(i, "tenant-init");
            let _ = graph.insert_mapping(&mapping);
        }
    }

    for &num_connections in &[1usize, 5, 10, 20] {
        group.throughput(Throughput::Elements(num_connections as u64 * 100));
        group.bench_with_input(
            BenchmarkId::new("connections", num_connections),
            &num_connections,
            |b, &num_connections| {
                b.iter(|| {
                    let handles: Vec<_> = (0..num_connections)
                        .map(|_| {
                            let db_path = db_path_str.clone();
                            thread::spawn(move || {
                                let graph = SemanticGraph::new(&db_path).unwrap();
                                for i in 0..100 {
                                    let _ = graph.lookup(
                                        &format!("origin-{}", i % 1000),
                                        "tenant-init",
                                    );
                                }
                            })
                        })
                        .collect();
                    for h in handles {
                        let _ = h.join();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.4: Memory Chip scaling — 10K, 100K entries
// ---------------------------------------------------------------------------

fn bench_memory_chip_at_scale(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/memory_chip_at_scale");
    group.sample_size(10);

    for &entry_count in &[1_000usize, 10_000, 50_000] {
        // Insert throughput
        group.throughput(Throughput::Elements(100));
        group.bench_with_input(
            BenchmarkId::new("insert_batch_100", entry_count),
            &entry_count,
            |b, &entry_count| {
                b.iter(|| {
                    let graph = SemanticGraph::new(":memory:").unwrap();
                    let start = entry_count;
                    for i in start..start + 100 {
                        let mapping = make_mapping(i, "tenant-scale");
                        let _ = graph.insert_mapping(black_box(&mapping));
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.3.5: SubscriptionGate quota check overhead
// ---------------------------------------------------------------------------

fn bench_subscription_gate(c: &mut Criterion) {
    let mut group = c.benchmark_group("resource_limits/subscription_gate");
    group.throughput(Throughput::Elements(1));

    for tier in [
        SubscriptionTier::Starter,
        SubscriptionTier::Business,
        SubscriptionTier::Enterprise,
        SubscriptionTier::OnPremiseEnterprise,
    ] {
        let tier_name1 = format!("{:?}", tier);
        let tier_name2 = format!("{:?}", tier);
        let gate = SubscriptionGate::new(tier);

        group.bench_with_input(
            BenchmarkId::new("check_mechanism", tier_name1),
            &gate,
            |b, gate| {
                b.iter(|| {
                    let _ = gate.check_mechanism(black_box(LearningMechanism::SchemaDrift));
                });
            },
        );

        let gate2 = SubscriptionGate::new(tier);
        group.bench_with_input(
            BenchmarkId::new("check_quota", tier_name2),
            &gate2,
            |b, gate2| {
                b.iter(|| {
                    let _ = gate2.check_mapping_quota(black_box(50));
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_memory_cache_extreme,
    bench_unbounded_hashmap,
    bench_sustained_safety_gate,
    bench_sustained_merkle_seal,
    bench_concurrent_db_connections,
    bench_memory_chip_at_scale,
    bench_subscription_gate,
);
criterion_main!(benches);
