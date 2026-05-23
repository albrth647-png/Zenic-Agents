//! Benchmarks for MerkleSeal — BLAKE3-based cryptographic integrity.
//!
//! Measures:
//! - BLAKE3 hash computation (single mapping)
//! - Merkle root computation (batch)
//! - seal_mapping (serialize + hash + update root)
//! - verify_mapping (serialize + compare hash)
//! - verify_batch (N verifications)
//! - verify_graph_integrity (full graph check)

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use zenic_memory::{LearningMechanism, MerkleSeal, SemanticGraph, SemanticMapping};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_mapping(id: usize) -> SemanticMapping {
    SemanticMapping::new(
        format!("map-{id}"),
        format!("origin-{id}"),
        "synonym_of".to_string(),
        format!("dest-{id}"),
        LearningMechanism::SchemaDrift,
    )
}

fn make_large_mapping(id: usize) -> SemanticMapping {
    let long_origin = "x".repeat(1024);
    let long_dest = "y".repeat(1024);
    SemanticMapping::new(
        format!("map-large-{id}"),
        format!("{long_origin}-{id}"),
        "synonym_of".to_string(),
        format!("{long_dest}-{id}"),
        LearningMechanism::IntentRouting,
    )
}

fn populate_and_seal(seal: &mut MerkleSeal, count: usize) -> Vec<String> {
    let mut hashes = Vec::with_capacity(count);
    for i in 0..count {
        let mapping = make_mapping(i);
        let hash = seal.seal_mapping(&mapping).unwrap();
        hashes.push(hash);
    }
    hashes
}

// ---------------------------------------------------------------------------
// Benchmark: BLAKE3 single hash
// ---------------------------------------------------------------------------

/// Measures raw BLAKE3 hash computation on different payload sizes.
fn bench_blake3_hash(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/blake3_hash");

    let payloads: Vec<(&str, Vec<u8>)> = vec![
        ("64_bytes", vec![0u8; 64]),
        ("256_bytes", vec![0u8; 256]),
        ("1_kb", vec![0u8; 1024]),
        ("4_kb", vec![0u8; 4096]),
        ("16_kb", vec![0u8; 16384]),
    ];

    for (name, payload) in &payloads {
        group.throughput(Throughput::Bytes(payload.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("payload", name),
            payload,
            |b, payload| {
                b.iter(|| {
                    let _ = blake3::hash(black_box(payload));
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: bincode serialization
// ---------------------------------------------------------------------------

/// Measures bincode serialization cost for SemanticMapping.
fn bench_bincode_serialize(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/bincode_serialize");

    let small = make_mapping(0);
    let large = make_large_mapping(0);

    group.throughput(Throughput::Elements(1));
    group.bench_function("small_mapping", |b| {
        b.iter(|| {
            let _ = bincode::serialize(black_box(&small));
        });
    });

    group.bench_function("large_mapping", |b| {
        b.iter(|| {
            let _ = bincode::serialize(black_box(&large));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: seal_mapping (full path: serialize + hash + store + update root)
// ---------------------------------------------------------------------------

/// Measures the full seal_mapping pipeline.
fn bench_seal_mapping(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/seal_mapping");

    for &pre_sealed in &[0usize, 10, 100, 1000] {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("pre_sealed", pre_sealed),
            &pre_sealed,
            |b, &pre_sealed| {
                let mut idx = pre_sealed;
                b.iter(|| {
                    let mut seal = MerkleSeal::new();
                    populate_and_seal(&mut seal, pre_sealed);
                    let mapping = make_mapping(idx);
                    let _ = seal.seal_mapping(black_box(&mapping)).unwrap();
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: verify_mapping
// ---------------------------------------------------------------------------

/// Measures mapping verification against a stored hash.
fn bench_verify_mapping(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/verify_mapping");

    for &count in &[1usize, 10, 100, 1000] {
        let mut seal = MerkleSeal::new();
        let hashes = populate_and_seal(&mut seal, count);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("sealed_count", count),
            &(seal, hashes),
            |b, (seal, hashes)| {
                let mut idx = 0;
                b.iter(|| {
                    let mapping = make_mapping(idx % count);
                    let hash = &hashes[idx % count];
                    let _ = seal.verify_mapping(black_box(&mapping), black_box(hash));
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: verify_batch
// ---------------------------------------------------------------------------

/// Measures batch verification of multiple mappings.
fn bench_verify_batch(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/verify_batch");

    for &batch_size in &[1usize, 10, 50, 100] {
        group.throughput(Throughput::Elements(batch_size as u64));
        group.bench_with_input(
            BenchmarkId::new("batch_size", batch_size),
            &batch_size,
            |b, &batch_size| {
                let mut seal = MerkleSeal::new();
                let hashes = populate_and_seal(&mut seal, batch_size);
                let pairs: Vec<(SemanticMapping, String)> = (0..batch_size)
                    .map(|i| (make_mapping(i), hashes[i].clone()))
                    .collect();

                b.iter(|| {
                    let _ = seal.verify_batch(black_box(&pairs));
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Merkle root computation (compute from leaves)
// ---------------------------------------------------------------------------

/// Measures computing a Merkle root from a set of leaf data.
fn bench_compute_root(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/compute_root");

    for &leaf_count in &[1usize, 10, 100, 1000] {
        let leaves: Vec<Vec<u8>> = (0..leaf_count)
            .map(|i| format!("leaf-{}", i).into_bytes())
            .collect();

        group.throughput(Throughput::Elements(leaf_count as u64));
        group.bench_with_input(
            BenchmarkId::new("leaf_count", leaf_count),
            &leaves,
            |b, leaves| {
                b.iter(|| {
                    let mut seal = MerkleSeal::new();
                    seal.compute(black_box(leaves));
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: verify_graph_integrity
// ---------------------------------------------------------------------------

/// Measures full graph integrity verification.
fn bench_verify_graph_integrity(c: &mut Criterion) {
    let mut group = c.benchmark_group("merkle_seal/verify_graph_integrity");

    for &mapping_count in &[10usize, 100, 500] {
        group.throughput(Throughput::Elements(mapping_count as u64));
        group.bench_with_input(
            BenchmarkId::new("mappings", mapping_count),
            &mapping_count,
            |b, &mapping_count| {
                b.iter(|| {
                    // Set up a graph with sealed mappings
                    let graph = SemanticGraph::new(":memory:").unwrap();
                    let mut seal = MerkleSeal::new();

                    for i in 0..mapping_count {
                        let mut mapping = make_mapping(i);
                        let hash = seal.seal_mapping(&mapping).unwrap();
                        mapping.merkle_hash = Some(hash);
                        graph.insert_mapping(&mapping).unwrap();
                    }

                    // Verify integrity
                    let _ = seal.verify_graph_integrity(black_box(&graph));
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_blake3_hash,
    bench_bincode_serialize,
    bench_seal_mapping,
    bench_verify_mapping,
    bench_verify_batch,
    bench_compute_root,
    bench_verify_graph_integrity,
);
criterion_main!(benches);
