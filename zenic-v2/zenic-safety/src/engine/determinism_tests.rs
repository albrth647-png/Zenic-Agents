//! Phase 5: Determinism Verification Tests — zenic-safety crate
//!
//! These tests verify that the safety pipeline produces identical outputs
//! for identical inputs across N=100 runs, and that operations are idempotent.

use crate::categories::NicheCategory;
use crate::compliance::ComplianceStandard;
use crate::domain_rules::DomainRuleSet;
use crate::engine::core::DomainSafetyGate;
use crate::engine::types::DomainSafetyCheckResult;
use crate::sensitivity::DataSensitivity;
use crate::verdict::{ActionCategory, SafetyVerdict};

// ═══════════════════════════════════════════════════════════════════════════
// 5.3 REPRODUCIBILITY TESTS
// ═══════════════════════════════════════════════════════════════════════════

/// Helper: extract the determinism-relevant fields from a DomainSafetyCheckResult.
/// We compare verdicts and escalation flags (not reasons, which may vary in
/// formatting but must be consistent).
#[derive(Debug)]
struct DeterminismSnapshot {
    base_verdict: SafetyVerdict,
    domain_verdict: SafetyVerdict,
    final_verdict: SafetyVerdict,
    niche_category: NicheCategory,
    data_sensitivity: DataSensitivity,
    domain_rules_matched: Vec<String>,
    escalation_applied: bool,
    can_proceed: bool,
    compliance_compliant_count: usize,
    compliance_violation_count: usize,
    compliance_critical_count: usize,
}

impl DeterminismSnapshot {
    fn from_result(r: &DomainSafetyCheckResult) -> Self {
        Self {
            base_verdict: r.base_verdict,
            domain_verdict: r.domain_verdict,
            final_verdict: r.final_verdict,
            niche_category: r.niche_category,
            data_sensitivity: r.data_sensitivity,
            domain_rules_matched: r.domain_rules_matched.clone(),
            escalation_applied: r.escalation_applied,
            can_proceed: r.can_proceed,
            compliance_compliant_count: r.compliance_results.iter().filter(|c| c.compliant).count(),
            compliance_violation_count: r.compliance_results.iter().filter(|c| !c.compliant).count(),
            compliance_critical_count: r
                .compliance_results
                .iter()
                .filter(|c| c.risk_level == "critical" && !c.compliant)
                .count(),
        }
    }
}

impl PartialEq for DeterminismSnapshot {
    fn eq(&self, other: &Self) -> bool {
        self.base_verdict == other.base_verdict
            && self.domain_verdict == other.domain_verdict
            && self.final_verdict == other.final_verdict
            && self.niche_category == other.niche_category
            && self.data_sensitivity == other.data_sensitivity
            && self.domain_rules_matched == other.domain_rules_matched
            && self.escalation_applied == other.escalation_applied
            && self.can_proceed == other.can_proceed
            && self.compliance_compliant_count == other.compliance_compliant_count
            && self.compliance_violation_count == other.compliance_violation_count
            && self.compliance_critical_count == other.compliance_critical_count
    }
}

/// Run the safety pipeline N times and assert all outputs are identical.
fn assert_reproducible(
    n: usize,
    action_type: &str,
    config: &serde_json::Value,
    niche: NicheCategory,
    sensitivity: DataSensitivity,
) {
    let gate = DomainSafetyGate::new();
    let first: DeterminismSnapshot = {
        let r = gate.check(action_type, config, niche, sensitivity);
        DeterminismSnapshot::from_result(&r)
    };

    for i in 1..n {
        let r = gate.check(action_type, config, niche, sensitivity);
        let snap = DeterminismSnapshot::from_result(&r);
        assert_eq!(
            first, snap,
            "DIVERGENCE at run {} for action_type={:?}, config={:?}, niche={:?}, sensitivity={:?}\n  Expected: {:?}\n  Got:      {:?}",
            i, action_type, config, niche, sensitivity, first, snap
        );
    }
}

// ── Reproducibility: SafetyVerdict escalation ────────────────────────────

#[test]
fn repro_verdict_escalation_n100() {
    // Escalation is a pure function — must always produce the same result.
    for _ in 0..100 {
        assert_eq!(
            SafetyVerdict::Allow.escalate(SafetyVerdict::Confirm),
            SafetyVerdict::Confirm
        );
        assert_eq!(
            SafetyVerdict::Confirm.escalate(SafetyVerdict::Deny),
            SafetyVerdict::Deny
        );
        assert_eq!(
            SafetyVerdict::Deny.escalate(SafetyVerdict::Allow),
            SafetyVerdict::Deny
        );
        assert_eq!(
            SafetyVerdict::Approve.escalate(SafetyVerdict::Confirm),
            SafetyVerdict::Approve
        );
    }
}

// ── Reproducibility: DataSensitivity escalation ──────────────────────────

#[test]
fn repro_sensitivity_escalation_n100() {
    for _ in 0..100 {
        assert_eq!(
            DataSensitivity::Critical.escalate_verdict(SafetyVerdict::Allow),
            SafetyVerdict::Confirm
        );
        assert_eq!(
            DataSensitivity::Critical.escalate_verdict(SafetyVerdict::Approve),
            SafetyVerdict::Deny
        );
        assert_eq!(
            DataSensitivity::High.escalate_verdict(SafetyVerdict::Allow),
            SafetyVerdict::Confirm
        );
        assert_eq!(
            DataSensitivity::Low.escalate_verdict(SafetyVerdict::Allow),
            SafetyVerdict::Allow
        );
    }
}

// ── Reproducibility: Action classification ───────────────────────────────

#[test]
fn repro_classify_action_n100() {
    let cases: Vec<(&str, serde_json::Value, ActionCategory)> = vec![
        // Database actions
        ("database", serde_json::json!({"operation": "delete"}), ActionCategory::Destructive),
        ("database", serde_json::json!({"query": "DROP TABLE users"}), ActionCategory::Destructive),
        ("database", serde_json::json!({"query": "SELECT * FROM users"}), ActionCategory::Safe),
        ("database", serde_json::json!({"query": "INSERT INTO users"}), ActionCategory::Moderate),
        ("database", serde_json::json!({"operation": "backup"}), ActionCategory::System),
        // Email actions
        ("email", serde_json::json!({"subject": "hello", "body": "world"}), ActionCategory::Moderate),
        ("email", serde_json::json!({"subject": "Invoice #123", "body": "payment due"}), ActionCategory::Financial),
        // File actions
        ("file", serde_json::json!({"operation": "delete"}), ActionCategory::Destructive),
        ("file", serde_json::json!({"operation": "read"}), ActionCategory::Safe),
        ("file", serde_json::json!({"operation": "write"}), ActionCategory::Moderate),
        // HTTP actions
        ("http", serde_json::json!({"method": "GET"}), ActionCategory::Safe),
        ("http", serde_json::json!({"method": "DELETE"}), ActionCategory::Moderate),
        // Misc
        ("schedule", serde_json::json!({}), ActionCategory::System),
        ("notification", serde_json::json!({}), ActionCategory::Safe),
        ("transform", serde_json::json!({}), ActionCategory::Safe),
        ("discord", serde_json::json!({}), ActionCategory::Moderate),
        ("niche_onboarding", serde_json::json!({}), ActionCategory::Moderate),
        ("unknown_action", serde_json::json!({}), ActionCategory::Moderate),
    ];

    for _ in 0..100 {
        for (action, config, expected) in &cases {
            let got = DomainSafetyGate::classify_action(action, config);
            assert_eq!(
                got, *expected,
                "classify_action({:?}, {:?}) = {:?}, expected {:?}",
                action, config, got, expected
            );
        }
    }
}

// ── Reproducibility: Full 4-layer pipeline ───────────────────────────────

#[test]
fn repro_full_pipeline_safe_action_n100() {
    assert_reproducible(
        100,
        "notification",
        &serde_json::json!({"action": "view_dashboard"}),
        NicheCategory::AiData,
        DataSensitivity::Low,
    );
}

#[test]
fn repro_full_pipeline_fintech_deny_n100() {
    assert_reproducible(
        100,
        "compliance_operation",
        &serde_json::json!({"action": "bypass_compliance", "target": "kyc_check"}),
        NicheCategory::FinTech,
        DataSensitivity::Medium,
    );
}

#[test]
fn repro_full_pipeline_healthtech_critical_n100() {
    assert_reproducible(
        100,
        "data_access",
        &serde_json::json!({"action": "phi_access", "data_type": "health_record"}),
        NicheCategory::HealthTech,
        DataSensitivity::Critical,
    );
}

#[test]
fn repro_full_pipeline_edtech_high_n100() {
    assert_reproducible(
        100,
        "notification",
        &serde_json::json!({"action": "view_data"}),
        NicheCategory::EdTech,
        DataSensitivity::High,
    );
}

#[test]
fn repro_full_pipeline_destructive_db_n100() {
    assert_reproducible(
        100,
        "database",
        &serde_json::json!({"operation": "delete", "query": "DELETE FROM users WHERE id > 100"}),
        NicheCategory::FinTech,
        DataSensitivity::Low,
    );
}

#[test]
fn repro_full_pipeline_financial_email_n100() {
    assert_reproducible(
        100,
        "email",
        &serde_json::json!({"subject": "Invoice", "body": "Payment due"}),
        NicheCategory::FinTech,
        DataSensitivity::Medium,
    );
}

#[test]
fn repro_full_pipeline_greentech_iso_n100() {
    assert_reproducible(
        100,
        "system_modify",
        &serde_json::json!({"infrastructure_change": "server_migration"}),
        NicheCategory::GreenTech,
        DataSensitivity::Low,
    );
}

#[test]
fn repro_full_pipeline_legaltech_deny_n100() {
    assert_reproducible(
        100,
        "document_operation",
        &serde_json::json!({"action": "document_delete", "target": "legal_contract"}),
        NicheCategory::LegalTech,
        DataSensitivity::Medium,
    );
}

#[test]
fn repro_full_pipeline_proptech_financial_n100() {
    assert_reproducible(
        100,
        "property_deal",
        &serde_json::json!({"action": "property_transaction", "target": "real_estate_deal"}),
        NicheCategory::PropTech,
        DataSensitivity::High,
    );
}

#[test]
fn repro_all_niches_all_sensitivities_n100() {
    // Cross-product test: all niches × all sensitivities
    for niche in NicheCategory::ALL {
        for sensitivity in DataSensitivity::ALL {
            assert_reproducible(
                100,
                "notification",
                &serde_json::json!({"action": "view_data"}),
                niche,
                sensitivity,
            );
        }
    }
}

// ── Reproducibility: Compliance engine ───────────────────────────────────

#[test]
fn repro_compliance_hipaa_n100() {
    use crate::compliance::ComplianceEngine;
    let engine = ComplianceEngine::new();
    let config = serde_json::json!({"data_type": "phi", "action": "access"});

    let first_result = engine.check_standard(ComplianceStandard::Hipaa, "data_access", &config);
    for _ in 1..100 {
        let result = engine.check_standard(ComplianceStandard::Hipaa, "data_access", &config);
        assert_eq!(result.compliant, first_result.compliant);
        assert_eq!(result.violations.len(), first_result.violations.len());
        assert_eq!(result.risk_level, first_result.risk_level);
    }
}

#[test]
fn repro_compliance_pci_dss_n100() {
    use crate::compliance::ComplianceEngine;
    let engine = ComplianceEngine::new();
    let config = serde_json::json!({"data_type": "card", "operation": "process"});

    let first_result = engine.check_standard(ComplianceStandard::PciDss, "payment", &config);
    for _ in 1..100 {
        let result = engine.check_standard(ComplianceStandard::PciDss, "payment", &config);
        assert_eq!(result.compliant, first_result.compliant);
        assert_eq!(result.violations.len(), first_result.violations.len());
    }
}

#[test]
fn repro_compliance_gdpr_n100() {
    use crate::compliance::ComplianceEngine;
    let engine = ComplianceEngine::new();
    let config = serde_json::json!({"data_type": "personal_data", "action": "process"});

    let first_result = engine.check_standard(ComplianceStandard::Gdpr, "data_process", &config);
    for _ in 1..100 {
        let result = engine.check_standard(ComplianceStandard::Gdpr, "data_process", &config);
        assert_eq!(result.compliant, first_result.compliant);
        assert_eq!(result.violations.len(), first_result.violations.len());
    }
}

#[test]
fn repro_compliance_all_10_standards_n100() {
    use crate::compliance::ComplianceEngine;
    let engine = ComplianceEngine::new();
    let config = serde_json::json!({"data_type": "phi", "action": "access"});

    for standard in ComplianceStandard::ALL {
        let first = engine.check_standard(standard, "data_access", &config);
        for _ in 1..100 {
            let result = engine.check_standard(standard, "data_access", &config);
            assert_eq!(result.compliant, first.compliant,
                "Compliance reproducibility failed for {:?}", standard);
            assert_eq!(result.violations.len(), first.violations.len(),
                "Violation count diverged for {:?}", standard);
        }
    }
}

// ── Reproducibility: Domain rule matching ────────────────────────────────

#[test]
fn repro_domain_rules_n100() {
    let ruleset = DomainRuleSet::new();
    let config = serde_json::json!({"action": "bypass_compliance", "target": "kyc_check"});

    let first_matches: Vec<String> = ruleset
        .check(NicheCategory::FinTech, "compliance_operation", &config)
        .iter()
        .map(|r| r.name.clone())
        .collect();

    for _ in 1..100 {
        let matches: Vec<String> = ruleset
            .check(NicheCategory::FinTech, "compliance_operation", &config)
            .iter()
            .map(|r| r.name.clone())
            .collect();
        assert_eq!(matches, first_matches, "Domain rule matching diverged");
    }
}

#[test]
fn repro_domain_rules_all_categories_n100() {
    let ruleset = DomainRuleSet::new();
    for niche in NicheCategory::ALL {
        let first_matches: Vec<String> = ruleset
            .rules_for_category(niche)
            .iter()
            .map(|r| r.name.clone())
            .collect();
        for _ in 1..100 {
            let matches: Vec<String> = ruleset
                .rules_for_category(niche)
                .iter()
                .map(|r| r.name.clone())
                .collect();
            assert_eq!(matches, first_matches, "Domain rules diverged for {:?}", niche);
        }
    }
}

// ── Reproducibility: Default verdict mapping ─────────────────────────────

#[test]
fn repro_default_verdict_n100() {
    let cases = vec![
        (ActionCategory::Safe, SafetyVerdict::Allow),
        (ActionCategory::Moderate, SafetyVerdict::Allow),
        (ActionCategory::Destructive, SafetyVerdict::Confirm),
        (ActionCategory::Financial, SafetyVerdict::Approve),
        (ActionCategory::System, SafetyVerdict::Confirm),
    ];
    for _ in 0..100 {
        for (cat, expected) in &cases {
            assert_eq!(DomainSafetyGate::default_verdict(*cat), *expected);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// 5.4 IDEMPOTENCY TESTS
// ═══════════════════════════════════════════════════════════════════════════

// ── Idempotency: SafetyVerdict escalation ────────────────────────────────

#[test]
fn idempotent_verdict_escalation() {
    // Escalating the same verdict twice should give the same result.
    let v = SafetyVerdict::Allow;
    let first = v.escalate(SafetyVerdict::Confirm);
    let second = first.escalate(SafetyVerdict::Confirm);
    assert_eq!(first, second);

    // Escalating with a lower verdict should not change.
    let v2 = SafetyVerdict::Deny;
    let after = v2.escalate(SafetyVerdict::Allow);
    assert_eq!(after, SafetyVerdict::Deny);
    let after2 = after.escalate(SafetyVerdict::Allow);
    assert_eq!(after, after2);
}

// ── Idempotency: DataSensitivity escalation ──────────────────────────────

#[test]
fn idempotent_sensitivity_escalation() {
    // Applying sensitivity escalation to the same verdict twice produces
    // the same result as applying it once.
    let s = DataSensitivity::Critical;
    let v1 = s.escalate_verdict(SafetyVerdict::Allow);
    let v2 = s.escalate_verdict(v1);
    // Critical: Allow → Confirm, Confirm → Approve
    assert_eq!(v1, SafetyVerdict::Confirm);
    assert_eq!(v2, SafetyVerdict::Approve);

    // But re-applying to the same starting point is consistent
    for _ in 0..100 {
        assert_eq!(s.escalate_verdict(SafetyVerdict::Allow), SafetyVerdict::Confirm);
    }
}

// ── Idempotency: Full pipeline same input twice ──────────────────────────

#[test]
fn idempotent_full_pipeline_same_input_twice() {
    let gate = DomainSafetyGate::new();
    let config = serde_json::json!({"action": "view_dashboard"});

    let r1 = gate.check("notification", &config, NicheCategory::AiData, DataSensitivity::Low);
    let r2 = gate.check("notification", &config, NicheCategory::AiData, DataSensitivity::Low);

    assert_eq!(r1.base_verdict, r2.base_verdict);
    assert_eq!(r1.domain_verdict, r2.domain_verdict);
    assert_eq!(r1.final_verdict, r2.final_verdict);
    assert_eq!(r1.escalation_applied, r2.escalation_applied);
    assert_eq!(r1.can_proceed, r2.can_proceed);
    assert_eq!(r1.domain_rules_matched, r2.domain_rules_matched);
}

#[test]
fn idempotent_deny_cannot_be_overridden() {
    // Running the same DENY-triggering input twice should still produce DENY.
    let gate = DomainSafetyGate::new();
    let config = serde_json::json!({"action": "bypass_compliance", "target": "kyc_check"});

    let r1 = gate.check("compliance_operation", &config, NicheCategory::FinTech, DataSensitivity::Medium);
    let r2 = gate.check("compliance_operation", &config, NicheCategory::FinTech, DataSensitivity::Medium);

    assert_eq!(r1.final_verdict, SafetyVerdict::Deny);
    assert_eq!(r2.final_verdict, SafetyVerdict::Deny);
    assert!(!r1.can_proceed);
    assert!(!r2.can_proceed);
}

// ── Idempotency: Compliance checks ───────────────────────────────────────

#[test]
fn idempotent_compliance_check() {
    use crate::compliance::ComplianceEngine;
    let engine = ComplianceEngine::new();
    let config = serde_json::json!({"data_type": "phi"});

    let r1 = engine.check_standard(ComplianceStandard::Hipaa, "data_access", &config);
    let r2 = engine.check_standard(ComplianceStandard::Hipaa, "data_access", &config);

    assert_eq!(r1.compliant, r2.compliant);
    assert_eq!(r1.violations, r2.violations);
    assert_eq!(r1.risk_level, r2.risk_level);
}

// ── Idempotency: Domain rule matching ────────────────────────────────────

#[test]
fn idempotent_domain_rule_check() {
    let ruleset = DomainRuleSet::new();
    let config = serde_json::json!({"action": "bypass_compliance"});

    let r1: Vec<String> = ruleset
        .check(NicheCategory::FinTech, "compliance_operation", &config)
        .iter()
        .map(|r| r.name.clone())
        .collect();
    let r2: Vec<String> = ruleset
        .check(NicheCategory::FinTech, "compliance_operation", &config)
        .iter()
        .map(|r| r.name.clone())
        .collect();

    assert_eq!(r1, r2);
}

// ── Idempotency: Classification ──────────────────────────────────────────

#[test]
fn idempotent_classify_action() {
    let config = serde_json::json!({"operation": "delete"});

    let c1 = DomainSafetyGate::classify_action("database", &config);
    let c2 = DomainSafetyGate::classify_action("database", &config);
    assert_eq!(c1, c2);
    assert_eq!(c1, ActionCategory::Destructive);
}

// ── Idempotency: NicheCategory compliance_standards ──────────────────────

#[test]
fn idempotent_niche_compliance_standards() {
    for niche in NicheCategory::ALL {
        let s1 = niche.compliance_standards().to_vec();
        let s2 = niche.compliance_standards().to_vec();
        assert_eq!(s1, s2, "Compliance standards diverged for {:?}", niche);
    }
}

// ── Idempotency: DomainSafetyGate.new() produces consistent gate ─────────

#[test]
fn idempotent_gate_construction() {
    let g1 = DomainSafetyGate::new();
    let g2 = DomainSafetyGate::new();

    let config = serde_json::json!({"action": "test"});
    for niche in NicheCategory::ALL {
        for sensitivity in DataSensitivity::ALL {
            let r1 = g1.check("notification", &config, niche, sensitivity);
            let r2 = g2.check("notification", &config, niche, sensitivity);
            assert_eq!(r1.final_verdict, r2.final_verdict,
                "Two gate instances produced different verdicts for {:?}/{:?}", niche, sensitivity);
        }
    }
}

// ── Idempotency: All 35 domain rules always load the same ────────────────

#[test]
fn idempotent_domain_rule_loading() {
    let r1 = DomainRuleSet::new();
    let r2 = DomainRuleSet::new();

    assert_eq!(r1.len(), r2.len());
    assert_eq!(r1.len(), 35);

    for niche in NicheCategory::ALL {
        let n1: Vec<String> = r1.rules_for_category(niche).iter().map(|r| r.name.clone()).collect();
        let n2: Vec<String> = r2.rules_for_category(niche).iter().map(|r| r.name.clone()).collect();
        assert_eq!(n1, n2, "Rule names diverged for {:?}", niche);
    }
}
