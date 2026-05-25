//! Load testing benchmarks for concurrent safety validation and memory operations.
//!
//! Scenarios:
//! - 10 concurrent safety validations
//! - 100 concurrent safety validations
//! - 1000 concurrent safety validations
//! - Burst traffic simulation (0→1000 in 1 second)
//! - Sustained high load (many iterations)
//! - Concurrent SemanticGraph writes (SQLite contention)
//! - Unbounded state growth simulation (CONFIRMATIONS/APPROVALS/DENIED_ACTIONS)
//! - MemoryChip concurrent store/retrieve
//! - SharedMemoryBus concurrent pub/sub

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use std::sync::{Arc, Mutex};
use std::thread;

use zenic_memory::{LearningMechanism, MemoryCache, SemanticGraph, SemanticMapping};
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
// Load Test: Concurrent safety gate validations
// ---------------------------------------------------------------------------

/// Simulates concurrent safety gate validation requests.
/// Each thread creates its own gate and runs validations.
fn bench_concurrent_safety_validations(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/safety_gate_concurrent");

    let configs = vec![
        json!({"action": "view_dashboard"}),
        json!({"operation": "delete", "query": "DELETE FROM users"}),
        json!({"action": "invoice_create", "subject": "Payment", "body": "Due"}),
    ];

    for &num_threads in &[1usize, 10, 100] {
        let iters_per_thread = 1000 / num_threads.max(1);
        group.throughput(Throughput::Elements(num_threads as u64 * iters_per_thread as u64));
        group.bench_with_input(
            BenchmarkId::new("threads", num_threads),
            &num_threads,
            |b, &num_threads| {
                b.iter(|| {
                    let handles: Vec<_> = (0..num_threads)
                        .map(|thread_id| {
                            thread::spawn(move || {
                                let gate = DomainSafetyGate::new();
                                let niche = NicheCategory::ALL[thread_id % 7];
                                let sensitivity = DataSensitivity::ALL[thread_id % 4];
                                let config = &configs[thread_id % configs.len()];

                                for i in 0..iters_per_thread {
                                    let action = match i % 3 {
                                        0 => "notification",
                                        1 => "database",
                                        _ => "email",
                                    };
                                    let _ = gate.check(
                                        black_box(action),
                                        black_box(config),
                                        black_box(niche),
                                        black_box(sensitivity),
                                    );
                                }
                            })
                        })
                        .collect();

                    for h in handles {
                        h.join().unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: 1000 concurrent validations (stress test)
// ---------------------------------------------------------------------------

/// Stress test: 1000 threads each performing safety validations.
/// This tests thread creation overhead and memory usage at scale.
fn bench_1000_concurrent(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/safety_1000_concurrent");
    group.throughput(Throughput::Elements(1000));
    group.sample_size(10); // Reduced sample size for long-running test

    group.bench_function("1000_threads_10_iters", |b| {
        b.iter(|| {
            let handles: Vec<_> = (0..1000)
                .map(|thread_id| {
                    thread::spawn(move || {
                        let gate = DomainSafetyGate::new();
                        let niche = NicheCategory::ALL[thread_id % 7];
                        let config = json!({"action": "test"});

                        for _ in 0..10 {
                            let _ = gate.check(
                                black_box("notification"),
                                black_box(&config),
                                black_box(niche),
                                black_box(DataSensitivity::Low),
                            );
                        }
                    })
                })
                .collect();

            for h in handles {
                let _ = h.join();
            }
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: Concurrent SemanticGraph writes (SQLite contention)
// ---------------------------------------------------------------------------

/// Tests SQLite write contention under concurrent access.
/// Multiple threads writing to the same in-memory database.
fn bench_concurrent_graph_writes(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/graph_concurrent_writes");

    for &num_threads in &[1usize, 2, 4, 8] {
        group.throughput(Throughput::Elements(num_threads as u64 * 100));
        group.bench_with_input(
            BenchmarkId::new("threads", num_threads),
            &num_threads,
            |b, &num_threads| {
                b.iter(|| {
                    // Use a file-backed DB for multi-connection access
                    let tmp_dir = tempfile::tempdir().unwrap();
                    let db_path = tmp_dir.path().join("bench.db");
                    let db_path_str = db_path.to_str().unwrap().to_string();

                    // Create and initialize
                    {
                        let graph = SemanticGraph::new(&db_path_str).unwrap();
                        for i in 0..50 {
                            let mapping = make_mapping(i, "tenant-init");
                            graph.insert_mapping(&mapping).unwrap();
                        }
                    }

                    let handles: Vec<_> = (0..num_threads)
                        .map(|thread_id| {
                            let db_path = db_path_str.clone();
                            thread::spawn(move || {
                                let graph = SemanticGraph::new(&db_path).unwrap();
                                let tenant = format!("tenant-{}", thread_id);

                                for i in 0..100 {
                                    let mapping = make_mapping(
                                        thread_id * 10000 + i,
                                        &tenant,
                                    );
                                    let _ = graph.insert_mapping(&mapping);
                                }
                            })
                        })
                        .collect();

                    for h in handles {
                        h.join().unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: Unbounded state growth simulation
// ---------------------------------------------------------------------------

/// Simulates the unbounded growth of CONFIRMATIONS/APPROVALS/DENIED_ACTIONS maps.
/// Tests HashMap lookup performance as the maps grow.
fn bench_unbounded_state_growth(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/unbounded_state_growth");

    for &entry_count in &[100usize, 1000, 10000, 100000] {
        // Simulate CONFIRMATIONS map
        let confirmations: Arc<Mutex<std::collections::HashMap<String, f64>>> =
            Arc::new(Mutex::new((0..entry_count)
                .map(|i| (format!("act_{}", i), i as f64))
                .collect()));

        group.throughput(Throughput::Elements(1000));
        group.bench_with_input(
            BenchmarkId::new("confirmations_lookup", entry_count),
            &confirmations,
            |b, confirmations| {
                b.iter(|| {
                    for i in 0..1000 {
                        let key = format!("act_{}", i % entry_count);
                        let map = confirmations.lock().unwrap();
                        let _ = black_box(map.contains_key(&key));
                    }
                });
            },
        );

        // Simulate DENIED_ACTIONS map
        let denied: Arc<Mutex<std::collections::HashMap<String, f64>>> =
            Arc::new(Mutex::new((0..entry_count)
                .map(|i| (format!("denied_{}", i), i as f64))
                .collect()));

        group.bench_with_input(
            BenchmarkId::new("denied_insert", entry_count),
            &denied,
            |b, denied| {
                let mut idx = entry_count;
                b.iter(|| {
                    let mut map = denied.lock().unwrap();
                    map.insert(format!("denied_{}", idx), idx as f64);
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: MemoryChip concurrent store/retrieve
// ---------------------------------------------------------------------------

/// Tests concurrent MemoryCache store/retrieve operations.
fn bench_concurrent_memory_cache(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/memory_cache_concurrent");

    let cache_sizes = [100, 500, 2000];

    for &cache_size in &cache_sizes {
        for &num_threads in &[1usize, 4] {
            let cache = Arc::new(MemoryCache::new(cache_size));
            let tenant = "tenant-load";

            // Pre-populate
            for i in 0..cache_size {
                let mapping = make_mapping(i, tenant);
                let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
            }

            let iters = 1000;
            group.throughput(Throughput::Elements(num_threads as u64 * iters as u64));
            group.bench_with_input(
                BenchmarkId::new(
                    format!("size_{}", cache_size),
                    num_threads,
                ),
                &(cache.clone(), num_threads),
                |b, (cache, num_threads)| {
                    b.iter(|| {
                        let handles: Vec<_> = (0..*num_threads)
                            .map(|thread_id| {
                                let cache = Arc::clone(cache);
                                let tenant = tenant.to_string();
                                thread::spawn(move || {
                                    for i in 0..iters {
                                        let key = format!("origin-{}", (thread_id * iters + i) % cache_size);
                                        let _ = cache.lookup(&key, &tenant);
                                    }
                                })
                            })
                            .collect();

                        for h in handles {
                            h.join().unwrap();
                        }
                    });
                },
            );
        }
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: Burst simulation (rapid sequential validations)
// ---------------------------------------------------------------------------

/// Simulates burst traffic: rapid sequential safety validations.
fn bench_burst_traffic(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/burst_traffic");
    group.sample_size(10);

    for &burst_size in &[100usize, 1000, 10000] {
        group.throughput(Throughput::Elements(burst_size as u64));
        group.bench_with_input(
            BenchmarkId::new("burst", burst_size),
            &burst_size,
            |b, &burst_size| {
                let gate = DomainSafetyGate::new();
                let config = json!({"action": "view_dashboard"});

                b.iter(|| {
                    for i in 0..burst_size {
                        let niche = NicheCategory::ALL[i % 7];
                        let sensitivity = DataSensitivity::ALL[i % 4];
                        let action = match i % 5 {
                            0 => "notification",
                            1 => "database",
                            2 => "email",
                            3 => "file",
                            _ => "http",
                        };
                        let _ = gate.check(
                            black_box(action),
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
// Load Test: MemoryChip scaling (10K, 100K entries)
// ---------------------------------------------------------------------------

/// Tests MemoryCache performance with large numbers of entries.
fn bench_memory_chip_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/memory_chip_scaling");

    for &entry_count in &[100usize, 1000, 10000] {
        let cache = MemoryCache::new(entry_count + 100);
        let tenant = "tenant-scale";

        // Populate to capacity
        for i in 0..entry_count {
            let mapping = make_mapping(i, tenant);
            let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("lookup_at_capacity", entry_count),
            &cache,
            |b, cache| {
                let mut idx = 0;
                b.iter(|| {
                    let key = format!("origin-{}", idx % entry_count);
                    let _ = cache.lookup(black_box(&key), black_box(tenant));
                    idx += 1;
                });
            },
        );

        // Insert at capacity (triggers eviction)
        group.bench_with_input(
            BenchmarkId::new("insert_at_capacity", entry_count),
            &cache,
            |b, cache| {
                let mut idx = entry_count;
                b.iter(|| {
                    let mapping = make_mapping(idx, tenant);
                    let _ = cache.insert(
                        black_box(&format!("origin-{}", idx)),
                        black_box(&mapping),
                        black_box(tenant),
                    );
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Load Test: SemanticGraph scaling (10K, 50K entries)
// ---------------------------------------------------------------------------

/// Tests SemanticGraph performance with large numbers of mappings.
fn bench_semantic_graph_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("load/semantic_graph_scaling");

    for &entry_count in &[100usize, 1000, 10000] {
        group.throughput(Throughput::Elements(1));

        // Lookup at scale
        group.bench_with_input(
            BenchmarkId::new("lookup", entry_count),
            &entry_count,
            |b, &entry_count| {
                let graph = SemanticGraph::new(":memory:").unwrap();
                let tenant = "tenant-scale";
                for i in 0..entry_count {
                    let mapping = make_mapping(i, tenant);
                    graph.insert_mapping(&mapping).unwrap();
                }

                let mut idx = 0;
                b.iter(|| {
                    let origin = format!("origin-{}", idx % entry_count);
                    let _ = graph.lookup(black_box(&origin), black_box(tenant));
                    idx += 1;
                });
            },
        );

        // Insert at scale
        group.bench_with_input(
            BenchmarkId::new("insert", entry_count),
            &entry_count,
            |b, &entry_count| {
                b.iter(|| {
                    let graph = SemanticGraph::new(":memory:").unwrap();
                    let tenant = "tenant-scale";
                    for i in 0..entry_count {
                        let mapping = make_mapping(i, tenant);
                        let _ = graph.insert_mapping(&mapping);
                    }
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_concurrent_safety_validations,
    bench_1000_concurrent,
    bench_concurrent_graph_writes,
    bench_unbounded_state_growth,
    bench_concurrent_memory_cache,
    bench_burst_traffic,
    bench_memory_chip_scaling,
    bench_semantic_graph_scaling,
);
criterion_main!(benches);
