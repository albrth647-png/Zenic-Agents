//! Benchmarks for WorkflowEngine — Durable workflow execution with SAGA compensation.
//!
//! Measures:
//! - Workflow definition creation and validation
//! - Single-step workflow execution
//! - Multi-step workflow (5, 10, 50 steps)
//! - Workflow with retry policy
//! - SAGA compensation execution time
//! - Checkpoint save/restore
//! - Workflow with compensation keys

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use zenic_flow::engine::{StepExecutor, WorkflowDefinition, WorkflowEngine};
use zenic_flow::retry::RetryPolicy;
use zenic_flow::step::WorkflowStep;
use zenic_proto::{SessionId, TenantId, WorkflowId};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// A trivial step executor that always succeeds with empty output.
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

/// A step executor that fails on a specific step name.
struct FailOnStepExecutor {
    fail_step: String,
}

impl StepExecutor for FailOnStepExecutor {
    fn execute_step(
        &self,
        step: &WorkflowStep,
        _input: Option<&[u8]>,
    ) -> Result<Vec<u8>, String> {
        if step.name == self.fail_step {
            Err(format!("Intentional failure on step '{}'", step.name))
        } else {
            Ok(vec![])
        }
    }
}

fn make_workflow(step_count: usize, with_compensation: bool) -> WorkflowDefinition {
    let steps: Vec<WorkflowStep> = (0..step_count)
        .map(|i| {
            let mut step = WorkflowStep::new(
                &format!("step_{}", i),
                &format!("Step {} of {}", i, step_count),
            );
            if with_compensation {
                step = step.compensation_key(&format!("compensate_{}", i));
            }
            step
        })
        .collect();

    WorkflowDefinition::new(
        WorkflowId::new(),
        &format!("bench_workflow_{}", step_count),
        "Benchmark workflow",
        steps,
        RetryPolicy::no_retry(),
    )
}

// ---------------------------------------------------------------------------
// Benchmark: Single-step workflow
// ---------------------------------------------------------------------------

fn bench_single_step(c: &mut Criterion) {
    let mut group = c.benchmark_group("workflow_engine/single_step");
    group.throughput(Throughput::Elements(1));

    group.bench_function("execute", |b| {
        let executor = SuccessExecutor;
        let definition = make_workflow(1, false);
        b.iter(|| {
            let mut engine = WorkflowEngine::new();
            let _ = engine.execute(
                black_box(&definition),
                black_box(&executor),
                black_box(SessionId::new()),
                black_box(TenantId::new()),
            );
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Multi-step workflow
// ---------------------------------------------------------------------------

fn bench_multi_step(c: &mut Criterion) {
    let mut group = c.benchmark_group("workflow_engine/multi_step");

    for &step_count in &[5usize, 10, 25, 50] {
        group.throughput(Throughput::Elements(step_count as u64));
        group.bench_with_input(
            BenchmarkId::new("steps", step_count),
            &step_count,
            |b, &step_count| {
                let executor = SuccessExecutor;
                let definition = make_workflow(step_count, false);
                b.iter(|| {
                    let mut engine = WorkflowEngine::new();
                    let _ = engine.execute(
                        black_box(&definition),
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
// Benchmark: Workflow with retry
// ---------------------------------------------------------------------------

fn bench_with_retry(c: &mut Criterion) {
    let mut group = c.benchmark_group("workflow_engine/with_retry");
    group.throughput(Throughput::Elements(1));

    let mut steps = vec![WorkflowStep::new("step_0", "Always succeeds")];
    steps.push(
        WorkflowStep::new("step_1", "Has retry")
            .retry_policy(RetryPolicy::new(3, 100, 1000, 2.0)),
    );
    steps.push(WorkflowStep::new("step_2", "Also succeeds"));

    let definition = WorkflowDefinition::new(
        WorkflowId::new(),
        "retry_workflow",
        "Benchmark with retry policy",
        steps,
        RetryPolicy::no_retry(),
    );

    group.bench_function("3_step_with_retry", |b| {
        let executor = SuccessExecutor;
        b.iter(|| {
            let mut engine = WorkflowEngine::new();
            let _ = engine.execute(
                black_box(&definition),
                black_box(&executor),
                black_box(SessionId::new()),
                black_box(TenantId::new()),
            );
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: SAGA compensation
// ---------------------------------------------------------------------------

fn bench_saga_compensation(c: &mut Criterion) {
    let mut group = c.benchmark_group("workflow_engine/saga_compensation");

    for &step_count in &[5usize, 10, 25] {
        group.throughput(Throughput::Elements(step_count as u64));
        group.bench_with_input(
            BenchmarkId::new("compensate", step_count),
            &step_count,
            |b, &step_count| {
                let executor = FailOnStepExecutor {
                    fail_step: format!("step_{}", step_count / 2),
                };
                let definition = make_workflow(step_count, true);
                b.iter(|| {
                    let mut engine = WorkflowEngine::new();
                    // Register trivial compensations
                    for i in 0..step_count {
                        let _ = engine.register_compensation(
                            &format!("compensate_{}", i),
                            Box::new(NoOpCompensation),
                        );
                    }
                    let _ = engine.execute(
                        black_box(&definition),
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
// Benchmark: Checkpoint operations
// ---------------------------------------------------------------------------

fn bench_checkpoint(c: &mut Criterion) {
    let mut group = c.benchmark_group("workflow_engine/checkpoint");
    group.throughput(Throughput::Elements(1));

    let executor = SuccessExecutor;

    group.bench_function("5_step_checkpoint_count", |b| {
        let definition = make_workflow(5, false);
        b.iter(|| {
            let mut engine = WorkflowEngine::new();
            let _ = engine.execute(
                black_box(&definition),
                black_box(&executor),
                black_box(SessionId::new()),
                black_box(TenantId::new()),
            );
            // Each step creates a checkpoint
            let _ = black_box(engine.checkpoint_count());
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// NoOp Compensation
// ---------------------------------------------------------------------------

use zenic_flow::compensation::CompensationAction;
use zenic_flow::step::StepResult;

struct NoOpCompensation;

impl CompensationAction for NoOpCompensation {
    fn compensate(&self, _result: &StepResult) -> Result<(), zenic_flow::errors::FlowError> {
        Ok(())
    }

    fn name(&self) -> &str {
        "no_op_compensation"
    }
}

criterion_group!(
    benches,
    bench_single_step,
    bench_multi_step,
    bench_with_retry,
    bench_saga_compensation,
    bench_checkpoint,
);
criterion_main!(benches);
