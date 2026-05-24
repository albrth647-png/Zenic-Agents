//! Subscription query tests: read-only accessors and trial expiration checks.
//!
//! The `impl SubscriptionEngine` methods that were previously here are now
//! consolidated in `engine_impl.rs`.

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use crate::engine::SubscriptionEngine;
    use crate::payment::UsdtPaymentMethod;
    use crate::types::SubscriptionStatus;
    use zenic_proto::TenantId;

    fn make_engine() -> SubscriptionEngine {
        SubscriptionEngine::new(
            "TCompanyWallet1234567890abcdefghijk".to_string(),
            UsdtPaymentMethod::Manual,
        )
    }

    #[test]
    fn engine_trial_expiration() {
        let mut engine = make_engine();
        let tenant = TenantId::new();

        engine.signup(tenant, 1000).expect("signup");

        // Expire the trial (14 days later).
        let expired = engine.check_trial_expirations(1000 + crate::trial::TRIAL_DURATION_MS);
        assert_eq!(expired.len(), 1);

        let subscription = engine.get_subscription(&tenant).expect("subscription");
        assert_eq!(subscription.status, SubscriptionStatus::Expired);
    }

    #[test]
    fn engine_company_wallet() {
        let engine = make_engine();
        assert!(engine.company_wallet().starts_with('T'));
    }
}
