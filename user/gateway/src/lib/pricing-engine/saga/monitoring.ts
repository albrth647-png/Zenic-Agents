// ─── Zenic-Agents v3 — Saga Monitoring ───────────────────────────────────
// USDT TRC20 ONLY. Read-only monitoring functions for saga execution status.
// Provides query capabilities for saga state, history, and tenant-level views.

import { db } from "@/lib/db";
import type {
  SagaTypeName,
  SagaStatusName,
  SagaStepStatusName,
  SagaOrchestratorResult,
} from "./types";

// ═══════════════════════════════════════════════════════════════════════════
// Monitoring Functions
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Get the status of a Saga execution
 */
export async function getSagaStatus(executionId: string): Promise<SagaOrchestratorResult | null> {
  const sagaExecution = await db.sagaExecution.findUnique({
    where: { executionId },
    include: { steps: { orderBy: { stepIndex: "asc" } } },
  });

  if (!sagaExecution) return null;

  return {
    executionId: sagaExecution.executionId,
    sagaType: sagaExecution.sagaType as SagaTypeName,
    status: sagaExecution.status as SagaStatusName,
    currentStepIndex: sagaExecution.currentStepIndex,
    totalSteps: sagaExecution.totalSteps,
    completedSteps: sagaExecution.completedSteps,
    errorMessage: sagaExecution.errorMessage || undefined,
    compensationReason: sagaExecution.compensationReason || undefined,
    steps: sagaExecution.steps.map(s => ({
      stepIndex: s.stepIndex,
      stepName: s.stepName,
      status: s.status as SagaStepStatusName,
      output: JSON.parse(s.output || "{}"),
      error: s.errorMessage || undefined,
    })),
  };
}

/**
 * Get all Sagas for a tenant
 */
export async function getSagasForTenant(tenantId: string): Promise<SagaOrchestratorResult[]> {
  const executions = await db.sagaExecution.findMany({
    where: { tenantId },
    include: { steps: { orderBy: { stepIndex: "asc" } } },
    orderBy: { createdAt: "desc" },
    take: 50,
  });

  return executions.map(saga => ({
    executionId: saga.executionId,
    sagaType: saga.sagaType as SagaTypeName,
    status: saga.status as SagaStatusName,
    currentStepIndex: saga.currentStepIndex,
    totalSteps: saga.totalSteps,
    completedSteps: saga.completedSteps,
    errorMessage: saga.errorMessage || undefined,
    compensationReason: saga.compensationReason || undefined,
    steps: saga.steps.map(s => ({
      stepIndex: s.stepIndex,
      stepName: s.stepName,
      status: s.status as SagaStepStatusName,
      output: JSON.parse(s.output || "{}"),
      error: s.errorMessage || undefined,
    })),
  }));
}

/**
 * Get a summary of saga statuses for a tenant.
 * Returns counts grouped by status.
 */
export async function getSagaStatusSummary(tenantId: string): Promise<Record<SagaStatusName, number>> {
  const executions = await db.sagaExecution.findMany({
    where: { tenantId },
    select: { status: true },
  });

  const summary: Record<string, number> = {
    pending: 0,
    running: 0,
    completed: 0,
    compensating: 0,
    compensated: 0,
    failed: 0,
    timed_out: 0,
    paused: 0,
  };

  for (const execution of executions) {
    const status = execution.status;
    if (status in summary) {
      summary[status]++;
    }
  }

  return summary as Record<SagaStatusName, number>;
}

/**
 * Check if a tenant has any active (running or paused) sagas.
 */
export async function hasActiveSagas(tenantId: string): Promise<boolean> {
  const count = await db.sagaExecution.count({
    where: {
      tenantId,
      status: { in: ["running", "paused", "compensating"] },
    },
  });
  return count > 0;
}

/**
 * Get the latest saga execution for a tenant.
 * Returns the most recent saga execution or null if none exist.
 */
export async function getLatestSagaForTenant(tenantId: string): Promise<SagaOrchestratorResult | null> {
  const sagaExecution = await db.sagaExecution.findFirst({
    where: { tenantId },
    include: { steps: { orderBy: { stepIndex: "asc" } } },
    orderBy: { createdAt: "desc" },
  });

  if (!sagaExecution) return null;

  return {
    executionId: sagaExecution.executionId,
    sagaType: sagaExecution.sagaType as SagaTypeName,
    status: sagaExecution.status as SagaStatusName,
    currentStepIndex: sagaExecution.currentStepIndex,
    totalSteps: sagaExecution.totalSteps,
    completedSteps: sagaExecution.completedSteps,
    errorMessage: sagaExecution.errorMessage || undefined,
    compensationReason: sagaExecution.compensationReason || undefined,
    steps: sagaExecution.steps.map(s => ({
      stepIndex: s.stepIndex,
      stepName: s.stepName,
      status: s.status as SagaStepStatusName,
      output: JSON.parse(s.output || "{}"),
      error: s.errorMessage || undefined,
    })),
  };
}
