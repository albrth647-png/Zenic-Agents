//! Scalability limit testing — Determine breaking points and degradation curves.
//!
//! Measures:
//! - Single process: max concurrent safety checks before degradation
//! - MemoryCache scaling: 10K, 100K, 1M entries with insert + lookup
//! - SemanticGraph scaling: INSERT + SELECT at 10K, 50K, 100K rows
//! - DAG graph size limits: blast radius at 100, 500, 1000, 5000 nodes
//! - Workflow step count limits: 10, 50, 100, 500 steps
//! - MerkleSeal: batch verification at scale
//! - Encrypted DB: write throughput at scale

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use std::sync::Arc;
use std::thread;

use zenic_memory::{
    LearningMechanism, MemoryCache, MerkleSeal, SemanticGraph, SemanticMapping,
};
use zenic_safety::categories::NicheCategory;
use zenic_safety::engine::DomainSafetyGate;
use zenic_safety::sensitivity::DataSensitivity;
use serde_json::json;
use zenic_flow::engine::{StepExecutor, WorkflowDefinition, WorkflowEngine};
use zenic_flow::retry::RetryPolicy;
use zenic_flow::step::WorkflowStep;
use zenic_proto::{SessionId, TenantId, WorkflowId};

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

struct SuccessExecutor;

impl StepExecutor for SuccessExecutor {
    fn execute_step(
        &self,
        _step: &WorkflowStep,
        _input: Option<&[u8]>,
    ) -> Result<Vec<u8>, String> {
        Ok(vec![])
    }
}

// ---------------------------------------------------------------------------
// 6.4.1: Single process — concurrent safety checks degradation
// ---------------------------------------------------------------------------

fn bench_concurrent_safety_degradation(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/concurrent_safety_degradation");
    group.sample_size(10);

    let iters_per_thread = 100;

    for &num_threads in &[1usize, 2, 4, 8, 16, 32] {
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
                                let config = json!({"action": "view_dashboard"});
                                let niche = NicheCategory::ALL[thread_id % 7];
                                let sensitivity = DataSensitivity::ALL[thread_id % 4];

                                for i in 0..iters_per_thread {
                                    let action = match i % 3 {
                                        0 => "notification",
                                        1 => "database",
                                        _ => "email",
                                    };
                                    let _ = gate.check(
                                        black_box(action),
                                        black_box(&config),
                                        black_box(niche),
                                        black_box(sensitivity),
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
// 6.4.2: MemoryCache scaling — insert + lookup at scale
// ---------------------------------------------------------------------------

fn bench_memory_cache_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/memory_cache_scaling");
    group.sample_size(10);

    for &max_size in &[1_000usize, 10_000, 100_000] {
        let cache = Arc::new(MemoryCache::new(max_size));
        let tenant = "tenant-scale";

        // Pre-populate to 80% capacity
        let populate_count = (max_size as f64 * 0.8) as usize;
        for i in 0..populate_count {
            let mapping = make_mapping(i, tenant);
            let _ = cache.insert(&format!("origin-{}", i), &mapping, tenant);
        }

        // Lookup at 80% capacity
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("lookup_at_80pct", max_size),
            &cache,
            |b, cache| {
                let mut idx = 0;
                b.iter(|| {
                    let key = format!("origin-{}", idx % populate_count);
                    let _ = cache.lookup(black_box(&key), black_box(tenant));
                    idx += 1;
                });
            },
        );

        // Insert at 80% capacity (near eviction)
        let cache2 = Arc::new(MemoryCache::new(max_size));
        for i in 0..populate_count {
            let mapping = make_mapping(i, tenant);
            let _ = cache2.insert(&format!("origin-{}", i), &mapping, tenant);
        }

        group.bench_with_input(
            BenchmarkId::new("insert_at_80pct", max_size),
            &cache2,
            |b, cache2| {
                let mut idx = populate_count;
                b.iter(|| {
                    let mapping = make_mapping(idx, tenant);
                    let _ = cache2.insert(
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
// 6.4.2b: SemanticGraph scaling — INSERT + SELECT at scale
// ---------------------------------------------------------------------------

fn bench_semantic_graph_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/semantic_graph_scaling");
    group.sample_size(10);

    for &row_count in &[1_000usize, 10_000, 50_000] {
        let tenant = "tenant-graph-scale";

        // Bulk INSERT throughput
        group.throughput(Throughput::Elements(row_count as u64));
        group.bench_with_input(
            BenchmarkId::new("bulk_insert", row_count),
            &row_count,
            |b, &row_count| {
                b.iter(|| {
                    let graph = SemanticGraph::new(":memory:").unwrap();
                    for i in 0..row_count {
                        let mapping = make_mapping(i, tenant);
                        let _ = graph.insert_mapping(&mapping);
                    }
                });
            },
        );

        // SELECT after pre-population
        let graph = SemanticGraph::new(":memory:").unwrap();
        for i in 0..row_count {
            let mapping = make_mapping(i, tenant);
            let _ = graph.insert_mapping(&mapping);
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("lookup_after_populate", row_count),
            &graph,
            |b, graph| {
                let mut idx = 0;
                b.iter(|| {
                    let origin = format!("origin-{}", idx % row_count);
                    let _ = graph.lookup(black_box(&origin), black_box(tenant));
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.4.3: DAG graph size limits — blast radius at scale
// ---------------------------------------------------------------------------

fn bench_dag_blast_radius_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/dag_blast_radius");
    group.sample_size(10);

    use std::collections::{HashMap, HashSet, VecDeque};

    for &node_count in &[100usize, 500, 1000, 5000] {
        // Build a DAG with fanout=3
        let mut edges: Vec<(String, String)> = Vec::new();
        for i in 0..node_count {
            for j in 1..=3 {
                let target = i * 3 + j;
                if target < node_count {
                    edges.push((format!("n{}", i), format!("n{}", target)));
                }
            }
        }

        let mut forward: HashMap<String, Vec<String>> = HashMap::new();
        for (src, dst) in &edges {
            forward.entry(src.clone()).or_default().push(dst.clone());
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("bfs_from_root", node_count),
            &forward,
            |b, forward| {
                b.iter(|| {
                    let mut visited = HashSet::new();
                    let mut queue = VecDeque::new();
                    queue.push_back("n0".to_string());

                    while let Some(current) = queue.pop_front() {
                        if visited.contains(&current) {
                            continue;
                        }
                        visited.insert(current.clone());
                        if let Some(neighbors) = forward.get(&current) {
                            for n in neighbors {
                                if !visited.contains(n) {
                                    queue.push_back(n.clone());
                                }
                            }
                        }
                    }
                    let _ = black_box(visited.len());
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.4.4: Workflow step count limits
// ---------------------------------------------------------------------------

fn bench_workflow_step_limits(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/workflow_steps");
    group.sample_size(10);

    let executor = SuccessExecutor;

    for &step_count in &[10usize, 50, 100, 500] {
        let steps: Vec<WorkflowStep> = (0..step_count)
            .map(|i| WorkflowStep::new(&format!("step_{}", i), &format!("Step {}", i)))
            .collect();
        let definition = WorkflowDefinition::new(
            WorkflowId::new(),
            &format!("bench_{}_steps", step_count),
            "Benchmark",
            steps,
            RetryPolicy::no_retry(),
        );

        group.throughput(Throughput::Elements(step_count as u64));
        group.bench_with_input(
            BenchmarkId::new("execute", step_count),
            &definition,
            |b, definition| {
                b.iter(|| {
                    let mut engine = WorkflowEngine::new();
                    let _ = engine.execute(
                        black_box(definition),
                        black_box(&executor),
                        black_box(SessionId::new()),
                        black_box(TenantId::new()),
                    );
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.4.5: MerkleSeal batch verification at scale
// ---------------------------------------------------------------------------

fn bench_merkle_batch_verification(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/merkle_batch_verification");
    group.sample_size(10);

    for &count in &[100usize, 1000, 5000] {
        let mut seal = MerkleSeal::new();
        let mut pairs = Vec::with_capacity(count);
        for i in 0..count {
            let mapping = make_mapping(i, "tenant-seal");
            let hash = seal.seal_mapping(&mapping).unwrap();
            pairs.push((mapping, hash));
        }

        group.throughput(Throughput::Elements(count as u64));
        group.bench_with_input(
            BenchmarkId::new("verify_batch", count),
            &(seal, pairs),
            |b, (seal, pairs)| {
                b.iter(|| {
                    let results = seal.verify_batch(black_box(pairs));
                    let _ = black_box(results);
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// 6.4.6: Encrypted DB write throughput at scale
// ---------------------------------------------------------------------------

fn bench_encrypted_db_write_throughput(c: &mut Criterion) {
    let mut group = c.benchmark_group("scalability/encrypted_db_writes");
    group.sample_size(10);

    use rusqlite::Connection;

    for &batch_size in &[100usize, 1000, 10000] {
        group.throughput(Throughput::Elements(batch_size as u64));
        group.bench_with_input(
            BenchmarkId::new("encrypted_insert_batch", batch_size),
            &batch_size,
            |b, &batch_size| {
                b.iter(|| {
                    let conn = Connection::open(":memory:").unwrap();
                    conn.pragma_update(None, "key", "bench_key").unwrap();
                    conn.execute_batch(
                        "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, value REAL, data BLOB)"
                    ).unwrap();

                    let tx = conn.unchecked_transaction().unwrap();
                    for i in 0..batch_size {
                        conn.execute(
                            "INSERT INTO t (id, name, value, data) VALUES (?1, ?2, ?3, ?4)",
                            rusqlite::params![
                                i as i64,
                                format!("name-{}", i),
                                i as f64 * 1.5,
                                vec![0u8; 64]
                            ],
                        ).unwrap();
                    }
                    tx.commit().unwrap();
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_concurrent_safety_degradation,
    bench_memory_cache_scaling,
    bench_semantic_graph_scaling,
    bench_dag_blast_radius_scaling,
    bench_workflow_step_limits,
    bench_merkle_batch_verification,
    bench_encrypted_db_write_throughput,
);
criterion_main!(benches);
