// ─── Zenic-Agents v3 — Saga Orchestrator Types ──────────────────────────
// USDT TRC20 ONLY. Type definitions for the Saga pattern implementation.
// All subscription lifecycle operations are managed as Sagas with
// compensating actions for rollback on failure.

// ═══════════════════════════════════════════════════════════════════════════
// Saga Type Constants
// ═══════════════════════════════════════════════════════════════════════════

export const SagaTypeName = {
  CANCELLATION: "cancellation",
  RENEWAL: "renewal",
  UPGRADE: "upgrade",
  DOWNGRADE: "downgrade",
  REACTIVATION: "reactivation",
} as const;
export type SagaTypeName = (typeof SagaTypeName)[keyof typeof SagaTypeName];

export const SagaStatusName = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  COMPENSATING: "compensating",
  COMPENSATED: "compensated",
  FAILED: "failed",
  TIMED_OUT: "timed_out",
  PAUSED: "paused",
} as const;
export type SagaStatusName = (typeof SagaStatusName)[keyof typeof SagaStatusName];

export const SagaStepStatusName = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
  COMPENSATING: "compensating",
  COMPENSATED: "compensated",
  SKIPPED: "skipped",
} as const;
export type SagaStepStatusName = (typeof SagaStepStatusName)[keyof typeof SagaStepStatusName];

// ═══════════════════════════════════════════════════════════════════════════
// Saga Result Types
// ═══════════════════════════════════════════════════════════════════════════

export interface SagaStepResult {
  success: boolean;
  output?: Record<string, unknown>;
  error?: string;
}

export interface SagaOrchestratorResult {
  executionId: string;
  sagaType: SagaTypeName;
  status: SagaStatusName;
  currentStepIndex: number;
  totalSteps: number;
  completedSteps: number;
  errorMessage?: string;
  compensationReason?: string;
  steps: Array<{
    stepIndex: number;
    stepName: string;
    status: SagaStepStatusName;
    output?: Record<string, unknown>;
    error?: string;
  }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Handler Types
// ═══════════════════════════════════════════════════════════════════════════

export type StepHandler = (input: Record<string, unknown>) => Promise<SagaStepResult>;
export type CompensationHandler = (input: Record<string, unknown>, stepOutput: Record<string, unknown>) => Promise<void>;

// ═══════════════════════════════════════════════════════════════════════════
// Saga Definition Types
// ═══════════════════════════════════════════════════════════════════════════

export interface SagaStepDefinition {
  step_index: number;
  step_name: string;
  description: string;
  action: string;
  compensating_action: string;
  is_critical: boolean;
  timeout_ms: number;
  retry_count: number;
  requires_external_input: boolean;
}

export interface SagaDefinition {
  saga_type: string;
  version: string;
  description: string;
  steps: SagaStepDefinition[];
  timeout_ms: number;
  max_retries: number;
  payment_currency: string;
  payment_network: string;
}
