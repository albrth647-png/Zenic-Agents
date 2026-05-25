//! Benchmarks for DomainSafetyGate — 4-layer safety validation pipeline.
//!
//! Measures:
//! - Cold-start validation (fresh gate, no prior state)
//! - Cache-hit validation (same action type, repeated)
//! - All 7 NicheCategory validations
//! - Extended compliance check (safety_validate_extended path)
//! - Rate limiter overhead
//! - Safety rule regex matching

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use serde_json::json;

use zenic_safety::categories::NicheCategory;
use zenic_safety::compliance::ComplianceEngine;
use zenic_safety::domain_rules::DomainRuleSet;
use zenic_safety::engine::DomainSafetyGate;
use zenic_safety::sensitivity::DataSensitivity;
use zenic_safety::verdict::SafetyVerdict;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Standard config for a safe action.
fn safe_config() -> serde_json::Value {
    json!({"action": "view_dashboard"})
}

/// Config for a destructive database action.
fn destructive_config() -> serde_json::Value {
    json!({"operation": "delete", "query": "DROP TABLE users"})
}

/// Config for a financial action.
fn financial_config() -> serde_json::Value {
    json!({"action": "invoice_create", "subject": "Monthly invoice", "body": "Payment due"})
}

/// Config for a healthtech PHI access.
fn health_phi_config() -> serde_json::Value {
    json!({"action": "phi_access", "data_type": "health_record"})
}

// ---------------------------------------------------------------------------
// Benchmark: Safety gate cold-start validation
// ---------------------------------------------------------------------------

/// Measures the cost of creating a new DomainSafetyGate and running one check.
/// This captures the one-time initialization cost of DomainRuleSet (35 rules)
/// and ComplianceEngine.
fn bench_cold_start(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/cold_start");

    let configs: Vec<(&str, serde_json::Value, NicheCategory, DataSensitivity)> = vec![
        ("safe_notification", safe_config(), NicheCategory::AiData, DataSensitivity::Low),
        ("destructive_db", destructive_config(), NicheCategory::FinTech, DataSensitivity::Low),
        ("financial_email", financial_config(), NicheCategory::FinTech, DataSensitivity::Medium),
        ("health_phi", health_phi_config(), NicheCategory::HealthTech, DataSensitivity::Critical),
    ];

    for (name, config, niche, sensitivity) in &configs {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("new_gate_per_iter", name),
            &(*config, *niche, *sensitivity),
            |b, &(config, niche, sensitivity)| {
                b.iter(|| {
                    let gate = DomainSafetyGate::new();
                    let _result = gate.check(
                        black_box("notification"),
                        black_box(&config),
                        black_box(niche),
                        black_box(sensitivity),
                    );
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Reused gate (warm cache hit path)
// ---------------------------------------------------------------------------

/// Measures the cost of checking with a pre-created gate.
/// This isolates the check() overhead without initialization cost.
fn bench_warm_gate(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/warm_check");

    let gate = DomainSafetyGate::new();

    // Safe action — short-circuit at Layer 1
    group.throughput(Throughput::Elements(1));
    group.bench_function("safe_allow", |b| {
        let config = safe_config();
        b.iter(|| {
            let _ = gate.check(
                black_box("notification"),
                black_box(&config),
                black_box(NicheCategory::AiData),
                black_box(DataSensitivity::Low),
            );
        });
    });

    // Destructive action — traverses all 4 layers
    group.bench_function("destructive_deny", |b| {
        let config = destructive_config();
        b.iter(|| {
            let _ = gate.check(
                black_box("database"),
                black_box(&config),
                black_box(NicheCategory::FinTech),
                black_box(DataSensitivity::Low),
            );
        });
    });

    // Financial action with compliance
    group.bench_function("financial_compliance", |b| {
        let config = financial_config();
        b.iter(|| {
            let _ = gate.check(
                black_box("email"),
                black_box(&config),
                black_box(NicheCategory::FinTech),
                black_box(DataSensitivity::Medium),
            );
        });
    });

    // Critical sensitivity escalation
    group.bench_function("critical_escalation", |b| {
        let config = safe_config();
        b.iter(|| {
            let _ = gate.check(
                black_box("notification"),
                black_box(&config),
                black_box(NicheCategory::HealthTech),
                black_box(DataSensitivity::Critical),
            );
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: All 7 NicheCategory validations
// ---------------------------------------------------------------------------

/// Measures validation across all 7 niche categories.
/// Each category has 5 domain-specific rules and varying compliance standards.
fn bench_all_niche_categories(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/all_niches");

    let gate = DomainSafetyGate::new();
    let config = json!({"action": "data_access"});

    for niche in NicheCategory::ALL {
        let niche_name = niche.as_str();
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("niche_check", niche_name),
            &niche,
            |b, &niche| {
                b.iter(|| {
                    let _ = gate.check(
                        black_box("data_access"),
                        black_box(&config),
                        black_box(niche),
                        black_box(DataSensitivity::Medium),
                    );
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Compliance engine alone
// ---------------------------------------------------------------------------

/// Measures compliance checking overhead for each standard.
fn bench_compliance_alone(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/compliance");

    let engine = ComplianceEngine::new();
    let phi_config = json!({"data_type": "phi", "action": "access"});

    use zenic_safety::compliance::ComplianceStandard;
    let standards = [
        (ComplianceStandard::Hipaa, "hipaa"),
        (ComplianceStandard::PciDss, "pci_dss"),
        (ComplianceStandard::Gdpr, "gdpr"),
        (ComplianceStandard::Sox, "sox"),
        (ComplianceStandard::AmlKyc, "aml_kyc"),
        (ComplianceStandard::Coppa, "coppa"),
        (ComplianceStandard::Iso27001, "iso_27001"),
        (ComplianceStandard::Soc2, "soc2"),
    ];

    for (standard, name) in &standards {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("standard", name),
            &(*standard,),
            |b, &(standard,)| {
                b.iter(|| {
                    let _ = engine.check_standard(
                        black_box(standard),
                        black_box("data_access"),
                        black_box(&phi_config),
                    );
                });
            },
        );
    }

    // Category-wide compliance (3-4 standards at once)
    for niche in NicheCategory::ALL {
        let niche_name = niche.as_str();
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("category_check", niche_name),
            &niche,
            |b, &niche| {
                b.iter(|| {
                    let _ = engine.check_category(
                        black_box(niche),
                        black_box("data_access"),
                        black_box(&phi_config),
                    );
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Domain rule matching
// ---------------------------------------------------------------------------

/// Measures domain rule set matching performance.
fn bench_domain_rules(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/domain_rules");

    let ruleset = DomainRuleSet::new();

    // Test each category
    for niche in NicheCategory::ALL {
        let niche_name = niche.as_str();
        let config = json!({"action": "phi_access", "target": "health_record"});
        group.throughput(Throughput::Elements(5)); // 5 rules per category
        group.bench_with_input(
            BenchmarkId::new("check", niche_name),
            &niche,
            |b, &niche| {
                b.iter(|| {
                    let _ = ruleset.check(
                        black_box(niche),
                        black_box("data_access"),
                        black_box(&config),
                    );
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Sensitivity escalation
// ---------------------------------------------------------------------------

/// Measures sensitivity escalation performance.
fn bench_sensitivity_escalation(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/sensitivity_escalation");

    for sensitivity in DataSensitivity::ALL {
        let name = format!("{:?}", sensitivity);
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("escalate", name),
            &sensitivity,
            |b, &sensitivity| {
                b.iter(|| {
                    let _ = sensitivity.escalate_verdict(black_box(SafetyVerdict::Allow));
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Classify action
// ---------------------------------------------------------------------------

/// Measures action classification performance (Layer 1).
fn bench_classify_action(c: &mut Criterion) {
    let mut group = c.benchmark_group("safety_gate/classify_action");

    let cases: Vec<(&str, serde_json::Value)> = vec![
        ("database", json!({"operation": "delete", "query": "DELETE FROM users"})),
        ("email", json!({"subject": "Invoice", "body": "Payment due"})),
        ("file", json!({"operation": "delete"})),
        ("http", json!({"method": "DELETE"})),
        ("notification", json!({})),
        ("schedule", json!({})),
        ("transform", json!({})),
        ("niche_onboarding", json!({})),
    ];

    for (action_type, config) in &cases {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("action", action_type),
            &(*action_type, config.clone()),
            |b, &(action_type, config)| {
                b.iter(|| {
                    let _ = DomainSafetyGate::classify_action(
                        black_box(action_type),
                        black_box(&config),
                    );
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_cold_start,
    bench_warm_gate,
    bench_all_niche_categories,
    bench_compliance_alone,
    bench_domain_rules,
    bench_sensitivity_escalation,
    bench_classify_action,
);
criterion_main!(benches);
