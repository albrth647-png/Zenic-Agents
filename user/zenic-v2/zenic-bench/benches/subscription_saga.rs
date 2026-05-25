//! Benchmarks for SubscriptionSaga and PricingEngine.
//!
//! Measures:
//! - SignupSaga execution time
//! - PaymentSaga execution time
//! - CancellationSaga execution time
//! - RenewalSaga execution time
//! - UpgradeSaga execution time
//! - PricingEngine calculation time
//! - PricingEngine recommendation time

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use zenic_subscription::pricing::PricingEngine;
use zenic_subscription::saga::{
    CancellationSaga, PaymentSaga, RenewalSaga, SignupSaga, SubscriptionSaga, UpgradeSaga,
    SagaContext,
};
use zenic_subscription::types::SubscriptionTierName;
use zenic_proto::TenantId;

// ---------------------------------------------------------------------------
// Benchmark: SignupSaga
// ---------------------------------------------------------------------------

fn bench_signup_saga(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/signup");
    group.throughput(Throughput::Elements(1));

    group.bench_function("success_path", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Starter);
            let saga = SignupSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.bench_function("duplicate_user_failure", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Starter);
            ctx.set_data("user_exists", "true");
            let saga = SignupSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: PaymentSaga
// ---------------------------------------------------------------------------

fn bench_payment_saga(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/payment");
    group.throughput(Throughput::Elements(1));

    group.bench_function("success_path", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Business);
            ctx.set_data("payment_verified", "true");
            let saga = PaymentSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: CancellationSaga
// ---------------------------------------------------------------------------

fn bench_cancellation_saga(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/cancellation");
    group.throughput(Throughput::Elements(1));

    group.bench_function("success_path", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Business);
            ctx.set_data("subscription_active", "true");
            let saga = CancellationSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: RenewalSaga
// ---------------------------------------------------------------------------

fn bench_renewal_saga(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/renewal");
    group.throughput(Throughput::Elements(1));

    group.bench_function("success_path", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Business);
            ctx.set_data("renewal_eligible", "true");
            let saga = RenewalSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: UpgradeSaga
// ---------------------------------------------------------------------------

fn bench_upgrade_saga(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/upgrade");
    group.throughput(Throughput::Elements(1));

    group.bench_function("starter_to_business", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Starter);
            ctx.set_data("target_tier", "Business");
            let saga = UpgradeSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.bench_function("business_to_enterprise", |b| {
        b.iter(|| {
            let mut ctx = SagaContext::new(TenantId::new(), SubscriptionTierName::Business);
            ctx.set_data("target_tier", "Enterprise");
            let saga = UpgradeSaga;
            let _ = black_box(saga.execute(black_box(&mut ctx)));
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: PricingEngine
// ---------------------------------------------------------------------------

fn bench_pricing_engine(c: &mut Criterion) {
    let mut group = c.benchmark_group("subscription_saga/pricing");

    // Monthly cost calculation
    for tier in [
        SubscriptionTierName::Starter,
        SubscriptionTierName::Business,
        SubscriptionTierName::Enterprise,
    ] {
        let tier_name = format!("{:?}", tier);
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("monthly_cost", tier_name),
            &tier,
            |b, &tier| {
                b.iter(|| {
                    let _ = PricingEngine::calculate_monthly_cost(
                        black_box(tier),
                        black_box(&[]),
                    );
                });
            },
        );
    }

    // Annual cost
    group.throughput(Throughput::Elements(1));
    group.bench_function("annual_cost", |b| {
        b.iter(|| {
            let _ = PricingEngine::calculate_annual_cost(
                black_box(SubscriptionTierName::Business),
                black_box(&[]),
            );
        });
    });

    // Upgrade proration
    group.throughput(Throughput::Elements(1));
    group.bench_function("upgrade_proration", |b| {
        b.iter(|| {
            let _ = PricingEngine::calculate_upgrade_proration(
                black_box(SubscriptionTierName::Starter),
                black_box(SubscriptionTierName::Business),
                black_box(15),
                black_box(30),
            );
        });
    });

    // Tier recommendation
    group.throughput(Throughput::Elements(1));
    group.bench_function("recommend_tier", |b| {
        b.iter(|| {
            let _ = PricingEngine::recommend_tier(
                black_box(10),
                black_box(500),
                black_box(5),
                black_box(true),
                black_box(false),
            );
        });
    });

    // Payment validation
    group.throughput(Throughput::Elements(1));
    group.bench_function("validate_payment", |b| {
        b.iter(|| {
            let _ = PricingEngine::validate_payment_amount(
                black_box(99),
                black_box(99),
                black_box(2.0),
            );
        });
    });

    // Format pricing report (string formatting — heavier)
    group.throughput(Throughput::Elements(1));
    group.bench_function("format_report", |b| {
        b.iter(|| {
            let _ = PricingEngine::format_pricing_report(
                black_box(SubscriptionTierName::Business),
                black_box(&["extra_workflows_10".to_string()]),
            );
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_signup_saga,
    bench_payment_saga,
    bench_cancellation_saga,
    bench_renewal_saga,
    bench_upgrade_saga,
    bench_pricing_engine,
);
criterion_main!(benches);
