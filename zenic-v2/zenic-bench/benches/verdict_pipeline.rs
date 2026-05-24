//! Benchmarks for VerdictAdapter — LLM verdict processing pipeline.
//!
//! Measures:
//! - VerdictAdapter::process_verdict (deterministic path, Layer 1)
//! - VerdictAdapter::process_verdict (IA YES path, Layer 4)
//! - VerdictAdapter::process_verdict (IA NO path, Layer 4)
//! - VerdictAdapter::process_verdict (escalation path, tie score)
//! - VerdictAdapter::process_full_verdict (with mapping context)
//! - VerdictAdapter::construct_binary_question
//! - VerdictAdapter::format_qwen3_prompt
//! - VerdictAdapter::parse_llm_response (SÍ/NO tokens)
//! - Cold-start: new adapter + first verdict
//! - Repeated verdicts (warm adapter)

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use zenic_memory::{LearningMechanism, LearningVerdict, SemanticMapping, VerdictAdapter};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_mapping(id: usize) -> SemanticMapping {
    SemanticMapping::new(
        format!("verdict-map-{id}"),
        format!("origin-{id}"),
        "synonym_of".to_string(),
        format!("dest-{id}"),
        LearningMechanism::SchemaDrift,
    )
}

/// Layer 1 deterministic verdict (auto-commit, no IA needed)
fn deterministic_verdict() -> LearningVerdict {
    let mapping = make_mapping(0);
    LearningVerdict::deterministic_accept(mapping)
}

/// IA YES verdict (Layer 4, affirmative)
fn ia_yes_verdict() -> LearningVerdict {
    let mapping = make_mapping(0);
    LearningVerdict::ia_verdict(
        mapping,
        true,       // ia_response = YES
        vec!["ia_confirmed".to_string()],
        vec!["low_consensus".to_string()],
        0.8,
    )
}

/// IA NO verdict (Layer 4, negative)
fn ia_no_verdict() -> LearningVerdict {
    let mapping = make_mapping(0);
    LearningVerdict::ia_verdict(
        mapping,
        false,      // ia_response = NO
        vec![],
        vec!["ia_rejected".to_string(), "low_confidence".to_string()],
        -0.7,
    )
}

/// Tie/escalation verdict (consensus near zero)
fn tie_verdict() -> LearningVerdict {
    let mapping = make_mapping(0);
    LearningVerdict::ia_verdict(
        mapping,
        false,      // ia_response = NO
        vec!["some_evidence".to_string()],
        vec!["some_counterevidence".to_string()],
        0.05,       // Near-zero consensus → tie → escalation
    )
}

// ---------------------------------------------------------------------------
// Benchmark: process_verdict — deterministic path (Layer 1)
// ---------------------------------------------------------------------------

fn bench_process_verdict_deterministic(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/process_verdict");
    group.throughput(Throughput::Elements(1));

    group.bench_function("deterministic_layer1", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let verdict = deterministic_verdict();
            let _ = adapter.process_verdict(black_box(verdict));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: process_verdict — IA YES path
// ---------------------------------------------------------------------------

fn bench_process_verdict_ia_yes(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/process_verdict");
    group.throughput(Throughput::Elements(1));

    group.bench_function("ia_yes_layer4", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let verdict = ia_yes_verdict();
            let _ = adapter.process_verdict(black_box(verdict));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: process_verdict — IA NO path
// ---------------------------------------------------------------------------

fn bench_process_verdict_ia_no(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/process_verdict");
    group.throughput(Throughput::Elements(1));

    group.bench_function("ia_no_layer4", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let verdict = ia_no_verdict();
            let _ = adapter.process_verdict(black_box(verdict));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: process_verdict — escalation (tie) path
// ---------------------------------------------------------------------------

fn bench_process_verdict_escalation(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/process_verdict");
    group.throughput(Throughput::Elements(1));

    group.bench_function("escalation_tie", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let verdict = tie_verdict();
            let _ = adapter.process_verdict(black_box(verdict));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: process_full_verdict (with mapping + HITL)
// ---------------------------------------------------------------------------

fn bench_process_full_verdict(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/process_full_verdict");
    group.throughput(Throughput::Elements(1));

    group.bench_function("full_deterministic", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let mapping = make_mapping(0);
            let verdict = deterministic_verdict();
            let _ = adapter.process_full_verdict(
                black_box(mapping),
                black_box(verdict),
            );
        });
    });

    group.bench_function("full_escalation", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let mapping = make_mapping(0);
            let verdict = tie_verdict();
            let _ = adapter.process_full_verdict(
                black_box(mapping),
                black_box(verdict),
            );
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Cold-start (new adapter + first verdict)
// ---------------------------------------------------------------------------

fn bench_cold_start(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/cold_start");
    group.throughput(Throughput::Elements(1));

    group.bench_function("new_adapter_first_verdict", |b| {
        b.iter(|| {
            let mut adapter = VerdictAdapter::new();
            let _ = adapter.process_verdict(black_box(deterministic_verdict()));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Binary question construction
// ---------------------------------------------------------------------------

fn bench_binary_question(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/binary_question");
    group.throughput(Throughput::Elements(1));

    group.bench_function("construct", |b| {
        let mapping = make_mapping(0);
        b.iter(|| {
            let _ = VerdictAdapter::construct_binary_question(black_box(&mapping));
        });
    });

    group.bench_function("format_qwen3_prompt", |b| {
        let mapping = make_mapping(0);
        b.iter(|| {
            let _ = VerdictAdapter::format_qwen3_prompt(black_box(&mapping));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: LLM response parsing
// ---------------------------------------------------------------------------

fn bench_parse_llm_response(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/parse_llm_response");
    group.throughput(Throughput::Elements(1));

    let tokens = ["SÍ", "NO", "SI", "YES", "N", "1", "0"];

    for token in &tokens {
        group.bench_with_input(
            BenchmarkId::new("token", *token),
            token,
            |b, token| {
                b.iter(|| {
                    let _ = VerdictAdapter::parse_llm_response(black_box(token));
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Repeated verdicts (warm adapter)
// ---------------------------------------------------------------------------

fn bench_repeated_verdicts(c: &mut Criterion) {
    let mut group = c.benchmark_group("verdict_pipeline/repeated_verdicts");

    for &count in &[1usize, 10, 100, 1000] {
        group.throughput(Throughput::Elements(count as u64));
        group.bench_with_input(
            BenchmarkId::new("batch", count),
            &count,
            |b, &count| {
                b.iter(|| {
                    let mut adapter = VerdictAdapter::new();
                    for i in 0..count {
                        let verdict = if i % 3 == 0 {
                            deterministic_verdict()
                        } else if i % 3 == 1 {
                            ia_yes_verdict()
                        } else {
                            ia_no_verdict()
                        };
                        let _ = adapter.process_verdict(black_box(verdict));
                    }
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_process_verdict_deterministic,
    bench_process_verdict_ia_yes,
    bench_process_verdict_ia_no,
    bench_process_verdict_escalation,
    bench_process_full_verdict,
    bench_cold_start,
    bench_binary_question,
    bench_parse_llm_response,
    bench_repeated_verdicts,
);
criterion_main!(benches);
