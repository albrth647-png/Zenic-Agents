//! Benchmarks for HITL Bridge + LifecycleManager — Human approval and
//! learning lifecycle operations.
//!
//! Measures:
//! - HITL Bridge: submit_for_review, approve (with validation), reject
//! - HITL Bridge: session validation
//! - LifecycleManager: start_episode, phase transitions
//! - LifecycleManager: full lifecycle (proposed → deployed)
//! - LifecycleManager: compensation path
//! - MemoryChip full pipeline: insert → approve → seal

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use zenic_memory::{
    HitlBridge, LearningMechanism, LearningVerdict, LifecycleManager, MemoryApprovalRequest,
    MerkleSeal, SemanticGraph, SemanticMapping,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_mapping(id: usize) -> SemanticMapping {
    SemanticMapping::new(
        format!("hitl-map-{id}"),
        format!("origin-{id}"),
        "synonym_of".to_string(),
        format!("dest-{id}"),
        LearningMechanism::SchemaDrift,
    )
}

fn make_valid_session_id() -> String {
    "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6".to_string() // 32 hex chars
}

fn make_approval_request(mapping_id: &str) -> MemoryApprovalRequest {
    MemoryApprovalRequest {
        admin_evidence_review: true,
        admin_justification: "This is a valid justification that meets the minimum length requirement of fifty characters.".to_string(),
        risk_acknowledgment: true,
        admin_session_id: make_valid_session_id(),
        mapping_id: mapping_id.to_string(),
        ia_question: "Is this mapping correct?".to_string(),
        ia_response: true,
        evidence_for: vec!["pattern_match".to_string()],
        evidence_against: vec![],
        consensus_score: 0.85,
    }
}

fn verdict_for_mapping() -> LearningVerdict {
    let mapping = make_mapping(0);
    LearningVerdict::ia_verdict(
        mapping,
        true,
        vec!["matched".to_string()],
        vec![],
        0.75,
    )
}

// ---------------------------------------------------------------------------
// Benchmark: HITL Bridge — submit_for_review
// ---------------------------------------------------------------------------

fn bench_hitl_submit(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/submit_for_review");
    group.throughput(Throughput::Elements(1));

    for &count in &[1usize, 10, 50, 100] {
        group.bench_with_input(
            BenchmarkId::new("batch", count),
            &count,
            |b, &count| {
                b.iter(|| {
                    let mut bridge = HitlBridge::new();
                    for i in 0..count {
                        let request = make_approval_request(&format!("map-{}", i));
                        let _ = bridge.submit_for_review(black_box(request));
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: HITL Bridge — approve (with GRIETA 3 validation)
// ---------------------------------------------------------------------------

fn bench_hitl_approve(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/approve");
    group.throughput(Throughput::Elements(1));

    group.bench_function("single_approve", |b| {
        b.iter(|| {
            let mut bridge = HitlBridge::new();
            let request = make_approval_request("map-0");
            let _ = bridge.submit_for_review(request);
            let _ = bridge.approve(
                black_box("map-0"),
                black_box(true),
                black_box("This is a valid justification that meets the minimum length requirement of fifty characters.".to_string()),
                black_box(true),
                black_box(make_valid_session_id()),
            );
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: HITL Bridge — reject
// ---------------------------------------------------------------------------

fn bench_hitl_reject(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/reject");
    group.throughput(Throughput::Elements(1));

    group.bench_function("single_reject", |b| {
        b.iter(|| {
            let mut bridge = HitlBridge::new();
            let request = make_approval_request("map-0");
            let _ = bridge.submit_for_review(request);
            let _ = bridge.reject(black_box("map-0"), black_box("test rejection"));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: HITL Bridge — session validation
// ---------------------------------------------------------------------------

fn bench_session_validation(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/session_validation");
    group.throughput(Throughput::Elements(1));

    let valid = make_valid_session_id();
    let invalid = "short";
    let non_hex = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz";

    group.bench_function("valid_session", |b| {
        b.iter(|| {
            let _ = HitlBridge::validate_session(black_box(&valid));
        });
    });

    group.bench_function("invalid_short", |b| {
        b.iter(|| {
            let _ = HitlBridge::validate_session(black_box(invalid));
        });
    });

    group.bench_function("invalid_non_hex", |b| {
        b.iter(|| {
            let _ = HitlBridge::validate_session(black_box(non_hex));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: LifecycleManager — start_episode
// ---------------------------------------------------------------------------

fn bench_lifecycle_start(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/start_episode");
    group.throughput(Throughput::Elements(1));

    group.bench_function("single_episode", |b| {
        b.iter(|| {
            let mut manager = LifecycleManager::new();
            let mapping = make_mapping(0);
            let _ = manager.start_episode(black_box(mapping));
        });
    });

    // Multiple episodes
    for &count in &[10usize, 50, 100] {
        group.throughput(Throughput::Elements(count as u64));
        group.bench_with_input(
            BenchmarkId::new("batch_episodes", count),
            &count,
            |b, &count| {
                b.iter(|| {
                    let mut manager = LifecycleManager::new();
                    for i in 0..count {
                        let mapping = make_mapping(i);
                        let _ = manager.start_episode(black_box(mapping));
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: LifecycleManager — full lifecycle (proposed → deployed)
// ---------------------------------------------------------------------------

fn bench_full_lifecycle(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/full_lifecycle");
    group.throughput(Throughput::Elements(1));

    group.bench_function("single_mapping_lifecycle", |b| {
        b.iter(|| {
            let mut manager = LifecycleManager::new();
            let mapping = make_mapping(0);
            let episode = manager.start_episode(mapping).unwrap();
            let id = episode.id.clone();

            // Propose → EvidenceCollected
            let _ = manager.collect_evidence(&id);
            // EvidenceCollected → ConsensusResolved
            let _ = manager.resolve_consensus(&id);
            // ConsensusResolved → Classified
            let mapping2 = make_mapping(0);
            let verdict = LearningVerdict::ia_verdict(
                mapping2, true,
                vec!["evidence".to_string()], vec![], 0.85,
            );
            manager.classify(&id, verdict);
            // Classified → Committed
            manager.validate(&id);
            // Committed → Deployed
            manager.deploy(&id);
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: LifecycleManager — compensation path
// ---------------------------------------------------------------------------

fn bench_lifecycle_compensation(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/compensation");
    group.throughput(Throughput::Elements(1));

    group.bench_function("discard_path", |b| {
        b.iter(|| {
            let mut manager = LifecycleManager::new();
            let mapping = make_mapping(0);
            let episode = manager.start_episode(mapping).unwrap();
            let id = episode.id.clone();
            manager.discard(&id, "bench discard");
        });
    });

    group.bench_function("compensate_simple_path", |b| {
        b.iter(|| {
            let mut manager = LifecycleManager::new();
            let mapping = make_mapping(0);
            let episode = manager.start_episode(mapping).unwrap();
            let id = episode.id.clone();
            manager.compensate_simple(&id, "bench compensate");
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Full MemoryChip pipeline (insert → approve → seal)
// ---------------------------------------------------------------------------

fn bench_memory_chip_pipeline(c: &mut Criterion) {
    let mut group = c.benchmark_group("hitl_lifecycle/memory_chip_pipeline");
    group.throughput(Throughput::Elements(1));

    group.bench_function("insert_approve_seal", |b| {
        b.iter(|| {
            let graph = SemanticGraph::new(":memory:").unwrap();
            let mut seal = MerkleSeal::new();
            let mut bridge = HitlBridge::new();

            let mapping = make_mapping(0);
            graph.insert_mapping(&mapping).unwrap();

            // Submit for HITL review
            let verdict = LearningVerdict::ia_verdict(
                make_mapping(0), true,
                vec!["evidence".to_string()], vec![], 0.85,
            );
            let request = HitlBridge::create_request_from_verdict(
                &verdict,
                make_valid_session_id(),
            );
            let _ = bridge.submit_for_review(request);

            // Approve
            let _ = bridge.approve(
                &mapping.mapping_id,
                true,
                "This is a valid justification that meets the minimum length requirement of fifty characters.".to_string(),
                true,
                make_valid_session_id(),
            );

            // Seal with Merkle
            let hash = seal.seal_mapping(&mapping).unwrap();

            // Update graph
            graph.approve_mapping(&mapping.mapping_id, &hash).unwrap();
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_hitl_submit,
    bench_hitl_approve,
    bench_hitl_reject,
    bench_session_validation,
    bench_lifecycle_start,
    bench_full_lifecycle,
    bench_lifecycle_compensation,
    bench_memory_chip_pipeline,
);
criterion_main!(benches);
